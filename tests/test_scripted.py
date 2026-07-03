"""Scripted FSM agents live a coherent anchor-driven day without models."""
from sim.clock import TICKS_PER_DAY, minute_of_day, parse_hhmm
from sim.content import load_agents, load_town
from sim.runner import run
from sim.scripted import ScriptedAgent
from sim.world import World

TOWN = load_town()
SEEDS = load_agents()


def simulate(ticks, seed=42):
    world = World(TOWN, SEEDS, master_seed=seed)
    controllers = {aid: ScriptedAgent(s) for aid, s in SEEDS.items()}
    for _ in range(ticks):
        minute = minute_of_day(world.tick)
        intents = {}
        for aid in sorted(controllers):
            intent = controllers[aid].intent(world, minute)
            if intent is not None:
                intents[aid] = intent
        world.step(intents)
    return world


def test_everyone_asleep_at_midnight():
    world = simulate(6)  # 00:01
    assert all(a.status == "sleeping" for a in world.agents.values())


def test_commuter_is_at_work_mid_morning():
    # sela_crane: home != workplace; check she's at her workplace at 10:30
    assert SEEDS["sela_crane"]["home"] != SEEDS["sela_crane"]["workplace"]
    work_start = parse_hhmm(SEEDS["sela_crane"]["daily_anchors"]["work_start"])
    assert work_start <= 10 * 60
    world = simulate(int(10.5 * 3600 // 10))  # 10:30
    assert world.location_of("sela_crane") == SEEDS["sela_crane"]["workplace"]


def test_everyone_home_or_workplace_all_day():
    world = World(TOWN, SEEDS, master_seed=1)
    controllers = {aid: ScriptedAgent(s) for aid, s in SEEDS.items()}
    valid = {aid: {s["home"], s["workplace"], None} for aid, s in SEEDS.items()}  # None while commuting
    for _ in range(TICKS_PER_DAY):
        minute = minute_of_day(world.tick)
        intents = {}
        for aid in sorted(controllers):
            intent = controllers[aid].intent(world, minute)
            if intent is not None:
                intents[aid] = intent
        events = world.step(intents)
        assert not [e for e in events if e[0] == "intent_rejected"], events
    for aid in world.agents:
        assert world.location_of(aid) in valid[aid]


def test_full_day_produces_movement_and_sleep_cycles():
    import io
    sink = io.BytesIO()
    run(TICKS_PER_DAY, seed=42, sink=sink)
    lines = sink.getvalue().decode().splitlines()
    kinds = [line.split('"kind":"')[1].split('"')[0] for line in lines]
    commuters = sum(1 for s in SEEDS.values() if s["home"] != s["workplace"])
    assert commuters > 0
    assert kinds.count("agent_arrived") == 2 * commuters       # out and back
    assert kinds.count("agent_status_changed") == 2 * len(SEEDS)  # wake + sleep each
    assert kinds.count("agent_moved") > 20 * commuters         # real walks, not teleports
