"""Iteration 8 tests: codice_fiscale/indirizzo/cellulare, secondo motore, pagamento toggle + report."""
import os
import pytest
import requests
from datetime import date

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE_URL}/api"

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@portomare.it")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "portomare2026")


@pytest.fixture(scope="module")
def s():
    sess = requests.Session()
    sess.headers.update({"Content-Type": "application/json"})
    r = sess.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        # Auth may not be enforced; try unauthenticated
        pass
    return sess


@pytest.fixture(scope="module")
def created_ids(s):
    ids = []
    yield ids
    for cid in ids:
        try:
            s.delete(f"{API}/clienti/{cid}", timeout=10)
        except Exception:
            pass


# ---------- Anagrafica: codice_fiscale / indirizzo / cellulare ----------

def test_create_cliente_with_new_anagrafica_fields(s, created_ids):
    payload = {
        "nome": "TEST_Marco", "cognome": "TEST_Rossi",
        "tipo_barca": "Cabinato", "lunghezza": 8.5,
        "tipo_sosta": "dentro", "anno": 2026,
        "codice_fiscale": "RSSMRC80A01H501U",
        "indirizzo": "Via Roma 12, Genova",
        "cellulare": "+39 333 1234567",
        "telefono": "0101234567",
        "email": "marco@test.it",
    }
    r = s.post(f"{API}/clienti", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    created_ids.append(data["id"])
    assert data["codice_fiscale"] == "RSSMRC80A01H501U"
    assert data["indirizzo"] == "Via Roma 12, Genova"
    assert data["cellulare"] == "+39 333 1234567"

    # GET to verify persistence
    g = s.get(f"{API}/clienti/{data['id']}", timeout=10)
    assert g.status_code == 200
    got = g.json()
    assert got["codice_fiscale"] == "RSSMRC80A01H501U"
    assert got["indirizzo"] == "Via Roma 12, Genova"
    assert got["cellulare"] == "+39 333 1234567"


def test_backwards_compat_no_new_fields(s, created_ids):
    payload = {
        "nome": "TEST_Old", "cognome": "TEST_Compat",
        "tipo_barca": "Gommone", "lunghezza": 4.5, "tipo_sosta": "fuori", "anno": 2026,
    }
    r = s.post(f"{API}/clienti", json=payload, timeout=15)
    assert r.status_code == 200
    data = r.json()
    created_ids.append(data["id"])
    assert data["codice_fiscale"] == ""
    assert data["indirizzo"] == ""
    assert data["cellulare"] == ""
    assert data["pagato"] is False
    assert data["data_pagamento"] is None
    assert data["secondo_motore"] is False


# ---------- Secondo motore ----------

def test_calcola_costi_secondo_motore_doubles_motor_cost(s):
    # Single motor
    r1 = s.get(f"{API}/calcola-costi", params={
        "lunghezza": 8, "tipo_sosta": "dentro",
        "potenza_motore": 100, "litri_olio_motore": 4,
        "numero_candele": 4, "numero_termostati": 1,
        "secondo_motore": "false",
    }, timeout=10)
    assert r1.status_code == 200
    single = r1.json()["costo_manutenzione_motore"]

    # Two motors identical
    r2 = s.get(f"{API}/calcola-costi", params={
        "lunghezza": 8, "tipo_sosta": "dentro",
        "potenza_motore": 100, "litri_olio_motore": 4,
        "numero_candele": 4, "numero_termostati": 1,
        "secondo_motore": "true",
        "potenza_motore_2": 100, "litri_olio_motore_2": 4,
        "numero_candele_2": 4, "numero_termostati_2": 1,
    }, timeout=10)
    assert r2.status_code == 200
    double = r2.json()["costo_manutenzione_motore"]

    # Double should be approximately 2x single (manodopera + ricambi both counted twice)
    assert double > single * 1.8, f"Expected ~2x, got single={single} double={double}"
    assert double <= single * 2.05


def test_create_cliente_with_secondo_motore(s, created_ids):
    payload = {
        "nome": "TEST_TwinMotor", "cognome": "TEST_Bimotore",
        "tipo_barca": "Yacht", "lunghezza": 12,
        "tipo_sosta": "dentro", "anno": 2026,
        "potenza_motore": 150, "litri_olio_motore": 5,
        "numero_candele": 6, "numero_termostati": 2,
        "secondo_motore": True,
        "potenza_motore_2": 150, "litri_olio_motore_2": 5,
        "numero_candele_2": 6, "numero_termostati_2": 2,
    }
    r = s.post(f"{API}/clienti", json=payload, timeout=15)
    assert r.status_code == 200, r.text
    data = r.json()
    created_ids.append(data["id"])
    assert data["secondo_motore"] is True
    assert data["potenza_motore_2"] == 150
    # Motor cost should be significantly higher than a single-motor equivalent
    assert data["costo_manutenzione_motore"] > 500

    # Compare to single-motor identical config
    single_payload = {**payload, "secondo_motore": False, "cognome": "TEST_SoloMotor"}
    r2 = s.post(f"{API}/clienti", json=single_payload, timeout=15)
    assert r2.status_code == 200
    d2 = r2.json()
    created_ids.append(d2["id"])
    assert data["costo_manutenzione_motore"] > d2["costo_manutenzione_motore"] * 1.5


# ---------- PATCH pagato ----------

def test_patch_pagato_sets_true_and_date(s, created_ids):
    payload = {"nome": "TEST_Pay", "cognome": "TEST_ToPay", "tipo_barca": "Gommone",
               "lunghezza": 5, "tipo_sosta": "dentro", "anno": 2026}
    r = s.post(f"{API}/clienti", json=payload, timeout=15)
    assert r.status_code == 200
    cid = r.json()["id"]
    created_ids.append(cid)

    # Toggle pagato=true
    r2 = s.patch(f"{API}/clienti/{cid}/pagato", json={"pagato": True}, timeout=10)
    assert r2.status_code == 200
    j = r2.json()
    assert j["pagato"] is True
    assert j["data_pagamento"] == date.today().isoformat()

    # Verify persisted via GET
    g = s.get(f"{API}/clienti/{cid}", timeout=10)
    assert g.status_code == 200
    got = g.json()
    assert got["pagato"] is True
    assert got["data_pagamento"] == date.today().isoformat()


def test_patch_pagato_false_clears_date(s, created_ids):
    payload = {"nome": "TEST_Unpay", "cognome": "TEST_Rev", "tipo_barca": "Gommone",
               "lunghezza": 5, "tipo_sosta": "dentro", "anno": 2026}
    r = s.post(f"{API}/clienti", json=payload, timeout=15)
    cid = r.json()["id"]
    created_ids.append(cid)

    # First set true
    s.patch(f"{API}/clienti/{cid}/pagato", json={"pagato": True}, timeout=10)
    # Then set false
    r3 = s.patch(f"{API}/clienti/{cid}/pagato", json={"pagato": False}, timeout=10)
    assert r3.status_code == 200
    j = r3.json()
    assert j["pagato"] is False
    assert j["data_pagamento"] is None

    g = s.get(f"{API}/clienti/{cid}", timeout=10)
    got = g.json()
    assert got["pagato"] is False
    assert got["data_pagamento"] is None


def test_patch_pagato_404(s):
    r = s.patch(f"{API}/clienti/nonexistent-id-xyz/pagato", json={"pagato": True}, timeout=10)
    assert r.status_code == 404


# ---------- PUT preserves pagato ----------

def test_put_cliente_preserves_pagato(s, created_ids):
    payload = {"nome": "TEST_Preserve", "cognome": "TEST_Pay", "tipo_barca": "Gommone",
               "lunghezza": 5, "tipo_sosta": "dentro", "anno": 2026}
    r = s.post(f"{API}/clienti", json=payload, timeout=15)
    cid = r.json()["id"]
    created_ids.append(cid)

    # Mark paid
    s.patch(f"{API}/clienti/{cid}/pagato", json={"pagato": True}, timeout=10)

    # PUT with different data (no pagato in payload)
    put_payload = {**payload, "lunghezza": 6.5}
    r2 = s.put(f"{API}/clienti/{cid}", json=put_payload, timeout=15)
    assert r2.status_code == 200
    updated = r2.json()

    # NOTE: Reviewing PUT logic: ClienteCreate has pagato field default=False
    # so PUT may overwrite pagato to False unless explicitly preserved.
    # This test asserts the reviewer's requirement.
    g = s.get(f"{API}/clienti/{cid}", timeout=10)
    got = g.json()
    # Assert pagato preserved
    assert got["pagato"] is True, f"pagato was NOT preserved after PUT: got={got}"
    assert got["data_pagamento"] == date.today().isoformat()


# ---------- Report pagamenti ----------

def test_report_pagamenti_returns_shape_and_sums(s, created_ids):
    # Create two clients in 2026 with known totals; toggle one paid
    p1 = {"nome": "TEST_Rpt1", "cognome": "TEST_Aaa", "tipo_barca": "X", "lunghezza": 5,
          "tipo_sosta": "dentro", "anno": 2026}
    p2 = {"nome": "TEST_Rpt2", "cognome": "TEST_Bbb", "tipo_barca": "X", "lunghezza": 5,
          "tipo_sosta": "dentro", "anno": 2026}
    id1 = s.post(f"{API}/clienti", json=p1, timeout=15).json()["id"]
    id2 = s.post(f"{API}/clienti", json=p2, timeout=15).json()["id"]
    created_ids.extend([id1, id2])
    s.patch(f"{API}/clienti/{id1}/pagato", json={"pagato": True}, timeout=10)

    r = s.get(f"{API}/report/pagamenti", params={"anno": 2026}, timeout=15)
    assert r.status_code == 200
    data = r.json()
    assert "clienti" in data
    assert "totale_pagato" in data
    assert "totale_da_pagare" in data
    assert "numero_pagati" in data
    assert "numero_non_pagati" in data
    assert data["numero_pagati"] >= 1
    assert data["numero_non_pagati"] >= 1

    # Cross-check sums
    tot_paid = sum(c["totale"] for c in data["clienti"] if c["pagato"])
    tot_unpaid = sum(c["totale"] for c in data["clienti"] if not c["pagato"])
    assert abs(tot_paid - data["totale_pagato"]) < 0.05
    assert abs(tot_unpaid - data["totale_da_pagare"]) < 0.05

    # Ensure our marked client appears as paid
    entry = next((c for c in data["clienti"] if c["id"] == id1), None)
    assert entry is not None
    assert entry["pagato"] is True
    assert entry["data_pagamento"] == date.today().isoformat()

    # Ensure required cliente fields
    for c in data["clienti"]:
        for k in ("id", "nome", "cognome", "totale", "pagato"):
            assert k in c


def test_report_pagamenti_year_isolation(s):
    r26 = s.get(f"{API}/report/pagamenti", params={"anno": 2026}, timeout=15)
    r27 = s.get(f"{API}/report/pagamenti", params={"anno": 2027}, timeout=15)
    assert r26.status_code == 200
    assert r27.status_code == 200
    ids_2026 = {c["id"] for c in r26.json()["clienti"]}
    ids_2027 = {c["id"] for c in r27.json()["clienti"]}
    # No overlap (each cliente belongs to exactly one anno)
    assert ids_2026.isdisjoint(ids_2027)
