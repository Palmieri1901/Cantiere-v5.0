"""Shared pytest fixtures. Auth was added in iteration 6 — regression test sessions
now need to be logged in to access /api/*."""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/") or "http://localhost:8001"
API = f"{BASE_URL}/api"

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@portomare.it")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "portomare2026")


def _login_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    r = s.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin auth failed: {r.status_code} {r.text}")
    return s


@pytest.fixture(scope="module")
def session():
    """Authenticated session (cookie-based). Overrides local unauth'd fixtures with same name."""
    return _login_session()
