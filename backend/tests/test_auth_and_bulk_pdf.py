"""
Iteration 6 tests: JWT email/password auth + /api/export/preventivi.zip bulk PDF export.
Auth uses httpOnly cookie or Bearer token. Admin auto-seeded on startup.
"""
import os
import io
import zipfile
import time
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', 'https://marina-workspace.preview.emergentagent.com').rstrip('/')
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@portomare.it"
ADMIN_PASSWORD = "portomare2026"


# ---------- Fixtures ----------

@pytest.fixture(scope="module")
def anon_session():
    return requests.Session()


@pytest.fixture(scope="module")
def auth_session():
    """Session logged in as admin via cookie."""
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200
    return r.json()["token"]


# ---------- Unauthenticated access is blocked ----------

class TestUnauthenticated:
    def test_get_clienti_without_auth_returns_401(self, anon_session):
        r = anon_session.get(f"{API}/clienti", timeout=10)
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_get_stats_without_auth_returns_401(self, anon_session):
        r = anon_session.get(f"{API}/stats", timeout=10)
        assert r.status_code == 401

    def test_get_tariffe_without_auth_returns_401(self, anon_session):
        r = anon_session.get(f"{API}/tariffe", timeout=10)
        assert r.status_code == 401

    def test_get_cantiere_without_auth_returns_401(self, anon_session):
        r = anon_session.get(f"{API}/cantiere", timeout=10)
        assert r.status_code == 401

    def test_get_posti_barca_without_auth_returns_401(self, anon_session):
        r = anon_session.get(f"{API}/posti-barca", timeout=10)
        assert r.status_code == 401

    def test_get_export_zip_without_auth_returns_401(self, anon_session):
        r = anon_session.get(f"{API}/export/preventivi.zip", timeout=15)
        assert r.status_code == 401

    def test_auth_me_without_auth_returns_401(self, anon_session):
        r = anon_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 401


# ---------- Login ----------

class TestLogin:
    def test_login_success_returns_user_and_sets_cookie(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        # Response shape
        assert data.get("email") == ADMIN_EMAIL
        assert data.get("nome") == "Admin"
        assert data.get("role") == "admin"
        assert isinstance(data.get("id"), str) and len(data["id"]) > 0
        assert isinstance(data.get("token"), str) and len(data["token"]) > 20
        # No password_hash leaked
        assert "password_hash" not in data
        # Cookie set
        assert "access_token" in s.cookies, f"access_token cookie not set. Cookies: {dict(s.cookies)}"
        # Set-Cookie header present
        set_cookie = r.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie.lower() or "access_token=" in set_cookie

    def test_login_wrong_password_returns_401(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": "wrongpass"}, timeout=10)
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_login_nonexistent_email_returns_401(self):
        r = requests.post(f"{API}/auth/login", json={"email": "nobody-xyz@nope.test", "password": "x"}, timeout=10)
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_login_case_insensitive_email(self):
        r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL.upper(), "password": ADMIN_PASSWORD}, timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL


# ---------- /auth/me and Authorization header ----------

class TestAuthMe:
    def test_me_with_cookie_returns_user_no_hash(self, auth_session):
        r = auth_session.get(f"{API}/auth/me", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == ADMIN_EMAIL
        assert data["nome"] == "Admin"
        assert data["role"] == "admin"
        assert "password_hash" not in data
        assert isinstance(data["id"], str)

    def test_clienti_with_cookie_returns_200(self, auth_session):
        r = auth_session.get(f"{API}/clienti", timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_clienti_with_bearer_token_returns_200(self, admin_token):
        r = requests.get(f"{API}/clienti", headers={"Authorization": f"Bearer {admin_token}"}, timeout=10)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_me_with_bearer_token_returns_200(self, admin_token):
        r = requests.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {admin_token}"}, timeout=10)
        assert r.status_code == 200
        assert r.json()["email"] == ADMIN_EMAIL

    def test_invalid_bearer_token_returns_401(self):
        r = requests.get(f"{API}/clienti", headers={"Authorization": "Bearer notavalidtoken"}, timeout=10)
        assert r.status_code == 401


# ---------- Logout ----------

class TestLogout:
    def test_logout_clears_cookie_and_subsequent_request_401(self):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=10)
        assert r.status_code == 200
        assert "access_token" in s.cookies

        # Confirm authed
        r2 = s.get(f"{API}/clienti", timeout=10)
        assert r2.status_code == 200

        # Logout
        r3 = s.post(f"{API}/auth/logout", timeout=10)
        assert r3.status_code == 200
        # Cookie removed (or expired/empty)
        val = s.cookies.get("access_token", "")
        assert not val, f"Cookie should be cleared, got: {val!r}"

        # Subsequent request unauthorized
        r4 = s.get(f"{API}/clienti", timeout=10)
        assert r4.status_code == 401


# ---------- Register ----------

class TestRegister:
    _test_email = None

    def test_register_new_user_creates_and_logs_in(self):
        # Unique per run
        email = f"test_user_{int(time.time()*1000)}@example.test"
        TestRegister._test_email = email
        s = requests.Session()
        r = s.post(f"{API}/auth/register", json={"email": email, "password": "testpass123", "nome": "Test User"}, timeout=15)
        assert r.status_code == 200, f"Register failed: {r.status_code} {r.text}"
        data = r.json()
        assert data["email"] == email
        assert data["nome"] == "Test User"
        assert data["role"] == "user"
        assert isinstance(data.get("token"), str)
        # Cookie set → session authed
        assert "access_token" in s.cookies
        # /auth/me works
        r2 = s.get(f"{API}/auth/me", timeout=10)
        assert r2.status_code == 200
        assert r2.json()["email"] == email

    def test_register_duplicate_email_returns_400(self):
        assert TestRegister._test_email, "prev test must have run"
        r = requests.post(f"{API}/auth/register", json={"email": TestRegister._test_email, "password": "x"}, timeout=10)
        assert r.status_code == 400
        assert "detail" in r.json()

    def test_register_missing_email_returns_400(self):
        r = requests.post(f"{API}/auth/register", json={"email": "", "password": "x"}, timeout=10)
        assert r.status_code == 400


# ---------- Bulk PDF export ZIP ----------

class TestBulkPDFExport:
    _created_ids = []

    @classmethod
    def teardown_class(cls):
        s = requests.Session()
        r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=10)
        if r.status_code == 200:
            for cid in cls._created_ids:
                try:
                    s.delete(f"{API}/clienti/{cid}", timeout=10)
                except Exception:
                    pass

    def _create_client(self, session, **overrides):
        payload = {
            "nome": "Giovanni",
            "cognome": "Verdi_TEST",
            "tipo_barca": "Cabinato",
            "lunghezza": 8.0,
            "tipo_sosta": "dentro",
            "telefono": "111",
            "email": "verdi@test.it",
            "potenza_motore": 120,
        }
        payload.update(overrides)
        r = session.post(f"{API}/clienti", json=payload, timeout=15)
        assert r.status_code == 200, f"Create client failed: {r.status_code} {r.text}"
        cid = r.json()["id"]
        TestBulkPDFExport._created_ids.append(cid)
        return r.json()

    def test_bulk_zip_export_has_valid_pdfs(self, auth_session):
        # Ensure at least 2 known clienti exist. Use unique posto to avoid conflicts.
        # Find free posti
        r = auth_session.get(f"{API}/posti-barca", timeout=10)
        assert r.status_code == 200
        posti = r.json()
        free = [p["numero"] for p in posti if not p["occupato"]]
        assert len(free) >= 2, "Need free posti to create test clients"

        c1 = self._create_client(auth_session, nome="Giovanni", cognome="Verdi_TEST", posto_barca=free[0])
        c2 = self._create_client(auth_session, nome="Mario", cognome="Rossi_TEST", posto_barca=free[1], lunghezza=6.5)

        # Fetch ZIP
        r = auth_session.get(f"{API}/export/preventivi.zip", timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/zip")
        cd = r.headers.get("content-disposition", "")
        assert "preventivi_cantiere_" in cd and cd.endswith(".zip"[-4:])

        content = r.content
        assert len(content) > 500, f"ZIP too small: {len(content)}"

        # Parse ZIP
        zf = zipfile.ZipFile(io.BytesIO(content))
        names = zf.namelist()
        assert len(names) >= 2, f"ZIP should contain >=2 PDFs; got {names}"

        # Each PDF must be sanitized name and valid (>2000 bytes, starts with %PDF)
        for name in names:
            # sanitized: only alnum, dot, underscore, dash
            assert all(ch.isalnum() or ch in "._-" for ch in name), f"Invalid filename: {name}"
            assert name.endswith(".pdf"), f"Not a pdf: {name}"
            data = zf.read(name)
            assert len(data) > 2000, f"PDF {name} too small: {len(data)}"
            assert data.startswith(b"%PDF"), f"PDF {name} invalid magic bytes"

        # Verify our test filenames appear (posto-prefixed, sanitized lowercase)
        expected_frag_1 = f"{int(c1['posto_barca']):03d}_verdi"  # 'verdi_test' after underscore strip? underscore is preserved
        expected_frag_2 = f"{int(c2['posto_barca']):03d}_rossi"
        joined = " ".join(names).lower()
        assert expected_frag_1 in joined, f"Missing filename with {expected_frag_1} in {names}"
        assert expected_frag_2 in joined, f"Missing filename with {expected_frag_2} in {names}"

    def test_bulk_zip_via_bearer_token(self, admin_token):
        r = requests.get(f"{API}/export/preventivi.zip",
                         headers={"Authorization": f"Bearer {admin_token}"}, timeout=60)
        assert r.status_code == 200
        assert r.headers.get("content-type", "").startswith("application/zip")


# ---------- Ensure existing (protected) endpoints still work when authed ----------

class TestExistingProtectedEndpoints:
    def test_stats_authed(self, auth_session):
        r = auth_session.get(f"{API}/stats", timeout=10)
        assert r.status_code == 200
        data = r.json()
        for k in ("totale_clienti", "posti_totali", "posti_occupati", "posti_liberi",
                  "sosta_dentro", "sosta_fuori", "sosta_fuori_sede", "entrate_totali"):
            assert k in data

    def test_tariffe_authed(self, auth_session):
        r = auth_session.get(f"{API}/tariffe", timeout=10)
        assert r.status_code == 200
        assert "copertura_per_metro" in r.json()

    def test_cantiere_authed(self, auth_session):
        r = auth_session.get(f"{API}/cantiere", timeout=10)
        assert r.status_code == 200
        assert "nome" in r.json()

    def test_calcola_costi_authed(self, auth_session):
        r = auth_session.get(f"{API}/calcola-costi",
                             params={"lunghezza": 8, "tipo_sosta": "dentro"}, timeout=10)
        assert r.status_code == 200
        assert "costo_sosta" in r.json()
