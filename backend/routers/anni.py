"""Gestione anni: lista, apertura (con duplicazione clienti), eliminazione."""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from database import db, logger
from models import ApriAnnoRequest, Cliente
from helpers import get_tariffe_doc, calcola_costi, serialize

router = APIRouter()


@router.get("/anni")
async def list_anni():
    """Ritorna la lista degli anni con conteggio clienti per anno."""
    now_year = datetime.now().year
    docs = await db.clienti.find({}, {"anno": 1, "_id": 0}).to_list(20000)
    counts = {}
    for d in docs:
        y = d.get("anno") or now_year
        counts[y] = counts.get(y, 0) + 1
    if now_year not in counts:
        counts[now_year] = counts.get(now_year, 0)

    anni_sorted = sorted(counts.keys(), reverse=True)
    return {
        "anno_corrente": now_year,
        "anni": [{"anno": y, "clienti": counts[y]} for y in anni_sorted],
    }


@router.post("/anni/apri")
async def apri_anno(payload: ApriAnnoRequest):
    """Apre un nuovo anno. Se duplica_da è specificato, copia i clienti da quell'anno (ricalcolando i costi con le tariffe correnti)."""
    if payload.anno < 2000 or payload.anno > 2100:
        raise HTTPException(400, "Anno non valido")

    existing_count = await db.clienti.count_documents({"anno": payload.anno})

    duplicati = 0
    if payload.duplica_da is not None and existing_count == 0:
        origine = await db.clienti.find({"anno": payload.duplica_da}, {"_id": 0}).to_list(10000)
        t = await get_tariffe_doc()
        for c in origine:
            new_id = str(uuid.uuid4())
            auto_costi = calcola_costi(
                c.get("lunghezza", 0), c.get("tipo_sosta", "dentro"), t,
                c.get("potenza_motore", 0) or 0,
                c.get("numero_candele", 4) or 4,
                c.get("numero_termostati", 1) or 1,
                bool(c.get("antivegetativa_attiva", True)),
                bool(c.get("girante_attivo", True)),
                float(c.get("litri_olio_motore", 3.0) or 3.0),
                bool(c.get("lavaggio_inizio_attivo", True)),
                bool(c.get("lavaggio_fine_attivo", True)),
                bool(c.get("secondo_motore", False)),
                float(c.get("potenza_motore_2", 0) or 0),
                float(c.get("litri_olio_motore_2", 3.0) or 3.0),
                int(c.get("numero_candele_2", 4) or 4),
                int(c.get("numero_termostati_2", 1) or 1),
                bool(c.get("girante_2_attivo", True)),
                bool(c.get("scafo_sporco_attivo", False)),
                bool(c.get("copertura_attiva", False)),
                float(c.get("litri_olio_piede", 1.0) or 1.0),
                float(c.get("litri_olio_piede_2", 1.0) or 1.0),
                int(c.get("giorni_sosta_temporanea", 0) or 0),
                str(c.get("destinazione_alaggio_varo") or "marina_di_campo"),
                bool(c.get("alaggio_varo_attivo", False)),
                int(c.get("numero_movimenti") or 1),
                bool(c.get("primo_motore_attivo", True)),
                str(c.get("tipo_motore") or "fuoribordo"),
                str(c.get("tipo_motore_2") or "fuoribordo"),
            )
            auto_costi.pop("ricambi_dettaglio", None)
            auto_costi.pop("ricambi_2_dettaglio", None)

            data = {**c, **auto_costi, "id": new_id, "anno": payload.anno,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    "note_lavori": "", "scadenza_antivegetativa": None, "scadenza_manutenzione": None}
            try:
                cli = Cliente(**{k: v for k, v in data.items() if k in Cliente.model_fields or k in ("posto_barca", "scadenza_antivegetativa", "scadenza_manutenzione")})
                await db.clienti.insert_one(serialize(cli))
                duplicati += 1
            except Exception as e:
                logger.warning(f"Errore duplicazione cliente: {e}")

    return {"ok": True, "anno": payload.anno, "duplicati": duplicati, "gia_esistenti": existing_count}


@router.delete("/anni/{anno}")
async def elimina_anno(anno: int):
    """Elimina tutti i clienti e lavori di un anno specifico."""
    res_clienti = await db.clienti.delete_many({"anno": anno})
    res_lavori = await db.lavori.delete_many({"anno": anno})
    return {
        "ok": True,
        "anno": anno,
        "clienti_eliminati": res_clienti.deleted_count,
        "lavori_eliminati": res_lavori.deleted_count,
    }
