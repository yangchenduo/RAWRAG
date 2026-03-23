# app/utils/llm.py
import os
from typing import List, Dict, Any, Optional
from dashscope import Generation
from http import HTTPStatus
from app.core.config import settings

api_key = getattr(settings, 'DASHSCOPE_API_KEY', None) or os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    raise ValueError("❌ 未找到 DASHSCOPE_API_KEY，请在 .env 中配置或在系统环境变量中设置")

def call_llm_with_tools(
    messages: List[Dict[str, str]],
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_choice: str = "auto"
) -> Dict[str, Any]:
    """
    支持 Function Calling 的大模型调用
    :param messages: 对话消息列表，格式 [{"role": "user", "content": "..."}, ...]
    :param tools: 工具定义列表，符合 DashScope 规范
    :param tool_choice: "auto" 让模型自动决定，或指定工具名如 {"type": "function", "function": {"name": "get_weather"}}
    :return: 响应字典，包含 content 或 tool_calls
    """
    try:
        response = Generation.call(
            model=getattr(settings, 'MODEL_NAME', 'qwen-plus'),
            messages=messages,
            api_key=api_key,
            result_format='message',
            tools=tools,
            tool_choice=tool_choice
        )

        if response.status_code == HTTPStatus.OK:
            # 返回第一条 choice 的信息
            choice = response.output.choices[0]
            return {
                "content": choice.message.content,
                "tool_calls": getattr(choice.message, "tool_calls", None)
            }
        else:
            error_msg = f"Request id: {response.request_id}, Status code: {response.status_code}, error code: {response.code}, error message: {response.message}"
            print(f"❌ LLM调用失败: {error_msg}")
            return {"content": f"⚠️ AI 服务响应异常：{response.code}", "tool_calls": None}
    except Exception as e:
        print(f"❌ 本地调用出错: {e}")
        return {"content": f"⚠️ 系统内部错误：{str(e)}", "tool_calls": None}

# 保留原有的简单调用方式，便于兼容
def call_llm(prompt: str, history: list = None):
    """简单文本调用（兼容旧代码）"""
    messages = []
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    res = call_llm_with_tools(messages, tools=None)
    return res.get("content", "")