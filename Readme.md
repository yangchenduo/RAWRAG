# docker安装
cd D:\DATA\RawRAG\RAWRAG
docker compose up -d       

# 创建虚拟环境

## 只设置一次
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
python -m venv venv

.\venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt

## 同步 requirements.txt
pip freeze > requirements.txt

## 清楚缓存
Remove-Item -Recurse -Force __pycache__ -ErrorAction SilentlyContinue; Remove-Item -Recurse -Force app\__pycache__ -ErrorAction SilentlyContinue; Remove-Item -Recurse -Force app\core\__pycache__ -ErrorAction SilentlyContinue

# 启动
python -m uvicorn main:app --reload