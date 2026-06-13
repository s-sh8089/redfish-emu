import base64
import bcrypt
import sqlite3
from datetime import datetime, timezone, timedelta
from fastapi import Request, Depends, HTTPException
from .database import get_db

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


def verify_auth(
    request: Request,
    db: sqlite3.Connection = Depends(get_db),
) -> str | None:
    """FastAPI dependency. Returns username on success, None for public routes.
    Raises HTTPException(401) on auth failure."""
    path = request.url.path
    method = request.method

    if (method, path) in _PUBLIC_EXACT:
        return None
    if path.startswith(_PUBLIC_PREFIXES):
        return None

    token = request.headers.get('X-Auth-Token')
    if token:
        return _verify_token(db, token)

    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Basic '):
        try:
            decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
            username, password = decoded.split(':', 1)
        except Exception:
            pass
        else:
            return _verify_basic(db, username, password)

    raise HTTPException(
        status_code=401,
        detail=_unauth_body('Authentication required.'),
        headers={'WWW-Authenticate': 'Basic realm="Redfish"'},
    )


def _verify_token(db: sqlite3.Connection, token: str) -> str:
    session = db.execute('SELECT * FROM sessions WHERE token=?', (token,)).fetchone()
    if not session:
        raise HTTPException(
            status_code=401,
            detail=_unauth_body('Invalid or missing authentication token.'),
        )
    created = datetime.fromisoformat(session['created_at'])
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        db.execute('DELETE FROM sessions WHERE token=?', (token,))
        db.commit()
        raise HTTPException(
            status_code=401,
            detail=_unauth_body('Session has timed out.'),
        )
    return session['username']


def _verify_basic(db: sqlite3.Connection, username: str, password: str) -> str:
    account = db.execute(
        'SELECT * FROM accounts WHERE username=? AND enabled=1', (username,)
    ).fetchone()
    if not account:
        raise HTTPException(status_code=401, detail=_unauth_body('Invalid credentials.'))
    if account['locked']:
        raise HTTPException(status_code=401, detail=_unauth_body('Account is locked.'))
    if not _check_password(password, account['password']):
        _increment_failure(db, account['id'])
        raise HTTPException(status_code=401, detail=_unauth_body('Invalid credentials.'))
    db.execute('UPDATE accounts SET login_failure_count=0 WHERE id=?', (account['id'],))
    db.commit()
    return username


def _check_password(plain: str, stored: str) -> bool:
    if stored and (stored.startswith('$2b$') or stored.startswith('$2a$')):
        try:
            return bcrypt.checkpw(plain.encode(), stored.encode())
        except Exception:
            return False
    return plain == stored


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def _increment_failure(db: sqlite3.Connection, account_id: str) -> None:
    row = db.execute(
        'SELECT login_failure_count FROM accounts WHERE id=?', (account_id,)
    ).fetchone()
    count = ((row['login_failure_count'] or 0) if row else 0) + 1
    if count >= LOCKOUT_THRESHOLD:
        db.execute(
            'UPDATE accounts SET locked=1, login_failure_count=? WHERE id=?', (count, account_id)
        )
    else:
        db.execute(
            'UPDATE accounts SET login_failure_count=? WHERE id=?', (count, account_id)
        )
    db.commit()


def _unauth_body(message: str) -> dict:
    return {
        'error': {
            'code': 'Base.1.0.NoValidSession',
            'message': message,
            '@Message.ExtendedInfo': []
        }
    }
