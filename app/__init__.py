import os
from flask import Flask
from .config import Config
from .database import init_db, close_db
from .helpers import not_found_response, method_not_allowed_response, json_response
from .routes import (
    service_root, account_service, session_service, systems, chassis, managers,
    event_service, update_service, task_service, telemetry_service,
    certificate_service, json_schemas, registries, cables, aggregation_service
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.dirname(os.path.abspath(app.config['DB_PATH'])), exist_ok=True)
    init_db(app)
    app.teardown_appcontext(close_db)

    @app.errorhandler(404)
    def handle_404(e):
        return not_found_response()

    @app.errorhandler(405)
    def handle_405(e):
        return method_not_allowed_response()

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
