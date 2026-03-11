# app/utils/embedding.py
import os
from sentence_transformers import SentenceTransformer

# 设置 HuggingFace 镜像（.env 中配置了 HF_ENDPOINT）
if os.getenv("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = os.getenv("HF_ENDPOINT")

# 加载模型 (第一次运行会自动下载，约 90MB，支持中文)
# 如果网络不好，可以手动下载后指定本地路径
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
model = SentenceTransformer(MODEL_NAME)

def get_embedding(text: str):
    """将文本转换为向量"""
    return model.encode(text).tolist()

def get_dimension():
    """获取向量维度"""
    return model.get_sentence_embedding_dimension()