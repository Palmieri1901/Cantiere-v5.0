"""Endpoints info cantiere (nome, logo, contatti)."""
from datetime import datetime, timezone
from fastapi import APIRouter

from database import db
from models import Cantiere, CantiereUpdate
from helpers import serialize

router = APIRouter()


@router.get("/cantiere", response_model=Cantiere)
async def get_cantiere():
    doc = await db.cantiere.find_one({"id": "default"}, {"_id": 0})
    if not doc:
        c = Cantiere()
        await db.cantiere.insert_one(serialize(c))
        return c
    return Cantiere(**doc)


@router.put("/cantiere", response_model=Cantiere)
async def update_cantiere(payload: CantiereUpdate):
    doc = await db.cantiere.find_one({"id": "default"}, {"_id": 0})
    current = Cantiere(**doc) if doc else Cantiere()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    new_data = current.model_dump()
    new_data.update(updates)
    new_data["updated_at"] = datetime.now(timezone.utc)
    c = Cantiere(**new_data)
    await db.cantiere.update_one({"id": "default"}, {"$set": serialize(c)}, upsert=True)
    return c
