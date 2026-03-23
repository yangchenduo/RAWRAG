import datetime

def get_current_time() -> str:
    """返回当前日期和时间"""
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S")