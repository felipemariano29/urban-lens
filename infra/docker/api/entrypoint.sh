#!/bin/sh
set -eu

exec uvicorn urban_lens.api.main:app --host 0.0.0.0 --port 8000
