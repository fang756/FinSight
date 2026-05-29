"""
FinSight 新闻舆情采集 + SnowNLP 情感分析
"""
import time
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from snownlp import SnowNLP
from database import SessionLocal, NewsSentiment


def analyze_sentiment(text: str) -> tuple:
    """
    SnowNLP 情感分析
    返回 (score, label)
    score: 0-1, >0.6 正面, <0.4 负面, 其余中性
    """
    try:
        s = SnowNLP(text)
        score = s.sentiments
        if score > 0.6:
            label = "正面"
        elif score < 0.4:
            label = "负面"
        else:
            label = "中性"
        return round(score, 4), label
    except Exception:
        return 0.5, "中性"


def fetch_news(code: str) -> pd.DataFrame:
    """从 AKShare 获取股票最新新闻（最多100条）"""
    pure_code = code.split(".")[0]
    try:
        df = ak.stock_news_em(symbol=pure_code)
        if df.empty:
            return pd.DataFrame()
        col_title = "新闻标题" if "新闻标题" in df.columns else (df.columns[1] if len(df.columns) > 1 else None)
        if col_title:
            df = df.drop_duplicates(subset=[col_title])
        return df
    except Exception as e:
        print(f"  [!] 新闻获取失败: {e}")
        return pd.DataFrame()


def save_news_to_db(ts_code: str, stock_name: str = "") -> int:
    """
    采集新闻 + 情感分析 + 入库
    返回新增条数
    """
    print(f"[舆情] 开始采集 {ts_code} {stock_name} 的新闻...")
    df = fetch_news(ts_code)

    if df.empty:
        print(f"  [!] 未获取到新闻")
        return 0

    print(f"  [*] 获取到 {len(df)} 条新闻，开始情感分析...")

    # 动态映射列名（AKShare版本不同列名可能不同）
    col_title = "新闻标题" if "新闻标题" in df.columns else (df.columns[1] if len(df.columns) > 1 else None)
    col_content = "新闻内容" if "新闻内容" in df.columns else (df.columns[2] if len(df.columns) > 2 else None)
    col_date = "发布时间" if "发布时间" in df.columns else (df.columns[3] if len(df.columns) > 3 else None)
    col_source = "文章来源" if "文章来源" in df.columns else (df.columns[4] if len(df.columns) > 4 else None)

    session = SessionLocal()
    saved = 0
    try:
        for _, row in df.iterrows():
            title = row.get(col_title) if col_title else ""
            content = row.get(col_content) or title
            pub_date = row.get(col_date, datetime.now())
            source = row.get(col_source, "")

            if not title:
                continue

            # 检查是否已存在（按标题去重）
            existing = session.query(NewsSentiment).filter(
                NewsSentiment.ts_code == ts_code,
                NewsSentiment.title == title
            ).first()
            if existing:
                continue

            score, label = analyze_sentiment(title)

            session.add(NewsSentiment(
                ts_code=ts_code,
                pub_date=pub_date,
                title=title,
                content=str(content)[:5000],
                sentiment_score=score,
                sentiment_label=label,
                source=str(source)[:100],
            ))
            saved += 1

        session.commit()
        print(f"  [+] 新增 {saved} 条新闻情感数据")
    except Exception as e:
        session.rollback()
        print(f"  [!] 入库失败: {e}")
    finally:
        session.close()

    return saved


def get_recent_news(ts_code: str, days: int = 7, limit: int = 20) -> list:
    """查询近期新闻情感数据"""
    session = SessionLocal()
    try:
        since = datetime.now() - timedelta(days=days)
        rows = session.query(NewsSentiment).filter(
            NewsSentiment.ts_code == ts_code,
            NewsSentiment.pub_date >= since
        ).order_by(NewsSentiment.pub_date.desc()).limit(limit).all()

        results = []
        for r in rows:
            results.append({
                "title": r.title,
                "pub_date": r.pub_date.strftime("%Y-%m-%d %H:%M") if r.pub_date else "",
                "sentiment_score": float(r.sentiment_score) if r.sentiment_score else 0.5,
                "sentiment_label": r.sentiment_label or "中性",
                "source": r.source or "",
            })
        return results
    finally:
        session.close()


def get_sentiment_summary(ts_code: str, days: int = 7) -> dict:
    """获取情感统计摘要"""
    session = SessionLocal()
    try:
        since = datetime.now() - timedelta(days=days)
        rows = session.query(NewsSentiment).filter(
            NewsSentiment.ts_code == ts_code,
            NewsSentiment.pub_date >= since
        ).all()

        total = len(rows)
        if total == 0:
            return {"total": 0, "positive": 0, "negative": 0, "neutral": 0, "avg_score": 0.5}

        positive = sum(1 for r in rows if r.sentiment_label == "正面")
        negative = sum(1 for r in rows if r.sentiment_label == "负面")
        neutral = sum(1 for r in rows if r.sentiment_label == "中性")
        avg_score = sum(float(r.sentiment_score) for r in rows if r.sentiment_score) / total

        return {
            "total": total,
            "positive": positive,
            "negative": negative,
            "neutral": neutral,
            "avg_score": round(avg_score, 4),
        }
    finally:
        session.close()
