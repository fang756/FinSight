# FinSight - A股智能投研分析平台

## 《金融数据挖掘课程设计》项目方案书

> **适用对象：** 数据科学与大数据技术专业 大三学生
> **开发周期：** 1周（7天）
> **团队建议：** 3-4人小组

---

## 一、项目概述

### 1.1 项目名称
**FinSight** — A股智能投研分析平台

### 1.2 核心理念：一周可答辩的最小闭环

不做大而全，做**小而精**。三个数据挖掘模块（选股+预测+异常）串成"选-测-警"闭环，加上 AI 投资助手辅助分析，前端能点、后端能调、模型能跑、结果能看。

### 1.3 与传统课程设计的差异

| 维度 | 传统方案 | 本项目 |
|------|---------|--------|
| 交付形式 | Jupyter Notebook + 静态图 | Web应用，前端可交互 |
| 算法覆盖 | 通常只做1-2种 | 分类+回归+聚类+异常检测 四类全覆盖 |
| 数据 | 小样本/示例数据 | BaoStock稳定数据源，自动采集 |
| AI能力 | 无 | 集成DeepSeek大模型，支持自然语言问答 |
| 复用性 | 一次性作业 | 前后端分离，可扩展为毕设 |

---

## 二、精简架构（一周可落地）

```
┌──────────────────────────────────────────────────────┐
│              前端 (Vue 3 + ECharts)                   │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │因子选股│ │趋势预测│ │异常预警│ │AI助手  │        │
│  └────────┘ └────────┘ └────────┘ └────────┘        │
└──────────────────────┬───────────────────────────────┘
                       │ HTTP (Axios / SSE流式)
┌──────────────────────▼───────────────────────────────┐
│          后端 (FastAPI + SQLAlchemy)                  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐      │
│  │因子API │ │预测API │ │异常API │ │AI问答API │      │
│  └────────┘ └────────┘ └────────┘ └──────────┘      │
└──────────┬───────────────────────────────┬───────────┘
           │                               │
┌──────────▼───────────────────┐ ┌────────▼───────────┐
│  数据挖掘层 (sklearn+PyTorch) │ │  DeepSeek AI       │
│ 多因子选股│LSTM预测│异常检测  │ │  ＋ SnowNLP情感    │
└──────────┬───────────────────┘ └────────┬───────────┘
           │                               │
┌──────────▼──────────────────────────────▼───────────┐
│             MySQL + BaoStock 数据源                  │
└─────────────────────────────────────────────────────┘
```

### 精简原则：砍掉一切非必要

| 原方案组件 | 处理 | 理由 |
|-----------|------|------|
| Celery + Redis | **砍掉** | 模型训练改为同步请求，前端加loading即可 |
| WebSocket | **砍掉** | SSE流式替代（用于AI聊天），更轻量 |
| JWT认证 | **砍掉** | 课程设计无需用户体系，直接开放访问 |
| FinBERT NLP | **砍掉** | 微调BERT需要GPU+大量时间，一周搞不定 |
| 回测引擎 | **砍掉** | 独立模块，与核心挖掘无关 |
| Docker | **砍掉** | 本地直接跑，省掉容器化调试时间 |
| AKShare | **替换** | 接口不稳定，换用BaoStock（专为量化设计的API） |

### 技术选型

| 层次 | 技术 | 理由 |
|------|------|------|
| 前端 | Vue 3 + Vite + ECharts + Element Plus | 大三学生大概率学过Vue |
| 后端 | FastAPI + SQLAlchemy | Python生态，自动API文档 |
| ML | Scikit-learn | 多因子/聚类/异常检测 |
| DL | PyTorch | LSTM预测 |
| NLP | SnowNLP | 零配置中文情感分析，1行代码出结果 |
| AI | DeepSeek API + OpenAI SDK | 大模型驱动的智能投资助手 |
| 数据源 | BaoStock | 专为量化交易设计的免费API，稳定无反爬 |
| 数据库 | MySQL | 学校一般都有，学生熟悉 |

---

## 三、三个核心挖掘模块（精简实现）

### 3.1 模块一：多因子选股（分类 + 特征工程）

**数据挖掘考点：** 特征工程、标准化、PCA降维、分类评估

**实现方案（2天可完成）：**

```python
# 1. 因子构建 — 从BaoStock获取行情数据，计算5个维度因子
factors = {
    '价值': ['PE', 'PB'],
    '质量': ['ROE'],
    '动量': ['过去3月收益率', '过去6月收益率'],
    '波动': ['波动率', '最大回撤'],
    '量价': ['成交量变化', '换手率']
}

# 2. 因子预处理
#    - 去极值：MAD法 (Median Absolute Deviation)
#    - 标准化：Z-Score
#    - 缺失值：行业均值填充

# 3. 因子合成 — 等权加总（最简单，1行代码）
composite_score = (z_value + z_quality + z_momentum + z_volatility + z_volume) / 5

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
# 1. 数据 — 日K线（BaoStock获取），取收盘价 + 成交量
# 2. 特征 — 过去20日滑动窗口
# 3. 模型 — 单层LSTM（够用了）
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
```

**前端交互：**
- 散点图（ECharts scatter）— 正常灰/异常红
- K线图上标注异常交易日（红色标记）
- 异常股票列表

---

## 四、AI 投资助手（附加模块）

除了三个核心挖掘模块，系统还集成了一个 AI 投资助手（股小查），通过 DeepSeek 大模型提供自然语言交互。

### 4.1 技术实现

```python
# 1. 舆情采集 — AKShare获取个股新闻，SnowNLP做情感分析
news = ak.stock_news_em(symbol="000858")
news['sentiment'] = news['标题'].apply(lambda x: SnowNLP(x).sentiments)

# 2. 情感数据入库 — 存入MySQL news_sentiment表（去重）
# 3. AI问答 — 将情感摘要作为上下文，调用DeepSeek API
messages = [
    {"role": "system", "content": "你是一个股票投资助手，基于新闻情感数据回答"},
    {"role": "user", "content": question}
]
response = openai.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=[...],   # 工具调用：搜索股票、查行情、查预测
    stream=True    # SSE流式输出
)
```

### 4.2 功能特点

- **流式回答**：采用 SSE 流式输出，问答体验流畅（解决 120s 超时问题）
- **工具调用**：支持搜索股票、查 K 线行情、查因子评分、查 LSTM 预测
- **实时新闻**：用户指定股票时，自动拉取最新新闻+情感分析
- **非股票问题拒绝**：非金融问题礼貌拒绝，限定问答范围
- **系统外股票**：支持查询数据库中未收录的股票（实时从 BaoStock 拉取）

### 4.3 交互流程

```
用户提问 → 前端 SSE请求 → 后端识别股票 → 查新闻情感
    → 组装Prompt → DeepSeek API流式返回 → 前端实时渲染
```

---

## 五、数据库设计（精简版）

```sql
-- 股票基本信息
CREATE TABLE stock_info (
    ts_code     VARCHAR(20) PRIMARY KEY,   -- 如 600519.SH
    name        VARCHAR(50) NOT NULL,
    industry    VARCHAR(30),
    market      VARCHAR(10),
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 日线行情（核心表，所有模块共用）
CREATE TABLE stock_daily (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code     VARCHAR(20) NOT NULL,
    trade_date  DATE NOT NULL,
    open        DECIMAL(10,2),
    close       DECIMAL(10,2),
    high        DECIMAL(10,2),
    low         DECIMAL(10,2),
    volume      BIGINT,
    amount      DECIMAL(18,2),
    turnover    DECIMAL(8,4),
    pct_chg     DECIMAL(8,4),              -- 涨跌幅
    UNIQUE KEY uk_code_date (ts_code, trade_date),
    INDEX idx_date (trade_date)
);

-- 因子评分
CREATE TABLE factor_score (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code         VARCHAR(20) NOT NULL,
    trade_date      DATE NOT NULL,
    factor_pe       DECIMAL(8,4),
    factor_pb       DECIMAL(8,4),
    factor_roe      DECIMAL(8,4),
    factor_momentum DECIMAL(8,4),
    composite_score DECIMAL(8,4),
    rank_num        INT,
    UNIQUE KEY uk_code_date (ts_code, trade_date)
);

-- 新闻情感分析
CREATE TABLE news_sentiment (
    id              BIGINT AUTO_INCREMENT PRIMARY KEY,
    ts_code         VARCHAR(20) NOT NULL,
    pub_date        DATETIME,
    title           VARCHAR(500),
    content         TEXT,
    sentiment_score DECIMAL(6,4),
    sentiment_label VARCHAR(10),            -- positive/negative/neutral
    source          VARCHAR(100),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_code (ts_code),
    INDEX idx_date (pub_date)
);
```

---

## 六、前端页面

### 6.1 页面规划

| 页面 | 路由 | 核心组件 | 工时 |
|------|------|---------|------|
| 首页总览 | `/` | 数据状态 + 涨跌分布 + 模块入口 | 0.5天 |
| 因子选股 | `/factor` | 雷达图 + 评分表 + 行业筛选 | 1天 |
| 趋势预测 | `/predict` | K线图 + 预测线 + 评估指标 | 1天 |
| 异常检测 | `/anomaly` | 散点图 + K线标注 + 预警表 | 0.5天 |
| AI助手 | `/chat` | 对话气泡 + 股票选择 + 流式渲染 | 1天 |

### 6.2 首页总览设计

```
┌──────────────────────────────────────────────────────────┐
│  FinSight — A股智能投研分析平台                           │
├──────────┬───────────┬───────────┬──────────────────────┤
│ 上涨 24只 │ 下跌 23只 │ 平均涨跌  │ 数据截至 2026-06-01   │
│ 涨幅榜TOP │ 跌幅榜TOP │  +0.02%  │                      │
├──────────┴───────────┴───────────┴──────────────────────┤
│ ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│ │ 因子选股  │  │ 趋势预测  │  │ 异常检测  │  │ AI助手   │ │
│ │  进入 →  │  │  进入 →  │  │  进入 →  │  │  进入 →  │ │
│ └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
└──────────────────────────────────────────────────────────┘
```

---

## 七、后端API

```python
# ============ 行情 ============
GET  /api/market/indices          # 大盘指数（涨跌数量/涨幅榜/跌幅榜）
GET  /api/market/kline/{code}     # 个股K线数据
GET  /api/market/sectors          # 行业涨跌
GET  /api/market/stocks           # 股票列表

# ============ 因子选股 ============
GET  /api/factor/radar/{code}     # 个股因子雷达数据
GET  /api/factor/ranking          # 因子排名列表（支持行业筛选）
POST /api/factor/refresh          # 重新计算因子

# ============ LSTM预测 ============
POST /api/predict/train/{code}    # 触发训练
GET  /api/predict/result/{code}   # 获取预测结果
GET  /api/predict/models          # 已训练模型列表

# ============ 异常检测 ============
GET  /api/anomaly/detect          # 执行异常检测
GET  /api/anomaly/alerts          # 预警列表
GET  /api/anomaly/kline/{code}    # 带异常标注的K线数据

# ============ 数据管理 ============
POST /api/data/init               # 初始化数据（后台运行，立即返回）
GET  /api/data/init-status        # 初始化进度轮询
GET  /api/data/status             # 数据状态统计

# ============ AI 助手 ============
POST /api/chat/ask                # AI问答（同步）
POST /api/chat/ask-stream         # AI问答（SSE流式）
POST /api/chat/refresh-news/{code}# 刷新个股新闻舆情
GET  /api/chat/sentiment/{code}   # 情感统计摘要
```

> 共 **19个接口**，没有认证、没有WebSocket、没有分页。

---

## 八、项目目录结构

```
FinSight/
├── frontend/                        # 前端
│   ├── src/
│   │   ├── views/
│   │   │   ├── HomeView.vue         # 首页总览
│   │   │   ├── FactorView.vue       # 因子选股
│   │   │   ├── PredictView.vue      # 趋势预测
│   │   │   ├── AnomalyView.vue      # 异常检测
│   │   │   └── ChatView.vue         # AI投资助手
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
│   ├── main.py                      # FastAPI入口（所有路由集中于此）
│   ├── database.py                  # 数据库连接 + ORM模型
│   ├── config.py                    # 配置（数据库连接/API Key）
│   ├── data_fetcher.py              # BaoStock数据采集 + 增量更新
│   ├── tools.py                     # 工具函数（搜索/行情/因子/预测）
│   ├── factor_engine.py             # 多因子选股引擎
│   ├── lstm_model.py                # LSTM预测模型
│   ├── anomaly_detector.py          # 异常检测引擎
│   ├── news_fetcher.py              # 新闻采集 + SnowNLP情感分析
│   ├── sentiment_agent.py           # DeepSeek AI问答引擎
│   └── requirements.txt
│
├── data/                            # 数据目录（CSV备份）
│   └── README.md
│
├── init_db.sql                      # 建表脚本
├── finsight_data.sql                # 完整数据导出
└── README.md                        # 项目说明
```

---

## 九、7天开发计划（精确到小时）

### Day 1：环境搭建 + 数据入库（周一）

| 时段 | 任务 | 产出 |
|------|------|------|
| 上午 | Python环境 + MySQL建表 + BaoStock数据采集脚本 | `init_db.sql` + `data_fetcher.py` |
| 下午 | 采集沪深300近2年日K线数据，导入MySQL | 数据库有数据 |
| 晚上 | FastAPI骨架 + 数据库连通测试 | `main.py` + `database.py` + 行情接口 |

### Day 2：多因子选股模块（周二）

| 时段 | 任务 | 产出 |
|------|------|------|
| 上午 | 因子构建脚本：5维因子计算 + MAD去极值 + Z-Score标准化 | `factor_engine.py` |
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

### Day 5：异常检测 + AI助手（周五）

| 时段 | 任务 | 产出 |
|------|------|------|
| 上午 | Isolation Forest + K-Means聚类实现 | `anomaly_detector.py` |
| 下午 | 异常检测API + 前端散点图 + K线标注 | `/api/anomaly/*` + `AnomalyView.vue` |
| 晚上 | 新闻采集 + SnowNLP情感分析 + AI问答 | `news_fetcher.py` + `ChatView.vue` |

### Day 6：系统集成 + Bug修复（周六）

| 时段 | 任务 | 产出 |
|------|------|------|
| 上午 | 前后端联调，确保4个模块都能走通 | 可运行的完整系统 |
| 下午 | Bug修复（超时/数据缺失/流式渲染） | 稳定版 |
| 晚上 | 预录制演示视频（防答辩时翻车） | demo.mp4 |

### Day 7：文档 + 答辩准备（周日）

| 时段 | 任务 | 产出 |
|------|------|------|
| 上午 | README文档 + 代码注释补充 | 完整项目文档 |
| 下午 | 答辩PPT（重点：3个算法 + AI创新点） | 答辩PPT |
| 晚上 | 演示排练 | 自信答辩 |

---

## 十、课程考核点覆盖

| 课程要求 | 模块 | 具体实现 |
|---------|------|---------|
| **数据预处理** | 全模块 | 缺失值填充、MAD去极值、Z-Score标准化、滑动窗口 |
| **分类算法** | 因子选股 | 按综合评分Top N选股（二分类：入选/未入选） |
| **回归预测** | LSTM | 时序回归预测下一日收盘价，MAE/RMSE评估 |
| **聚类算法** | 异常检测 | K-Means将交易模式分为3类 |
| **异常检测** | 异常检测 | Isolation Forest检测异常交易日 |
| **NLP文本挖掘** | AI助手 | SnowNLP情感分析 + DeepSeek大模型问答 |
| **可视化** | 前端 | 雷达图、K线图、散点图（3种ECharts图表） |
| **系统实现** | 全栈 | 前后端分离Web应用 |

---

## 十一、数据获取方案

| 数据 | 数据源 | 获取方式 | 频率 |
|------|--------|---------|------|
| 日K线 | BaoStock | `bs.query_history_k_data_plus()` | 增量更新（每日） |
| 股票列表 | BaoStock | `bs.query_hs300_stocks()` | 每月 |
| 股票信息 | BaoStock | `bs.query_stock_basic()` | 首次采集 |
| 财经新闻 | AKShare | `ak.stock_news_em(symbol)` | 实时拉取（用户查询时） |

**首次数据采集（BaoStock）：**

```python
import baostock as bs
import pandas as pd
from sqlalchemy import create_engine

engine = create_engine("mysql+pymysql://root:password@localhost:3306/finsight")

# 1. 登录BaoStock
lg = bs.login()
# 2. 获取沪深300成分股
hs300 = bs.query_hs300_stocks()
stock_list = hs300.get_data()

# 3. 批量采集日K线（约5分钟）
for code in stock_list['code'].tolist()[:50]:
    try:
        rs = bs.query_history_k_data_plus(
            code, "date,open,close,high,low,volume,amount,turn,pctChg",
            start_date="2023-01-01", end_date="2026-12-31",
            frequency="d", adjustflag="3"
        )
        df = rs.get_data()
        df['ts_code'] = code  # 转为 ts_code 格式
        df.to_sql('stock_daily', engine, if_exists='append', index=False)
    except Exception as e:
        print(f"{code} 采集失败: {e}")

bs.logout()
```

**增量更新（每日收盘后）：**

```python
# init_data() 自动检查每只股票的最新交易日
# 只拉取缺失日期段的数据，已有数据不重复采集
today = date.today().strftime("%Y-%m-%d")
last_date = get_last_trade_date(code)   # 从数据库查询
start_date = last_date + 1 day          # 只拉取缺失部分
```

---

## 十二、答辩策略

### 核心话术（1分钟开场）

> 我们的项目叫 FinSight，是一个 A股智能投研分析平台。包含**三个核心数据挖掘模块**——多因子选股、LSTM趋势预测、异常交易检测——形成"选股-预测-预警"的投研闭环。此外还集成了**DeepSeek AI投资助手**，支持自然语言问答。数据源采用 BaoStock（专为量化设计的稳定API）。

### 演示顺序（5分钟）

1. **首页** — 数据状态 + 涨跌分布（证明数据是真实A股行情）
2. **因子选股** — 选一只股票看雷达图，展示Top20排名
3. **趋势预测** — 点"训练"，等待几秒，K线图上出现预测虚线
4. **异常检测** — 散点图红色标注异常点 + K线标注
5. **AI助手** — 提问"帮我分析茅台最近走势"，展示流式回答 + 新闻情感

### 老师可能问的问题

| 问题 | 回答要点 |
|------|---------|
| 为什么选LSTM不用Transformer？ | LSTM对短序列时序预测够用，训练快，一周内可完成 |
| 因子选股的IC值是多少？ | （实际跑出来填）展示IC时序图 |
| 异常检测的contamination为什么设0.05？ | A股异常交易日约占5%，与Isolation Forest默认值一致 |
| 数据源为什么用BaoStock？ | 比AKShare更稳定，专为量化设计的API，无爬虫被封风险 |
| 大模型是怎么接进来的？ | 通过OpenAI SDK调用DeepSeek API，新闻情感数据作为上下文 |
| 前后端怎么通信的？ | FastAPI提供REST API + SSE流式，前端Axios/Fetch调用 |

---

## 十三、风险与对策

| 风险 | 概率 | 对策 |
|------|------|------|
| BaoStock查询限速 | 低 | 采集脚本已有重试机制，每次请求间隔2秒 |
| LSTM训练时间过长 | 低 | 只训练单只股票，序列长度限制20日 |
| DeepSeek API不可用 | 低 | 前端有超时处理+错误提示，不影响核心模块 |
| 前端Vue不熟 | 中 | 用最简单的组合式API，不搞Pinia状态管理 |
| MySQL连不上 | 低 | 可通过 config.py 快速切换连接配置 |
| 答辩时网络不通 | 中 | 提前录制演示视频 + 缓存数据到本地 |

---

*本方案专为一周速通设计，核心原则：能跑通 > 完美 > 功能多*
