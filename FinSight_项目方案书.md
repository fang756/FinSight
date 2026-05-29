# FinSight - A股智能投研分析平台

## 《金融数据挖掘课程设计》项目方案书（一周速通版）

> **适用对象：** 数据科学与大数据技术专业 大三学生
> **开发周期：** 1周（7天）
> **团队建议：** 3-4人小组

---

## 一、项目概述

### 1.1 项目名称
**FinSight** — A股智能投研分析平台

### 1.2 核心理念：一周可答辩的最小闭环

不做大而全，做**小而精**。三个数据挖掘模块（选股+预测+异常）串成"选-测-警"闭环，前端能点、后端能调、模型能跑、结果能看。

### 1.3 与传统课程设计的差异

| 维度 | 传统方案 | 本项目 |
|------|---------|--------|
| 交付形式 | Jupyter Notebook + 静态图 | Web应用，前端可交互 |
| 算法覆盖 | 通常只做1-2种 | 分类+回归+聚类+异常检测 四类全覆盖 |
| 数据 | 小样本/示例数据 | AKShare真实A股数据，自动采集 |
| 复用性 | 一次性作业 | 前后端分离，可扩展为毕设 |

---

## 二、精简架构（一周可落地）

```
┌──────────────────────────────────────────────┐
│         前端 (Vue 3 + ECharts)                │
│  ┌────────┐ ┌────────┐ ┌────────┐            │
│  │因子选股│ │趋势预测│ │异常预警│            │
│  └────────┘ └────────┘ └────────┘            │
└──────────────┬───────────────────────────────┘
               │ HTTP (Axios)
┌──────────────▼───────────────────────────────┐
│         后端 (FastAPI + SQLAlchemy)           │
│  ┌────────┐ ┌────────┐ ┌────────┐            │
│  │因子API │ │预测API │ │异常API │            │
│  └────────┘ └────────┘ └────────┘            │
└──────────────┬───────────────────────────────┘
               │
┌──────────────▼───────────────────────────────┐
│    数据挖掘层 (Scikit-learn + PyTorch)        │
│  多因子选股 │ LSTM预测 │ Isolation Forest     │
└──────────────┬───────────────────────────────┘
               │
┌──────────────▼───────────────────────────────┐
│    MySQL + AKShare数据源                      │
└──────────────────────────────────────────────┘
```

### 精简原则：砍掉一切非必要

| 原方案组件 | 处理 | 理由 |
|-----------|------|------|
| Celery + Redis | **砍掉** | 模型训练改为同步请求，前端加loading即可 |
| WebSocket | **砍掉** | 改为普通HTTP轮询或手动刷新 |
| JWT认证 | **砍掉** | 课程设计无需用户体系，直接开放访问 |
| FinBERT NLP | **砍掉** | 微调BERT需要GPU+大量时间，一周搞不定 |
| 回测引擎 | **砍掉** | 独立模块，与核心挖掘无关，加分会更好但没有也能答辩 |
| Docker | **砍掉** | 本地直接跑，省掉容器化调试时间 |
| 舆情模块 | **替换为轻量版** | 用SnowNLP（0配置中文情感分析）替代FinBERT |

### 技术选型（精简版）

| 层次 | 技术 | 理由 |
|------|------|------|
| 前端 | Vue 3 + Vite + ECharts + Element Plus | 大三学生大概率学过Vue |
| 后端 | FastAPI + SQLAlchemy | Python生态，自动API文档 |
| ML | Scikit-learn | 多因子/聚类/异常检测 |
| DL | PyTorch | LSTM预测（如果时间紧可换sklearn的MLP） |
| NLP | SnowNLP | 零配置中文情感分析，1行代码出结果 |
| 数据源 | AKShare | pip install即用，免费A股数据 |
| 数据库 | MySQL | 学校一般都有，学生熟悉 |

---

## 三、三个核心挖掘模块（精简实现）

### 3.1 模块一：多因子选股（分类 + 特征工程）

**数据挖掘考点：** 特征工程、标准化、PCA降维、分类评估

**实现方案（2天可完成）：**

```python
# 1. 因子构建 — 从AKShare获取财务数据，计算5个维度因子
factors = {
    '价值': ['PE', 'PB', '股息率'],
    '成长': ['营收增速', '净利润增速'],
    '质量': ['ROE', '资产负债率'],
    '动量': ['过去3月收益率', '过去6月收益率'],
    '波动': ['波动率', '最大回撤']
}

# 2. 因子预处理
#    - 去极值：MAD法 (Median Absolute Deviation)
#    - 标准化：Z-Score
#    - 缺失值：行业均值填充

# 3. 因子合成 — 等权加总（最简单，1行代码）
composite_score = (z_value + z_growth + z_quality + z_momentum + z_volatility) / 5

# 4. 选股 — 综合评分排名，取Top N
selected = df.nlargest(20, 'composite_score')
```

**前端交互：**
- 因子雷达图（ECharts radar）— 展示单只股票5维因子
- 评分排名表 — Element Plus表格，可排序
- 行业筛选下拉框

### 3.2 模块二：LSTM价格趋势预测（回归/时序预测）

**数据挖掘考点：** 时序建模、深度学习、序列预测、过拟合控制

**实现方案（2天可完成）：**

```python
# 1. 数据 — 日K线（AKShare获取），取收盘价 + 成交量
# 2. 特征 — 过去20日滑动窗口
# 3. 模型 — 单层LSTM（够用了，别搞Attention）
class LSTMModel(nn.Module):
    def __init__(self, input_size=2, hidden_size=64, num_layers=1):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 1)  # 输出下一日收盘价

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(out[:, -1, :])

# 4. 预测 — 未来5日收盘价
# 5. 评估 — MAE / RMSE / 方向准确率
```

**前端交互：**
- K线图 + 预测虚线（ECharts candlestick + line）
- 评估指标卡片（MAE/RMSE/方向准确率）
- 股票代码输入框 + 预测按钮

### 3.3 模块三：异常交易检测（异常检测 + 聚类）

**数据挖掘考点：** 无监督学习、异常检测、聚类分析

**实现方案（1.5天可完成）：**

```python
# 方法1：Isolation Forest — 检测异常交易日
from sklearn.ensemble import IsolationForest
clf = IsolationForest(contamination=0.05, random_state=42)
df['is_anomaly'] = clf.fit_predict(X[['换手率', '涨跌幅', '成交量比']])

# 方法2：K-Means聚类 — 将交易模式分为3类（正常/疑似/异常）
from sklearn.cluster import KMeans
kmeans = KMeans(n_clusters=3, random_state=42)
df['cluster'] = kmeans.fit_predict(X_scaled)

# 异常 = 远离所有聚类中心的点
```

**前端交互：**
- 散点图（ECharts scatter）— 正常灰/异常红
- K线图上标注异常交易日（红色标记）
- 异常股票列表

---

## 四、数据库设计（精简版）

```sql
-- 股票基本信息
CREATE TABLE stock_info (
    stock_code  VARCHAR(10) PRIMARY KEY,
    stock_name  VARCHAR(50) NOT NULL,
    industry    VARCHAR(30),
    list_date   DATE,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 日线行情（核心表，所有模块共用）
CREATE TABLE stock_daily (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code  VARCHAR(10) NOT NULL,
    trade_date  DATE NOT NULL,
    open        DECIMAL(10,2),
    close       DECIMAL(10,2),
    high        DECIMAL(10,2),
    low         DECIMAL(10,2),
    volume      BIGINT,
    amount      DECIMAL(18,2),
    turnover    DECIMAL(8,4),
    pct_change  DECIMAL(8,4),       -- 涨跌幅
    UNIQUE KEY uk_code_date (stock_code, trade_date),
    INDEX idx_date (trade_date)
);

-- 因子评分
CREATE TABLE factor_score (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code  VARCHAR(10) NOT NULL,
    trade_date  DATE NOT NULL,
    value_score DECIMAL(8,4),
    growth_score DECIMAL(8,4),
    quality_score DECIMAL(8,4),
    momentum_score DECIMAL(8,4),
    volatility_score DECIMAL(8,4),
    composite_score DECIMAL(8,4),
    UNIQUE KEY uk_code_date (stock_code, trade_date)
);

-- 异常检测结果
CREATE TABLE anomaly_result (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code  VARCHAR(10) NOT NULL,
    trade_date  DATE NOT NULL,
    anomaly_score DECIMAL(8,4),
    cluster_label INT,
    is_anomaly  BOOLEAN,
    detail      JSON,
    INDEX idx_date (trade_date)
);
```

> 只有4张表，30分钟建完。

---

## 五、前端页面（3个核心页面 + 1个首页）

### 5.1 页面规划

| 页面 | 路由 | 核心组件 | 工时 |
|------|------|---------|------|
| 首页总览 | `/` | 指数卡片 + 涨跌分布 + 模块入口 | 0.5天 |
| 因子选股 | `/factor` | 雷达图 + 评分表 + 行业筛选 | 1天 |
| 趋势预测 | `/predict` | K线图 + 预测线 + 评估指标 | 1天 |
| 异常检测 | `/anomaly` | 散点图 + K线标注 + 预警表 | 0.5天 |

### 5.2 首页总览设计

```
┌─────────────────────────────────────────────────────┐
│  FinSight — A股智能投研分析平台                      │
├───────────┬───────────┬───────────┬─────────────────┤
│  上证指数  │  深证成指  │  创业板指  │  异常预警数     │
│  3,234.56 │ 10,567.89 │  2,123.45 │     5只         │
│  ▲ +1.23% │  ▼ -0.56% │  ▲ +2.01% │                │
├───────────┴───────────┴───────────┴─────────────────┤
│  今日涨跌分布柱状图        │   行业涨跌热力图          │
│  [========ECharts========] │ [======ECharts=======]  │
├────────────────────────────┴────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ 因子选股  │  │ 趋势预测  │  │ 异常检测  │          │
│  │  进入 →  │  │  进入 →  │  │  进入 →  │          │
│  └──────────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────┘
```

---

## 六、后端API（精简版，15个接口）

```python
# ============ 行情 ============
GET  /api/market/indices          # 大盘指数
GET  /api/market/kline/{code}     # 个股K线数据
GET  /api/market/sectors          # 行业涨跌

# ============ 因子选股 ============
GET  /api/factor/radar/{code}     # 个股因子雷达数据
GET  /api/factor/ranking          # 因子排名列表（支持行业筛选）
POST /api/factor/refresh          # 重新计算因子（从AKShare拉取最新数据）

# ============ LSTM预测 ============
POST /api/predict/train/{code}    # 触发训练（同步，前端loading等待）
GET  /api/predict/result/{code}   # 获取预测结果
GET  /api/predict/models          # 已训练模型列表

# ============ 异常检测 ============
GET  /api/anomaly/detect          # 异常检测结果（支持日期范围筛选）
GET  /api/anomaly/alerts          # 预警列表
GET  /api/anomaly/kline/{code}    # 带异常标注的K线数据

# ============ 数据管理 ============
POST /api/data/init               # 初始化数据（首次运行时采集）
GET  /api/data/status             # 数据状态（已采集多少只股票、日期范围）
```

> 没有认证模块、没有WebSocket、没有分页——够用就行。

---

## 七、项目目录结构（精简版）

```
FinSight/
├── frontend/                        # 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── HomeView.vue         # 首页总览
│   │   │   ├── FactorView.vue       # 因子选股
│   │   │   ├── PredictView.vue      # 趋势预测
│   │   │   └── AnomalyView.vue      # 异常检测
│   │   ├── components/
│   │   │   ├── KlineChart.vue       # K线图组件
│   │   │   ├── RadarChart.vue       # 雷达图组件
│   │   │   └── ScatterChart.vue     # 散点图组件
│   │   ├── api/
│   │   │   └── index.js             # 统一API封装（axios）
│   │   ├── router/
│   │   │   └── index.js
│   │   ├── App.vue
│   │   └── main.js
│   ├── package.json
│   └── vite.config.js
│
├── backend/                         # 后端
│   ├── main.py                      # FastAPI入口（所有路由集中于此，不超过300行）
│   ├── database.py                  # 数据库连接 + ORM模型
│   ├── data_fetcher.py              # AKShare数据采集（独立脚本）
│   ├── factor_engine.py             # 多因子选股引擎
│   ├── lstm_model.py                # LSTM预测模型
│   ├── anomaly_detector.py          # 异常检测引擎
│   ├── requirements.txt
│   └── config.py                    # 配置（数据库连接等）
│
├── data/                            # 数据目录（CSV备份）
│   └── README.md
│
├── init_db.sql                      # 建表脚本
└── README.md                        # 项目说明
```

> 后端核心只有 **6个Python文件**，每个文件100-300行。不搞分层架构、不搞service/repository模式——单文件直出，大三学生能看懂、能改。

---

## 八、7天开发计划（精确到小时）

### Day 1：环境搭建 + 数据入库（周一）

| 时段 | 任务 | 产出 |
|------|------|------|
| 上午 | Python环境 + MySQL建表 + AKShare数据采集脚本 | `init_db.sql` + `data_fetcher.py` |
| 下午 | 采集沪深300成分股近2年日K线 + 基本面数据，导入MySQL | 数据库有数据 |
| 晚上 | FastAPI骨架 + 数据库连通测试 | `main.py` + `database.py` + `/api/market/*` |

### Day 2：多因子选股模块（周二）

| 时段 | 任务 | 产出 |
|------|------|------|
| 上午 | 因子构建脚本：5维因子计算 + 去极值MAD + Z-Score标准化 | `factor_engine.py` |
| 下午 | 因子API：排名列表 + 雷达数据 + 行业筛选 | `/api/factor/*` |
| 晚上 | 前端因子页面：雷达图 + 排名表 | `FactorView.vue` + `RadarChart.vue` |

### Day 3-4：LSTM预测模块（周三-周四）

| 时段 | 任务 | 产出 |
|------|------|------|
| Day3上午 | 数据集构建：滑动窗口 + 训练/测试集切分 | `lstm_model.py` 前半部分 |
| Day3下午 | LSTM模型定义 + 训练循环 + 保存模型 | `lstm_model.py` 完整版 |
| Day3晚上 | 预测API：训练 + 推理 + 评估指标 | `/api/predict/*` |
| Day4上午 | 前端K线图组件（ECharts candlestick） | `KlineChart.vue` |
| Day4下午 | 预测线叠加 + 评估指标展示 | `PredictView.vue` |
| Day4晚上 | 联调 + 预训练2-3只股票的模型备用 | 可演示的预测功能 |

### Day 5：异常检测模块（周五）

| 时段 | 任务 | 产出 |
|------|------|------|
| 上午 | Isolation Forest + K-Means聚类实现 | `anomaly_detector.py` |
| 下午 | 异常检测API + 前端散点图 + K线标注 | `/api/anomaly/*` + `AnomalyView.vue` |
| 晚上 | 首页总览页面（指数卡片 + 模块入口） | `HomeView.vue` |

### Day 6：系统集成 + Bug修复（周六）

| 时段 | 任务 | 产出 |
|------|------|------|
| 上午 | 前后端联调，确保3个模块都能走通 | 可运行的完整系统 |
| 下午 | Bug修复 + 边界情况处理（数据缺失、网络超时） | 稳定版 |
| 晚上 | 预录制演示视频（防答辩时翻车） | demo.mp4 |

### Day 7：文档 + 答辩准备（周日）

| 时段 | 任务 | 产出 |
|------|------|------|
| 上午 | README文档 + 代码注释补充 | 完整项目文档 |
| 下午 | 答辩PPT（重点：3个算法原理 + 1个创新点） | 答辩PPT |
| 晚上 | 演示排练 | 自信答辩 |

---

## 九、课程考核点覆盖

| 课程要求 | 模块 | 具体实现 |
|---------|------|---------|
| **数据预处理** | 全模块 | 缺失值填充、MAD去极值、Z-Score标准化、滑动窗口 |
| **分类算法** | 因子选股 | 按综合评分Top N选股（二分类：入选/未入选）+ 评估 |
| **回归预测** | LSTM | 时序回归预测下一日收盘价，MAE/RMSE评估 |
| **聚类算法** | 异常检测 | K-Means将交易模式分为3类 |
| **异常检测** | 异常检测 | Isolation Forest检测异常交易日 |
| **可视化** | 前端 | 雷达图、K线图、散点图、热力图（4种ECharts图表） |
| **系统实现** | 全栈 | 前后端分离Web应用 |

---

## 十、加分项（时间允许再做）

按优先级排序，做完核心3模块后如果还有时间：

| 优先级 | 加分项 | 预计工时 | 加分点 |
|--------|--------|---------|--------|
| P1 | SnowNLP舆情模块 | 3小时 | NLP文本挖掘覆盖 |
| P2 | 因子IC有效性检验 | 2小时 | 量化因子分析深度 |
| P3 | 预测结果回测（简单版） | 3小时 | 策略验证闭环 |
| P4 | Docker部署 | 1小时 | 工程化加分 |

### SnowNLP舆情模块（3小时速通版）

```python
from snownlp import SnowNLP

# AKShare获取财经新闻标题
news = ak.stock_news_em(symbol="000001")

# 一行代码情感分析
news['sentiment'] = news['标题'].apply(lambda x: SnowNLP(x).sentiments)
# sentiments返回0-1浮点数，>0.6正面，<0.4负面，中间中性

# 前端：新闻列表 + 情感标签（绿/灰/红）
```

> 不需要训练模型、不需要GPU、不需要微调——pip install snownlp 即可。

---

## 十一、数据获取方案

| 数据 | 数据源 | 获取方式 | 频率 |
|------|--------|---------|------|
| 日K线 | AKShare | `ak.stock_zh_a_hist(symbol, period="daily")` | 首次全量 + 后续增量 |
| 实时行情 | AKShare | `ak.stock_zh_a_spot_em()` | 首页展示 |
| 财务指标 | AKShare | `ak.stock_financial_analysis_indicator(symbol)` | 因子计算用 |
| 行业分类 | AKShare | `ak.stock_board_industry_name_em()` | 行业筛选用 |
| 股票列表 | AKShare | `ak.stock_info_a_code_name()` | 基础数据 |
| 财经新闻 | AKShare | `ak.stock_news_em(symbol)` | 加分项：舆情 |

**首次数据采集脚本示例：**

```python
import akshare as ak
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("mysql+pymysql://root:password@localhost:3306/finsight")

# 1. 获取沪深300成分股
hs300 = ak.index_stock_cons_weight_csindex(symbol="000300")
stock_list = hs300['品种代码'].tolist()

# 2. 批量采集日K线（约5分钟）
for code in stock_list[:50]:  # 先采50只，够用就行
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily",
                                 start_date="20230101", end_date="20261231")
        df.to_sql('stock_daily', engine, if_exists='append', index=False)
    except Exception as e:
        print(f"{code} 采集失败: {e}")
```

---

## 十二、答辩策略

### 核心话术（1分钟开场）

> 我们的项目叫 FinSight，是一个 A股智能投研分析平台。传统课程设计往往只做单一算法的 Jupyter 分析，我们做了一个**完整的前后端分离 Web 应用**，包含三个核心挖掘模块——多因子选股、LSTM趋势预测、异常交易检测——形成"选股-预测-预警"的投研闭环。

### 演示顺序（5分钟）

1. **首页** — 大盘指数卡片，涨跌分布图，证明数据是真的
2. **因子选股** — 选一只股票看雷达图，展示Top20排名表
3. **趋势预测** — 点"训练"，等5秒，K线图上出现预测虚线
4. **异常检测** — 散点图红色标注异常点，K线图上红标异常日
5. **加分项** — 如果做了舆情，展示新闻情感标签

### 老师可能问的问题

| 问题 | 回答要点 |
|------|---------|
| 为什么选LSTM不用Transformer？ | LSTM对短序列时序预测够用，训练快，一周内可完成。Transformer数据需求量大，小样本反而不如LSTM |
| 因子选股的IC值是多少？ | （实际跑出来填）动量因子IC通常0.03-0.05，价值因子IC波动大，展示IC时序图 |
| 异常检测的contamination为什么设0.05？ | A股异常交易日约占5%，与Isolation Forest默认值一致，也做过0.03和0.1的对比 |
| 前后端怎么通信的？ | FastAPI提供REST API，前端Axios调用，返回JSON数据，ECharts渲染 |
| 数据量有多大？ | 50只股票 × 2年日K ≈ 25000条记录，MySQL存储 < 10MB |

---

## 十三、风险与对策

| 风险 | 概率 | 对策 |
|------|------|------|
| AKShare接口变更/限速 | 中 | 提前采集数据存CSV，答辩时从CSV读 |
| LSTM训练时间过长 | 低 | 只训练单只股票，序列长度限制60日 |
| 前端Vue不熟 | 中 | 用最简单的组合式API，不搞Pinia状态管理，直接组件内state |
| MySQL连不上 | 低 | SQLite兜底，改一行连接字符串即可 |
| 答辩时网络不通 | 中 | Day6预录视频 + 提前缓存所有数据到本地 |

---

*本方案专为一周速通设计，核心原则：能跑通 > 完美 > 功能多*
