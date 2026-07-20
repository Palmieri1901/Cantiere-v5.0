from fastapi import FastAPI, APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import io
import zipfile
import bcrypt
import jwt
from datetime import timedelta
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

TOTAL_POSTI = 200


# ---------- AUTH (setup precoce per protezione router) ----------

from fastapi import Request, Depends, Response

JWT_ALGORITHM = "HS256"

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=8),
        "type": "access",
    }
    return jwt.encode(payload, os.environ["JWT_SECRET"], algorithm=JWT_ALGORITHM)


async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Non autenticato")
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET"], algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token non valido")
        user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="Utente non trovato")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessione scaduta")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token non valido")


api_router = APIRouter(prefix="/api")


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
    costo_olio_motore: float = 12.0  # € al litro
    costo_filtro_olio: float = 18.0
    costo_candela: float = 12.0
    costo_termostato: float = 35.0
    costo_olio_piede: float = 25.0
    costo_anodi_interni: float = 40.0
    costo_anodi_esterni: float = 60.0
    costo_ingrassaggio: float = 30.0
    # Sosta
    sosta_dentro_per_metro: float = 180.0
    sosta_fuori_per_metro: float = 120.0
    # Sosta fuori sede: nessun costo sosta, ma movimentazione + taccaggio
    costo_movimentazione_per_metro: float = 25.0
    costo_taccaggio_per_metro: float = 20.0
    # Lavaggi ed extra
    costo_lavaggio_inizio_stagione: float = 80.0
    costo_lavaggio_fine_stagione: float = 80.0
    maggiorazione_scafo_sporco_per_metro: float = 15.0  # applicata se antivegetativa disattivata
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
    costo_anodi_interni: Optional[float] = None
    costo_anodi_esterni: Optional[float] = None
    costo_ingrassaggio: Optional[float] = None
    sosta_dentro_per_metro: Optional[float] = None
    sosta_fuori_per_metro: Optional[float] = None
    costo_movimentazione_per_metro: Optional[float] = None
    costo_taccaggio_per_metro: Optional[float] = None
    costo_lavaggio_inizio_stagione: Optional[float] = None
    costo_lavaggio_fine_stagione: Optional[float] = None
    maggiorazione_scafo_sporco_per_metro: Optional[float] = None


class Cliente(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    cognome: str
    tipo_barca: str
    lunghezza: float  # metri
    tipo_sosta: str  # "dentro" | "fuori" | "fuori_sede"
    anno: int = Field(default_factory=lambda: datetime.now().year)
    posto_barca: Optional[int] = None  # 1-200
    telefono: Optional[str] = ""
    email: Optional[str] = ""
    # Motore
    potenza_motore: float = 0.0  # HP (cavalli)
    litri_olio_motore: float = 3.0  # capacità olio motore in litri
    numero_candele: int = 4
    numero_termostati: int = 1
    # Interruttori applicabilità
    antivegetativa_attiva: bool = True
    girante_attivo: bool = True
    lavaggio_inizio_attivo: bool = True
    lavaggio_fine_attivo: bool = True
    # Costi (auto o manuali)
    costo_sosta: float = 0.0
    costo_copertura: float = 0.0
    costo_alaggio: float = 0.0
    costo_varo: float = 0.0
    costo_antivegetativa: float = 0.0
    costo_manutenzione_motore: float = 0.0
    costo_lavaggio_inizio: float = 0.0
    costo_lavaggio_fine: float = 0.0
    costo_scafo_sporco: float = 0.0
    costo_movimentazione: float = 0.0
    costo_taccaggio: float = 0.0
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
    anno: Optional[int] = None
    posto_barca: Optional[int] = None
    telefono: Optional[str] = ""
    email: Optional[str] = ""
    potenza_motore: Optional[float] = 0.0
    litri_olio_motore: Optional[float] = 3.0
    numero_candele: Optional[int] = 4
    numero_termostati: Optional[int] = 1
    antivegetativa_attiva: Optional[bool] = True
    girante_attivo: Optional[bool] = True
    lavaggio_inizio_attivo: Optional[bool] = True
    lavaggio_fine_attivo: Optional[bool] = True
    costo_sosta: Optional[float] = None
    costo_copertura: Optional[float] = None
    costo_alaggio: Optional[float] = None
    costo_varo: Optional[float] = None
    costo_antivegetativa: Optional[float] = None
    costo_manutenzione_motore: Optional[float] = None
    costo_lavaggio_inizio: Optional[float] = None
    costo_lavaggio_fine: Optional[float] = None
    costo_scafo_sporco: Optional[float] = None
    costo_movimentazione: Optional[float] = None
    costo_taccaggio: Optional[float] = None
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


def calcola_ricambi(numero_candele: int, numero_termostati: int, t: Tariffe,
                    girante_attivo: bool = True, litri_olio_motore: float = 3.0) -> dict:
    """Costo ricambi motore: girante, olio motore (× litri), filtro olio, candele, termostati, olio piede, anodi, ingrassaggio."""
    nc = int(numero_candele or 0)
    nt = int(numero_termostati or 0)
    litri = float(litri_olio_motore or 0)
    return {
        "girante": round(t.costo_girante, 2) if girante_attivo else 0.0,
        "olio_motore": round(litri * t.costo_olio_motore, 2),
        "filtro_olio": round(t.costo_filtro_olio, 2),
        "candele": round(nc * t.costo_candela, 2),
        "termostati": round(nt * t.costo_termostato, 2),
        "olio_piede": round(t.costo_olio_piede, 2),
        "anodi_interni": round(t.costo_anodi_interni, 2),
        "anodi_esterni": round(t.costo_anodi_esterni, 2),
        "ingrassaggio": round(t.costo_ingrassaggio, 2),
    }


def calcola_costi(lunghezza: float, tipo_sosta: str, t: Tariffe,
                  potenza_motore: float = 0.0, numero_candele: int = 4,
                  numero_termostati: int = 1,
                  antivegetativa_attiva: bool = True,
                  girante_attivo: bool = True,
                  litri_olio_motore: float = 3.0,
                  lavaggio_inizio_attivo: bool = True,
                  lavaggio_fine_attivo: bool = True) -> dict:
    """Calcola costi automatici in base a lunghezza, tipo sosta e motore."""
    manodopera = calcola_motore_labor(potenza_motore, t)
    ricambi = calcola_ricambi(numero_candele, numero_termostati, t, girante_attivo, litri_olio_motore)
    ricambi_tot = round(sum(ricambi.values()), 2)
    motore_tot = round(manodopera + ricambi_tot, 2)

    antiveg = round(lunghezza * t.antivegetativa_per_metro, 2) if antivegetativa_attiva else 0.0
    scafo_sporco = round(lunghezza * t.maggiorazione_scafo_sporco_per_metro, 2) if not antivegetativa_attiva else 0.0
    lav_inizio = round(t.costo_lavaggio_inizio_stagione, 2) if lavaggio_inizio_attivo else 0.0
    lav_fine = round(t.costo_lavaggio_fine_stagione, 2) if lavaggio_fine_attivo else 0.0

    base = {
        "costo_antivegetativa": antiveg,
        "costo_manutenzione_motore": motore_tot,
        "costo_manodopera_motore": manodopera,
        "costo_ricambi_totale": ricambi_tot,
        "costo_lavaggio_inizio": lav_inizio,
        "costo_lavaggio_fine": lav_fine,
        "costo_scafo_sporco": scafo_sporco,
        "ricambi_dettaglio": ricambi,
    }

    # Movimentazione e taccaggio applicati solo per sosta fuori sede
    movimentazione = round(lunghezza * t.costo_movimentazione_per_metro, 2) if tipo_sosta == "fuori_sede" else 0.0
    taccaggio = round(lunghezza * t.costo_taccaggio_per_metro, 2) if tipo_sosta == "fuori_sede" else 0.0
    base["costo_movimentazione"] = movimentazione
    base["costo_taccaggio"] = taccaggio

    if tipo_sosta == "fuori":
        base.update({
            "costo_sosta": round(lunghezza * t.sosta_fuori_per_metro, 2),
            "costo_copertura": round(lunghezza * t.copertura_per_metro, 2),
            "costo_alaggio": calcola_alaggio(lunghezza, t),
            "costo_varo": calcola_varo(lunghezza, t),
        })
    elif tipo_sosta == "fuori_sede":
        # Nessun costo sosta/copertura/alaggio/varo: la barca è custodita dal cliente
        base.update({
            "costo_sosta": 0.0,
            "costo_copertura": 0.0,
            "costo_alaggio": 0.0,
            "costo_varo": 0.0,
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
                        numero_termostati: int = 1,
                        antivegetativa_attiva: bool = True,
                        girante_attivo: bool = True,
                        litri_olio_motore: float = 3.0,
                        lavaggio_inizio_attivo: bool = True,
                        lavaggio_fine_attivo: bool = True):
    if tipo_sosta not in ("dentro", "fuori", "fuori_sede"):
        raise HTTPException(400, "tipo_sosta deve essere 'dentro', 'fuori' o 'fuori_sede'")
    t = await get_tariffe_doc()
    return calcola_costi(lunghezza, tipo_sosta, t, potenza_motore,
                         numero_candele, numero_termostati,
                         antivegetativa_attiva, girante_attivo, litri_olio_motore,
                         lavaggio_inizio_attivo, lavaggio_fine_attivo)


# --- Clienti ---
@api_router.get("/clienti", response_model=List[Cliente])
async def list_clienti(anno: Optional[int] = None):
    q = {}
    if anno is not None:
        q["anno"] = anno
    docs = await db.clienti.find(q, {"_id": 0}).to_list(1000)
    return [Cliente(**deserialize_cliente(d)) for d in docs]


@api_router.get("/clienti/{cliente_id}", response_model=Cliente)
async def get_cliente(cliente_id: str):
    doc = await db.clienti.find_one({"id": cliente_id}, {"_id": 0})
    if not doc:
        raise HTTPException(404, "Cliente non trovato")
    return Cliente(**deserialize_cliente(doc))


@api_router.post("/clienti", response_model=Cliente)
async def create_cliente(payload: ClienteCreate):
    if payload.tipo_sosta not in ("dentro", "fuori", "fuori_sede"):
        raise HTTPException(400, "tipo_sosta deve essere 'dentro', 'fuori' o 'fuori_sede'")
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

    if payload.tipo_sosta not in ("dentro", "fuori", "fuori_sede"):
        raise HTTPException(400, "tipo_sosta deve essere 'dentro', 'fuori' o 'fuori_sede'")

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
        "sosta_fuori_sede": fuori_sede,
        "entrate_totali": round(entrate_totali, 2),
        "scadenze_prossime": scadenze[:10],
    }


# --- Posti barca ---
@api_router.get("/posti-barca")
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
    anno: int = Field(default_factory=lambda: datetime.now().year)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LavoroCreate(BaseModel):
    cliente_id: str
    data: str
    tipo: str
    descrizione: Optional[str] = ""
    costo: Optional[float] = 0.0
    materiali: Optional[str] = ""
    stato: Optional[str] = "completato"
    anno: Optional[int] = None


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
    cantiere_doc = await db.cantiere.find_one({"id": "default"}, {"_id": 0}) or {}
    t_current = await get_tariffe_doc()

    pdf_bytes = _build_preventivo_pdf(doc, lavori_docs, cantiere_doc, t_current)
    filename = f"preventivo_{doc.get('cognome','cliente').lower()}_{doc.get('nome','').lower()}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@api_router.get("/export/preventivi.zip")
async def export_tutti_pdf():
    """Esporta un archivio ZIP con un PDF preventivo per ogni cliente."""
    clienti_docs = await db.clienti.find({}, {"_id": 0}).to_list(10000)
    if not clienti_docs:
        raise HTTPException(404, "Nessun cliente da esportare")
    cantiere_doc = await db.cantiere.find_one({"id": "default"}, {"_id": 0}) or {}
    t_current = await get_tariffe_doc()

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for c in clienti_docs:
            lavori_docs = await db.lavori.find({"cliente_id": c["id"]}, {"_id": 0}).sort("data", -1).to_list(500)
            pdf_bytes = _build_preventivo_pdf(c, lavori_docs, cantiere_doc, t_current)
            posto = f"{int(c['posto_barca']):03d}_" if c.get("posto_barca") else ""
            filename = f"{posto}{(c.get('cognome') or 'cliente').lower()}_{(c.get('nome') or '').lower()}.pdf"
            # Sanitize filename
            filename = "".join(ch for ch in filename if ch.isalnum() or ch in "._-")
            zf.writestr(filename, pdf_bytes)
    zip_buf.seek(0)
    zip_filename = f"preventivi_cantiere_{datetime.now().strftime('%Y%m%d')}.zip"
    return StreamingResponse(
        zip_buf,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={zip_filename}"}
    )


def _build_preventivo_pdf(doc: dict, lavori_docs: list, cantiere_doc: dict, t_current: Tariffe) -> bytes:
    """Genera il PDF preventivo come bytes. Estratto per riuso in singolo + bulk export."""
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

    # Header con logo/nome cantiere + indirizzo
    from reportlab.platypus import Image as RLImage
    import base64 as _b64
    nome_cantiere = (cantiere_doc.get("nome") or "PORTOMARE").upper()
    indirizzo_parts = [x for x in [cantiere_doc.get("indirizzo"), " ".join(filter(None, [cantiere_doc.get("cap"), cantiere_doc.get("citta"), (f"({cantiere_doc.get('provincia')})" if cantiere_doc.get("provincia") else "")])), cantiere_doc.get("telefono"), cantiere_doc.get("email"), cantiere_doc.get("piva") and f"P.IVA {cantiere_doc.get('piva')}"] if x]
    contatti_txt = " · ".join(indirizzo_parts) if indirizzo_parts else ""

    logo_b64 = cantiere_doc.get("logo_base64") or ""
    logo_cell = Paragraph(f"<b>{nome_cantiere}</b>", ParagraphStyle("brand", fontName="Helvetica-Bold", fontSize=18, textColor=NAVY))
    if logo_b64 and "," in logo_b64:
        try:
            raw = _b64.b64decode(logo_b64.split(",", 1)[1])
            logo_cell = RLImage(io.BytesIO(raw), width=30*mm, height=18*mm, kind="proportional")
        except Exception:
            pass

    header_tbl = Table([
        [logo_cell,
         Paragraph(f"<para align=right><font color='#5B6478' size=8>PREVENTIVO</font><br/><font size=14 color='#B0562E'><b>#{doc.get('posto_barca') or '—'}</b></font><br/><font color='#5B6478' size=8>{date.today().strftime('%d/%m/%Y')}</font></para>", body)]
    ], colWidths=[100*mm, 74*mm])
    header_tbl.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elems.append(header_tbl)
    if contatti_txt:
        elems.append(Spacer(1, 2*mm))
        elems.append(Paragraph(f"<font color='#5B6478' size=8>{contatti_txt}</font>", body))
    elems.append(Spacer(1, 4*mm))
    # separator
    sep = Table([[""]], colWidths=[174*mm], rowHeights=[2])
    sep.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), TEAK)]))
    elems.append(sep)
    elems.append(Spacer(1, 6*mm))

    elems.append(Paragraph("CLIENTE E IMBARCAZIONE", h2))
    potenza = doc.get('potenza_motore') or 0
    litri_pdf = doc.get('litri_olio_motore') or 0
    sosta_label = 'Al coperto' if doc.get('tipo_sosta')=='dentro' else 'Fuori sede' if doc.get('tipo_sosta')=='fuori_sede' else 'A terra (fuori)'
    info_tbl = Table([
        [Paragraph("Cliente", label), Paragraph("Contatti", label)],
        [Paragraph(f"<b>{doc.get('cognome','')} {doc.get('nome','')}</b>", val),
         Paragraph(f"{doc.get('telefono') or '—'}<br/>{doc.get('email') or '—'}", body)],
        [Spacer(1, 3*mm), Spacer(1, 3*mm)],
        [Paragraph("Imbarcazione", label), Paragraph("Sosta", label)],
        [Paragraph(f"<b>{doc.get('tipo_barca','')}</b><br/><font color='#5B6478' size=9>Lunghezza: {doc.get('lunghezza','')} m · Motore: {int(potenza) if potenza else '—'} HP · Olio: {litri_pdf:g} L</font>", body),
         Paragraph(f"<b>{sosta_label}</b><br/><font color='#5B6478' size=9>Posto barca: #{str(doc.get('posto_barca') or '—').zfill(3) if doc.get('posto_barca') else '—'}</font>", body)],
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
    add("Movimentazione", "costo_movimentazione")
    add("Taccaggio", "costo_taccaggio")
    add("Copertura", "costo_copertura")
    add("Alaggio", "costo_alaggio")
    add("Varo", "costo_varo")
    add("Antivegetativa", "costo_antivegetativa")
    add("Magg. scafo sporco", "costo_scafo_sporco")
    add("Lavaggio inizio stagione", "costo_lavaggio_inizio")
    add("Lavaggio fine stagione", "costo_lavaggio_fine")
    add("Manutenzione motore", "costo_manutenzione_motore")
    totale = sum(float(doc.get(k) or 0) for k in ("costo_sosta","costo_movimentazione","costo_taccaggio","costo_copertura","costo_alaggio","costo_varo","costo_antivegetativa","costo_scafo_sporco","costo_lavaggio_inizio","costo_lavaggio_fine","costo_manutenzione_motore"))

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
        # Ricalcola breakdown ricambi da tariffe correnti (passate come parametro)
        nc = int(doc.get("numero_candele") or 0)
        nt = int(doc.get("numero_termostati") or 0)
        girante_attivo = bool(doc.get("girante_attivo", True))
        litri = float(doc.get("litri_olio_motore") or 0)
        ric_rows = [
            ["Manodopera motore", "", _euro(manodopera)],
        ]
        if girante_attivo:
            ric_rows.append(["Girante", "1", _euro(t_current.costo_girante)])
        ric_rows.extend([
            ["Olio motore", f"{litri:g} L", _euro(litri * t_current.costo_olio_motore)],
            ["Filtro olio", "1", _euro(t_current.costo_filtro_olio)],
            ["Candele", str(nc), _euro(nc * t_current.costo_candela)],
            ["Termostato", str(nt), _euro(nt * t_current.costo_termostato)],
            ["Olio piede", "1", _euro(t_current.costo_olio_piede)],
            ["Anodi interni", "1", _euro(t_current.costo_anodi_interni)],
            ["Anodi esterni", "1", _euro(t_current.costo_anodi_esterni)],
            ["Ingrassaggio", "1", _euro(t_current.costo_ingrassaggio)],
        ])
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
    footer_name = cantiere_doc.get("nome") or "Portomare"
    elems.append(Paragraph(
        f"Documento generato automaticamente da {footer_name} — Gestione Cantiere Nautico. "
        f"Il presente preventivo ha validità 30 giorni dalla data di emissione ({date.today().strftime('%d/%m/%Y')}).",
        tiny
    ))

    pdf.build(elems)
    buf.seek(0)
    return buf.getvalue()


# ---------- CANTIERE INFO (logo + indirizzo) ----------

class Cantiere(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: "default")
    nome: str = "Portomare"
    slogan: str = "Cantiere nautico dal 1985"
    indirizzo: str = ""
    citta: str = ""
    cap: str = ""
    provincia: str = ""
    telefono: str = ""
    email: str = ""
    piva: str = ""
    sito_web: str = ""
    orari: str = ""
    logo_base64: str = ""  # data:image/...;base64,...
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CantiereUpdate(BaseModel):
    nome: Optional[str] = None
    slogan: Optional[str] = None
    indirizzo: Optional[str] = None
    citta: Optional[str] = None
    cap: Optional[str] = None
    provincia: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    piva: Optional[str] = None
    sito_web: Optional[str] = None
    orari: Optional[str] = None
    logo_base64: Optional[str] = None


@api_router.get("/cantiere", response_model=Cantiere)
async def get_cantiere():
    doc = await db.cantiere.find_one({"id": "default"}, {"_id": 0})
    if not doc:
        c = Cantiere()
        await db.cantiere.insert_one(serialize(c))
        return c
    return Cantiere(**doc)


@api_router.put("/cantiere", response_model=Cantiere)
async def update_cantiere(payload: CantiereUpdate):
    current = await get_cantiere()
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    new_data = current.model_dump()
    new_data.update(updates)
    new_data["updated_at"] = datetime.now(timezone.utc)
    c = Cantiere(**new_data)
    await db.cantiere.update_one({"id": "default"}, {"$set": serialize(c)}, upsert=True)
    return c


# ---------- BACKUP / RESTORE ----------

@api_router.get("/backup")
async def backup_data():
    """Esporta tutti i dati del cantiere in un unico JSON scaricabile."""
    import json as _json
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


class RestoreRequest(BaseModel):
    version: Optional[int] = None
    cantiere: Optional[dict] = None
    tariffe: Optional[dict] = None
    clienti: Optional[List[dict]] = None
    lavori: Optional[List[dict]] = None


@api_router.post("/restore")
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


# ---------- AUTH ROUTES ----------

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    nome: Optional[str] = ""


auth_router = APIRouter(prefix="/api/auth")


def _set_cookie(response: Response, token: str):
    response.set_cookie(
        key="access_token", value=token, httponly=True, secure=False,
        samesite="lax", max_age=8 * 3600, path="/",
    )


@auth_router.post("/register")
async def register(payload: RegisterRequest, response: Response):
    email = payload.email.strip().lower()
    if not email or not payload.password:
        raise HTTPException(400, "Email e password obbligatorie")
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(400, "Email già registrata")
    user_id = str(uuid.uuid4())
    doc = {
        "id": user_id,
        "email": email,
        "password_hash": hash_password(payload.password),
        "nome": payload.nome or email.split("@")[0],
        "role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(doc)
    token = create_access_token(user_id, email)
    _set_cookie(response, token)
    return {"id": user_id, "email": email, "nome": doc["nome"], "role": "user", "token": token}


@auth_router.post("/login")
async def login(payload: LoginRequest, response: Response):
    email = payload.email.strip().lower()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(401, "Email o password non corretta")
    token = create_access_token(user["id"], email)
    _set_cookie(response, token)
    return {"id": user["id"], "email": email, "nome": user.get("nome", ""), "role": user.get("role", "user"), "token": token}


@auth_router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    return {"ok": True}


@auth_router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {"id": user["id"], "email": user["email"], "nome": user.get("nome", ""), "role": user.get("role", "user")}


app.include_router(auth_router)


async def seed_admin():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@portomare.it").strip().lower()
    admin_password = os.environ.get("ADMIN_PASSWORD", "portomare2026")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": admin_email,
            "password_hash": hash_password(admin_password),
            "nome": "Admin",
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        logger.info(f"Admin seeded: {admin_email}")
    elif not verify_password(admin_password, existing.get("password_hash", "")):
        await db.users.update_one(
            {"email": admin_email},
            {"$set": {"password_hash": hash_password(admin_password)}}
        )
        logger.info(f"Admin password updated: {admin_email}")


@app.on_event("startup")
async def _startup():
    await db.users.create_index("email", unique=True)
    await seed_admin()


# ---------- REPORT INCASSI ----------

@api_router.get("/report/incassi")
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

    # Suddivisione motore
    incasso_manodopera = s("costo_manodopera_motore")
    incasso_ricambi = s("costo_ricambi_totale")

    totale = round(
        incasso_sosta + incasso_movimentazione + incasso_taccaggio +
        incasso_alaggio + incasso_varo + incasso_coperture +
        incasso_antivegetativa + incasso_scafo_sporco +
        incasso_lavaggio_inizio + incasso_lavaggio_fine +
        incasso_motore, 2
    )

    # Ripartizione per tipo sosta
    per_tipo_sosta = {"dentro": 0.0, "fuori": 0.0, "fuori_sede": 0.0}
    for d in docs:
        tipo = d.get("tipo_sosta")
        if tipo in per_tipo_sosta:
            client_tot = sum(float(d.get(k) or 0) for k in (
                "costo_sosta","costo_movimentazione","costo_taccaggio",
                "costo_alaggio","costo_varo","costo_copertura",
                "costo_antivegetativa","costo_scafo_sporco",
                "costo_lavaggio_inizio","costo_lavaggio_fine",
                "costo_manutenzione_motore"
            ))
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


# ---------- GESTIONE ANNI ----------

@api_router.get("/anni")
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


class ApriAnnoRequest(BaseModel):
    anno: int
    duplica_da: Optional[int] = None  # anno da cui duplicare i clienti


@api_router.post("/anni/apri")
async def apri_anno(payload: ApriAnnoRequest):
    """Apre un nuovo anno. Se duplica_da è specificato, copia i clienti da quell'anno (ricalcolando i costi con le tariffe correnti)."""
    if payload.anno < 2000 or payload.anno > 2100:
        raise HTTPException(400, "Anno non valido")

    # Verifica se ci sono già clienti per quest'anno
    existing_count = await db.clienti.count_documents({"anno": payload.anno})

    duplicati = 0
    if payload.duplica_da is not None and existing_count == 0:
        origine = await db.clienti.find({"anno": payload.duplica_da}, {"_id": 0}).to_list(10000)
        t = await get_tariffe_doc()
        for c in origine:
            # Nuovo ID e anno, ricalcola costi
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
            )
            auto_costi.pop("ricambi_dettaglio", None)

            data = {**c, **auto_costi, "id": new_id, "anno": payload.anno,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                    # Reset note e scadenze del nuovo anno
                    "note_lavori": "", "scadenza_antivegetativa": None, "scadenza_manutenzione": None}
            try:
                cli = Cliente(**{k: v for k, v in data.items() if k in Cliente.model_fields or k in ("posto_barca", "scadenza_antivegetativa", "scadenza_manutenzione")})
                await db.clienti.insert_one(serialize(cli))
                duplicati += 1
            except Exception as e:
                logger.warning(f"Errore duplicazione cliente: {e}")

    return {"ok": True, "anno": payload.anno, "duplicati": duplicati, "gia_esistenti": existing_count}


@api_router.delete("/anni/{anno}")
async def elimina_anno(anno: int):
    """Elimina tutti i clienti e lavori di un anno specifico."""
    if anno == datetime.now().year:
        # Permettiamo di svuotare anche l'anno corrente ma con conteggio
        pass
    res_clienti = await db.clienti.delete_many({"anno": anno})
    # Recupera ID clienti eliminati per pulire lavori? Meglio filtrare per anno lavoro
    res_lavori = await db.lavori.delete_many({"anno": anno})
    return {
        "ok": True,
        "anno": anno,
        "clienti_eliminati": res_clienti.deleted_count,
        "lavori_eliminati": res_lavori.deleted_count,
    }


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
