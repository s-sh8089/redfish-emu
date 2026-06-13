import json
import sqlite3
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Body
from ..database import get_db
from ..auth import verify_auth
from ..helpers import json_response, not_found_response, bad_request_response, created_response, no_content_response

router = APIRouter(dependencies=[Depends(verify_auth)])


@router.get('/redfish/v1/CertificateService/')
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


@router.get('/redfish/v1/CertificateService/CertificateLocations/')
def certificate_locations(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute('SELECT id, parent_path FROM certificates').fetchall()
    certs = [{'@odata.id': f'{row["parent_path"]}/{row["id"]}/'.replace('//', '/')}
             for row in rows]
    return json_response({
        '@odata.id': '/redfish/v1/CertificateService/CertificateLocations/',
        '@odata.type': '#CertificateLocations.v1_0_4.CertificateLocations',
        'Id': 'CertificateLocations',
        'Name': 'Certificate Locations',
        'Description': 'Defines a resource that an administrator can use to locate all certificates',
        'Links': {
            'Certificates': certs,
            'Certificates@odata.count': len(certs)
        }
    })


@router.post('/redfish/v1/CertificateService/Actions/CertificateService.GenerateCSR')
def generate_csr(body: dict | None = Body(default=None)):
    data = body or {}
    for field in ['CommonName', 'CertificateCollection']:
        if field not in data:
            return bad_request_response(f'{field} is required.')
    csr_string = (
        '-----BEGIN CERTIFICATE REQUEST-----\n'
        'MIICijCCAXICAQAwRTELMAkGA1UEBhMCVVMxEzARBgNVBAgMClNvbWUtU3RhdGUx\n'
        'ITAfBgNVBAoMGEludGVybmV0IFdpZGdpdHMgUHR5IEx0ZDCCASIwDQYJKoZIhvcN\n'
        'AQEBBQADggEPADCCAQoCggEBAMa3F/mock/csr/data==\n'
        '-----END CERTIFICATE REQUEST-----'
    )
    return json_response({
        'CSRString': csr_string,
        'CertificateCollection': data['CertificateCollection']
    })


@router.post('/redfish/v1/CertificateService/Actions/CertificateService.ReplaceCertificate')
def replace_certificate(
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    data = body or {}
    if 'CertificateString' not in data or 'CertificateType' not in data or 'CertificateUri' not in data:
        return bad_request_response('CertificateString, CertificateType and CertificateUri are required.')
    uri = data['CertificateUri'].get('@odata.id', '') if isinstance(data['CertificateUri'], dict) else data['CertificateUri']
    cert_id = uri.rstrip('/').split('/')[-1]
    if not db.execute('SELECT id FROM certificates WHERE id=?', (cert_id,)).fetchone():
        return not_found_response()
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        'UPDATE certificates SET certificate_string=?, valid_not_before=?, valid_not_after=? WHERE id=?',
        (data['CertificateString'], now, now, cert_id)
    )
    db.commit()
    return no_content_response()


@router.post('/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates/')
def create_https_certificate(
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    data = body or {}
    if 'CertificateString' not in data or 'CertificateType' not in data:
        return bad_request_response('CertificateString and CertificateType are required.')
    count = db.execute(
        "SELECT COUNT(*) FROM certificates WHERE parent_path=?",
        ('/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates',)
    ).fetchone()[0]
    cert_id = str(count + 1)
    now = datetime.now(timezone.utc).isoformat()
    issuer = json.dumps({'CommonName': 'Imported Certificate'})
    subject = json.dumps({'CommonName': 'Imported Certificate'})
    key_usage = json.dumps(['KeyEncipherment', 'DigitalSignature'])
    db.execute('''
        INSERT INTO certificates (id, parent_path, certificate_string, description,
            issuer, subject, key_usage, valid_not_before, valid_not_after)
        VALUES (?,?,?,?,?,?,?,?,?)
    ''', (cert_id, '/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates',
          data['CertificateString'], 'Imported HTTPS Certificate',
          issuer, subject, key_usage, now, now))
    db.commit()
    location = f'/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates/{cert_id}/'
    return created_response({
        '@odata.id': location,
        '@odata.type': '#Certificate.v1_6_0.Certificate',
        'Id': cert_id,
        'Name': 'HTTPS Certificate',
        'CertificateString': data['CertificateString']
    }, location=location)
