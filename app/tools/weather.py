def get_weather(city: str) -> str:
    """模拟天气查询，实际可调用真实 API"""
    # 模拟数据
    weather_data = {
        "北京": "晴，25°C",
        "上海": "多云，22°C",
        "广州": "阵雨，28°C",
        "深圳": "阴，26°C",
    }
    return weather_data.get(city, f"{city} 的天气数据暂未收录")