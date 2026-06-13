import asyncio
import json
import os
import sqlite3
import urllib.request

_DB_PATH = os.environ.get('DB_PATH', 'data/redfish.db')

_sse_clients: list[asyncio.Queue] = []
_sse_lock = asyncio.Lock()


async def add_sse_client() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    async with _sse_lock:
        _sse_clients.append(q)
    return q


async def remove_sse_client(q: asyncio.Queue) -> None:
    async with _sse_lock:
        try:
            _sse_clients.remove(q)
        except ValueError:
            pass


async def _broadcast_to_sse(event_data: dict) -> None:
    async with _sse_lock:
        for q in list(_sse_clients):
            try:
                q.put_nowait(event_data)
            except asyncio.QueueFull:
                pass


async def dispatch_event(event_data: dict) -> None:
    """Broadcast to SSE clients immediately, then deliver webhooks in background."""
    await _broadcast_to_sse(event_data)
    asyncio.create_task(_deliver_webhooks(event_data))


async def _deliver_webhooks(event_data: dict) -> None:
    await asyncio.to_thread(_send_to_subscribers, event_data)


def _send_to_subscribers(event_data: dict) -> None:
    db = sqlite3.connect(_DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        rows = db.execute('SELECT * FROM event_subscriptions').fetchall()
        for row in rows:
            if _matches_filter(row, event_data):
                _post_event(row['destination'], event_data)
    finally:
        db.close()


def _matches_filter(row, event_data: dict) -> bool:
    event_types = json.loads(row['event_types']) if row['event_types'] else []
    if not event_types:
        return True
    events = event_data.get('Events', [])
    if not events:
        return True
    return events[0].get('EventType', '') in event_types


def _post_event(destination: str, event_data: dict) -> None:
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
