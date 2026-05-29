"""
修复 stock_info 表中的行业数据
"""
import sys
sys.path.insert(0, __file__.rsplit("\\", 1)[0])

from sqlalchemy import text
from database import engine
from config import STOCK_INDUSTRY_MAP

print("修复股票行业数据...")

with engine.connect() as conn:
    for code, industry in STOCK_INDUSTRY_MAP.items():
        conn.execute(text(
            "UPDATE stock_info SET industry = :industry WHERE ts_code = :code"
        ), {"industry": industry, "code": code})
    conn.commit()

print(f"  [+] Updated {len(STOCK_INDUSTRY_MAP)} stocks' industry info")

# 验证
with engine.connect() as conn:
    result = conn.execute(text(
        "SELECT COUNT(*) FROM stock_info WHERE industry IS NOT NULL"
    )).scalar()
    total = conn.execute(text("SELECT COUNT(*) FROM stock_info")).scalar()
    print(f"  数据库统计: {result}/{total} 只股票有行业信息")
