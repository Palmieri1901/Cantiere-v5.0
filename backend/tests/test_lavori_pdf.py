"""Backend tests for Portomare - Iteration 2
Focus: NEW features (lavori CRUD, preventivo PDF) + regression on existing endpoints.
"""
import os
import io
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fallback to internal for CI
    BASE_URL = "http://localhost:8001"
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def test_cliente(session):
    """Create a dedicated test client for the lavori/PDF tests, delete at teardown."""
    payload = {
        "nome": "TEST_Mario",
        "cognome": "TEST_Verdi",
        "tipo_barca": "Cabinato test",
        "lunghezza": 9.0,
        "tipo_sosta": "dentro",
        "telefono": "+39 000 0000000",
        "email": "test_mario@example.com",
    }
    r = session.post(f"{API}/clienti", json=payload)
    assert r.status_code == 200, r.text
    c = r.json()
    yield c
    # cleanup - remove lavori then cliente
    try:
        lav = session.get(f"{API}/clienti/{c['id']}/lavori").json()
        for l in lav:
            session.delete(f"{API}/lavori/{l['id']}")
    except Exception:
        pass
    session.delete(f"{API}/clienti/{c['id']}")


# ============= REGRESSION on existing endpoints =============

class TestRegression:
    def test_root(self, session):
        r = session.get(f"{API}/")
        assert r.status_code == 200

    def test_stats(self, session):
        r = session.get(f"{API}/stats")
        assert r.status_code == 200
        d = r.json()
        assert d["posti_totali"] == 200
        assert "posti_occupati" in d
        assert "entrate_totali" in d
        assert isinstance(d.get("scadenze_prossime"), list)

    def test_tariffe_get(self, session):
        r = session.get(f"{API}/tariffe")
        assert r.status_code == 200
        assert "sosta_dentro_per_metro" in r.json()

    def test_clienti_list(self, session):
        r = session.get(f"{API}/clienti")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_posti_barca(self, session):
        r = session.get(f"{API}/posti-barca")
        assert r.status_code == 200
        assert len(r.json()) == 200

    def test_export_csv(self, session):
        r = session.get(f"{API}/export/clienti.csv")
        assert r.status_code == 200
        assert "text/csv" in r.headers.get("content-type", "")

    def test_export_xlsx(self, session):
        r = session.get(f"{API}/export/clienti.xlsx")
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "")


# ============= LAVORI CRUD =============

class TestLavori:
    def test_create_lavoro(self, session, test_cliente):
        payload = {
            "cliente_id": test_cliente["id"],
            "data": "2026-01-10",
            "tipo": "Antivegetativa",
            "descrizione": "TEST Applicazione antivegetativa autolucidante",
            "costo": 540.0,
            "materiali": "3L vernice, mastici",
            "stato": "completato",
        }
        r = session.post(f"{API}/lavori", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert "id" in d and d["id"]
        assert "created_at" in d
        assert d["cliente_id"] == test_cliente["id"]
        assert d["tipo"] == "Antivegetativa"
        assert d["costo"] == 540.0
        assert d["stato"] == "completato"
        # store for later
        pytest.LAVORO_ID = d["id"]

    def test_create_second_lavoro(self, session, test_cliente):
        payload = {
            "cliente_id": test_cliente["id"],
            "data": "2025-11-05",
            "tipo": "Manutenzione motore",
            "descrizione": "TEST cambio olio",
            "costo": 250.0,
            "materiali": "filtro olio, olio 5W40",
            "stato": "completato",
        }
        r = session.post(f"{API}/lavori", json=payload)
        assert r.status_code == 200, r.text

    def test_list_lavori_sorted_desc(self, session, test_cliente):
        r = session.get(f"{API}/clienti/{test_cliente['id']}/lavori")
        assert r.status_code == 200
        rows = r.json()
        assert len(rows) >= 2
        dates = [row["data"] for row in rows]
        assert dates == sorted(dates, reverse=True), f"Not sorted desc: {dates}"

    def test_create_invalid_stato(self, session, test_cliente):
        payload = {
            "cliente_id": test_cliente["id"],
            "data": "2026-01-10",
            "tipo": "Riparazione",
            "stato": "bogus_state",
        }
        r = session.post(f"{API}/lavori", json=payload)
        assert r.status_code == 400

    def test_create_nonexistent_cliente(self, session):
        payload = {
            "cliente_id": "does-not-exist-xyz",
            "data": "2026-01-10",
            "tipo": "Riparazione",
            "stato": "completato",
        }
        r = session.post(f"{API}/lavori", json=payload)
        assert r.status_code == 404

    def test_update_lavoro(self, session, test_cliente):
        lid = pytest.LAVORO_ID
        payload = {
            "cliente_id": test_cliente["id"],
            "data": "2026-01-15",
            "tipo": "Antivegetativa",
            "descrizione": "TEST descrizione aggiornata",
            "costo": 600.0,
            "materiali": "3L vernice, mastici",
            "stato": "in_corso",
        }
        r = session.put(f"{API}/lavori/{lid}", json=payload)
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["costo"] == 600.0
        assert d["stato"] == "in_corso"
        # Verify persisted
        r2 = session.get(f"{API}/clienti/{test_cliente['id']}/lavori")
        rows = r2.json()
        found = [x for x in rows if x["id"] == lid][0]
        assert found["costo"] == 600.0
        assert found["stato"] == "in_corso"

    def test_delete_lavoro(self, session, test_cliente):
        lid = pytest.LAVORO_ID
        r = session.delete(f"{API}/lavori/{lid}")
        assert r.status_code == 200
        # verify gone
        r2 = session.get(f"{API}/clienti/{test_cliente['id']}/lavori")
        ids = [x["id"] for x in r2.json()]
        assert lid not in ids

    def test_delete_nonexistent_lavoro(self, session):
        r = session.delete(f"{API}/lavori/nope-nope-nope")
        assert r.status_code == 404


# ============= PDF PREVENTIVO =============

class TestPreventivoPdf:
    def test_pdf_returns_valid(self, session, test_cliente):
        r = session.get(f"{API}/clienti/{test_cliente['id']}/preventivo.pdf")
        assert r.status_code == 200, r.text
        assert r.headers.get("content-type", "").startswith("application/pdf"), r.headers
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower()
        assert ".pdf" in cd.lower()
        content = r.content
        assert len(content) > 1500, f"PDF too small: {len(content)} bytes"
        assert content[:4] == b"%PDF", "Not a valid PDF header"

    def test_pdf_404_for_missing_cliente(self, session):
        r = session.get(f"{API}/clienti/nope-not-found/preventivo.pdf")
        assert r.status_code == 404
