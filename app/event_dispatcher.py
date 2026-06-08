import json
import queue
import threading
import urllib.request
import urllib.error

_sse_clients = []
_sse_lock = threading.Lock()


def add_sse_client():
    q = queue.Queue(maxsize=100)
    with _sse_lock:
        _sse_clients.append(q)
    return q


def remove_sse_client(q):
    with _sse_lock:
        try:
            _sse_clients.remove(q)
        except ValueError:
            pass


def _broadcast_to_sse(event_data):
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(event_data)
            except queue.Full:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


def dispatch_event(app, event_data):
    thread = threading.Thread(
        target=_send_to_subscribers,
        args=(app, event_data),
        daemon=True
    )
    thread.start()


def _send_to_subscribers(app, event_data):
    _broadcast_to_sse(event_data)
    with app.app_context():
        from .database import get_db
        db = get_db()
        rows = db.execute('SELECT * FROM event_subscriptions').fetchall()
        for row in rows:
            if not _matches_filter(row, event_data):
                continue
            _post_event(row['destination'], event_data)


def _matches_filter(row, event_data):
    event_types = json.loads(row['event_types']) if row['event_types'] else []
    if not event_types:
        return True
    events = event_data.get('Events', [])
    if not events:
        return True
    return events[0].get('EventType', '') in event_types


def _post_event(destination, event_data):
    try:
        payload = json.dumps(event_data).encode('utf-8')
        req = urllib.request.Request(
            destination,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception:
        pass
