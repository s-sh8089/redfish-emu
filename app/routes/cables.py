import sqlite3
from fastapi import APIRouter, Depends
from ..database import get_db
from ..auth import verify_auth
from ..helpers import json_response, not_found_response

router = APIRouter(dependencies=[Depends(verify_auth)])


@router.get('/redfish/v1/Cables/')
def cables(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute('SELECT id FROM cables').fetchall()
    members = [{'@odata.id': f'/redfish/v1/Cables/{row["id"]}/'} for row in rows]
    return json_response({
        '@odata.id': '/redfish/v1/Cables/',
        '@odata.type': '#CableCollection.CableCollection',
        'Name': 'Cable Collection',
        'Description': 'List of cables',
        'Members@odata.count': len(members),
        'Members': members
    })


@router.get('/redfish/v1/Cables/{cable_id}/')
def cable(cable_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM cables WHERE id=?', (cable_id,)).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'/redfish/v1/Cables/{cable_id}/',
        '@odata.type': '#Cable.v1_2_0.Cable',
        'Id': row['id'],
        'Name': row['id'],
        'CableType': row['cable_type'],
        'LengthMeters': row['length_meters']
    })
