// Tiny dependency-free emitter. Never attach prompts, results, or runtime IDs.
const endpoint = (process.env.VISUAL_BRAIN_ENDPOINT || 'http://127.0.0.1:18896').replace(/\/$/, '');

export async function emit(category, action, source) {
  try {
    await fetch(`${endpoint}/v1/event`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        ...(process.env.VISUAL_BRAIN_TOKEN ? { authorization: `Bearer ${process.env.VISUAL_BRAIN_TOKEN}` } : {}),
      },
      body: JSON.stringify({ category, action, source }),
      signal: AbortSignal.timeout(1000),
    });
  } catch {
    // Telemetry is best-effort and never blocks agent execution.
  }
}

export async function observe(category, source, fn) {
  await emit(category, 'start', source);
  try { return await fn(); }
  finally { await emit(category, 'end', source); }
}
