"""The P1 gate: byte-equal ledger across headless runs, no LLM.

The committed fixture is the permanent wall — if it breaks, either you
changed sim semantics on purpose (regenerate it in the same commit and say
so) or you introduced nondeterminism (fix that instead).

Regenerate: uv run python -m sim.runner --ticks 3000 --seed 42 \
    --out tests/fixtures/ledger_scripted_seed42_3000.jsonl
"""
import io
import pathlib

from sim.runner import run

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "ledger_scripted_seed42_3000.jsonl"


def run_bytes(ticks=3000, seed=42) -> bytes:
    sink = io.BytesIO()
    run(ticks, seed=seed, sink=sink)
    return sink.getvalue()


def test_two_runs_byte_equal():
    assert run_bytes() == run_bytes()


def test_run_matches_committed_fixture():
    assert run_bytes() == FIXTURE.read_bytes()


def test_different_seed_same_structure():
    # scripted mode uses no randomness yet, so seed only changes run_id;
    # this pins that fact so introducing PRNG use later is a conscious change
    a, b = run_bytes(seed=1), run_bytes(seed=2)
    assert a != b  # run_id and seed differ
    assert len(a.splitlines()) == len(b.splitlines())
