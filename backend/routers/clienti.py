"""Endpoints CRUD clienti + preview costi + preventivo PDF + storico multi-anno + toggle pagato."""
import io
import re
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from database import db, TOTAL_POSTI
from models import Cliente, ClienteCreate, PagatoUpdate
from helpers import (
    get_tariffe_doc, calcola_costi, serialize, deserialize_cliente,
    _sanitize_lavorazioni_extra,
)
from pdf_builders import _build_preventivo_pdf, _build_storico_pdf

router = APIRouter()


@router.get("/calcola-costi")
async def preview_costi(lunghezza: float, tipo_sosta: str,
                        potenza_motore: float = 0.0,
                        numero_candele: int = 4,
                        numero_termostati: int = 1,
                        antivegetativa_attiva: bool = True,
                        girante_attivo: bool = True,
                        litri_olio_motore: float = 3.0,
                        lavaggio_inizio_attivo: bool = True,
                        lavaggio_fine_attivo: bool = True,
                        secondo_motore: bool = False,
                        potenza_motore_2: float = 0.0,
                        litri_olio_motore_2: float = 3.0,
                        numero_candele_2: int = 4,
                        numero_termostati_2: int = 1,
                        girante_2_attivo: bool = True,
                        scafo_sporco_attivo: bool = False,
                        copertura_attiva: bool = False,
                        litri_olio_piede: float = 1.0,
                        litri_olio_piede_2: float = 1.0,
                        giorni_sosta_temporanea: int = 0,
                        destinazione_alaggio_varo: str = "marina_di_campo",
                        alaggio_varo_attivo: bool = False,
                        numero_movimenti: int = 1,
                        primo_motore_attivo: bool = True):
    if tipo_sosta not in ("dentro", "fuori", "fuori_sede", "temporanea"):
        raise HTTPException(400, "tipo_sosta deve essere 'dentro', 'fuori', 'fuori_sede' o 'temporanea'")
    t = await get_tariffe_doc()
    return calcola_costi(lunghezza, tipo_sosta, t, potenza_motore,
                         numero_candele, numero_termostati,
                         antivegetativa_attiva, girante_attivo, litri_olio_motore,
                         lavaggio_inizio_attivo, lavaggio_fine_attivo,
                         secondo_motore, potenza_motore_2, litri_olio_motore_2,
                         numero_candele_2, numero_termostati_2, girante_2_attivo,
                         scafo_sporco_attivo, copertura_attiva,
                         litri_olio_piede, litri_olio_piede_2,
                         giorni_sosta_temporanea, destinazione_alaggio_varo,
                         alaggio_varo_attivo, numero_movimenti,
                         primo_motore_attivo)


@router.get("/clienti", response_model=List[Cliente])
async def list_clienti(anno: Optional[int] = None):
    q = {}
    if anno is not None:
        q["anno"] = anno
    docs = await db.clienti.find(q, {"_id": 0}).to_list(1000)
    docs.sort(key=lambda d: ((d.get("cognome") or "").strip().lower(), (d.get("nome") or "").strip().lower()))
    return [Cliente(**deserialize_cliente(d)) for d in docs]


@router.get("/clienti/{cliente_id}", response_model=Cliente)
async def get_cliente(cliente_id: str):
    doc = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Cliente non trovato")
    return Cliente(**deserialize_cliente(doc))


@router.post("/clienti", response_model=Cliente)
async def create_cliente(payload: ClienteCreate):
    if payload.tipo_sosta not in ("dentro", "fuori", "fuori_sede", "temporanea"):
        raise HTTPException(400, "tipo_sosta deve essere 'dentro', 'fuori', 'fuori_sede' o 'temporanea'")
    if payload.posto_barca is not None:
        if payload.posto_barca < 1 or payload.posto_barca > TOTAL_POSTI:
            raise HTTPException(400, f"Posto barca deve essere tra 1 e {TOTAL_POSTI}")
        anno_check = payload.anno or datetime.now().year
        existing = await db.clienti.find_one({"posto_barca": payload.posto_barca, "anno": anno_check})
        if existing:
            raise HTTPException(400, f"Posto barca {payload.posto_barca} già occupato per l'anno {anno_check}")

    t = await get_tariffe_doc()
    auto_costi = calcola_costi(
        payload.lunghezza, payload.tipo_sosta, t,
        payload.potenza_motore or 0,
        payload.numero_candele or 4,
        payload.numero_termostati or 1,
        bool(payload.antivegetativa_attiva if payload.antivegetativa_attiva is not None else True),
        bool(payload.girante_attivo if payload.girante_attivo is not None else True),
        float(payload.litri_olio_motore if payload.litri_olio_motore is not None else 3.0),
        bool(payload.lavaggio_inizio_attivo if payload.lavaggio_inizio_attivo is not None else True),
        bool(payload.lavaggio_fine_attivo if payload.lavaggio_fine_attivo is not None else True),
        bool(payload.secondo_motore if payload.secondo_motore is not None else False),
        float(payload.potenza_motore_2 or 0),
        float(payload.litri_olio_motore_2 if payload.litri_olio_motore_2 is not None else 3.0),
        int(payload.numero_candele_2 or 4),
        int(payload.numero_termostati_2 or 1),
        bool(payload.girante_2_attivo if payload.girante_2_attivo is not None else True),
        bool(payload.scafo_sporco_attivo if payload.scafo_sporco_attivo is not None else False),
        bool(payload.copertura_attiva if payload.copertura_attiva is not None else False),
        float(payload.litri_olio_piede if payload.litri_olio_piede is not None else 1.0),
        float(payload.litri_olio_piede_2 if payload.litri_olio_piede_2 is not None else 1.0),
        int(payload.giorni_sosta_temporanea or 0),
        (payload.destinazione_alaggio_varo or "marina_di_campo"),
        bool(payload.alaggio_varo_attivo if payload.alaggio_varo_attivo is not None else False),
        int(payload.numero_movimenti or 1),
        bool(payload.primo_motore_attivo if payload.primo_motore_attivo is not None else True),
    )
    auto_costi.pop("ricambi_dettaglio", None)
    auto_costi.pop("ricambi_2_dettaglio", None)

    data = payload.model_dump()
    if data.get("lavorazioni_extra") is not None:
        data["lavorazioni_extra"] = _sanitize_lavorazioni_extra(data["lavorazioni_extra"])
    manual_alaggio_varo = (payload.alaggio_varo_attivo and payload.destinazione_alaggio_varo == "altra")
    for k in auto_costi:
        val = data.get(k)
        if manual_alaggio_varo and k in ("costo_alaggio", "costo_varo"):
            data[k] = float(val) if val is not None else 0.0
        elif not payload.override_costi or val is None:
            data[k] = auto_costi[k]
        else:
            data[k] = val

    cliente = Cliente(**{k: v for k, v in data.items() if v is not None or k in ("posto_barca", "scadenza_antivegetativa", "scadenza_manutenzione")})
    await db.clienti.insert_one(serialize(cliente))
    return cliente


@router.put("/clienti/{cliente_id}", response_model=Cliente)
async def update_cliente(cliente_id: str, payload: ClienteCreate):
    existing = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Cliente non trovato")

    if payload.tipo_sosta not in ("dentro", "fuori", "fuori_sede", "temporanea"):
        raise HTTPException(400, "tipo_sosta deve essere 'dentro', 'fuori', 'fuori_sede' o 'temporanea'")

    if payload.posto_barca is not None:
        if payload.posto_barca < 1 or payload.posto_barca > TOTAL_POSTI:
            raise HTTPException(400, f"Posto barca deve essere tra 1 e {TOTAL_POSTI}")
        anno_check = payload.anno or existing.get("anno") or datetime.now().year
        conflict = await db.clienti.find_one({"posto_barca": payload.posto_barca, "anno": anno_check, "id": {"$ne": cliente_id}})
        if conflict:
            raise HTTPException(400, f"Posto barca {payload.posto_barca} già occupato per l'anno {anno_check}")

    t = await get_tariffe_doc()
    auto_costi = calcola_costi(
        payload.lunghezza, payload.tipo_sosta, t,
        payload.potenza_motore or 0,
        payload.numero_candele or 4,
        payload.numero_termostati or 1,
        bool(payload.antivegetativa_attiva if payload.antivegetativa_attiva is not None else True),
        bool(payload.girante_attivo if payload.girante_attivo is not None else True),
        float(payload.litri_olio_motore if payload.litri_olio_motore is not None else 3.0),
        bool(payload.lavaggio_inizio_attivo if payload.lavaggio_inizio_attivo is not None else True),
        bool(payload.lavaggio_fine_attivo if payload.lavaggio_fine_attivo is not None else True),
        bool(payload.secondo_motore if payload.secondo_motore is not None else False),
        float(payload.potenza_motore_2 or 0),
        float(payload.litri_olio_motore_2 if payload.litri_olio_motore_2 is not None else 3.0),
        int(payload.numero_candele_2 or 4),
        int(payload.numero_termostati_2 or 1),
        bool(payload.girante_2_attivo if payload.girante_2_attivo is not None else True),
        bool(payload.scafo_sporco_attivo if payload.scafo_sporco_attivo is not None else False),
        bool(payload.copertura_attiva if payload.copertura_attiva is not None else False),
        float(payload.litri_olio_piede if payload.litri_olio_piede is not None else 1.0),
        float(payload.litri_olio_piede_2 if payload.litri_olio_piede_2 is not None else 1.0),
        int(payload.giorni_sosta_temporanea or 0),
        (payload.destinazione_alaggio_varo or existing.get("destinazione_alaggio_varo") or "marina_di_campo"),
        bool(payload.alaggio_varo_attivo if payload.alaggio_varo_attivo is not None else existing.get("alaggio_varo_attivo", False)),
        int(payload.numero_movimenti if payload.numero_movimenti is not None else existing.get("numero_movimenti", 1) or 1),
        bool(payload.primo_motore_attivo if payload.primo_motore_attivo is not None else existing.get("primo_motore_attivo", True)),
    )
    auto_costi.pop("ricambi_dettaglio", None)
    auto_costi.pop("ricambi_2_dettaglio", None)

    data = payload.model_dump()
    if data.get("lavorazioni_extra") is not None:
        data["lavorazioni_extra"] = _sanitize_lavorazioni_extra(data["lavorazioni_extra"])
    dest_effettiva = payload.destinazione_alaggio_varo or existing.get("destinazione_alaggio_varo") or "marina_di_campo"
    av_attivo = payload.alaggio_varo_attivo if payload.alaggio_varo_attivo is not None else existing.get("alaggio_varo_attivo", False)
    manual_alaggio_varo = (av_attivo and dest_effettiva == "altra")
    for k in auto_costi:
        val = data.get(k)
        if manual_alaggio_varo and k in ("costo_alaggio", "costo_varo"):
            data[k] = float(val) if val is not None else 0.0
        elif not payload.override_costi or val is None:
            data[k] = auto_costi[k]
        else:
            data[k] = val

    merged = deserialize_cliente(existing)
    merged.update({k: v for k, v in data.items() if v is not None or k in ("posto_barca", "scadenza_antivegetativa", "scadenza_manutenzione")})
    merged["id"] = cliente_id
    merged["updated_at"] = datetime.now(timezone.utc)
    cliente = Cliente(**merged)
    await db.clienti.update_one({"id": cliente_id}, {"$set": serialize(cliente)})
    return cliente


@router.delete("/clienti/{cliente_id}")
async def delete_cliente(cliente_id: str):
    res = await db.clienti.delete_one({"id": cliente_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Cliente non trovato")
    return {"ok": True}


@router.patch("/clienti/{cliente_id}/pagato")
async def toggle_pagato(cliente_id: str, payload: PagatoUpdate):
    """Aggiorna lo stato di pagamento del cliente."""
    existing = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Cliente non trovato")
    update = {
        "pagato": bool(payload.pagato),
        "data_pagamento": datetime.now(timezone.utc).date().isoformat() if payload.pagato else None,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.clienti.update_one({"id": cliente_id}, {"$set": update})
    return {"ok": True, "cliente_id": cliente_id, **update}


@router.get("/clienti/{cliente_id}/preventivo.pdf")
async def preventivo_pdf(cliente_id: str):
    doc = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Cliente non trovato")
    lavori_docs = await db.lavori.find({"cliente_id": cliente_id}, {"_id": 0}).sort("data", -1).to_list(500)
    cantiere_doc = await db.cantiere.find_one({"id": "default"}, {"_id": 0}) or {}
    t_current = await get_tariffe_doc()

    pdf_bytes = _build_preventivo_pdf(doc, lavori_docs, cantiere_doc, t_current)
    filename = f"preventivo_{doc.get('cognome','cliente').lower()}_{doc.get('nome','').lower()}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/clienti-nominativi")
async def get_nominativi_clienti():
    """Ritorna la lista distinct di clienti (cognome+nome) presenti nell'archivio, con conteggio anni."""
    pipeline = [
        {"$group": {
            "_id": {"cognome": "$cognome", "nome": "$nome"},
            "anni": {"$addToSet": "$anno"},
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id.cognome": 1, "_id.nome": 1}},
    ]
    out = []
    async for r in db.clienti.aggregate(pipeline):
        cog = (r["_id"].get("cognome") or "").strip()
        nom = (r["_id"].get("nome") or "").strip()
        if not cog and not nom:
            continue
        anni = sorted([a for a in (r.get("anni") or []) if a], reverse=True)
        out.append({"cognome": cog, "nome": nom, "anni": anni, "count": r.get("count", 0)})
    return out


@router.get("/clienti-storico.pdf")
async def storico_cliente_pdf(cognome: str, nome: str):
    """Genera un PDF A4 con lo storico di un cliente (per cognome+nome) diviso per anni."""
    cog_re = {"$regex": f"^{re.escape(cognome.strip())}$", "$options": "i"}
    nom_re = {"$regex": f"^{re.escape(nome.strip())}$", "$options": "i"}
    docs = await db.clienti.find({"cognome": cog_re, "nome": nom_re}, {"_id": 0}).to_list(500)
    if not docs:
        raise HTTPException(404, "Nessun cliente trovato con questo nome")
    docs.sort(key=lambda d: -(d.get("anno") or 0))
    cantiere_doc = await db.cantiere.find_one({"id": "default"}, {"_id": 0}) or {}

    pdf_bytes = _build_storico_pdf(docs, cantiere_doc)
    filename = f"storico_{cognome.lower()}_{nome.lower()}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
