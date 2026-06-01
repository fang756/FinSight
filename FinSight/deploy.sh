#!/bin/bash
# FinSight 一键部署脚本
set -e

echo "========================================="
echo "  FinSight 部署脚本"
echo "========================================="

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 1. 拉取最新代码
echo "[1/5] 拉取最新代码..."
git pull origin master

# 2. 安装 Python 依赖
echo "[2/5] 安装 Python 依赖..."
cd backend
pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
cd ..

# 3. 安装前端依赖并构建
echo "[3/5] 构建前端..."
cd frontend
npm install --registry=https://registry.npmmirror.com
npm run build
cd ..

# 4. 提示数据库配置
echo ""
echo "[4/5] 数据库检查"
echo "确保 MySQL 中已存在 finsight 数据库，且 finsight_data.sql 已导入。"
echo "如需修改数据库连接，请编辑 backend/config.py 中的 DB_* 配置。"
echo ""

# 5. 启动服务
echo "[5/5] 启动服务..."
PORT=8003

# 检查端口是否被占用
OLD_PID=$(lsof -ti :$PORT 2>/dev/null || true)
if [ -n "$OLD_PID" ]; then
    echo "  端口 $PORT 已被占用，停止旧进程 (PID: $OLD_PID)..."
    kill -9 $OLD_PID 2>/dev/null || true
    sleep 1
fi

cd backend
nohup python -m uvicorn main:app --host 0.0.0.0 --port $PORT > ../finsight.log 2>&1 &
PID=$!
cd ..

sleep 2

# 检查是否启动成功
if kill -0 $PID 2>/dev/null; then
    echo ""
    echo "========================================="
    echo "  部署完成！"
    echo "  访问地址: http://118.31.221.240:$PORT"
    echo "  日志文件: finsight.log"
    echo "  停止服务: kill $PID"
    echo ""
    echo "  ⚠️ 阿里云安全组需要放行端口 $PORT"
    echo "  操作路径: 阿里云控制台 → 安全组 → 添加规则"
    echo "  入方向: TCP/$PORT, 源: 0.0.0.0/0"
    echo "========================================="
else
    echo "❌ 启动失败，请检查 logs: cat finsight.log"
    exit 1
fi