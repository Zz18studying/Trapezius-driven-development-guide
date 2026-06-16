# -*- coding: utf-8 -*-
"""
数据库模型定义
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

Base = declarative_base()

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Conversation(Base):
    """对话记录表"""
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    user_question = Column(Text)
    ai_answer = Column(Text)
    sources = Column(Text, nullable=True)  # JSON 格式存储
    response_time = Column(Float, default=0.0)  # 响应时间（秒）
    sentiment = Column(String(20), nullable=True)  # 情感标签: positive, neutral, negative
    created_at = Column(DateTime, default=datetime.now)


class KnowledgeDocument(Base):
    """知识文档表"""
    __tablename__ = "knowledge_documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255))
    file_path = Column(String(500))
    file_type = Column(String(20))  # pdf, docx, txt, md
    file_size = Column(Integer)  # 字节
    status = Column(String(20), default="uploaded")  # uploaded, processing, processed, failed
    chunk_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class DigitalHumanConfig(Base):
    """数字人配置表"""
    __tablename__ = "digital_human_config"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(100), unique=True)
    config_value = Column(Text)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# 创建所有表
def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()