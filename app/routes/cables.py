from flask import Blueprint
from ..database import get_db
from ..helpers import json_response, not_found_response

bp = Blueprint('cables', __name__)


@bp.route('/redfish/v1/Cables/')
def cables():
    db = get_db()
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


@bp.route('/redfish/v1/Cables/<cable_id>/')
def cable(cable_id):
    db = get_db()
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
