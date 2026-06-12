import json
import uuid
from flask import Blueprint, request
from ..database import get_db
from ..helpers import json_response, not_found_response, bad_request_response, no_content_response, created_response, log_entry_to_dict, now_iso

bp = Blueprint('systems', __name__)

BASE = '/redfish/v1/Systems'


@bp.route('/redfish/v1/Systems/')
def systems():
    return json_response({
        '@odata.id': '/redfish/v1/Systems/',
        '@odata.type': '#ComputerSystemCollection.ComputerSystemCollection',
        'Name': 'Computer System Collection',
        'Members@odata.count': 1,
        'Members': [{'@odata.id': '/redfish/v1/Systems/system'}]
    })


@bp.route('/redfish/v1/Systems/system', methods=['GET', 'PATCH'])
@bp.route('/redfish/v1/Systems/system/', methods=['GET', 'PATCH'])
def system():
    db = get_db()
    row = db.execute('SELECT * FROM systems WHERE id="system"').fetchone()
    if not row:
        return not_found_response()

    if request.method == 'PATCH':
        data = request.get_json() or {}
        fields = []
        values = []
        boot = data.get('Boot', {})
        if 'BootSourceOverrideTarget' in boot:
            fields.append('boot_source_override_target=?')
            values.append(boot['BootSourceOverrideTarget'])
        if 'BootSourceOverrideEnabled' in boot:
            fields.append('boot_source_override_enabled=?')
            values.append(boot['BootSourceOverrideEnabled'])
        if 'BootSourceOverrideMode' in boot:
            fields.append('boot_source_override_mode=?')
            values.append(boot['BootSourceOverrideMode'])
        if 'PowerRestorePolicy' in data:
            fields.append('power_restore_policy=?')
            values.append(data['PowerRestorePolicy'])
        if 'AssetTag' in data:
            fields.append('asset_tag=?')
            values.append(data['AssetTag'])
        if 'PowerMode' in data:
            fields.append('power_mode=?')
            values.append(data['PowerMode'])
        if fields:
            values.append('system')
            db.execute(f'UPDATE systems SET {", ".join(fields)} WHERE id=?', values)
            db.commit()
        row = db.execute('SELECT * FROM systems WHERE id="system"').fetchone()

    procs = db.execute('SELECT COUNT(*) FROM processors WHERE system_id="system"').fetchone()[0]
    mem_rows = db.execute('SELECT SUM(capacity_mib) FROM memory_modules WHERE system_id="system"').fetchone()[0] or 0
    mem_count = db.execute('SELECT COUNT(*) FROM memory_modules WHERE system_id="system"').fetchone()[0]

    return json_response({
        '@odata.id': '/redfish/v1/Systems/system',
        '@odata.type': '#ComputerSystem.v1_21_0.ComputerSystem',
        'Id': 'system',
        'Name': 'Computer System',
        'SystemType': row['system_type'],
        'Manufacturer': row['manufacturer'],
        'Model': row['model'],
        'SubModel': row['sub_model'],
        'SerialNumber': row['serial_number'],
        'PartNumber': row['part_number'],
        'AssetTag': row['asset_tag'] or '',
        'BiosVersion': row['bios_version'],
        'PowerState': row['power_state'],
        'PowerRestorePolicy': row['power_restore_policy'],
        'PowerMode': row['power_mode'],
        'Boot': {
            'BootSourceOverrideTarget': row['boot_source_override_target'],
            'BootSourceOverrideEnabled': row['boot_source_override_enabled'],
            'BootSourceOverrideMode': row['boot_source_override_mode'],
        },
        'Status': {
            'State': row['status_state'],
            'Health': row['status_health']
        },
        'ProcessorSummary': {
            'Count': procs,
            'Status': {'Health': 'OK', 'State': 'Enabled'}
        },
        'MemorySummary': {
            'TotalSystemMemoryGiB': round(mem_rows / 1024, 1),
            'Status': {'Health': 'OK', 'State': 'Enabled'}
        },
        'Processors': {'@odata.id': f'{BASE}/system/Processors/'},
        'Memory': {'@odata.id': f'{BASE}/system/Memory/'},
        'Storage': {'@odata.id': f'{BASE}/system/Storage/'},
        'EthernetInterfaces': {'@odata.id': f'{BASE}/system/EthernetInterfaces/'},
        'FabricAdapters': {'@odata.id': f'{BASE}/system/FabricAdapters/'},
        'Bios': {'@odata.id': f'{BASE}/system/Bios/'},
        'LogServices': {'@odata.id': f'{BASE}/system/LogServices/'},
        'PCIeDevices': {'@odata.id': f'{BASE}/system/PCIeDevices/'},
        'Description': 'Computer System',
        'Links': {
            'Chassis': [{'@odata.id': '/redfish/v1/Chassis/chassis1/'}],
            'ManagedBy': [{'@odata.id': '/redfish/v1/Managers/bmc/'}]
        },
        'Actions': {
            '#ComputerSystem.Reset': {
                'target': f'{BASE}/system/Actions/ComputerSystem.Reset',
                'ResetType@Redfish.AllowableValues': [
                    'On', 'ForceOff', 'GracefulShutdown', 'GracefulRestart',
                    'ForceRestart', 'Nmi', 'ForceOn', 'PushPowerButton'
                ]
            }
        }
    })


_SYSTEM_RESET_TYPES = {'On', 'ForceOff', 'GracefulShutdown', 'GracefulRestart', 'ForceRestart', 'Nmi', 'ForceOn', 'PushPowerButton'}
_SYSTEM_RESET_TO_POWER_ON = {'On', 'ForceOn', 'GracefulRestart', 'ForceRestart', 'Nmi'}
_SYSTEM_RESET_TO_POWER_OFF = {'ForceOff', 'GracefulShutdown'}


@bp.route('/redfish/v1/Systems/system/Actions/ComputerSystem.Reset', methods=['POST'])
def system_reset():
    db = get_db()
    row = db.execute('SELECT power_state FROM systems WHERE id="system"').fetchone()
    if not row:
        return not_found_response()
    data = request.get_json() or {}
    reset_type = data.get('ResetType')
    if reset_type not in _SYSTEM_RESET_TYPES:
        return bad_request_response(f'Invalid ResetType. Allowable values: {sorted(_SYSTEM_RESET_TYPES)}')
    if reset_type in _SYSTEM_RESET_TO_POWER_ON:
        new_state = 'On'
    elif reset_type in _SYSTEM_RESET_TO_POWER_OFF:
        new_state = 'Off'
    else:
        new_state = 'Off' if row['power_state'] == 'On' else 'On'
    db.execute('UPDATE systems SET power_state=? WHERE id="system"', (new_state,))
    db.commit()
    return no_content_response()


@bp.route('/redfish/v1/Systems/system/SecureBoot/', methods=['GET', 'PATCH'])
def secure_boot():
    db = get_db()
    row = db.execute('SELECT secure_boot_enable FROM systems WHERE id="system"').fetchone()
    if not row:
        return not_found_response()
    if request.method == 'PATCH':
        data = request.get_json() or {}
        if 'SecureBootEnable' in data:
            db.execute('UPDATE systems SET secure_boot_enable=? WHERE id="system"',
                       (1 if data['SecureBootEnable'] else 0,))
            db.commit()
        row = db.execute('SELECT secure_boot_enable FROM systems WHERE id="system"').fetchone()
    return json_response({
        '@odata.id': '/redfish/v1/Systems/system/SecureBoot/',
        '@odata.type': '#SecureBoot.v1_1_0.SecureBoot',
        'Id': 'SecureBoot',
        'Name': 'UEFI Secure Boot',
        'Description': 'UEFI Secure Boot',
        'SecureBootEnable': bool(row['secure_boot_enable']),
        'SecureBootCurrentBoot': 'Enabled' if row['secure_boot_enable'] else 'Disabled',
        'SecureBootMode': 'UserMode',
        'Actions': {
            '#SecureBoot.ResetKeys': {
                'target': '/redfish/v1/Systems/system/SecureBoot/Actions/SecureBoot.ResetKeys'
            }
        }
    })


@bp.route('/redfish/v1/Systems/system/Bios/', methods=['GET', 'PATCH'])
def bios():
    db = get_db()
    row = db.execute('SELECT bios_version, bios_attributes FROM systems WHERE id="system"').fetchone()
    if not row:
        return not_found_response()
    attrs = json.loads(row['bios_attributes']) if row['bios_attributes'] else {
        'BootMode': 'Uefi',
        'NicBoot1': 'NetworkBoot',
        'NicBoot2': 'Disabled',
        'QuietBoot': True,
        'SriovGlobalEnable': 'Disabled',
    }
    if request.method == 'PATCH':
        data = request.get_json() or {}
        if 'Attributes' in data and isinstance(data['Attributes'], dict):
            attrs.update(data['Attributes'])
            db.execute('UPDATE systems SET bios_attributes=? WHERE id="system"',
                       (json.dumps(attrs),))
            db.commit()
    return json_response({
        '@odata.id': '/redfish/v1/Systems/system/Bios/',
        '@odata.type': '#Bios.v1_2_0.Bios',
        'Id': 'Bios',
        'Name': 'BIOS Configuration',
        'Description': 'BIOS Configuration',
        'Attributes': attrs,
        'Links': {
            'ActiveSoftwareImage': {'@odata.id': '/redfish/v1/UpdateService/FirmwareInventory/BIOS/'},
            'SoftwareImages': [{'@odata.id': '/redfish/v1/UpdateService/FirmwareInventory/BIOS/'}],
            'SoftwareImages@odata.count': 1
        },
        'Actions': {
            '#Bios.ResetBios': {'target': '/redfish/v1/Systems/system/Bios/Actions/Bios.ResetBios'},
            '#Bios.ChangePassword': {'target': '/redfish/v1/Systems/system/Bios/Actions/Bios.ChangePassword'}
        }
    })


@bp.route('/redfish/v1/Systems/system/Bios/Actions/Bios.ResetBios', methods=['POST'])
def bios_reset():
    db = get_db()
    db.execute('UPDATE systems SET bios_attributes=NULL WHERE id="system"')
    db.commit()
    return no_content_response()


@bp.route('/redfish/v1/Systems/system/Bios/Actions/Bios.ChangePassword', methods=['POST'])
def bios_change_password():
    data = request.get_json() or {}
    if 'PasswordName' not in data or 'NewPassword' not in data:
        return bad_request_response('PasswordName and NewPassword are required.')
    return no_content_response()


@bp.route('/redfish/v1/Systems/system/Processors/')
def processors():
    db = get_db()
    rows = db.execute('SELECT id FROM processors WHERE system_id="system"').fetchall()
    members = [{'@odata.id': f'{BASE}/system/Processors/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/system/Processors/',
        '@odata.type': '#ProcessorCollection.ProcessorCollection',
        'Name': 'Processor Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/Systems/system/Processors/<proc_id>/')
def processor(proc_id):
    db = get_db()
    row = db.execute('SELECT * FROM processors WHERE id=? AND system_id="system"', (proc_id,)).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/system/Processors/{proc_id}/',
        '@odata.type': '#Processor.v1_16_0.Processor',
        'Id': row['id'],
        'Name': row['id'],
        'Socket': row['socket'],
        'ProcessorType': row['processor_type'],
        'ProcessorArchitecture': row['processor_architecture'],
        'InstructionSet': row['instruction_set'],
        'Manufacturer': row['manufacturer'],
        'Model': row['model'],
        'MaxSpeedMHz': row['max_speed_mhz'],
        'TotalCores': row['total_cores'],
        'TotalThreads': row['total_threads'],
        'SerialNumber': row['serial_number'],
        'PartNumber': row['part_number'],
        'SparePartNumber': row['spare_part_number'],
        'Version': row['version'],
        'ProcessorId': {'VendorId': row['processor_id']},
        'Status': {'State': row['status_state'], 'Health': row['status_health']}
    })


@bp.route('/redfish/v1/Systems/system/Memory/')
def memory_collection():
    db = get_db()
    rows = db.execute('SELECT id FROM memory_modules WHERE system_id="system"').fetchall()
    members = [{'@odata.id': f'{BASE}/system/Memory/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/system/Memory/',
        '@odata.type': '#MemoryCollection.MemoryCollection',
        'Name': 'Memory Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/Systems/system/Memory/<mem_id>/')
def memory(mem_id):
    db = get_db()
    row = db.execute('SELECT * FROM memory_modules WHERE id=? AND system_id="system"', (mem_id,)).fetchone()
    if not row:
        return not_found_response()
    allowed_speeds = json.loads(row['allowed_speeds_mhz']) if row['allowed_speeds_mhz'] else []
    return json_response({
        '@odata.id': f'{BASE}/system/Memory/{mem_id}/',
        '@odata.type': '#Memory.v1_17_0.Memory',
        'Id': row['id'],
        'Name': row['id'],
        'BaseModuleType': row['base_module_type'],
        'CapacityMiB': row['capacity_mib'],
        'DataWidthBits': row['data_width_bits'],
        'BusWidthBits': row['bus_width_bits'],
        'ErrorCorrection': row['error_correction'],
        'Manufacturer': row['manufacturer'],
        'Model': row['model'],
        'SerialNumber': row['serial_number'],
        'PartNumber': row['part_number'],
        'SparePartNumber': row['spare_part_number'],
        'OperatingSpeedMhz': row['operating_speed_mhz'],
        'AllowedSpeedsMHz': allowed_speeds,
        'RankCount': row['rank_count'],
        'FirmwareRevision': row['firmware_revision'],
        'Status': {'State': row['status_state'], 'Health': row['status_health']}
    })


@bp.route('/redfish/v1/Systems/system/Memory/<mem_id>/MemoryMetrics/')
def memory_metrics(mem_id):
    db = get_db()
    row = db.execute('SELECT id FROM memory_modules WHERE id=? AND system_id="system"', (mem_id,)).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/system/Memory/{mem_id}/MemoryMetrics/',
        '@odata.type': '#MemoryMetrics.v1_7_1.MemoryMetrics',
        'Id': 'MemoryMetrics',
        'Name': 'Memory Metrics',
        'Description': 'Memory Metrics',
        'HealthData': {
            'AlarmTrips': {
                'Temperature': False,
                'SpareBlock': False,
                'UncorrectableECCError': False,
                'CorrectableECCError': False,
                'AddressParityError': False
            }
        }
    })


@bp.route('/redfish/v1/Systems/system/Storage/')
def storage_collection():
    db = get_db()
    rows = db.execute('SELECT id FROM storage WHERE system_id="system"').fetchall()
    members = [{'@odata.id': f'{BASE}/system/Storage/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/system/Storage/',
        '@odata.type': '#StorageCollection.StorageCollection',
        'Name': 'Storage Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/Systems/system/Storage/<storage_id>/')
def storage(storage_id):
    db = get_db()
    row = db.execute('SELECT * FROM storage WHERE id=? AND system_id="system"', (storage_id,)).fetchone()
    if not row:
        return not_found_response()
    drives = db.execute('SELECT id FROM drives WHERE storage_id=?', (storage_id,)).fetchall()
    drive_members = [{'@odata.id': f'{BASE}/system/Storage/{storage_id}/Drive/{d["id"]}/'}
                     for d in drives]
    return json_response({
        '@odata.id': f'{BASE}/system/Storage/{storage_id}/',
        '@odata.type': '#Storage.v1_14_0.Storage',
        'Id': row['id'],
        'Name': row['id'],
        'Drives': drive_members,
        'Drives@odata.count': len(drive_members),
        'Controllers': {'@odata.id': f'{BASE}/system/Storage/{storage_id}/Controllers/'},
        'Volumes': {'@odata.id': f'{BASE}/system/Storage/{storage_id}/Volumes/'},
        'Status': {'State': row['status_state'], 'Health': row['status_health']}
    })


@bp.route('/redfish/v1/Systems/system/Storage/<storage_id>/Controllers/')
def storage_controllers(storage_id):
    db = get_db()
    if not db.execute('SELECT id FROM storage WHERE id=? AND system_id="system"', (storage_id,)).fetchone():
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/system/Storage/{storage_id}/Controllers/',
        '@odata.type': '#StorageControllerCollection.StorageControllerCollection',
        'Name': 'Storage Controller Collection',
        'Members@odata.count': 1,
        'Members': [{'@odata.id': f'{BASE}/system/Storage/{storage_id}/Controllers/0/'}]
    })


@bp.route('/redfish/v1/Systems/system/Storage/<storage_id>/Controllers/<ctrl_id>/')
def storage_controller(storage_id, ctrl_id):
    db = get_db()
    if not db.execute('SELECT id FROM storage WHERE id=? AND system_id="system"', (storage_id,)).fetchone():
        return not_found_response()
    if ctrl_id != '0':
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/system/Storage/{storage_id}/Controllers/{ctrl_id}/',
        '@odata.type': '#StorageController.v1_7_0.StorageController',
        'Id': ctrl_id,
        'Name': 'Storage Controller 0',
        'Manufacturer': 'Dell Inc.',
        'Model': 'PERC H755',
        'FirmwareVersion': '1.0.0',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'SupportedControllerProtocols': ['PCIe'],
        'SupportedDeviceProtocols': ['SAS', 'SATA']
    })


@bp.route('/redfish/v1/Systems/system/Storage/<storage_id>/Volumes/')
def volumes(storage_id):
    db = get_db()
    if not db.execute('SELECT id FROM storage WHERE id=? AND system_id="system"', (storage_id,)).fetchone():
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/system/Storage/{storage_id}/Volumes/',
        '@odata.type': '#VolumeCollection.VolumeCollection',
        'Name': 'Volume Collection',
        'Members@odata.count': 0,
        'Members': []
    })


@bp.route('/redfish/v1/Systems/system/Storage/<storage_id>/Drive/<drive_id>/')
def drive(storage_id, drive_id):
    db = get_db()
    row = db.execute('SELECT * FROM drives WHERE id=? AND storage_id=?', (drive_id, storage_id)).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/system/Storage/{storage_id}/Drive/{drive_id}/',
        '@odata.type': '#Drive.v1_17_0.Drive',
        'Id': row['id'],
        'Name': row['id'],
        'CapacityBytes': row['capacity_bytes'],
        'EncryptionStatus': row['encryption_status'],
        'Status': {'State': row['status_state'], 'Health': row['status_health']},
        'Links': {
            'Chassis': {'@odata.id': '/redfish/v1/Chassis/chassis1/'}
        }
    })


@bp.route('/redfish/v1/Systems/system/EthernetInterfaces/')
def system_ethernet_interfaces():
    db = get_db()
    rows = db.execute("SELECT id FROM ethernet_interfaces WHERE parent_type='system'").fetchall()
    members = [{'@odata.id': f'{BASE}/system/EthernetInterfaces/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/system/EthernetInterfaces/',
        '@odata.type': '#EthernetInterfaceCollection.EthernetInterfaceCollection',
        'Name': 'Ethernet Interface Collection',
        'Description': 'List of Ethernet Interfaces for this System',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/Systems/system/EthernetInterfaces/<iface_id>/')
def system_ethernet_interface(iface_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM ethernet_interfaces WHERE id=? AND parent_type='system'",
        (iface_id,)
    ).fetchone()
    if not row:
        return not_found_response()
    ipv4 = json.loads(row['ipv4_addresses']) if row['ipv4_addresses'] else []
    ipv4_static = json.loads(row['ipv4_static_addresses']) if row['ipv4_static_addresses'] else []
    ipv6 = json.loads(row['ipv6_addresses']) if row['ipv6_addresses'] else []
    dns = json.loads(row['name_servers']) if row['name_servers'] else []
    return json_response({
        '@odata.id': f'{BASE}/system/EthernetInterfaces/{iface_id}/',
        '@odata.type': '#EthernetInterface.v1_12_0.EthernetInterface',
        'Id': iface_id,
        'Name': iface_id,
        'MACAddress': row['mac_address'],
        'InterfaceEnabled': bool(row['interface_enabled']),
        'LinkStatus': row['link_status'],
        'SpeedMbps': row['speed_mbps'],
        'IPv4Addresses': ipv4,
        'IPv4StaticAddresses': ipv4_static,
        'IPv6Addresses': ipv6,
        'NameServers': dns,
        'Status': {'State': row['status_state'], 'Health': row['status_health']}
    })


@bp.route('/redfish/v1/Systems/system/FabricAdapters/')
def fabric_adapters():
    db = get_db()
    rows = db.execute('SELECT id FROM fabric_adapters WHERE system_id="system"').fetchall()
    members = [{'@odata.id': f'{BASE}/system/FabricAdapters/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/system/FabricAdapters/',
        '@odata.type': '#FabricAdapterCollection.FabricAdapterCollection',
        'Name': 'Fabric Adapter Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/Systems/system/FabricAdapters/<adapter_id>/')
def fabric_adapter(adapter_id):
    db = get_db()
    row = db.execute('SELECT * FROM fabric_adapters WHERE id=? AND system_id="system"', (adapter_id,)).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/system/FabricAdapters/{adapter_id}/',
        '@odata.type': '#FabricAdapter.v1_4_0.FabricAdapter',
        'Id': row['id'],
        'Name': row['id'],
        'Model': row['model'],
        'PartNumber': row['part_number'],
        'SerialNumber': row['serial_number'],
        'SparePartNumber': row['spare_part_number'],
        'Status': {'State': row['status_state'], 'Health': row['status_health']},
        'Location': {}
    })


@bp.route('/redfish/v1/Systems/system/PCIeDevices/')
def pcie_devices():
    db = get_db()
    rows = db.execute('SELECT id FROM pcie_devices WHERE system_id="system"').fetchall()
    members = [{'@odata.id': f'{BASE}/system/PCIeDevices/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/system/PCIeDevices/',
        '@odata.type': '#PCIeDeviceCollection.PCIeDeviceCollection',
        'Name': 'PCIe Device Collection',
        'Description': 'List of PCIe Devices',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/Systems/system/PCIeDevices/<device_id>/')
def pcie_device(device_id):
    db = get_db()
    row = db.execute('SELECT * FROM pcie_devices WHERE id=? AND system_id="system"', (device_id,)).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/system/PCIeDevices/{device_id}/',
        '@odata.type': '#PCIeDevice.v1_12_0.PCIeDevice',
        'Id': row['id'],
        'Name': row['id'],
        'PCIeInterface': {
            'LanesInUse': row['lanes_in_use']
        }
    })


@bp.route('/redfish/v1/Systems/system/LogServices/')
def system_log_services():
    return json_response({
        '@odata.id': f'{BASE}/system/LogServices/',
        '@odata.type': '#LogServiceCollection.LogServiceCollection',
        'Name': 'Log Service Collection',
        'Description': 'List of log services',
        'Members@odata.count': 2,
        'Members': [
            {'@odata.id': f'{BASE}/system/LogServices/EventLog/'},
            {'@odata.id': f'{BASE}/system/LogServices/SEL/'}
        ]
    })


@bp.route('/redfish/v1/Systems/system/LogServices/EventLog/')
def system_eventlog():
    return json_response({
        '@odata.id': f'{BASE}/system/LogServices/EventLog/',
        '@odata.type': '#LogService.v1_4_0.LogService',
        'Id': 'EventLog',
        'Name': 'Event Log',
        'Description': 'System Event Log',
        'DateTime': now_iso(),
        'DateTimeLocalOffset': '+00:00',
        'MaxNumberOfRecords': 4096,
        'OverWritePolicy': 'WrapsWhenFull',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'Entries': {'@odata.id': f'{BASE}/system/LogServices/EventLog/Entries/'},
        'Actions': {
            '#LogService.ClearLog': {
                'target': f'{BASE}/system/LogServices/EventLog/Actions/LogService.ClearLog'
            }
        }
    })


@bp.route('/redfish/v1/Systems/system/LogServices/EventLog/Actions/LogService.ClearLog', methods=['POST'])
def system_eventlog_clear():
    db = get_db()
    db.execute("DELETE FROM log_entries WHERE log_service_id='EventLog' AND parent_type='system'")
    db.commit()
    return no_content_response()


@bp.route('/redfish/v1/Systems/system/LogServices/EventLog/Entries/', methods=['GET', 'POST'])
def system_eventlog_entries():
    db = get_db()
    if request.method == 'POST':
        return _create_log_entry(db, 'EventLog', 'system',
                                 f'{BASE}/system/LogServices/EventLog/Entries/')
    rows = db.execute(
        "SELECT * FROM log_entries WHERE log_service_id='EventLog' AND parent_type='system'"
    ).fetchall()
    members = [{'@odata.id': f'{BASE}/system/LogServices/EventLog/Entries/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/system/LogServices/EventLog/Entries/',
        '@odata.type': '#LogEntryCollection.LogEntryCollection',
        'Name': 'Log Entry Collection',
        'Description': 'Collection of log entries',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/Systems/system/LogServices/EventLog/Entries/<entry_id>/', methods=['GET', 'PATCH', 'DELETE'])
def system_eventlog_entry(entry_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM log_entries WHERE id=? AND log_service_id='EventLog' AND parent_type='system'",
        (entry_id,)
    ).fetchone()
    if not row:
        return not_found_response()
    odata_id = f'{BASE}/system/LogServices/EventLog/Entries/{entry_id}/'
    if request.method == 'PATCH':
        return _patch_log_entry(db, entry_id, odata_id)
    if request.method == 'DELETE':
        db.execute('DELETE FROM log_entries WHERE id=?', (entry_id,))
        db.commit()
        return no_content_response()
    return json_response(log_entry_to_dict(row, odata_id))


@bp.route('/redfish/v1/Systems/system/LogServices/SEL/')
def system_sel():
    return json_response({
        '@odata.id': f'{BASE}/system/LogServices/SEL/',
        '@odata.type': '#LogService.v1_4_0.LogService',
        'Id': 'SEL',
        'Name': 'SEL',
        'Description': 'IPMI System Event Log',
        'DateTime': now_iso(),
        'DateTimeLocalOffset': '+00:00',
        'MaxNumberOfRecords': 4096,
        'OverWritePolicy': 'WrapsWhenFull',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'Entries': {'@odata.id': f'{BASE}/system/LogServices/SEL/Entries/'},
        'Actions': {
            '#LogService.ClearLog': {
                'target': f'{BASE}/system/LogServices/SEL/Actions/LogService.ClearLog'
            }
        }
    })


@bp.route('/redfish/v1/Systems/system/LogServices/SEL/Actions/LogService.ClearLog', methods=['POST'])
def system_sel_clear():
    db = get_db()
    db.execute("DELETE FROM log_entries WHERE log_service_id='SEL' AND parent_type='system'")
    db.commit()
    return no_content_response()


@bp.route('/redfish/v1/Systems/system/LogServices/SEL/Entries/', methods=['GET', 'POST'])
def system_sel_entries():
    db = get_db()
    if request.method == 'POST':
        return _create_log_entry(db, 'SEL', 'system',
                                 f'{BASE}/system/LogServices/SEL/Entries/')
    rows = db.execute(
        "SELECT * FROM log_entries WHERE log_service_id='SEL' AND parent_type='system'"
    ).fetchall()
    members = [{'@odata.id': f'{BASE}/system/LogServices/SEL/Entries/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/system/LogServices/SEL/Entries/',
        '@odata.type': '#LogEntryCollection.LogEntryCollection',
        'Name': 'Log Entry Collection',
        'Description': 'SEL entries',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/Systems/system/LogServices/SEL/Entries/<entry_id>/', methods=['GET', 'PATCH', 'DELETE'])
def system_sel_entry(entry_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM log_entries WHERE id=? AND log_service_id='SEL' AND parent_type='system'",
        (entry_id,)
    ).fetchone()
    if not row:
        return not_found_response()
    odata_id = f'{BASE}/system/LogServices/SEL/Entries/{entry_id}/'
    if request.method == 'PATCH':
        return _patch_log_entry(db, entry_id, odata_id)
    if request.method == 'DELETE':
        db.execute('DELETE FROM log_entries WHERE id=?', (entry_id,))
        db.commit()
        return no_content_response()
    return json_response(log_entry_to_dict(row, odata_id))


def _create_log_entry(db, log_service_id, parent_type, collection_path):
    data = request.get_json() or {}
    if 'Message' not in data:
        return bad_request_response('Message is required.')
    now = now_iso()
    entry_id = str(uuid.uuid4()).replace('-', '')[:16]
    db.execute(
        '''INSERT INTO log_entries
           (id, log_service_id, parent_type, entry_type, severity, message, message_id, message_args,
            created, modified, resolved, sensor_type, entry_code, additional_data_uri)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
        (entry_id, log_service_id, parent_type,
         data.get('EntryType', 'Event'),
         data.get('Severity', 'OK'),
         data['Message'],
         data.get('MessageId', ''),
         json.dumps(data.get('MessageArgs', [])),
         now, now, 0,
         data.get('SensorType'),
         data.get('EntryCode'),
         data.get('AdditionalDataURI'))
    )
    db.commit()
    row = db.execute('SELECT * FROM log_entries WHERE id=?', (entry_id,)).fetchone()
    odata_id = f'{collection_path}{entry_id}/'
    return created_response(log_entry_to_dict(row, odata_id), location=odata_id)


def _patch_log_entry(db, entry_id, odata_id):
    data = request.get_json() or {}
    fields, values = [], []
    if 'Resolved' in data:
        fields.append('resolved=?')
        values.append(1 if data['Resolved'] else 0)
    if 'Message' in data:
        fields.append('message=?')
        values.append(data['Message'])
    if 'Severity' in data:
        fields.append('severity=?')
        values.append(data['Severity'])
    if fields:
        fields.append('modified=?')
        values.append(now_iso())
        values.append(entry_id)
        db.execute(f'UPDATE log_entries SET {", ".join(fields)} WHERE id=?', values)
        db.commit()
    row = db.execute('SELECT * FROM log_entries WHERE id=?', (entry_id,)).fetchone()
    return json_response(log_entry_to_dict(row, odata_id))
