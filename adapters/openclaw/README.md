# OpenClaw adapter

This optional adapter observes OpenClaw Gateway diagnostic lifecycle events and projects them into fixed Visual Brain category/action/source values named for OpenTelemetry GenAI semantic-convention operations. The compatibility envelope is not OTLP; use the official `diagnostics-otel` exporter for standard OTLP traces. The adapter does not forward diagnostic payloads, prompts, output, tool names/arguments/results, agent/session IDs, or model/provider names.

## Install

1. Start Visual Brain (for example, `python3 server.py`).
2. Install this directory as a linked OpenClaw plugin: `openclaw plugins install --link adapters/openclaw`.
3. Restart/reload the Gateway as instructed by your OpenClaw version. Confirm `/healthz` and the dashboard's telemetry indicator.
4. If the collector is not on the same host, configure `VISUAL_BRAIN_ENDPOINT` and `VISUAL_BRAIN_TOKEN` in the Gateway process environment. Keep the receiver behind TLS and authenticated viewer access.

The adapter uses the exported `openclaw/plugin-sdk/plugin-entry` and `openclaw/plugin-sdk/diagnostic-runtime` module paths. Internal diagnostic event names and coverage can evolve between OpenClaw releases; pin a tested OpenClaw version for production. If the plugin API differs, use OpenTelemetry GenAI instrumentation or the documented compatibility mapping from a supported hook instead of changing the receiver.

## Coverage

Model calls, tool execution, skills, and agent/harness lifecycle are projected only to their matching GenAI semantic-convention operation labels. The adapter does not infer planning from message flow, or memory from arbitrary storage activity. `MEMORY` and `PLAN` remain `UNKNOWN` until the runtime emits matching GenAI memory/retrieval or `plan` spans. The OpenTelemetry GenAI conventions are currently marked **Development**; see the mapping and upstream references in the main README.
