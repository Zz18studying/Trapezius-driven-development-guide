# -*- coding: utf-8 -*-
"""
批量更新历史对话的情感标签
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.database import SessionLocal, Conversation
from services.sentiment_service import analyze_sentiment

def main():
    db = SessionLocal()
    try:
        # 查找 sentiment 为 NULL 或空字符串的记录
        conversations = db.query(Conversation).filter(
            (Conversation.sentiment.is_(None)) | (Conversation.sentiment == '')
        ).all()
        
        print(f"找到 {len(conversations)} 条未标注情感的对话")
        if not conversations:
            print("无需处理")
            return
            
        count = 0
        for idx, conv in enumerate(conversations):
            if conv.user_question:
                sentiment = analyze_sentiment(conv.user_question, use_llm=True)
                conv.sentiment = sentiment
                count += 1
                if count % 10 == 0:
                    print(f"已处理 {count}/{len(conversations)} 条...")
                    db.commit()
        db.commit()
        print(f"✅ 完成！共更新 {count} 条对话的情感标签")
    except Exception as e:
        print(f"❌ 出错: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()
