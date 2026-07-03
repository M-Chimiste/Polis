"""Crossing conversation requests (live-gate bug 2026-07-03): three requests
crossing in one tick let the world broker two conversations sharing an agent;
the loser was dropped with no conversation_ended and the ghosted requester
never got a signal. Invariants now: every conversation_started gets exactly
one conversation_ended, and every request gets an accept or explicit decline.
"""
import asyncio

from cognition.completions import CognitionGateway, CompletionLog
from cognition.embedding import HashEmbedder
from cognition.runner import fake_gateway
from cognition.runtime import CognitionRuntime, Conversation, Settings
from sim.content import load_agents, load_town

A, B, C = "ilse_alder", "maren_alder", "piet_alder"
RUN_ID = "00000000-0000-0000-0000-00000000c0de"


def make_runtime():
    town = load_town()
    seeds = {aid: s for aid, s in load_agents().items() if aid in (A, B, C)}
    from sim.world import World
    world = World(town, seeds, master_seed=7)
    # co-locate all three, awake, mid-morning (test surgery: the bug needs
    # exact same-tick crossing, which a live day only produces by chance)
    anchor = world.agents[A].pos
    for aid in (A, B, C):
        world.agents[aid].pos = anchor
        world.agents[aid].status = "idle"
    log = CompletionLog(RUN_ID)
    runtime = CognitionRuntime(world, seeds, CognitionGateway(fake_gateway(), log),
                               HashEmbedder(), Settings(), RUN_ID)
    return world, runtime


def converse(aid, partner, mode, tick):
    return {"agent_id": aid, "tick": tick, "kind": "converse_with",
            "partner_id": partner, "mode": mode}


def test_crossing_requests_leave_no_dangling_conversation():
    world, runtime = make_runtime()

    # the exact live-day crossing: A->C, B->C, C->A in one world step
    events = world.step({
        A: converse(A, C, "request", world.tick),
        B: converse(B, C, "request", world.tick),
        C: converse(C, A, "request", world.tick),
    })
    assert [e[0] for e in events].count("conversation_requested") == 3

    async def drive():
        all_events = list(events)
        pending = all_events
        for _ in range(60):  # enough ticks to resolve, converse, and wind down
            intents, cognition_events = await runtime.tick(pending)
            world_events = world.step(intents)
            pending = cognition_events + world_events
            all_events.extend(pending)
        return all_events

    all_events = asyncio.run(drive())
    kinds = [e[0] for e in all_events]

    started = kinds.count("conversation_started")
    ended = kinds.count("conversation_ended")
    declined = kinds.count("conversation_declined")

    # exactly one conversation actually ran (utterances flowed)
    assert kinds.count("utterance") > 0
    # every started is closed; nothing dangles
    assert started == ended
    assert all(m.conversation is None for m in runtime.minds.values())
    # nobody was ghosted: 3 requests -> started pair(s) + explicit decline(s)
    assert declined >= 1
    # queues fully drained
    assert all(not m.incoming_requests for m in runtime.minds.values())


def test_second_request_to_busy_agent_gets_declined():
    world, runtime = make_runtime()

    # A and C are mid-conversation; B requests C
    conv = Conversation(initiator=A, partner=C, speaker=A)
    runtime.minds[A].conversation = conv
    runtime.minds[C].conversation = conv
    events = world.step({B: converse(B, C, "request", world.tick)})

    async def drive():
        all_events = list(events)
        pending = all_events
        for _ in range(4):
            intents, cognition_events = await runtime.tick(pending)
            world_events = world.step(intents)
            pending = cognition_events + world_events
            all_events.extend(pending)
        return all_events

    all_events = asyncio.run(drive())
    declines = [e for e in all_events if e[0] == "conversation_declined"
                and e[2]["partner"] == B]
    assert declines, "busy agent must explicitly decline, not ghost"
