import uuid
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request
from ..database import get_db
from ..helpers import json_response, not_found_response, bad_request_response, created_response, no_content_response
from ..auth import _check_password, _increment_failure, SESSION_TIMEOUT_MINUTES

bp = Blueprint('session_service', __name__)


@bp.route('/redfish/v1/SessionService/')
def session_service():
    return json_response({
        '@odata.id': '/redfish/v1/SessionService/',
        '@odata.type': '#SessionService.v1_1_8.SessionService',
        'Id': 'SessionService',
        'Name': 'Session Service',
        'Description': 'Session Service',
        'ServiceEnabled': True,
        'SessionTimeout': SESSION_TIMEOUT_MINUTES * 60,
        'Sessions': {'@odata.id': '/redfish/v1/SessionService/Sessions/'}
    })


@bp.route('/redfish/v1/SessionService/Sessions/', methods=['GET', 'POST'])
def sessions():
    db = get_db()
    if request.method == 'GET':
        _purge_expired_sessions(db)
        rows = db.execute('SELECT id FROM sessions').fetchall()
        members = [{'@odata.id': f'/redfish/v1/SessionService/Sessions/{row["id"]}/'}
                   for row in rows]
        return json_response({
            '@odata.id': '/redfish/v1/SessionService/Sessions/',
            '@odata.type': '#SessionCollection.SessionCollection',
            'Name': 'Session Collection',
            'Description': 'List of active sessions',
            'Members@odata.count': len(members),
            'Members': members
        })

    data = request.get_json()
    if not data or 'UserName' not in data or 'Password' not in data:
        return bad_request_response('UserName and Password are required.')

    account = db.execute(
        'SELECT * FROM accounts WHERE username=? AND enabled=1',
        (data['UserName'],)
    ).fetchone()
    if not account:
        return bad_request_response('Invalid credentials.')
    if account['locked']:
        return bad_request_response('Account is locked.')
    if not _check_password(data['Password'], account['password']):
        _increment_failure(db, account['id'])
        return bad_request_response('Invalid credentials.')

    db.execute('UPDATE accounts SET login_failure_count=0 WHERE id=?', (account['id'],))

    session_id = str(uuid.uuid4()).replace('-', '')[:16]
    token = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    client_ip = request.remote_addr or '127.0.0.1'

    db.execute(
        'INSERT INTO sessions (id, username, token, client_origin_ip, created_at) VALUES (?,?,?,?,?)',
        (session_id, data['UserName'], token, client_ip, now)
    )
    db.commit()

    session_data = {
        '@odata.id': f'/redfish/v1/SessionService/Sessions/{session_id}/',
        '@odata.type': '#Session.v1_6_0.Session',
        'Id': session_id,
        'Name': 'User Session',
        'UserName': data['UserName'],
        'ClientOriginIPAddress': client_ip,
        'Description': 'User Session',
        'Oem': {}
    }
    resp = created_response(session_data, location=f'/redfish/v1/SessionService/Sessions/{session_id}/')
    resp.headers['X-Auth-Token'] = token
    return resp


@bp.route('/redfish/v1/SessionService/Sessions/<session_id>/', methods=['GET', 'DELETE'])
def session(session_id):
    db = get_db()
    row = db.execute('SELECT * FROM sessions WHERE id=?', (session_id,)).fetchone()
    if not row:
        return not_found_response()

    # Check timeout
    created = datetime.fromisoformat(row['created_at'])
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        db.execute('DELETE FROM sessions WHERE id=?', (session_id,))
        db.commit()
        return not_found_response()

    if request.method == 'GET':
        return json_response({
            '@odata.id': f'/redfish/v1/SessionService/Sessions/{session_id}/',
            '@odata.type': '#Session.v1_6_0.Session',
            'Id': session_id,
            'Name': 'User Session',
            'UserName': row['username'],
            'ClientOriginIPAddress': row['client_origin_ip'] or '',
            'Description': 'User Session',
            'Oem': {}
        })
    else:
        db.execute('DELETE FROM sessions WHERE id=?', (session_id,))
        db.commit()
        return no_content_response()


def _purge_expired_sessions(db):
    rows = db.execute('SELECT id, created_at FROM sessions').fetchall()
    expired = []
    for row in rows:
        try:
            created = datetime.fromisoformat(row['created_at'])
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - created > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
                expired.append(row['id'])
        except Exception:
            pass
    if expired:
        db.executemany('DELETE FROM sessions WHERE id=?', [(i,) for i in expired])
        db.commit()
