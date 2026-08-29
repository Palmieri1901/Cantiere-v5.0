"""Endpoint preventivo veloce (senza salvataggio cliente)."""
import io
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from database import db
from models import PreventivoInline
from helpers import get_tariffe_doc, calcola_costi, _sanitize_lavorazioni_extra
from pdf_builders import _build_preventivo_pdf

router = APIRouter()


@router.post("/preventivo/pdf")
async def preventivo_pdf_inline(payload: PreventivoInline):
    """Genera un PDF preventivo al volo senza salvare in DB. Basta nome+cognome."""
    if not payload.nome.strip() or not payload.cognome.strip():
        raise HTTPException(400, "Nome e cognome sono obbligatori")
    if payload.tipo_sosta not in ("dentro", "fuori", "fuori_sede", "temporanea"):
        payload.tipo_sosta = "dentro"

    t = await get_tariffe_doc()
    cantiere_doc = await db.cantiere.find_one({"id": "default"}, {"_id": 0}) or {}

    lunghezza = float(payload.lunghezza or 0)
    auto_costi = calcola_costi(
        lunghezza, payload.tipo_sosta or "dentro", t,
        float(payload.potenza_motore or 0),
        int(payload.numero_candele or 4),
        int(payload.numero_termostati or 1),
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
        int(payload.giorni_sosta_temporanea if payload.giorni_sosta_temporanea is not None else 0),
        (payload.destinazione_alaggio_varo or "marina_di_campo"),
        bool(payload.alaggio_varo_attivo if payload.alaggio_varo_attivo is not None else False),
        int(payload.numero_movimenti or 1),
        bool(payload.primo_motore_attivo if payload.primo_motore_attivo is not None else True),
        (payload.tipo_motore or "fuoribordo"),
        (payload.tipo_motore_2 or "fuoribordo"),
        bool(payload.filtro_olio_attivo if payload.filtro_olio_attivo is not None else True),
        bool(payload.anodi_interni_attivo if payload.anodi_interni_attivo is not None else True),
        bool(payload.anodi_esterni_attivo if payload.anodi_esterni_attivo is not None else True),
        bool(payload.olio_piede_attivo if payload.olio_piede_attivo is not None else True),
        bool(payload.filtro_olio_2_attivo if payload.filtro_olio_2_attivo is not None else True),
        bool(payload.anodi_interni_2_attivo if payload.anodi_interni_2_attivo is not None else True),
        bool(payload.anodi_esterni_2_attivo if payload.anodi_esterni_2_attivo is not None else True),
        bool(payload.olio_piede_2_attivo if payload.olio_piede_2_attivo is not None else True),
    )
    auto_costi.pop("ricambi_dettaglio", None)
    auto_costi.pop("ricambi_2_dettaglio", None)

    doc = payload.model_dump()
    manual_alaggio_varo = (payload.alaggio_varo_attivo and payload.destinazione_alaggio_varo == "altra")
    for k, v in auto_costi.items():
        if manual_alaggio_varo and k in ("costo_alaggio", "costo_varo"):
            existing_val = doc.get(k)
            doc[k] = float(existing_val) if existing_val is not None else 0.0
        else:
            doc[k] = v
    doc["lavorazioni_extra"] = _sanitize_lavorazioni_extra(doc.get("lavorazioni_extra"))

    pdf_bytes = _build_preventivo_pdf(doc, [], cantiere_doc, t)
    filename = f"preventivo_{payload.cognome.strip()}_{payload.nome.strip()}.pdf".replace(" ", "_")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
