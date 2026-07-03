"""Shared fixture: one treated 5-agent cognition day (fake model), exported
as run artifacts — several P3 test modules post-process it."""
import asyncio
import io

import pytest

from cognition.runner import export_memories, fake_gateway, run_cognition
from cognition.runtime import Settings
from sim.clock import TICKS_PER_DAY

FIVE = ["ilse_alder", "maren_alder", "piet_alder", "sela_crane", "tobias_crane"]
FACT = "there is a gathering at the tavern on day three"
TREATMENT = {"kind": "seeded_fact", "fact": FACT, "target_agent": "maren_alder",
             "inject_tick": 2400, "importance": 9}


@pytest.fixture(scope="session")
def treated_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("treated_run")
    ledger, completions = io.BytesIO(), io.BytesIO()

    async def go():
        return await run_cognition(
            TICKS_PER_DAY, seed=42, agent_ids=FIVE,
            settings=Settings(reflection_importance_sum_threshold=40.0),
            gateway=fake_gateway(), treatments=[TREATMENT],
            ledger_sink=ledger, completions_sink=completions)

    writer, gateway, runtime = asyncio.run(go())
    (out / "ledger.jsonl").write_bytes(ledger.getvalue())
    (out / "completions.jsonl").write_bytes(completions.getvalue())
    memories = io.BytesIO()
    export_memories(runtime, memories)
    (out / "memories.jsonl").write_bytes(memories.getvalue())
    return {"dir": out, "writer": writer, "gateway": gateway, "runtime": runtime,
            "agents": FIVE, "fact": FACT, "treatment": TREATMENT}
