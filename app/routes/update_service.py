import json
from flask import Blueprint
from ..database import get_db
from ..helpers import json_response, not_found_response

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
        'Actions': {
            '#UpdateService.SimpleUpdate': {
                'target': '/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate',
                'TransferProtocol@Redfish.AllowableValues': ['HTTP', 'HTTPS', 'TFTP', 'SCP']
            }
        }
    })


@bp.route('/redfish/v1/UpdateService/FirmwareInventory/')
def firmware_inventory():
    db = get_db()
    rows = db.execute('SELECT id FROM firmware_inventory').fetchall()
    members = [{'@odata.id': f'/redfish/v1/UpdateService/FirmwareInventory/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': '/redfish/v1/UpdateService/FirmwareInventory/',
        '@odata.type': '#SoftwareInventoryCollection.SoftwareInventoryCollection',
        'Name': 'Software Inventory Collection',
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
