# -*- coding: utf-8 -*-
"""
Scenic spot review APIs.
"""

from datetime import datetime
import re
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from models.database import SessionLocal, SessionAllocation, SpotReview


router = APIRouter(prefix="/api/spots", tags=["景点评价"])


class SpotReviewRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=100)
    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(default="", max_length=300)


SESSION_ID_RE = re.compile(r"^lingshan_\d{8}_\d{4}$")


def is_valid_session_id(session_id: str) -> bool:
    return bool(SESSION_ID_RE.match(session_id or ""))


def ensure_review_session(db, session_id: str) -> None:
    allocation = db.query(SessionAllocation).filter(
        SessionAllocation.session_id == session_id
    ).first()
    now = datetime.now()
    if allocation:
        allocation.updated_at = now
        return

    db.add(SessionAllocation(
        session_id=session_id,
        device_id="review_only",
        created_at=now,
        updated_at=now,
    ))


def review_to_dict(review: SpotReview) -> dict:
    return {
        "id": review.id,
        "spot_id": review.spot_id,
        "session_id": review.session_id,
        "rating": review.rating,
        "comment": review.comment or "",
        "created_at": review.created_at.isoformat() if review.created_at else None,
    }


def get_summary(db, spot_id: int) -> dict:
    row = db.query(
        func.count(SpotReview.id),
        func.avg(SpotReview.rating)
    ).filter(SpotReview.spot_id == spot_id).one()
    count = int(row[0] or 0)
    average = float(row[1] or 0)
    return {
        "spot_id": spot_id,
        "count": count,
        "average": average,
    }


@router.get("/ratings")
async def get_all_ratings():
    db = SessionLocal()
    try:
        rows = db.query(
            SpotReview.spot_id,
            func.count(SpotReview.id),
            func.avg(SpotReview.rating)
        ).group_by(SpotReview.spot_id).all()

        ratings = {
            str(spot_id): {
                "spot_id": spot_id,
                "count": int(count or 0),
                "average": float(average or 0),
            }
            for spot_id, count, average in rows
        }
        return {"code": 0, "data": ratings, "msg": "success"}
    finally:
        db.close()


@router.get("/{spot_id}/reviews")
async def get_reviews(spot_id: int):
    db = SessionLocal()
    try:
        reviews = db.query(SpotReview).filter(
            SpotReview.spot_id == spot_id
        ).order_by(SpotReview.created_at.desc()).all()
        return {
            "code": 0,
            "data": {
                "summary": get_summary(db, spot_id),
                "reviews": [review_to_dict(review) for review in reviews],
            },
            "msg": "success",
        }
    finally:
        db.close()


@router.post("/{spot_id}/reviews")
async def create_review(spot_id: int, payload: SpotReviewRequest):
    session_id = payload.session_id.strip()
    comment = (payload.comment or "").strip()

    db = SessionLocal()
    try:
        if not is_valid_session_id(session_id):
            return {"code": 1, "data": None, "msg": "会话 ID 格式不正确，请重新获取会话 ID"}

        ensure_review_session(db, session_id)

        existing = db.query(SpotReview).filter(
            SpotReview.spot_id == spot_id,
            SpotReview.session_id == session_id
        ).first()
        if existing:
            return {"code": 1, "data": None, "msg": "当前会话 ID 已评价过该景点"}

        now = datetime.now()
        review = SpotReview(
            spot_id=spot_id,
            session_id=session_id,
            rating=payload.rating,
            comment=comment,
            created_at=now,
            updated_at=now,
        )
        db.add(review)
        db.commit()
        db.refresh(review)

        reviews = db.query(SpotReview).filter(
            SpotReview.spot_id == spot_id
        ).order_by(SpotReview.created_at.desc()).all()
        return {
            "code": 0,
            "data": {
                "summary": get_summary(db, spot_id),
                "review": review_to_dict(review),
                "reviews": [review_to_dict(item) for item in reviews],
            },
            "msg": "success",
        }
    except IntegrityError:
        db.rollback()
        return {"code": 1, "data": None, "msg": "当前会话 ID 已评价过该景点"}
    except Exception as exc:
        db.rollback()
        return {"code": 1, "data": None, "msg": str(exc)}
    finally:
        db.close()
