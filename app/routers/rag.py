# app/routers/rag.py
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from pymilvus import Collection
from datetime import datetime
import io
from typing import List

from app.models.document import DocumentMeta, SessionLocal, engine, Base, MILVUS_COLLECTION_NAME, VECTOR_DIMENSION
from app.utils.embedding import get_embedding, get_dimension
from app.core.config import settings

router = APIRouter(prefix="/rag", tags=["RAG 核心功能"])

# 简单的文本切片函数 (实际项目中可用 LangChain 的 RecursiveCharacterTextSplitter)
def split_text(text: str, chunk_size: int = 500, overlap: int = 50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), title: str = Form(None)):
    """
    上传文档：读取内容 -> 切片 -> 向量化 -> 存入 Postgres 和 Milvus
    """
    # 1. 读取文件内容 (简单处理 txt/md，生产环境需解析 pdf/docx)
    try:
        content = await file.read()
        text_content = content.decode("utf-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件读取失败: {str(e)}")

    if not text_content.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    # 2. 文本切片
    chunks = split_text(text_content)
    if not chunks:
        raise HTTPException(status_code=400, detail="切片后无内容")

    # 3. 准备向量数据
    print(f"正在生成 {len(chunks)} 个片段的向量...")
    embeddings = [get_embedding(chunk) for chunk in chunks]
    
    # 校验维度
    if len(embeddings[0]) != VECTOR_DIMENSION:
        # 动态调整或报错，这里假设模型维度与配置一致
        pass 

    # 4. 存入 PostgreSQL (元数据)
    db = SessionLocal()
    try:
        doc_title = title if title else file.filename
        doc_meta = DocumentMeta(
            title=doc_title,
            file_path=f"uploads/{file.filename}", # 模拟路径
            content_preview=text_content[:200],
            vector_id=None # 稍后更新
        )
        db.add(doc_meta)
        db.commit()
        db.refresh(doc_meta) # 获取生成的 ID
        
        # 5. 存入 Milvus (向量数据)
        collection = Collection(MILVUS_COLLECTION_NAME)
        
        # 构造插入数据
        entities = [
            [doc_meta.id] * len(chunks),  # doc_id (关联 PG ID)
            chunks,                       # chunk_text
            embeddings                    # embedding
        ]
        
        mr = collection.insert(entities)
        collection.flush() # 确保写入
        
        # 更新 PG 中的 vector_id (这里简化处理，实际是一对多，可以用关联表，这里暂存第一个 ID 或忽略)
        # 为了演示简单，我们只记录 PG ID，查询时通过 doc_id 过滤
        print(f"✅ 文档 '{doc_title}' 上传成功！切片数: {len(chunks)}, Milvus ID 范围: {mr.primary_keys}")
        
        return {
            "message": "上传成功",
            "document_id": doc_meta.id,
            "title": doc_title,
            "chunks_count": len(chunks)
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"数据库写入失败: {str(e)}")
    finally:
        db.close()

@router.get("/search")
async def search_documents(query: str, top_k: int = 3):
    """
    搜索：问题向量化 -> Milvus 检索 -> 返回原文片段
    """
    if not query:
        raise HTTPException(status_code=400, detail="查询内容不能为空")

    # 1. 问题向量化
    query_vector = [get_embedding(query)]

    # 2. Milvus 检索
    collection = Collection(MILVUS_COLLECTION_NAME)
    collection.load() # 确保加载
    
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    
    results = collection.search(
        data=query_vector,
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        output_fields=["doc_id", "chunk_text"] # 返回原始文本和关联 ID
    )

    # 3. 格式化结果
    hits = []
    for hits_in_batch in results:
        for hit in hits_in_batch:
            hits.append({
                "score": hit.score,
                "content": hit.entity.get("chunk_text"),
                "doc_id": hit.entity.get("doc_id")
            })
    
    return {"query": query, "results": hits}