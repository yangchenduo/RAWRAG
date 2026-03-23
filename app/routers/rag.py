# app/routers/rag.py
from app.utils.llm import call_llm
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Form
from sqlalchemy.orm import Session
from pymilvus import Collection
from datetime import datetime
import io
from typing import List

from app.models.document import DocumentMeta, SessionLocal, engine, Base, MILVUS_COLLECTION_NAME, VECTOR_DIMENSION
from app.utils.embedding import get_embedding, get_dimension
from app.core.config import settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.models.user import User
from app.routers.auth import get_current_user
from app.utils.agent import run_agent

router = APIRouter(prefix="/api/rag", tags=["RAG 核心功能"])

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=100,
    length_function=len,
    separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""], # 针对中文优化分隔符
)

def split_text_smart(text: str):
    """使用 LangChain 进行智能切片"""
    chunks = text_splitter.split_text(text)
    # 过滤掉过短的碎片（比如只有几个标点的）
    return [c for c in chunks if len(c.strip()) > 10]

@router.post("/upload")
async def upload_document(file: UploadFile = File(...), title: str = Form(None), current_user: User = Depends(get_current_user)):
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
    print(f"📝 正在对文档进行智能切片...")
    chunks = split_text_smart(text_content)
    
    if not chunks:
        raise HTTPException(status_code=400, detail="切片后无有效内容")
    
    print(f"✅ 切片完成：共 {len(chunks)} 个片段 (原长度: {len(text_content)})")

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
async def search_documents(query: str, top_k: int = 3,current_user: User = Depends(get_current_user)):
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

    doc_ids = set()
    hits_data = [] # 临时存储
    
    for hits_in_batch in results:
        for hit in hits_in_batch:
            doc_id = hit.entity.get("doc_id")
            if doc_id:
                doc_ids.add(doc_id)
            hits_data.append({
                "score": hit.score,
                "content": hit.entity.get("chunk_text"),
                "doc_id": doc_id
            })

    # 3. 从 PostgreSQL 查询这些 doc_id 对应的标题
    db = SessionLocal()
    doc_titles_map = {}
    try:
        from app.models.document import DocumentMeta
        docs = db.query(DocumentMeta).filter(DocumentMeta.id.in_(list(doc_ids))).all()
        for doc in docs:
            doc_titles_map[doc.id] = doc.title
    finally:
        db.close()

    # 4. 组装最终结果
    final_hits = []
    for item in hits_data:
        final_hits.append({
            "score": round(item["score"], 4), # 保留4位小数
            "content": item["content"].replace("\r\n", " ").strip(), # 清理换行符
            "source_file": doc_titles_map.get(item["doc_id"], "未知文件"), # 显示文件名
            "doc_id": item["doc_id"]
        })
    
    return {"query": query, "results": final_hits}


@router.post("/chat")
async def rag_chat(query: str = Form(...), top_k: int = Form(default=3),current_user: User = Depends(get_current_user)):
    """
    RAG 核心聊天接口：
    1. 向量检索相关片段
    2. 构建 Prompt (上下文 + 问题)
    3. 调用 DashScope 生成回答
    """
    if not query:
        raise HTTPException(status_code=400, detail="问题不能为空")

    # === 1. 向量检索 (复用之前的逻辑) ===
    query_vector = [get_embedding(query)]
    collection = Collection(MILVUS_COLLECTION_NAME)
    collection.load()
    
    search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
    results = collection.search(
        data=query_vector,
        anns_field="embedding",
        param=search_params,
        limit=top_k,
        output_fields=["chunk_text", "doc_id"]
    )

    # 提取上下文片段
    context_chunks = []
    source_files = set()
    
    for hits_in_batch in results:
        for hit in hits_in_batch:
            text = hit.entity.get("chunk_text")
            doc_id = hit.entity.get("doc_id")
            if text:
                context_chunks.append(text)
                source_files.add(str(doc_id)) # 简单记录 ID，实际可查表获取文件名

    # 如果没有检索到内容
    if not context_chunks:
        # 直接问 LLM，不带上下文
        final_prompt = f"请回答这个问题：{query}"
        context_info = "无相关文档"
    else:
        # === 2. 构建 RAG Prompt ===
        # 将检索到的片段拼接成上下文
        context_text = "\n\n".join([f"[片段{i+1}]: {chunk}" for i, chunk in enumerate(context_chunks)])
        
        # 经典的 RAG Prompt 模板
        final_prompt = f"""
你是一个智能助手。请根据以下【参考信息】来回答用户的【问题】。
如果【参考信息】中没有答案，请直接说“根据提供的资料，我无法回答这个问题”，不要编造。

【参考信息】：
{context_text}

【问题】：
{query}

【回答】：
"""
        context_info = f"引用了 {len(context_chunks)} 个片段 (来源ID: {', '.join(source_files)})"

    # === 3. 调用 Qwen ===
    print(f"🤖 正在向 Qwen 提问... (上下文长度: {len(final_prompt)})")
    ai_response = call_llm(final_prompt)

    return {
        "query": query,
        "answer": ai_response,
        "sources": {
            "count": len(context_chunks),
            "details": context_chunks # 返回具体片段供前端展示引用
        },
        "meta": context_info
    }

@router.post("/agent")
async def agent_endpoint(query: str = Form(...), current_user: User = Depends(get_current_user)):
    """
    意图识别 + 工具调用接口
    接收用户自然语言输入，自动识别意图并调用对应工具
    """
    if not query:
        raise HTTPException(status_code=400, detail="输入不能为空")

    result = run_agent(query)
    return {
        "input": query,
        "result": result
    }