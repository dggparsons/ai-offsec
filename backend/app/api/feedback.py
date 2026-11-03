import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Event, Feedback

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

VALID_ACTIONS = {"open", "save", "escalate", "dismiss", "important"}


class FeedbackIn(BaseModel):
    event_id: uuid.UUID
    action: str
    analyst: str = "anonymous"
    note: str = ""


@router.post("", status_code=201)
async def submit_feedback(payload: FeedbackIn, db: AsyncSession = Depends(get_db)):
    if payload.action not in VALID_ACTIONS:
        raise HTTPException(400, f"action must be one of {sorted(VALID_ACTIONS)}")
    exists = await db.scalar(select(Event.id).where(Event.id == payload.event_id))
    if not exists:
        raise HTTPException(404, "event not found")
    fb = Feedback(**payload.model_dump())
    db.add(fb)
    await db.commit()
    return {"status": "recorded", "action": payload.action}
