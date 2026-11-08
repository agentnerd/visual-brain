# OpenClaw adapter

This optional adapter observes OpenClaw Gateway diagnostic lifecycle events and sends only fixed category/action/source values to Visual Brain. It does not forward diagnostic payloads, prompts, output, tool names/arguments/results, agent/session IDs, or model/provider names.

## Install

1. Start Visual Brain (for example, `python3 server.py`).
2. Install this directory as a linked OpenClaw plugin: `openclaw plugins install --link adapters/openclaw`.
3. Restart/reload the Gateway as instructed by your OpenClaw version. Confirm `/healthz` and the dashboard's telemetry indicator.
4. If the collector is not on the same host, configure `VISUAL_BRAIN_ENDPOINT` and `VISUAL_BRAIN_TOKEN` in the Gateway process environment. Keep the receiver behind TLS and authenticated viewer access.

The adapter uses the exported `openclaw/plugin-sdk/plugin-entry` and `openclaw/plugin-sdk/diagnostic-runtime` module paths. Internal diagnostic event names and coverage can evolve between OpenClaw releases; pin a tested OpenClaw version for production. If the plugin API differs, use the stable HTTP event contract from a supported hook instead of changing the receiver.

## Coverage

Model calls, tool execution, skills, agent/harness lifecycle, and gateway message flow are emitted when corresponding diagnostics exist. The adapter reports message flow as `planning` only as an observable activity category; this is not a view of private planning or reasoning. Memory remains `UNKNOWN` unless a future runtime exposes an explicit retrieval event.
