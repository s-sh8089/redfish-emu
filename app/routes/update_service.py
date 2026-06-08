import json
from flask import Blueprint, request
from ..database import get_db
from ..helpers import json_response, not_found_response, bad_request_response, created_response
from .task_service import create_task, complete_task

bp = Blueprint('update_service', __name__)


@bp.route('/redfish/v1/UpdateService/')
def update_service():
    return json_response({
        '@odata.id': '/redfish/v1/UpdateService/',
        '@odata.type': '#UpdateService.v1_11_0.UpdateService',
        'Id': 'UpdateService',
        'Name': 'Update Service',
        'Description': 'Service for Software Update',
        'ServiceEnabled': True,
        'HttpPushUri': '/redfish/v1/UpdateService/update',
        'HttpPushUriOptions': {
            'HttpPushUriApplyTime': {
                'ApplyTime': 'Immediate',
                'ApplyTime@Redfish.AllowableValues': ['Immediate', 'AtMaintenanceWindowStart']
            }
        },
        'MaxImageSizeBytes': 536870912,
        'FirmwareInventory': {'@odata.id': '/redfish/v1/UpdateService/FirmwareInventory/'},
        'SoftwareInventory': {'@odata.id': '/redfish/v1/UpdateService/SoftwareInventory/'},
        'Actions': {
            '#UpdateService.SimpleUpdate': {
                'target': '/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate',
                'TransferProtocol@Redfish.AllowableValues': ['HTTP', 'HTTPS', 'TFTP', 'SCP']
            }
        }
    })


@bp.route('/redfish/v1/UpdateService/update', methods=['POST'])
def http_push_update():
    db = get_db()
    if 'file' not in request.files:
        return bad_request_response('No firmware file provided (multipart field "file" required).')
    fw_file = request.files['file']
    filename = fw_file.filename or 'unknown'
    task_id = create_task(db, messages=[{'Message': f'Firmware upload started: {filename}', 'Severity': 'OK'}])
    complete_task(db, task_id, messages=[{'Message': f'Firmware uploaded: {filename}', 'Severity': 'OK'}])
    task_data = {
        '@odata.id': f'/redfish/v1/TaskService/Tasks/{task_id}/',
        '@odata.type': '#Task.v1_7_0.Task',
        'Id': task_id,
        'TaskState': 'Completed',
        'TaskStatus': 'OK'
    }
    return created_response(task_data, location=f'/redfish/v1/TaskService/Tasks/{task_id}/')


@bp.route('/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate', methods=['POST'])
def simple_update():
    data = request.get_json() or {}
    image_uri = data.get('ImageURI')
    if not image_uri:
        return bad_request_response('ImageURI is required')
    targets = data.get('Targets', [])
    db = get_db()
    new_version = image_uri.rstrip('/').split('/')[-1]
    if targets:
        for target in targets:
            fw_id = target.rstrip('/').split('/')[-1]
            if db.execute('SELECT id FROM firmware_inventory WHERE id=?', (fw_id,)).fetchone():
                db.execute('UPDATE firmware_inventory SET version=? WHERE id=?', (new_version, fw_id))
    task_id = create_task(db, messages=[{'Message': f'SimpleUpdate started for {image_uri}', 'Severity': 'OK'}])
    complete_task(db, task_id, messages=[{'Message': 'SimpleUpdate completed.', 'Severity': 'OK'}])
    db.commit()
    return json_response({'@odata.id': f'/redfish/v1/TaskService/Tasks/{task_id}/'}, 202)


@bp.route('/redfish/v1/UpdateService/FirmwareInventory/')
def firmware_inventory():
    db = get_db()
    rows = db.execute('SELECT id FROM firmware_inventory').fetchall()
    members = [{'@odata.id': f'/redfish/v1/UpdateService/FirmwareInventory/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': '/redfish/v1/UpdateService/FirmwareInventory/',
        '@odata.type': '#SoftwareInventoryCollection.SoftwareInventoryCollection',
        'Name': 'Firmware Inventory Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/UpdateService/FirmwareInventory/<fw_id>/')
def firmware_item(fw_id):
    db = get_db()
    row = db.execute('SELECT * FROM firmware_inventory WHERE id=?', (fw_id,)).fetchone()
    if not row:
        return not_found_response()
    related = json.loads(row['related_item']) if row['related_item'] else []
    return json_response({
        '@odata.id': f'/redfish/v1/UpdateService/FirmwareInventory/{fw_id}/',
        '@odata.type': '#SoftwareInventory.v1_10_0.SoftwareInventory',
        'Id': row['id'],
        'Name': row['id'],
        'Description': row['description'],
        'Version': row['version'],
        'Updateable': bool(row['updateable']),
        'Status': {'State': row['status_state'], 'Health': row['status_health']},
        'RelatedItem': related,
        'RelatedItem@odata.count': len(related)
    })


@bp.route('/redfish/v1/UpdateService/SoftwareInventory/')
def software_inventory():
    db = get_db()
    rows = db.execute('SELECT id FROM firmware_inventory').fetchall()
    members = [{'@odata.id': f'/redfish/v1/UpdateService/SoftwareInventory/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': '/redfish/v1/UpdateService/SoftwareInventory/',
        '@odata.type': '#SoftwareInventoryCollection.SoftwareInventoryCollection',
        'Name': 'Software Inventory Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/UpdateService/SoftwareInventory/<fw_id>/')
def software_item(fw_id):
    db = get_db()
    row = db.execute('SELECT * FROM firmware_inventory WHERE id=?', (fw_id,)).fetchone()
    if not row:
        return not_found_response()
    related = json.loads(row['related_item']) if row['related_item'] else []
    return json_response({
        '@odata.id': f'/redfish/v1/UpdateService/SoftwareInventory/{fw_id}/',
        '@odata.type': '#SoftwareInventory.v1_10_0.SoftwareInventory',
        'Id': row['id'],
        'Name': row['id'],
        'Description': row['description'],
        'Version': row['version'],
        'Updateable': bool(row['updateable']),
        'Status': {'State': row['status_state'], 'Health': row['status_health']},
        'RelatedItem': related,
        'RelatedItem@odata.count': len(related)
    })
