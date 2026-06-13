import json
import sqlite3
import uuid
from fastapi import APIRouter, Depends, Body
from ..database import get_db
from ..auth import verify_auth, hash_password
from ..helpers import json_response, not_found_response, bad_request_response, created_response, no_content_response

router = APIRouter(dependencies=[Depends(verify_auth)])


@router.get('/redfish/v1/AccountService/')
def account_service():
    return json_response({
        '@odata.id': '/redfish/v1/AccountService/',
        '@odata.type': '#AccountService.v1_13_0.AccountService',
        'Id': 'AccountService',
        'Name': 'Account Service',
        'Description': 'Account Service',
        'ServiceEnabled': True,
        'AccountLockoutDuration': 30,
        'AccountLockoutThreshold': 3,
        'MaxPasswordLength': 20,
        'MinPasswordLength': 8,
        'Accounts': {'@odata.id': '/redfish/v1/AccountService/Accounts/'},
        'Roles': {'@odata.id': '/redfish/v1/AccountService/Roles/'},
        'LDAP': {
            'ServiceEnabled': False,
            'Certificates': {'@odata.id': '/redfish/v1/AccountService/LDAP/Certificates/'}
        },
        'Oem': {
            'OpenBMC': {
                'AuthMethods': {
                    'BasicAuth': True,
                    'Cookie': True,
                    'SessionToken': True,
                    'TLS': False,
                    'XToken': True
                }
            }
        }
    })


@router.get('/redfish/v1/AccountService/Accounts/')
def accounts(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute('SELECT id FROM accounts').fetchall()
    members = [{'@odata.id': f'/redfish/v1/AccountService/Accounts/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': '/redfish/v1/AccountService/Accounts/',
        '@odata.type': '#ManagerAccountCollection.ManagerAccountCollection',
        'Name': 'Accounts Collection',
        'Description': 'List of user accounts',
        'Members@odata.count': len(members),
        'Members': members
    })


@router.post('/redfish/v1/AccountService/Accounts/')
def accounts_post(
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    data = body or {}
    if not data or 'UserName' not in data or 'Password' not in data or 'RoleId' not in data:
        return bad_request_response('UserName, Password, RoleId are required.')
    plain_pw = data['Password']
    if len(plain_pw) < 8:
        return bad_request_response('Password must be at least 8 characters.')
    if len(plain_pw) > 20:
        return bad_request_response('Password must be at most 20 characters.')
    account_id = data['UserName']
    if db.execute('SELECT id FROM accounts WHERE username=?', (account_id,)).fetchone():
        return bad_request_response('Account already exists.')
    db.execute(
        'INSERT INTO accounts (id, username, password, role_id, enabled, locked, password_change_required, description) VALUES (?,?,?,?,?,?,?,?)',
        (account_id, data['UserName'], hash_password(plain_pw), data['RoleId'],
         1 if data.get('Enabled', True) else 0, 0, 0, data.get('Description', ''))
    )
    db.commit()
    row = db.execute('SELECT * FROM accounts WHERE id=?', (account_id,)).fetchone()
    return created_response(
        _account_to_dict(row),
        location=f'/redfish/v1/AccountService/Accounts/{account_id}/'
    )


@router.get('/redfish/v1/AccountService/Accounts/{account_id}/')
def account_get(account_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM accounts WHERE id=?', (account_id,)).fetchone()
    if not row:
        return not_found_response()
    return json_response(_account_to_dict(row))


@router.patch('/redfish/v1/AccountService/Accounts/{account_id}/')
def account_patch(
    account_id: str,
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    row = db.execute('SELECT * FROM accounts WHERE id=?', (account_id,)).fetchone()
    if not row:
        return not_found_response()
    data = body or {}
    fields, values = [], []
    if 'Password' in data:
        plain_pw = data['Password']
        if len(plain_pw) < 8:
            return bad_request_response('Password must be at least 8 characters.')
        if len(plain_pw) > 20:
            return bad_request_response('Password must be at most 20 characters.')
        fields.append('password=?')
        values.append(hash_password(plain_pw))
    if 'RoleId' in data:
        fields.append('role_id=?')
        values.append(data['RoleId'])
    if 'Enabled' in data:
        fields.append('enabled=?')
        values.append(1 if data['Enabled'] else 0)
    if 'Locked' in data:
        fields.append('locked=?')
        values.append(1 if data['Locked'] else 0)
        if not data['Locked']:
            fields.append('login_failure_count=?')
            values.append(0)
    if fields:
        values.append(account_id)
        db.execute(f'UPDATE accounts SET {", ".join(fields)} WHERE id=?', values)
        db.commit()
    row = db.execute('SELECT * FROM accounts WHERE id=?', (account_id,)).fetchone()
    return json_response(_account_to_dict(row))


@router.delete('/redfish/v1/AccountService/Accounts/{account_id}/')
def account_delete(account_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM accounts WHERE id=?', (account_id,)).fetchone():
        return not_found_response()
    db.execute('DELETE FROM accounts WHERE id=?', (account_id,))
    db.commit()
    return no_content_response()


def _account_to_dict(row) -> dict:
    return {
        '@odata.id': f'/redfish/v1/AccountService/Accounts/{row["id"]}/',
        '@odata.type': '#ManagerAccount.v1_10_0.ManagerAccount',
        'Id': row['id'],
        'Name': row['username'],
        'UserName': row['username'],
        'RoleId': row['role_id'],
        'Enabled': bool(row['enabled']),
        'Locked': bool(row['locked']),
        'PasswordChangeRequired': bool(row['password_change_required']),
        'Description': row['description'] or '',
        'AccountTypes': ['Redfish'],
        'Links': {
            'Role': {'@odata.id': f'/redfish/v1/AccountService/Roles/{row["role_id"]}/'}
        },
        'Locked@Redfish.AllowableValues': [True, False]
    }


@router.get('/redfish/v1/AccountService/Roles/')
def roles(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute('SELECT id FROM roles').fetchall()
    members = [{'@odata.id': f'/redfish/v1/AccountService/Roles/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': '/redfish/v1/AccountService/Roles/',
        '@odata.type': '#RoleCollection.RoleCollection',
        'Name': 'Roles Collection',
        'Description': 'List of roles',
        'Members@odata.count': len(members),
        'Members': members
    })


@router.get('/redfish/v1/AccountService/Roles/{role_id}/')
def role(role_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM roles WHERE id=?', (role_id,)).fetchone()
    if not row:
        return not_found_response()
    privileges = json.loads(row['assigned_privileges']) if row['assigned_privileges'] else []
    return json_response({
        '@odata.id': f'/redfish/v1/AccountService/Roles/{role_id}/',
        '@odata.type': '#Role.v1_3_1.Role',
        'Id': row['id'],
        'Name': row['id'],
        'Description': row['description'] or '',
        'IsPredefined': bool(row['is_predefined']),
        'RoleId': row['id'],
        'AssignedPrivileges': privileges,
        'OemPrivileges': []
    })


@router.get('/redfish/v1/AccountService/LDAP/Certificates/')
def ldap_certificates():
    return json_response({
        '@odata.id': '/redfish/v1/AccountService/LDAP/Certificates/',
        '@odata.type': '#CertificateCollection.CertificateCollection',
        'Name': 'LDAP Certificate Collection',
        'Description': 'LDAP Certificates',
        'Members@odata.count': 0,
        'Members': []
    })
