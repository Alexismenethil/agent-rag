"""Smoke test del endpoint /health. La forma de la respuesta no depende de la BD."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_responde_con_forma_correcta():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"status", "db"}
    assert body["status"] in {"ok", "degraded"}
    assert body["db"] in {"ok", "down"}


def test_root_responde():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "agente-rag"
