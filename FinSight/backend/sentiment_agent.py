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
系统里只有50只自选股的**因子评分、LSTM预测、异常检测**数据。
但以下工具**所有A股都支持**（会自动从网络实时拉取）：

- ✅ **search_stock** — 搜索任何A股
- ✅ **get_stock_kline_data** — 查任何股票的K线行情（实时）
- ✅ **get_news_sentiment** — 查任何股票的新闻舆情（**实时拉取**）

所以当用户提到一只不在系统里的股票时：
1. 先用 `search_stock` 查股票代码
2. 直接用 `get_stock_kline_data` 和 `get_news_sentiment` 查行情和新闻（**不用问用户**）
3. 如果想看因子评分、趋势预测、异常检测 → 问用户是否要做**完整分析**
4. 用户同意后，调用 `fetch_and_analyze_stock` 一次性搞定

## 使用工具的规则
- 如果需要的信息可以直接用工具获取，**不要问用户**，直接调用工具
- 对于耗时较长的功能（因子排名、趋势预测、异常检测），先问用户是否需要
- 工具调用后，把结果整理成容易理解的回答

## 回答规则
- **只回答与A股、股票投资、金融相关的问题**，对于非股票相关问题（如天气、科技、生活等），礼貌拒绝：「不好意思，我是专注于A股投资的智能助手，这方面的问题我没法帮你回答哦😊 你可以问我关于股票行情、新闻、分析方面的问题~」
- 不提供具体的买卖建议，只做分析参考
- 如果数据不足，如实告知并给出建议
- 用中文回答
- **重要：调用工具时必须用 JSON function calling，不要输出 <tool_calls> XML 标签**"""


def ask_ai(question: str, ts_code: str = None, history: list = None) -> dict:
    """调用 DeepSeek API，支持 function calling 工具调用"""
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "your-api-key-here":
        return {"success": False, "message": "请先配置 DeepSeek API Key"}

    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # 如果选定了股票，自动拉取最新新闻并注入上下文
        if ts_code:
            try:
                from news_fetcher import fetch_news, save_news_to_db
                df = fetch_news(ts_code)
                if not df.empty:
                    save_news_to_db(ts_code)
            except Exception:
                pass
            summary = get_sentiment_summary(ts_code, days=7)
            news = get_recent_news(ts_code, days=7, limit=5)
            ctx = json.dumps({"selected_stock_ts_code": ts_code, "sentiment_summary": summary, "recent_news": news}, ensure_ascii=False)
            messages.append({"role": "user", "content": f"当前选中的股票数据：\n{ctx}"})
            messages.append({"role": "assistant", "content": "好嘞！我记住了，随时可以帮你分析这只股票~ 😊"})

        # 对话历史
        if history:
            for h in history[-6:]:
                messages.append({"role": h["role"], "content": h["content"]})

        messages.append({"role": "user", "content": question})

        # === 循环处理（每轮都传 tools，让模型始终能用 JSON function calling）===
        max_rounds = 5
        for _round in range(max_rounds):
            kwargs = {"model": DEEPSEEK_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 2000, "tools": TOOL_DEFINITIONS, "tool_choice": "auto"}

            response = client.chat.completions.create(**kwargs)
            msg = response.choices[0].message

            has_json_calls = msg.tool_calls and len(msg.tool_calls) > 0
            text_calls = _parse_text_tool_calls(msg.content or "")

            if has_json_calls:
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
            elif text_calls:
                text_msg = {"role": "assistant", "content": msg.content}
                messages.append(text_msg)
                for func_name, func_args in text_calls:
                    handler = TOOL_DISPATCH.get(func_name)
                    if handler:
                        try:
                            result = handler(func_args)
                        except Exception as e:
                            result = {"error": str(e)}
                    else:
                        result = {"error": f"未知工具: {func_name}"}
                    messages.append({
                        "role": "user",
                        "content": f"工具 {func_name} 返回结果：{json.dumps(result, ensure_ascii=False)}",
                    })
            else:
                clean = _strip_xml_tool_tags(msg.content or "")
                return {"success": True, "answer": clean}

        answer = msg.content or "（处理超时，请重试）"
        return {"success": True, "answer": _strip_xml_tool_tags(answer)}

    except Exception as e:
        return {"success": False, "message": f"AI 请求失败: {str(e)}"}


def ask_ai_stream(question: str, ts_code: str = None, history: list = None):
    """流式版：先静默完成工具调用，最终回答流式输出（SSE）"""
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "your-api-key-here":
        yield f"data: {json.dumps({'error': '请先配置 DeepSeek API Key'}, ensure_ascii=False)}\n\n"
        return

    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        if ts_code:
            try:
                from news_fetcher import fetch_news, save_news_to_db
                df = fetch_news(ts_code)
                if not df.empty:
                    save_news_to_db(ts_code)
            except Exception:
                pass
            summary = get_sentiment_summary(ts_code, days=7)
            news = get_recent_news(ts_code, days=7, limit=5)
            ctx = json.dumps({"selected_stock_ts_code": ts_code, "sentiment_summary": summary, "recent_news": news}, ensure_ascii=False)
            messages.append({"role": "user", "content": f"当前选中的股票数据：\n{ctx}"})
            messages.append({"role": "assistant", "content": "好嘞！我记住了，随时可以帮你分析这只股票~ 😊"})

        if history:
            for h in history[-6:]:
                messages.append({"role": h["role"], "content": h["content"]})

        messages.append({"role": "user", "content": question})

        # === Phase 1: 工具调用轮次（非流式，静默处理） ===
        max_rounds = 5
        for _round in range(max_rounds):
            kwargs = {"model": DEEPSEEK_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 2000, "tools": TOOL_DEFINITIONS, "tool_choice": "auto"}
            response = client.chat.completions.create(**kwargs)
            msg = response.choices[0].message

            has_json_calls = msg.tool_calls and len(msg.tool_calls) > 0
            text_calls = _parse_text_tool_calls(msg.content or "")

            if has_json_calls:
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
            elif text_calls:
                messages.append({"role": "assistant", "content": msg.content})
                for func_name, func_args in text_calls:
                    handler = TOOL_DISPATCH.get(func_name)
                    if handler:
                        try:
                            result = handler(func_args)
                        except Exception as e:
                            result = {"error": str(e)}
                    else:
                        result = {"error": f"未知工具: {func_name}"}
                    messages.append({
                        "role": "user",
                        "content": f"工具 {func_name} 返回结果：{json.dumps(result, ensure_ascii=False)}",
                    })
            else:
                # 无工具调用 → 开始流式输出最终回答
                break
        else:
            _round = max_rounds  # 超出最大轮次

        # === Phase 2: 流式输出最终回答 ===
        if _round >= max_rounds:
            # 超时，回退到非流式
            final_text = msg.content or "（处理超时，请重试）"
            for chunk_start in range(0, len(final_text), 3):
                yield f"data: {json.dumps({'content': final_text[chunk_start:chunk_start+3]}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            return

        # 重新发起流式请求生成最终回答
        stream_kwargs = {"model": DEEPSEEK_MODEL, "messages": messages, "temperature": 0.7, "max_tokens": 2000, "stream": True}
        # 传 tools 让模型有机会再次调用（但已经没工具要调了）
        stream_kwargs["tools"] = TOOL_DEFINITIONS
        stream_kwargs["tool_choice"] = "auto"

        stream = client.chat.completions.create(**stream_kwargs)
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield f"data: {json.dumps({'content': delta.content}, ensure_ascii=False)}\n\n"
            # 如果流式过程中又出现了工具调用（极端情况），忽略并让下一轮处理
        yield f"data: {json.dumps({'done': True})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"


def _parse_text_tool_calls(content: str) -> list:
    """解析 DeepSeek 文本格式的工具调用（XML / DSML 格式）"""
    import re
    # 先尝试提取 <invoke>...</invoke> 块（兼容 DSML 包装）
    calls = []
    # DeepSeek 可能用 DSML 标签包裹，提取里面内容
    text = content
    # 尝试多种模式
    patterns = [
        r'<invoke\s+name="([^"]+)"[^>]*>(.*?)</invoke>',
        r'<invoke\s+name=\'([^\']+)\'[^>]*>(.*?)</invoke>',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text, re.DOTALL):
            func_name = m.group(1)
            params = {}
            param_pattern = r'<parameter\s+name="([^"]+)"[^>]*>(.*?)</parameter>'
            for pm in re.finditer(param_pattern, m.group(2), re.DOTALL):
                pname = pm.group(1)
                pval = pm.group(2).strip()
                if pval in ("true", "True"):
                    pval = True
                elif pval in ("false", "False"):
                    pval = False
                params[pname] = pval
            calls.append((func_name, params))
        if calls:
            break
    return calls


def _strip_xml_tool_tags(text: str) -> str:
    """清理回答中残留的 XML/DSML 工具调用标签，防止泄漏到前端"""
    import re
    # 移除 <tool_calls>...</tool_calls> 块（含 DSML 前缀）
    text = re.sub(r'(?:<DSML>)?\s*<tool_calls>\s*(?:</DSML>)?.*?(?:<DSML>)?\s*</tool_calls>\s*(?:</DSML>)?', '', text, flags=re.DOTALL)
    # 移除单独的 <invoke>...</invoke> 块
    text = re.sub(r'<invoke\s+name="[^"]*"[^>]*>.*?</invoke>', '', text, flags=re.DOTALL)
    # 移除结尾可能有的 `</invoke></tool_calls>` 残留
    text = re.sub(r'\s*</?(?:invoke|tool_calls|parameter)>(\s*</?(?:invoke|tool_calls|parameter)>)*', '', text)
    # 移除 <DSML> 标签
    text = re.sub(r'</?DSML>', '', text)
    return text.strip()
