"""
FinSight 数据采集脚本
使用 AKShare 采集A股数据并入库
"""
import time
import akshare as ak
import pandas as pd
from sqlalchemy import text
from database import engine, SessionLocal, StockInfo, StockDaily
from config import STOCK_COUNT, DATA_START_DATE, DATA_END_DATE, STOCK_INDUSTRY_MAP


def fetch_stock_list(count: int = STOCK_COUNT) -> pd.DataFrame:
    """获取股票列表（沪深300成分股前N只）"""
    print(f"[数据采集] 获取沪深300成分股...")
    try:
        df = ak.index_stock_cons_csindex(symbol="000300")
        df = df.head(count)
        df = df.rename(columns={
            "品种代码": "ts_code",
            "品种名称": "name",
        })
        df["ts_code"] = df["ts_code"].astype(str).str.zfill(6)
        # 补全市场后缀
        def add_suffix(code):
            if code.startswith("6"):
                return code + ".SH"
            else:
                return code + ".SZ"
        df["ts_code"] = df["ts_code"].apply(add_suffix)
        print(f"[数据采集] 获取到 {len(df)} 只股票")
        return df[["ts_code", "name"]]
    except Exception as e:
        print(f"[数据采集] 获取股票列表失败: {e}")
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
    """获取单只股票日K线数据（带重试机制）"""
    pure_code = code.split(".")[0]
    for attempt in range(max_retries):
        try:
            df = ak.stock_zh_a_hist(
                symbol=pure_code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust="qfq"
            )
            if df.empty:
                return pd.DataFrame()

            df = df.rename(columns={
                "日期": "trade_date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "vol",
                "成交额": "amount",
                "换手率": "turnover",
                "涨跌幅": "pct_chg",
            })
            df["ts_code"] = code
            df["trade_date"] = pd.to_datetime(df["trade_date"]).dt.date
            cols = ["ts_code", "trade_date", "open", "close", "high",
                    "low", "vol", "amount", "turnover", "pct_chg"]
            df = df[[c for c in cols if c in df.columns]]
            return df
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 2
                print(f"  [!] {code} 采集失败，{wait}s后重试...", end="")
                time.sleep(wait)
            else:
                print(f"  [!] {code} 采集失败: {e}")
                return pd.DataFrame()


def fetch_stock_info(code: str, name: str) -> dict:
    """获取股票基本信息（行业等）"""
    market = "SH" if code.endswith(".SH") else "SZ"
    # 使用本地映射表（AKShare行业接口不稳定）
    industry = STOCK_INDUSTRY_MAP.get(code)
    if not industry:
        # 兜底：尝试AKShare
        try:
            df = ak.stock_individual_info_em(symbol=code.split(".")[0])
            info = dict(zip(df["item"], df["value"]))
            industry = info.get("行业", None)
        except Exception:
            pass
    return {
        "ts_code": code,
        "name": name,
        "industry": industry,
        "market": market,
    }


def init_data():
    """主入口：初始化所有数据"""
    print("=" * 50)
    print("FinSight 数据初始化开始")
    print("=" * 50)

    # 1. 获取股票列表
    stock_list = fetch_stock_list()
    print(f"\n[1/3] 获取到 {len(stock_list)} 只股票，开始采集基本信息...")

    # 2. 入库股票基本信息
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

    # 3. 采集日K线数据
    print(f"\n[2/3] 开始采集日K线数据（共 {len(stock_list)} 只）...")
    all_daily = []
    success = 0
    for i, (_, row) in enumerate(stock_list.iterrows()):
        code = row["ts_code"]
        name = row["name"]
        print(f"  [{i+1}/{len(stock_list)}] 采集 {code} {name}...", end="")
        df = fetch_stock_daily(code, DATA_START_DATE, DATA_END_DATE)
        if not df.empty:
            all_daily.append(df)
            success += 1
            print(f" {len(df)}条")
        else:
            print(" 无数据")
        time.sleep(1.5)  # 增加延时避免被限流

    # 4. 批量入库K线数据
    if all_daily:
        print(f"\n[3/3] 入库K线数据（{success}只股票，共{sum(len(d) for d in all_daily)}条）...")
        combined = pd.concat(all_daily, ignore_index=True)
        try:
            combined.to_sql(
                "stock_daily", engine,
                if_exists="append", index=False,
                method="multi", chunksize=1000
            )
            print(f"  [+] K-line data saved to database")
        except Exception as e:
            print(f"  批量入库遇到问题，切换逐条模式: {e}")
            session = SessionLocal()
            for _, row_data in combined.iterrows():
                try:
                    session.execute(text(
                        "INSERT IGNORE INTO stock_daily "
                        "(ts_code, trade_date, open, close, high, low, vol, amount, turnover, pct_chg) "
                        "VALUES (:ts_code, :trade_date, :open, :close, :high, :low, :vol, :amount, :turnover, :pct_chg)"
                    ), row_data.to_dict())
                except Exception:
                    pass
            session.commit()
            session.close()
            print(f"  [+] K-line data saved (row-by-row mode)")

    print("\n" + "=" * 50)
    print("数据初始化完成！")
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
