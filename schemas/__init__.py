"""Contract schemas: JSON Schema is the source of truth (schemas/json/).

Pydantic mirrors are generated into schemas/models/ by scripts/gen_models.sh —
never hand-edit them; edit the JSON Schema and regenerate. Validation against
the raw JSON Schema (this module) is the wall; the pydantic mirrors are for
ergonomic typed access in Python code.
"""
import functools
import json
import pathlib

from jsonschema import Draft202012Validator, FormatChecker

JSON_DIR = pathlib.Path(__file__).resolve().parent / "json"

SCHEMA_NAMES = sorted(p.name.removesuffix(".schema.json") for p in JSON_DIR.glob("*.schema.json"))


@functools.cache
def load_schema(name: str) -> dict:
    path = JSON_DIR / f"{name}.schema.json"
    if not path.exists():
        raise KeyError(f"unknown schema '{name}' (have: {', '.join(SCHEMA_NAMES)})")
    return json.loads(path.read_text())


@functools.cache
def validator_for(name: str) -> Draft202012Validator:
    return Draft202012Validator(load_schema(name), format_checker=FormatChecker())


def validate(name: str, instance) -> None:
    """Raise jsonschema.ValidationError if instance violates the named schema."""
    validator_for(name).validate(instance)


def errors(name: str, instance) -> list[str]:
    """All violations as strings; empty list means valid."""
    return [e.message for e in validator_for(name).iter_errors(instance)]
