from fastapi import FastAPI, HTTPException
from app.core.config import settings
import psycopg2
from pymilvus import connections
from app.models.document import init_db_tables, init_milvus_collection
from contextlib import asynccontextmanager
from app.routers import rag


@asynccontextmanager
async def startup_db_client(app: FastAPI):

    """应用启动时检查数据库连接并初始化表结构"""
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
    
    try:
        init_db_tables()       # 创建 Postgres 表
        init_milvus_collection() # 创建 Milvus Collection
        print("🎉 所有数据模型初始化完毕！")
    except Exception as e:
        print(f"⚠️ 数据模型初始化警告: {e}")
        # 注意：这里不要抛出异常导致启动失败，除非你认为表不存在就不能运行

    yield 

    # --- 关闭逻辑 (Shutdown) ---
    # 如果需要关闭数据库连接或 Milvus 连接，可以在这里写
    print(f"🛑 {settings.APP_NAME} 正在关闭...")
    # 例如: connections.disconnect("default")

app = FastAPI(
    title=settings.APP_NAME,
    description="手搓的 RAG 系统 - 基于 FastAPI + Milvus + Postgres",
    version="0.1.0",
    lifespan=startup_db_client
)

# 注册路由
app.include_router(rag.router)

@app.get("/")
async def root():
    return {"message": "Welcome to RawRAG! System is running."}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.APP_NAME}