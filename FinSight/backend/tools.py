"""
FinSight 股小查工具集
搜索股票 + 调用项目各功能模块
"""
import time
import akshare as ak
from datetime import datetime, timedelta
from sqlalchemy import text
from database import SessionLocal
from config import STOCK_INDUSTRY_MAP


def search_stock(keyword: str) -> dict:
    """搜索A股股票代码和名称"""
    try:
        df = _akshare_retry(ak.stock_info_a_code_name)
        if df.empty:
            return {"found": False, "message": "无法获取股票列表"}

        result = df[
            df["name"].str.contains(keyword, na=False) |
            df["code"].str.contains(keyword, na=False)
        ]

        if result.empty:
            return {"found": False, "message": f"未找到匹配「{keyword}」的股票"}

        stocks = []
        for _, row in result.head(5).iterrows():
            code = row["code"]
            ts_code = f"{code}.SH" if code.startswith("6") else f"{code}.SZ"
            stocks.append({"ts_code": ts_code, "name": row["name"], "code": code})

        return {"found": True, "stocks": stocks}
    except Exception as e:
        return {"found": False, "message": f"搜索失败: {str(e)}"}


def get_stock_kline_data(ts_code: str, limit: int = 30) -> dict:
    """获取K线行情（优先查DB，查不到从AKShare实时拉）"""
    try:
        db = SessionLocal()
        rows = db.execute(text("""
            SELECT trade_date, close, pct_chg
            FROM stock_daily
            WHERE ts_code = :code
            ORDER BY trade_date DESC
            LIMIT :limit
        """), {"code": ts_code, "limit": limit}).fetchall()
        db.close()

        if rows:
            kline = [{"date": str(r[0]), "close": float(r[1]), "pct_change": float(r[2])} for r in reversed(rows)]
            return {"has_data": True, "source": "database", "kline": kline}

        pure_code = ts_code.split(".")[0]
        df = _akshare_retry(
            ak.stock_zh_a_hist,
            symbol=pure_code, period="daily",
            start_date=(datetime.now() - timedelta(days=60)).strftime("%Y%m%d"),
            end_date=datetime.now().strftime("%Y%m%d"), adjust="qfq"
        )
        if df is not None and not df.empty:
            kline = []
            for _, r in df.iterrows():
                kline.append({
                    "date": str(r["日期"]),
                    "close": float(r["收盘"]),
                    "pct_change": float(r["涨跌幅"]) if "涨跌幅" in r else 0,
                })
            return {"has_data": True, "source": "akshare", "kline": kline[-limit:]}

        return {"has_data": False, "message": f"未找到 {ts_code} 的行情数据"}
    except Exception as e:
        return {"has_data": False, "message": f"获取行情失败: {str(e)}"}


def get_factor_ranking(ts_code: str) -> dict:
    """获取因子评分（PE/PB/ROE/动量/波动 + 综合）"""
    try:
        db = SessionLocal()
        row = db.execute(text("""
            SELECT fs.ts_code, si.name, fs.composite_score,
                   fs.factor_pe, fs.factor_pb, fs.factor_roe,
                   fs.factor_momentum, fs.rank_num
            FROM factor_score fs
            JOIN stock_info si ON fs.ts_code = si.ts_code
            WHERE fs.ts_code = :code
            ORDER BY fs.trade_date DESC
            LIMIT 1
        """), {"code": ts_code}).fetchone()
        db.close()

        if not row:
            return {"available": False, "message": "该股票暂无因子评分数据，请先在「因子选股」页面刷新计算"}

        return {
            "available": True,
            "ts_code": row[0], "name": row[1],
            "composite_score": round(float(row[2]), 4) if row[2] else 0,
            "pe": round(float(row[3]), 4) if row[3] else 0,
            "pb": round(float(row[4]), 4) if row[4] else 0,
            "roe": round(float(row[5]), 4) if row[5] else 0,
            "momentum": round(float(row[6]), 4) if row[6] else 0,
            "rank": int(row[7]) if row[7] else 0,
        }
    except Exception as e:
        return {"available": False, "message": f"获取因子数据失败: {str(e)}"}


def get_prediction(ts_code: str) -> dict:
    """获取LSTM趋势预测"""
    try:
        from lstm_model import predict_next
        result = predict_next(ts_code, days=5)
        if "error" in result:
            return {"available": False, "message": result["error"]}
        return {"available": True, "data": result}
    except Exception as e:
        return {"available": False, "message": f"获取预测失败: {str(e)}"}


def get_anomaly_alerts(ts_code: str) -> dict:
    """获取异常检测预警"""
    try:
        from anomaly_detector import get_anomaly_kline
        result = get_anomaly_kline(ts_code)
        if "error" in result:
            return {"available": False, "message": result["error"]}
        anomalies = [a for a in result.get("kline", []) if a.get("is_anomaly")]
        return {"available": True, "anomaly_count": len(anomalies), "anomalies": anomalies[:10]}
    except Exception as e:
        return {"available": False, "message": f"获取异常检测失败: {str(e)}"}


def get_news_sentiment(ts_code: str, days: int = 7) -> dict:
    """获取新闻情感数据"""
    from news_fetcher import get_recent_news, get_sentiment_summary
    summary = get_sentiment_summary(ts_code, days=days)
    news = get_recent_news(ts_code, days=days, limit=10)
    return {"summary": summary, "news": news}


def _akshare_retry(func, *args, **kwargs):
    """AKShare 请求重试（最多5次，间隔递增）"""
    for attempt in range(5):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < 4:
                time.sleep(2 + attempt * 2)
            else:
                raise e


def fetch_and_analyze_stock(ts_code: str) -> dict:
    """采集数据 → 计算因子 → 训练预测 一站式分析"""
    pure_code = ts_code.split(".")[0]
    result = {"ts_code": ts_code, "name": ts_code, "data_fetched": False, "factor": None, "prediction": None}

    # 1. 获取股票名称
    try:
        name_df = _akshare_retry(ak.stock_info_a_code_name)
        if name_df is not None and not name_df.empty:
            match = name_df[name_df["code"] == pure_code]
            if not match.empty:
                result["name"] = match.iloc[0]["name"]
    except Exception:
        pass

    # 2. 尝试采集日线数据并存入DB
    try:
        df = _akshare_retry(
            ak.stock_zh_a_hist,
            symbol=pure_code, period="daily",
            start_date="20230101",
            end_date=datetime.now().strftime("%Y%m%d"), adjust="qfq"
        )
        if df is not None and not df.empty:
            from database import SessionLocal
            from sqlalchemy import text
            db = SessionLocal()
            try:
                exists = db.execute(text("SELECT ts_code FROM stock_info WHERE ts_code=:c"), {"c": ts_code}).fetchone()
                if not exists:
                    industry = STOCK_INDUSTRY_MAP.get(ts_code)
                    db.execute(text("INSERT INTO stock_info (ts_code, name, industry) VALUES (:c, :n, :i)"),
                               {"c": ts_code, "n": result["name"], "i": industry})
                else:
                    industry = STOCK_INDUSTRY_MAP.get(ts_code)
                    if industry:
                        db.execute(text("UPDATE stock_info SET industry = :i WHERE ts_code = :c AND industry IS NULL"),
                                   {"i": industry, "c": ts_code})
                saved = 0
                for _, r in df.iterrows():
                    turnover_val = float(r["换手率"]) if "换手率" in r else 0
                    exists = db.execute(text("SELECT id, turnover FROM stock_daily WHERE ts_code=:c AND trade_date=:d"),
                                        {"c": ts_code, "d": str(r["日期"])}).fetchone()
                    if not exists:
                        db.execute(text("""
                            INSERT INTO stock_daily (ts_code, trade_date, open, high, low, close, vol, amount, turnover, pct_chg)
                            VALUES (:c,:d,:o,:h,:l,:cl,:v,:a,:t,:p)
                        """), {
                            "c": ts_code, "d": str(r["日期"]),
                            "o": float(r["开盘"]), "h": float(r["最高"]),
                            "l": float(r["最低"]), "cl": float(r["收盘"]),
                            "v": float(r["成交量"]) if "成交量" in r else 0,
                            "a": float(r["成交额"]) if "成交额" in r else 0,
                            "t": turnover_val,
                            "p": float(r["涨跌幅"]) if "涨跌幅" in r else 0,
                        })
                        saved += 1
                    elif exists.turnover is None or exists.turnover == 0:
                        db.execute(text("UPDATE stock_daily SET turnover = :t WHERE id = :id"),
                                   {"t": turnover_val, "id": exists.id})
                db.commit()
                result["data_fetched"] = True
                result["records_saved"] = saved
            except Exception:
                db.rollback()
            finally:
                db.close()
    except Exception:
        pass

    # 3. 计算因子（如果数据采集成功）
    if result["data_fetched"]:
        try:
            from factor_engine import calculate_factors, save_factor_scores
            factor_df = calculate_factors()
            if factor_df is not None and not factor_df.empty:
                save_factor_scores(factor_df)
                row = factor_df[factor_df["ts_code"] == ts_code]
                if not row.empty:
                    r = row.iloc[0]
                    def _safe(v, default=0):
                        try:
                            val = float(v)
                            return round(val, 4) if not (val != val) else default  # NaN check
                        except:
                            return default
                    result["factor"] = {
                        "composite_score": _safe(r["composite_score"]),
                        "rank": int(r["rank_num"]) if r["rank_num"] else 0,
                        "momentum": _safe(r["factor_momentum"]),
                        "pe": _safe(r["factor_pe"]),
                        "pb": _safe(r["factor_pb"]),
                        "roe": _safe(r["factor_roe"]),
                    }
        except Exception:
            pass

        # 4. 训练 LSTM 并预测
        try:
            from lstm_model import train_model, predict_next
            train_model(ts_code, epochs=50)
            pred = predict_next(ts_code, days=5)
            if pred.get("success") and pred.get("predictions"):
                pred_list = []
                for p in pred["predictions"]:
                    pred_list.append({"day": p.get("day", 0), "price": round(float(p.get("predicted_price", 0)), 2)})
                result["prediction"] = {"predictions": pred_list}
        except Exception:
            pass

    # 5. 尝试获取行情概览（即使没有存入DB，也尝试获取最近行情）
    if not result["data_fetched"]:
        try:
            kline = get_stock_kline_data(ts_code, limit=5)
            if kline.get("has_data"):
                result["recent_kline"] = kline["kline"]
        except Exception:
            pass

    result["success"] = True
    return result
