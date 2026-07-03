"""Model gateway (glasshouse pattern reimplemented from scratch, zero code import).

Validation wall + structured outputs + one repair re-prompt + named hardware
profiles + per-model/per-role sampling config. Callers get a typed result,
never an exception, so gateway-down degrades to plan-cache execution instead
of crashing the sim (service-optionality pattern).
"""
from services.gateway.config import (
    RoleConfig,
    SamplingConfig,
    ServingProfile,
    TierConfig,
    load_profiles,
)
from services.gateway.client import (
    GatewayCompletion,
    GatewayFailure,
    GatewayResult,
    ModelGateway,
)

__all__ = [
    "GatewayCompletion",
    "GatewayFailure",
    "GatewayResult",
    "ModelGateway",
    "RoleConfig",
    "SamplingConfig",
    "ServingProfile",
    "TierConfig",
    "load_profiles",
]
