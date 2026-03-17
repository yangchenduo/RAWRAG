# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean
from app.db.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password = Column(String(64), nullable=False) # 存 MD5 (32位字符)
    is_active = Column(Boolean, default=True)