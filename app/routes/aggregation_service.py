import sqlite3
from fastapi import APIRouter, Depends
from ..database import get_db
from ..auth import verify_auth
from ..helpers import json_response, not_found_response

router = APIRouter(dependencies=[Depends(verify_auth)])

BASE = '/redfish/v1/AggregationService'


@router.get('/redfish/v1/AggregationService/')
def aggregation_service(db: sqlite3.Connection = Depends(get_db)):
    return json_response({
        '@odata.id': f'{BASE}/',
        '@odata.type': '#AggregationService.v1_0_1.AggregationService',
        'Id': 'AggregationService',
        'Name': 'Aggregation Service',
        'Description': 'Aggregation Service',
        'ServiceEnabled': True,
        'AggregationSources': {'@odata.id': f'{BASE}/AggregationSources'}
    })


@router.get('/redfish/v1/AggregationService/AggregationSources')
def aggregation_sources(db: sqlite3.Connection = Depends(get_db)):
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


@router.get('/redfish/v1/AggregationService/AggregationSources/{source_id}')
def aggregation_source(source_id: str, db: sqlite3.Connection = Depends(get_db)):
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
