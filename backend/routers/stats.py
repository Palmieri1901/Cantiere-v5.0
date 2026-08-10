"""Statistiche dashboard + gestione posti barca."""
from datetime import datetime, date, timedelta
from typing import Optional
from fastapi import APIRouter

from database import db, TOTAL_POSTI
from helpers import _totale_extra

router = APIRouter()


@router.get("/stats")
async def stats(anno: Optional[int] = None):
    q = {}
    if anno is not None:
        q["anno"] = anno
    docs = await db.clienti.find(q, {"_id": 0}).to_list(1000)
    dentro = sum(1 for d in docs if d.get("tipo_sosta") == "dentro")
    fuori = sum(1 for d in docs if d.get("tipo_sosta") == "fuori")
    fuori_sede = sum(1 for d in docs if d.get("tipo_sosta") == "fuori_sede")
    occupati = sum(1 for d in docs if d.get("posto_barca"))
    liberi = TOTAL_POSTI - occupati

    entrate_totali = 0.0
    for d in docs:
        entrate_totali += sum([
            d.get("costo_sosta", 0) or 0,
            d.get("costo_movimentazione", 0) or 0,
            d.get("costo_taccaggio", 0) or 0,
            d.get("costo_copertura", 0) or 0,
            d.get("costo_alaggio", 0) or 0,
            d.get("costo_varo", 0) or 0,
            d.get("costo_antivegetativa", 0) or 0,
            d.get("costo_manutenzione_motore", 0) or 0,
            d.get("costo_lavaggio_inizio", 0) or 0,
            d.get("costo_lavaggio_fine", 0) or 0,
            d.get("costo_scafo_sporco", 0) or 0,
        ])
        entrate_totali += _totale_extra(d)

    oggi = date.today()
    limite = oggi + timedelta(days=30)
    scadenze = []
    for d in docs:
        for tipo, key in (("Antivegetativa", "scadenza_antivegetativa"), ("Manutenzione motore", "scadenza_manutenzione")):
            v = d.get(key)
            if v:
                try:
                    dt = datetime.fromisoformat(v).date() if "T" in v else date.fromisoformat(v)
                    if oggi <= dt <= limite:
                        scadenze.append({
                            "cliente_id": d["id"],
                            "nome": f"{d.get('cognome','')} {d.get('nome','')}",
                            "tipo": tipo,
                            "data": dt.isoformat(),
                            "giorni_rimanenti": (dt - oggi).days,
                        })
                except Exception:
                    pass
    scadenze.sort(key=lambda x: x["giorni_rimanenti"])

    return {
        "totale_clienti": len(docs),
        "posti_totali": TOTAL_POSTI,
        "posti_occupati": occupati,
        "posti_liberi": liberi,
        "sosta_dentro": dentro,
        "sosta_fuori": fuori,
        "sosta_fuori_sede": fuori_sede,
        "entrate_totali": round(entrate_totali, 2),
        "scadenze_prossime": scadenze[:10],
    }


@router.get("/posti-barca")
async def posti_barca(anno: Optional[int] = None):
    q = {"posto_barca": {"$ne": None}}
    if anno is not None:
        q["anno"] = anno
    docs = await db.clienti.find(q, {"_id": 0}).to_list(1000)
    occupati_map = {d["posto_barca"]: d for d in docs if d.get("posto_barca")}
    result = []
    for i in range(1, TOTAL_POSTI + 1):
        c = occupati_map.get(i)
        result.append({
            "numero": i,
            "occupato": c is not None,
            "cliente_id": c.get("id") if c else None,
            "cliente_nome": f"{c.get('cognome','')} {c.get('nome','')}" if c else None,
            "tipo_sosta": c.get("tipo_sosta") if c else None,
            "tipo_barca": c.get("tipo_barca") if c else None,
        })
    return result


@router.get("/posti-barca/next")
async def next_posto_libero(anno: Optional[int] = None, escludi_cliente_id: Optional[str] = None):
    """Ritorna il primo posto barca libero (1-200) per l'anno indicato."""
    anno_target = anno if anno is not None else datetime.now().year
    q = {"posto_barca": {"$ne": None}, "anno": anno_target}
    if escludi_cliente_id:
        q["id"] = {"$ne": escludi_cliente_id}
    docs = await db.clienti.find(q, {"posto_barca": 1, "_id": 0}).to_list(2000)
    occupati = {int(d["posto_barca"]) for d in docs if d.get("posto_barca")}
    for i in range(1, TOTAL_POSTI + 1):
        if i not in occupati:
            return {"anno": anno_target, "posto": i, "posti_liberi": TOTAL_POSTI - len(occupati)}
    return {"anno": anno_target, "posto": None, "posti_liberi": 0}
