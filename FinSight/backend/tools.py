"""
FinSight 股小查工具集
使用 BaoStock 搜索股票 + 获取行情（更稳定）
"""
import time
import baostock as bs
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from database import SessionLocal
from config import STOCK_INDUSTRY_MAP


def _to_bs_code(ts_code: str) -> str:
    code = ts_code.split(".")[0]
    market = ts_code.split(".")[1].lower()
    return f"{market}.{code}"


def _from_bs_code(bs_code: str) -> str:
    parts = bs_code.split(".")
    market = parts[0].upper()
    code = parts[1]
    return f"{code}.{market}"


def _bs_login():
    lg = bs.login()
    if lg.error_code != "0":
        raise Exception(f"BaoStock login failed: {lg.error_msg}")


def search_stock(keyword: str) -> dict:
    """搜索A股股票代码和名称（使用 BaoStock）"""
    try:
        _bs_login()
        # query_all_stock 需要交易日，尝试今天→昨天→最近可用日期
        today = datetime.now()
        for delta in range(10):
            day = (today - timedelta(days=delta)).strftime("%Y-%m-%d")
            rs = bs.query_all_stock(day=day)
            df = rs.get_data()
            if df is not None and len(df) > 100:
                break
        bs.logout()

        if df.empty:
            return {"found": False, "message": "无法获取股票列表"}

        # 过滤掉指数、退市等非交易品种（code 以 b. 开头的是指数）
        df = df[~df["code"].str.startswith("b.")]
        df["ts_code"] = df["code"].apply(_from_bs_code)
        df["code_num"] = df["code"].str.split(".").str[1]

        result = df[
            df["code_name"].str.contains(keyword, na=False) |
            df["code_num"].str.contains(keyword, na=False)
        ]

        if result.empty:
            return {"found": False, "message": f"未找到匹配「{keyword}」的股票"}

        stocks = []
        for _, row in result.head(5).iterrows():
            stocks.append({"ts_code": row["ts_code"], "name": row["code_name"], "code": row["code_num"]})

        return {"found": True, "stocks": stocks}
    except Exception as e:
        return {"found": False, "message": f"搜索失败: {str(e)}"}


def get_stock_kline_data(ts_code: str, limit: int = 30) -> dict:
    """获取K线行情（优先查DB，查不到从 BaoStock 实时拉）"""
    try:
        # 1. 查数据库
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

        # 2. 从 BaoStock 实时拉取
        bs_code = _to_bs_code(ts_code)
        _bs_login()
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        rs = bs.query_history_k_data_plus(
            bs_code, "date,close,pctChg",
            start_date=start, end_date=end,
            frequency="d", adjustflag="3",
        )
        df = rs.get_data()
        bs.logout()

        if df is not None and not df.empty:
            df = df[df["pctChg"] != ""].copy()
            kline = []
            for _, r in df.iterrows():
                kline.append({
                    "date": str(r["date"]),
                    "close": float(r["close"]) if r["close"] else 0,
                    "pct_change": float(r["pctChg"]) if r["pctChg"] else 0,
                })
            return {"has_data": True, "source": "baostock", "kline": kline[-limit:]}

        return {"has_data": False, "message": f"未找到 {ts_code} 的行情数据"}
    except Exception as e:
        try:
            bs.logout()
        except Exception:
            pass
        return {"has_data": False, "message": f"获取行情失败: {str(e)}"}


def get_factor_ranking(ts_code: str) -> dict:
    """获取因子评分"""
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
            return {"available": False, "message": "暂无因子评分数据，请先在「因子选股」页面刷新计算"}

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
    """获取新闻情感数据（AKShare 实时拉取）"""
    from news_fetcher import get_recent_news, get_sentiment_summary, fetch_news, analyze_sentiment
    from database import SessionLocal, NewsSentiment

    try:
        df = fetch_news(ts_code)
        if not df.empty:
            session = SessionLocal()
            try:
                col_title = "新闻标题" if "新闻标题" in df.columns else (df.columns[1] if len(df.columns) > 1 else None)
                col_content = "新闻内容" if "新闻内容" in df.columns else (df.columns[2] if len(df.columns) > 2 else None)
                col_date = "发布时间" if "发布时间" in df.columns else (df.columns[3] if len(df.columns) > 3 else None)
                col_source = "文章来源" if "文章来源" in df.columns else (df.columns[4] if len(df.columns) > 4 else None)
                new_count = 0
                for _, row in df.iterrows():
                    title = row.get(col_title) if col_title else ""
                    if not title:
                        continue
                    existing = session.query(NewsSentiment).filter(
                        NewsSentiment.ts_code == ts_code,
                        NewsSentiment.title == title
                    ).first()
                    if existing:
                        continue
                    content = row.get(col_content) or title
                    pub_date = row.get(col_date, datetime.now())
                    source = row.get(col_source, "")
                    score, label = analyze_sentiment(title)
                    session.add(NewsSentiment(
                        ts_code=ts_code, pub_date=pub_date, title=title,
                        content=str(content)[:5000], sentiment_score=score,
                        sentiment_label=label, source=str(source)[:100],
                    ))
                    new_count += 1
                if new_count > 0:
                    session.commit()
            except Exception:
                session.rollback()
            finally:
                session.close()
    except Exception:
        pass

    summary = get_sentiment_summary(ts_code, days=days)
    news = get_recent_news(ts_code, days=days, limit=10)
    return {"summary": summary, "news": news}


def fetch_and_analyze_stock(ts_code: str) -> dict:
    """采集数据 → 计算因子 → 训练预测 一站式分析（使用 BaoStock）"""
    result = {"ts_code": ts_code, "name": ts_code, "data_fetched": False, "factor": None, "prediction": None}
    pure_code = ts_code.split(".")[0]

    # 1. 获取股票名称
    try:
        _bs_login()
        rs = bs.query_stock_basic(_to_bs_code(ts_code))
        if rs and rs.error_code == "0":
            info = rs.get_data()
            if not info.empty:
                result["name"] = info.iloc[0]["code_name"]
        bs.logout()
    except Exception:
        try:
            bs.logout()
        except Exception:
            pass

    # 2. 采集日线数据并存入DB
    try:
        _bs_login()
        end = datetime.now().strftime("%Y-%m-%d")
        rs = bs.query_history_k_data_plus(
            _to_bs_code(ts_code),
            "date,open,high,low,close,volume,amount,turn,pctChg",
            start_date="2023-01-01", end_date=end,
            frequency="d", adjustflag="3",
        )
        df = rs.get_data()
        bs.logout()

        if df is not None and not df.empty:
            df = df[df["pctChg"] != ""].copy()
            db = SessionLocal()
            try:
                exists = db.execute(text("SELECT ts_code FROM stock_info WHERE ts_code=:c"), {"c": ts_code}).fetchone()
                if not exists:
                    industry = STOCK_INDUSTRY_MAP.get(ts_code)
                    db.execute(text("INSERT INTO stock_info (ts_code, name, industry) VALUES (:c, :n, :i)"),
                               {"c": ts_code, "n": result["name"], "i": industry})

                saved = 0
                for _, r in df.iterrows():
                    trade_date = str(r["date"]).replace("-", "")
                    exists = db.execute(text("SELECT id FROM stock_daily WHERE ts_code=:c AND trade_date=:d"),
                                        {"c": ts_code, "d": trade_date}).fetchone()
                    if not exists:
                        db.execute(text("""
                            INSERT INTO stock_daily (ts_code, trade_date, open, high, low, close, vol, amount, turnover, pct_chg)
                            VALUES (:c,:d,:o,:h,:l,:cl,:v,:a,:t,:p)
                        """), {
                            "c": ts_code, "d": trade_date,
                            "o": float(r["open"]) if r["open"] else 0,
                            "h": float(r["high"]) if r["high"] else 0,
                            "l": float(r["low"]) if r["low"] else 0,
                            "cl": float(r["close"]) if r["close"] else 0,
                            "v": float(r["volume"]) if r["volume"] else 0,
                            "a": float(r["amount"]) if r["amount"] else 0,
                            "t": float(r["turn"]) if r["turn"] else 0,
                            "p": float(r["pctChg"]) if r["pctChg"] else 0,
                        })
                        saved += 1
                db.commit()
                result["data_fetched"] = True
                result["records_saved"] = saved
            except Exception:
                db.rollback()
            finally:
                db.close()
    except Exception:
        try:
            bs.logout()
        except Exception:
            pass

    # 3. 计算因子 + 4. 训练预测
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
                            return round(val, 4) if not (val != val) else default
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

        try:
            from lstm_model import train_model, predict_next
            train_model(ts_code, epochs=50)
            pred = predict_next(ts_code, days=5)
            if pred.get("success") and pred.get("predictions"):
                result["prediction"] = {
                    "predictions": [{"day": p.get("day", 0), "price": round(float(p.get("predicted_price", 0)), 2)} for p in pred["predictions"]]
                }
        except Exception:
            pass

    if not result["data_fetched"]:
        try:
            kline = get_stock_kline_data(ts_code, limit=5)
            if kline.get("has_data"):
                result["recent_kline"] = kline["kline"]
        except Exception:
            pass

    result["success"] = True
    return result
