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
from datetime import datetime, timezone
import pandas as pd

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
    alaggio_per_metro: float = 25.0
    varo_per_metro: float = 25.0
    antivegetativa_per_metro: float = 60.0
    manutenzione_motore_base: float = 250.0
    sosta_dentro_per_metro: float = 180.0
    sosta_fuori_per_metro: float = 120.0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TariffeUpdate(BaseModel):
    copertura_per_metro: Optional[float] = None
    alaggio_per_metro: Optional[float] = None
    varo_per_metro: Optional[float] = None
    antivegetativa_per_metro: Optional[float] = None
    manutenzione_motore_base: Optional[float] = None
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
    # Costi (auto o manuali)
    costo_sosta: float = 0.0
    costo_copertura: float = 0.0
    costo_alaggio: float = 0.0
    costo_varo: float = 0.0
    costo_antivegetativa: float = 0.0
    costo_manutenzione_motore: float = 0.0
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


def calcola_costi(lunghezza: float, tipo_sosta: str, t: Tariffe) -> dict:
    """Calcola costi automatici in base a lunghezza e tipo sosta."""
    if tipo_sosta == "fuori":
        return {
            "costo_sosta": round(lunghezza * t.sosta_fuori_per_metro, 2),
            "costo_copertura": round(lunghezza * t.copertura_per_metro, 2),
            "costo_alaggio": round(lunghezza * t.alaggio_per_metro, 2),
            "costo_varo": round(lunghezza * t.varo_per_metro, 2),
            "costo_antivegetativa": round(lunghezza * t.antivegetativa_per_metro, 2),
            "costo_manutenzione_motore": round(t.manutenzione_motore_base, 2),
        }
    else:  # dentro
        return {
            "costo_sosta": round(lunghezza * t.sosta_dentro_per_metro, 2),
            "costo_copertura": 0.0,
            "costo_alaggio": 0.0,
            "costo_varo": 0.0,
            "costo_antivegetativa": round(lunghezza * t.antivegetativa_per_metro, 2),
            "costo_manutenzione_motore": round(t.manutenzione_motore_base, 2),
        }


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
async def preview_costi(lunghezza: float, tipo_sosta: str):
    if tipo_sosta not in ("dentro", "fuori"):
        raise HTTPException(400, "tipo_sosta deve essere 'dentro' o 'fuori'")
    t = await get_tariffe_doc()
    return calcola_costi(lunghezza, tipo_sosta, t)


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
    auto_costi = calcola_costi(payload.lunghezza, payload.tipo_sosta, t)

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
    auto_costi = calcola_costi(payload.lunghezza, payload.tipo_sosta, t)

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
    from datetime import date, timedelta
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
