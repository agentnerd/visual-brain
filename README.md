# Visual Brain

**A harness-agnostic live activity display for AI agents.** Small agents, tools, and harness adapters send content-free lifecycle events to one receiver. The receiver exposes a web brain, JSON state, and Server-Sent Events (SSE), so other dashboards and widgets can share the same stream.

It visualizes observable execution—not model thoughts. It never needs prompts, completions, tool arguments/results, or private reasoning.

## Quick start

Requires Python 3.10+; no third-party packages.

```sh
python3 server.py
```

Open <http://127.0.0.1:18896>. Send an event from any runtime:

```sh
curl -X POST http://127.0.0.1:18896/v1/event \
  -H 'Content-Type: application/json' \
  -d '{"category":"model","action":"start","source":"model.call"}'
```

Finish the operation by sending the same event with `"action":"end"`. See [`examples/`](examples/) for Python and JavaScript emitters. Use only the fixed event fields and source names below; never put user data or runtime IDs in them.

## Portable event contract

`POST /v1/event` accepts a bounded JSON object:

```json
{"category":"tools","action":"start","source":"tool.execution"}
```

| Category | Allowed source | Typical lifecycle |
|---|---|---|
| `model` | `model.call` | `start`, `end`, `pulse` |
| `tools` | `tool.execution` | `start`, `end`, `pulse` |
| `memory` | `memory.access` | `pulse` |
| `skills` | `skill.use` | `pulse` |
| `planning` | `agent.phase` | `pulse` |
| `agents` | `agent.run` | `start`, `end`, `pulse` |

`/v1/heartbeat` accepts `{"event":"bridge-heartbeat"}`. For long operations, `action:"heartbeat"` with an integer `active` count (0–512) keeps active state accurate without manufacturing event rows. The receiver rejects extra fields. Region states are `ACTIVE`, `INACTIVE`, or `UNKNOWN`; unknown means no event observed, not proof that no work happened.

## Displays and integrations

- **Browser dashboard:** built in; responsive and updated over SSE.
- **Other dashboards/widgets:** consume `GET /state` (snapshot JSON) or `GET /events` (SSE). Each SSE `data:` value is a complete state snapshot. Embed the dashboard as a same-origin iframe or recreate the visualization with any frontend.
- **Telegram:** host the dashboard at an authenticated HTTPS origin and open it as a Telegram Mini App/Web App. A chat message cannot contain an arbitrary interactive widget. This repo provides the web component endpoint, not a Telegram bot, hosting account, or public tunnel.
- **Any agent/harness:** implement the small HTTP contract using a native hook, middleware, callback, or wrapper. Example emitters are dependency-free. Events may originate from different agents and languages and feed one collector.
- **OpenClaw:** an optional observer is in [`adapters/openclaw/`](adapters/openclaw/). It uses OpenClaw's exported plugin SDK and runtime diagnostic stream; runtime diagnostic coverage/API can vary by OpenClaw version. This is one adapter, not a core requirement.

## Local and cloud deployment

Local loopback is the default and needs no credentials. For a private cloud/VPS, terminate TLS and enforce viewer authentication at a trusted reverse proxy. Bind the receiver remotely only with an ingest token:

```sh
export VISUAL_BRAIN_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
python3 server.py --host 0.0.0.0 --port 18896 --token "$VISUAL_BRAIN_TOKEN" --allow-remote
```

Configure the same token as `Authorization: Bearer …` on agent POSTs. Keep viewer access behind SSO/OIDC or equivalent reverse-proxy auth; the ingest token is not a viewer login. Do not expose the receiver directly to the Internet: it does not terminate TLS, manage users, or provide tenant isolation. For Telegram Mini Apps, serve the UI and API from the authenticated HTTPS deployment and validate Telegram `initData` in your own trusted backend before granting a viewer session.

## Privacy and limits

- Event schema intentionally excludes content, names, IDs, provider/model labels, and arbitrary attributes.
- The in-memory recent-event ring is capped at 64; process restart clears it.
- Ingest requests are size-limited. The remote bind requires explicit opt-in and a bearer token.
- Do not send identifiers in event fields or attach this receiver to an untrusted network. Transport privacy and viewer authorization for cloud are the operator's responsibility.
- `UNKNOWN` is the honest fallback when an adapter cannot observe a category. The display does not infer memory access, planning, or activity from silence.
- No durability, analytics, multi-tenant separation, or external telemetry vendor is required.

## Run locally

```sh
python3 server.py --host 127.0.0.1 --port 18896
```

Endpoints: `GET /`, `GET /state`, `GET /events`, `GET /healthz`, `POST /v1/event`, and `POST /v1/heartbeat`.

## License

Apache-2.0. See [`LICENSE`](LICENSE).
