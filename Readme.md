> ⚠️ **许可声明**：本项目代码仅供学习和参考。允许下载和查看，但**严禁修改、严禁商用、严禁基于此代码开发衍生产品**。如需授权请联系作者。

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

# 数据库相关
alembic current - 查看当前版本
alembic upgrade head - 初始化数据库

alembic revision --autogenerate -m "Add document table" - 当数据库变化时使用此命令维护数据库版本
alembic upgrade head - 再次执行此命令升级到最新版本

# 启动
python -m uvicorn main:app --reload

# 创建测试用户
python scripts/create_admin.py

- API 文档 ： http://127.0.0.1:8000/docs
- 健康检查 ： http://127.0.0.1:8000/health
- 根路径 ： http://127.0.0.1:8000/
- minio: http://127.0.0.1:9000
