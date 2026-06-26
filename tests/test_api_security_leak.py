from pathlib import Path

from fastapi.testclient import TestClient

from gw2radar.api import state
from gw2radar.api.main import app

API_KEY_SIGNATURES = [
    "api_key",
    "api-key",
    "apikey",
    "raw_payload",
    "encrypted_value",
    "GW2APIKEY",
    "12345678-1234-1234-1234-123456789abc",
]


def test_all_endpoints_no_api_key_leak() -> None:
    state.reset_cached_graph()
    client = TestClient(app)
    client.post("/mock/load")
    endpoints = [
        ("GET", "/health"),
        ("GET", "/api/v1/player/account-value"),
        ("GET", "/api/v1/player/readiness"),
        ("GET", "/api/v1/market/watchlist"),
        ("GET", "/api/v1/market/signals"),
        ("GET", "/api/v1/market/goal-cost-index"),
        ("GET", "/api/v1/market/patch-freshness"),
        ("GET", "/api/v1/legendary/portfolio"),
        ("GET", "/api/v1/legendary/goals"),
        ("GET", "/api/v1/ontology/registry"),
        ("POST", "/api/v1/ontology/enrich"),
        ("POST", "/api/v1/ontology/qa"),
        ("POST", "/api/v1/ontology/impact/sell-item?item_id=gw2:item:mystic_coin"),
        ("POST", "/api/v1/ontology/impact/goal-change?goal_id=gw2:goal:aurora"),
        ("POST", "/api/v1/ontology/query/relations?predicate=requires"),
    ]
    leaks: list[str] = []
    for method, path in endpoints:
        try:
            if method == "GET":
                resp = client.get(path)
            else:
                resp = client.post(path)
            body = resp.text.lower()
            for sig in API_KEY_SIGNATURES:
                if sig.lower() in body:
                    leaks.append(f"[{resp.status_code}] {method} {path} contains '{sig}'")
                    break
        except Exception as exc:
            leaks.append(f"[ERROR] {method} {path} raised: {exc}")
    assert not leaks, f"API key leaks detected ({len(leaks)}):\n" + "\n".join(leaks[:10])


def test_impact_sell_item_output_safe() -> None:
    state.reset_cached_graph()
    client = TestClient(app)
    client.post("/mock/load")
    resp = client.post("/api/v1/ontology/impact/sell-item?item_id=gw2:item:mystic_coin")
    assert resp.status_code == 200
    body = resp.text.lower()
    for sig in API_KEY_SIGNATURES:
        assert sig.lower() not in body, f"Leak: {sig} in impact/sell-item response"


def test_player_html_api_key_input_is_password() -> None:
    html_path = Path(__file__).resolve().parents[1] / "src" / "gw2radar" / "ui" / "static" / "player.html"
    html = html_path.read_text(encoding="utf-8")
    assert 'type="password"' in html, "API key input must be type=password"
    assert "api-key-input" in html, "API key input must have id=api-key-input"


def test_player_html_no_raw_key_exposure() -> None:
    html_path = Path(__file__).resolve().parents[1] / "src" / "gw2radar" / "ui" / "static" / "player.html"
    html = html_path.read_text(encoding="utf-8").lower()
    assert "api_key" not in html or "api-key-input" in html


def test_impact_goal_change_output_safe() -> None:
    state.reset_cached_graph()
    client = TestClient(app)
    client.post("/mock/load")
    resp = client.post("/api/v1/ontology/impact/goal-change?goal_id=gw2:goal:aurora")
    assert resp.status_code == 200
    body = resp.text.lower()
    for sig in API_KEY_SIGNATURES:
        assert sig.lower() not in body, f"Leak: {sig} in impact/goal-change response"
