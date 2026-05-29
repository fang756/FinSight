"""
FinSight 多因子选股引擎
数据挖掘考点：特征工程、MAD去极值、Z-Score标准化、等权合成
"""
import pandas as pd
import numpy as np
from sqlalchemy import text
from database import engine, SessionLocal, FactorScore
from config import FACTOR_MAD_SCALE, FACTOR_CLIP_SIGMA


def _mad_clip(series: pd.Series, scale=FACTOR_MAD_SCALE, n_sigmas=FACTOR_CLIP_SIGMA) -> pd.Series:
    """
    MAD法去极值
    原理：中位数绝对偏差(MAD)比标准差更鲁棒，不受极端值影响
    超过 n_sigmas * MAD 的值被截断到边界
    """
    median = series.median()
    mad = (series - median).abs().median() * scale
    if mad == 0:
        return series
    lower = median - n_sigmas * mad
    upper = median + n_sigmas * mad
    return series.clip(lower, upper)


def _zscore(series: pd.Series) -> pd.Series:
    """Z-Score标准化"""
    std = series.std()
    if std == 0:
        return pd.Series(0, index=series.index)
    return (series - series.mean()) / std


def calculate_factors(trade_date: str = None) -> pd.DataFrame:
    """
    计算多因子评分

    五大因子维度：
    1. 价值因子(factor_pe)：低PE = 价值型，得分高（用换手率代理）
    2. 成长因子(factor_pb)：高营收增速 = 成长型（用短期动量代理）
    3. 质量因子(factor_roe)：高ROE = 高质量（用低波动代理）
    4. 动量因子(factor_momentum)：过去N日收益率高 = 动量强
    5. 波动因子(factor_vol)：低波动率 = 稳健，得分高

    处理流程：原始因子 → MAD去极值 → Z-Score标准化 → 等权加总
    """
    session = SessionLocal()
    try:
        if not trade_date:
            result = session.execute(text(
                "SELECT MAX(trade_date) FROM stock_daily"
            )).scalar()
            trade_date = str(result)

        df = pd.read_sql(text("""
            SELECT d.ts_code, s.name, s.industry,
                   d.trade_date, d.close, d.vol, d.amount,
                   d.turnover, d.pct_chg, d.high, d.low
            FROM stock_daily d
            LEFT JOIN stock_info s ON d.ts_code = s.ts_code
            WHERE d.trade_date <= :trade_date
            ORDER BY d.ts_code, d.trade_date
        """), engine, params={"trade_date": trade_date})
    finally:
        session.close()

    if df.empty:
        return pd.DataFrame()

    # ============ 因子计算 ============
    latest_date = df["trade_date"].max()

    # 1. 动量因子：过去20日和5日收益率
    momentum_list = []
    for code, group in df.groupby("ts_code"):
        group = group.sort_values("trade_date")
        if len(group) < 2:  # 至少2天才能算收益率
            continue
        latest = group.iloc[-1]
        if len(group) >= 20:
            ret_20 = (latest["close"] - group.iloc[-20]["close"]) / group.iloc[-20]["close"]
        elif len(group) >= 5:
            ret_20 = (latest["close"] - group.iloc[-5]["close"]) / group.iloc[-5]["close"]
        else:
            ret_20 = (latest["close"] - group.iloc[0]["close"]) / group.iloc[0]["close"]
        ret_5 = (latest["close"] - group.iloc[-min(5, len(group))]["close"]) / group.iloc[-min(5, len(group))]["close"]
        momentum_list.append({
            "ts_code": code,
            "name": latest.get("name", ""),
            "industry": latest.get("industry", ""),
            "trade_date": latest_date,
            "close": latest["close"],
            "momentum_20": ret_20,
            "momentum_5": ret_5,
        })

    if not momentum_list:
        return pd.DataFrame()

    result_df = pd.DataFrame(momentum_list)

    # 2. 波动因子：过去20日收益率标准差
    volatility_list = []
    for code, group in df.groupby("ts_code"):
        group = group.sort_values("trade_date")
        if len(group) >= 20:
            vol = group.tail(20)["pct_chg"].std()
        elif len(group) >= 2:
            vol = group["pct_chg"].std()
        else:
            vol = np.nan
        volatility_list.append({"ts_code": code, "volatility": vol})

    vol_df = pd.DataFrame(volatility_list)
    result_df = result_df.merge(vol_df, on="ts_code", how="left")

    # 3. 换手率因子（流动性代理）
    turnover_list = []
    for code, group in df.groupby("ts_code"):
        group = group.sort_values("trade_date")
        if len(group) >= 5:
            avg_turnover = group.tail(5)["turnover"].mean()
        elif len(group) >= 1:
            avg_turnover = group["turnover"].mean()
        else:
            avg_turnover = np.nan
        turnover_list.append({"ts_code": code, "avg_turnover": avg_turnover})

    turn_df = pd.DataFrame(turnover_list)
    result_df = result_df.merge(turn_df, on="ts_code", how="left")

    # ============ 因子预处理 ============
    factor_cols = {
        "momentum_5": True,
        "momentum_20": True,
        "volatility": False,     # 越小越好，需反向
        "avg_turnover": True,
    }

    for col, higher_is_better in factor_cols.items():
        result_df[col] = _mad_clip(result_df[col].dropna().reindex(result_df.index))
        result_df[col + "_z"] = _zscore(result_df[col])
        if not higher_is_better:
            result_df[col + "_z"] = -result_df[col + "_z"]

    # ============ 因子合成（等权） ============
    z_cols = [c + "_z" for c in factor_cols.keys()]
    result_df["composite_score"] = result_df[z_cols].mean(axis=1)

    # 映射到5维因子展示
    result_df["factor_pe"] = result_df["avg_turnover_z"]         # 价值/流动性
    result_df["factor_pb"] = result_df["momentum_5_z"]           # 成长/短期动量
    result_df["factor_roe"] = -result_df["volatility_z"]         # 质量/低波动
    result_df["factor_momentum"] = result_df["momentum_20_z"]    # 动量
    result_df["factor_vol"] = -result_df["volatility_z"]         # 波动因子

    # 排名
    result_df = result_df.sort_values("composite_score", ascending=False)
    result_df = result_df.reset_index(drop=True)
    result_df["rank_num"] = range(1, len(result_df) + 1)

    return result_df


def save_factor_scores(df: pd.DataFrame):
    """将因子评分保存到数据库"""
    session = SessionLocal()
    try:
        for _, row in df.iterrows():
            def _v(v):
                try:
                    val = float(v)
                    return None if (val != val) else val  # NaN → None
                except:
                    return None
            existing = session.query(FactorScore).filter_by(
                ts_code=row["ts_code"],
                trade_date=row["trade_date"]
            ).first()
            if existing:
                existing.factor_pe = _v(row.get("factor_pe"))
                existing.factor_pb = _v(row.get("factor_pb"))
                existing.factor_roe = _v(row.get("factor_roe"))
                existing.factor_momentum = _v(row.get("factor_momentum"))
                existing.factor_vol = _v(row.get("factor_vol"))
                existing.composite_score = _v(row.get("composite_score"))
                existing.rank_num = int(row.get("rank_num")) if row.get("rank_num") else None
            else:
                session.add(FactorScore(
                    ts_code=row["ts_code"],
                    trade_date=row["trade_date"],
                    factor_pe=_v(row.get("factor_pe")),
                    factor_pb=_v(row.get("factor_pb")),
                    factor_roe=_v(row.get("factor_roe")),
                    factor_momentum=_v(row.get("factor_momentum")),
                    factor_vol=_v(row.get("factor_vol")),
                    composite_score=_v(row.get("composite_score")),
                    rank_num=int(row.get("rank_num")) if row.get("rank_num") else None,
                ))
        session.commit()
        print(f"  [+] Factor scores saved ({len(df)} records)")
    except Exception as e:
        session.rollback()
        print(f"  [!] 因子评分保存失败: {e}")
    finally:
        session.close()


def _nan_to_none(val):
    """将 NaN 转为 None（JSON 安全）"""
    try:
        return None if (val != val) else val
    except:
        return val


def get_factor_ranking(industry: str = None, top_n: int = 20) -> list:
    """获取因子排名"""
    df = calculate_factors()
    if df.empty:
        return []

    if industry:
        df = df[df["industry"] == industry]

    df = df.head(top_n)
    records = df[["ts_code", "name", "industry", "composite_score",
                   "factor_pe", "factor_pb", "factor_roe",
                   "factor_momentum", "factor_vol", "rank_num"]].to_dict(orient="records")

    for rec in records:
        for k, v in rec.items():
            rec[k] = _nan_to_none(v)

    return records


def get_factor_radar(ts_code: str) -> dict:
    """获取单只股票的因子雷达数据"""
    df = calculate_factors()
    if df.empty:
        return {}

    row = df[df["ts_code"] == ts_code]
    if row.empty:
        return {}

    r = row.iloc[0]
    return {
        "ts_code": r["ts_code"],
        "name": r.get("name", ""),
        "factors": {
            "价值": round(float(r["factor_pe"]) if pd.notna(r["factor_pe"]) else 0, 4),
            "成长": round(float(r["factor_pb"]) if pd.notna(r["factor_pb"]) else 0, 4),
            "质量": round(float(r["factor_roe"]) if pd.notna(r["factor_roe"]) else 0, 4),
            "动量": round(float(r["factor_momentum"]) if pd.notna(r["factor_momentum"]) else 0, 4),
            "波动": round(float(r["factor_vol"]) if pd.notna(r["factor_vol"]) else 0, 4),
        },
        "composite_score": round(float(r["composite_score"]), 4),
    }
