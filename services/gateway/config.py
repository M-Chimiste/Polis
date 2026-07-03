"""Named hardware profiles with per-model/per-role sampling config.

Source of truth for what to record in an experiment config: the profile name
plus the per-role sampling block (the experiment config hash covers sampling,
so conditions with different sampling are distinct experiments).
"""
from __future__ import annotations

import pathlib

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

DEFAULT_PROFILES_PATH = pathlib.Path(__file__).resolve().parent.parent / "serving" / "profiles.yaml"


class SamplingConfig(BaseModel):
    """Per-role sampling. No global policy, no temperature-0 requirement.

    Reasoning budget is capped server-side at vLLM launch (request-level
    enable_thinking may be ignored — the glasshouse qwen3.6 lesson), so it
    deliberately has no field here.
    """

    model_config = ConfigDict(extra="forbid")

    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    min_p: float | None = None
    max_tokens: int | None = None

    def as_request_params(self) -> dict:
        """Non-null params for an OpenAI-compatible request body.

        top_k / min_p are vLLM extensions; vLLM accepts them as top-level
        body fields on /v1/chat/completions.
        """
        return {k: v for k, v in self.model_dump().items() if v is not None}


class TierConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    model: str


class RoleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tier: str
    sampling: SamplingConfig


class ServingProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    base_url: str
    tiers: dict[str, TierConfig]
    roles: dict[str, RoleConfig]

    @model_validator(mode="after")
    def _roles_reference_real_tiers(self) -> "ServingProfile":
        for role, cfg in self.roles.items():
            if cfg.tier not in self.tiers:
                raise ValueError(f"role '{role}' references unknown tier '{cfg.tier}'")
        return self

    def resolve(self, role: str) -> tuple[str, SamplingConfig]:
        """Return (model, sampling) for a call-site role. KeyError on unknown role."""
        if role not in self.roles:
            raise KeyError(f"unknown role '{role}' in profile '{self.name}' (have: {', '.join(sorted(self.roles))})")
        cfg = self.roles[role]
        return self.tiers[cfg.tier].model, cfg.sampling


def load_profiles(path: pathlib.Path | str = DEFAULT_PROFILES_PATH) -> dict[str, ServingProfile]:
    raw = yaml.safe_load(pathlib.Path(path).read_text())
    return {
        name: ServingProfile(name=name, **body)
        for name, body in raw["profiles"].items()
    }
