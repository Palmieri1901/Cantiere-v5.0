"""Backup completo JSON + restore da JSON."""
import json as _json
from datetime import datetime, timezone
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from database import db
from models import Cantiere, Cliente, Lavoro, RestoreRequest, Tariffe
from helpers import serialize

router = APIRouter()


@router.get("/backup")
async def backup_data():
    """Esporta tutti i dati del cantiere in un unico JSON scaricabile."""
    clienti = await db.clienti.find({}, {"_id": 0}).to_list(10000)
    lavori = await db.lavori.find({}, {"_id": 0}).to_list(10000)
    tariffe = await db.tariffe.find_one({"id": "default"}, {"_id": 0})
    cantiere = await db.cantiere.find_one({"id": "default"}, {"_id": 0})

    payload = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "app": "Portomare Cantiere Nautico",
        "cantiere": cantiere,
        "tariffe": tariffe,
        "clienti": clienti,
        "lavori": lavori,
        "counts": {
            "clienti": len(clienti),
            "lavori": len(lavori),
        }
    }
    body = _json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    filename = f"backup_cantiere_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        iter([body]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/restore")
async def restore_data(payload: RestoreRequest):
    """Ripristina i dati dal backup JSON. Sovrascrive completamente il DB."""
    restored = {"clienti": 0, "lavori": 0, "tariffe": False, "cantiere": False}

    if payload.cantiere is not None:
        c = Cantiere(**{k: v for k, v in payload.cantiere.items() if k in Cantiere.model_fields})
        await db.cantiere.delete_many({})
        await db.cantiere.insert_one(serialize(c))
        restored["cantiere"] = True

    if payload.tariffe is not None:
        t = Tariffe(**{k: v for k, v in payload.tariffe.items() if k in Tariffe.model_fields})
        await db.tariffe.delete_many({})
        await db.tariffe.insert_one(serialize(t))
        restored["tariffe"] = True

    if payload.clienti is not None:
        await db.clienti.delete_many({})
        docs = []
        for c in payload.clienti:
            try:
                cli = Cliente(**{k: v for k, v in c.items() if k in Cliente.model_fields})
                docs.append(serialize(cli))
            except Exception:
                pass
        if docs:
            await db.clienti.insert_many(docs)
        restored["clienti"] = len(docs)

    if payload.lavori is not None:
        await db.lavori.delete_many({})
        docs = []
        for l in payload.lavori:
            try:
                lav = Lavoro(**{k: v for k, v in l.items() if k in Lavoro.model_fields})
                docs.append(serialize(lav))
            except Exception:
                pass
        if docs:
            await db.lavori.insert_many(docs)
        restored["lavori"] = len(docs)

    return {"ok": True, "restored": restored}
