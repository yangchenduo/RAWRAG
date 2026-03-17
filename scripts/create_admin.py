# scripts/create_admin.py
import sys
import os

# 确保能导入项目模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal, engine
from app.models.user import User
from app.db.base_class import Base
from app.core.security import get_password_hash

# 先创建表结构
Base.metadata.create_all(bind=engine)
print("✅ 数据库表结构初始化完成")

db = SessionLocal()

username = "admin"
password_plain = "123456"

# 1. 检查用户是否存在
user = db.query(User).filter(User.username == username).first()

if user:
    print(f"⚠️ 用户 {username} 已存在。是否需要重置密码？(y/n): ")
    # 简单起见，这里如果存在我们就跳过，或者你可以手动删除数据库里的用户再跑
    # 为了演示，我们直接报错提示
    print("❌ 用户已存在，请先在数据库中删除该用户，或修改脚本逻辑进行更新。")
else:
    # 2. 生成 bcrypt 哈希
    password_hash = get_password_hash(password_plain)
    
    # 3. 创建新用户
    new_user = User(username=username, password=password_hash, is_active=True)
    db.add(new_user)
    db.commit()
    
    print(f"✅ 管理员创建成功！")
    print(f"   用户名: {username}")
    print(f"   密码: {password_plain}")
    print(f"   哈希值 (bcrypt): {password_hash[:20]}... (已隐藏部分)")

db.close()