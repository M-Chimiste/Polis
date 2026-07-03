"""Content wall: content/ validates against schemas AND the standalone validator."""
import subprocess
import sys

from sim.content import CONTENT_DIR, ROOT, content_hash, load_agents, load_relationships, load_town


def test_town_loads_and_validates():
    town = load_town()
    assert town["id"] == "harrowmere"
    assert len(town["locations"]) == 16


def test_agents_load_and_validate():
    agents = load_agents()
    assert len(agents) == 20
    assert all(a["home"] and a["workplace"] for a in agents.values())


def test_relationships_load_and_validate():
    edges = load_relationships()
    assert len(edges) == 32


def test_agent_refs_resolve_to_locations_and_agents():
    town = load_town()
    agents = load_agents()
    loc_ids = {l["id"] for l in town["locations"]}
    for a in agents.values():
        assert a["home"] in loc_ids
        assert a["workplace"] in loc_ids
    for e in load_relationships():
        assert e["a"] in agents and e["b"] in agents


def test_needs_grounding_coverage():
    """Every home affords sleep+food; every workplace affords work; the town
    has leisure. This is what the future needs system grounds against."""
    town = load_town()
    affordances = {
        l["id"]: {a for o in l["objects"] for a in o["affordances"]}
        for l in town["locations"]
    }
    for agent in load_agents().values():
        assert {"sleep", "food"} <= affordances[agent["home"]], agent["id"]
        assert "work" in affordances[agent["workplace"]], agent["id"]
    all_affordances = set().union(*affordances.values())
    assert all_affordances == {"sleep", "food", "hygiene", "leisure", "social", "work"}


def test_objects_are_generic_fixtures():
    town = load_town()
    for l in town["locations"]:
        for o in l["objects"]:
            assert "'s " not in o["name"], f"{o['id']}: '{o['name']}' looks agent-owned"


def test_standalone_validator_passes():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_content.py")],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


def test_content_hash_is_stable_and_config_shaped():
    h1, h2 = content_hash(), content_hash()
    assert h1 == h2
    assert len(h1) == 64 and int(h1, 16) >= 0
    assert CONTENT_DIR.is_dir()
