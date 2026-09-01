"""Serializzazione, sanitize e calcolo automatico dei costi cantiere."""
from datetime import datetime
from typing import List
from fastapi import HTTPException
from pydantic import BaseModel

from database import db
from models import Tariffe


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


def _sanitize_lavorazioni_extra(lst) -> List[dict]:
    """Valida e normalizza la lista lavorazioni extra: max 20 voci, ciascuna {descrizione, prezzo}."""
    if not lst:
        return []
    if not isinstance(lst, list):
        raise HTTPException(400, "lavorazioni_extra deve essere una lista")
    if len(lst) > 20:
        raise HTTPException(400, "Massimo 20 lavorazioni extra per cliente")
    out = []
    for item in lst:
        if not isinstance(item, dict):
            continue
        desc = str(item.get("descrizione") or "").strip()
        try:
            prezzo = round(float(item.get("prezzo") or 0), 2)
        except (TypeError, ValueError):
            prezzo = 0.0
        if not desc and prezzo == 0:
            continue
        out.append({"descrizione": desc, "prezzo": prezzo})
    return out


def _totale_extra(doc: dict) -> float:
    lst = doc.get("lavorazioni_extra") or []
    if not isinstance(lst, list):
        return 0.0
    return round(sum(float((it or {}).get("prezzo") or 0) for it in lst), 2)


async def get_tariffe_doc() -> Tariffe:
    doc = await db.tariffe.find_one({"id": "default"}, {"_id": 0})
    if not doc:
        t = Tariffe()
        await db.tariffe.insert_one(serialize(t))
        return t
    return Tariffe(**doc)


def calcola_alaggio(lunghezza: float, t: Tariffe) -> float:
    """Alaggio: forfait ≤5m e forfait >5m (due tariffe fisse, non moltiplicate per metro)."""
    if lunghezza <= 5:
        return round(t.alaggio_fino_5m, 2)
    return round(t.alaggio_oltre_5m_per_metro, 2)


def calcola_varo(lunghezza: float, t: Tariffe) -> float:
    """Varo: forfait ≤5m e forfait >5m."""
    if lunghezza <= 5:
        return round(t.varo_fino_5m, 2)
    return round(t.varo_oltre_5m_per_metro, 2)


def larghezza_barca(lunghezza: float, larghezza_personalizzata: float = None) -> float:
    """Larghezza a scaglioni di lunghezza (2,5 / 3 / 4). Se `larghezza_personalizzata` > 0
    viene usata come override manuale (catamarani, pontoon, ecc.)."""
    if larghezza_personalizzata and float(larghezza_personalizzata) > 0:
        return float(larghezza_personalizzata)
    L = float(lunghezza or 0)
    if L <= 6.5:
        return 2.5
    if L <= 9.0:
        return 3.0
    return 4.0


def calcola_motore_labor(potenza_hp: float, t: Tariffe, tipo_motore: str = "fuoribordo") -> float:
    """Manodopera manutenzione motore.
    · Fuoribordo: 4 scaglioni HP (2-15, 16-40, 41-150, oltre 150)
    · Entrobordo: tariffa unica valida per qualsiasi HP"""
    if potenza_hp <= 0:
        return 0.0
    if tipo_motore == "entrobordo":
        return round(t.motore_labor_entrobordo or 0, 2)
    # fuoribordo
    if potenza_hp <= 15:
        return round(t.motore_labor_2_15hp, 2)
    if potenza_hp <= 40:
        return round(t.motore_labor_fino_40hp, 2)
    if potenza_hp <= 150:
        return round(t.motore_labor_40_150hp, 2)
    return round(t.motore_labor_oltre_150hp, 2)


def calcola_ricambi(numero_candele: int, numero_termostati: int, t: Tariffe,
                    girante_attivo: bool = True, litri_olio_motore: float = 3.0,
                    litri_olio_piede: float = 1.0,
                    filtro_olio_attivo: bool = True,
                    anodi_interni_attivo: bool = True,
                    anodi_esterni_attivo: bool = True,
                    olio_piede_attivo: bool = True) -> dict:
    """Costo ricambi motore: girante, olio motore (× litri), filtro olio, candele, termostati, olio piede (× litri), anodi, ingrassaggio. Ogni voce è opzionale via flag *_attivo."""
    nc = int(numero_candele or 0)
    nt = int(numero_termostati or 0)
    litri = float(litri_olio_motore or 0)
    litri_piede = float(litri_olio_piede or 0)
    return {
        "girante": round(t.costo_girante, 2) if girante_attivo else 0.0,
        "olio_motore": round(litri * t.costo_olio_motore, 2),
        "filtro_olio": round(t.costo_filtro_olio, 2) if filtro_olio_attivo else 0.0,
        "candele": round(nc * t.costo_candela, 2),
        "termostati": round(nt * t.costo_termostato, 2),
        "olio_piede": round(litri_piede * t.costo_olio_piede, 2) if olio_piede_attivo else 0.0,
        "anodi_interni": round(t.costo_anodi_interni, 2) if anodi_interni_attivo else 0.0,
        "anodi_esterni": round(t.costo_anodi_esterni, 2) if anodi_esterni_attivo else 0.0,
        "ingrassaggio": round(t.costo_ingrassaggio, 2),
    }


def calcola_costi(lunghezza: float, tipo_sosta: str, t: Tariffe,
                  potenza_motore: float = 0.0, numero_candele: int = 4,
                  numero_termostati: int = 1,
                  antivegetativa_attiva: bool = True,
                  girante_attivo: bool = True,
                  litri_olio_motore: float = 3.0,
                  lavaggio_inizio_attivo: bool = True,
                  lavaggio_fine_attivo: bool = True,
                  secondo_motore: bool = False,
                  potenza_motore_2: float = 0.0,
                  litri_olio_motore_2: float = 3.0,
                  numero_candele_2: int = 4,
                  numero_termostati_2: int = 1,
                  girante_2_attivo: bool = True,
                  scafo_sporco_attivo: bool = False,
                  copertura_attiva: bool = False,
                  litri_olio_piede: float = 1.0,
                  litri_olio_piede_2: float = 1.0,
                  giorni_sosta_temporanea: int = 0,
                  destinazione_alaggio_varo: str = "marina_di_campo",
                  alaggio_varo_attivo: bool = False,
                  numero_movimenti: int = 1,
                  primo_motore_attivo: bool = True,
                  tipo_motore: str = "fuoribordo",
                  tipo_motore_2: str = "fuoribordo",
                  filtro_olio_attivo: bool = True,
                  anodi_interni_attivo: bool = True,
                  anodi_esterni_attivo: bool = True,
                  olio_piede_attivo: bool = True,
                  filtro_olio_2_attivo: bool = True,
                  anodi_interni_2_attivo: bool = True,
                  anodi_esterni_2_attivo: bool = True,
                  olio_piede_2_attivo: bool = True,
                  larghezza_personalizzata: float = None) -> dict:
    """Calcola costi automatici in base a lunghezza, tipo sosta e (uno o due) motori."""
    if primo_motore_attivo:
        manodopera = calcola_motore_labor(potenza_motore, t, tipo_motore)
        ricambi = calcola_ricambi(numero_candele, numero_termostati, t, girante_attivo,
                                  litri_olio_motore, litri_olio_piede,
                                  filtro_olio_attivo, anodi_interni_attivo, anodi_esterni_attivo,
                                  olio_piede_attivo)
        ricambi_tot = round(sum(ricambi.values()), 2)
    else:
        manodopera = 0.0
        ricambi = {}
        ricambi_tot = 0.0

    manodopera_2 = 0.0
    ricambi_2_tot = 0.0
    ricambi_2 = {}
    if secondo_motore:
        manodopera_2 = calcola_motore_labor(potenza_motore_2, t, tipo_motore_2)
        ricambi_2 = calcola_ricambi(numero_candele_2, numero_termostati_2, t, girante_2_attivo,
                                    litri_olio_motore_2, litri_olio_piede_2,
                                    filtro_olio_2_attivo, anodi_interni_2_attivo, anodi_esterni_2_attivo,
                                    olio_piede_2_attivo)
        ricambi_2_tot = round(sum(ricambi_2.values()), 2)

    motore_tot = round(manodopera + ricambi_tot + manodopera_2 + ricambi_2_tot, 2)

    # Superficie occupata: lunghezza × larghezza (override manuale se presente)
    larghezza = larghezza_barca(lunghezza, larghezza_personalizzata)
    mq = round(float(lunghezza or 0) * larghezza, 2)

    antiveg = round(mq * t.antivegetativa_per_metro, 2) if antivegetativa_attiva else 0.0
    scafo_sporco = round(lunghezza * t.maggiorazione_scafo_sporco_per_metro, 2) if scafo_sporco_attivo else 0.0
    lav_inizio = round(lunghezza * t.costo_lavaggio_inizio_stagione, 2) if lavaggio_inizio_attivo else 0.0
    lav_fine = round(lunghezza * t.costo_lavaggio_fine_stagione, 2) if lavaggio_fine_attivo else 0.0

    base = {
        "costo_antivegetativa": antiveg,
        "costo_manutenzione_motore": motore_tot,
        "costo_manodopera_motore": manodopera,
        "costo_ricambi_totale": ricambi_tot,
        "costo_manodopera_motore_2": manodopera_2,
        "costo_ricambi_motore_2_totale": ricambi_2_tot,
        "costo_lavaggio_inizio": lav_inizio,
        "costo_lavaggio_fine": lav_fine,
        "costo_scafo_sporco": scafo_sporco,
        "ricambi_dettaglio": ricambi,
        "ricambi_2_dettaglio": ricambi_2,
    }

    movimentazione = round(lunghezza * t.costo_movimentazione_per_metro, 2) if tipo_sosta == "fuori_sede" else 0.0
    taccaggio = round(lunghezza * t.costo_taccaggio_per_metro, 2) if tipo_sosta == "fuori_sede" else 0.0
    base["costo_movimentazione"] = movimentazione
    base["costo_taccaggio"] = taccaggio

    copertura = round(mq * t.copertura_per_metro, 2) if copertura_attiva else 0.0

    mov = max(1, int(numero_movimenti or 1))
    if alaggio_varo_attivo:
        if destinazione_alaggio_varo == "marina_di_campo":
            alaggio_val = round(calcola_alaggio(lunghezza, t) * mov, 2)
            varo_val = round(calcola_varo(lunghezza, t) * mov, 2)
        else:
            alaggio_val = 0.0
            varo_val = 0.0
    else:
        alaggio_val = 0.0
        varo_val = 0.0

    if tipo_sosta == "fuori":
        base.update({
            "costo_sosta": round(mq * t.sosta_fuori_per_metro, 2),
            "costo_copertura": copertura,
            "costo_alaggio": alaggio_val,
            "costo_varo": varo_val,
        })
    elif tipo_sosta == "fuori_sede":
        base.update({
            "costo_sosta": 0.0,
            "costo_copertura": copertura,
            "costo_alaggio": alaggio_val,
            "costo_varo": varo_val,
        })
    elif tipo_sosta == "temporanea":
        giorni = int(giorni_sosta_temporanea or 0)
        base.update({
            "costo_sosta": round(giorni * mq * t.sosta_temporanea_giornaliera, 2),
            "costo_copertura": copertura,
            "costo_alaggio": alaggio_val,
            "costo_varo": varo_val,
        })
    else:
        base.update({
            "costo_sosta": round(mq * t.sosta_dentro_per_metro, 2),
            "costo_copertura": copertura,
            "costo_alaggio": alaggio_val,
            "costo_varo": varo_val,
        })
    return base


def _euro(v: float) -> str:
    s = f"{v:,.2f}"
    return "€ " + s.replace(",", "X").replace(".", ",").replace("X", ".")
