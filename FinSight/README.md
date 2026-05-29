# FinSight - A股智能投研分析平台

> 《金融数据挖掘课程设计》项目 | 数据科学与大数据技术专业

## 快速启动

### 1. 初始化数据库

```bash
# 创建数据库和表
mysql -u root -p < init_db.sql
```

### 2. 后端启动

```bash
cd backend

# 安装依赖
pip install -r requirements.txt

# 修改数据库连接（如需要）
# 编辑 config.py 中的 DB_PASSWORD 等

# 启动后端
python main.py
```

后端运行在 http://localhost:8000，API文档在 http://localhost:8000/docs

### 3. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端运行在 http://localhost:3000

### 4. 首次使用

1. 打开 http://localhost:3000
2. 点击"初始化数据"按钮（采集A股数据，约3-5分钟）
3. 数据采集完成后即可使用三大模块

## 项目结构

```
FinSight/
├── backend/                    # 后端 (FastAPI)
│   ├── main.py                # API入口（15个接口）
│   ├── config.py              # 配置文件
│   ├── database.py            # 数据库连接 + ORM模型
│   ├── data_fetcher.py        # AKShare数据采集
│   ├── factor_engine.py       # 多因子选股引擎
│   ├── lstm_model.py          # LSTM预测模型
│   ├── anomaly_detector.py    # 异常检测引擎
│   └── requirements.txt       # Python依赖
├── frontend/                   # 前端 (Vue 3)
│   ├── src/
│   │   ├── views/             # 4个页面
│   │   ├── components/        # 3个图表组件
│   │   ├── api/               # API封装
│   │   └── router/            # 路由
│   └── package.json
├── init_db.sql                 # 数据库建表脚本
└── README.md
```

## 三大核心模块

### 1. 多因子选股
- **算法：** MAD去极值 + Z-Score标准化 + 等权合成
- **因子：** 价值/成长/质量/动量/波动 五维因子体系
- **可视化：** 因子雷达图 + 排名表

### 2. LSTM趋势预测
- **算法：** 单层LSTM + 滑动窗口 + Walk-Forward验证
- **输入：** 过去20日(收盘价, 成交量)序列
- **输出：** 未来N日收盘价预测
- **评估：** MAE / RMSE / 方向准确率

### 3. 异常交易检测
- **算法：** Isolation Forest + K-Means 双引擎
- **特征：** 换手率/涨跌幅/成交量比/振幅
- **可视化：** 散点图(正常灰/异常红) + K线异常标注

## 数据挖掘考核点覆盖

| 考核点 | 模块 |
|--------|------|
| 数据预处理 | 全模块（去极值MAD/标准化Z-Score/滑动窗口） |
| 分类算法 | 因子选股（评分Top N选股） |
| 回归预测 | LSTM价格预测 |
| 聚类算法 | 异常检测（K-Means交易模式聚类） |
| 异常检测 | Isolation Forest + Z-Score |
| 可视化 | 雷达图/K线图/散点图/热力图 |
| 系统实现 | 前后端分离Web应用 |
