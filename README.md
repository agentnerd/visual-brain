# Visual Brain

**A harness-agnostic live activity display for AI agents.** Visual Brain accepts standard [OpenTelemetry OTLP/HTTP traces](https://opentelemetry.io/docs/specs/otlp/) and projects allowlisted GenAI operation spans into a responsive browser brain. The UI also exposes state as JSON and Server-Sent Events (SSE), so widgets and other dashboards can share it.

There is no Visual Brain-specific agent SDK requirement. If an agent framework already exports OpenTelemetry GenAI spans, point it at this receiver. Otherwise, use the framework's OTel instrumentation or the optional small custom event API. The display shows observed execution—not model thoughts—and never needs prompts, completions, tool arguments/results, or private reasoning.

## Local install

Requires Python 3.10+. Core dashboard has no dependencies. To accept standard OTLP traces, install the optional protocol package:

```sh
git clone https://github.com/agentnerd/visual-brain.git
cd visual-brain
python3 -m pip install -r requirements-otel.txt
python3 server.py
```

Open <http://127.0.0.1:18896>. Configure your agent's OpenTelemetry exporter:

```sh
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:18896
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
```

The receiver supports standard OTLP/HTTP protobuf and JSON on `/v1/traces`. Your framework/instrumentation must emit spans with the OpenTelemetry GenAI semantic-convention attribute `gen_ai.operation.name`. It maps common operations such as `chat`, `text_completion`, and `embeddings` to **MODEL**, `execute_tool` to **TOOLS**, and `invoke_agent` / `create_agent` to **AGENTS**. OTel GenAI conventions do not currently provide portable event coverage for every brain region; unobserved **MEMORY**, **SKILLS**, and **PLANNING** stay `UNKNOWN` rather than being guessed.

## Live timing limits

The UI updates as telemetry arrives. Most OpenTelemetry tracing SDKs export a span only after that operation finishes, so OTLP traces alone usually show completed work as **RECENT**, not continuously **ACTIVE** during a long call. **ACTIVE** requires an instrumentation/export path that reports in-flight lifecycle state. The optional event endpoint supports explicit start/end and heartbeats for runtimes that expose those hooks. Do not mistake a completed span or a quiet feed for current activity.

## Displays and integrations

- **Browser dashboard:** built in; responsive and updated over SSE.
- **Other dashboards/widgets:** consume `GET /state` (snapshot JSON) or `GET /events` (SSE). Each SSE `data:` value is a complete state snapshot. Embed the dashboard as a same-origin iframe or create a native visualization.
- **Telegram:** host the dashboard at an authenticated HTTPS origin and open it as a Telegram Mini App/Web App. A chat message cannot contain an arbitrary interactive widget. This repo provides the web display, not a Telegram bot, hosting account, or public tunnel.
- **Any agent/harness:** use its existing OpenTelemetry instrumentation/exporter. For runtimes with lifecycle hooks but no OTel export, the optional event API below is a minimal fallback; there is no need to adopt it when OTLP is available.
- **OpenClaw:** an optional adapter is in [`adapters/openclaw/`](adapters/openclaw/). It observes OpenClaw Gateway diagnostic events, including live starts/ends where emitted. Runtime diagnostic coverage/API can vary by OpenClaw version.

## Optional event API

`POST /v1/event` accepts a deliberately small, content-free JSON object:

```json
{"category":"tools","action":"start","source":"tool.execution"}
```

Send the same event with `"action":"end"` when it completes. Allowed category/source pairs are `model/model.call`, `tools/tool.execution`, `memory/memory.access`, `skills/skill.use`, `planning/agent.phase`, and `agents/agent.run`; allowed actions are `start`, `end`, `pulse`, and `heartbeat`. A heartbeat event may include integer `active` (0–512). `POST /v1/heartbeat` accepts `{"event":"bridge-heartbeat"}`. Extra fields are rejected. See [`examples/`](examples/) for tiny Python and JavaScript fallback emitters.

## Cloud / private deployment

For a private cloud/VPS, terminate TLS and enforce viewer authentication at a trusted reverse proxy. Bind the receiver remotely only with an ingest token:

```sh
export VISUAL_BRAIN_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python3 server.py --host 0.0.0.0 --port 18896 --token "$VISUAL_BRAIN_TOKEN" --allow-remote
```

Configure the same token in OTel exporter headers (for shell environments: `export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer%20${VISUAL_BRAIN_TOKEN}"`) or as `Authorization: Bearer …` on fallback POSTs. Keep viewer access behind SSO/OIDC or equivalent proxy auth; the ingest token is not a viewer login. Do not expose the receiver directly to the Internet: it does not terminate TLS, manage users, or provide tenant isolation. For Telegram Mini Apps, serve UI and API from an authenticated HTTPS deployment and validate Telegram `initData` in a trusted backend before granting a viewer session.

## Privacy and limits

- OTLP data is parsed in memory; only allowlisted operation categories, fixed source labels, counters, timestamps, and aggregate in-flight counts appear in the UI.
- Span names, attributes (including model names), resource metadata, prompts, outputs, IDs, and tool details are not copied into the public state projection.
- The recent-event ring is capped at 64; process restart clears it. Ingest request size is capped at 1 MiB.
- Local loopback is the default. Remote bind requires explicit opt-in and a bearer token. Cloud transport privacy and viewer authentication remain the operator's responsibility.
- No durability, analytics, multi-tenant separation, or external telemetry vendor is required.

## Endpoints

`GET /`, `GET /state`, `GET /events`, `GET /healthz`, `POST /v1/traces` (OTLP/HTTP), `POST /v1/event` (optional fallback), and `POST /v1/heartbeat`.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
