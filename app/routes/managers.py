import json
from datetime import datetime, timezone
from flask import Blueprint
from ..database import get_db
from ..helpers import json_response, not_found_response

bp = Blueprint('managers', __name__)

BASE = '/redfish/v1/Managers'


@bp.route('/redfish/v1/Managers/')
def managers():
    return json_response({
        '@odata.id': '/redfish/v1/Managers/',
        '@odata.type': '#ManagerCollection.ManagerCollection',
        'Name': 'Manager Collection',
        'Members@odata.count': 1,
        'Members': [{'@odata.id': '/redfish/v1/Managers/bmc/'}]
    })


@bp.route('/redfish/v1/Managers/bmc/')
def manager_bmc():
    db = get_db()
    row = db.execute('SELECT * FROM managers WHERE id="bmc"').fetchone()
    if not row:
        return not_found_response()
    now = datetime.now(timezone.utc).isoformat()
    return json_response({
        '@odata.id': '/redfish/v1/Managers/bmc/',
        '@odata.type': '#Manager.v1_17_0.Manager',
        'Id': 'bmc',
        'Name': 'OpenBmc Manager',
        'ManagerType': row['manager_type'],
        'Description': row['description'],
        'FirmwareVersion': row['firmware_version'],
        'Model': row['model'],
        'Manufacturer': row['manufacturer'],
        'SerialNumber': row['serial_number'],
        'PartNumber': row['part_number'],
        'SparePartNumber': row['spare_part_number'],
        'PowerState': row['power_state'],
        'DateTime': now,
        'DateTimeLocalOffset': row['datetime_local_offset'],
        'LastResetTime': row['last_reset_time'],
        'UUID': row['uuid'],
        'ServiceEntryPointUUID': row['service_entry_point_uuid'],
        'Status': {'State': row['status_state'], 'Health': row['status_health']},
        'EthernetInterfaces': {'@odata.id': f'{BASE}/bmc/EthernetInterfaces/'},
        'LogServices': {'@odata.id': f'{BASE}/bmc/LogServices/'},
        'NetworkProtocol': {'@odata.id': f'{BASE}/bmc/NetworkProtocol/'},
        'Links': {
            'ManagerForChassis': [{'@odata.id': '/redfish/v1/Chassis/chassis1/'}],
            'ManagerForChassis@odata.count': 1,
            'ManagerForServers': [{'@odata.id': '/redfish/v1/Systems/system'}],
            'ManagerForServers@odata.count': 1,
            'ManagerInChassis': {'@odata.id': '/redfish/v1/Chassis/chassis1/'},
            'ActiveSoftwareImage': {'@odata.id': '/redfish/v1/UpdateService/FirmwareInventory/BMC/'},
            'SoftwareImages': [{'@odata.id': '/redfish/v1/UpdateService/FirmwareInventory/BMC/'}],
            'SoftwareImages@odata.count': 1
        },
        'GraphicalConsole': {'ServiceEnabled': False, 'MaxConcurrentSessions': 0, 'ConnectTypesSupported': []},
        'SerialConsole': {'ServiceEnabled': True, 'MaxConcurrentSessions': 1, 'ConnectTypesSupported': ['SSH']},
        'Oem': {},
        'Actions': {
            '#Manager.Reset': {
                'target': f'{BASE}/bmc/Actions/Manager.Reset',
                'ResetType@Redfish.AllowableValues': ['GracefulRestart', 'ForceRestart']
            }
        }
    })


@bp.route('/redfish/v1/Managers/bmc/EthernetInterfaces/')
def bmc_ethernet_interfaces():
    db = get_db()
    rows = db.execute("SELECT id FROM ethernet_interfaces WHERE parent_type='manager' AND parent_id='bmc'").fetchall()
    members = [{'@odata.id': f'{BASE}/bmc/EthernetInterfaces/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/bmc/EthernetInterfaces/',
        '@odata.type': '#EthernetInterfaceCollection.EthernetInterfaceCollection',
        'Name': 'Ethernet Interface Collection',
        'Description': 'List of Ethernet Interfaces for this Manager',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/Managers/bmc/EthernetInterfaces/<iface_id>/')
def bmc_ethernet_interface(iface_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM ethernet_interfaces WHERE id=? AND parent_type='manager' AND parent_id='bmc'",
        (iface_id,)
    ).fetchone()
    if not row:
        return not_found_response()
    ipv4 = json.loads(row['ipv4_addresses']) if row['ipv4_addresses'] else []
    ipv4_static = json.loads(row['ipv4_static_addresses']) if row['ipv4_static_addresses'] else []
    ipv6 = json.loads(row['ipv6_addresses']) if row['ipv6_addresses'] else []
    ipv6_static = json.loads(row['ipv6_static_addresses']) if row['ipv6_static_addresses'] else []
    dns = json.loads(row['name_servers']) if row['name_servers'] else []
    static_dns = json.loads(row['static_name_servers']) if row['static_name_servers'] else []
    dhcpv4 = json.loads(row['dhcpv4']) if row['dhcpv4'] else {}
    dhcpv6 = json.loads(row['dhcpv6']) if row['dhcpv6'] else {}
    return json_response({
        '@odata.id': f'{BASE}/bmc/EthernetInterfaces/{iface_id}/',
        '@odata.type': '#EthernetInterface.v1_12_0.EthernetInterface',
        'Id': iface_id,
        'Name': iface_id,
        'Description': f'Management Network Interface {iface_id}',
        'MACAddress': row['mac_address'],
        'FQDN': row['fqdn'],
        'HostName': row['hostname'],
        'InterfaceEnabled': bool(row['interface_enabled']),
        'LinkStatus': row['link_status'],
        'SpeedMbps': row['speed_mbps'],
        'IPv4Addresses': ipv4,
        'IPv4StaticAddresses': ipv4_static,
        'IPv6Addresses': ipv6,
        'IPv6StaticAddresses': ipv6_static,
        'IPv6DefaultGateway': row['ipv6_default_gateway'] or '::',
        'IPv6AddressPolicyTable': [],
        'NameServers': dns,
        'StaticNameServers': static_dns,
        'DHCPv4': dhcpv4,
        'DHCPv6': dhcpv6,
        'VLANs': {'@odata.id': f'{BASE}/bmc/EthernetInterfaces/{iface_id}/VLANs/'},
        'Status': {'State': row['status_state'], 'Health': row['status_health']}
    })


@bp.route('/redfish/v1/Managers/bmc/EthernetInterfaces/<iface_id>/VLANs/')
def bmc_vlans(iface_id):
    db = get_db()
    rows = db.execute('SELECT * FROM vlans WHERE ethernet_interface_id=?', (iface_id,)).fetchall()
    members = []
    for v in rows:
        members.append({
            '@odata.id': f'{BASE}/bmc/EthernetInterfaces/{iface_id}/VLANs/{v["id"]}/',
            'VLANEnable': bool(v['vlan_enable']),
            'VLANId': v['vlan_id']
        })
    return json_response({
        '@odata.id': f'{BASE}/bmc/EthernetInterfaces/{iface_id}/VLANs/',
        '@odata.type': '#VLanNetworkInterfaceCollection.VLanNetworkInterfaceCollection',
        'Name': 'VLAN Network Interface Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/Managers/bmc/LogServices/')
def bmc_log_services():
    return json_response({
        '@odata.id': f'{BASE}/bmc/LogServices/',
        '@odata.type': '#LogServiceCollection.LogServiceCollection',
        'Name': 'Log Service Collection',
        'Description': 'List of log services',
        'Members@odata.count': 1,
        'Members': [{'@odata.id': f'{BASE}/bmc/LogServices/RedfishLog/'}]
    })


@bp.route('/redfish/v1/Managers/bmc/LogServices/RedfishLog/')
def bmc_redfishlog():
    now = datetime.now(timezone.utc).isoformat()
    return json_response({
        '@odata.id': f'{BASE}/bmc/LogServices/RedfishLog/',
        '@odata.type': '#LogService.v1_4_0.LogService',
        'Id': 'RedfishLog',
        'Name': 'Redfish Log',
        'Description': 'Redfish Log Service',
        'DateTime': now,
        'MaxNumberOfRecords': 4096,
        'OverWritePolicy': 'WrapsWhenFull',
        'Entries': {'@odata.id': f'{BASE}/bmc/LogServices/RedfishLog/Entries/'},
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'Actions': {
            '#LogService.ClearLog': {
                'target': f'{BASE}/bmc/LogServices/RedfishLog/Actions/LogService.ClearLog'
            }
        }
    })


@bp.route('/redfish/v1/Managers/bmc/LogServices/RedfishLog/Entries/')
def bmc_log_entries():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM log_entries WHERE log_service_id='RedfishLog' AND parent_type='manager'"
    ).fetchall()
    members = [{'@odata.id': f'{BASE}/bmc/LogServices/RedfishLog/Entries/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/bmc/LogServices/RedfishLog/Entries/',
        '@odata.type': '#LogEntryCollection.LogEntryCollection',
        'Name': 'Log Entry Collection',
        'Description': 'Collection of log entries',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/Managers/bmc/LogServices/RedfishLog/Entries/<entry_id>/')
def bmc_log_entry(entry_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM log_entries WHERE id=? AND log_service_id='RedfishLog' AND parent_type='manager'",
        (entry_id,)
    ).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/bmc/LogServices/RedfishLog/Entries/{entry_id}/',
        '@odata.type': '#LogEntry.v1_15_0.LogEntry',
        'Id': row['id'],
        'Name': 'Log Entry',
        'EntryType': row['entry_type'],
        'Message': row['message'],
        'Created': row['created'],
    })


@bp.route('/redfish/v1/Managers/bmc/ManagerDiagnosticData/')
def manager_diagnostic_data():
    return json_response({
        '@odata.id': f'{BASE}/bmc/ManagerDiagnosticData/',
        '@odata.type': '#ManagerDiagnosticData.v1_2_0.ManagerDiagnosticData',
        'Id': 'ManagerDiagnosticData',
        'Name': 'Manager Diagnostic Data',
        'ServiceRootUptimeSeconds': 3600.0,
    })


@bp.route('/redfish/v1/Managers/bmc/ManagerDiagnosticData/GooglegRPCStatistics')
def grpc_statistics():
    return json_response({
        '@odata.id': f'{BASE}/bmc/ManagerDiagnosticData/GooglegRPCStatistics',
        '@odata.type': '#ManagerDiagnosticData.v1_2_0.ManagerDiagnosticData',
        'Id': 'GooglegRPCStatistics',
        'Name': 'gRPC Statistics',
        'gRPCInitLatencyMs': 0.0,
        'AuthenticationLatencyMs': 1.2,
        'QueueLatencyMs': 0.5,
        'RequestLatencyMs': 2.0,
        'ProcessingLatencyMs': 1.8,
        'ResponseLatencyMs': 0.3,
        'AuthorizedCount': 42,
        'AuthorizedFailCount': 0,
        'AuthenticatedCount': 42,
        'AuthenticatedFailCount': 1,
        'HTTPMethods': {},
        'HTTPResponseCodes': {'200': 38, '401': 1, '404': 3},
        'gRPCStatusCodes': {}
    })


@bp.route('/redfish/v1/Managers/bmc/NetworkProtocol/')
def network_protocol():
    return json_response({
        '@odata.id': f'{BASE}/bmc/NetworkProtocol/',
        '@odata.type': '#ManagerNetworkProtocol.v1_9_0.ManagerNetworkProtocol',
        'Id': 'NetworkProtocol',
        'Name': 'Manager Network Protocol',
        'Description': 'Manager Network Services',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'HostName': 'bmc',
        'FQDN': 'bmc.example.com',
        'HTTP': {'ProtocolEnabled': True, 'Port': 80},
        'HTTPS': {
            'ProtocolEnabled': True,
            'Port': 443,
            'Certificates': {'@odata.id': f'{BASE}/bmc/NetworkProtocol/HTTPS/Certificates/'}
        },
        'SSH': {'ProtocolEnabled': True, 'Port': 22},
        'IPMI': {'ProtocolEnabled': True, 'Port': 623},
        'NTP': {
            'ProtocolEnabled': True,
            'Port': 123,
            'NTPServers': ['pool.ntp.org'],
            'NetworkSuppliedServers': []
        }
    })


@bp.route('/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates/')
def https_certificates():
    db = get_db()
    rows = db.execute(
        "SELECT id FROM certificates WHERE parent_path=?",
        ('/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates',)
    ).fetchall()
    members = [{'@odata.id': f'{BASE}/bmc/NetworkProtocol/HTTPS/Certificates/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/bmc/NetworkProtocol/HTTPS/Certificates/',
        '@odata.type': '#CertificateCollection.CertificateCollection',
        'Name': 'HTTPS Certificate Collection',
        'Description': 'HTTPS Certificates',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates/<cert_id>/')
def https_certificate(cert_id):
    db = get_db()
    row = db.execute(
        "SELECT * FROM certificates WHERE id=? AND parent_path=?",
        (cert_id, '/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates')
    ).fetchone()
    if not row:
        return not_found_response()
    issuer = json.loads(row['issuer']) if row['issuer'] else {}
    subject = json.loads(row['subject']) if row['subject'] else {}
    key_usage = json.loads(row['key_usage']) if row['key_usage'] else []
    return json_response({
        '@odata.id': f'{BASE}/bmc/NetworkProtocol/HTTPS/Certificates/{cert_id}/',
        '@odata.type': '#Certificate.v1_6_0.Certificate',
        'Id': cert_id,
        'Name': 'HTTPS Certificate',
        'Description': row['description'],
        'CertificateString': row['certificate_string'],
        'Issuer': issuer,
        'Subject': subject,
        'KeyUsage': key_usage,
        'ValidNotBefore': row['valid_not_before'],
        'ValidNotAfter': row['valid_not_after']
    })


@bp.route('/redfish/v1/Managers/bmc/Truststore/Certificates/')
def truststore_certificates():
    return json_response({
        '@odata.id': f'{BASE}/bmc/Truststore/Certificates/',
        '@odata.type': '#CertificateCollection.CertificateCollection',
        'Name': 'Truststore Certificate Collection',
        'Description': 'Truststore Certificates',
        'Members@odata.count': 0,
        'Members': []
    })
