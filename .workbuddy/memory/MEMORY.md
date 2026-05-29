# MEMORY.md - 长期记忆

## 用户背景
- 关注K12教育信息化，熟悉高中学段管理逻辑
- 正在开发中国高中生管理系统（MySQL + MCP架构）
- 风格：干练简洁，方案确认后期待AI自主执行
- 本地MySQL: root@localhost:3306, 密码 MAMA5202.qq, 数据库 feishu_test（高中生系统）+ finsight（金融项目）

## 项目记录

### FinSight - A股智能投研分析平台 (2026-05-28)
- 《金融数据挖掘课程设计》项目，一周速通版
- 对象：数据科学与大数据技术专业大三学生，开发时间1周
- 3个核心挖掘模块：多因子选股 / LSTM预测 / 异常检测（+ SnowNLP舆情为加分项）
- 技术栈精简：Vue 3 + FastAPI + Scikit-learn + PyTorch + AKShare + MySQL
- 后端6个Python文件，前端4个页面，7天精确到半天的开发计划
- 方案书路径：C:\Users\fanghongjiang\WorkBuddy\2026-05-28-14-49-49\FinSight_项目方案书.md
- 后端已启动验证通过：FastAPI @ localhost:8000, Python venv @ .workbuddy\binaries\python\envs\finsight\
- 数据库5张表已建好，50只沪深300成分股4926条K线已入库
- 代码字段已统一为ts_code/name/vol/pct_chg
- 已修复：Vite代理IPv6问题（target改127.0.0.1）、中文引号编译错误、ElMessage未导入
- 已改造：因子选股+趋势预测页面的股票输入改为el-select+filterable可搜索下拉框
- 前端API新增：getStockList（/api/market/stocks）
- 已修复：预测线残留问题——训练后不再自动显示回测预测线，点击"预测未来价格"后才显示；切换股票时清空所有预测数据
- 后端端口从8000改为8001（避免TIME_WAIT），前端vite代理同步改为8001
- 已修复：万科A训练500错误——train_model/predict_next加try/except，Vite代理加timeout:120000
- 启动脚本：start.bat / start-backend.bat / start-frontend.bat（路径：FinSight/目录下）
- 已修复：bat脚本中文乱码——文件名+内容全部改为英文，路径改用绝对路径（避免%~dp0在含中文路径下乱码）
- 注意：run_in_background启动的进程会超时回收，长期运行需用bat脚本或Start-Process
