"""Cantiere Nautico API — entrypoint FastAPI.

L'app è organizzata in moduli:
  · database.py       — client MongoDB, logger, TOTAL_POSTI
  · models.py         — modelli Pydantic (Cliente, Tariffe, Lavoro, Cantiere, ...)
  · helpers.py        — serialize, calcolo automatico dei costi, _euro
  · auth.py           — JWT auth + endpoints + seed_admin
  · pdf_builders.py   — costruttori PDF (preventivo, storico multi-anno)
  · routers/*.py      — un router per dominio (tariffe, clienti, lavori,
                        stats, export, cantiere, backup, preventivo,
                        report, anni)
"""
import os
from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware

from database import client as mongo_client, db, logger
from auth import auth_router, seed_admin
from routers import (
    tariffe, clienti, lavori, stats, export,
    cantiere, backup, preventivo, report, anni,
)


app = FastAPI(title="Cantiere Nautico API")

api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "Cantiere Nautico API - OK"}


# Aggrega tutti i router di dominio sotto /api
api_router.include_router(tariffe.router)
api_router.include_router(clienti.router)
api_router.include_router(lavori.router)
api_router.include_router(stats.router)
api_router.include_router(export.router)
api_router.include_router(cantiere.router)
api_router.include_router(backup.router)
api_router.include_router(preventivo.router)
api_router.include_router(report.router)
api_router.include_router(anni.router)

app.include_router(api_router)
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.on_event("startup")
async def _startup():
    await db.users.create_index("email", unique=True)
    await seed_admin()
    # Migrazione iter13: scafo_sporco_attivo
    try:
        await db.clienti.update_many(
            {"scafo_sporco_attivo": {"$exists": False}, "costo_scafo_sporco": {"$gt": 0}},
            {"$set": {"scafo_sporco_attivo": True}},
        )
        await db.clienti.update_many(
            {"scafo_sporco_attivo": {"$exists": False}},
            {"$set": {"scafo_sporco_attivo": False}},
        )
    except Exception as e:
        logger.warning(f"Migration iter13 scafo_sporco_attivo skipped: {e}")
    # Migrazione iter14: copertura_attiva
    try:
        await db.clienti.update_many(
            {"copertura_attiva": {"$exists": False}, "costo_copertura": {"$gt": 0}},
            {"$set": {"copertura_attiva": True}},
        )
        await db.clienti.update_many(
            {"copertura_attiva": {"$exists": False}},
            {"$set": {"copertura_attiva": False}},
        )
    except Exception as e:
        logger.warning(f"Migration iter14 copertura_attiva skipped: {e}")
    # Migrazione iter20: alaggio_varo_attivo per sosta fuori/temporanea
    try:
        await db.clienti.update_many(
            {"alaggio_varo_attivo": {"$exists": False}, "tipo_sosta": {"$in": ["fuori", "temporanea"]}},
            {"$set": {"alaggio_varo_attivo": True}},
        )
        await db.clienti.update_many(
            {"alaggio_varo_attivo": {"$exists": False}},
            {"$set": {"alaggio_varo_attivo": False}},
        )
    except Exception as e:
        logger.warning(f"Migration iter20 alaggio_varo_attivo skipped: {e}")
    # Migrazione iter29: forza alaggio_varo_attivo=True su temporanea
    try:
        await db.clienti.update_many(
            {"tipo_sosta": "temporanea", "alaggio_varo_attivo": False},
            {"$set": {"alaggio_varo_attivo": True}},
        )
    except Exception as e:
        logger.warning(f"Migration iter29 temporanea→alaggio_varo skipped: {e}")


@app.on_event("shutdown")
async def _shutdown():
    mongo_client.close()
