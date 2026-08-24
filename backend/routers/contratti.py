"""Endpoint generazione PDF contratto firma-cliente."""
import io
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
    titolo: str = "CONTRATTO DI RIMESSAGGIO E MANUTENZIONE"


@router.post("/contratti/pdf")
async def genera_contratto_pdf(payload: ContrattoRequest):
    """Genera un PDF contratto per il cliente indicato, con testo/clausole personalizzabili
    e spazio per la firma. Non salva nulla in DB."""
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
    SAND = colors.HexColor("#F3EFE7")
    MUTED = colors.HexColor("#5B6478")

    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, textColor=NAVY, spaceAfter=4, leading=22)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10, textColor=TEAK, leading=13, letterSpace=1.5, spaceBefore=6, spaceAfter=3)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName="Helvetica", fontSize=10, textColor=NAVY, leading=14)
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
    logo_cell = Paragraph(f"<b>{nome_cantiere}</b>", ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=18, textColor=NAVY))
    if logo_b64 and "," in logo_b64:
        try:
            raw = _b64.b64decode(logo_b64.split(",", 1)[1])
            logo_cell = RLImage(io.BytesIO(raw), width=30*mm, height=18*mm, kind="proportional")
        except Exception:
            pass

    header_tbl = Table([
        [logo_cell,
         Paragraph(f"<para align=right><font color='#5B6478' size=8>CONTRATTO</font><br/>"
                   f"<font size=12 color='#B0562E'><b>{date.today().strftime('%d/%m/%Y')}</b></font></para>", body)]
    ], colWidths=[95*mm, 79*mm])
    header_tbl.setStyle(TableStyle([("VALIGN", (0,0), (-1,-1), "MIDDLE")]))
    elems.append(header_tbl)
    if contatti_txt:
        elems.append(Spacer(1, 1*mm))
        elems.append(Paragraph(f"<font color='#5B6478' size=8>{contatti_txt}</font>", body))
    sep = Table([[""]], colWidths=[174*mm], rowHeights=[1.5])
    sep.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), TEAK)]))
    elems.append(Spacer(1, 3*mm))
    elems.append(sep)
    elems.append(Spacer(1, 4*mm))

    # Titolo
    elems.append(Paragraph(f"<b>{payload.titolo}</b>", h1))
    elems.append(Spacer(1, 3*mm))

    # Anagrafica cliente
    elems.append(Paragraph("DATI CLIENTE", h2))
    tbl_data = [
        ["Cliente", f"{cliente.get('cognome','')} {cliente.get('nome','')}"],
        ["Codice Fiscale", cliente.get("codice_fiscale") or "—"],
        ["Indirizzo", cliente.get("indirizzo") or "—"],
        ["Contatti", " · ".join([x for x in [cliente.get("telefono"), cliente.get("cellulare"), cliente.get("email")] if x]) or "—"],
        ["Imbarcazione", f"{cliente.get('tipo_barca') or '—'} · L. {cliente.get('lunghezza') or '—'} m"],
        ["Posto barca", f"#{int(cliente['posto_barca']):03d}" if cliente.get("posto_barca") else "—"],
    ]
    info_tbl = Table(tbl_data, colWidths=[40*mm, 134*mm])
    info_tbl.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("TEXTCOLOR", (0,0), (0,-1), MUTED),
        ("TEXTCOLOR", (1,0), (1,-1), NAVY),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, SAND]),
        ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#D9D9D9")),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
    ]))
    elems.append(info_tbl)

    # Testo contratto
    elems.append(Spacer(1, 5*mm))
    elems.append(Paragraph("CLAUSOLE E CONDIZIONI", h2))
    for para in payload.testo.split("\n"):
        if para.strip():
            safe = para.replace("<", "&lt;").replace(">", "&gt;")
            elems.append(Paragraph(safe, body))
        else:
            elems.append(Spacer(1, 2*mm))

    # Spazio firma
    elems.append(Spacer(1, 12*mm))
    firma_tbl = Table([
        [Paragraph("Luogo e data", small), Paragraph("Firma per accettazione", small)],
        [Paragraph("_" * 40, body), Paragraph("_" * 40, body)],
    ], colWidths=[87*mm, 87*mm])
    firma_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "BOTTOM"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
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
