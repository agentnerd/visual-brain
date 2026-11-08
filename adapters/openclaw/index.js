import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { onInternalDiagnosticEvent } from "openclaw/plugin-sdk/diagnostic-runtime";

const ENDPOINT = process.env.VISUAL_BRAIN_ENDPOINT || 'http://127.0.0.1:18896';
const TOKEN = process.env.VISUAL_BRAIN_TOKEN;
const MAX_ACTIVE = 512;
const ACTIVE_TTL_MS = { model: 10 * 60_000, tools: 20 * 60_000, agents: 15 * 60_000, skills: 2 * 60_000, planning: 2 * 60_000 };
const EVENT_TYPES = [
  'model.call.started', 'model.call.completed', 'model.call.error',
  'tool.execution.started', 'tool.execution.completed', 'tool.execution.error', 'tool.execution.blocked',
  'skill.used', 'run.started', 'run.completed', 'run.progress', 'run.execution_phase',
  'harness.run.started', 'harness.run.completed', 'harness.run.error',
];

export default definePluginEntry({
  id: 'visual-brain-telemetry',
  name: 'Visual Brain Telemetry',
  register(api) {
    if (api.registrationMode !== 'full') return;
    const active = new Map();
    const categorySource = {
      model: 'gen_ai.client.inference', tools: 'gen_ai.execute_tool',
      skills: 'gen_ai.execute_tool.load_skill', agents: 'gen_ai.invoke_agent.internal',
      planning: 'gen_ai.plan.internal',
    };
    const inFlight = new Map(Object.keys(categorySource).map((category) => [category, new Map()]));
    let sequence = 0;
    let pending = 0;

    function post(path, payload) {
      if (pending >= 64) return;
      pending++;
      void fetch(`${ENDPOINT}${path}`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', ...(TOKEN ? { authorization: `Bearer ${TOKEN}` } : {}) },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(750),
      }).catch(() => {}).finally(() => { pending--; });
    }

    function event(category, action, source = categorySource[category]) {
      post('/v1/event', { category, action, source });
    }

    function start(category, key) {
      if (!key || active.has(key)) return;
      if (active.size >= MAX_ACTIVE) return;
      const now = Date.now();
      active.set(key, { category, lastSeen: now });
      inFlight.get(category).set(key, now);
      event(category, 'start');
    }

    function end(category, key) {
      if (key && active.get(key)?.category === category) {
        active.delete(key);
        inFlight.get(category).delete(key);
        event(category, 'end');
      } else {
        event(category, 'pulse');
      }
    }

    function pulse(category, refreshActive = false) {
      event(category, 'pulse');
      if (refreshActive) {
        const now = Date.now();
        for (const [key, state] of active) {
          if (state.category !== category) continue;
          state.lastSeen = now;
          inFlight.get(category).set(key, now);
        }
      }
    }

    const unsubscribe = onInternalDiagnosticEvent((evt) => {
      if (!evt || typeof evt.type !== 'string') return;
      switch (evt.type) {
        case 'model.call.started':
          start('model', `model:${evt.agentId || ''}:${evt.runId || ''}:${evt.callId}`);
          break;
        case 'model.call.completed':
        case 'model.call.error':
          end('model', `model:${evt.agentId || ''}:${evt.runId || ''}:${evt.callId}`);
          break;
        case 'tool.execution.started': {
          const scope = `${evt.runId || evt.sessionId || 'run'}:${evt.agentId || ''}:`;
          const id = evt.toolCallId ? `${scope}${evt.toolCallId}` : `${scope}${evt.toolName}:${++sequence}`;
          start('tools', `tool:${id}`);
          break;
        }
        case 'tool.execution.completed':
        case 'tool.execution.error':
          if (evt.toolCallId) end('tools', `tool:${evt.runId || evt.sessionId || 'run'}:${evt.agentId || ''}:${evt.toolCallId}`);
          else {
            const prefix = `tool:${evt.runId || evt.sessionId || 'run'}:${evt.agentId || ''}:${evt.toolName}:`;
            const key = [...inFlight.get('tools')].find((candidate) => candidate.startsWith(prefix));
            end('tools', key);
          }
          break;
        case 'tool.execution.blocked':
          pulse('tools');
          break;
        case 'skill.used':
          if (evt.activation === 'read') {
            event('skills', 'pulse', 'gen_ai.execute_tool.read_skill_resource');
          } else {
            event('tools', 'pulse');
          }
          break;
        case 'run.started':
        case 'harness.run.started':
          start('agents', `agent:${evt.runId || evt.sessionId || evt.sessionKey || 'run'}:${evt.harnessId || ''}:${evt.type}`);
          break;
        case 'run.completed':
        case 'harness.run.completed':
        case 'harness.run.error':
          end('agents', `agent:${evt.runId || evt.sessionId || evt.sessionKey || 'run'}:${evt.harnessId || ''}:${evt.type.replace(/\.(completed|error)$/, '.started')}`);
          break;
        case 'run.progress':
        case 'run.execution_phase':
          pulse('agents', true);
          break;
        default:
          break;
      }
    }, { include: EVENT_TYPES, includeTrusted: EVENT_TYPES });

    const heartbeat = setInterval(() => {
      if (pending < 64) {
        post('/v1/heartbeat', { event: 'bridge-heartbeat' });
        const now = Date.now();
        for (const [key, state] of active) {
          if (now - state.lastSeen <= ACTIVE_TTL_MS[state.category]) continue;
          active.delete(key);
          inFlight.get(state.category).delete(key);
        }
        for (const [category, keys] of inFlight) {
          post('/v1/event', { category, action: 'heartbeat', source: categorySource[category], active: keys.size });
        }
      }
    }, 2500);
    heartbeat.unref();
    post('/v1/heartbeat', { event: 'bridge-heartbeat' });

    api.lifecycle?.onDispose?.(() => {
      clearInterval(heartbeat);
      unsubscribe();
    });
  },
});
