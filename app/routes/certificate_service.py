from flask import Blueprint
from ..helpers import json_response

bp = Blueprint('certificate_service', __name__)


@bp.route('/redfish/v1/CertificateService/')
def certificate_service():
    return json_response({
        '@odata.id': '/redfish/v1/CertificateService/',
        '@odata.type': '#CertificateService.v1_0_4.CertificateService',
        'Id': 'CertificateService',
        'Name': 'Certificate Service',
        'Description': 'Actions available to manage certificates',
        'CertificateLocations': {'@odata.id': '/redfish/v1/CertificateService/CertificateLocations/'},
        'Actions': {
            '#CertificateService.GenerateCSR': {
                'target': '/redfish/v1/CertificateService/Actions/CertificateService.GenerateCSR'
            },
            '#CertificateService.ReplaceCertificate': {
                'target': '/redfish/v1/CertificateService/Actions/CertificateService.ReplaceCertificate'
            }
        }
    })


@bp.route('/redfish/v1/CertificateService/CertificateLocations/')
def certificate_locations():
    return json_response({
        '@odata.id': '/redfish/v1/CertificateService/CertificateLocations/',
        '@odata.type': '#CertificateLocations.v1_0_4.CertificateLocations',
        'Id': 'CertificateLocations',
        'Name': 'Certificate Locations',
        'Description': 'Defines a resource that an administrator can use to locate all certificates',
        'Links': {
            'Certificates': [
                {'@odata.id': '/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates/1/'}
            ],
            'Certificates@odata.count': 1
        }
    })
