# backend/init_db.py
from services.db_service import init_database

if __name__ == "__main__":
    init_database()
    print("数据库创建完成")