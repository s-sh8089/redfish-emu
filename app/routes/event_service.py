import json
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request, current_app
from ..database import get_db
from ..helpers import json_response, not_found_response, bad_request_response, created_response, no_content_response
from ..event_dispatcher import dispatch_event

bp = Blueprint('event_service', __name__)


@bp.route('/redfish/v1/EventService/')
def event_service():
    db = get_db()
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
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'Subscriptions': {'@odata.id': '/redfish/v1/EventService/Subscriptions/'},
        'Actions': {
            '#EventService.SubmitTestEvent': {
                'target': '/redfish/v1/EventService/Actions/EventService.SubmitTestEvent'
            }
        }
    })


@bp.route('/redfish/v1/EventService/Subscriptions/', methods=['GET', 'POST'])
def subscriptions():
    db = get_db()
    if request.method == 'GET':
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
    else:
        data = request.get_json()
        if not data or 'Destination' not in data:
            return bad_request_response('Destination is required.')
        sub_id = str(uuid.uuid4()).replace('-', '')[:12]
        db.execute(
            'INSERT INTO event_subscriptions (id, destination, context, protocol, event_types, origin_resources) VALUES (?,?,?,?,?,?)',
            (sub_id, data['Destination'], data.get('Context', ''),
             data.get('Protocol', 'Redfish'),
             json.dumps(data.get('EventTypes', [])),
             json.dumps(data.get('OriginResources', [])))
        )
        db.commit()
        row = db.execute('SELECT * FROM event_subscriptions WHERE id=?', (sub_id,)).fetchone()
        return created_response(
            _subscription_to_dict(row),
            location=f'/redfish/v1/EventService/Subscriptions/{sub_id}/'
        )


@bp.route('/redfish/v1/EventService/Subscriptions/<sub_id>/', methods=['GET', 'DELETE'])
def subscription(sub_id):
    db = get_db()
    row = db.execute('SELECT * FROM event_subscriptions WHERE id=?', (sub_id,)).fetchone()
    if not row:
        return not_found_response()
    if request.method == 'GET':
        return json_response(_subscription_to_dict(row))
    else:
        db.execute('DELETE FROM event_subscriptions WHERE id=?', (sub_id,))
        db.commit()
        return no_content_response()


@bp.route('/redfish/v1/EventService/Actions/EventService.SubmitTestEvent', methods=['POST'])
def submit_test_event():
    data = request.get_json() or {}
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

    dispatch_event(current_app._get_current_object(), event_payload)
    return no_content_response()


def _subscription_to_dict(row):
    event_types = json.loads(row['event_types']) if row['event_types'] else []
    origin_resources = json.loads(row['origin_resources']) if row['origin_resources'] else []
    return {
        '@odata.id': f'/redfish/v1/EventService/Subscriptions/{row["id"]}/',
        '@odata.type': '#EventDestination.v1_13_0.EventDestination',
        'Id': row['id'],
        'Name': f'Event Subscription {row["id"]}',
        'Destination': row['destination'],
        'Context': row['context'] or '',
        'Protocol': row['protocol'],
        'EventTypes': event_types,
        'OriginResources': origin_resources
    }
