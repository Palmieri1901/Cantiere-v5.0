"""Backend tests for Portomare - Iteration 3
Focus: tiered pricing for alaggio/varo, tiered motor labor (HP), motor parts (ricambi).

All tests live in a single class so pytest-xdist loadscope pins them to one worker,
avoiding races on the shared tariffe state across parallel workers.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "http://localhost:8001"
API = f"{BASE_URL}/api"

DEFAULTS = {
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
    "costo_olio_motore": 55.0,
    "costo_filtro_olio": 18.0,
    "costo_candela": 12.0,
    "costo_termostato": 35.0,
    "costo_olio_piede": 25.0,
    "sosta_dentro_per_metro": 180.0,
    "sosta_fuori_per_metro": 120.0,
}

REQUIRED_TARIFFE_FIELDS = list(DEFAULTS.keys())


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="function", autouse=True)
def reset_tariffe(session):
    """Reset tariffe to known defaults before every test in this class."""
    r = session.put(f"{API}/tariffe", json=DEFAULTS)
    assert r.status_code == 200
    yield


class TestTariffeAndMotore:
    """Combined class so xdist loadscope keeps everything on a single worker."""

    # ---------- Tariffe schema ----------
    def test_tariffe_has_all_new_fields(self, session):
        r = session.get(f"{API}/tariffe")
        assert r.status_code == 200
        data = r.json()
        for f in REQUIRED_TARIFFE_FIELDS:
            assert f in data, f"Missing field: {f}"
            assert isinstance(data[f], (int, float)), f"Not numeric: {f}"

    def test_put_tariffe_updates_new_fields(self, session):
        r = session.put(f"{API}/tariffe", json={
            "motore_labor_40_150hp": 333.0,
            "costo_candela": 14.5,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["motore_labor_40_150hp"] == 333.0
        assert d["costo_candela"] == 14.5

        r2 = session.get(f"{API}/tariffe")
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["motore_labor_40_150hp"] == 333.0
        assert d2["costo_candela"] == 14.5

    # ---------- Calcola-costi tiered logic ----------
    def test_small_boat_forfait_and_low_hp(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 4, "tipo_sosta": "fuori",
            "potenza_motore": 30, "numero_candele": 2, "numero_termostati": 1,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["costo_alaggio"] == 90.0
        assert d["costo_varo"] == 90.0
        assert d["costo_manodopera_motore"] == 180.0
        rb = d["ricambi_dettaglio"]
        assert rb["girante"] == 45.0
        assert rb["olio_motore"] == 55.0
        assert rb["filtro_olio"] == 18.0
        assert rb["candele"] == 2 * 12.0
        assert rb["termostati"] == 1 * 35.0
        assert rb["olio_piede"] == 25.0
        expected_ricambi = 45 + 55 + 18 + 24 + 35 + 25
        assert d["costo_ricambi_totale"] == expected_ricambi
        assert d["costo_manutenzione_motore"] == 180 + expected_ricambi
        assert d["costo_sosta"] == 4 * 120.0
        assert d["costo_copertura"] == 4 * 45.0
        assert d["costo_antivegetativa"] == 4 * 60.0

    def test_big_boat_per_meter_and_high_hp(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 10, "tipo_sosta": "fuori",
            "potenza_motore": 200, "numero_candele": 6, "numero_termostati": 2,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["costo_alaggio"] == 10 * 25.0
        assert d["costo_varo"] == 10 * 25.0
        assert d["costo_manodopera_motore"] == 550.0
        rb = d["ricambi_dettaglio"]
        assert rb["candele"] == 6 * 12.0
        assert rb["termostati"] == 2 * 35.0
        expected_ricambi = 45 + 55 + 18 + 72 + 70 + 25
        assert d["costo_ricambi_totale"] == expected_ricambi
        assert d["costo_manutenzione_motore"] == 550 + expected_ricambi

    def test_mid_range_hp_40_150(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "dentro",
            "potenza_motore": 100, "numero_candele": 4, "numero_termostati": 1,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_manodopera_motore"] == 320.0
        assert d["costo_alaggio"] == 0.0
        assert d["costo_varo"] == 0.0
        assert d["costo_copertura"] == 0.0
        assert d["costo_sosta"] == 8 * 180.0

    def test_zero_hp_no_manodopera(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 6, "tipo_sosta": "fuori",
            "potenza_motore": 0, "numero_candele": 4, "numero_termostati": 1,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_manodopera_motore"] == 0.0
        assert d["costo_manutenzione_motore"] == d["costo_ricambi_totale"]

    # ---------- Cliente with motor ----------
    def test_create_cliente_with_motor_computes_correctly(self, session):
        payload = {
            "nome": "TEST_Luca", "cognome": "TEST_Rossi",
            "tipo_barca": "Cabinato test", "lunghezza": 10.0,
            "tipo_sosta": "fuori",
            "potenza_motore": 200, "numero_candele": 6, "numero_termostati": 2,
        }
        r = session.post(f"{API}/clienti", json=payload)
        assert r.status_code == 200, r.text
        c = r.json()
        try:
            expected_ricambi = 45 + 55 + 18 + 72 + 70 + 25
            assert c["costo_manodopera_motore"] == 550.0
            assert c["costo_ricambi_totale"] == expected_ricambi
            assert c["costo_manutenzione_motore"] == 550 + expected_ricambi
            assert c["costo_alaggio"] == 250.0
            assert c["costo_varo"] == 250.0
            r2 = session.get(f"{API}/clienti/{c['id']}")
            assert r2.status_code == 200
            got = r2.json()
            assert got["costo_manutenzione_motore"] == c["costo_manutenzione_motore"]
            assert got["potenza_motore"] == 200
            assert got["numero_candele"] == 6
            assert got["numero_termostati"] == 2
        finally:
            session.delete(f"{API}/clienti/{c['id']}")

    def test_create_cliente_small_boat_forfait(self, session):
        payload = {
            "nome": "TEST_Anna", "cognome": "TEST_Bianchi",
            "tipo_barca": "Gommone test", "lunghezza": 4.0,
            "tipo_sosta": "fuori",
            "potenza_motore": 30, "numero_candele": 2, "numero_termostati": 1,
        }
        r = session.post(f"{API}/clienti", json=payload)
        assert r.status_code == 200, r.text
        c = r.json()
        try:
            assert c["costo_alaggio"] == 90.0
            assert c["costo_varo"] == 90.0
            assert c["costo_manodopera_motore"] == 180.0
        finally:
            session.delete(f"{API}/clienti/{c['id']}")

    # ---------- PDF regression with motor ----------
    def test_pdf_over_3000_bytes_with_motor(self, session):
        payload = {
            "nome": "TEST_Pdf", "cognome": "TEST_Cliente",
            "tipo_barca": "Yacht test", "lunghezza": 12.0,
            "tipo_sosta": "fuori",
            "potenza_motore": 250, "numero_candele": 8, "numero_termostati": 2,
        }
        rc = session.post(f"{API}/clienti", json=payload)
        assert rc.status_code == 200
        c = rc.json()
        try:
            session.post(f"{API}/lavori", json={
                "cliente_id": c["id"], "data": "2026-01-05",
                "tipo": "Manutenzione motore", "descrizione": "TEST tagliando",
                "costo": 700.0, "materiali": "olio, filtri", "stato": "completato",
            })
            r = session.get(f"{API}/clienti/{c['id']}/preventivo.pdf")
            assert r.status_code == 200
            assert r.headers.get("content-type", "").startswith("application/pdf")
            assert r.content[:4] == b"%PDF"
            assert len(r.content) > 3000, f"PDF too small: {len(r.content)} bytes"
        finally:
            lav = session.get(f"{API}/clienti/{c['id']}/lavori").json()
            for l in lav:
                session.delete(f"{API}/lavori/{l['id']}")
            session.delete(f"{API}/clienti/{c['id']}")
