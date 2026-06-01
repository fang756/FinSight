"""
FinSight 数据采集脚本
使用 BaoStock 采集A股数据并入库（更稳定）
"""
import time
import baostock as bs
import pandas as pd
from datetime import date, timedelta
from sqlalchemy import text
from database import engine, SessionLocal, StockInfo, StockDaily
from config import STOCK_COUNT, DATA_START_DATE, STOCK_INDUSTRY_MAP


def _to_bs_code(ts_code: str) -> str:
    """转换 ts_code (600519.SH) 为 BaoStock 格式 (sh.600519)"""
    code = ts_code.split(".")[0]
    market = ts_code.split(".")[1].lower()
    return f"{market}.{code}"


def _from_bs_code(bs_code: str) -> str:
    """转换 BaoStock 格式 (sh.600519) 为 ts_code (600519.SH)"""
    parts = bs_code.split(".")
    market = parts[0].upper()
    code = parts[1]
    return f"{code}.{market}"


def _bs_login():
    """BaoStock 登录（可重复调用）"""
    lg = bs.login()
    if lg.error_code != "0":
        raise Exception(f"BaoStock login failed: {lg.error_msg}")


def fetch_stock_list(count: int = STOCK_COUNT) -> pd.DataFrame:
    """获取股票列表（沪深300成分股前N只）"""
    print(f"[数据采集] 获取沪深300成分股...")
    try:
        _bs_login()
        rs = bs.query_hs300_stocks()
        df = rs.get_data()
        bs.logout()
        if df.empty:
            raise Exception("empty result")
        df = df.head(count)
        df["ts_code"] = df["code"].apply(_from_bs_code)
        df = df.rename(columns={"code_name": "name"})
        print(f"[数据采集] 获取到 {len(df)} 只股票")
        return df[["ts_code", "name"]]
    except Exception as e:
        print(f"[数据采集] 获取股票列表失败: {e}，使用内置列表")
        try:
            bs.logout()
        except Exception:
            pass
        fallback = [
            ("000001.SZ", "平安银行"), ("000002.SZ", "万科A"), ("000063.SZ", "中兴通讯"),
            ("000333.SZ", "美的集团"), ("000338.SZ", "潍柴动力"), ("000425.SZ", "徐工机械"),
            ("000568.SZ", "泸州老窖"), ("000625.SZ", "长安汽车"), ("000651.SZ", "格力电器"),
            ("000858.SZ", "五粮液"), ("000895.SZ", "双汇发展"), ("000938.SZ", "紫光股份"),
            ("001979.SZ", "招商蛇口"), ("002001.SZ", "新和成"), ("002007.SZ", "华兰生物"),
            ("002024.SZ", "苏宁易购"), ("002027.SZ", "分众传媒"), ("002049.SZ", "紫光国微"),
            ("002120.SZ", "韵达股份"), ("002142.SZ", "宁波银行"), ("002230.SZ", "科大讯飞"),
            ("002241.SZ", "歌尔股份"), ("002304.SZ", "洋河股份"), ("002352.SZ", "顺丰控股"),
            ("002415.SZ", "海康威视"), ("002460.SZ", "赣锋锂业"), ("002475.SZ", "立讯精密"),
            ("002493.SZ", "荣盛石化"), ("002555.SZ", "三七互娱"), ("002594.SZ", "比亚迪"),
            ("002601.SZ", "龙蟒佰利"), ("002607.SZ", "中公教育"), ("002709.SZ", "天赐材料"),
            ("002714.SZ", "牧原股份"), ("002736.SZ", "国信证券"), ("002812.SZ", "恩捷股份"),
            ("002841.SZ", "视源股份"), ("003816.SZ", "中国广核"), ("600000.SH", "浦发银行"),
            ("600009.SH", "上海机场"), ("600010.SH", "包钢股份"), ("600011.SH", "华能国际"),
            ("600016.SH", "民生银行"), ("600019.SH", "宝钢股份"), ("600025.SH", "华能水电"),
            ("600028.SH", "中国石化"), ("600029.SH", "南方航空"), ("600030.SH", "中信证券"),
            ("600031.SH", "三一重工"), ("600036.SH", "招商银行"),
        ]
        return pd.DataFrame(fallback[:count], columns=["ts_code", "name"])


def fetch_stock_daily(code: str, start_date: str, end_date: str, max_retries: int = 3) -> pd.DataFrame:
    """使用 BaoStock 获取单只股票日K线数据"""
    bs_code = _to_bs_code(code)
    for attempt in range(max_retries):
        try:
            _bs_login()
            fields = "date,code,open,high,low,close,volume,amount,turn,pctChg"
            rs = bs.query_history_k_data_plus(
                bs_code, fields,
                start_date=start_date,
                end_date=end_date,
                frequency="d",
                adjustflag="3",  # 前复权
            )
            df = rs.get_data()
            bs.logout()
            if df.empty:
                return pd.DataFrame()

            df = df.rename(columns={
                "date": "trade_date",
                "open": "open", "high": "high",
                "low": "low", "close": "close",
                "volume": "vol", "amount": "amount",
                "turn": "turnover", "pctChg": "pct_chg",
            })
            df["ts_code"] = code
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
            # 过滤停牌日（涨跌幅为空的）
            df = df[df["pct_chg"] != ""].copy()
            for col in ["open", "high", "low", "close", "vol", "amount", "turnover", "pct_chg"]:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            cols = ["ts_code", "trade_date", "open", "close", "high",
                    "low", "vol", "amount", "turnover", "pct_chg"]
            return df[[c for c in cols if c in df.columns]]
        except Exception as e:
            try:
                bs.logout()
            except Exception:
                pass
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 2
                print(f"  [!] {code} 采集失败，{wait}s后重试...", end="")
                time.sleep(wait)
            else:
                print(f"  [!] {code} 采集失败: {e}")
                return pd.DataFrame()


def fetch_stock_info(code: str, name: str) -> dict:
    """使用 BaoStock 获取股票基本信息"""
    market = "SH" if code.endswith(".SH") else "SZ"
    industry = STOCK_INDUSTRY_MAP.get(code)
    if not industry:
        try:
            _bs_login()
            rs = bs.query_stock_basic(_to_bs_code(code))
            if rs and rs.error_code == "0":
                info = rs.get_data()
                if not info.empty:
                    industry = info.iloc[0].get("industry", None)
            bs.logout()
        except Exception:
            try:
                bs.logout()
            except Exception:
                pass
    return {"ts_code": code, "name": name, "industry": industry, "market": market}


def get_last_trade_date(ts_code: str) -> str:
    """查询数据库中某股票最新交易日"""
    session = SessionLocal()
    try:
        row = session.execute(text(
            "SELECT MAX(trade_date) FROM stock_daily WHERE ts_code = :code"
        ), {"code": ts_code}).fetchone()
        return str(row[0]) if row and row[0] else None
    finally:
        session.close()


def init_data():
    """主入口：增量更新数据（只拉取缺失的最新数据）"""
    print("=" * 50)
    print("FinSight 数据增量更新开始")
    print("=" * 50)

    today = date.today().strftime("%Y-%m-%d")

    # 1. 获取股票列表
    stock_list = fetch_stock_list()
    print(f"\n[1/3] 获取到 {len(stock_list)} 只股票，开始采集基本信息...")

    # 2. 入库股票基本信息（仅新增）
    session = SessionLocal()
    try:
        for _, row in stock_list.iterrows():
            info = fetch_stock_info(row["ts_code"], row["name"])
            existing = session.query(StockInfo).filter_by(ts_code=row["ts_code"]).first()
            if not existing:
                session.add(StockInfo(**info))
        session.commit()
        print(f"  [+] Stock info saved to database")
    except Exception as e:
        session.rollback()
        print(f"  [!] 股票信息入库失败: {e}")
    finally:
        session.close()

    # 3. 增量采集日K线数据
    print(f"\n[2/3] 增量采集日K线数据（共 {len(stock_list)} 只，仅拉取缺失日期）...")
    all_daily = []
    success = 0
    for i, (_, row) in enumerate(stock_list.iterrows()):
        code = row["ts_code"]
        name = row["name"]

        last_date = get_last_trade_date(code)
        if last_date:
            start_date = (pd.to_datetime(last_date) + timedelta(days=1)).strftime("%Y-%m-%d")
            if start_date >= today:
                print(f"  [{i+1}/{len(stock_list)}] {code} {name} → 已是最新（{last_date}），跳过")
                continue
        else:
            start_date = DATA_START_DATE

        print(f"  [{i+1}/{len(stock_list)}] {code} {name}  {last_date}→{today}...", end="")
        df = fetch_stock_daily(code, start_date, today)
        if not df.empty:
            try:
                sess2 = SessionLocal()
                existing_dates = set(
                    r[0] for r in sess2.execute(text(
                        "SELECT trade_date FROM stock_daily WHERE ts_code = :code"
                    ), {"code": code}).fetchall()
                )
                sess2.close()
                df = df[~df["trade_date"].isin(existing_dates)]
            except Exception:
                pass
            if not df.empty:
                all_daily.append(df)
                success += 1
                print(f" +{len(df)}条")
            else:
                print(" 无新数据")
        else:
            print(" 无数据")

    # 4. 批量入库新K线数据
    if all_daily:
        total_new = sum(len(d) for d in all_daily)
        print(f"\n[3/3] 入库新K线数据（{success}只股票，共{total_new}条）...")
        combined = pd.concat(all_daily, ignore_index=True)
        try:
            combined.to_sql("stock_daily", engine, if_exists="append", index=False, method="multi", chunksize=1000)
            print(f"  [+] 新增 {total_new} 条K线数据")
        except Exception as e:
            print(f"  批量入库遇到问题，切换逐条模式: {e}")
            sess3 = SessionLocal()
            try:
                for _, row_data in combined.iterrows():
                    sess3.execute(text(
                        "INSERT IGNORE INTO stock_daily "
                        "(ts_code, trade_date, open, close, high, low, vol, amount, turnover, pct_chg) "
                        "VALUES (:ts_code, :trade_date, :open, :close, :high, :low, :vol, :amount, :turnover, :pct_chg)"
                    ), row_data.to_dict())
                sess3.commit()
                print(f"  [+] 新增 {total_new} 条K线数据（逐条模式）")
            except Exception as e2:
                sess3.rollback()
                print(f"  [!] 入库失败: {e2}")
            finally:
                sess3.close()
    else:
        print(f"\n[3/3] 所有股票已是最新，无需更新")

    status = get_data_status()
    print(f"\n当前数据库状态：{status['stock_count']}只股票，{status['daily_count']}条日线数据")
    print(f"数据日期范围：{status['date_range']['start']} ~ {status['date_range']['end']}")
    print("\n" + "=" * 50)
    print("数据增量更新完成！")
    print("=" * 50)


def get_data_status() -> dict:
    """获取数据状态统计"""
    session = SessionLocal()
    try:
        stock_count = session.query(StockInfo).count()
        daily_count = session.query(StockDaily).count()
        date_range = session.execute(text(
            "SELECT MIN(trade_date) as min_date, MAX(trade_date) as max_date FROM stock_daily"
        )).fetchone()
        return {
            "stock_count": stock_count,
            "daily_count": daily_count,
            "date_range": {
                "start": str(date_range[0]) if date_range[0] else None,
                "end": str(date_range[1]) if date_range[1] else None,
            }
        }
    finally:
        session.close()


if __name__ == "__main__":
    init_data()
