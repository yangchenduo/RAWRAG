# app/models/document.py
from sqlalchemy import Column, Integer, String, DateTime, Text, create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility

from app.core.config import settings
from app.db.base_class import Base

# ==========================================
# 1. PostgreSQL 模型 (存元数据)
# ==========================================
class DocumentMeta(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, comment="文档标题")
    file_path = Column(String(500), nullable=True, comment="原始文件路径")
    content_preview = Column(Text, nullable=True, comment="内容前200字预览")
    
    # 关联 Milvus 中的 vector_id
    vector_id = Column(Integer, nullable=True, comment="对应的 Milvus 向量 ID")
    
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    def __repr__(self):
        return f"<DocumentMeta(title={self.title}, id={self.id})>"

# 初始化 Postgres 引擎
engine = create_engine(
    f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db_tables():
    """在 Postgres 中创建表"""
    Base.metadata.create_all(bind=engine)
    print("✅ PostgreSQL 数据表初始化完成")

# ==========================================
# 2. Milvus 模型 (存向量)
# ==========================================
MILVUS_COLLECTION_NAME = "rag_documents"
VECTOR_DIMENSION = 384

def init_milvus_collection():
    """在 Milvus 中创建或重用 Collection，确保维度匹配"""
    try:
        # 检查 Collection 是否已存在
        if utility.has_collection(MILVUS_COLLECTION_NAME):
            # 获取现有 Collection 信息
            collection = Collection(MILVUS_COLLECTION_NAME)
            schema = collection.schema
            # 查找 embedding 字段的维度
            for field in schema.fields:
                if field.name == "embedding":
                    existing_dim = field.params.get("dim")
                    if existing_dim == VECTOR_DIMENSION:
                        print(f"✅ Collection '{MILVUS_COLLECTION_NAME}' 已存在且维度匹配 ({VECTOR_DIMENSION})，直接使用")
                        collection.load()  # 确保加载
                        return
                    else:
                        print(f"ℹ️ Collection '{MILVUS_COLLECTION_NAME}' 维度不匹配 (现有 {existing_dim}，需要 {VECTOR_DIMENSION})，准备删除重建")
                        utility.drop_collection(MILVUS_COLLECTION_NAME)
                        break
            else:
                # 没有找到 embedding 字段，可能是旧版本，删除重建
                print(f"ℹ️ Collection '{MILVUS_COLLECTION_NAME}' 结构异常，删除重建")
                utility.drop_collection(MILVUS_COLLECTION_NAME)

        # 创建新的 Collection
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="doc_id", dtype=DataType.INT64),
            FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=2048),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=VECTOR_DIMENSION)
        ]

        schema = CollectionSchema(fields, description="RAG 文档向量集合")
        collection = Collection(name=MILVUS_COLLECTION_NAME, schema=schema)

        # 创建索引 (IVF_FLAT 是常用且高效的索引)
        index_params = {
            "metric_type": "COSINE", # 余弦相似度
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        collection.create_index(field_name="embedding", index_params=index_params)      
        # 加载到内存
        collection.load()
        print(f"✅ Milvus Collection '{MILVUS_COLLECTION_NAME}' 创建并加载成功 (维度：{VECTOR_DIMENSION})")
        
    except Exception as e:
        print(f"❌ Milvus 初始化失败：{e}")
        raise
