from fastapi import FastAPI, HTTPException
from app.core.config import settings
import psycopg2
from pymilvus import connections

app = FastAPI(
    title=settings.APP_NAME,
    description="手搓的 RAG 系统 - 基于 FastAPI + Milvus + Postgres",
    version="0.1.0"
)

@app.on_event("startup")
async def startup_db_client():
    """应用启动时检查数据库连接"""
    print(f"🚀 正在启动 {settings.APP_NAME}...")
    
    # 1. 测试 PostgreSQL 连接
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            database=settings.POSTGRES_DB
        )
        conn.close()
        print("✅ PostgreSQL 连接成功!")
    except Exception as e:
        print(f"❌ PostgreSQL 连接失败: {e}")

    # 2. 测试 Milvus 连接
    try:
        # 注意：如果 .env 里用户名密码为空，这里可能需要调整
        user = settings.MILVUS_USERNAME if settings.MILVUS_USERNAME else None
        password = settings.MILVUS_PASSWORD if settings.MILVUS_PASSWORD else None
        
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT,
            user=user,
            password=password
        )
        print("✅ Milvus 连接成功!")
    except Exception as e:
        print(f"❌ Milvus 连接失败: {e}")

@app.get("/")
async def root():
    return {"message": "Welcome to RawRAG! System is running."}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}