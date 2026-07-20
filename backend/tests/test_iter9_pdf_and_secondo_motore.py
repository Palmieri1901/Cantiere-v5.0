"""Iteration 9 tests: report PDF, secondo motore with separate girante toggle,
PUT regression (booleans), preventivo PDF with 2 motor tables.

Auth has been REMOVED — API routes are open (no login needed).
"""
import os
import time
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE_URL}/api"
ANNO = 2026


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def created_ids():
    return []


@pytest.fixture(scope="module", autouse=True)
def cleanup(created_ids):
    yield
    s = requests.Session()
    for cid in created_ids:
        try:
            s.delete(f"{API}/clienti/{cid}", timeout=10)
        except Exception:
            pass


# ---------- Report PDF ----------

class TestReportPagamentiPdf:

    def _fetch(self, client, stato):
        return client.get(f"{API}/report/pagamenti.pdf", params={"anno": ANNO, "stato": stato}, timeout=30)

    def test_pdf_tutti(self, client):
        r = self._fetch(client, "tutti")
        assert r.status_code == 200, r.text[:300]
        assert r.headers.get("content-type", "").startswith("application/pdf"), r.headers
        assert r.content[:5] == b"%PDF-", r.content[:20]
        assert len(r.content) > 1024, f"PDF too small: {len(r.content)} bytes"

    def test_pdf_pagati(self, client):
        r = self._fetch(client, "pagati")
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 1024

    def test_pdf_non_pagati(self, client):
        r = self._fetch(client, "non_pagati")
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 1024

    def test_pdf_stato_invalido(self, client):
        r = self._fetch(client, "xyz")
        assert r.status_code == 400, f"expected 400 got {r.status_code}: {r.text[:200]}"


# ---------- calcola-costi with secondo motore + girante_2 separato ----------

class TestCalcolaCostiSecondoMotore:

    def test_secondo_motore_ricambi_2_no_girante(self, client):
        params = {
            "lunghezza": 8.0,
            "tipo_sosta": "dentro",
            "potenza_motore": 100,
            "numero_candele": 4,
            "numero_termostati": 1,
            "litri_olio_motore": 3.0,
            "girante_attivo": True,
            "secondo_motore": True,
            "potenza_motore_2": 150,
            "girante_2_attivo": False,
            "numero_candele_2": 6,
            "litri_olio_motore_2": 4,
            "numero_termostati_2": 1,
        }
        r = client.get(f"{API}/calcola-costi", params=params, timeout=15)
        assert r.status_code == 200, r.text
        d = r.json()

        assert "costo_manodopera_motore_2" in d
        assert "costo_ricambi_motore_2_totale" in d
        # motor 1 vs motor 2 manodopera potenza differ → labor may or may not differ (depends on tariff tiers).
        # Assert both non-zero.
        assert d["costo_manodopera_motore"] > 0, d
        assert d["costo_manodopera_motore_2"] > 0, d
        assert d["costo_ricambi_totale"] > 0, d
        assert d["costo_ricambi_motore_2_totale"] > 0, d

        # ricambi_2_dettaglio present and girante == 0 when girante_2_attivo=false
        assert "ricambi_2_dettaglio" in d, d
        r2 = d["ricambi_2_dettaglio"]
        girante_val = r2.get("girante", 0)
        assert girante_val == 0, f"girante should be 0 when girante_2_attivo=false, got {girante_val}"
        # Motor 1 girante should be > 0 since girante_attivo=True
        r1 = d.get("ricambi_dettaglio", {})
        assert r1.get("girante", 0) > 0, f"motor1 girante should be > 0, got {r1}"

        # candele_2 = 6 candles vs 4 candles → higher cost for motor 2
        assert r2.get("candele", 0) > r1.get("candele", 0), (r1, r2)
        # olio_motore_2 (4L) > olio_motore (3L)
        assert r2.get("olio_motore", 0) > r1.get("olio_motore", 0), (r1, r2)


# ---------- POST /api/clienti with secondo_motore + girante toggles ----------

class TestClienteSecondoMotore:

    def test_create_persists_motore_2(self, client, created_ids):
        payload = {
            "nome": "TEST_iter9",
            "cognome": "SecondoMotore",
            "tipo_barca": "cabinato",
            "lunghezza": 8.0,
            "tipo_sosta": "dentro",
            "anno": ANNO,
            "potenza_motore": 100,
            "numero_candele": 4,
            "girante_attivo": True,
            "litri_olio_motore": 3.0,
            "secondo_motore": True,
            "potenza_motore_2": 150,
            "girante_2_attivo": False,
            "numero_candele_2": 6,
            "litri_olio_motore_2": 4,
            "numero_termostati_2": 1,
        }
        r = client.post(f"{API}/clienti", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        c = r.json()
        created_ids.append(c["id"])

        assert c["secondo_motore"] is True
        assert c["girante_attivo"] is True
        assert c["girante_2_attivo"] is False
        assert c["costo_manodopera_motore"] > 0
        assert c["costo_ricambi_totale"] > 0
        assert c["costo_manodopera_motore_2"] > 0
        assert c["costo_ricambi_motore_2_totale"] > 0

        # Verify persistence via GET
        r2 = client.get(f"{API}/clienti/{c['id']}", timeout=10)
        assert r2.status_code == 200
        c2 = r2.json()
        assert c2["costo_manodopera_motore_2"] == c["costo_manodopera_motore_2"]
        assert c2["costo_ricambi_motore_2_totale"] == c["costo_ricambi_motore_2_totale"]
        assert c2["girante_2_attivo"] is False


# ---------- PUT regression: booleans preserved ----------

class TestPutClientePreservesBooleans:

    def test_put_only_nome_preserves_girante2_and_pagato(self, client, created_ids):
        # 1) create client with secondo_motore + girante_2 = false + pagato via PATCH
        create_payload = {
            "nome": "TEST_iter9",
            "cognome": "BoolRegression",
            "tipo_barca": "gommone",
            "lunghezza": 6.0,
            "tipo_sosta": "dentro",
            "anno": ANNO,
            "potenza_motore": 80,
            "secondo_motore": True,
            "potenza_motore_2": 80,
            "girante_attivo": True,
            "girante_2_attivo": False,
        }
        r = client.post(f"{API}/clienti", json=create_payload, timeout=15)
        assert r.status_code == 200, r.text
        c = r.json()
        cid = c["id"]
        created_ids.append(cid)
        assert c["girante_2_attivo"] is False
        assert c["pagato"] is False

        # 2) mark paid via PATCH
        r_pay = client.patch(f"{API}/clienti/{cid}/pagato", json={"pagato": True}, timeout=10)
        assert r_pay.status_code == 200, r_pay.text
        assert r_pay.json()["pagato"] is True

        # 3) PUT with only nome (and required fields) — must NOT reset girante_2_attivo or pagato
        put_payload = {
            "nome": "TEST_iter9_renamed",
            "cognome": "BoolRegression",
            "tipo_barca": "gommone",
            "lunghezza": 6.0,
            "tipo_sosta": "dentro",
        }
        r_put = client.put(f"{API}/clienti/{cid}", json=put_payload, timeout=15)
        assert r_put.status_code == 200, r_put.text

        # 4) GET and verify preservation
        r_get = client.get(f"{API}/clienti/{cid}", timeout=10)
        assert r_get.status_code == 200
        c2 = r_get.json()
        assert c2["nome"] == "TEST_iter9_renamed"
        assert c2["pagato"] is True, f"pagato was reset! full: {c2}"
        assert c2["girante_2_attivo"] is False, f"girante_2_attivo was reset! full: {c2}"


# ---------- Preventivo PDF with 2 motors ----------

class TestPreventivoPdfDueMotori:

    def test_preventivo_pdf_secondo_motore(self, client, created_ids):
        payload = {
            "nome": "TEST_iter9",
            "cognome": "PreventivoDueMotori",
            "tipo_barca": "cabinato",
            "lunghezza": 9.0,
            "tipo_sosta": "dentro",
            "anno": ANNO,
            "potenza_motore": 100,
            "secondo_motore": True,
            "potenza_motore_2": 150,
            "girante_attivo": True,
            "girante_2_attivo": False,
            "numero_candele_2": 6,
        }
        r = client.post(f"{API}/clienti", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        cid = r.json()["id"]
        created_ids.append(cid)

        r_pdf = client.get(f"{API}/clienti/{cid}/preventivo.pdf", timeout=30)
        assert r_pdf.status_code == 200, r_pdf.text[:200]
        assert r_pdf.headers.get("content-type", "").startswith("application/pdf")
        assert r_pdf.content[:5] == b"%PDF-"
        assert len(r_pdf.content) > 2048
