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


def test_mid_run_subscriber_gets_backlog_then_live():
    """A viewer joining late must see the whole world, not a partial one."""
    broadcaster = LedgerBroadcaster()
    app = create_app(broadcaster)
    early = [{"run_id": "r", "seq": i, "tick": i, "kind": "agent_moved",
              "agent_id": "a", "data": {}} for i in range(3)]
    for event in early:
        broadcaster.publish(event)  # published before anyone connects
    with TestClient(app) as client:
        with client.websocket_connect("/ws/ledger") as ws:
            got = [ws.receive_json() for _ in range(3)]
            assert [e["seq"] for e in got] == [0, 1, 2]  # backlog replayed
            live = {"run_id": "r", "seq": 3, "tick": 9, "kind": "agent_moved",
                    "agent_id": "a", "data": {}}
            broadcaster.publish(live)
            assert ws.receive_json() == live  # then live-tails


def test_unsubscribe_on_disconnect():
    broadcaster = LedgerBroadcaster()
    app = create_app(broadcaster)
    with TestClient(app) as client:
        with client.websocket_connect("/ws/ledger"):
            assert len(broadcaster._subscribers) == 1
    broadcaster.publish({"k": 1})  # no subscribers left; must not blow up
    assert len(broadcaster._subscribers) == 0


def test_run_cognition_on_event_hook_sees_every_ledger_event():
    """The live-mode seam: --serve-ws wires broadcaster.publish here."""
    import asyncio

    from cognition.runner import fake_gateway, run_cognition

    seen: list[dict] = []
    writer, *_ = asyncio.run(run_cognition(
        60, seed=42, agent_ids=["maren_alder", "piet_alder"],
        gateway=fake_gateway(), on_event=seen.append))
    assert len(seen) == writer.seq
    assert seen[0]["kind"] == "run_started"
    assert seen[-1]["kind"] == "run_finished"
