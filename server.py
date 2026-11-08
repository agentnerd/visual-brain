"""Small content-minimizing receiver for Visual Brain events."""
import argparse
import collections
import hmac
import json
import pathlib
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CATEGORIES = ('model', 'tools', 'memory', 'skills', 'planning', 'agents')
SOURCES = {'model': 'model.call', 'tools': 'tool.execution', 'memory': 'memory.access',
           'skills': 'skill.use', 'planning': 'agent.phase', 'agents': 'agent.run'}


class Brain:
    def __init__(self):
        self.lock = threading.RLock()
        self.changed = threading.Condition(self.lock)
        self.counts = collections.Counter()
        self.last = {}
        self.active = collections.Counter()
        self.active_seen = {}
        self.bridge_seen = 0.0
        self.events = collections.deque(maxlen=64)
        self.revision = 0

    def observe(self, category, source, action='pulse', active=None):
        with self.changed:
            now = time.time()
            self.bridge_seen = now
            if action == 'start':
                self.counts[category] += 1
                self.active[category] = min(512, self.active[category] + 1)
                self.last[category] = now
                self.active_seen[category] = now
            elif action == 'end':
                self.counts[category] += 1
                self.active[category] = max(0, self.active[category] - 1)
                self.last[category] = now
                self.active_seen[category] = now
            elif action == 'heartbeat':
                self.active[category] = active
                self.active_seen[category] = now
            else:
                self.counts[category] += 1
                self.last[category] = now
            if action != 'heartbeat':
                self.events.append({'category': category, 'source': source, 'action': action, 'at': round(now, 3)})
            self.revision += 1
            self.changed.notify_all()

    def snapshot(self):
        with self.lock:
            now = time.time()
            for category, seen in list(self.active_seen.items()):
                if now - seen > 10:
                    self.active[category] = 0
            return {
                'regions': {category: {
                    'state': 'ACTIVE' if self.active[category] > 0 or now - self.last.get(category, 0) < 6 else ('INACTIVE' if category in self.last else 'UNKNOWN'),
                    'count': self.counts[category], 'active': self.active[category],
                } for category in CATEGORIES},
                'events': list(self.events),
                'bridge': 'CONNECTED' if now - self.bridge_seen < 10 else 'DISCONNECTED',
                'scope': 'Observed lifecycle metadata only; private content is not collected.',
            }


def serve(host='127.0.0.1', port=18896, token=None, allow_remote=False):
    if host not in ('127.0.0.1', 'localhost', '::1') and (not allow_remote or not token):
        raise SystemExit('Remote bind requires --allow-remote and --token; put TLS and viewer authentication in a trusted reverse proxy.')
    brain = Brain()

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    class Handler(BaseHTTPRequestHandler):
        protocol_version = 'HTTP/1.1'

        def log_message(self, *_args):
            pass

        def respond(self, status, payload, content_type='application/json'):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            if self.path == '/v1/heartbeat':
                if token and not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
                    return self.respond(401, {'error': 'unauthorized'})
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    payload = json.loads(self.rfile.read(length)) if 0 < length <= 4096 else None
                    if payload != {'event': 'bridge-heartbeat'}:
                        raise ValueError()
                    with brain.changed:
                        brain.bridge_seen = time.time()
                        brain.revision += 1
                        brain.changed.notify_all()
                    return self.respond(202, {})
                except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
                    return self.respond(400, {'error': 'invalid heartbeat'})
            if self.path != '/v1/event':
                return self.respond(404, {'error': 'not found'})
            if token and not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
                return self.respond(401, {'error': 'unauthorized'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.respond(415, {'error': 'application/json required'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                payload = json.loads(self.rfile.read(length)) if 0 < length <= 4096 else None
                if not isinstance(payload, dict) or not set(payload) <= {'category', 'action', 'source', 'active'} or not {'category', 'action', 'source'} <= set(payload):
                    raise ValueError()
                category, action, source = payload['category'], payload['action'], payload['source']
                if category not in CATEGORIES or source != SOURCES[category] or action not in ('start', 'end', 'pulse', 'heartbeat'):
                    raise ValueError()
                if action == 'heartbeat':
                    if set(payload) != {'category', 'action', 'source', 'active'} or type(payload['active']) is not int or not 0 <= payload['active'] <= 512:
                        raise ValueError()
                elif set(payload) != {'category', 'action', 'source'}:
                    raise ValueError()
                brain.observe(category, source, action, payload.get('active'))
                return self.respond(202, {})
            except (ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
                return self.respond(400, {'error': 'invalid event'})

        def do_GET(self):
            if self.path == '/state':
                return self.respond(200, brain.snapshot())
            if self.path == '/events':
                self.send_response(200)
                self.send_header('Content-Type', 'text/event-stream')
                self.send_header('Cache-Control', 'no-cache, no-transform')
                self.send_header('Connection', 'keep-alive')
                self.send_header('X-Accel-Buffering', 'no')
                self.end_headers()
                previous = None
                try:
                    while True:
                        state = json.dumps(brain.snapshot(), separators=(',', ':'))
                        if state != previous:
                            self.wfile.write(('data: ' + state + '\n\n').encode())
                            self.wfile.flush()
                            previous = state
                        time.sleep(0.75)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    return
            if self.path == '/':
                return self.respond(200, pathlib.Path(__file__).with_name('index.html').read_bytes(), 'text/html; charset=utf-8')
            if self.path == '/healthz':
                return self.respond(200, {'status': 'ok'})
            return self.respond(404, {'error': 'not found'})

    httpd = Server((host, port), Handler)
    print(f'Visual Brain listening on http://{host}:{port}', flush=True)
    try:
        httpd.serve_forever()
    finally:
        httpd.server_close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Visual Brain event receiver and browser display')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=18896)
    parser.add_argument('--token', default=None)
    parser.add_argument('--allow-remote', action='store_true')
    args = parser.parse_args()
    serve(args.host, args.port, args.token, args.allow_remote)
