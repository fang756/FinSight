import sys
sys.path.insert(0, r"C:\Users\fanghongjiang\Desktop\2026-05-28-14-49-49\FinSight\backend")
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
db.execute(text("UPDATE stock_info SET industry = :ind WHERE ts_code = :code"),
           {"ind": "白酒", "code": "600519.SH"})
db.commit()
r = db.execute(text("SELECT ts_code, name, industry FROM stock_info WHERE ts_code = :code"),
              {"code": "600519.SH"}).fetchone()
print(f"Updated: {r}")
db.close()
