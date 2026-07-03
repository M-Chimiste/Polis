"""Seeded PRNG streams, one per subsystem.

Each subsystem draws from its own named stream so adding randomness to one
subsystem never perturbs another — a prerequisite for byte-equal replay.
"""
from __future__ import annotations

import hashlib
import random


class RngStreams:
    def __init__(self, master_seed: int):
        self.master_seed = master_seed
        self._streams: dict[str, random.Random] = {}

    def stream(self, name: str) -> random.Random:
        if name not in self._streams:
            digest = hashlib.sha256(f"{self.master_seed}:{name}".encode()).digest()
            self._streams[name] = random.Random(int.from_bytes(digest[:8], "big"))
        return self._streams[name]
