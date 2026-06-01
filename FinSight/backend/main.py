"""
FinSight FastAPI 主入口
"""
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from database import SessionLocal
from data_fetcher import init_data, get_data_status
from factor_engine import calculate_factors, get_factor_ranking, get_factor_radar, save_factor_scores
from lstm_model import train_model, predict_next, get_trained_models
from anomaly_detector import detect_anomalies, get_anomaly_alerts, get_anomaly_kline
from news_fetcher import save_news_to_db, get_recent_news, get_sentiment_summary
from sentiment_agent import ask_ai, ask_ai_stream

app = FastAPI(
    title="FinSight API",
    description="A股智能投研分析平台 - 金融数据挖掘课程设计",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ 响应模型 ============

class TrainRequest(BaseModel):
    ts_code: str
    epochs: int = 50


class ChatRequest(BaseModel):
    question: str
    ts_code: Optional[str] = None
    history: Optional[list] = None


# ============ 健康检查 ============

@app.get("/api/health", tags=["系统"])
def health_check():
    """健康检查"""
    return {"status": "ok", "service": "FinSight API"}


# ============ 行情接口 ============

@app.get("/api/market/indices", tags=["行情"])
def get_market_indices():
    """获取大盘指数概览"""
    db = SessionLocal()
    try:
        from sqlalchemy import text
        latest = db.execute(text(
            "SELECT MAX(trade_date) as latest_date FROM stock_daily"
        )).fetchone()

        if not latest or not latest[0]:
            return {"indices": [], "latest_date": None}

        latest_date = str(latest[0])

        stats = db.execute(text("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN pct_chg > 0 THEN 1 ELSE 0 END) as up_count,
                SUM(CASE WHEN pct_chg < 0 THEN 1 ELSE 0 END) as down_count,
                AVG(pct_chg) as avg_change
            FROM stock_daily
            WHERE trade_date = :date
        """), {"date": latest_date}).fetchone()

        # 获取上涨/下跌股票明细
        up_stocks = db.execute(text("""
            SELECT d.ts_code, s.name, d.pct_chg
            FROM stock_daily d
            JOIN stock_info s ON d.ts_code = s.ts_code
            WHERE d.trade_date = :date AND d.pct_chg > 0
            ORDER BY d.pct_chg DESC
        """), {"date": latest_date}).fetchall()

        down_stocks = db.execute(text("""
            SELECT d.ts_code, s.name, d.pct_chg
            FROM stock_daily d
            JOIN stock_info s ON d.ts_code = s.ts_code
            WHERE d.trade_date = :date AND d.pct_chg < 0
            ORDER BY d.pct_chg ASC
        """), {"date": latest_date}).fetchall()

        return {
            "latest_date": latest_date,
            "market_stats": {
                "total": stats[0],
                "up_count": stats[1],
                "down_count": stats[2],
                "avg_change": round(float(stats[3]), 4) if stats[3] else 0,
                "up_stocks": [{"ts_code": r[0], "name": r[1], "pct_chg": round(float(r[2]), 2)} for r in up_stocks],
                "down_stocks": [{"ts_code": r[0], "name": r[1], "pct_chg": round(float(r[2]), 2)} for r in down_stocks],
            }
        }
    finally:
        db.close()


@app.get("/api/market/kline/{ts_code}", tags=["行情"])
def get_kline(ts_code: str, limit: int = Query(120, ge=10, le=500)):
    """获取个股K线数据"""
    db = SessionLocal()
    try:
        from sqlalchemy import text
        rows = db.execute(text("""
            SELECT trade_date, open, close, high, low, vol, pct_chg
            FROM stock_daily
            WHERE ts_code = :code
            ORDER BY trade_date DESC
            LIMIT :limit
        """), {"code": ts_code, "limit": limit}).fetchall()

        kline = []
        for r in reversed(rows):
            kline.append({
                "date": str(r[0]),
                "open": float(r[1]) if r[1] else None,
                "close": float(r[2]) if r[2] else None,
                "high": float(r[3]) if r[3] else None,
                "low": float(r[4]) if r[4] else None,
                "volume": float(r[5]) if r[5] else None,
                "pct_change": float(r[6]) if r[6] else None,
            })
        return {"ts_code": ts_code, "kline": kline}
    finally:
        db.close()


@app.get("/api/market/sectors", tags=["行情"])
def get_sectors():
    """获取行业板块数据"""
    db = SessionLocal()
    try:
        from sqlalchemy import text
        rows = db.execute(text("""
            SELECT s.industry,
                   COUNT(DISTINCT d.ts_code) as stock_count,
                   AVG(d.pct_chg) as avg_change
            FROM stock_daily d
            JOIN stock_info s ON d.ts_code = s.ts_code
            WHERE d.trade_date = (SELECT MAX(trade_date) FROM stock_daily)
              AND s.industry IS NOT NULL
            GROUP BY s.industry
            ORDER BY avg_change DESC
        """)).fetchall()

        sectors = []
        for r in rows:
            sectors.append({
                "industry": r[0],
                "stock_count": r[1],
                "avg_change": round(float(r[2]), 4) if r[2] else 0,
            })
        return {"sectors": sectors}
    finally:
        db.close()


@app.get("/api/market/stocks", tags=["行情"])
def get_stock_list():
    """获取股票列表"""
    db = SessionLocal()
    try:
        from sqlalchemy import text
        rows = db.execute(text("""
            SELECT ts_code, name, industry
            FROM stock_info
            ORDER BY ts_code
        """)).fetchall()

        stocks = []
        for r in rows:
            stocks.append({
                "ts_code": r[0],
                "name": r[1],
                "industry": r[2],
            })
        return {"stocks": stocks, "total": len(stocks)}
    finally:
        db.close()


# ============ 因子选股接口 ============

@app.get("/api/factor/ranking", tags=["因子选股"])
def api_factor_ranking(
    industry: Optional[str] = Query(None, description="行业筛选"),
    top_n: int = Query(20, ge=5, le=100),
):
    """获取因子排名列表"""
    data = get_factor_ranking(industry=industry, top_n=top_n)
    return {"ranking": data, "total": len(data)}


@app.get("/api/factor/radar/{ts_code}", tags=["因子选股"])
def api_factor_radar(ts_code: str):
    """获取个股因子雷达数据"""
    data = get_factor_radar(ts_code)
    if not data:
        return {"error": f"未找到股票 {ts_code} 的因子数据"}
    return data


@app.post("/api/factor/refresh", tags=["因子选股"])
def api_factor_refresh():
    """重新计算因子评分"""
    df = calculate_factors()
    if df.empty:
        return {"success": False, "message": "数据不足，无法计算因子"}
    save_factor_scores(df)
    return {"success": True, "message": f"因子计算完成，共 {len(df)} 只股票"}


# ============ LSTM预测接口 ============

@app.post("/api/predict/train/{ts_code}", tags=["趋势预测"])
def api_predict_train(ts_code: str, epochs: int = Query(50, ge=10, le=200)):
    """训练LSTM模型"""
    result = train_model(ts_code, epochs=epochs)
    return result


@app.get("/api/predict/result/{ts_code}", tags=["趋势预测"])
def api_predict_result(ts_code: str, days: int = Query(5, ge=1, le=10)):
    """获取预测结果"""
    result = predict_next(ts_code, days=days)
    return result


@app.get("/api/predict/models", tags=["趋势预测"])
def api_predict_models():
    """获取已训练模型列表"""
    models = get_trained_models()
    return {"models": models}


# ============ 异常检测接口 ============

@app.get("/api/anomaly/detect", tags=["异常检测"])
def api_anomaly_detect(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
):
    """执行异常检测"""
    result = detect_anomalies(start_date=start_date, end_date=end_date)
    return result


@app.get("/api/anomaly/alerts", tags=["异常检测"])
def api_anomaly_alerts():
    """获取异常预警列表"""
    alerts = get_anomaly_alerts()
    return {"alerts": alerts}


@app.get("/api/anomaly/kline/{ts_code}", tags=["异常检测"])
def api_anomaly_kline(ts_code: str):
    """获取带异常标注的K线数据"""
    return get_anomaly_kline(ts_code)


# ============ 数据管理接口 ============

# 初始化进度状态
_init_status = {"running": False, "progress": "", "done": False, "error": None}


def _run_init_background():
    """后台执行数据初始化"""
    global _init_status
    try:
        _init_status = {"running": True, "progress": "开始采集...", "done": False, "error": None}
        # 重定向 print 到日志
        import sys, io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            init_data()
            output = sys.stdout.getvalue()
        finally:
            sys.stdout = old_stdout
        print(output, end="")
        _init_status["running"] = False
        _init_status["done"] = True
        _init_status["progress"] = "初始化完成"
    except Exception as e:
        _init_status["running"] = False
        _init_status["done"] = True
        _init_status["error"] = str(e)


@app.post("/api/data/init", tags=["数据管理"])
def api_data_init():
    """初始化数据（后台执行，立即返回）"""
    global _init_status
    if _init_status["running"]:
        return {"success": True, "message": "正在采集中，请勿重复点击"}
    import threading
    t = threading.Thread(target=_run_init_background, daemon=True)
    t.start()
    return {"success": True, "message": "数据采集已启动，请查看状态"}


@app.get("/api/data/init-status", tags=["数据管理"])
def api_init_status():
    """获取初始化进度"""
    return _init_status


@app.get("/api/data/status", tags=["数据管理"])
def api_data_status():
    """获取数据状态"""
    return get_data_status()


# ============ AI 助手接口 ============

@app.get("/api/chat/sentiment/{ts_code}", tags=["AI 助手"])
def api_chat_sentiment(ts_code: str, days: int = Query(7, ge=1, le=30)):
    """获取股票情感统计"""
    return get_sentiment_summary(ts_code, days=days)

@app.post("/api/chat/refresh-news/{ts_code}", tags=["AI 助手"])
def api_refresh_news(ts_code: str):
    """采集指定股票的新闻并做情感分析"""
    from database import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        name = db.execute(text(
            "SELECT name FROM stock_info WHERE ts_code = :code"
        ), {"code": ts_code}).scalar() or ts_code
    finally:
        db.close()

    count = save_news_to_db(ts_code, name)
    return {"success": True, "ts_code": ts_code, "name": name, "new_count": count}


@app.post("/api/chat/ask", tags=["AI 助手"])
def api_chat_ask(req: ChatRequest):
    """AI 问答"""
    result = ask_ai(req.question, ts_code=req.ts_code, history=req.history)
    return result


@app.post("/api/chat/ask-stream", tags=["AI 助手"])
async def api_chat_ask_stream(req: ChatRequest):
    """AI 问答（流式 SSE）"""
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        ask_ai_stream(req.question, ts_code=req.ts_code, history=req.history),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============ 启动入口 ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
