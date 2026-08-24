"""Endpoint generazione PDF contratto firma-cliente."""
import io
import re
import base64 as _b64
from datetime import date
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage

from database import db

router = APIRouter()


class ContrattoRequest(BaseModel):
    cliente_id: str
    testo: str
    titolo: str = "CONTRATTO DI RIMESSAGGIO INVERNALE E MANUTENZIONE"


def _fill_placeholders(testo: str, cliente: dict) -> str:
    """Sostituisce i placeholder {{campo}} con i dati del cliente."""
    posto = cliente.get("posto_barca")
    posto_str = f"#{int(posto):03d}" if posto else "______________"
    potenza = cliente.get("potenza_motore") or 0
    tipo_m = cliente.get("tipo_motore") or ""
    if potenza and tipo_m:
        motore_str = f"{int(potenza)} HP {tipo_m}"
    elif potenza:
        motore_str = f"{int(potenza)} HP"
    else:
        motore_str = "______________"
    lunghezza = cliente.get("lunghezza")
    lung_str = f"{lunghezza:g}" if lunghezza else "______"

    replacements = {
        "{{cognome}}": cliente.get("cognome", "") or "______________",
        "{{nome}}": cliente.get("nome", "") or "______________",
        "{{codice_fiscale}}": cliente.get("codice_fiscale") or "____________________",
        "{{indirizzo}}": cliente.get("indirizzo") or "________________________________________",
        "{{telefono}}": cliente.get("telefono") or "____________",
        "{{email}}": cliente.get("email") or "____________________",
        "{{tipo_barca}}": cliente.get("tipo_barca") or "____________________",
        "{{lunghezza}}": lung_str,
        "{{potenza_motore}}": motore_str,
        "{{posto_barca}}": posto_str,
        "{{data_oggi}}": date.today().strftime("%d/%m/%Y"),
    }
    for k, v in replacements.items():
        testo = testo.replace(k, str(v))
    return testo


def _md_to_html(line: str) -> str:
    """Converte **grassetto** in tag <b> e mette in escape gli angoli."""
    safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)


@router.post("/contratti/pdf")
async def genera_contratto_pdf(payload: ContrattoRequest):
    """Genera un PDF contratto per il cliente indicato con placeholder {{campo}} sostituiti
    dai dati del cliente. Supporta **grassetto** nel testo. Include spazio firma."""
    if not payload.testo.strip():
        raise HTTPException(400, "Il testo del contratto è obbligatorio")

    cliente = await db.clienti.find_one({"id": payload.cliente_id}, {"_id": 0})
    if not cliente:
        raise HTTPException(404, "Cliente non trovato")
    cantiere = await db.cantiere.find_one({"id": "default"}, {"_id": 0}) or {}

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm, topMargin=15*mm, bottomMargin=15*mm,
        title=f"Contratto {cliente.get('cognome','')} {cliente.get('nome','')}"
    )
    styles = getSampleStyleSheet()
    NAVY = colors.HexColor("#0F1B3D")
    TEAK = colors.HexColor("#B0562E")
    MUTED = colors.HexColor("#5B6478")

    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=15, textColor=NAVY, spaceAfter=1, leading=18, alignment=1)
    subtitle = ParagraphStyle("sub", parent=styles["Normal"], fontName="Helvetica-Oblique", fontSize=9, textColor=MUTED, leading=11, alignment=1)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName="Helvetica", fontSize=9.5, textColor=NAVY, leading=13)
    small = ParagraphStyle("small", parent=styles["Normal"], fontName="Helvetica", fontSize=8, textColor=MUTED, leading=10)

    elems = []
    nome_cantiere = (cantiere.get("nome") or "PORTOMARE").upper()
    contatti_parts = [x for x in [
        cantiere.get("indirizzo"),
        " ".join(filter(None, [cantiere.get("cap"), cantiere.get("citta"),
                               (f"({cantiere.get('provincia')})" if cantiere.get("provincia") else "")])),
        cantiere.get("telefono"),
        cantiere.get("email"),
        cantiere.get("piva") and f"P.IVA {cantiere['piva']}",
    ] if x]
    contatti_txt = " · ".join(contatti_parts)

    logo_b64 = cantiere.get("logo_base64") or ""
    logo_cell = Paragraph(f"<b>{nome_cantiere}</b>", ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=14, textColor=NAVY))
    if logo_b64 and "," in logo_b64:
        try:
            raw = _b64.b64decode(logo_b64.split(",", 1)[1])
            logo_cell = RLImage(io.BytesIO(raw), width=28*mm, height=16*mm, kind="proportional")
        except Exception:
            pass

    header_line = Paragraph(f"<font color='#5B6478' size=8>{contatti_txt}</font>", small) if contatti_txt else Paragraph("", small)
    header_tbl = Table([[logo_cell, header_line]], colWidths=[45*mm, 129*mm])
    header_tbl.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE"), ("ALIGN", (1,0), (1,0), "RIGHT")]))
    elems.append(header_tbl)
    sep = Table([[""]], colWidths=[174*mm], rowHeights=[0.8])
    sep.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), TEAK)]))
    elems.append(Spacer(1, 2*mm))
    elems.append(sep)
    elems.append(Spacer(1, 3*mm))

    # Titolo centrato
    elems.append(Paragraph(payload.titolo.upper(), h1))
    elems.append(Spacer(1, 4*mm))

    # Testo contratto (con placeholder sostituiti e **grassetto**)
    testo_finale = _fill_placeholders(payload.testo, cliente)
    lines = testo_finale.split("\n")
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            elems.append(Spacer(1, 1.5*mm))
            continue
        # Titoli sezione (solo **bold** su tutta la riga): usa colore teak
        if stripped.startswith("**") and stripped.endswith("**") and stripped.count("**") == 2:
            titolo_sez = stripped.strip("*").strip()
            sez_style = ParagraphStyle("sez", parent=body, fontName="Helvetica-Bold", fontSize=10, textColor=TEAK, spaceBefore=3, spaceAfter=1.5, leading=13)
            elems.append(Paragraph(_md_to_html(titolo_sez), sez_style))
        else:
            elems.append(Paragraph(_md_to_html(line), body))

    # Spazio firma
    elems.append(Spacer(1, 10*mm))
    firma_tbl = Table([
        [Paragraph("Luogo e data", small), Paragraph("Firma per accettazione e approvazione clausole vessatorie", small)],
        ["", ""],
    ], colWidths=[70*mm, 104*mm], rowHeights=[6*mm, 10*mm])
    firma_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,0), "TOP"),
        ("LINEBELOW", (0,1), (0,1), 0.5, NAVY),
        ("LINEBELOW", (1,1), (1,1), 0.5, NAVY),
        ("TOPPADDING", (0,0), (-1,-1), 0),
        ("BOTTOMPADDING", (0,0), (-1,-1), 0),
    ]))
    elems.append(firma_tbl)

    pdf.build(elems)
    buf.seek(0)
    filename = f"contratto_{(cliente.get('cognome') or 'cliente').lower()}_{(cliente.get('nome') or '').lower()}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
