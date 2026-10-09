import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "gateway_v3.py").read_text(encoding="utf-8")

def test_gateway_parses_as_python():
    ast.parse(SOURCE)

def test_required_routes_are_declared():
    for route in [
        '@app.post("/v1/video")',
        '@app.post("/v1/voice")',
        '@app.get("/v1/models")',
        '@app.post("/v1/embed")',
        '@app.websocket("/v1/stream")',
        '@app.post("/v1/subscribe")',
        '@app.post("/webhooks/mollie")',
        '@app.post("/v1/scan/image")',
        '@app.post("/v1/push/subscribe")',
    ]:
        assert route in SOURCE, f"Missing route: {route}"

def test_pricing_contract_and_daily_quota():
    assert '"price": 49, "requests_per_day": 1000' in SOURCE
    assert '"price": 199, "requests_per_day": None' in SOURCE
    assert '"price": 0, "requests_per_day": 20' in SOURCE
    assert "Re-check the daily quota for every message" in SOURCE

def test_secret_values_are_environment_configured():
    assert 'os.getenv("WHISPER_URL"' in SOURCE
    assert 'os.getenv("MOLLIE_API_KEY"' in SOURCE
    assert 'os.getenv("VAPID_PRIVATE_KEY"' in SOURCE
