"""Optional compatibility emitter mapping to GenAI convention span labels."""
import json
import os
import urllib.request
from contextlib import contextmanager

ENDPOINT = os.getenv('VISUAL_BRAIN_ENDPOINT', 'http://127.0.0.1:18896').rstrip('/')
TOKEN = os.getenv('VISUAL_BRAIN_TOKEN')


def emit(category, action, source):
    body = json.dumps({'category': category, 'action': action, 'source': source}).encode()
    headers = {'Content-Type': 'application/json'}
    if TOKEN:
        headers['Authorization'] = f'Bearer {TOKEN}'
    request = urllib.request.Request(ENDPOINT + '/v1/event', data=body, headers=headers)
    try:
        urllib.request.urlopen(request, timeout=1).close()
    except Exception:
        # Observability must not break the agent's actual operation.
        pass


@contextmanager
def operation(category, source):
    emit(category, 'start', source)
    try:
        yield
    finally:
        emit(category, 'end', source)


if __name__ == '__main__':
    with operation('model', 'gen_ai.client.inference'):
        print('Replace this block with your model invocation.')
