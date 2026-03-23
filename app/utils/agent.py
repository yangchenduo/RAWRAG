# app/utils/agent.py
from typing import Dict, Any, List
from app.tools import get_current_time, calculate, get_weather
from app.utils.llm import call_llm_with_tools
import json



# 工具注册表（同时保存执行函数）
TOOLS = {
    "get_current_time": {
        "function": get_current_time,
        "description": "获取当前日期和时间",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    "calculate": {
        "function": calculate,
        "description": "执行数学计算，支持加减乘除幂等运算",
        "parameters": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "数学表达式，例如 '1+2*3'"
                }
            },
            "required": ["expression"]
        }
    },
    "get_weather": {
        "function": get_weather,
        "description": "查询指定城市的天气",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如 '北京'"
                }
            },
            "required": ["city"]
        }
    }
}

def build_tools_for_api() -> List[Dict[str, Any]]:
    """将内部工具定义转换为 DashScope 的 tools 格式"""
    tools_list = []
    for name, info in TOOLS.items():
        tools_list.append({
            "type": "function",
            "function": {
                "name": name,
                "description": info["description"],
                "parameters": info["parameters"]
            }
        })
    return tools_list

def run_agent(user_input: str) -> str:
    """
    主流程：使用 Function Calling 识别意图并执行工具
    """
    # 1. 构建对话消息
    messages = [
        {"role": "system", "content": "你是一个智能助手，可以根据用户输入调用合适的工具。如果不需要工具，就正常回答。"},
        {"role": "user", "content": user_input}
    ]
    
    # 2. 获取工具定义
    tools = build_tools_for_api()
    print("工具定义：{tools}")
    
    # 3. 第一次调用 LLM，获取是否有工具调用
    response = call_llm_with_tools(messages, tools=tools, tool_choice="auto")
    print("LLM 响应：{response}")
    
    # 4. 如果模型返回了 tool_calls
    if response.get("tool_calls"):
        tool_calls = response["tool_calls"]
        tool_call = tool_calls[0]
        function_name = tool_call["function"]["name"]
        arguments_str = tool_call["function"]["arguments"]
        
        # 将 JSON 字符串转换为字典
        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            return f"参数解析失败：{arguments_str}"
        
        tool_func = TOOLS.get(function_name, {}).get("function")
        if tool_func:
            try:
                result = tool_func(**arguments)  # 现在 arguments 是字典
                return f"工具 {function_name} 执行结果：{result}"
            except Exception as e:
                return f"工具执行失败：{e}"
        else:
            return f"未知工具：{function_name}"
    else:
        # 没有工具调用，直接返回 LLM 的回答
        return response.get("content", "抱歉，我没有理解你的意思。")