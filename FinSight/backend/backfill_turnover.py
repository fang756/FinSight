"""Backfill turnover data for 600519.SH using retry mechanism"""
import sys
sys.path.insert(0, r"C:\Users\fanghongjiang\Desktop\2026-05-28-14-49-49\FinSight\backend")
from tools import _akshare_retry
import akshare as ak
from database import SessionLocal
from sqlalchemy import text
from datetime import datetime

print("Fetching data for 600519.SH with retry...")
try:
    df = _akshare_retry(ak.stock_zh_a_hist, symbol="600519", period="daily",
                        start_date="20230101",
                        end_date=datetime.now().strftime("%Y%m%d"), adjust="qfq")
except Exception as e:
    print(f"Failed after retries: {e}")
    exit()

if df is None or df.empty:
    print("No data fetched!")
    exit()

print(f"Got {len(df)} records")

db = SessionLocal()
updated = 0
for _, r in df.iterrows():
    turnover_val = float(r["换手率"]) if "换手率" in r else 0
    result = db.execute(text("UPDATE stock_daily SET turnover = :t WHERE ts_code = '600519.SH' AND trade_date = :d AND (turnover IS NULL OR turnover = 0)"),
               {"t": turnover_val, "d": str(r["日期"])})
    if result.rowcount > 0:
        updated += 1

db.commit()
db.close()
print(f"Updated {updated} records with turnover data")
