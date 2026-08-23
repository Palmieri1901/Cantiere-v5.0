"""Endpoints per Tariffe e listino prezzi."""
import io
from datetime import datetime, timezone, date
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

from database import db, logger
from models import Tariffe, TariffeUpdate
from helpers import get_tariffe_doc, serialize, calcola_costi, _euro

router = APIRouter()


@router.get("/tariffe", response_model=Tariffe)
async def get_tariffe():
    return await get_tariffe_doc()


@router.put("/tariffe", response_model=Tariffe)
async def update_tariffe(payload: TariffeUpdate):
    current = await get_tariffe_doc()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    new_data = current.model_dump()
    new_data.update(updates)
    new_data["updated_at"] = datetime.now(timezone.utc)
    t = Tariffe(**new_data)
    await db.tariffe.update_one({"id": "default"}, {"$set": serialize(t)}, upsert=True)
    return t


@router.post("/tariffe/ricalcola")
async def ricalcola_costi_anno(anno: int):
    """Ricalcola i costi di tutti i clienti dell'anno indicato usando le tariffe correnti."""
    t = await get_tariffe_doc()
    clienti_docs = await db.clienti.find({"anno": anno}, {"_id": 0}).to_list(10000)
    aggiornati = 0
    for c in clienti_docs:
        try:
            auto_costi = calcola_costi(
                float(c.get("lunghezza") or 0),
                str(c.get("tipo_sosta") or "dentro"),
                t,
                float(c.get("potenza_motore") or 0),
                int(c.get("numero_candele") or 4),
                int(c.get("numero_termostati") or 1),
                bool(c.get("antivegetativa_attiva", True)),
                bool(c.get("girante_attivo", True)),
                float(c.get("litri_olio_motore") or 3.0),
                bool(c.get("lavaggio_inizio_attivo", True)),
                bool(c.get("lavaggio_fine_attivo", True)),
                bool(c.get("secondo_motore", False)),
                float(c.get("potenza_motore_2") or 0),
                float(c.get("litri_olio_motore_2") or 3.0),
                int(c.get("numero_candele_2") or 4),
                int(c.get("numero_termostati_2") or 1),
                bool(c.get("girante_2_attivo", True)),
                bool(c.get("scafo_sporco_attivo", False)),
                bool(c.get("copertura_attiva", False)),
                float(c.get("litri_olio_piede") or 1.0),
                float(c.get("litri_olio_piede_2") or 1.0),
                int(c.get("giorni_sosta_temporanea") or 0),
                str(c.get("destinazione_alaggio_varo") or "marina_di_campo"),
                bool(c.get("alaggio_varo_attivo", False)),
                int(c.get("numero_movimenti") or 1),
                bool(c.get("primo_motore_attivo", True)),
                str(c.get("tipo_motore") or "fuoribordo"),
                str(c.get("tipo_motore_2") or "fuoribordo"),
            )
            auto_costi.pop("ricambi_dettaglio", None)
            auto_costi.pop("ricambi_2_dettaglio", None)

            override = bool(c.get("override_costi", False))
            manual_av = bool(c.get("alaggio_varo_attivo", False)) and str(c.get("destinazione_alaggio_varo")) == "altra"

            updates = {}
            for k, v in auto_costi.items():
                if override:
                    continue
                if manual_av and k in ("costo_alaggio", "costo_varo"):
                    continue
                updates[k] = v
            if updates:
                updates["updated_at"] = datetime.now(timezone.utc).isoformat()
                await db.clienti.update_one({"id": c["id"]}, {"$set": updates})
                aggiornati += 1
        except Exception as e:
            logger.warning(f"Ricalcolo cliente {c.get('id')} fallito: {e}")
    return {"ok": True, "anno": anno, "aggiornati": aggiornati, "totali": len(clienti_docs)}


@router.get("/tariffe/listino.pdf")
async def listino_prezzi_pdf():
    """Genera il listino prezzi ufficiale su carta intestata del cantiere."""
    t = await get_tariffe_doc()
    cantiere = await db.cantiere.find_one({"id": "default"}, {"_id": 0}) or {}

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm, topMargin=12*mm, bottomMargin=12*mm,
        title=f"Listino prezzi — {cantiere.get('nome') or 'Cantiere Nautico'}"
    )
    styles = getSampleStyleSheet()
    NAVY = colors.HexColor("#0F1B3D")
    TEAK = colors.HexColor("#B0562E")
    SAND = colors.HexColor("#F3EFE7")
    MUTED = colors.HexColor("#5B6478")

    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, textColor=NAVY, spaceAfter=1, leading=20)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=9, textColor=TEAK, spaceBefore=3, spaceAfter=1, leading=11)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName="Helvetica", fontSize=8, textColor=NAVY, leading=10)
    tiny = ParagraphStyle("tiny", parent=styles["Normal"], fontName="Helvetica", fontSize=7, textColor=MUTED, leading=9)
    date_style = ParagraphStyle("date", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, textColor=TEAK, leading=12)

    elems = []
    nome_cantiere = (cantiere.get("nome") or "CANTIERE NAUTICO").upper()
    contatti = " · ".join([x for x in [
        cantiere.get("indirizzo"),
        cantiere.get("telefono"),
        cantiere.get("email"),
        cantiere.get("piva") and f"P.IVA {cantiere['piva']}",
    ] if x])

    logo_b64 = cantiere.get("logo_base64")
    left_col = [Paragraph(f"<b>{nome_cantiere}</b>", h1)]
    if cantiere.get("slogan"):
        left_col.append(Paragraph(f"<font color='#5B6478' size=8><i>{cantiere['slogan']}</i></font>", body))
    if contatti:
        left_col.append(Spacer(1, 1*mm))
        left_col.append(Paragraph(f"<font color='#5B6478' size=8>{contatti}</font>", body))

    if logo_b64:
        try:
            import base64 as _b64
            raw = _b64.b64decode(logo_b64.split(",")[-1] if "," in logo_b64 else logo_b64)
            img = Image(io.BytesIO(raw), width=22*mm, height=22*mm, kind="proportional")
            header_tbl = Table([[left_col, img]], colWidths=[150*mm, 30*mm])
        except Exception:
            header_tbl = Table([[left_col, ""]], colWidths=[150*mm, 30*mm])
    else:
        header_tbl = Table([[left_col, ""]], colWidths=[150*mm, 30*mm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    elems.append(header_tbl)
    elems.append(Spacer(1, 2*mm))

    sep = Table([[""]], colWidths=[180*mm], rowHeights=[1.5])
    sep.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), TEAK)]))
    elems.append(sep)
    elems.append(Spacer(1, 2*mm))

    title_tbl = Table([[
        Paragraph("<b>LISTINO PREZZI</b> · <font color='#5B6478' size=8>Tariffario in vigore</font>", h1),
        Paragraph(f"Data emissione · <font size=12 color='#B0562E'>{date.today().strftime('%d/%m/%Y')}</font>", date_style),
    ]], colWidths=[110*mm, 70*mm])
    title_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("ALIGN", (1,0), (1,0), "RIGHT"),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    elems.append(title_tbl)
    elems.append(Spacer(1, 2*mm))

    groups = [
        ("SOSTA", [
            ("Sosta al coperto", "sosta_dentro_per_metro", "€ / metro / anno"),
            ("Sosta su piazzale (fuori)", "sosta_fuori_per_metro", "€ / metro / anno"),
            ("Sosta temporanea", "sosta_temporanea_giornaliera", "€ al mt / giorno"),
            ("Movimentazione (fuori sede)", "costo_movimentazione_per_metro", "€ / metro"),
            ("Taccaggio (fuori sede)", "costo_taccaggio_per_metro", "€ / metro"),
        ]),
        ("ALAGGIO & VARO", [
            ("Alaggio · fino a 5 m", "alaggio_fino_5m", "forfait"),
            ("Alaggio · oltre 5 m", "alaggio_oltre_5m_per_metro", "forfait"),
            ("Varo · fino a 5 m", "varo_fino_5m", "forfait"),
            ("Varo · oltre 5 m", "varo_oltre_5m_per_metro", "forfait"),
        ]),
        ("COPERTURA & TRATTAMENTI SCAFO", [
            ("Copertura", "copertura_per_metro", "€ / metro"),
            ("Antivegetativa", "antivegetativa_per_metro", "€ / metro"),
            ("Maggiorazione scafo sporco", "maggiorazione_scafo_sporco_per_metro", "€ / metro"),
            ("Lavaggio inizio stagione", "costo_lavaggio_inizio_stagione", "€ / metro"),
            ("Lavaggio fine stagione", "costo_lavaggio_fine_stagione", "€ / metro"),
        ]),
        ("MANODOPERA MOTORE", [
            ("Manodopera motore (qualsiasi HP)", "motore_labor", "forfait"),
            ("Maggiorazione entrobordo", "maggiorazione_entrobordo", "€ (aggiunto se motore entrobordo)"),
        ]),
        ("RICAMBI & MATERIALI", [
            ("Girante", "costo_girante", "cad."),
            ("Olio motore", "costo_olio_motore", "€ / litro"),
            ("Filtro olio", "costo_filtro_olio", "cad."),
            ("Candela", "costo_candela", "cad."),
            ("Termostato", "costo_termostato", "cad."),
            ("Olio piede", "costo_olio_piede", "€ / litro"),
            ("Kit anodi interni", "costo_anodi_interni", "forfait"),
            ("Kit anodi esterni", "costo_anodi_esterni", "forfait"),
            ("Ingrassaggio completo", "costo_ingrassaggio", "forfait"),
        ]),
    ]

    tariffe_dict = t.model_dump()
    for titolo, voci in groups:
        elems.append(Paragraph(titolo, h2))
        rows = [["VOCE", "UNITÀ", "IMPORTO"]]
        for label, key, unit in voci:
            val = tariffe_dict.get(key, 0) or 0
            rows.append([label, unit, _euro(float(val))])
        tbl = Table(rows, colWidths=[100*mm, 40*mm, 40*mm])
        n = len(rows) - 1
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NAVY),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 7),
            ("ALIGN", (2,0), (2,-1), "RIGHT"),
            ("ALIGN", (1,0), (1,-1), "CENTER"),
            ("FONTNAME", (0,1), (-1,n), "Helvetica"),
            ("FONTSIZE", (0,1), (-1,n), 8),
            ("TEXTCOLOR", (0,1), (-1,n), NAVY),
            ("ROWBACKGROUNDS", (0,1), (-1,n), [colors.white, SAND]),
            ("LINEBELOW", (0,1), (-1,n), 0.3, colors.HexColor("#D9D9D9")),
            ("TOPPADDING", (0,0), (-1,-1), 1),
            ("BOTTOMPADDING", (0,0), (-1,-1), 1),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ]))
        elems.append(tbl)

    elems.append(Spacer(1, 2*mm))
    elems.append(Paragraph(
        f"Prezzi al netto di IVA salvo diversa indicazione · Listino aggiornato al {date.today().strftime('%d/%m/%Y')} · "
        f"Per preventivi personalizzati contattare {cantiere.get('telefono') or cantiere.get('email') or 'il cantiere'}.",
        tiny
    ))

    pdf.build(elems)
    buf.seek(0)
    filename = f"listino_prezzi_{date.today().strftime('%Y%m%d')}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
