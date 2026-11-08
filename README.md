# Visual Brain

**A harness-agnostic live activity display for AI agents.** Visual Brain accepts standard [OpenTelemetry OTLP/HTTP traces](https://opentelemetry.io/docs/specs/otlp/) and projects allowlisted OpenTelemetry GenAI semantic-convention spans into a responsive browser brain. The UI also exposes state as JSON and Server-Sent Events (SSE), so widgets and other dashboards can share it.

There is no Visual Brain-specific agent SDK requirement. If an agent framework already exports OpenTelemetry GenAI spans, point it at this receiver. Otherwise, use the framework's OpenTelemetry instrumentation. A small optional compatibility event endpoint remains for runtimes without OTLP support; its accepted category/source values map to the same published GenAI conventions, but that fallback envelope itself is not OTLP. The display shows observed execution—not model thoughts—and never needs prompts, completions, tool arguments/results, or private reasoning.

## Local install

Requires Python 3.10+. The one-command launcher creates an isolated virtual environment, installs the OTLP protocol dependency, then starts the local display:

```sh
git clone https://github.com/agentnerd/visual-brain.git
cd visual-brain
./scripts/run-local.sh
```

Open <http://127.0.0.1:18896>. Configure your agent's OpenTelemetry exporter:

```sh
export OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:18896
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
```

The receiver supports standard OTLP/HTTP protobuf and JSON on `/v1/traces`. Spans must include the standard `gen_ai.operation.name` attribute. The brain's six labels are Visual Brain groupings—not OpenTelemetry category names—and each maps to an operation or refinement in the OpenTelemetry GenAI semantic conventions:

| Brain region | OpenTelemetry GenAI mapping |
| --- | --- |
| MODEL | `gen_ai.client.inference`, `gen_ai.client.embeddings`, `gen_ai.fetch_response.client` (`chat`, `generate_content`, `text_completion`, `realtime_inference`, `embeddings`, `fetch_response`) |
| TOOLS | `gen_ai.execute_tool` (`execute_tool`) |
| MEMORY | `gen_ai.memory.client` (`create_memory_store`, `search_memory`, `create_memory`, `update_memory`, `upsert_memory`, `delete_memory`, `delete_memory_store`) and `gen_ai.retrieval` (`retrieval`) |
| SKILLS | `gen_ai.execute_tool` with `gen_ai.skill.name`; resource reads may also include `gen_ai.skill.resource.name` |
| PLAN | `gen_ai.plan.internal` (`plan`) |
| AGENTS | `gen_ai.invoke_agent.internal`, `gen_ai.client.invoke_agent`, `gen_ai.create_agent.client` (`invoke_agent`, `create_agent`) |

These GenAI conventions are currently marked **Development** by OpenTelemetry and may evolve. See the [GenAI spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md), [agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md), and [tool/skill refinements](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/execute-tool.md). The receiver recognizes only allowlisted standard operation names and the presence—not value—of skill attributes. It no longer guesses from proprietary span names or maps generic message flow to planning. If no matching standard span is observed, the region stays **UNKNOWN**.

## Live timing limits

The UI updates as telemetry arrives. Most OpenTelemetry tracing SDKs export a span only after that operation finishes, so OTLP traces alone usually show completed work as **RECENT**, not continuously **ACTIVE** during a long call. **ACTIVE** requires an instrumentation/export path that reports in-flight lifecycle state. The optional compatibility endpoint supports explicit start/end and heartbeats for runtimes that expose those hooks; each accepted source still names the mapped GenAI semantic-convention operation. Do not mistake a completed span or a quiet feed for current activity.

## Displays and integrations

- **Browser dashboard:** built in; responsive and updated over SSE.
- **Other dashboards/widgets:** consume `GET /state` (snapshot JSON) or `GET /events` (SSE). Each SSE `data:` value is a complete state snapshot. Embed the dashboard as a same-origin iframe or create a native visualization.
- **Telegram:** host the dashboard at an authenticated HTTPS origin and open it as a Telegram Mini App/Web App. A chat message cannot contain an arbitrary interactive widget. This repo provides the web display, not a Telegram bot, hosting account, or public tunnel.
- **Any agent/harness:** use its existing OpenTelemetry instrumentation/exporter. For runtimes with lifecycle hooks but no OTLP export, the optional compatibility event API below is a minimal fallback; there is no need to adopt it when OTLP is available.
- **OpenClaw:** an optional adapter is in [`adapters/openclaw/`](adapters/openclaw/). It observes OpenClaw Gateway diagnostic events, including live starts/ends where emitted. Runtime diagnostic coverage/API can vary by OpenClaw version.

### OpenClaw Gateway install

For standard OTLP from OpenClaw, install its official exporter and point traces at this local receiver:

```sh
openclaw plugins install clawhub:@openclaw/diagnostics-otel
```

Merge these entries into the existing OpenClaw config (preserve other plugin entries and diagnostic settings):

```json5
{
  plugins: {
    allow: ["diagnostics-otel"],
    entries: { "diagnostics-otel": { enabled: true } }
  },
  diagnostics: {
    enabled: true,
    otel: {
      enabled: true,
      endpoint: "http://127.0.0.1:18896",
      protocol: "http/protobuf",
      traces: true,
      metrics: false,
      logs: false,
      sampleRate: 1.0
    }
  }
}
```

The optional `adapters/openclaw/` plugin translates supported Gateway lifecycle signals into the same mapped region/source vocabulary. Planning and memory are not inferred from message flow; they appear only when an explicit matching GenAI semantic-convention operation is instrumented. OTLP spans usually arrive at completion and show as **RECENT**. Avoid enabling duplicate sources if duplicate counts are undesirable.

## Optional event API

`POST /v1/event` is an optional Visual Brain compatibility envelope, not an OpenTelemetry endpoint. It accepts only fixed region/action/source combinations mapped to GenAI semantic conventions. For upgrade continuity, the bundled receiver also normalizes the previous OpenClaw adapter's model/tool/agent labels to their standard equivalents; it deliberately rejects its old generic message-to-planning label. New adapters should send the standard labels below:

```json
{"category":"tools","action":"start","source":"gen_ai.execute_tool"}
```

Send the same event with `"action":"end"` when it completes. Accepted standard span labels are `gen_ai.client.inference`, `gen_ai.client.embeddings`, `gen_ai.fetch_response.client`, `gen_ai.execute_tool`, `gen_ai.memory.client`, `gen_ai.retrieval`, `gen_ai.execute_tool.load_skill`, `gen_ai.execute_tool.read_skill_resource`, `gen_ai.plan.internal`, `gen_ai.invoke_agent.internal`, `gen_ai.client.invoke_agent`, and `gen_ai.create_agent.client`; each label is accepted only for its mapped region. Allowed actions are `start`, `end`, `pulse`, and `heartbeat`. A heartbeat event may include integer `active` (0–512). `POST /v1/heartbeat` accepts `{"event":"bridge-heartbeat"}`. Extra fields are rejected. See [`examples/`](examples/) for tiny Python and JavaScript fallback emitters.

## Cloud / private deployment

For a private cloud/VPS, terminate TLS and enforce viewer authentication at a trusted reverse proxy. Bind the receiver remotely only with an ingest token:

```sh
export VISUAL_BRAIN_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python3 server.py --host 0.0.0.0 --port 18896 --token "$VISUAL_BRAIN_TOKEN" --allow-remote
```

Configure the same token in OTel exporter headers (for shell environments: `export OTEL_EXPORTER_OTLP_HEADERS="Authorization=Bearer%20${VISUAL_BRAIN_TOKEN}"`) or as `Authorization: Bearer …` on compatibility POSTs. Keep viewer access behind SSO/OIDC or equivalent proxy auth; the ingest token is not a viewer login. Do not expose the receiver directly to the Internet: it does not terminate TLS, manage users, or provide tenant isolation. For Telegram Mini Apps, serve UI and API from an authenticated HTTPS deployment and validate Telegram `initData` in a trusted backend before granting a viewer session.

## Privacy and limits

- OTLP data is parsed in memory; only allowlisted GenAI operations/refinements, fixed standard span labels, counters, timestamps, and aggregate in-flight counts appear in the UI.
- Span names, attributes (including model names), resource metadata, prompts, outputs, IDs, and tool details are not copied into the public state projection.
- The recent-event ring is capped at 64; process restart clears it. Ingest request size is capped at 1 MiB.
- Local loopback is the default. Remote bind requires explicit opt-in and a bearer token. Cloud transport privacy and viewer authentication remain the operator's responsibility.
- No durability, analytics, multi-tenant separation, or external telemetry vendor is required.

## Endpoints

`GET /`, `GET /state`, `GET /events`, `GET /healthz`, `POST /v1/traces` (OTLP/HTTP), `POST /v1/event` (optional compatibility envelope), and `POST /v1/heartbeat`.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
