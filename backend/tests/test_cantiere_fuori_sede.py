"""Backend tests for Portomare - Iteration 5.
Focus:
  - /api/cantiere GET/PUT (new resource)
  - Tariffe: costo_movimentazione_per_metro, costo_taccaggio_per_metro,
             costo_lavaggio_inizio_stagione, costo_lavaggio_fine_stagione,
             maggiorazione_scafo_sporco_per_metro
  - calcola-costi tipo_sosta='fuori_sede' logic
  - antivegetativa_attiva=false triggers scafo_sporco
  - lavaggio_inizio_attivo/fine_attivo toggles
  - Cliente POST with tipo_sosta='fuori_sede' and 'invalid'
  - /api/stats returns sosta_fuori_sede
  - PDF preventivo uses cantiere.nome + contatti
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "http://localhost:8001"
API = f"{BASE_URL}/api"


# session fixture provided by conftest.py (authenticated)


@pytest.fixture(scope="module", autouse=True)
def _restore_tariffe_defaults(session):
    """Ensure tariffe are set to iter-5 defaults before running this module."""
    session.put(f"{API}/tariffe", json={
        "copertura_per_metro": 45.0,
        "alaggio_fino_5m": 90.0,
        "alaggio_oltre_5m_per_metro": 25.0,
        "varo_fino_5m": 90.0,
        "varo_oltre_5m_per_metro": 25.0,
        "antivegetativa_per_metro": 60.0,
        "motore_labor_fino_40hp": 180.0,
        "motore_labor_40_150hp": 320.0,
        "motore_labor_oltre_150hp": 550.0,
        "costo_girante": 45.0,
        "costo_olio_motore": 12.0,
        "costo_filtro_olio": 18.0,
        "costo_candela": 12.0,
        "costo_termostato": 35.0,
        "costo_olio_piede": 25.0,
        "costo_anodi_interni": 40.0,
        "costo_anodi_esterni": 60.0,
        "costo_ingrassaggio": 30.0,
        "sosta_dentro_per_metro": 180.0,
        "sosta_fuori_per_metro": 120.0,
        "costo_movimentazione_per_metro": 25.0,
        "costo_taccaggio_per_metro": 20.0,
        "costo_lavaggio_inizio_stagione": 80.0,
        "costo_lavaggio_fine_stagione": 80.0,
        "maggiorazione_scafo_sporco_per_metro": 15.0,
    })
    yield


class TestCantiereEndpoint:
    """GET/PUT /api/cantiere"""

    def test_get_cantiere_default_fields(self, session):
        r = session.get(f"{API}/cantiere")
        assert r.status_code == 200
        d = r.json()
        for k in ("nome", "slogan", "indirizzo", "citta", "cap", "provincia",
                  "telefono", "email", "piva", "sito_web", "orari", "logo_base64"):
            assert k in d, f"Missing field: {k}"

    def test_put_cantiere_persists_fields(self, session):
        payload = {
            "nome": "TEST_Cantiere_Iter5",
            "indirizzo": "Via Test 1",
            "citta": "Genova",
            "cap": "16128",
            "telefono": "010-1234567",
            "email": "test-iter5@cantiere.it",
        }
        r = session.put(f"{API}/cantiere", json=payload)
        assert r.status_code == 200
        d = r.json()
        for k, v in payload.items():
            assert d[k] == v, f"Field {k} not persisted: {d[k]} != {v}"
        # verify GET persists
        r2 = session.get(f"{API}/cantiere")
        d2 = r2.json()
        for k, v in payload.items():
            assert d2[k] == v

    def test_put_cantiere_logo_base64(self, session):
        # small 1x1 png data URL
        logo = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkAAIAAAoAAv/lxKUAAAAASUVORK5CYII="
        r = session.put(f"{API}/cantiere", json={"logo_base64": logo})
        assert r.status_code == 200
        assert r.json()["logo_base64"] == logo
        r2 = session.get(f"{API}/cantiere")
        assert r2.json()["logo_base64"] == logo
        # cleanup logo
        session.put(f"{API}/cantiere", json={"logo_base64": ""})


class TestTariffeFuoriSedeLavaggi:
    """Tariffe: new fields defaults 25/20/80/80/15"""

    def test_tariffe_new_fields_defaults(self, session):
        r = session.get(f"{API}/tariffe")
        assert r.status_code == 200
        d = r.json()
        assert d["costo_movimentazione_per_metro"] == 25.0
        assert d["costo_taccaggio_per_metro"] == 20.0
        assert d["costo_lavaggio_inizio_stagione"] == 80.0
        assert d["costo_lavaggio_fine_stagione"] == 80.0
        assert d["maggiorazione_scafo_sporco_per_metro"] == 15.0


class TestCalcolaCostiFuoriSede:
    """calcola-costi with tipo_sosta='fuori_sede'"""

    def test_fuori_sede_only_movimentazione_taccaggio(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "fuori_sede",
            "potenza_motore": 0,  # zero to avoid confounding motore
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_sosta"] == 0
        assert d["costo_copertura"] == 0
        assert d["costo_alaggio"] == 0
        assert d["costo_varo"] == 0
        # L * 25 and L * 20
        assert d["costo_movimentazione"] == 8 * 25.0
        assert d["costo_taccaggio"] == 8 * 20.0

    def test_dentro_no_movimentazione_taccaggio(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "dentro", "potenza_motore": 0,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_movimentazione"] == 0
        assert d["costo_taccaggio"] == 0
        assert d["costo_sosta"] == 8 * 180.0

    def test_fuori_no_movimentazione_taccaggio(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "fuori", "potenza_motore": 0,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_movimentazione"] == 0
        assert d["costo_taccaggio"] == 0


class TestScafoSporcoAndLavaggi:
    def test_antivegetativa_off_adds_scafo_sporco(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "fuori",
            "potenza_motore": 0,
            "antivegetativa_attiva": "false",
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_antivegetativa"] == 0
        assert d["costo_scafo_sporco"] == 8 * 15.0  # 120

    def test_antivegetativa_on_no_scafo_sporco(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "fuori",
            "potenza_motore": 0,
            "antivegetativa_attiva": "true",
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_scafo_sporco"] == 0
        assert d["costo_antivegetativa"] == 8 * 60.0

    def test_lavaggio_inizio_off(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "fuori",
            "potenza_motore": 0,
            "lavaggio_inizio_attivo": "false",
        })
        d = r.json()
        assert d["costo_lavaggio_inizio"] == 0
        assert d["costo_lavaggio_fine"] == 80.0

    def test_lavaggio_fine_off(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "fuori",
            "potenza_motore": 0,
            "lavaggio_fine_attivo": "false",
        })
        d = r.json()
        assert d["costo_lavaggio_fine"] == 0
        assert d["costo_lavaggio_inizio"] == 80.0

    def test_lavaggi_both_on_default(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "fuori",
            "potenza_motore": 0,
        })
        d = r.json()
        assert d["costo_lavaggio_inizio"] == 80.0
        assert d["costo_lavaggio_fine"] == 80.0


class TestClienteFuoriSede:
    def test_create_cliente_fuori_sede(self, session):
        payload = {
            "nome": "TEST_Fuori", "cognome": "TEST_Sede",
            "tipo_barca": "Rimessaggio test", "lunghezza": 8.0,
            "tipo_sosta": "fuori_sede",
            "potenza_motore": 0,
        }
        r = session.post(f"{API}/clienti", json=payload)
        assert r.status_code == 200, r.text
        c = r.json()
        try:
            assert c["tipo_sosta"] == "fuori_sede"
            assert c["costo_sosta"] == 0
            assert c["costo_copertura"] == 0
            assert c["costo_alaggio"] == 0
            assert c["costo_varo"] == 0
            assert c["costo_movimentazione"] == 8 * 25.0
            assert c["costo_taccaggio"] == 8 * 20.0
            # verify persistence
            r2 = session.get(f"{API}/clienti/{c['id']}")
            got = r2.json()
            assert got["tipo_sosta"] == "fuori_sede"
            assert got["costo_movimentazione"] == 200.0
            assert got["costo_taccaggio"] == 160.0
        finally:
            session.delete(f"{API}/clienti/{c['id']}")

    def test_create_cliente_invalid_tipo_sosta(self, session):
        payload = {
            "nome": "TEST_Invalid", "cognome": "TEST_X",
            "tipo_barca": "test", "lunghezza": 5.0,
            "tipo_sosta": "invalid",
        }
        r = session.post(f"{API}/clienti", json=payload)
        assert r.status_code == 400

    def test_stats_returns_sosta_fuori_sede(self, session):
        # create one fuori_sede cliente
        payload = {
            "nome": "TEST_Stats", "cognome": "TEST_FS",
            "tipo_barca": "test", "lunghezza": 6.0,
            "tipo_sosta": "fuori_sede",
        }
        r = session.post(f"{API}/clienti", json=payload)
        assert r.status_code == 200
        c = r.json()
        try:
            r2 = session.get(f"{API}/stats")
            assert r2.status_code == 200
            d = r2.json()
            assert "sosta_fuori_sede" in d
            assert d["sosta_fuori_sede"] >= 1
        finally:
            session.delete(f"{API}/clienti/{c['id']}")


class TestPDFCantiereBranding:
    def test_pdf_uses_cantiere_nome_and_contatti(self, session):
        # set cantiere data
        session.put(f"{API}/cantiere", json={
            "nome": "TEST_Portomare_Iter5",
            "indirizzo": "Via Marina 42",
            "citta": "Genova",
            "cap": "16128",
            "provincia": "GE",
            "telefono": "+39 010 999 8888",
            "email": "info@iter5-test.it",
            "piva": "01234567890",
        })
        # create a client with some costs
        cpayload = {
            "nome": "TEST_Pdf", "cognome": "TEST_Iter5",
            "tipo_barca": "Cabinato test", "lunghezza": 8.0,
            "tipo_sosta": "fuori_sede",
            "potenza_motore": 60,
        }
        r = session.post(f"{API}/clienti", json=cpayload)
        assert r.status_code == 200
        c = r.json()
        try:
            pr = session.get(f"{API}/clienti/{c['id']}/preventivo.pdf")
            assert pr.status_code == 200
            assert pr.content[:4] == b"%PDF"
            assert len(pr.content) > 3000
            # PDF is binary; can't easily grep for text but we assert size
        finally:
            session.delete(f"{API}/clienti/{c['id']}")
            # restore cantiere to defaults (empty fields)
            session.put(f"{API}/cantiere", json={
                "nome": "Portomare", "indirizzo": "", "citta": "", "cap": "",
                "provincia": "", "telefono": "", "email": "", "piva": "",
            })
