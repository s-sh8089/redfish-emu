import asyncio
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Body, Request
from sse_starlette.sse import EventSourceResponse
from ..database import get_db
from ..auth import verify_auth
from ..helpers import json_response, not_found_response, bad_request_response, created_response, no_content_response
from ..event_dispatcher import dispatch_event, add_sse_client, remove_sse_client

router = APIRouter(dependencies=[Depends(verify_auth)])


@router.get('/redfish/v1/EventService/')
def event_service(db: sqlite3.Connection = Depends(get_db)):
    count = db.execute('SELECT COUNT(*) FROM event_subscriptions').fetchone()[0]
    return json_response({
        '@odata.id': '/redfish/v1/EventService/',
        '@odata.type': '#EventService.v1_7_0.EventService',
        'Id': 'EventService',
        'Name': 'Event Service',
        'ServiceEnabled': True,
        'DeliveryRetryAttempts': 3,
        'DeliveryRetryIntervalSeconds': 60,
        'EventFormatTypes': ['Event', 'MetricReport'],
        'RegistryPrefixes': ['Base', 'OpenBMC', 'TaskEvent'],
        'ResourceTypes': [],
        'SSEFilterPropertiesSupported': {
            'EventFormatType': True,
            'MessageId': True,
            'MetricReportDefinition': True,
            'OriginResource': True,
            'RegistryPrefix': True,
            'ResourceType': True,
            'SubordinateResources': True
        },
        'ServerSentEventUri': '/redfish/v1/EventService/SSE',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'Subscriptions': {'@odata.id': '/redfish/v1/EventService/Subscriptions/'},
        'Actions': {
            '#EventService.SubmitTestEvent': {
                'target': '/redfish/v1/EventService/Actions/EventService.SubmitTestEvent'
            }
        }
    })


@router.get('/redfish/v1/EventService/Subscriptions/')
def subscriptions_get(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute('SELECT id FROM event_subscriptions').fetchall()
    members = [{'@odata.id': f'/redfish/v1/EventService/Subscriptions/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': '/redfish/v1/EventService/Subscriptions/',
        '@odata.type': '#EventDestinationCollection.EventDestinationCollection',
        'Name': 'Event Subscriptions Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@router.post('/redfish/v1/EventService/Subscriptions/')
def subscriptions_post(
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    data = body or {}
    if not data or 'Destination' not in data:
        return bad_request_response('Destination is required.')
    sub_id = str(uuid.uuid4()).replace('-', '')[:12]
    db.execute(
        '''INSERT INTO event_subscriptions
           (id, destination, context, protocol, event_types, origin_resources, registry_prefixes, message_ids, resource_types)
           VALUES (?,?,?,?,?,?,?,?,?)''',
        (sub_id, data['Destination'], data.get('Context', ''),
         data.get('Protocol', 'Redfish'),
         json.dumps(data.get('EventTypes', [])),
         json.dumps(data.get('OriginResources', [])),
         json.dumps(data.get('RegistryPrefixes', [])),
         json.dumps(data.get('MessageIds', [])),
         json.dumps(data.get('ResourceTypes', [])))
    )
    db.commit()
    row = db.execute('SELECT * FROM event_subscriptions WHERE id=?', (sub_id,)).fetchone()
    return created_response(
        _subscription_to_dict(row),
        location=f'/redfish/v1/EventService/Subscriptions/{sub_id}/'
    )


@router.get('/redfish/v1/EventService/Subscriptions/{sub_id}/')
def subscription_get(sub_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM event_subscriptions WHERE id=?', (sub_id,)).fetchone()
    if not row:
        return not_found_response()
    return json_response(_subscription_to_dict(row))


@router.patch('/redfish/v1/EventService/Subscriptions/{sub_id}/')
def subscription_patch(
    sub_id: str,
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    row = db.execute('SELECT * FROM event_subscriptions WHERE id=?', (sub_id,)).fetchone()
    if not row:
        return not_found_response()
    data = body or {}
    fields, values = [], []
    if 'Context' in data:
        fields.append('context=?'); values.append(data['Context'])
    if 'EventTypes' in data:
        fields.append('event_types=?'); values.append(json.dumps(data['EventTypes']))
    if 'OriginResources' in data:
        fields.append('origin_resources=?'); values.append(json.dumps(data['OriginResources']))
    if 'RegistryPrefixes' in data:
        fields.append('registry_prefixes=?'); values.append(json.dumps(data['RegistryPrefixes']))
    if 'MessageIds' in data:
        fields.append('message_ids=?'); values.append(json.dumps(data['MessageIds']))
    if 'ResourceTypes' in data:
        fields.append('resource_types=?'); values.append(json.dumps(data['ResourceTypes']))
    if fields:
        values.append(sub_id)
        db.execute(f'UPDATE event_subscriptions SET {", ".join(fields)} WHERE id=?', values)
        db.commit()
    row = db.execute('SELECT * FROM event_subscriptions WHERE id=?', (sub_id,)).fetchone()
    return json_response(_subscription_to_dict(row))


@router.delete('/redfish/v1/EventService/Subscriptions/{sub_id}/')
def subscription_delete(sub_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM event_subscriptions WHERE id=?', (sub_id,)).fetchone():
        return not_found_response()
    db.execute('DELETE FROM event_subscriptions WHERE id=?', (sub_id,))
    db.commit()
    return no_content_response()


@router.post('/redfish/v1/EventService/Actions/EventService.SubmitTestEvent')
async def submit_test_event(body: dict | None = Body(default=None)):
    data = body or {}
    event_id = str(uuid.uuid4()).replace('-', '')[:8]
    now = datetime.now(timezone.utc).isoformat()
    event_payload = {
        '@odata.type': '#Event.v1_7_0.Event',
        'Id': event_id,
        'Name': 'Test Event',
        'Context': data.get('Context', ''),
        'Events': [{
            'EventType': data.get('EventType', 'Alert'),
            'EventId': event_id,
            'EventTimestamp': now,
            'Severity': data.get('Severity', 'OK'),
            'Message': data.get('Message', 'This is a test event.'),
            'MessageId': data.get('MessageId', 'Base.1.0.GeneralError'),
            'MessageArgs': data.get('MessageArgs', []),
            'OriginOfCondition': {'@odata.id': data.get('OriginOfCondition', '/redfish/v1/')}
        }]
    }
    await dispatch_event(event_payload)
    return no_content_response()


@router.get('/redfish/v1/EventService/SSE')
async def sse_stream(request: Request):
    q = await add_sse_client()

    async def generator():
        try:
            yield {'comment': 'Redfish SSE stream'}
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield {'data': json.dumps(event)}
                except asyncio.TimeoutError:
                    yield {'comment': 'heartbeat'}
        finally:
            await remove_sse_client(q)

    return EventSourceResponse(generator(), headers={'OData-Version': '4.0'})


def _subscription_to_dict(row) -> dict:
    event_types = json.loads(row['event_types']) if row['event_types'] else []
    origin_resources = json.loads(row['origin_resources']) if row['origin_resources'] else []
    registry_prefixes = json.loads(row['registry_prefixes']) if row['registry_prefixes'] else []
    message_ids = json.loads(row['message_ids']) if row['message_ids'] else []
    resource_types = json.loads(row['resource_types']) if row['resource_types'] else []
    return {
        '@odata.id': f'/redfish/v1/EventService/Subscriptions/{row["id"]}/',
        '@odata.type': '#EventDestination.v1_13_0.EventDestination',
        'Id': row['id'],
        'Name': f'Event Subscription {row["id"]}',
        'Destination': row['destination'],
        'Context': row['context'] or '',
        'Protocol': row['protocol'],
        'EventTypes': event_types,
        'OriginResources': origin_resources,
        'RegistryPrefixes': registry_prefixes,
        'MessageIds': message_ids,
        'ResourceTypes': resource_types,
    }
