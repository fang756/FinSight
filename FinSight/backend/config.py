"""
FinSight 配置文件
"""
import os

# ============ 数据库配置 ============
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "MAMA5202.qq")
DB_NAME = os.getenv("DB_NAME", "finsight")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

# ============ AKShare 数据采集配置 ============
# 采集的股票范围: 沪深300前50只（够用且采集快）
STOCK_COUNT = int(os.getenv("STOCK_COUNT", 50))
# 历史数据起始日期
DATA_START_DATE = os.getenv("DATA_START_DATE", "2023-01-01")
DATA_END_DATE = os.getenv("DATA_END_DATE", "20261231")

# ============ LSTM 模型配置 ============
LSTM_SEQUENCE_LENGTH = 20      # 输入序列长度（过去20个交易日）
LSTM_HIDDEN_SIZE = 64          # 隐藏层维度
LSTM_NUM_LAYERS = 1            # LSTM层数
LSTM_EPOCHS = 50               # 训练轮数
LSTM_LEARNING_RATE = 0.001     # 学习率
LSTM_TRAIN_RATIO = 0.8         # 训练集比例

# ============ 异常检测配置 ============
ANOMALY_CONTAMINATION = 0.05   # Isolation Forest 异常比例
KMEANS_N_CLUSTERS = 3          # K-Means 聚类数

# ============ 因子选股配置 ============
FACTOR_MAD_SCALE = 1.4826      # MAD去极值缩放因子(1.4826使得MAD与标准差等价)
FACTOR_CLIP_SIGMA = 3          # 超过3倍MAD的截断

# 股票行业映射（课程设计简化版，AKShare行业接口不稳定）
STOCK_INDUSTRY_MAP = {
    "000001.SZ": "银行", "000002.SZ": "房地产", "000063.SZ": "通信设备",
    "000333.SZ": "家电", "000338.SZ": "汽车零部件", "000425.SZ": "工程机械",
    "000568.SZ": "白酒", "000625.SZ": "汽车整车", "000651.SZ": "家电",
    "000858.SZ": "白酒", "000895.SZ": "食品加工", "000938.SZ": "IT服务",
    "001979.SZ": "房地产", "002001.SZ": "化学制品", "002007.SZ": "生物制品",
    "002024.SZ": "零售", "002027.SZ": "广告营销", "002049.SZ": "半导体",
    "002120.SZ": "物流", "002142.SZ": "银行", "002230.SZ": "软件开发",
    "002241.SZ": "消费电子", "002304.SZ": "白酒", "002352.SZ": "物流",
    "002415.SZ": "安防设备", "002460.SZ": "能源金属", "002475.SZ": "消费电子",
    "002493.SZ": "炼化", "002555.SZ": "游戏", "002594.SZ": "汽车整车",
    "002601.SZ": "化学制品", "002607.SZ": "教育", "002709.SZ": "电池",
    "002714.SZ": "养殖", "002736.SZ": "证券", "002812.SZ": "电池",
    "002841.SZ": "消费电子", "003816.SZ": "电力", "600000.SH": "银行",
    "600009.SH": "机场", "600010.SH": "钢铁", "600011.SH": "电力",
    "600016.SH": "银行", "600019.SH": "钢铁", "600025.SH": "电力",
    "600028.SH": "炼化", "600029.SH": "航空", "600030.SH": "证券",
    "600031.SH": "工程机械", "600036.SH": "银行", "600519.SH": "白酒",
}

# ============ DeepSeek AI 配置 ============
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
