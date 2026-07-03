"""Measurement plane (P3): post-processes the ledger and memory store only.

Never reads sim internals live; probes run against frozen state copies and
must leave zero footprint in sim data."""
