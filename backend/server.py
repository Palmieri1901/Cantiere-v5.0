from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import io
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone, date
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI(title="Cantiere Nautico API")
api_router = APIRouter(prefix="/api")

TOTAL_POSTI = 200


# ---------- MODELS ----------

class Tariffe(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: "default")
    copertura_per_metro: float = 45.0
    # Alaggio/Varo a scaglioni per lunghezza
    alaggio_fino_5m: float = 90.0
    alaggio_oltre_5m_per_metro: float = 25.0
    varo_fino_5m: float = 90.0
    varo_oltre_5m_per_metro: float = 25.0
    antivegetativa_per_metro: float = 60.0
    # Manodopera motore a scaglioni di potenza HP
    motore_labor_fino_40hp: float = 180.0
    motore_labor_40_150hp: float = 320.0
    motore_labor_oltre_150hp: float = 550.0
    # Ricambi motore (costo unitario)
    costo_girante: float = 45.0
    costo_olio_motore: float = 55.0
    costo_filtro_olio: float = 18.0
    costo_candela: float = 12.0
    costo_termostato: float = 35.0
    costo_olio_piede: float = 25.0
    # Sosta
    sosta_dentro_per_metro: float = 180.0
    sosta_fuori_per_metro: float = 120.0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TariffeUpdate(BaseModel):
    copertura_per_metro: Optional[float] = None
    alaggio_fino_5m: Optional[float] = None
    alaggio_oltre_5m_per_metro: Optional[float] = None
    varo_fino_5m: Optional[float] = None
    varo_oltre_5m_per_metro: Optional[float] = None
    antivegetativa_per_metro: Optional[float] = None
    motore_labor_fino_40hp: Optional[float] = None
    motore_labor_40_150hp: Optional[float] = None
    motore_labor_oltre_150hp: Optional[float] = None
    costo_girante: Optional[float] = None
    costo_olio_motore: Optional[float] = None
    costo_filtro_olio: Optional[float] = None
    costo_candela: Optional[float] = None
    costo_termostato: Optional[float] = None
    costo_olio_piede: Optional[float] = None
    sosta_dentro_per_metro: Optional[float] = None
    sosta_fuori_per_metro: Optional[float] = None


class Cliente(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    cognome: str
    tipo_barca: str
    lunghezza: float  # metri
    tipo_sosta: str  # "dentro" | "fuori"
    posto_barca: Optional[int] = None  # 1-200
    telefono: Optional[str] = ""
    email: Optional[str] = ""
    # Motore
    potenza_motore: float = 0.0  # HP
    numero_candele: int = 4
    numero_termostati: int = 1
    # Costi (auto o manuali)
    costo_sosta: float = 0.0
    costo_copertura: float = 0.0
    costo_alaggio: float = 0.0
    costo_varo: float = 0.0
    costo_antivegetativa: float = 0.0
    costo_manutenzione_motore: float = 0.0
    # Breakdown ricambi (informativo)
    costo_ricambi_totale: float = 0.0
    costo_manodopera_motore: float = 0.0
    # Override flags: se true, valore non ricalcolato automaticamente
    override_costi: bool = False
    # Lavori
    note_lavori: str = ""
    scadenza_antivegetativa: Optional[str] = None  # ISO date string
    scadenza_manutenzione: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClienteCreate(BaseModel):
    nome: str
    cognome: str
    tipo_barca: str
    lunghezza: float
    tipo_sosta: str
    posto_barca: Optional[int] = None
    telefono: Optional[str] = ""
    email: Optional[str] = ""
    potenza_motore: Optional[float] = 0.0
    numero_candele: Optional[int] = 4
    numero_termostati: Optional[int] = 1
    costo_sosta: Optional[float] = None
    costo_copertura: Optional[float] = None
    costo_alaggio: Optional[float] = None
    costo_varo: Optional[float] = None
    costo_antivegetativa: Optional[float] = None
    costo_manutenzione_motore: Optional[float] = None
    override_costi: bool = False
    note_lavori: str = ""
    scadenza_antivegetativa: Optional[str] = None
    scadenza_manutenzione: Optional[str] = None


# ---------- HELPERS ----------

def serialize(obj: BaseModel) -> dict:
    d = obj.model_dump()
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


def deserialize_cliente(doc: dict) -> dict:
    if doc is None:
        return None
    doc.pop('_id', None)
    for k in ('created_at', 'updated_at'):
        if isinstance(doc.get(k), str):
            try:
                doc[k] = datetime.fromisoformat(doc[k])
            except Exception:
                pass
    return doc


async def get_tariffe_doc() -> Tariffe:
    doc = await db.tariffe.find_one({"id": "default"}, {"_id": 0})
    if not doc:
        t = Tariffe()
        await db.tariffe.insert_one(serialize(t))
        return t
    return Tariffe(**doc)


def calcola_alaggio(lunghezza: float, t: Tariffe) -> float:
    """Alaggio: forfait fino a 5m, sopra 5m tariffa a metro."""
    if lunghezza <= 5:
        return round(t.alaggio_fino_5m, 2)
    return round(lunghezza * t.alaggio_oltre_5m_per_metro, 2)


def calcola_varo(lunghezza: float, t: Tariffe) -> float:
    if lunghezza <= 5:
        return round(t.varo_fino_5m, 2)
    return round(lunghezza * t.varo_oltre_5m_per_metro, 2)


def calcola_motore_labor(potenza_hp: float, t: Tariffe) -> float:
    """Manodopera manutenzione motore in base a potenza HP."""
    if potenza_hp <= 0:
        return 0.0
    if potenza_hp <= 40:
        return round(t.motore_labor_fino_40hp, 2)
    if potenza_hp <= 150:
        return round(t.motore_labor_40_150hp, 2)
    return round(t.motore_labor_oltre_150hp, 2)


def calcola_ricambi(numero_candele: int, numero_termostati: int, t: Tariffe) -> dict:
    """Costo ricambi motore: girante, olio motore, filtro olio, candele, termostati, olio piede."""
    nc = int(numero_candele or 0)
    nt = int(numero_termostati or 0)
    return {
        "girante": round(t.costo_girante, 2),
        "olio_motore": round(t.costo_olio_motore, 2),
        "filtro_olio": round(t.costo_filtro_olio, 2),
        "candele": round(nc * t.costo_candela, 2),
        "termostati": round(nt * t.costo_termostato, 2),
        "olio_piede": round(t.costo_olio_piede, 2),
    }


def calcola_costi(lunghezza: float, tipo_sosta: str, t: Tariffe,
                  potenza_motore: float = 0.0, numero_candele: int = 4,
                  numero_termostati: int = 1) -> dict:
    """Calcola costi automatici in base a lunghezza, tipo sosta e motore."""
    manodopera = calcola_motore_labor(potenza_motore, t)
    ricambi = calcola_ricambi(numero_candele, numero_termostati, t)
    ricambi_tot = round(sum(ricambi.values()), 2)
    motore_tot = round(manodopera + ricambi_tot, 2)

    base = {
        "costo_antivegetativa": round(lunghezza * t.antivegetativa_per_metro, 2),
        "costo_manutenzione_motore": motore_tot,
        "costo_manodopera_motore": manodopera,
        "costo_ricambi_totale": ricambi_tot,
        "ricambi_dettaglio": ricambi,
    }

    if tipo_sosta == "fuori":
        base.update({
            "costo_sosta": round(lunghezza * t.sosta_fuori_per_metro, 2),
            "costo_copertura": round(lunghezza * t.copertura_per_metro, 2),
            "costo_alaggio": calcola_alaggio(lunghezza, t),
            "costo_varo": calcola_varo(lunghezza, t),
        })
    else:
        base.update({
            "costo_sosta": round(lunghezza * t.sosta_dentro_per_metro, 2),
            "costo_copertura": 0.0,
            "costo_alaggio": 0.0,
            "costo_varo": 0.0,
        })
    return base


# ---------- ROUTES ----------

@api_router.get("/")
async def root():
    return {"message": "Cantiere Nautico API - OK"}


# --- Tariffe ---
@api_router.get("/tariffe", response_model=Tariffe)
async def get_tariffe():
    return await get_tariffe_doc()


@api_router.put("/tariffe", response_model=Tariffe)
async def update_tariffe(payload: TariffeUpdate):
    current = await get_tariffe_doc()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    new_data = current.model_dump()
    new_data.update(updates)
    new_data["updated_at"] = datetime.now(timezone.utc)
    t = Tariffe(**new_data)
    await db.tariffe.update_one({"id": "default"}, {"$set": serialize(t)}, upsert=True)
    return t


# --- Preview costi ---
@api_router.get("/calcola-costi")
async def preview_costi(lunghezza: float, tipo_sosta: str,
                        potenza_motore: float = 0.0,
                        numero_candele: int = 4,
                        numero_termostati: int = 1):
    if tipo_sosta not in ("dentro", "fuori"):
        raise HTTPException(400, "tipo_sosta deve essere 'dentro' o 'fuori'")
    t = await get_tariffe_doc()
    return calcola_costi(lunghezza, tipo_sosta, t, potenza_motore, numero_candele, numero_termostati)


# --- Clienti ---
@api_router.get("/clienti", response_model=List[Cliente])
async def list_clienti():
    docs = await db.clienti.find({}, {"_id": 0}).to_list(1000)
    return [Cliente(**deserialize_cliente(d)) for d in docs]


@api_router.get("/clienti/{cliente_id}", response_model=Cliente)
async def get_cliente(cliente_id: str):
    doc = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Cliente non trovato")
    return Cliente(**deserialize_cliente(doc))


@api_router.post("/clienti", response_model=Cliente)
async def create_cliente(payload: ClienteCreate):
    if payload.tipo_sosta not in ("dentro", "fuori"):
        raise HTTPException(400, "tipo_sosta deve essere 'dentro' o 'fuori'")
    if payload.posto_barca is not None:
        if payload.posto_barca < 1 or payload.posto_barca > TOTAL_POSTI:
            raise HTTPException(400, f"Posto barca deve essere tra 1 e {TOTAL_POSTI}")
        existing = await db.clienti.find_one({"posto_barca": payload.posto_barca})
        if existing:
            raise HTTPException(400, f"Posto barca {payload.posto_barca} già occupato")

    t = await get_tariffe_doc()
    auto_costi = calcola_costi(
        payload.lunghezza, payload.tipo_sosta, t,
        payload.potenza_motore or 0,
        payload.numero_candele or 4,
        payload.numero_termostati or 1,
    )
    # Rimuovi dettaglio non-modello prima di applicarlo
    ricambi_dettaglio = auto_costi.pop("ricambi_dettaglio", None)

    data = payload.model_dump()
    # Se override non attivo → usa costi calcolati; altrimenti usa quelli inseriti (fallback 0 se None)
    for k in auto_costi:
        val = data.get(k)
        if not payload.override_costi or val is None:
            data[k] = auto_costi[k]
        else:
            data[k] = val

    cliente = Cliente(**{k: v for k, v in data.items() if v is not None or k in ("posto_barca", "scadenza_antivegetativa", "scadenza_manutenzione")})
    await db.clienti.insert_one(serialize(cliente))
    return cliente


@api_router.put("/clienti/{cliente_id}", response_model=Cliente)
async def update_cliente(cliente_id: str, payload: ClienteCreate):
    existing = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Cliente non trovato")

    if payload.tipo_sosta not in ("dentro", "fuori"):
        raise HTTPException(400, "tipo_sosta deve essere 'dentro' o 'fuori'")

    if payload.posto_barca is not None:
        if payload.posto_barca < 1 or payload.posto_barca > TOTAL_POSTI:
            raise HTTPException(400, f"Posto barca deve essere tra 1 e {TOTAL_POSTI}")
        conflict = await db.clienti.find_one({"posto_barca": payload.posto_barca, "id": {"$ne": cliente_id}})
        if conflict:
            raise HTTPException(400, f"Posto barca {payload.posto_barca} già occupato")

    t = await get_tariffe_doc()
    auto_costi = calcola_costi(
        payload.lunghezza, payload.tipo_sosta, t,
        payload.potenza_motore or 0,
        payload.numero_candele or 4,
        payload.numero_termostati or 1,
    )
    auto_costi.pop("ricambi_dettaglio", None)

    data = payload.model_dump()
    for k in auto_costi:
        val = data.get(k)
        if not payload.override_costi or val is None:
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


@api_router.delete("/clienti/{cliente_id}")
async def delete_cliente(cliente_id: str):
    res = await db.clienti.delete_one({"id": cliente_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Cliente non trovato")
    return {"ok": True}


# --- Stats ---
@api_router.get("/stats")
async def stats():
    docs = await db.clienti.find({}, {"_id": 0}).to_list(1000)
    dentro = sum(1 for d in docs if d.get("tipo_sosta") == "dentro")
    fuori = sum(1 for d in docs if d.get("tipo_sosta") == "fuori")
    occupati = sum(1 for d in docs if d.get("posto_barca"))
    liberi = TOTAL_POSTI - occupati

    entrate_totali = 0.0
    for d in docs:
        entrate_totali += sum([
            d.get("costo_sosta", 0) or 0,
            d.get("costo_copertura", 0) or 0,
            d.get("costo_alaggio", 0) or 0,
            d.get("costo_varo", 0) or 0,
            d.get("costo_antivegetativa", 0) or 0,
            d.get("costo_manutenzione_motore", 0) or 0,
        ])

    # Scadenze prossime (entro 30 giorni)
    from datetime import timedelta
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
                            "nome": f"{d.get('nome','')} {d.get('cognome','')}",
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
        "entrate_totali": round(entrate_totali, 2),
        "scadenze_prossime": scadenze[:10],
    }


# --- Posti barca ---
@api_router.get("/posti-barca")
async def posti_barca():
    docs = await db.clienti.find({"posto_barca": {"$ne": None}}, {"_id": 0}).to_list(1000)
    occupati_map = {d["posto_barca"]: d for d in docs if d.get("posto_barca")}
    result = []
    for i in range(1, TOTAL_POSTI + 1):
        c = occupati_map.get(i)
        result.append({
            "numero": i,
            "occupato": c is not None,
            "cliente_id": c.get("id") if c else None,
            "cliente_nome": f"{c.get('nome','')} {c.get('cognome','')}" if c else None,
            "tipo_sosta": c.get("tipo_sosta") if c else None,
            "tipo_barca": c.get("tipo_barca") if c else None,
        })
    return result


# --- Export ---
@api_router.get("/export/clienti.csv")
async def export_csv():
    docs = await db.clienti.find({}, {"_id": 0}).to_list(1000)
    if not docs:
        docs = [{}]
    df = pd.DataFrame(docs)
    if not df.empty:
        cols_order = ["posto_barca", "nome", "cognome", "tipo_barca", "lunghezza", "tipo_sosta",
                      "telefono", "email", "costo_sosta", "costo_copertura", "costo_alaggio",
                      "costo_varo", "costo_antivegetativa", "costo_manutenzione_motore",
                      "scadenza_antivegetativa", "scadenza_manutenzione", "note_lavori"]
        cols = [c for c in cols_order if c in df.columns] + [c for c in df.columns if c not in cols_order]
        df = df[cols]

    buf = io.StringIO()
    df.to_csv(buf, index=False, sep=";")
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=clienti_cantiere.csv"}
    )


@api_router.get("/export/clienti.xlsx")
async def export_xlsx():
    docs = await db.clienti.find({}, {"_id": 0}).to_list(1000)
    df = pd.DataFrame(docs) if docs else pd.DataFrame()
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        (df if not df.empty else pd.DataFrame({"info": ["Nessun cliente"]})).to_excel(writer, index=False, sheet_name="Clienti")
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=clienti_cantiere.xlsx"}
    )


# ---------- LAVORI (storico strutturato) ----------

class Lavoro(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cliente_id: str
    data: str  # ISO date string YYYY-MM-DD
    tipo: str  # es. Antivegetativa, Manutenzione motore, Riparazione, Altro
    descrizione: str = ""
    costo: float = 0.0
    materiali: str = ""
    stato: str = "completato"  # pianificato | in_corso | completato
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LavoroCreate(BaseModel):
    cliente_id: str
    data: str
    tipo: str
    descrizione: Optional[str] = ""
    costo: Optional[float] = 0.0
    materiali: Optional[str] = ""
    stato: Optional[str] = "completato"


@api_router.get("/clienti/{cliente_id}/lavori", response_model=List[Lavoro])
async def list_lavori(cliente_id: str):
    docs = await db.lavori.find({"cliente_id": cliente_id}, {"_id": 0}).sort("data", -1).to_list(1000)
    for d in docs:
        if isinstance(d.get("created_at"), str):
            try:
                d["created_at"] = datetime.fromisoformat(d["created_at"])
            except Exception:
                pass
    return [Lavoro(**d) for d in docs]


@api_router.post("/lavori", response_model=Lavoro)
async def create_lavoro(payload: LavoroCreate):
    if payload.stato not in ("pianificato", "in_corso", "completato"):
        raise HTTPException(400, "Stato non valido")
    # verifica esistenza cliente
    c = await db.clienti.find_one({"id": payload.cliente_id})
    if not c:
        raise HTTPException(404, "Cliente non trovato")
    lavoro = Lavoro(**{k: v for k, v in payload.model_dump().items() if v is not None})
    await db.lavori.insert_one(serialize(lavoro))
    return lavoro


@api_router.put("/lavori/{lavoro_id}", response_model=Lavoro)
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


@api_router.delete("/lavori/{lavoro_id}")
async def delete_lavoro(lavoro_id: str):
    res = await db.lavori.delete_one({"id": lavoro_id})
    if res.deleted_count == 0:
        raise HTTPException(404, "Lavoro non trovato")
    return {"ok": True}


# ---------- PDF Preventivo ----------

def _euro(v: float) -> str:
    s = f"{v:,.2f}"
    return "€ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


@api_router.get("/clienti/{cliente_id}/preventivo.pdf")
async def preventivo_pdf(cliente_id: str):
    doc = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Cliente non trovato")
    lavori_docs = await db.lavori.find({"cliente_id": cliente_id}, {"_id": 0}).sort("data", -1).to_list(500)

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm, topMargin=18*mm, bottomMargin=18*mm,
        title=f"Preventivo {doc.get('cognome','')} {doc.get('nome','')}"
    )
    styles = getSampleStyleSheet()
    NAVY = colors.HexColor("#0F1B3D")
    TEAK = colors.HexColor("#B0562E")
    SAND = colors.HexColor("#F3EFE7")
    MUTED = colors.HexColor("#5B6478")

    h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=24, textColor=NAVY, spaceAfter=4, leading=28)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, textColor=TEAK, spaceBefore=14, spaceAfter=6, leading=13, letterSpace=2)
    label = ParagraphStyle("label", parent=styles["Normal"], fontName="Helvetica", fontSize=8, textColor=MUTED, leading=10)
    val = ParagraphStyle("val", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=11, textColor=NAVY, leading=14)
    body = ParagraphStyle("body", parent=styles["Normal"], fontName="Helvetica", fontSize=10, textColor=NAVY, leading=14)
    tiny = ParagraphStyle("tiny", parent=styles["Normal"], fontName="Helvetica", fontSize=8, textColor=MUTED, leading=10)

    elems = []

    # Header
    header_tbl = Table([
        [Paragraph("<b>PORTOMARE</b>", ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=18, textColor=NAVY)),
         Paragraph(f"<para align=right><font color='#5B6478' size=8>PREVENTIVO</font><br/><font size=14 color='#B0562E'><b>#{doc.get('posto_barca') or '—'}</b></font><br/><font color='#5B6478' size=8>{date.today().strftime('%d/%m/%Y')}</font></para>", body)]
    ], colWidths=[100*mm, 74*mm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elems.append(header_tbl)
    elems.append(Spacer(1, 4*mm))
    # separator
    sep = Table([[""]], colWidths=[174*mm], rowHeights=[2])
    sep.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), TEAK)]))
    elems.append(sep)
    elems.append(Spacer(1, 6*mm))

    elems.append(Paragraph("CLIENTE E IMBARCAZIONE", h2))
    potenza = doc.get('potenza_motore') or 0
    info_tbl = Table([
        [Paragraph("Cliente", label), Paragraph("Contatti", label)],
        [Paragraph(f"<b>{doc.get('cognome','')} {doc.get('nome','')}</b>", val),
         Paragraph(f"{doc.get('telefono') or '—'}<br/>{doc.get('email') or '—'}", body)],
        [Spacer(1, 3*mm), Spacer(1, 3*mm)],
        [Paragraph("Imbarcazione", label), Paragraph("Sosta", label)],
        [Paragraph(f"<b>{doc.get('tipo_barca','')}</b><br/><font color='#5B6478' size=9>Lunghezza: {doc.get('lunghezza','')} m · Motore: {int(potenza) if potenza else '—'} HP</font>", body),
         Paragraph(f"<b>{'In acqua (dentro)' if doc.get('tipo_sosta')=='dentro' else 'A terra (fuori)'}</b><br/><font color='#5B6478' size=9>Posto barca: #{str(doc.get('posto_barca') or '—').zfill(3) if doc.get('posto_barca') else '—'}</font>", body)],
    ], colWidths=[87*mm, 87*mm])
    info_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    elems.append(info_tbl)

    # Costi
    elems.append(Paragraph("DETTAGLIO COSTI ANNUALI", h2))
    voci = []
    def add(label_txt, key):
        v = float(doc.get(key) or 0)
        if v > 0:
            voci.append([label_txt, _euro(v)])
    add("Sosta", "costo_sosta")
    add("Copertura", "costo_copertura")
    add("Alaggio", "costo_alaggio")
    add("Varo", "costo_varo")
    add("Antivegetativa", "costo_antivegetativa")
    add("Manutenzione motore", "costo_manutenzione_motore")
    totale = sum(float(doc.get(k) or 0) for k in ("costo_sosta","costo_copertura","costo_alaggio","costo_varo","costo_antivegetativa","costo_manutenzione_motore"))

    if not voci:
        voci = [["Nessun costo configurato", "—"]]

    costi_data = [["VOCE", "IMPORTO"]] + voci + [["TOTALE", _euro(totale)]]
    costi_tbl = Table(costi_data, colWidths=[124*mm, 50*mm])
    n = len(voci)
    costi_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), NAVY),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 8),
        ("ALIGN", (1,0), (1,-1), "RIGHT"),
        ("FONTNAME", (0,1), (-1,n), "Helvetica"),
        ("FONTSIZE", (0,1), (-1,n), 10),
        ("TEXTCOLOR", (0,1), (-1,n), NAVY),
        ("ROWBACKGROUNDS", (0,1), (-1,n), [colors.white, SAND]),
        ("LINEBELOW", (0,1), (-1,n), 0.3, colors.HexColor("#D9D9D9")),
        # totale row
        ("BACKGROUND", (0,-1), (-1,-1), TEAK),
        ("TEXTCOLOR", (0,-1), (-1,-1), colors.white),
        ("FONTNAME", (0,-1), (-1,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,-1), (-1,-1), 12),
        ("TOPPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING", (0,0), (-1,-1), 10),
        ("RIGHTPADDING", (0,0), (-1,-1), 10),
    ]))
    elems.append(costi_tbl)

    # Dettaglio motore (manodopera + ricambi) se presente
    manodopera = float(doc.get("costo_manodopera_motore") or 0)
    ricambi_tot = float(doc.get("costo_ricambi_totale") or 0)
    if manodopera > 0 or ricambi_tot > 0:
        elems.append(Paragraph("DETTAGLIO MANUTENZIONE MOTORE", h2))
        # Ricalcola breakdown ricambi da tariffe correnti
        t_current = await get_tariffe_doc()
        nc = int(doc.get("numero_candele") or 0)
        nt = int(doc.get("numero_termostati") or 0)
        ric_rows = [
            ["Manodopera motore", "", _euro(manodopera)],
            ["Girante", "1", _euro(t_current.costo_girante)],
            ["Olio motore", "1", _euro(t_current.costo_olio_motore)],
            ["Filtro olio", "1", _euro(t_current.costo_filtro_olio)],
            ["Candele", str(nc), _euro(nc * t_current.costo_candela)],
            ["Termostato", str(nt), _euro(nt * t_current.costo_termostato)],
            ["Olio piede", "1", _euro(t_current.costo_olio_piede)],
        ]
        ric_data = [["VOCE", "Q.TÀ", "IMPORTO"]] + ric_rows
        ric_tbl = Table(ric_data, colWidths=[104*mm, 20*mm, 50*mm])
        ric_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NAVY),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 8),
            ("ALIGN", (1,0), (2,-1), "RIGHT"),
            ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
            ("FONTSIZE", (0,1), (-1,-1), 9),
            ("TEXTCOLOR", (0,1), (-1,-1), NAVY),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, SAND]),
            ("LINEBELOW", (0,1), (-1,-1), 0.3, colors.HexColor("#D9D9D9")),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ]))
        elems.append(ric_tbl)

    # Scadenze
    if doc.get("scadenza_antivegetativa") or doc.get("scadenza_manutenzione"):
        elems.append(Paragraph("PROSSIME SCADENZE", h2))
        rows = []
        if doc.get("scadenza_antivegetativa"):
            rows.append(["Antivegetativa", doc["scadenza_antivegetativa"]])
        if doc.get("scadenza_manutenzione"):
            rows.append(["Manutenzione motore", doc["scadenza_manutenzione"]])
        sc_tbl = Table(rows, colWidths=[124*mm, 50*mm])
        sc_tbl.setStyle(TableStyle([
            ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
            ("FONTSIZE", (0,0), (-1,-1), 10),
            ("TEXTCOLOR", (0,0), (-1,-1), NAVY),
            ("ALIGN", (1,0), (1,-1), "RIGHT"),
            ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#D9D9D9")),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ]))
        elems.append(sc_tbl)

    # Storico lavori strutturato
    if lavori_docs:
        elems.append(Paragraph("STORICO LAVORI ESEGUITI", h2))
        headers = ["Data", "Tipo", "Descrizione", "Costo"]
        rows = [headers]
        for l in lavori_docs[:20]:
            rows.append([
                l.get("data",""),
                l.get("tipo",""),
                (l.get("descrizione","") or "")[:60],
                _euro(float(l.get("costo") or 0)),
            ])
        lav_tbl = Table(rows, colWidths=[24*mm, 40*mm, 78*mm, 32*mm])
        lav_tbl.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), NAVY),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,0), 8),
            ("FONTSIZE", (0,1), (-1,-1), 9),
            ("TEXTCOLOR", (0,1), (-1,-1), NAVY),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, SAND]),
            ("ALIGN", (3,0), (3,-1), "RIGHT"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
        ]))
        elems.append(lav_tbl)

    # Note
    if doc.get("note_lavori"):
        elems.append(Paragraph("NOTE", h2))
        elems.append(Paragraph(doc["note_lavori"].replace("\n", "<br/>"), body))

    elems.append(Spacer(1, 10*mm))
    elems.append(Paragraph(
        "Documento generato automaticamente da Portomare — Gestione Cantiere Nautico. "
        f"Il presente preventivo ha validità 30 giorni dalla data di emissione ({date.today().strftime('%d/%m/%Y')}).",
        tiny
    ))

    pdf.build(elems)
    buf.seek(0)
    filename = f"preventivo_{doc.get('cognome','cliente').lower()}_{doc.get('nome','').lower()}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
