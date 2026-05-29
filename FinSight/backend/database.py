"""
FinSight 数据库连接 + ORM模型
"""
from sqlalchemy import create_engine, Column, BigInteger, String, Date, DateTime, Boolean, Integer, JSON, func, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_recycle=3600, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """FastAPI依赖注入：获取数据库session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============ ORM 模型（与数据库实际表结构对齐）============

class StockInfo(Base):
    __tablename__ = "stock_info"
    ts_code = Column(String(20), primary_key=True, comment='股票代码 如000001.SZ')
    name = Column(String(50), nullable=False, comment='股票名称')
    industry = Column(String(50), comment='所属行业')
    market = Column(String(20), comment='市场(SH/SZ)')
    list_date = Column(Date, comment='上市日期')
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class StockDaily(Base):
    __tablename__ = "stock_daily"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False, index=True, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    open = Column(Float(10), comment='开盘价')
    high = Column(Float(10), comment='最高价')
    low = Column(Float(10), comment='最低价')
    close = Column(Float(10), comment='收盘价')
    vol = Column(Float(20), comment='成交量(手)')
    amount = Column(Float(20), comment='成交额(千元)')
    pct_chg = Column(Float(10), comment='涨跌幅(%)')
    turnover = Column(Float(10), comment='换手率(%)')


class FactorScore(Base):
    __tablename__ = "factor_score"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='计算日期')
    factor_pe = Column(Float(10), comment='PE因子')
    factor_pb = Column(Float(10), comment='PB因子')
    factor_roe = Column(Float(10), comment='ROE因子')
    factor_momentum = Column(Float(10), comment='动量因子')
    factor_vol = Column(Float(10), comment='波动率因子')
    composite_score = Column(Float(10), comment='综合得分')
    rank_num = Column(Integer, comment='排名')


class AnomalyResult(Base):
    __tablename__ = "anomaly_result"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False, comment='股票代码')
    trade_date = Column(Date, nullable=False, comment='交易日期')
    anomaly_score = Column(Float(10), comment='异常分数')
    is_anomaly = Column(Boolean, default=False, comment='是否异常(0否1是)')
    cluster_label = Column(Integer, comment='K-Means聚类标签')
    method = Column(String(30), comment='检测方法')
    detail = Column(JSON, comment='异常详情')


class NewsSentiment(Base):
    __tablename__ = "news_sentiment"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ts_code = Column(String(20), nullable=False, comment='股票代码')
    pub_date = Column(DateTime, comment='发布时间')
    title = Column(String(500), comment='新闻标题')
    content = Column(String(5000), comment='新闻内容')
    sentiment_score = Column(Float(10), comment='情感得分(0-1)')
    sentiment_label = Column(String(20), comment='情感标签')
    source = Column(String(100), comment='来源')
