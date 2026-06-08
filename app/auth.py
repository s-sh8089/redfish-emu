import bcrypt
from datetime import datetime, timezone, timedelta
from flask import request, g
from .database import get_db
from .helpers import json_response

SESSION_TIMEOUT_MINUTES = 30
LOCKOUT_THRESHOLD = 3

_PUBLIC_EXACT = {
    ('GET', '/redfish/v1/'),
    ('POST', '/redfish/v1/SessionService/Sessions/'),
}
_PUBLIC_PREFIXES = (
    '/redfish/v1/JsonSchemas',
    '/redfish/v1/Registries',
)


def verify_auth():
    """Check X-Auth-Token or Basic Auth. Returns (username, None) on success,
    (None, None) for public routes, or (None, error_response) on failure."""
    if (request.method, request.path) in _PUBLIC_EXACT:
        return None, None
    if request.path.startswith(_PUBLIC_PREFIXES):
        return None, None

    db = get_db()
    token = request.headers.get('X-Auth-Token')
    if token:
        return _verify_token(db, token)
    auth = request.authorization
    if auth:
        return _verify_basic(db, auth.username, auth.password)

    resp = _unauth('Authentication required.')
    resp.headers['WWW-Authenticate'] = 'Basic realm="Redfish"'
    return None, resp


def _verify_token(db, token):
    session = db.execute('SELECT * FROM sessions WHERE token=?', (token,)).fetchone()
    if not session:
        return None, _unauth('Invalid or missing authentication token.')
    created = datetime.fromisoformat(session['created_at'])
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        db.execute('DELETE FROM sessions WHERE token=?', (token,))
        db.commit()
        return None, _unauth('Session has timed out.')
    return session['username'], None


def _verify_basic(db, username, password):
    account = db.execute(
        'SELECT * FROM accounts WHERE username=? AND enabled=1', (username,)
    ).fetchone()
    if not account:
        return None, _unauth('Invalid credentials.')
    if account['locked']:
        return None, _unauth('Account is locked.')
    if not _check_password(password, account['password']):
        _increment_failure(db, account['id'])
        return None, _unauth('Invalid credentials.')
    db.execute('UPDATE accounts SET login_failure_count=0 WHERE id=?', (account['id'],))
    db.commit()
    return username, None


def _check_password(plain, stored):
    if stored and (stored.startswith('$2b$') or stored.startswith('$2a$')):
        try:
            return bcrypt.checkpw(plain.encode(), stored.encode())
        except Exception:
            return False
    return plain == stored


def hash_password(plain):
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _increment_failure(db, account_id):
    row = db.execute('SELECT login_failure_count FROM accounts WHERE id=?', (account_id,)).fetchone()
    count = ((row['login_failure_count'] or 0) if row else 0) + 1
    if count >= LOCKOUT_THRESHOLD:
        db.execute('UPDATE accounts SET locked=1, login_failure_count=? WHERE id=?', (count, account_id))
    else:
        db.execute('UPDATE accounts SET login_failure_count=? WHERE id=?', (count, account_id))
    db.commit()


def _unauth(message):
    return json_response({
        'error': {
            'code': 'Base.1.0.NoValidSession',
            'message': message,
            '@Message.ExtendedInfo': []
        }
    }, 401)
