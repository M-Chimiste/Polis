#!/usr/bin/env bash
# Regenerate pydantic mirrors (schemas/models/) from the JSON Schemas
# (schemas/json/ — the source of truth). Run after any schema edit.
# Never hand-edit schemas/models/.
set -euo pipefail
cd "$(dirname "$0")/.."

uv run datamodel-codegen \
  --input schemas/json \
  --input-file-type jsonschema \
  --output schemas/models \
  --output-model-type pydantic_v2.BaseModel \
  --target-python-version 3.12 \
  --use-schema-description \
  --use-double-quotes \
  --disable-timestamp

echo "regenerated schemas/models/ from schemas/json/"
