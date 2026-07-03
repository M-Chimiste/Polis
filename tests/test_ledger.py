"""Ledger writer: schema-valid, canonical, byte-stable."""
import io
import json

import pytest

import schemas
from sim.ledger import LedgerWriter, canonical_line

RUN = "6f1a2b3c-4d5e-4f60-8a9b-0c1d2e3f4a5b"


def test_events_validate_and_serialize_canonically():
    sink = io.BytesIO()
    writer = LedgerWriter(RUN, sink=sink)
    e0 = writer.append(0, "run_started", None, {"seed": 1})
    e1 = writer.append(3, "agent_moved", "sela_crane", {"from": [1, 1], "to": [1, 2]})
    assert schemas.errors("ledger_event", e0) == []
    assert (e0["seq"], e1["seq"]) == (0, 1)
    lines = sink.getvalue().splitlines()
    assert len(lines) == 2
    # canonical: sorted keys, compact, parseable
    assert lines[1] == canonical_line(e1).strip()
    assert json.loads(lines[1])["agent_id"] == "sela_crane"
    assert b" " not in lines[0]


def test_invalid_event_is_an_internal_error():
    writer = LedgerWriter(RUN)
    with pytest.raises(ValueError):
        writer.append(-1, "agent_moved", "x", {})


def test_on_event_hook_receives_every_event():
    seen = []
    writer = LedgerWriter(RUN, on_event=seen.append)
    writer.append(0, "run_started", None, {})
    writer.append(1, "run_finished", None, {})
    assert [e["kind"] for e in seen] == ["run_started", "run_finished"]
