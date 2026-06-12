import os
import logging
from flask import Flask, g, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from .config import Config
from .database import init_db, close_db
from .helpers import not_found_response, method_not_allowed_response, json_response
from .auth import verify_auth
from .routes import (
    service_root, account_service, session_service, systems, chassis, managers,
    event_service, update_service, task_service, telemetry_service,
    certificate_service, json_schemas, registries, cables, aggregation_service
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

limiter = Limiter(key_func=get_remote_address)


def create_app():
    app = Flask(__name__)
    app.url_map.strict_slashes = False
    app.config.from_object(Config)

    cors_origins = os.environ.get('CORS_ORIGINS', '*')
    origins = [o.strip() for o in cors_origins.split(',')] if cors_origins != '*' else '*'
    CORS(app, origins=origins, supports_credentials=True)

    limiter.init_app(app)
    limiter.limit('600 per minute')(lambda: None)

    os.makedirs(os.path.dirname(os.path.abspath(app.config['DB_PATH'])), exist_ok=True)
    init_db(app)
    app.teardown_appcontext(close_db)

    @app.before_request
    def authenticate():
        username, err = verify_auth()
        if err:
            return err
        if username:
            g.current_user = username

    @app.before_request
    def log_request():
        app.logger.info('%s %s', request.method, request.path)

    @app.after_request
    def log_response(resp):
        app.logger.info('%s %s -> %s', request.method, request.path, resp.status_code)
        return resp

    @app.errorhandler(404)
    def handle_404(e):
        return not_found_response()

    @app.errorhandler(405)
    def handle_405(e):
        return method_not_allowed_response()

    @app.errorhandler(429)
    def handle_429(e):
        return json_response({
            'error': {
                'code': 'Base.1.0.ServiceTemporarilyUnavailable',
                'message': 'Too many requests. Please retry after a moment.',
                '@Message.ExtendedInfo': []
            }
        }, 429)

    @app.errorhandler(500)
    def handle_500(e):
        return json_response({
            'error': {
                'code': 'Base.1.0.InternalError',
                'message': 'An internal error has occurred.',
                '@Message.ExtendedInfo': []
            }
        }, 500)

    for bp in [
        service_root.bp,
        account_service.bp,
        session_service.bp,
        systems.bp,
        chassis.bp,
        managers.bp,
        event_service.bp,
        update_service.bp,
        task_service.bp,
        telemetry_service.bp,
        certificate_service.bp,
        json_schemas.bp,
        registries.bp,
        cables.bp,
        aggregation_service.bp,
    ]:
        app.register_blueprint(bp)

    return app
