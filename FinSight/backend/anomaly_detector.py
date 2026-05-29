"""
FinSight 异常交易检测引擎
数据挖掘考点：Isolation Forest(异常检测) + K-Means(聚类) + 统计分析
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import text
from database import SessionLocal, AnomalyResult, engine
from config import ANOMALY_CONTAMINATION, KMEANS_N_CLUSTERS


def detect_anomalies(start_date: str = None, end_date: str = None) -> dict:
    """
    执行异常交易检测

    检测维度：换手率、涨跌幅、成交量比(相对前5日均量)
    方法：
      1. Isolation Forest — 无监督异常检测
      2. K-Means — 将交易模式聚类，远离聚类中心的标记为疑似异常
      3. 综合判定 — 两种方法都标记为异常的为高置信异常
    """
    query = """
        SELECT d.ts_code, s.name, d.trade_date,
               d.close, d.vol, d.turnover, d.pct_chg,
               d.high, d.low
        FROM stock_daily d
        LEFT JOIN stock_info s ON d.ts_code = s.ts_code
        WHERE 1=1
    """
    params = {}
    if start_date:
        query += " AND d.trade_date >= :start_date"
        params["start_date"] = start_date
    if end_date:
        query += " AND d.trade_date <= :end_date"
        params["end_date"] = end_date

    query += " ORDER BY d.trade_date DESC LIMIT 5000"

    df = pd.read_sql(text(query), engine, params=params)

    if len(df) < 100:
        return {"total": 0, "anomaly_count": 0, "anomalies": [],
                "message": "数据量不足，至少需要100条记录"}

    # ============ 特征工程 ============
    df = df.sort_values(["ts_code", "trade_date"])
    df["vol_ma5"] = df.groupby("ts_code")["vol"].transform(
        lambda x: x.rolling(5, min_periods=1).mean()
    )
    df["volume_ratio"] = df["vol"] / df["vol_ma5"].replace(0, np.nan)
    df["volume_ratio"] = df["volume_ratio"].fillna(1.0)

    # 振幅
    df["amplitude"] = (df["high"] - df["low"]) / df["close"].replace(0, np.nan)
    df["amplitude"] = df["amplitude"].fillna(0)

    feature_cols = ["turnover", "pct_chg", "volume_ratio", "amplitude"]
    df_clean = df.dropna(subset=feature_cols).copy()

    if len(df_clean) < 50:
        return {"total": 0, "anomaly_count": 0, "anomalies": [],
                "message": "有效数据不足"}

    X = df_clean[feature_cols].values.astype(float)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # ============ 方法1: Isolation Forest ============
    iso_forest = IsolationForest(
        contamination=ANOMALY_CONTAMINATION,
        random_state=42,
        n_estimators=100
    )
    iso_labels = iso_forest.fit_predict(X_scaled)
    iso_anomaly = iso_labels == -1
    iso_scores = iso_forest.decision_function(X_scaled)
    df_clean["anomaly_score"] = -iso_scores
    df_clean["iso_anomaly"] = iso_anomaly

    # ============ 方法2: K-Means 聚类 ============
    kmeans = KMeans(n_clusters=KMEANS_N_CLUSTERS, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(X_scaled)
    df_clean["cluster_label"] = cluster_labels

    distances = []
    for i, label in enumerate(cluster_labels):
        center = kmeans.cluster_centers_[label]
        dist = np.linalg.norm(X_scaled[i] - center)
        distances.append(dist)
    df_clean["cluster_distance"] = distances

    dist_threshold = np.percentile(distances, 95)
    df_clean["kmeans_anomaly"] = df_clean["cluster_distance"] > dist_threshold

    # ============ 综合判定 ============
    df_clean["is_anomaly"] = df_clean["iso_anomaly"] & df_clean["kmeans_anomaly"]

    df_clean["method"] = "normal"
    df_clean.loc[df_clean["iso_anomaly"] & ~df_clean["kmeans_anomaly"],
                 "method"] = "isolation_forest"
    df_clean.loc[~df_clean["iso_anomaly"] & df_clean["kmeans_anomaly"],
                 "method"] = "kmeans"
    df_clean.loc[df_clean["is_anomaly"], "method"] = "combined"

    type_mapping = {
        "combined": "疑似操纵",
        "isolation_forest": "异常波动",
        "kmeans": "异常模式",
        "normal": "正常",
    }
    df_clean["anomaly_type_cn"] = df_clean["method"].map(type_mapping)

    # ============ 保存到数据库 ============
    anomaly_records = df_clean[df_clean["method"] != "normal"]
    session = SessionLocal()
    try:
        for _, row in anomaly_records.iterrows():
            existing = session.query(AnomalyResult).filter_by(
                ts_code=row["ts_code"],
                trade_date=row["trade_date"]
            ).first()
            detail = {
                "turnover": float(row["turnover"]) if pd.notna(row["turnover"]) else None,
                "pct_chg": float(row["pct_chg"]) if pd.notna(row["pct_chg"]) else None,
                "volume_ratio": round(float(row["volume_ratio"]), 4),
                "amplitude": round(float(row["amplitude"]), 4),
                "close": float(row["close"]) if pd.notna(row["close"]) else None,
            }
            if existing:
                existing.anomaly_score = row["anomaly_score"]
                existing.cluster_label = row["cluster_label"]
                existing.is_anomaly = bool(row["is_anomaly"])
                existing.method = row["method"]
                existing.detail = detail
            else:
                session.add(AnomalyResult(
                    ts_code=row["ts_code"],
                    trade_date=row["trade_date"],
                    anomaly_score=round(float(row["anomaly_score"]), 4),
                    cluster_label=int(row["cluster_label"]),
                    is_anomaly=bool(row["is_anomaly"]),
                    method=row["method"],
                    detail=detail,
                ))
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"  [!] 异常结果保存失败: {e}")
    finally:
        session.close()

    # ============ 返回结果 ============
    anomaly_list = df_clean[df_clean["method"] != "normal"].sort_values(
        "anomaly_score", ascending=False
    ).head(50)

    anomalies = []
    for _, row in anomaly_list.iterrows():
        anomalies.append({
            "ts_code": row["ts_code"],
            "name": row.get("name", ""),
            "trade_date": str(row["trade_date"]),
            "close": float(row["close"]) if pd.notna(row["close"]) else None,
            "pct_chg": round(float(row["pct_chg"]), 2) if pd.notna(row["pct_chg"]) else None,
            "turnover": round(float(row["turnover"]), 2) if pd.notna(row["turnover"]) else None,
            "volume_ratio": round(float(row["volume_ratio"]), 2),
            "anomaly_score": round(float(row["anomaly_score"]), 4),
            "cluster_label": int(row["cluster_label"]),
            "is_anomaly": bool(row["is_anomaly"]),
            "method": row["method"],
            "anomaly_type": row["anomaly_type_cn"],
        })

    scatter_data = []
    sample = df_clean.sample(min(500, len(df_clean)), random_state=42)
    for _, row in sample.iterrows():
        scatter_data.append({
            "ts_code": row["ts_code"],
            "turnover": float(row["turnover"]) if pd.notna(row["turnover"]) else 0,
            "pct_chg": float(row["pct_chg"]) if pd.notna(row["pct_chg"]) else 0,
            "volume_ratio": round(float(row["volume_ratio"]), 2),
            "anomaly_score": round(float(row["anomaly_score"]), 4),
            "is_anomaly": bool(row.get("is_anomaly", False)),
            "cluster_label": int(row["cluster_label"]),
        })

    return {
        "total": len(df_clean),
        "anomaly_count": len(anomaly_list),
        "anomalies": anomalies,
        "scatter_data": scatter_data,
        "methods": {
            "isolation_forest": {
                "contamination": ANOMALY_CONTAMINATION,
                "description": "基于随机分割，异常点更容易被孤立"
            },
            "kmeans": {
                "n_clusters": KMEANS_N_CLUSTERS,
                "distance_threshold": round(float(dist_threshold), 4),
                "description": "远离聚类中心的点为异常"
            }
        }
    }


def get_anomaly_alerts() -> list:
    """获取异常预警列表"""
    session = SessionLocal()
    try:
        results = session.query(AnomalyResult).filter(
            AnomalyResult.is_anomaly == True
        ).order_by(AnomalyResult.anomaly_score.desc()).limit(20).all()

        alerts = []
        for r in results:
            alerts.append({
                "ts_code": r.ts_code,
                "trade_date": str(r.trade_date),
                "anomaly_score": float(r.anomaly_score) if r.anomaly_score else None,
                "method": r.method,
                "detail": r.detail,
            })
        return alerts
    finally:
        session.close()


def get_anomaly_kline(ts_code: str) -> dict:
    """获取带异常标注的K线数据"""
    df = pd.read_sql(text("""
        SELECT trade_date, open, close, high, low, vol, pct_chg
        FROM stock_daily
        WHERE ts_code = :code
        ORDER BY trade_date ASC
    """), engine, params={"code": ts_code})

    session = SessionLocal()
    try:
        anomalies = session.query(AnomalyResult).filter(
            AnomalyResult.ts_code == ts_code,
            AnomalyResult.is_anomaly == True
        ).all()
        anomaly_dates = {str(a.trade_date) for a in anomalies}
    finally:
        session.close()

    kline = []
    for _, row in df.iterrows():
        kline.append({
            "date": str(row["trade_date"]),
            "open": float(row["open"]) if pd.notna(row["open"]) else None,
            "close": float(row["close"]) if pd.notna(row["close"]) else None,
            "high": float(row["high"]) if pd.notna(row["high"]) else None,
            "low": float(row["low"]) if pd.notna(row["low"]) else None,
            "volume": float(row["vol"]) if pd.notna(row["vol"]) else None,
            "is_anomaly": str(row["trade_date"]) in anomaly_dates,
        })

    return {
        "ts_code": ts_code,
        "kline": kline,
        "anomaly_count": len(anomaly_dates),
    }
