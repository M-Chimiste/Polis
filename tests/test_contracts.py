"""Fixture instances for the v0 cross-boundary contracts."""
import pytest

import schemas

RUN = "6f1a2b3c-4d5e-4f60-8a9b-0c1d2e3f4a5b"
MEM1 = "0e9d8c7b-6a5f-4e4d-8c2b-1a0f9e8d7c6b"
MEM2 = "1a2b3c4d-5e6f-4a8b-9c0d-e1f2a3b4c5d6"

LEDGER_EVENT = {
    "run_id": RUN, "seq": 0, "tick": 0, "kind": "agent_moved",
    "agent_id": "maren_alder", "data": {"from": [24, 30], "to": [24, 29]},
}

WORLD_EVENT = {
    "run_id": RUN, "seq": 1, "tick": 360, "kind": "treatment_injected",
    "agent_id": None, "data": {"fact": "there is a gathering at the tavern on day 3", "target_agent": "maren_alder"},
}

MEMORY_RECORD = {
    "id": MEM1, "run_id": RUN, "agent_id": "maren_alder", "kind": "observation",
    "tick": 12, "text": "Piet has been quieter than usual this week.", "importance": 4,
}

REFLECTION = {
    "id": MEM2, "run_id": RUN, "agent_id": "maren_alder", "kind": "reflection",
    "tick": 4000, "text": "Something is weighing on Piet that he is not saying.",
    "importance": 7, "citations": [MEM1],
}

EXPERIMENT_CONFIG = {
    "experiment_id": "diffusion-v0",
    "description": "seeded-fact diffusion, 20 agents, 3 sim-days",
    "seed": 42,
    "duration_ticks": 25920,
    "content_hash": "a" * 64,
    "gateway_profile": "mnemosyne",
    "roles": {
        "dialogue": {"tier": "fast", "sampling": {"temperature": 0.9, "top_p": 0.95, "max_tokens": 512}},
        "reflection": {"tier": "slow", "sampling": {"temperature": 0.8, "max_tokens": 1024}},
    },
    "retrieval": {"alpha": 1.0, "beta": 1.0, "gamma": 1.0},
    "perception": {"sight_cone_half_angle_deg": 65, "sight_range": 8, "hearing_radius": 3},
    "interrupt_importance_threshold": 6,
    "treatments": [
        {"kind": "seeded_fact", "fact": "there is a gathering at the tavern on day 3",
         "target_agent": "maren_alder", "inject_tick": 360}
    ],
}

PROBE_RESULT = {
    "probe_id": "2b3c4d5e-6f70-4a1b-8c2d-3e4f5a6b7c8d", "run_id": RUN,
    "agent_id": "sela_crane", "kind": "fact_check", "tick": 17280,
    "question": "Have you heard anything about a gathering at the tavern?",
    "response": "Petra mentioned something brewing at the Perch, day after tomorrow.",
    "scores": {"knows_fact": True},
}


@pytest.mark.parametrize("name,instance", [
    ("ledger_event", LEDGER_EVENT),
    ("ledger_event", WORLD_EVENT),
    ("memory_record", MEMORY_RECORD),
    ("memory_record", REFLECTION),
    ("experiment_config", EXPERIMENT_CONFIG),
    ("probe_result", PROBE_RESULT),
])
def test_valid_instances(name, instance):
    assert schemas.errors(name, instance) == []


@pytest.mark.parametrize("name,mutation", [
    ("ledger_event", {"seq": -1}),
    ("ledger_event", {"agent_id": 7}),
    ("memory_record", {"importance": 11}),
    ("memory_record", {"kind": "gossip"}),
    ("memory_record", {"id": "not-a-uuid"}),
    ("experiment_config", {"content_hash": "xyz"}),
    ("experiment_config", {"retrieval": {"alpha": 1.0}}),
    ("probe_result", {"kind": "seance"}),
])
def test_mutated_instances_rejected(name, mutation):
    base = {
        "ledger_event": LEDGER_EVENT,
        "memory_record": MEMORY_RECORD,
        "experiment_config": EXPERIMENT_CONFIG,
        "probe_result": PROBE_RESULT,
    }[name]
    assert schemas.errors(name, {**base, **mutation}) != []


def test_extra_properties_rejected_everywhere():
    for name, base in [
        ("ledger_event", LEDGER_EVENT),
        ("memory_record", MEMORY_RECORD),
        ("experiment_config", EXPERIMENT_CONFIG),
        ("probe_result", PROBE_RESULT),
    ]:
        assert schemas.errors(name, {**base, "surprise": 1}) != []
