import hashlib
import json
from flask import jsonify, make_response, request


def json_response(data, status=200):
    resp = make_response(jsonify(data), status)
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['OData-Version'] = '4.0'
    return resp


def etag_response(data, status=200):
    resp = json_response(data, status)
    etag = hashlib.md5(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()
    resp.headers['ETag'] = f'"{etag}"'
    return resp


def not_found_response():
    return json_response({
        "error": {
            "code": "Base.1.0.ResourceNotFound",
            "message": "The requested resource was not found.",
            "@Message.ExtendedInfo": []
        }
    }, 404)


def bad_request_response(message="Bad request"):
    return json_response({
        "error": {
            "code": "Base.1.0.GeneralError",
            "message": message,
            "@Message.ExtendedInfo": []
        }
    }, 400)


def method_not_allowed_response(allowed=None):
    resp = json_response({
        "error": {
            "code": "Base.1.0.OperationNotAllowed",
            "message": "The HTTP method is not allowed for this resource.",
            "@Message.ExtendedInfo": []
        }
    }, 405)
    if allowed:
        resp.headers['Allow'] = ', '.join(allowed)
    return resp


def created_response(data, location=None):
    resp = make_response(jsonify(data), 201)
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['OData-Version'] = '4.0'
    if location:
        resp.headers['Location'] = location
    return resp


def no_content_response():
    resp = make_response('', 204)
    resp.headers['OData-Version'] = '4.0'
    return resp


def apply_odata_params(members):
    """Apply $top and $skip OData query parameters to a list."""
    try:
        skip = int(request.args.get('$skip', 0))
        members = members[max(0, skip):]
    except (ValueError, TypeError):
        pass
    try:
        top = request.args.get('$top')
        if top is not None:
            members = members[:int(top)]
    except (ValueError, TypeError):
        pass
    return members


def odata_context(schema_type):
    return f'/redfish/v1/$metadata#{schema_type}'
