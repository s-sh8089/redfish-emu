import hashlib
import json
from datetime import datetime, timezone
from fastapi import Request
from fastapi.responses import JSONResponse, Response

_ODATA_HEADERS = {'OData-Version': '4.0'}


def json_response(data: dict, status: int = 200) -> JSONResponse:
    return JSONResponse(content=data, status_code=status, headers=_ODATA_HEADERS)


def etag_response(data: dict, status: int = 200) -> JSONResponse:
    etag = hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
    return JSONResponse(
        content=data,
        status_code=status,
        headers={**_ODATA_HEADERS, 'ETag': f'"{etag}"'},
    )


def not_found_response() -> JSONResponse:
    return json_response({
        "error": {
            "code": "Base.1.0.ResourceNotFound",
            "message": "The requested resource was not found.",
            "@Message.ExtendedInfo": []
        }
    }, 404)


def bad_request_response(message: str = "Bad request") -> JSONResponse:
    return json_response({
        "error": {
            "code": "Base.1.0.GeneralError",
            "message": message,
            "@Message.ExtendedInfo": []
        }
    }, 400)


def method_not_allowed_response(allowed=None) -> JSONResponse:
    headers = dict(_ODATA_HEADERS)
    if allowed:
        headers['Allow'] = ', '.join(allowed)
    return JSONResponse(
        content={
            "error": {
                "code": "Base.1.0.OperationNotAllowed",
                "message": "The HTTP method is not allowed for this resource.",
                "@Message.ExtendedInfo": []
            }
        },
        status_code=405,
        headers=headers,
    )


def created_response(data: dict, location: str = None) -> JSONResponse:
    headers = dict(_ODATA_HEADERS)
    if location:
        headers['Location'] = location
    return JSONResponse(content=data, status_code=201, headers=headers)


def no_content_response() -> Response:
    return Response(status_code=204, headers=_ODATA_HEADERS)


def apply_odata_params(members: list, request: Request) -> list:
    """Apply $top and $skip OData query parameters to a list."""
    try:
        skip = int(request.query_params.get('$skip', 0))
        members = members[max(0, skip):]
    except (ValueError, TypeError):
        pass
    try:
        top = request.query_params.get('$top')
        if top is not None:
            members = members[:int(top)]
    except (ValueError, TypeError):
        pass
    return members


def odata_context(schema_type: str) -> str:
    return f'/redfish/v1/$metadata#{schema_type}'


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_entry_to_dict(row, odata_id: str) -> dict:
    args = json.loads(row['message_args']) if row['message_args'] else []
    d = {
        '@odata.id': odata_id,
        '@odata.type': '#LogEntry.v1_15_0.LogEntry',
        'Id': row['id'],
        'Name': 'Log Entry',
        'EntryType': row['entry_type'],
        'Severity': row['severity'],
        'Message': row['message'],
        'MessageId': row['message_id'] or '',
        'MessageArgs': args,
        'Created': row['created'],
        'Modified': row['modified'],
        'Resolved': bool(row['resolved']),
    }
    if row['sensor_type']:
        d['SensorType'] = row['sensor_type']
    if row['entry_code']:
        d['EntryCode'] = row['entry_code']
    if row['additional_data_uri']:
        d['AdditionalDataURI'] = row['additional_data_uri']
    return d
