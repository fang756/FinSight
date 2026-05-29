"""
FinSight LSTM 价格趋势预测模型
数据挖掘考点：时序建模、深度学习、滑动窗口、Walk-Forward验证、过拟合控制
"""
import os
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import text
from database import engine
from config import (LSTM_SEQUENCE_LENGTH, LSTM_HIDDEN_SIZE, LSTM_NUM_LAYERS,
                    LSTM_EPOCHS, LSTM_LEARNING_RATE, LSTM_TRAIN_RATIO)


# ============ 模型定义 ============

class LSTMModel(nn.Module):
    """
    单层LSTM回归模型
    输入：过去N日的 (收盘价, 成交量) 序列
    输出：下一日收盘价
    """
    def __init__(self, input_size=2, hidden_size=LSTM_HIDDEN_SIZE,
                 num_layers=LSTM_NUM_LAYERS):
        super().__init__()
        # dropout只在num_layers>1时有效
        dropout = 0.1 if num_layers > 1 else 0
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers,
                            batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        out, (h_n, c_n) = self.lstm(x)
        out = self.fc(out[:, -1, :])
        return out.squeeze(-1)


# ============ 数据集构建 ============

def prepare_dataset(ts_code: str, seq_length: int = LSTM_SEQUENCE_LENGTH):
    """
    从数据库读取K线数据，构建滑动窗口数据集
    """
    df = pd.read_sql(text("""
        SELECT trade_date, close, vol
        FROM stock_daily
        WHERE ts_code = :code
        ORDER BY trade_date ASC
    """), engine, params={"code": ts_code})

    if len(df) < seq_length + 10:
        return None

    close_prices = df["close"].values.astype(float).reshape(-1, 1)
    volumes = df["vol"].values.astype(float).reshape(-1, 1)
    dates = df["trade_date"].values

    # 归一化
    scaler_close = MinMaxScaler()
    scaler_volume = MinMaxScaler()
    close_scaled = scaler_close.fit_transform(close_prices)
    volume_scaled = scaler_volume.fit_transform(volumes)

    # 合并特征: [close, volume]
    features = np.hstack([close_scaled, volume_scaled])

    # 滑动窗口切分
    X, y, y_dates = [], [], []
    for i in range(len(features) - seq_length):
        X.append(features[i:i + seq_length])
        y.append(close_scaled[i + seq_length, 0])
        y_dates.append(dates[i + seq_length])

    X = np.array(X, dtype=np.float32)
    y = np.array(y, dtype=np.float32)

    # 划分训练/测试集
    split_idx = int(len(X) * LSTM_TRAIN_RATIO)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    dates_test = y_dates[split_idx:]

    return X_train, y_train, X_test, y_test, scaler_close, dates_test


# ============ 训练 ============

def train_model(ts_code: str, epochs: int = LSTM_EPOCHS) -> dict:
    """训练LSTM模型并返回结果"""
    try:
        data = prepare_dataset(ts_code)
        if data is None:
            return {"success": False, "message": f"股票 {ts_code} 数据不足"}

        X_train, y_train, X_test, y_test, scaler_close, dates_test = data

        X_train_t = torch.FloatTensor(X_train)
        y_train_t = torch.FloatTensor(y_train)
        X_test_t = torch.FloatTensor(X_test)
        y_test_t = torch.FloatTensor(y_test)

        model = LSTMModel()
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=LSTM_LEARNING_RATE)

        model.train()
        losses = []
        for epoch in range(epochs):
            optimizer.zero_grad()
            output = model(X_train_t)
            loss = criterion(output, y_train_t)
            loss.backward()
            optimizer.step()
            losses.append(loss.item())

        model.eval()
        with torch.no_grad():
            test_pred = model(X_test_t).numpy()

        # 反归一化
        y_test_real = scaler_close.inverse_transform(y_test.reshape(-1, 1)).flatten()
        test_pred_real = scaler_close.inverse_transform(test_pred.reshape(-1, 1)).flatten()

        # 计算指标
        mae = np.mean(np.abs(y_test_real - test_pred_real))
        rmse = np.sqrt(np.mean((y_test_real - test_pred_real) ** 2))
        direction_correct = np.mean(
            np.sign(y_test_real[1:] - y_test_real[:-1]) ==
            np.sign(test_pred_real[1:] - test_pred_real[:-1])
        )

        # 保存模型
        save_dir = os.path.join(os.path.dirname(__file__), "..", "saved_models")
        os.makedirs(save_dir, exist_ok=True)
        # 文件名中的点替换为下划线避免扩展名问题
        safe_name = ts_code.replace(".", "_")
        model_path = os.path.join(save_dir, f"lstm_{safe_name}.pt")
        torch.save({
            "model_state": model.state_dict(),
            "scaler_close": scaler_close,
            "seq_length": LSTM_SEQUENCE_LENGTH,
            "ts_code": ts_code,
        }, model_path)

        # 构建预测结果
        predictions = []
        for i, date in enumerate(dates_test):
            predictions.append({
                "date": str(date),
                "actual": round(float(y_test_real[i]), 2),
                "predicted": round(float(test_pred_real[i]), 2),
            })

        return {
            "success": True,
            "message": f"模型训练完成，共{epochs}轮",
            "metrics": {
                "mae": round(float(mae), 4),
                "rmse": round(float(rmse), 4),
                "direction_accuracy": round(float(direction_correct), 4),
                "final_loss": round(float(losses[-1]), 6),
            },
            "predictions": predictions,
        }
    except Exception as e:
        return {"success": False, "message": f"训练异常: {str(e)}"}


# ============ 预测 ============

def predict_next(ts_code: str, days: int = 5) -> dict:
    """使用已训练模型预测未来N日价格"""
    try:
        save_dir = os.path.join(os.path.dirname(__file__), "..", "saved_models")
        safe_name = ts_code.replace(".", "_")
        model_path = os.path.join(save_dir, f"lstm_{safe_name}.pt")

        if not os.path.exists(model_path):
            return {"success": False, "message": f"股票 {ts_code} 模型未训练，请先训练"}

        checkpoint = torch.load(model_path, map_location="cpu", weights_only=False)
        scaler_close = checkpoint["scaler_close"]
        seq_length = checkpoint["seq_length"]

        model = LSTMModel()
        model.load_state_dict(checkpoint["model_state"])
        model.eval()

        df = pd.read_sql(text("""
            SELECT close, vol
            FROM stock_daily
            WHERE ts_code = :code
            ORDER BY trade_date DESC
            LIMIT :limit
        """), engine, params={"code": ts_code, "limit": seq_length + 10})

        if len(df) < seq_length:
            return {"success": False, "message": "数据不足"}

        df = df.sort_index(ascending=False).head(seq_length)
        close_prices = df["close"].values.astype(float).reshape(-1, 1)
        volumes = df["vol"].values.astype(float).reshape(-1, 1)

        vol_scaler = MinMaxScaler()
        close_scaled = scaler_close.transform(close_prices)
        vol_scaled = vol_scaler.fit_transform(volumes)

        features = np.hstack([close_scaled, vol_scaled]).astype(np.float32)
        input_seq = torch.FloatTensor(features).unsqueeze(0)

        predictions = []
        current_input = input_seq.clone()
        with torch.no_grad():
            for d in range(days):
                pred = model(current_input)
                pred_value = scaler_close.inverse_transform(
                    pred.numpy().reshape(-1, 1)
                )[0, 0]
                predictions.append({
                    "day": d + 1,
                    "predicted_price": round(float(pred_value), 2),
                })
                new_step = torch.FloatTensor([[
                    [float(pred.numpy()[0]), vol_scaled[-1, 0]]
                ]])
                current_input = torch.cat([current_input[:, 1:, :], new_step], dim=1)

        return {
            "success": True,
            "ts_code": ts_code,
            "predictions": predictions,
        }
    except Exception as e:
        return {"success": False, "message": f"预测异常: {str(e)}"}


def get_trained_models() -> list:
    """获取已训练的模型列表"""
    save_dir = os.path.join(os.path.dirname(__file__), "..", "saved_models")
    if not os.path.exists(save_dir):
        return []

    models = []
    for f in os.listdir(save_dir):
        if f.startswith("lstm_") and f.endswith(".pt"):
            # 还原ts_code: lstm_000001_SZ.pt → 000001.SZ
            code = f.replace("lstm_", "").replace(".pt", "")
            ts_code = code.replace("_", ".")
            models.append({"ts_code": ts_code, "model_file": f})
    return models
