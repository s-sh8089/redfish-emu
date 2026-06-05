from flask import jsonify, make_response


def json_response(data, status=200):
    resp = make_response(jsonify(data), status)
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['OData-Version'] = '4.0'
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


def method_not_allowed_response():
    return json_response({
        "error": {
            "code": "Base.1.0.OperationNotAllowed",
            "message": "The HTTP method is not allowed for this resource.",
            "@Message.ExtendedInfo": []
        }
    }, 405)


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
