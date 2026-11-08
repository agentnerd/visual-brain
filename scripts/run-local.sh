#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VENV="$ROOT/.venv"

if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi

if ! "$VENV/bin/python" -c 'import opentelemetry.proto.collector.trace.v1.trace_service_pb2' >/dev/null 2>&1; then
  "$VENV/bin/python" -m pip install --disable-pip-version-check -r "$ROOT/requirements-otel.txt"
fi
exec "$VENV/bin/python" "$ROOT/server.py" "$@"
