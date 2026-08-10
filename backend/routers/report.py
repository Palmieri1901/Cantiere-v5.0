"""Report incassi, pagamenti (JSON + PDF)."""
import io
from datetime import date
from typing import Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from database import db
from helpers import _totale_extra, _euro

router = APIRouter()


@router.get("/report/incassi")
async def report_incassi(anno: Optional[int] = None):
    """Sommatorie per categoria su tutti i clienti (filtrabili per anno)."""
    q = {}
    if anno is not None:
        q["anno"] = anno
    docs = await db.clienti.find(q, {"_id": 0}).to_list(10000)

    def s(key):
        return round(sum(float(d.get(key) or 0) for d in docs), 2)

    incasso_sosta = s("costo_sosta")
    incasso_movimentazione = s("costo_movimentazione")
    incasso_taccaggio = s("costo_taccaggio")
    incasso_alaggio = s("costo_alaggio")
    incasso_varo = s("costo_varo")
    incasso_coperture = s("costo_copertura")
    incasso_antivegetativa = s("costo_antivegetativa")
    incasso_scafo_sporco = s("costo_scafo_sporco")
    incasso_lavaggio_inizio = s("costo_lavaggio_inizio")
    incasso_lavaggio_fine = s("costo_lavaggio_fine")
    incasso_motore = s("costo_manutenzione_motore")
    incasso_lavorazioni_extra = round(sum(_totale_extra(d) for d in docs), 2)

    incasso_manodopera = s("costo_manodopera_motore")
    incasso_ricambi = s("costo_ricambi_totale")

    totale = round(
        incasso_sosta + incasso_movimentazione + incasso_taccaggio +
        incasso_alaggio + incasso_varo + incasso_coperture +
        incasso_antivegetativa + incasso_scafo_sporco +
        incasso_lavaggio_inizio + incasso_lavaggio_fine +
        incasso_motore + incasso_lavorazioni_extra, 2
    )

    per_tipo_sosta = {"dentro": 0.0, "fuori": 0.0, "fuori_sede": 0.0, "temporanea": 0.0}
    for d in docs:
        tipo = d.get("tipo_sosta")
        if tipo in per_tipo_sosta:
            client_tot = sum(float(d.get(k) or 0) for k in (
                "costo_sosta","costo_movimentazione","costo_taccaggio",
                "costo_alaggio","costo_varo","costo_copertura",
                "costo_antivegetativa","costo_scafo_sporco",
                "costo_lavaggio_inizio","costo_lavaggio_fine",
                "costo_manutenzione_motore"
            )) + _totale_extra(d)
            per_tipo_sosta[tipo] = round(per_tipo_sosta[tipo] + client_tot, 2)

    return {
        "totale_clienti": len(docs),
        "totale": totale,
        "categorie": {
            "sosta": incasso_sosta,
            "movimentazione_taccaggio": round(incasso_movimentazione + incasso_taccaggio, 2),
            "alaggio_varo": round(incasso_alaggio + incasso_varo, 2),
            "coperture": incasso_coperture,
            "antivegetativa": incasso_antivegetativa,
            "scafo_sporco": incasso_scafo_sporco,
            "lavaggi": round(incasso_lavaggio_inizio + incasso_lavaggio_fine, 2),
            "manutenzione_motore": incasso_motore,
            "lavorazioni_extra": incasso_lavorazioni_extra,
        },
        "motore_dettaglio": {
            "manodopera": incasso_manodopera,
            "ricambi": incasso_ricambi,
        },
        "sosta_dettaglio": {
            "sosta": incasso_sosta,
            "movimentazione": incasso_movimentazione,
            "taccaggio": incasso_taccaggio,
        },
        "alaggio_varo_dettaglio": {
            "alaggio": incasso_alaggio,
            "varo": incasso_varo,
        },
        "lavaggi_dettaglio": {
            "inizio_stagione": incasso_lavaggio_inizio,
            "fine_stagione": incasso_lavaggio_fine,
        },
        "per_tipo_sosta": per_tipo_sosta,
    }


@router.get("/report/pagamenti")
async def report_pagamenti(anno: Optional[int] = None):
    """Elenco clienti con stato pagamento e totale dovuto (per anno)."""
    q = {}
    if anno is not None:
        q["anno"] = anno
    docs = await db.clienti.find(q, {"_id": 0}).to_list(10000)
    docs.sort(key=lambda d: ((d.get("cognome") or "").strip().lower(), (d.get("nome") or "").strip().lower()))

    result = []
    for d in docs:
        totale = sum(float(d.get(k) or 0) for k in (
            "costo_sosta","costo_movimentazione","costo_taccaggio",
            "costo_copertura","costo_alaggio","costo_varo",
            "costo_antivegetativa","costo_scafo_sporco",
            "costo_lavaggio_inizio","costo_lavaggio_fine",
            "costo_manutenzione_motore"
        )) + _totale_extra(d)
        result.append({
            "id": d["id"],
            "nome": d.get("nome",""),
            "cognome": d.get("cognome",""),
            "tipo_barca": d.get("tipo_barca",""),
            "posto_barca": d.get("posto_barca"),
            "tipo_sosta": d.get("tipo_sosta"),
            "totale": round(totale, 2),
            "pagato": bool(d.get("pagato", False)),
            "data_pagamento": d.get("data_pagamento"),
        })

    totale_pagato = sum(c["totale"] for c in result if c["pagato"])
    totale_da_pagare = sum(c["totale"] for c in result if not c["pagato"])
    return {
        "clienti": result,
        "totale_pagato": round(totale_pagato, 2),
        "totale_da_pagare": round(totale_da_pagare, 2),
        "numero_pagati": sum(1 for c in result if c["pagato"]),
        "numero_non_pagati": sum(1 for c in result if not c["pagato"]),
    }


@router.get("/report/pagamenti.pdf")
async def report_pagamenti_pdf(anno: Optional[int] = None, stato: str = "tutti"):
    """Genera PDF stampabile del report pagamenti. stato: tutti|pagati|non_pagati"""
    if stato not in ("tutti", "pagati", "non_pagati"):
        raise HTTPException(400, "stato deve essere 'tutti', 'pagati' o 'non_pagati'")

    q = {}
    if anno is not None:
        q["anno"] = anno
    docs = await db.clienti.find(q, {"_id": 0}).to_list(10000)
    docs.sort(key=lambda d: ((d.get("cognome") or "").strip().lower(), (d.get("nome") or "").strip().lower()))
    cantiere_doc = await db.cantiere.find_one({"id": "default"}, {"_id": 0}) or {}

    rows_all = []
    for d in docs:
        totale = sum(float(d.get(k) or 0) for k in (
            "costo_sosta","costo_movimentazione","costo_taccaggio",
            "costo_copertura","costo_alaggio","costo_varo",
            "costo_antivegetativa","costo_scafo_sporco",
            "costo_lavaggio_inizio","costo_lavaggio_fine",
            "costo_manutenzione_motore"
        )) + _totale_extra(d)
        rows_all.append({
            "cognome": d.get("cognome", ""),
            "nome": d.get("nome", ""),
            "tipo_barca": d.get("tipo_barca", ""),
            "posto_barca": d.get("posto_barca"),
            "totale": round(totale, 2),
            "pagato": bool(d.get("pagato", False)),
            "data_pagamento": d.get("data_pagamento"),
        })

    if stato == "pagati":
        rows = [r for r in rows_all if r["pagato"]]
    elif stato == "non_pagati":
        rows = [r for r in rows_all if not r["pagato"]]
    else:
        rows = rows_all

    tot_pagati = sum(r["totale"] for r in rows_all if r["pagato"])
    tot_non_pagati = sum(r["totale"] for r in rows_all if not r["pagato"])

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm,
        title=f"Report pagamenti {anno or ''}"
    )
    styles = getSampleStyleSheet()
    NAVY = colors.HexColor("#0F1B3D")
    TEAK = colors.HexColor("#B0562E")
    SAND = colors.HexColor("#F3EFE7")
    GREEN = colors.HexColor("#16803C")
    RED = colors.HexColor("#B91C1C")
    MUTED = colors.HexColor("#5B6478")

    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20, textColor=NAVY, spaceAfter=4, leading=24)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName="Helvetica", fontSize=9, textColor=NAVY, leading=12)
    tiny = ParagraphStyle("tiny", parent=styles["Normal"], fontName="Helvetica", fontSize=8, textColor=MUTED, leading=10)

    elems = []
    nome_cantiere = (cantiere_doc.get("nome") or "PORTOMARE").upper()
    stato_label = {"tutti": "Tutti", "pagati": "Solo pagati", "non_pagati": "Solo non pagati"}[stato]
    anno_label = str(anno) if anno else "Tutti gli anni"

    elems.append(Paragraph(f"<b>{nome_cantiere}</b>", h1))
    elems.append(Paragraph(f"<font color='#5B6478' size=9>REPORT PAGAMENTI · Anno {anno_label} · Filtro: {stato_label} · Emesso: {date.today().strftime('%d/%m/%Y')}</font>", body))
    sep = Table([[""]], colWidths=[180*mm], rowHeights=[2])
    sep.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), TEAK)]))
    elems.append(Spacer(1, 3*mm))
    elems.append(sep)
    elems.append(Spacer(1, 5*mm))

    riepilogo = Table([
        [
            Paragraph(f"<b>Clienti totali</b><br/><font size=14>{len(rows_all)}</font>", body),
            Paragraph(f"<b><font color='#16803C'>Pagati</font></b><br/><font size=14 color='#16803C'>{sum(1 for r in rows_all if r['pagato'])} · {_euro(tot_pagati)}</font>", body),
            Paragraph(f"<b><font color='#B91C1C'>Non pagati</font></b><br/><font size=14 color='#B91C1C'>{sum(1 for r in rows_all if not r['pagato'])} · {_euro(tot_non_pagati)}</font>", body),
        ]
    ], colWidths=[60*mm, 60*mm, 60*mm])
    riepilogo.setStyle(TableStyle([
        ("BOX", (0,0), (-1,-1), 0.5, colors.HexColor("#D9D9D9")),
        ("INNERGRID", (0,0), (-1,-1), 0.5, colors.HexColor("#D9D9D9")),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
    ]))
    elems.append(riepilogo)
    elems.append(Spacer(1, 6*mm))

    header = ["Posto", "Cliente", "Barca", "Totale", "Stato", "Data pag."]
    table_data = [header]
    for r in rows:
        stato_cell = "PAGATO" if r["pagato"] else "NON PAGATO"
        table_data.append([
            f"#{int(r['posto_barca']):03d}" if r["posto_barca"] else "—",
            f"{r['cognome']} {r['nome']}".strip(),
            (r["tipo_barca"] or "")[:30],
            _euro(r["totale"]),
            stato_cell,
            r["data_pagamento"] or "—",
        ])
    tot_filtered = sum(r["totale"] for r in rows)
    table_data.append(["", "", "TOTALE", _euro(tot_filtered), "", ""])

    tbl = Table(table_data, colWidths=[18*mm, 52*mm, 40*mm, 28*mm, 26*mm, 22*mm], repeatRows=1)
    n = len(rows)
    style = [
        ("BACKGROUND", (0,0), (-1,0), NAVY),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 8),
        ("ALIGN", (3,0), (3,-1), "RIGHT"),
        ("ALIGN", (0,0), (0,-1), "CENTER"),
        ("ALIGN", (4,0), (4,-1), "CENTER"),
        ("FONTNAME", (0,1), (-1,n), "Helvetica"),
        ("FONTSIZE", (0,1), (-1,n), 8),
        ("TEXTCOLOR", (0,1), (-1,n), NAVY),
        ("ROWBACKGROUNDS", (0,1), (-1,n), [colors.white, SAND]),
        ("LINEBELOW", (0,1), (-1,n), 0.3, colors.HexColor("#D9D9D9")),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("BACKGROUND", (0,-1), (-1,-1), TEAK),
        ("TEXTCOLOR", (0,-1), (-1,-1), colors.white),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,-1), (-1,-1), 10),
        ("SPAN", (0,-1), (2,-1)),
    ]
    for i, r in enumerate(rows, start=1):
        col = GREEN if r["pagato"] else RED
        style.append(("TEXTCOLOR", (4,i), (4,i), col))
        style.append(("FONTNAME", (4,i), (4,i), "Helvetica-Bold"))
    tbl.setStyle(TableStyle(style))
    elems.append(tbl)

    if not rows:
        elems.append(Spacer(1, 4*mm))
        elems.append(Paragraph("<i>Nessun cliente corrisponde al filtro selezionato.</i>", body))

    elems.append(Spacer(1, 8*mm))
    elems.append(Paragraph(
        f"Documento generato automaticamente da {cantiere_doc.get('nome') or 'Portomare'} — {date.today().strftime('%d/%m/%Y %H:%M')}. "
        f"Il totale filtrato include solo i clienti visibili.",
        tiny
    ))

    pdf.build(elems)
    buf.seek(0)
    filename = f"report_pagamenti_{anno_label.replace(' ', '_').lower()}_{stato}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
