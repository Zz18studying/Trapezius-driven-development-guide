# -*- coding: utf-8 -*-
"""
数据库模型定义
"""

from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

Base = declarative_base()

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Conversation(Base):
    """对话记录表"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), index=True)
    user_question = Column(Text)
    ai_answer = Column(Text)
    sources = Column(Text, nullable=True)  # JSON 格式存储
    response_time = Column(Float, default=0.0)
    sentiment = Column(String(20), nullable=True)  # positive, neutral, negative
    created_at = Column(DateTime, default=datetime.now)


class HotTopicCache(Base):
    """话题缓存表（用于存储 LLM 聚类结果）"""
    __tablename__ = "hot_topic_cache"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(50))
    count = Column(Integer)
    keywords = Column(Text, nullable=True)  # JSON 数组
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


def init_db():
    """初始化数据库，创建所有表"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """获取数据库会话"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()