from flask import Blueprint
from ..helpers import json_response

bp = Blueprint('service_root', __name__)


@bp.route('/redfish/v1/')
@bp.route('/redfish/v1')
def service_root():
    return json_response({
        '@odata.id': '/redfish/v1/',
        '@odata.type': '#ServiceRoot.v1_13_0.ServiceRoot',
        'Id': 'RootService',
        'Name': 'Root Service',
        'RedfishVersion': '1.16.0',
        'UUID': '00000000-0000-0000-0000-000000000000',
        'AccountService': {'@odata.id': '/redfish/v1/AccountService/'},
        'AggregationService': {'@odata.id': '/redfish/v1/AggregationService/'},
        'CertificateService': {'@odata.id': '/redfish/v1/CertificateService/'},
        'Chassis': {'@odata.id': '/redfish/v1/Chassis/'},
        'EventService': {'@odata.id': '/redfish/v1/EventService/'},
        'JsonSchemas': {'@odata.id': '/redfish/v1/JsonSchemas/'},
        'Links': {
            'Sessions': {'@odata.id': '/redfish/v1/SessionService/Sessions/'},
            'ManagerProvidingService': {'@odata.id': '/redfish/v1/Managers/bmc/'}
        },
        'Managers': {'@odata.id': '/redfish/v1/Managers/'},
        'Registries': {'@odata.id': '/redfish/v1/Registries/'},
        'SessionService': {'@odata.id': '/redfish/v1/SessionService/'},
        'Systems': {'@odata.id': '/redfish/v1/Systems/'},
        'Tasks': {'@odata.id': '/redfish/v1/TaskService/'},
        'TelemetryService': {'@odata.id': '/redfish/v1/TelemetryService/'},
        'UpdateService': {'@odata.id': '/redfish/v1/UpdateService/'},
    })
