"""WebSocket sidecar: relays ledger events, zero authority."""
from fastapi.testclient import TestClient

from sim.stream import LedgerBroadcaster, create_app


def test_healthz():
    app = create_app(LedgerBroadcaster())
    with TestClient(app) as client:
        assert client.get("/healthz").json() == {"ok": True}


def test_ledger_events_stream_to_subscriber():
    broadcaster = LedgerBroadcaster()
    app = create_app(broadcaster)
    event = {"run_id": "r", "seq": 0, "tick": 3, "kind": "agent_moved",
             "agent_id": "sela_crane", "data": {"from": [1, 1], "to": [1, 2]}}
    with TestClient(app) as client:
        with client.websocket_connect("/ws/ledger") as ws:
            broadcaster.publish(event)
            assert ws.receive_json() == event


def test_unsubscribe_on_disconnect():
    broadcaster = LedgerBroadcaster()
    app = create_app(broadcaster)
    with TestClient(app) as client:
        with client.websocket_connect("/ws/ledger"):
            assert len(broadcaster._subscribers) == 1
    broadcaster.publish({"k": 1})  # no subscribers left; must not blow up
    assert len(broadcaster._subscribers) == 0
