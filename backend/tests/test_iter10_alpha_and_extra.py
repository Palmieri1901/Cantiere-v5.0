"""iter10 tests:
- Ordering clienti alfabetico per cognome case-insensitive
- lavorazioni_extra: creazione (normalizzazione), max 20 (400), preservazione in PUT
- PDF preventivo con LAVORAZIONI EXTRA
- Report pagamenti e report incassi includono lavorazioni_extra
- Stats: entrate_totali include lavorazioni_extra
"""
import os
import io
import pytest
import requests

def _load_frontend_env():
    envf = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env")
    envf = os.path.abspath(envf)
    if os.path.exists(envf):
        with open(envf) as f:
            for line in f:
                line = line.strip()
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _load_frontend_env() or "").rstrip("/")
if not BASE_URL:
    raise RuntimeError("REACT_APP_BACKEND_URL not set")
API = f"{BASE_URL}/api"

ANNO = 2026
PREFIX = "TEST_iter10_"


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def created_ids(client):
    ids = []
    yield ids
    # Cleanup
    for cid in ids:
        try:
            client.delete(f"{API}/clienti/{cid}", timeout=10)
        except Exception:
            pass


def _new_cliente(cognome, nome="Mario", extra=None, anno=ANNO):
    body = {
        "nome": nome,
        "cognome": cognome,
        "tipo_barca": "TestBoat",
        "lunghezza": 6.0,
        "tipo_sosta": "dentro",
        "anno": anno,
        "antivegetativa_attiva": False,
        "lavaggio_inizio_attivo": False,
        "lavaggio_fine_attivo": False,
    }
    if extra is not None:
        body["lavorazioni_extra"] = extra
    return body


# ---------- Ordering ----------

class TestOrdering:
    def test_alfabetico_cognome_case_insensitive(self, client, created_ids):
        # Create clients in a non-alphabetical order
        cognomi = ["zulu", "Alpha", "MIKE", "charlie"]
        expected = ["Alpha", "charlie", "MIKE", "zulu"]
        for c in cognomi:
            r = client.post(f"{API}/clienti", json=_new_cliente(PREFIX + c), timeout=15)
            assert r.status_code == 200, r.text
            created_ids.append(r.json()["id"])

        # GET without anno
        r = client.get(f"{API}/clienti", timeout=15)
        assert r.status_code == 200
        got_all = [x["cognome"] for x in r.json() if x["cognome"].startswith(PREFIX)]
        assert got_all == [PREFIX + c for c in expected], f"Order mismatch (no anno): {got_all}"

        # GET with anno=2026
        r = client.get(f"{API}/clienti", params={"anno": ANNO}, timeout=15)
        assert r.status_code == 200
        got_anno = [x["cognome"] for x in r.json() if x["cognome"].startswith(PREFIX)]
        assert got_anno == [PREFIX + c for c in expected], f"Order mismatch (anno): {got_anno}"


# ---------- Lavorazioni Extra Create ----------

class TestLavorazioniExtraCreate:
    def test_create_with_lavorazioni_extra(self, client, created_ids):
        extra = [
            {"descrizione": "Rip. elica", "prezzo": 250.5},
            {"descrizione": "Parabrezza", "prezzo": 480},
        ]
        r = client.post(f"{API}/clienti", json=_new_cliente(PREFIX + "extra1", extra=extra), timeout=15)
        assert r.status_code == 200, r.text
        cli = r.json()
        created_ids.append(cli["id"])

        assert "lavorazioni_extra" in cli
        le = cli["lavorazioni_extra"]
        assert len(le) == 2
        assert le[0]["descrizione"] == "Rip. elica"
        assert isinstance(le[0]["prezzo"], float)
        assert le[0]["prezzo"] == 250.5
        assert le[1]["descrizione"] == "Parabrezza"
        assert le[1]["prezzo"] == 480.0

        # Verify persistence with GET
        rg = client.get(f"{API}/clienti/{cli['id']}", timeout=15)
        assert rg.status_code == 200
        assert rg.json()["lavorazioni_extra"] == le

    def test_empty_row_filtered(self, client, created_ids):
        extra = [
            {"descrizione": "Voce valida", "prezzo": 100},
            {"descrizione": "", "prezzo": 0},          # deve essere filtrata
            {"descrizione": "  ", "prezzo": 0.0},      # deve essere filtrata (desc vuota dopo strip)
            {"descrizione": "Solo prezzo", "prezzo": 50},
            {"descrizione": "Solo desc", "prezzo": 0},
        ]
        r = client.post(f"{API}/clienti", json=_new_cliente(PREFIX + "filter1", extra=extra), timeout=15)
        assert r.status_code == 200, r.text
        cli = r.json()
        created_ids.append(cli["id"])
        le = cli["lavorazioni_extra"]
        # only descrizione empty AND prezzo 0 filtered → 3 rimangono
        descrizioni = [i["descrizione"] for i in le]
        assert "" not in descrizioni
        assert "Voce valida" in descrizioni
        assert "Solo prezzo" in descrizioni
        assert "Solo desc" in descrizioni
        assert len(le) == 3

    def test_max_21_returns_400(self, client, created_ids):
        extra = [{"descrizione": f"Voce {i}", "prezzo": 10} for i in range(21)]
        r = client.post(f"{API}/clienti", json=_new_cliente(PREFIX + "max21", extra=extra), timeout=15)
        assert r.status_code == 400, r.text
        assert "20" in r.text.lower() or "massimo" in r.text.lower()


# ---------- PUT preservation ----------

class TestPutPreservesLavorazioni:
    def test_put_partial_update_preserves_lavorazioni(self, client, created_ids):
        extra = [
            {"descrizione": "Rip. elica", "prezzo": 250.5},
            {"descrizione": "Parabrezza", "prezzo": 480},
        ]
        r = client.post(f"{API}/clienti", json=_new_cliente(PREFIX + "putpres", extra=extra), timeout=15)
        assert r.status_code == 200
        cli = r.json()
        created_ids.append(cli["id"])
        original_extra = cli["lavorazioni_extra"]

        # PUT without lavorazioni_extra, only changing nome
        update_body = _new_cliente(PREFIX + "putpres", nome="Luigi")
        # NOTE: intentionally NOT including lavorazioni_extra
        assert "lavorazioni_extra" not in update_body
        r2 = client.put(f"{API}/clienti/{cli['id']}", json=update_body, timeout=15)
        assert r2.status_code == 200, r2.text
        updated = r2.json()
        assert updated["nome"] == "Luigi"
        assert updated["lavorazioni_extra"] == original_extra, (
            f"lavorazioni_extra should be preserved but got {updated['lavorazioni_extra']}"
        )


# ---------- PDF Preventivo ----------

class TestPdfPreventivo:
    def test_pdf_contains_lavorazioni_extra(self, client, created_ids):
        extra = [
            {"descrizione": "Rip. elica", "prezzo": 250.5},
            {"descrizione": "Parabrezza", "prezzo": 480},
        ]
        r = client.post(f"{API}/clienti", json=_new_cliente(PREFIX + "pdf1", extra=extra), timeout=15)
        assert r.status_code == 200
        cid = r.json()["id"]
        created_ids.append(cid)

        rp = client.get(f"{API}/clienti/{cid}/preventivo.pdf", timeout=30)
        assert rp.status_code == 200
        content = rp.content
        assert content[:5] == b"%PDF-", "Not a valid PDF header"
        assert len(content) > 5 * 1024, f"PDF too small: {len(content)} bytes"

        # Try text extraction with pypdf if available
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            full_text = "\n".join(p.extract_text() or "" for p in reader.pages)
            # Section title should be present
            assert "LAVORAZIONI EXTRA" in full_text.upper(), "LAVORAZIONI EXTRA section missing in PDF text"
            # At least one description should appear
            assert "Rip" in full_text or "elica" in full_text.lower(), "Descrizione extra mancante"
        except ImportError:
            # Fallback: check the binary for the section keyword (may fail if compressed)
            # At minimum PDF must be valid; skip content assertion
            pass


# ---------- Report Pagamenti (JSON) ----------

class TestReportPagamenti:
    def test_totale_includes_lavorazioni_extra(self, client, created_ids):
        extra = [{"descrizione": "Test extra pag", "prezzo": 333.33}]
        r = client.post(f"{API}/clienti", json=_new_cliente(PREFIX + "pag1", extra=extra), timeout=15)
        assert r.status_code == 200
        cli = r.json()
        cid = cli["id"]
        created_ids.append(cid)

        # sosta dentro 6.0 * 180 = 1080 (default tariff), no antiveg, no lavaggi
        # extra = 333.33
        rp = client.get(f"{API}/report/pagamenti", params={"anno": ANNO}, timeout=15)
        assert rp.status_code == 200
        data = rp.json()
        our = next((c for c in data["clienti"] if c["id"] == cid), None)
        assert our is not None, "Cliente not found in report"
        # totale deve includere lavorazioni_extra (333.33)
        # Somma altri costi dalla risposta cliente
        base_sum = sum(
            float(cli.get(k) or 0) for k in (
                "costo_sosta", "costo_movimentazione", "costo_taccaggio",
                "costo_copertura", "costo_alaggio", "costo_varo",
                "costo_antivegetativa", "costo_scafo_sporco",
                "costo_lavaggio_inizio", "costo_lavaggio_fine",
                "costo_manutenzione_motore"
            )
        )
        expected = round(base_sum + 333.33, 2)
        assert our["totale"] == expected, f"Totale wrong: got {our['totale']} expected {expected}"


# ---------- Report Pagamenti PDF ----------

class TestReportPagamentiPdf:
    def test_pdf_valid(self, client):
        r = client.get(f"{API}/report/pagamenti.pdf",
                       params={"anno": ANNO, "stato": "tutti"}, timeout=30)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"
        assert len(r.content) > 3 * 1024


# ---------- Report Incassi ----------

class TestReportIncassi:
    def test_categoria_lavorazioni_extra_present(self, client, created_ids):
        # Ensure at least our test extra exists
        extra = [{"descrizione": "Incassi test", "prezzo": 123.45}]
        r = client.post(f"{API}/clienti", json=_new_cliente(PREFIX + "inc1", extra=extra), timeout=15)
        assert r.status_code == 200
        created_ids.append(r.json()["id"])

        ri = client.get(f"{API}/report/incassi", params={"anno": ANNO}, timeout=15)
        assert ri.status_code == 200
        d = ri.json()
        assert "categorie" in d
        assert "lavorazioni_extra" in d["categorie"], "Categoria 'lavorazioni_extra' mancante"
        assert d["categorie"]["lavorazioni_extra"] >= 123.45
        # Totale generale include extra
        somma_cat = sum(v for v in d["categorie"].values())
        assert abs(d["totale"] - round(somma_cat, 2)) < 0.05, (
            f"Totale ({d['totale']}) diverso dalla somma categorie ({somma_cat})"
        )


# ---------- Stats ----------

class TestStats:
    def test_entrate_totali_include_extra(self, client, created_ids):
        # Get stats prima
        r1 = client.get(f"{API}/stats", params={"anno": ANNO}, timeout=15)
        assert r1.status_code == 200
        before = r1.json()["entrate_totali"]

        # Crea cliente con solo lavorazioni_extra (annullo altri costi con override)
        body = _new_cliente(PREFIX + "stats1", extra=[{"descrizione": "Solo extra", "prezzo": 999.99}])
        r = client.post(f"{API}/clienti", json=body, timeout=15)
        assert r.status_code == 200
        cli = r.json()
        created_ids.append(cli["id"])
        client_total = sum(
            float(cli.get(k) or 0) for k in (
                "costo_sosta", "costo_movimentazione", "costo_taccaggio",
                "costo_copertura", "costo_alaggio", "costo_varo",
                "costo_antivegetativa", "costo_scafo_sporco",
                "costo_lavaggio_inizio", "costo_lavaggio_fine",
                "costo_manutenzione_motore"
            )
        ) + 999.99

        r2 = client.get(f"{API}/stats", params={"anno": ANNO}, timeout=15)
        after = r2.json()["entrate_totali"]
        delta = round(after - before, 2)
        assert abs(delta - round(client_total, 2)) < 0.05, (
            f"Delta entrate_totali ({delta}) != atteso ({client_total})"
        )
