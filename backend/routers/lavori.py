"""Endpoints CRUD lavori (storico strutturato)."""
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException

from database import db
from models import Lavoro, LavoroCreate
from helpers import serialize

router = APIRouter()


@router.get("/clienti/{cliente_id}/lavori", response_model=List[Lavoro])
async def list_lavori(cliente_id: str):
    docs = await db.lavori.find({"cliente_id": cliente_id}, {"_id": 0}).sort("data", -1).to_list(1000)
    for d in docs:
        if isinstance(d.get("created_at"), str):
            try:
                d["created_at"] = datetime.fromisoformat(d["created_at"])
            except Exception:
                pass
    return [Lavoro(**d) for d in docs]


@router.post("/lavori", response_model=Lavoro)
async def create_lavoro(payload: LavoroCreate):
    if payload.stato not in ("pianificato", "in_corso", "completato"):
        raise HTTPException(400, "Stato non valido")
    c = await db.clienti.find_one({"id": payload.cliente_id})
    if not c:
        raise HTTPException(404, "Cliente non trovato")
    lavoro = Lavoro(**{k: v for k, v in payload.model_dump().items() if v is not None})
    await db.lavori.insert_one(serialize(lavoro))
    return lavoro


@router.put("/lavori/{lavoro_id}", response_model=Lavoro)
async def update_lavoro(lavoro_id: str, payload: LavoroCreate):
    existing = await db.lavori.find_one({"id": lavoro_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Lavoro non trovato")
    if payload.stato not in ("pianificato", "in_corso", "completato"):
        raise HTTPException(400, "Stato non valido")
    merged = {**existing, **{k: v for k, v in payload.model_dump().items() if v is not None}}
    merged["id"] = lavoro_id
    lavoro = Lavoro(**merged)
    await db.lavori.update_one({"id": lavoro_id}, {"$set": serialize(lavoro)})
    return lavoro


@router.delete("/lavori/{lavoro_id}")
async def delete_lavoro(lavoro_id: str):
    res = await db.lavori.delete_one({"id": lavoro_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Lavoro non trovato")
    return {"ok": True}
