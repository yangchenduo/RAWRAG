# app/utils/llm.py
import os
from dashscope import Generation
from http import HTTPStatus
from app.core.config import settings

# 确保从环境变量读取 key
api_key = getattr(settings, 'DASHSCOPE_API_KEY', None) or os.getenv("DASHSCOPE_API_KEY")
if not api_key:
    raise ValueError("❌ 未找到 DASHSCOPE_API_KEY，请在 .env 中配置或在系统环境变量中设置")

def call_llm(prompt: str, history: list = None):
    """
    调用 DashScope 大模型 API
    :param prompt: 用户的问题或构建好的 Prompt
    :param history: 对话历史 (可选)，格式 [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
    """
    messages = []
    if history:
        messages.extend(history)
    
    # 将当前 prompt 作为最后一条用户消息
    messages.append({"role": "user", "content": prompt})

    try:
        response = Generation.call(
            model=getattr(settings, 'MODEL_NAME', 'qwen-plus'),
            messages=messages,
            api_key=api_key,
            result_format='message'  # 返回格式为 message 列表
        )

        if response.status_code == HTTPStatus.OK:
            return response.output.choices[0].message.content
        else:
            error_msg = f"Request id: {response.request_id}, Status code: {response.status_code}, error code: {response.code}, error message: {response.message}"
            print(f"❌ LLM调用失败: {error_msg}")
            return f"⚠️ AI 服务响应异常：{response.code}"

    except Exception as e:
        print(f"❌ 本地调用出错: {e}")
        return f"⚠️ 系统内部错误：{str(e)}"