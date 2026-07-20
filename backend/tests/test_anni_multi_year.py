"""Iteration 7: multi-year (anno) isolation tests.
Preconditions expected: DB has 6 clienti anno=2026 and 6 clienti anno=2027 (migration + previous duplication).
Uses the shared authenticated `session` fixture from conftest.py.
"""
import os
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE_URL}/api"


# --- /api/anni : lista anni ---
class TestAnniList:
    def test_get_anni_shape(self, session):
        r = session.get(f"{API}/anni")
        assert r.status_code == 200
        data = r.json()
        assert "anno_corrente" in data and isinstance(data["anno_corrente"], int)
        assert "anni" in data and isinstance(data["anni"], list)
        # anno_corrente must be 2026 (current year)
        assert data["anno_corrente"] == 2026

    def test_get_anni_contains_2026_and_2027(self, session):
        r = session.get(f"{API}/anni")
        data = r.json()
        by_year = {a["anno"]: a["clienti"] for a in data["anni"]}
        assert 2026 in by_year, f"2026 mancante in {list(by_year.keys())}"
        assert 2027 in by_year, f"2027 mancante in {list(by_year.keys())}"
        assert by_year[2026] == 6, f"2026 clienti = {by_year[2026]}, atteso 6"
        assert by_year[2027] == 6, f"2027 clienti = {by_year[2027]}, atteso 6"


# --- /api/clienti with anno filter ---
class TestClientiPerAnno:
    def test_clienti_2026(self, session):
        r = session.get(f"{API}/clienti?anno=2026")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 6
        assert all(c["anno"] == 2026 for c in data)

    def test_clienti_2027(self, session):
        r = session.get(f"{API}/clienti?anno=2027")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 6
        assert all(c["anno"] == 2027 for c in data)

    def test_clienti_no_filter_returns_all(self, session):
        r = session.get(f"{API}/clienti")
        assert r.status_code == 200
        data = r.json()
        # At least 12 (2026 + 2027). Some tests may have added more but never < 12.
        assert len(data) >= 12

    def test_stats_2026(self, session):
        r = session.get(f"{API}/stats?anno=2026")
        assert r.status_code == 200
        assert r.json()["totale_clienti"] == 6

    def test_stats_2027(self, session):
        r = session.get(f"{API}/stats?anno=2027")
        assert r.status_code == 200
        assert r.json()["totale_clienti"] == 6

    def test_posti_barca_2026(self, session):
        r = session.get(f"{API}/posti-barca?anno=2026")
        assert r.status_code == 200
        posti = r.json()
        assert len(posti) == 200  # TOTAL_POSTI slots regardless of anno
        occupati = [p for p in posti if p["occupato"]]
        # 2026 has 6 clients but only some have posto_barca assigned.
        # Key requirement: all occupied posti must reference clients that belong to 2026.
        clienti_2026_ids = {c["id"] for c in session.get(f"{API}/clienti?anno=2026").json()}
        for p in occupati:
            assert p["cliente_id"] in clienti_2026_ids, f"posto {p['numero']} occupato da cliente non-2026"

    def test_posti_barca_2027_independent(self, session):
        r = session.get(f"{API}/posti-barca?anno=2027")
        assert r.status_code == 200
        posti = r.json()
        occupati = [p for p in posti if p["occupato"]]
        clienti_2027_ids = {c["id"] for c in session.get(f"{API}/clienti?anno=2027").json()}
        for p in occupati:
            assert p["cliente_id"] in clienti_2027_ids, f"posto {p['numero']} occupato da cliente non-2027"
        # Also, 2026 and 2027 occupied posti clients must be disjoint (different IDs)
        r2026 = session.get(f"{API}/posti-barca?anno=2026").json()
        ids_2026 = {p["cliente_id"] for p in r2026 if p["occupato"]}
        ids_2027 = {p["cliente_id"] for p in occupati}
        assert ids_2026.isdisjoint(ids_2027), "clienti condivisi tra 2026 e 2027"

    def test_report_incassi_2026(self, session):
        r = session.get(f"{API}/report/incassi?anno=2026")
        assert r.status_code == 200
        data = r.json()
        assert data["totale_clienti"] == 6
        assert data["totale"] >= 0

    def test_report_incassi_year_isolation(self, session):
        """Report for one year must not include clients from other years."""
        r_2026 = session.get(f"{API}/report/incassi?anno=2026").json()
        r_2027 = session.get(f"{API}/report/incassi?anno=2027").json()
        r_all = session.get(f"{API}/report/incassi").json()
        # Total (no filter) should be >= sum of individual years (since >=12 clients)
        assert r_all["totale_clienti"] >= r_2026["totale_clienti"] + r_2027["totale_clienti"]


# --- POST /api/anni/apri ---
class TestApriAnno:
    def test_apri_anno_vuoto_2028(self, session):
        # Cleanup first in case a previous run left 2028
        session.delete(f"{API}/anni/2028")
        r = session.post(f"{API}/anni/apri", json={"anno": 2028})
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["anno"] == 2028
        assert data["duplicati"] == 0
        # verify no clients created
        r2 = session.get(f"{API}/clienti?anno=2028")
        assert r2.status_code == 200
        assert len(r2.json()) == 0

    def test_apri_anno_duplica_2026_to_2029(self, session):
        # Cleanup any existing 2029
        session.delete(f"{API}/anni/2029")
        r = session.post(f"{API}/anni/apri", json={"anno": 2029, "duplica_da": 2026})
        assert r.status_code == 200
        data = r.json()
        assert data["duplicati"] == 6
        # Verify GET
        r2 = session.get(f"{API}/clienti?anno=2029").json()
        assert len(r2) == 6
        assert all(c["anno"] == 2029 for c in r2)
        # IDs must differ from the 2026 originals
        ids_2026 = {c["id"] for c in session.get(f"{API}/clienti?anno=2026").json()}
        ids_2029 = {c["id"] for c in r2}
        assert ids_2026.isdisjoint(ids_2029), "IDs 2029 devono essere diversi da 2026"

    def test_apri_anno_idempotent(self, session):
        # Second call: no duplication, gia_esistenti = 6
        r = session.post(f"{API}/anni/apri", json={"anno": 2029, "duplica_da": 2026})
        assert r.status_code == 200
        data = r.json()
        assert data["duplicati"] == 0
        assert data["gia_esistenti"] == 6

    def test_apri_anno_invalid_year(self, session):
        r = session.post(f"{API}/anni/apri", json={"anno": 1999})
        assert r.status_code == 400
        r2 = session.post(f"{API}/anni/apri", json={"anno": 2101})
        assert r2.status_code == 400


# --- DELETE /api/anni/{anno} ---
class TestDeleteAnno:
    def test_delete_2028_empty(self, session):
        # 2028 should be empty (from TestApriAnno.test_apri_anno_vuoto_2028)
        r = session.delete(f"{API}/anni/2028")
        assert r.status_code == 200
        data = r.json()
        assert data["clienti_eliminati"] == 0

    def test_delete_2029_with_duplicated_clients(self, session):
        # 2029 should still have 6 clients
        r = session.delete(f"{API}/anni/2029")
        assert r.status_code == 200
        data = r.json()
        assert data["clienti_eliminati"] == 6
        # verify no more 2029
        assert len(session.get(f"{API}/clienti?anno=2029").json()) == 0

    def test_delete_does_not_affect_2026(self, session):
        # 2026 must still have 6 clients after 2028/2029 deletions
        r = session.get(f"{API}/clienti?anno=2026")
        assert len(r.json()) == 6


# --- Uniqueness posto barca is per-year ---
class TestPostoBarcaPerAnno:
    def test_same_posto_conflicts_in_same_year(self, session):
        # 2026 has clients on posti 1..6 presumably. Find first occupied posto in 2026
        clients_2026 = session.get(f"{API}/clienti?anno=2026").json()
        occupied = [c["posto_barca"] for c in clients_2026 if c.get("posto_barca")]
        assert occupied, "No occupied posto in 2026"
        conflicting_posto = occupied[0]

        payload = {
            "nome": "TEST_Anno", "cognome": "TEST_Duplicato",
            "tipo_barca": "Barca test", "lunghezza": 8.0,
            "tipo_sosta": "dentro", "anno": 2026,
            "posto_barca": conflicting_posto,
        }
        r = session.post(f"{API}/clienti", json=payload)
        assert r.status_code == 400, f"expected 400, got {r.status_code} — {r.text}"

    def test_same_posto_ok_in_different_year(self, session):
        clients_2026 = session.get(f"{API}/clienti?anno=2026").json()
        occupied = [c["posto_barca"] for c in clients_2026 if c.get("posto_barca")]
        posto = occupied[0]

        # Ensure 2028 is empty
        session.delete(f"{API}/anni/2028")
        payload = {
            "nome": "TEST_2028", "cognome": "TEST_SamePosto",
            "tipo_barca": "Barca test", "lunghezza": 8.0,
            "tipo_sosta": "dentro", "anno": 2028,
            "posto_barca": posto,
        }
        r = session.post(f"{API}/clienti", json=payload)
        assert r.status_code == 200, f"unexpected {r.status_code}: {r.text}"
        created = r.json()
        assert created["anno"] == 2028
        assert created["posto_barca"] == posto
        # cleanup
        session.delete(f"{API}/anni/2028")


# --- PUT preserves anno ---
class TestPutPreservesAnno:
    def test_put_without_anno_keeps_existing(self, session):
        # Grab a 2027 client, PUT with no anno field → should stay 2027
        c = session.get(f"{API}/clienti?anno=2027").json()[0]
        cid = c["id"]
        payload = {
            "nome": c["nome"], "cognome": c["cognome"],
            "tipo_barca": c["tipo_barca"], "lunghezza": c["lunghezza"],
            "tipo_sosta": c["tipo_sosta"],
            # NOTE: anno intentionally omitted
        }
        r = session.put(f"{API}/clienti/{cid}", json=payload)
        assert r.status_code == 200, r.text
        assert r.json()["anno"] == 2027, f"anno cambiato a {r.json()['anno']}"
        # persisted?
        r2 = session.get(f"{API}/clienti/{cid}").json()
        assert r2["anno"] == 2027
