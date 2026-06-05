from flask import Blueprint
from ..database import get_db
from ..helpers import json_response, not_found_response

bp = Blueprint('aggregation_service', __name__)

BASE = '/redfish/v1/AggregationService'


@bp.route('/redfish/v1/AggregationService/')
def aggregation_service():
    db = get_db()
    count = db.execute('SELECT COUNT(*) FROM aggregation_sources').fetchone()[0]
    return json_response({
        '@odata.id': f'{BASE}/',
        '@odata.type': '#AggregationService.v1_0_1.AggregationService',
        'Id': 'AggregationService',
        'Name': 'Aggregation Service',
        'Description': 'Aggregation Service',
        'ServiceEnabled': True,
        'AggregationSources': {'@odata.id': f'{BASE}/AggregationSources'}
    })


@bp.route('/redfish/v1/AggregationService/AggregationSources')
def aggregation_sources():
    db = get_db()
    rows = db.execute('SELECT id FROM aggregation_sources').fetchall()
    members = [{'@odata.id': f'{BASE}/AggregationSources/{row["id"]}'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/AggregationSources',
        '@odata.type': '#AggregationSourceCollection.AggregationSourceCollection',
        'Name': 'Aggregation Source Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/AggregationService/AggregationSources/<source_id>')
def aggregation_source(source_id):
    db = get_db()
    row = db.execute('SELECT * FROM aggregation_sources WHERE id=?', (source_id,)).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/AggregationSources/{source_id}',
        '@odata.type': '#AggregationSource.v1_3_1.AggregationSource',
        'Id': row['id'],
        'Name': row['id'],
        'HostName': row['hostname'],
        'Password': None
    })
