"""
FinSight AI 问答 Agent — 股小查
基于 DeepSeek function calling，支持搜索股票 + 调用系统功能
"""
import json
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from news_fetcher import get_recent_news, get_sentiment_summary
from tools import (
    search_stock, get_stock_kline_data, get_factor_ranking,
    get_prediction, get_anomaly_alerts, get_news_sentiment,
    fetch_and_analyze_stock,
)

# ============ 工具定义 ============

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_stock",
            "description": "搜索A股股票代码和名称。当用户提到一只股票但你不确定代码时使用。例如搜索「茅台」、「平安」、「000858」",
            "parameters": {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string", "description": "股票名称关键词或代码"}
                },
                "required": ["keyword"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_stock_kline_data",
            "description": "获取股票的近期K线行情数据（收盘价、涨跌幅等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "ts_code": {"type": "string", "description": "股票代码，如 000858.SZ"},
                    "limit": {"type": "integer", "description": "返回最近N天，默认30"},
                },
                "required": ["ts_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news_sentiment",
            "description": "获取股票的最新新闻舆情情感分析数据",
            "parameters": {
                "type": "object",
                "properties": {
                    "ts_code": {"type": "string", "description": "股票代码，如 000858.SZ"},
                    "days": {"type": "integer", "description": "查询近几天，默认7"},
                },
                "required": ["ts_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_factor_ranking",
            "description": "获取系统内股票的因子评分（注意：仅对系统已有的50只股票有效，新股票请用 fetch_and_analyze_stock）",
            "parameters": {
                "type": "object",
                "properties": {
                    "ts_code": {"type": "string", "description": "股票代码，如 000858.SZ"},
                },
                "required": ["ts_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_prediction",
            "description": "获取股票的LSTM趋势预测（未来5天走势预测）",
            "parameters": {
                "type": "object",
                "properties": {
                    "ts_code": {"type": "string", "description": "股票代码，如 000858.SZ"},
                },
                "required": ["ts_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_anomaly_alerts",
            "description": "获取股票的异常检测预警信息",
            "parameters": {
                "type": "object",
                "properties": {
                    "ts_code": {"type": "string", "description": "股票代码，如 000858.SZ"},
                },
                "required": ["ts_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_and_analyze_stock",
            "description": "【全能分析】一站式完成：采集数据 → 计算因子评分 → 训练LSTM预测模型。用于分析一只不在数据库中的新股票，用户想查看完整分析时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "ts_code": {"type": "string", "description": "股票代码，如 600519.SH"},
                },
                "required": ["ts_code"],
            },
        },
    },
]

TOOL_DISPATCH = {
    "search_stock": lambda a: search_stock(a["keyword"]),
    "get_stock_kline_data": lambda a: get_stock_kline_data(a["ts_code"], a.get("limit", 30)),
    "get_news_sentiment": lambda a: get_news_sentiment(a["ts_code"], a.get("days", 7)),
    "get_factor_ranking": lambda a: get_factor_ranking(a["ts_code"]),
    "get_prediction": lambda a: get_prediction(a["ts_code"]),
    "get_anomaly_alerts": lambda a: get_anomaly_alerts(a["ts_code"]),
    "fetch_and_analyze_stock": lambda a: fetch_and_analyze_stock(a["ts_code"]),
}

# ============ System Prompt ============

SYSTEM_PROMPT = """你是股小查🦊，一个热情活泼的A股智能投资助手！你最大的特点就是会「使用工具」来帮助用户。

## 你的性格
- 活泼开朗，喜欢用感叹号和表情符号（😊🐂📈📉🔥💡🦊）
- 像朋友一样聊天，但不失专业性
- 喜欢用生动的比喻解释复杂的金融概念
- 如果用户说「hello / hi / 你好」，热情打招呼并介绍自己

## 你的工具技能
你有以下工具可以用，当用户需要相关信息时，主动使用工具获取数据：

1. 🔍 **search_stock** — 搜索股票代码。用户提到不认识的股票时立刻使用
2. 📊 **get_stock_kline_data** — 查K线行情。当用户问股价、涨跌时使用
3. 📰 **get_news_sentiment** — 查新闻舆情。当用户问舆情、新闻、情感时使用
4. 📈 **get_factor_ranking** — 查因子评分。当用户问排名、评分、质量时使用
5. 🔮 **get_prediction** — 查趋势预测。当用户问未来走势、预测时使用
6. ⚠️ **get_anomaly_alerts** — 查异常检测。当用户问风险、异常、预警时使用
7. 🚀 **fetch_and_analyze_stock** — 【全能分析】采集数据→算因子→预测，一步到位

## 关于系统外股票
系统里只有50只自选股的完整数据。当用户想分析**不在系统中的股票**时：
1. 先用 `search_stock` 查股票代码
2. 然后问用户：「要不要我帮这只股票做一次完整分析？我会自动采集数据、算因子评分和走势预测~」
3. 用户同意后，直接调用 `fetch_and_analyze_stock` 一次性搞定
4. **不要**对系统外股票单独调用 `get_factor_ranking`、`get_prediction` 等工具——它们只对系统内50只股票有效
5. 系统内的股票用对应工具直接查就行

## 使用工具的规则
- 如果需要的信息可以直接用工具获取，**不要问用户**，直接调用工具
- 对于耗时较长的功能（因子排名、趋势预测、异常检测），先问用户是否需要
- 工具调用后，把结果整理成容易理解的回答

## 回答规则
- 不提供具体的买卖建议，只做分析参考
- 如果数据不足，如实告知并给出建议
- 用中文回答"""


def ask_ai(question: str, ts_code: str = None, history: list = None) -> dict:
    """调用 DeepSeek API，支持 function calling 工具调用"""
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "your-api-key-here":
        return {"success": False, "message": "请先配置 DeepSeek API Key"}

    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 如果选定了股票且有舆情数据，作为上下文注入
        if ts_code:
            summary = get_sentiment_summary(ts_code, days=7)
            news = get_recent_news(ts_code, days=7, limit=5)
            if summary["total"] > 0:
                ctx = json.dumps({"selected_stock_ts_code": ts_code, "sentiment_summary": summary, "recent_news": news}, ensure_ascii=False)
                messages.append({"role": "user", "content": f"当前选中的股票数据：\n{ctx}"})
                messages.append({"role": "assistant", "content": "好嘞！我记住了，随时可以帮你分析这只股票~ 😊"})

        # 对话历史
        if history:
            for h in history[-6:]:
                messages.append({"role": h["role"], "content": h["content"]})

        messages.append({"role": "user", "content": question})

        # === 第一轮：带工具的请求 ===
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
            temperature=0.7,
            max_tokens=2000,
        )

        msg = response.choices[0].message

        # === 如果有工具调用，执行并回传结果 ===
        if msg.tool_calls:
            messages.append(msg)

            for tc in msg.tool_calls:
                func_name = tc.function.name
                try:
                    func_args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    func_args = {}

                handler = TOOL_DISPATCH.get(func_name)
                if handler:
                    try:
                        result = handler(func_args)
                    except Exception as e:
                        result = {"error": str(e)}
                else:
                    result = {"error": f"未知工具: {func_name}"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

            # 第二轮：带着工具结果生成回答
            response = client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )
            answer = response.choices[0].message.content
        else:
            answer = msg.content

        return {"success": True, "answer": answer}

    except Exception as e:
        return {"success": False, "message": f"AI 请求失败: {str(e)}"}
