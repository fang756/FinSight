-- ============================================
-- FinSight 数据库初始化脚本
-- 使用方法: mysql -u root -p < init_db.sql
-- ============================================

CREATE DATABASE IF NOT EXISTS finsight DEFAULT CHARSET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE finsight;

-- 股票基本信息
CREATE TABLE IF NOT EXISTS stock_info (
    stock_code  VARCHAR(10) PRIMARY KEY COMMENT '股票代码 如 000001',
    stock_name  VARCHAR(50) NOT NULL COMMENT '股票名称',
    industry    VARCHAR(30) COMMENT '所属行业(申万一级)',
    list_date   DATE COMMENT '上市日期',
    market_cap  DECIMAL(18,2) COMMENT '总市值(亿元)',
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票基本信息';

-- 日线行情（核心表，所有模块共用）
CREATE TABLE IF NOT EXISTS stock_daily (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code  VARCHAR(10) NOT NULL COMMENT '股票代码',
    trade_date  DATE NOT NULL COMMENT '交易日期',
    open        DECIMAL(10,2) COMMENT '开盘价',
    close       DECIMAL(10,2) COMMENT '收盘价',
    high        DECIMAL(10,2) COMMENT '最高价',
    low         DECIMAL(10,2) COMMENT '最低价',
    volume      BIGINT COMMENT '成交量(手)',
    amount      DECIMAL(18,2) COMMENT '成交额(元)',
    turnover    DECIMAL(8,4) COMMENT '换手率(%)',
    pct_change  DECIMAL(8,4) COMMENT '涨跌幅(%)',
    UNIQUE KEY uk_code_date (stock_code, trade_date),
    INDEX idx_date (trade_date),
    INDEX idx_code (stock_code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='日线行情';

-- 因子评分
CREATE TABLE IF NOT EXISTS factor_score (
    id                BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code        VARCHAR(10) NOT NULL,
    trade_date        DATE NOT NULL,
    value_score       DECIMAL(8,4) COMMENT '价值因子得分',
    growth_score      DECIMAL(8,4) COMMENT '成长因子得分',
    quality_score     DECIMAL(8,4) COMMENT '质量因子得分',
    momentum_score    DECIMAL(8,4) COMMENT '动量因子得分',
    volatility_score  DECIMAL(8,4) COMMENT '波动因子得分',
    composite_score   DECIMAL(8,4) COMMENT '综合得分',
    UNIQUE KEY uk_code_date (stock_code, trade_date),
    INDEX idx_composite (composite_score DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='多因子评分';

-- 异常检测结果
CREATE TABLE IF NOT EXISTS anomaly_result (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code      VARCHAR(10) NOT NULL,
    trade_date      DATE NOT NULL,
    anomaly_score   DECIMAL(8,4) COMMENT '异常分数(越低越异常)',
    cluster_label   INT COMMENT 'K-Means聚类标签',
    is_anomaly      BOOLEAN COMMENT '是否异常',
    anomaly_type    VARCHAR(30) COMMENT '异常类型: volume_spike/price_manipulation/unusual_flow',
    detail          JSON COMMENT '异常详情',
    INDEX idx_date (trade_date),
    INDEX idx_anomaly (is_anomaly)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='异常检测结果';

-- 新闻舆情(加分项)
CREATE TABLE IF NOT EXISTS news_sentiment (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code  VARCHAR(10),
    pub_date    DATETIME COMMENT '发布时间',
    title       VARCHAR(300) COMMENT '新闻标题',
    source      VARCHAR(50) COMMENT '来源',
    sentiment   DECIMAL(5,4) COMMENT '情感分数 0-1 (>0.6正面 <0.4负面)',
    keywords    VARCHAR(300) COMMENT '关键词',
    INDEX idx_code_date (stock_code, pub_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新闻舆情情感';
