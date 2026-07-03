"""Cost telemetry over the completion log."""
import asyncio

from cognition.runner import FAKE_PROFILE, fake_gateway, run_cognition
from cognition.runtime import Settings
from cognition.telemetry import cost_report

ROLE_TIERS = {role: cfg.tier for role, cfg in FAKE_PROFILE.roles.items()}


def test_cost_report_accounts_for_every_call():
    async def go():
        return await run_cognition(2500, seed=7, agent_ids=["sela_crane", "tobias_crane"],
                                   settings=Settings(), gateway=fake_gateway())
    _, cog_gateway, _ = asyncio.run(go())
    report = cost_report(cog_gateway.log.records, ROLE_TIERS)
    assert report["totals"]["calls"] == cog_gateway.total_calls() > 0
    assert report["totals"]["prompt_tokens"] > 0
    assert report["totals"]["failures"] == 0
    tiers = {c["tier"] for c in report["cells"]}
    assert tiers <= {"fast", "slow"} and "fast" in tiers
    # per-agent per-hour cells are actually split by hour
    hours = {c["sim_hour"] for c in report["cells"]}
    assert len(hours) > 1
    agents = {c["agent_id"] for c in report["cells"]}
    assert agents == {"sela_crane", "tobias_crane"}
