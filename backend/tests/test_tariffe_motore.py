"""Backend tests for Portomare - Iteration 4
Focus:
- Tariffe schema now includes costo_anodi_interni (40), costo_anodi_esterni (60), costo_ingrassaggio (30)
- calcola-costi ricambi_dettaglio has 9 items (girante, olio_motore, filtro_olio, candele, termostati,
  olio_piede, anodi_interni, anodi_esterni, ingrassaggio)
- Toggle switches: antivegetativa_attiva (zeroes costo_antivegetativa) and girante_attivo (zeroes ricambio girante)
- Regression: tiered pricing (alaggio/varo/manodopera), Cliente CRUD, PDF preventivo.

All tests in single class so xdist loadscope pins them to one worker (shared tariffe state).
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    BASE_URL = "http://localhost:8001"
API = f"{BASE_URL}/api"

# Complete defaults including iteration-4 additions
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
    "costo_olio_motore": 12.0,  # € / litro (iter-5 semantics: multiplied by litri_olio_motore)
    "costo_filtro_olio": 18.0,
    "costo_candela": 12.0,
    "costo_termostato": 35.0,
    "costo_olio_piede": 25.0,
    "costo_anodi_interni": 40.0,
    "costo_anodi_esterni": 60.0,
    "costo_ingrassaggio": 30.0,
    "sosta_dentro_per_metro": 180.0,
    "sosta_fuori_per_metro": 120.0,
}

REQUIRED_TARIFFE_FIELDS = list(DEFAULTS.keys())


# session fixture provided by conftest.py (authenticated)


@pytest.fixture(scope="function", autouse=True)
def reset_tariffe(session):
    """Reset tariffe to full known defaults (incl. new fields) before every test."""
    r = session.put(f"{API}/tariffe", json=DEFAULTS)
    assert r.status_code == 200
    yield


class TestTariffeAndMotore:
    """Combined class so xdist loadscope keeps everything on a single worker."""

    # ---------- Tariffe schema (iter 4) ----------
    def test_tariffe_has_all_fields_incl_new(self, session):
        r = session.get(f"{API}/tariffe")
        assert r.status_code == 200
        data = r.json()
        for f in REQUIRED_TARIFFE_FIELDS:
            assert f in data, f"Missing field: {f}"
            assert isinstance(data[f], (int, float)), f"Not numeric: {f}"
        # explicit defaults for new fields
        assert data["costo_anodi_interni"] == 40.0
        assert data["costo_anodi_esterni"] == 60.0
        assert data["costo_ingrassaggio"] == 30.0

    def test_put_tariffe_updates_new_fields_persist(self, session):
        r = session.put(f"{API}/tariffe", json={
            "costo_anodi_interni": 50.0,
            "costo_ingrassaggio": 35.0,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_anodi_interni"] == 50.0
        assert d["costo_ingrassaggio"] == 35.0
        # Ensure other unchanged fields keep prior values
        assert d["costo_anodi_esterni"] == 60.0

        # GET verifies persistence
        r2 = session.get(f"{API}/tariffe")
        d2 = r2.json()
        assert d2["costo_anodi_interni"] == 50.0
        assert d2["costo_ingrassaggio"] == 35.0
        assert d2["costo_anodi_esterni"] == 60.0

    # ---------- Calcola-costi with iter 4 expected total ----------
    def test_calcola_costi_ricambi_dettaglio_9_items(self, session):
        """Exact scenario from review request: L=8, fuori, HP=120, 4 candele, 1 termostato."""
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "fuori",
            "potenza_motore": 120, "numero_candele": 4, "numero_termostati": 1,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        rb = d["ricambi_dettaglio"]
        # 9 items required
        expected_keys = {"girante", "olio_motore", "filtro_olio", "candele", "termostati",
                        "olio_piede", "anodi_interni", "anodi_esterni", "ingrassaggio"}
        assert set(rb.keys()) == expected_keys, f"Got: {set(rb.keys())}"
        assert rb["girante"] == 45.0
        assert rb["olio_motore"] == 36.0  # 3L * 12 €/L
        assert rb["filtro_olio"] == 18.0
        assert rb["candele"] == 48.0  # 4*12
        assert rb["termostati"] == 35.0  # 1*35
        assert rb["olio_piede"] == 25.0
        assert rb["anodi_interni"] == 40.0
        assert rb["anodi_esterni"] == 60.0
        assert rb["ingrassaggio"] == 30.0
        # total = 45+36+18+48+35+25+40+60+30 = 337
        assert d["costo_ricambi_totale"] == 337.0, f"got {d['costo_ricambi_totale']}"
        # 120 HP -> mid tier manodopera = 320
        assert d["costo_manodopera_motore"] == 320.0
        # motore total = 320 + 337 = 657
        assert d["costo_manutenzione_motore"] == 657.0

    # ---------- Toggle switches (iter 4) ----------
    def test_antivegetativa_disabled_zeroes_cost(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "fuori",
            "potenza_motore": 120, "numero_candele": 4, "numero_termostati": 1,
            "antivegetativa_attiva": "false",
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_antivegetativa"] == 0.0
        # ricambi unchanged
        assert d["costo_ricambi_totale"] == 337.0

    def test_antivegetativa_enabled_computes_cost(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "fuori",
            "potenza_motore": 120, "numero_candele": 4, "numero_termostati": 1,
            "antivegetativa_attiva": "true",
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_antivegetativa"] == 8 * 60.0  # 480

    def test_girante_disabled_zeroes_girante_and_drops_total_by_45(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "fuori",
            "potenza_motore": 120, "numero_candele": 4, "numero_termostati": 1,
            "girante_attivo": "false",
        })
        assert r.status_code == 200
        d = r.json()
        rb = d["ricambi_dettaglio"]
        assert rb["girante"] == 0.0
        # 337 - 45 = 292
        assert d["costo_ricambi_totale"] == 292.0
        # motore total drops by 45 too: 657 - 45 = 612
        assert d["costo_manutenzione_motore"] == 612.0

    def test_both_toggles_disabled(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 8, "tipo_sosta": "fuori",
            "potenza_motore": 120, "numero_candele": 4, "numero_termostati": 1,
            "antivegetativa_attiva": "false",
            "girante_attivo": "false",
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_antivegetativa"] == 0.0
        assert d["ricambi_dettaglio"]["girante"] == 0.0
        assert d["costo_ricambi_totale"] == 292.0

    # ---------- Cliente CRUD with toggles ----------
    def test_create_cliente_with_toggles_off(self, session):
        payload = {
            "nome": "TEST_Toggle", "cognome": "TEST_Off",
            "tipo_barca": "Cabinato test", "lunghezza": 8.0,
            "tipo_sosta": "fuori",
            "potenza_motore": 120, "numero_candele": 4, "numero_termostati": 1,
            "antivegetativa_attiva": False,
            "girante_attivo": False,
        }
        r = session.post(f"{API}/clienti", json=payload)
        assert r.status_code == 200, r.text
        c = r.json()
        try:
            assert c["antivegetativa_attiva"] is False
            assert c["girante_attivo"] is False
            assert c["costo_antivegetativa"] == 0.0
            assert c["costo_ricambi_totale"] == 292.0
            assert c["costo_manutenzione_motore"] == 612.0
            # GET persistence check
            r2 = session.get(f"{API}/clienti/{c['id']}")
            got = r2.json()
            assert got["antivegetativa_attiva"] is False
            assert got["girante_attivo"] is False
            assert got["costo_antivegetativa"] == 0.0
            assert got["costo_ricambi_totale"] == 292.0
        finally:
            session.delete(f"{API}/clienti/{c['id']}")

    def test_update_cliente_toggles_recomputes(self, session):
        # Create with both ON (default)
        payload = {
            "nome": "TEST_Upd", "cognome": "TEST_Toggle",
            "tipo_barca": "Yacht test", "lunghezza": 8.0,
            "tipo_sosta": "fuori",
            "potenza_motore": 120, "numero_candele": 4, "numero_termostati": 1,
        }
        r = session.post(f"{API}/clienti", json=payload)
        assert r.status_code == 200
        c = r.json()
        try:
            # both defaults true
            assert c["antivegetativa_attiva"] is True
            assert c["girante_attivo"] is True
            assert c["costo_antivegetativa"] == 480.0
            assert c["costo_ricambi_totale"] == 337.0

            # PUT with toggles off
            put_payload = dict(payload)
            put_payload["antivegetativa_attiva"] = False
            put_payload["girante_attivo"] = False
            r2 = session.put(f"{API}/clienti/{c['id']}", json=put_payload)
            assert r2.status_code == 200
            u = r2.json()
            assert u["antivegetativa_attiva"] is False
            assert u["girante_attivo"] is False
            assert u["costo_antivegetativa"] == 0.0
            assert u["costo_ricambi_totale"] == 292.0
            assert u["costo_manutenzione_motore"] == 612.0

            # Toggle back ON via PUT
            put_payload["antivegetativa_attiva"] = True
            put_payload["girante_attivo"] = True
            r3 = session.put(f"{API}/clienti/{c['id']}", json=put_payload)
            u3 = r3.json()
            assert u3["costo_antivegetativa"] == 480.0
            assert u3["costo_ricambi_totale"] == 337.0
        finally:
            session.delete(f"{API}/clienti/{c['id']}")

    # ---------- Regression: tiered pricing (still works) ----------
    def test_small_boat_forfait_and_low_hp(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 4, "tipo_sosta": "fuori",
            "potenza_motore": 30, "numero_candele": 2, "numero_termostati": 1,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_alaggio"] == 90.0
        assert d["costo_varo"] == 90.0
        assert d["costo_manodopera_motore"] == 180.0
        # ricambi: 45+36+18+(2*12=24)+35+25+40+60+30 = 313
        assert d["costo_ricambi_totale"] == 313.0
        assert d["costo_manutenzione_motore"] == 180 + 313

    def test_big_boat_and_high_hp(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 10, "tipo_sosta": "fuori",
            "potenza_motore": 200, "numero_candele": 6, "numero_termostati": 2,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_alaggio"] == 250.0
        assert d["costo_varo"] == 250.0
        assert d["costo_manodopera_motore"] == 550.0
        # ricambi: 45+36+18+(6*12=72)+(2*35=70)+25+40+60+30 = 396
        assert d["costo_ricambi_totale"] == 396.0

    def test_zero_hp_no_manodopera(self, session):
        r = session.get(f"{API}/calcola-costi", params={
            "lunghezza": 6, "tipo_sosta": "fuori",
            "potenza_motore": 0, "numero_candele": 4, "numero_termostati": 1,
        })
        assert r.status_code == 200
        d = r.json()
        assert d["costo_manodopera_motore"] == 0.0
        assert d["costo_manutenzione_motore"] == d["costo_ricambi_totale"]

    # ---------- PDF ----------
    def test_pdf_over_3000_bytes_with_new_ricambi_rows(self, session):
        payload = {
            "nome": "TEST_Pdf", "cognome": "TEST_Iter4",
            "tipo_barca": "Yacht test", "lunghezza": 10.0,
            "tipo_sosta": "fuori",
            "potenza_motore": 120, "numero_candele": 4, "numero_termostati": 1,
        }
        rc = session.post(f"{API}/clienti", json=payload)
        assert rc.status_code == 200
        c = rc.json()
        try:
            r = session.get(f"{API}/clienti/{c['id']}/preventivo.pdf")
            assert r.status_code == 200
            assert r.headers.get("content-type", "").startswith("application/pdf")
            assert r.content[:4] == b"%PDF"
            assert len(r.content) > 3000
        finally:
            session.delete(f"{API}/clienti/{c['id']}")

    def test_pdf_with_girante_off_still_valid(self, session):
        payload = {
            "nome": "TEST_Pdf2", "cognome": "TEST_NoGirante",
            "tipo_barca": "Yacht test", "lunghezza": 10.0,
            "tipo_sosta": "fuori",
            "potenza_motore": 120, "numero_candele": 4, "numero_termostati": 1,
            "girante_attivo": False,
        }
        rc = session.post(f"{API}/clienti", json=payload)
        assert rc.status_code == 200
        c = rc.json()
        try:
            r = session.get(f"{API}/clienti/{c['id']}/preventivo.pdf")
            assert r.status_code == 200
            assert len(r.content) > 3000
        finally:
            session.delete(f"{API}/clienti/{c['id']}")
