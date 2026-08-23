"""Pydantic models for the Cantiere Nautico API."""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class Tariffe(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: "default")
    copertura_per_metro: float = 45.0
    alaggio_fino_5m: float = 90.0
    alaggio_oltre_5m_per_metro: float = 25.0
    varo_fino_5m: float = 90.0
    varo_oltre_5m_per_metro: float = 25.0
    antivegetativa_per_metro: float = 60.0
    sosta_temporanea_giornaliera: float = 25.0
    motore_labor: float = 180.0
    # Maggiorazione € manodopera quando il motore è entrobordo
    maggiorazione_entrobordo: float = 50.0
    costo_girante: float = 45.0
    costo_olio_motore: float = 12.0
    costo_filtro_olio: float = 18.0
    costo_candela: float = 12.0
    costo_termostato: float = 35.0
    costo_olio_piede: float = 25.0
    costo_anodi_interni: float = 40.0
    costo_anodi_esterni: float = 60.0
    costo_ingrassaggio: float = 30.0
    sosta_dentro_per_metro: float = 180.0
    sosta_fuori_per_metro: float = 120.0
    costo_movimentazione_per_metro: float = 25.0
    costo_taccaggio_per_metro: float = 20.0
    costo_lavaggio_inizio_stagione: float = 80.0
    costo_lavaggio_fine_stagione: float = 80.0
    maggiorazione_scafo_sporco_per_metro: float = 15.0
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TariffeUpdate(BaseModel):
    """Partial update per Tariffe: tutti i campi opzionali."""
    model_config = ConfigDict(extra="ignore")

    copertura_per_metro: Optional[float] = None
    alaggio_fino_5m: Optional[float] = None
    alaggio_oltre_5m_per_metro: Optional[float] = None
    varo_fino_5m: Optional[float] = None
    varo_oltre_5m_per_metro: Optional[float] = None
    antivegetativa_per_metro: Optional[float] = None
    sosta_temporanea_giornaliera: Optional[float] = None
    motore_labor: Optional[float] = None
    maggiorazione_entrobordo: Optional[float] = None
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
    lunghezza: float
    tipo_sosta: str
    giorni_sosta_temporanea: int = 0
    anno: int = Field(default_factory=lambda: datetime.now().year)
    posto_barca: Optional[int] = None
    telefono: Optional[str] = ""
    email: Optional[str] = ""
    codice_fiscale: Optional[str] = ""
    indirizzo: Optional[str] = ""
    cellulare: Optional[str] = ""
    pagato: bool = False
    data_pagamento: Optional[str] = None
    potenza_motore: float = 0.0
    litri_olio_motore: float = 3.0
    litri_olio_piede: float = 1.0
    numero_candele: int = 4
    numero_termostati: int = 1
    tipo_motore: str = "fuoribordo"  # "fuoribordo" | "entrobordo"
    primo_motore_attivo: bool = True
    secondo_motore: bool = False
    potenza_motore_2: float = 0.0
    litri_olio_motore_2: float = 3.0
    litri_olio_piede_2: float = 1.0
    numero_candele_2: int = 4
    numero_termostati_2: int = 1
    tipo_motore_2: str = "fuoribordo"
    girante_2_attivo: bool = True
    antivegetativa_attiva: bool = True
    scafo_sporco_attivo: bool = False
    copertura_attiva: bool = False
    girante_attivo: bool = True
    lavaggio_inizio_attivo: bool = True
    lavaggio_fine_attivo: bool = True
    alaggio_varo_attivo: bool = False
    numero_movimenti: int = 1
    destinazione_alaggio_varo: str = "marina_di_campo"
    destinazione_altra_nome: Optional[str] = ""
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
    costo_ricambi_totale: float = 0.0
    costo_manodopera_motore: float = 0.0
    costo_ricambi_motore_2_totale: float = 0.0
    costo_manodopera_motore_2: float = 0.0
    lavorazioni_extra: List[dict] = Field(default_factory=list)
    override_costi: bool = False
    note_lavori: str = ""
    scadenza_antivegetativa: Optional[str] = None
    scadenza_manutenzione: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ClienteCreate(BaseModel):
    nome: str
    cognome: str
    tipo_barca: str
    lunghezza: float
    tipo_sosta: str
    giorni_sosta_temporanea: Optional[int] = None
    anno: Optional[int] = None
    posto_barca: Optional[int] = None
    telefono: Optional[str] = ""
    email: Optional[str] = ""
    codice_fiscale: Optional[str] = ""
    indirizzo: Optional[str] = ""
    cellulare: Optional[str] = ""
    pagato: Optional[bool] = None
    data_pagamento: Optional[str] = None
    potenza_motore: Optional[float] = 0.0
    litri_olio_motore: Optional[float] = 3.0
    litri_olio_piede: Optional[float] = None
    numero_candele: Optional[int] = 4
    numero_termostati: Optional[int] = 1
    tipo_motore: Optional[str] = None
    secondo_motore: Optional[bool] = False
    primo_motore_attivo: Optional[bool] = None
    potenza_motore_2: Optional[float] = 0.0
    litri_olio_motore_2: Optional[float] = 3.0
    litri_olio_piede_2: Optional[float] = None
    numero_candele_2: Optional[int] = 4
    numero_termostati_2: Optional[int] = 1
    tipo_motore_2: Optional[str] = None
    girante_2_attivo: Optional[bool] = None
    antivegetativa_attiva: Optional[bool] = True
    scafo_sporco_attivo: Optional[bool] = None
    copertura_attiva: Optional[bool] = None
    girante_attivo: Optional[bool] = True
    lavaggio_inizio_attivo: Optional[bool] = True
    lavaggio_fine_attivo: Optional[bool] = True
    costo_sosta: Optional[float] = None
    costo_copertura: Optional[float] = None
    costo_alaggio: Optional[float] = None
    costo_varo: Optional[float] = None
    alaggio_varo_attivo: Optional[bool] = None
    numero_movimenti: Optional[int] = None
    destinazione_alaggio_varo: Optional[str] = None
    destinazione_altra_nome: Optional[str] = None
    costo_antivegetativa: Optional[float] = None
    costo_manutenzione_motore: Optional[float] = None
    costo_lavaggio_inizio: Optional[float] = None
    costo_lavaggio_fine: Optional[float] = None
    costo_scafo_sporco: Optional[float] = None
    costo_movimentazione: Optional[float] = None
    costo_taccaggio: Optional[float] = None
    lavorazioni_extra: Optional[List[dict]] = None
    override_costi: bool = False
    note_lavori: str = ""
    scadenza_antivegetativa: Optional[str] = None
    scadenza_manutenzione: Optional[str] = None


class Lavoro(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cliente_id: str
    data: str
    tipo: str
    descrizione: str = ""
    costo: float = 0.0
    materiali: str = ""
    stato: str = "completato"
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
    logo_base64: str = ""
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


class PreventivoInline(ClienteCreate):
    """Payload preventivo veloce: solo nome e cognome sono obbligatori."""
    nome: str
    cognome: str
    tipo_barca: Optional[str] = "—"
    lunghezza: Optional[float] = 0.0
    tipo_sosta: Optional[str] = "dentro"


class RestoreRequest(BaseModel):
    version: Optional[int] = None
    cantiere: Optional[dict] = None
    tariffe: Optional[dict] = None
    clienti: Optional[List[dict]] = None
    lavori: Optional[List[dict]] = None


class PagatoUpdate(BaseModel):
    pagato: bool


class ApriAnnoRequest(BaseModel):
    anno: int
    duplica_da: Optional[int] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    nome: Optional[str] = ""
