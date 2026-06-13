import json
import sqlite3
import uuid
from fastapi import APIRouter, Depends, Body
from ..database import get_db
from ..auth import verify_auth
from ..helpers import (json_response, not_found_response, bad_request_response,
                       no_content_response, created_response, log_entry_to_dict, now_iso)

router = APIRouter(dependencies=[Depends(verify_auth)])

BASE = '/redfish/v1/Chassis'


@router.get('/redfish/v1/Chassis/')
def chassis_collection(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute('SELECT id FROM chassis').fetchall()
    members = [{'@odata.id': f'{BASE}/{row["id"]}/'} for row in rows]
    return json_response({
        '@odata.id': '/redfish/v1/Chassis/',
        '@odata.type': '#ChassisCollection.ChassisCollection',
        'Name': 'Chassis Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/')
def chassis(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM chassis WHERE id=?', (chassis_id,)).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/',
        '@odata.type': '#Chassis.v1_22_0.Chassis',
        'Id': chassis_id, 'Name': chassis_id,
        'ChassisType': row['chassis_type'],
        'PowerState': row['power_state'],
        'Status': {'State': row['status_state'], 'Health': row['status_health']},
        'Power': {'@odata.id': f'{BASE}/{chassis_id}/Power/'},
        'Thermal': {'@odata.id': f'{BASE}/{chassis_id}/Thermal/'},
        'Sensors': {'@odata.id': f'{BASE}/{chassis_id}/Sensors/'},
        'Assembly': {'@odata.id': f'{BASE}/{chassis_id}/Assembly/'},
        'PCIeDevices': {'@odata.id': f'{BASE}/{chassis_id}/PCIeSlots/'},
        'ThermalSubsystem': {'@odata.id': f'{BASE}/{chassis_id}/ThermalSubsystem'},
        'LogServices': {'@odata.id': f'{BASE}/{chassis_id}/LogServices/'},
        'Links': {
            'ComputerSystems': [{'@odata.id': '/redfish/v1/Systems/system'}],
            'ManagedBy': [{'@odata.id': '/redfish/v1/Managers/bmc/'}]
        },
        'Actions': {
            '#Chassis.Reset': {
                'target': f'{BASE}/{chassis_id}/Actions/Chassis.Reset',
                'ResetType@Redfish.AllowableValues': ['On', 'ForceOff', 'PowerCycle']
            }
        }
    })


_CHASSIS_RESET_TYPES = {'On', 'ForceOff', 'PowerCycle'}


@router.post('/redfish/v1/Chassis/{chassis_id}/Actions/Chassis.Reset')
def chassis_reset(
    chassis_id: str,
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    data = body or {}
    reset_type = data.get('ResetType')
    if reset_type not in _CHASSIS_RESET_TYPES:
        return bad_request_response(f'Invalid ResetType. Allowable values: {sorted(_CHASSIS_RESET_TYPES)}')
    new_state = 'Off' if reset_type == 'ForceOff' else 'On'
    db.execute('UPDATE chassis SET power_state=? WHERE id=?', (new_state, chassis_id))
    db.commit()
    return no_content_response()


@router.get('/redfish/v1/Chassis/{chassis_id}/Assembly/')
def assembly(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/Assembly/',
        '@odata.type': '#Assembly.v1_4_0.Assembly',
        'Id': 'Assembly', 'Name': 'Assembly',
        'Assemblies': [{
            '@odata.id': f'{BASE}/{chassis_id}/Assembly/Assemblies#/0',
            'MemberId': '0', 'Name': 'Chassis Assembly',
            'Model': 'PowerEdge R750', 'PartNumber': 'PN-CHASSIS',
            'SerialNumber': 'SN-CHASSIS', 'SparePartNumber': 'SPARE-CHASSIS', 'Location': {}
        }]
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/Drive/')
def chassis_drives(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    rows = db.execute('SELECT id FROM drives WHERE chassis_id=?', (chassis_id,)).fetchall()
    members = [{'@odata.id': f'{BASE}/{chassis_id}/Drive/{row["id"]}/'} for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/Drive/',
        '@odata.type': '#DriveCollection.DriveCollection',
        'Name': 'Drive Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/Drive/{drive_id}/')
def chassis_drive(chassis_id: str, drive_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM drives WHERE id=? AND chassis_id=?', (drive_id, chassis_id)).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/Drive/{drive_id}/',
        '@odata.type': '#Drive.v1_17_0.Drive',
        'Id': row['id'], 'Name': row['id'],
        'CapacityBytes': row['capacity_bytes'],
        'EncryptionStatus': row['encryption_status'],
        'Status': {'State': row['status_state'], 'Health': row['status_health']}
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/EnvironmentMetrics/')
def environment_metrics(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/EnvironmentMetrics/',
        '@odata.type': '#EnvironmentMetrics.v1_3_0.EnvironmentMetrics',
        'Id': 'EnvironmentMetrics', 'Name': 'Environment Metrics'
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/Thermal/')
def thermal(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    temps = db.execute('SELECT * FROM temperatures WHERE chassis_id=?', (chassis_id,)).fetchall()
    fans = db.execute('SELECT * FROM fans WHERE chassis_id=?', (chassis_id,)).fetchall()
    temp_list = []
    for t in temps:
        entry = {
            '@odata.id': f'{BASE}/{chassis_id}/Thermal#/Temperatures/{t["member_id"]}',
            'MemberId': t['member_id'], 'Name': t['name'],
            'ReadingCelsius': t['reading_celsius'],
            'Status': {'State': t['status_state'], 'Health': t['status_health']},
            'MinReadingRange': t['min_reading_range'], 'MaxReadingRange': t['max_reading_range']
        }
        for k, c in [('UpperThresholdNonCritical', 'upper_threshold_non_critical'),
                     ('UpperThresholdCritical', 'upper_threshold_critical'),
                     ('LowerThresholdNonCritical', 'lower_threshold_non_critical'),
                     ('LowerThresholdCritical', 'lower_threshold_critical')]:
            if t[c] is not None:
                entry[k] = t[c]
        temp_list.append(entry)
    fan_list = []
    for f in fans:
        entry = {
            '@odata.id': f'{BASE}/{chassis_id}/Thermal#/Fans/{f["member_id"]}',
            'MemberId': f['member_id'], 'Name': f['name'],
            'Reading': f['reading'], 'ReadingUnits': f['reading_units'],
            'Status': {'State': f['status_state'], 'Health': f['status_health']},
            'MinReadingRange': f['min_reading_range'], 'MaxReadingRange': f['max_reading_range']
        }
        for k, c in [('UpperThresholdNonCritical', 'upper_threshold_non_critical'),
                     ('UpperThresholdCritical', 'upper_threshold_critical'),
                     ('LowerThresholdNonCritical', 'lower_threshold_non_critical'),
                     ('LowerThresholdCritical', 'lower_threshold_critical')]:
            if f[c] is not None:
                entry[k] = f[c]
        fan_list.append(entry)
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/Thermal/',
        '@odata.type': '#Thermal.v1_7_1.Thermal',
        'Id': 'Thermal', 'Name': 'Thermal',
        'Temperatures': temp_list, 'Fans': fan_list, 'Redundancy': []
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/Power/')
def power(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    controls = db.execute('SELECT * FROM power_controls WHERE chassis_id=?', (chassis_id,)).fetchall()
    voltages = db.execute('SELECT * FROM voltages WHERE chassis_id=?', (chassis_id,)).fetchall()
    psus = db.execute('SELECT * FROM power_supplies WHERE chassis_id=?', (chassis_id,)).fetchall()
    power_controls = []
    for pc in controls:
        power_controls.append({
            '@odata.id': f'{BASE}/{chassis_id}/Power#/PowerControl/{pc["member_id"]}',
            'MemberId': pc['member_id'], 'Name': pc['member_id'],
            'PowerConsumedWatts': pc['power_consumed_watts'],
            'PowerMetrics': {
                'IntervalInMin': pc['power_metrics_interval_min'],
                'MinConsumedWatts': pc['power_metrics_min_consumed_watts'],
                'MaxConsumedWatts': pc['power_metrics_max_consumed_watts'],
                'AverageConsumedWatts': pc['power_metrics_avg_consumed_watts']
            },
            'RelatedItem': [
                {'@odata.id': '/redfish/v1/Systems/system'},
                {'@odata.id': f'{BASE}/{chassis_id}/'}
            ]
        })
    voltage_list = []
    for v in voltages:
        entry = {
            '@odata.id': f'{BASE}/{chassis_id}/Power#/Voltages/{v["member_id"]}',
            'MemberId': v['member_id'], 'Name': v['name'],
            'ReadingVolts': v['reading_volts'],
            'Status': {'State': v['status_state'], 'Health': v['status_health']},
            'PhysicalContext': v['physical_context'],
            'MinReadingRange': v['min_reading_range'], 'MaxReadingRange': v['max_reading_range'],
            'RelatedItem': [{'@odata.id': f'{BASE}/{chassis_id}/'}]
        }
        for k, c in [('UpperThresholdNonCritical', 'upper_threshold_non_critical'),
                     ('UpperThresholdCritical', 'upper_threshold_critical'),
                     ('LowerThresholdNonCritical', 'lower_threshold_non_critical'),
                     ('LowerThresholdCritical', 'lower_threshold_critical')]:
            if v[c] is not None:
                entry[k] = v[c]
        voltage_list.append(entry)
    psu_list = [{
        '@odata.id': f'{BASE}/{chassis_id}/Power#/PowerSupplies/{p["member_id"]}',
        'MemberId': p['member_id'], 'Name': p['member_id'],
        'Model': p['model'], 'Manufacturer': p['manufacturer'],
        'FirmwareVersion': p['firmware_version'], 'SerialNumber': p['serial_number'],
        'PartNumber': p['part_number'], 'LineInputVoltage': p['line_input_voltage'],
        'Status': {'State': p['status_state'], 'Health': p['status_health']},
        'RelatedItem': [{'@odata.id': f'{BASE}/{chassis_id}/'}]
    } for p in psus]
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/Power/',
        '@odata.type': '#Power.v1_7_1.Power',
        'Id': 'Power', 'Name': 'Power',
        'PowerControl': power_controls,
        'Voltages': voltage_list,
        'PowerSupplies': psu_list,
        'Redundancy': []
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/Sensors/')
def sensors_collection(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    rows = db.execute('SELECT id FROM sensors WHERE chassis_id=?', (chassis_id,)).fetchall()
    members = [{'@odata.id': f'{BASE}/{chassis_id}/Sensors/{row["id"]}/'} for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/Sensors/',
        '@odata.type': '#SensorCollection.SensorCollection',
        'Name': 'Sensor Collection', 'Description': 'List of sensors',
        'Members@odata.count': len(members), 'Members': members
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/Sensors/{sensor_id}/')
def sensor(chassis_id: str, sensor_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM sensors WHERE id=? AND chassis_id=?', (sensor_id, chassis_id)).fetchone()
    if not row:
        return not_found_response()
    thresholds = json.loads(row['thresholds']) if row['thresholds'] else {}
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/Sensors/{sensor_id}/',
        '@odata.type': '#Sensor.v1_7_0.Sensor',
        'Id': row['id'], 'Name': row['name'],
        'Reading': row['reading'], 'ReadingType': row['reading_type'],
        'ReadingUnits': row['reading_units'],
        'ReadingRangeMax': row['reading_range_max'], 'ReadingRangeMin': row['reading_range_min'],
        'Status': {'State': row['status_state'], 'Health': row['status_health']},
        'Thresholds': thresholds
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/ThermalSubsystem')
def thermal_subsystem(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/ThermalSubsystem',
        '@odata.type': '#ThermalSubsystem.v1_3_2.ThermalSubsystem',
        'Id': 'ThermalSubsystem', 'Name': 'Thermal Subsystem',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'Fans': {'@odata.id': f'{BASE}/{chassis_id}/ThermalSubsystem/Fans'}
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/ThermalSubsystem/Fans')
def thermal_fans_collection(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    rows = db.execute('SELECT member_id FROM fans WHERE chassis_id=?', (chassis_id,)).fetchall()
    members = [{'@odata.id': f'{BASE}/{chassis_id}/ThermalSubsystem/Fans/{row["member_id"]}/'} for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/ThermalSubsystem/Fans',
        '@odata.type': '#FanCollection.FanCollection',
        'Name': 'Fan Collection', 'Description': 'List of fans',
        'Members@odata.count': len(members), 'Members': members
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/ThermalSubsystem/Fans/{fan_name}/')
def thermal_fan(chassis_id: str, fan_name: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM fans WHERE member_id=? AND chassis_id=?', (fan_name, chassis_id)).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/ThermalSubsystem/Fans/{fan_name}/',
        '@odata.type': '#Fan.v1_5_0.Fan',
        'Id': row['member_id'], 'Name': row['name'],
        'Status': {'State': row['status_state'], 'Health': row['status_health']},
        'Location': {}, 'Manufacturer': 'Generic', 'Model': 'Fan',
        'SerialNumber': f'SN-{row["member_id"]}',
        'PartNumber': f'PN-{row["member_id"]}',
        'SparePartNumber': f'SPARE-{row["member_id"]}'
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/PowerSubsystem/')
@router.get('/redfish/v1/Chassis/{chassis_id}/PowerSubsystem')
def power_subsystem(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/PowerSubsystem',
        '@odata.type': '#PowerSubsystem.v1_1_0.PowerSubsystem',
        'Id': 'PowerSubsystem', 'Name': 'Power Subsystem',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'PowerSupplies': {'@odata.id': f'{BASE}/{chassis_id}/PowerSubsystem/PowerSupplies'},
        'PowerAllocationWatts': 1500.0
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/PowerSubsystem/PowerSupplies')
def power_supplies_collection(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    rows = db.execute('SELECT member_id FROM power_supplies WHERE chassis_id=?', (chassis_id,)).fetchall()
    members = [{'@odata.id': f'{BASE}/{chassis_id}/PowerSubsystem/PowerSupplies/{row["member_id"]}'} for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/PowerSubsystem/PowerSupplies',
        '@odata.type': '#PowerSupplyCollection.PowerSupplyCollection',
        'Name': 'Power Supply Collection', 'Description': 'List of power supplies',
        'Members@odata.count': len(members), 'Members': members
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/PowerSubsystem/PowerSupplies/{psu_id}')
def power_supply(chassis_id: str, psu_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM power_supplies WHERE member_id=? AND chassis_id=?', (psu_id, chassis_id)).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/PowerSubsystem/PowerSupplies/{psu_id}',
        '@odata.type': '#PowerSupply.v1_5_1.PowerSupply',
        'Id': row['member_id'], 'Name': row['member_id'],
        'Model': row['model'], 'Manufacturer': row['manufacturer'],
        'FirmwareVersion': row['firmware_version'], 'SerialNumber': row['serial_number'],
        'PartNumber': row['part_number'],
        'Status': {'State': row['status_state'], 'Health': row['status_health']},
        'EfficiencyRatings': [{'EfficiencyPercent': 92.0}],
        'Location': {}, 'SparePartNumber': f'SPARE-{row["member_id"]}'
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/PCIeSlots/')
def pcie_slots(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    rows = db.execute('SELECT * FROM pcie_slots WHERE chassis_id=?', (chassis_id,)).fetchall()
    members = [{'@odata.id': f'{BASE}/{chassis_id}/PCIeSlots/{row["id"]}'} for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/PCIeSlots/',
        '@odata.type': '#PCIeSlots.v1_6_1.PCIeSlots',
        'Id': 'PCIeSlots', 'Name': 'PCIe Slots',
        'Members': members
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/PCIeSlots/{slot_name}')
def pcie_slot(chassis_id: str, slot_name: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM pcie_slots WHERE id=? AND chassis_id=?', (slot_name, chassis_id)).fetchone()
    if not row:
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/PCIeSlots/{slot_name}',
        '@odata.type': '#PCIeSlots.v1_6_1.PCIeSlots',
        'Id': row['id'], 'Name': row['id'],
        'HotPluggable': bool(row['hotpluggable']),
        'Lanes': row['lanes'], 'PCIeType': row['pcie_type'], 'SlotType': row['slot_type']
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/LogServices/')
def chassis_log_services(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/LogServices/',
        '@odata.type': '#LogServiceCollection.LogServiceCollection',
        'Name': 'Log Service Collection', 'Description': 'List of log services',
        'Members@odata.count': 1,
        'Members': [{'@odata.id': f'{BASE}/{chassis_id}/LogServices/Log/'}]
    })


@router.get('/redfish/v1/Chassis/{chassis_id}/LogServices/Log/')
def chassis_log_service(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/LogServices/Log/',
        '@odata.type': '#LogService.v1_4_0.LogService',
        'Id': 'Log', 'Name': 'Chassis Log', 'Description': 'Chassis Log Service',
        'DateTime': now_iso(), 'DateTimeLocalOffset': '+00:00',
        'MaxNumberOfRecords': 4096, 'OverWritePolicy': 'WrapsWhenFull',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'Entries': {'@odata.id': f'{BASE}/{chassis_id}/LogServices/Log/Entries/'},
        'Actions': {'#LogService.ClearLog': {
            'target': f'{BASE}/{chassis_id}/LogServices/Log/Actions/LogService.ClearLog'
        }}
    })


@router.post('/redfish/v1/Chassis/{chassis_id}/LogServices/Log/Actions/LogService.ClearLog')
def chassis_log_clear(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    db.execute("DELETE FROM log_entries WHERE log_service_id='Log' AND parent_type='chassis'")
    db.commit()
    return no_content_response()


@router.get('/redfish/v1/Chassis/{chassis_id}/LogServices/Log/Entries/')
def chassis_log_entries(chassis_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    rows = db.execute(
        "SELECT * FROM log_entries WHERE log_service_id='Log' AND parent_type='chassis'"
    ).fetchall()
    members = [{'@odata.id': f'{BASE}/{chassis_id}/LogServices/Log/Entries/{row["id"]}/'} for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/{chassis_id}/LogServices/Log/Entries/',
        '@odata.type': '#LogEntryCollection.LogEntryCollection',
        'Name': 'Log Entry Collection', 'Description': 'Chassis log entries',
        'Members@odata.count': len(members), 'Members': members
    })


@router.post('/redfish/v1/Chassis/{chassis_id}/LogServices/Log/Entries/')
def chassis_log_entries_post(
    chassis_id: str,
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    return _create_log_entry(db, 'Log', 'chassis',
                             f'{BASE}/{chassis_id}/LogServices/Log/Entries/', body or {})


@router.get('/redfish/v1/Chassis/{chassis_id}/LogServices/Log/Entries/{entry_id}/')
def chassis_log_entry_get(chassis_id: str, entry_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    row = db.execute(
        "SELECT * FROM log_entries WHERE id=? AND log_service_id='Log' AND parent_type='chassis'",
        (entry_id,)
    ).fetchone()
    if not row:
        return not_found_response()
    return json_response(log_entry_to_dict(row, f'{BASE}/{chassis_id}/LogServices/Log/Entries/{entry_id}/'))


@router.patch('/redfish/v1/Chassis/{chassis_id}/LogServices/Log/Entries/{entry_id}/')
def chassis_log_entry_patch(
    chassis_id: str,
    entry_id: str,
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    odata_id = f'{BASE}/{chassis_id}/LogServices/Log/Entries/{entry_id}/'
    if not db.execute(
        "SELECT id FROM log_entries WHERE id=? AND log_service_id='Log' AND parent_type='chassis'",
        (entry_id,)
    ).fetchone():
        return not_found_response()
    return _patch_log_entry(db, entry_id, odata_id, body or {})


@router.delete('/redfish/v1/Chassis/{chassis_id}/LogServices/Log/Entries/{entry_id}/')
def chassis_log_entry_delete(chassis_id: str, entry_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM chassis WHERE id=?', (chassis_id,)).fetchone():
        return not_found_response()
    if not db.execute(
        "SELECT id FROM log_entries WHERE id=? AND log_service_id='Log' AND parent_type='chassis'",
        (entry_id,)
    ).fetchone():
        return not_found_response()
    db.execute('DELETE FROM log_entries WHERE id=?', (entry_id,))
    db.commit()
    return no_content_response()


def _create_log_entry(db, log_service_id, parent_type, collection_path, data):
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
         data.get('EntryType', 'Event'), data.get('Severity', 'OK'),
         data['Message'], data.get('MessageId', ''),
         json.dumps(data.get('MessageArgs', [])),
         now, now, 0,
         data.get('SensorType'), data.get('EntryCode'), data.get('AdditionalDataURI'))
    )
    db.commit()
    row = db.execute('SELECT * FROM log_entries WHERE id=?', (entry_id,)).fetchone()
    odata_id = f'{collection_path}{entry_id}/'
    return created_response(log_entry_to_dict(row, odata_id), location=odata_id)


def _patch_log_entry(db, entry_id, odata_id, data):
    fields, values = [], []
    if 'Resolved' in data:
        fields.append('resolved=?'); values.append(1 if data['Resolved'] else 0)
    if 'Message' in data:
        fields.append('message=?'); values.append(data['Message'])
    if 'Severity' in data:
        fields.append('severity=?'); values.append(data['Severity'])
    if fields:
        fields.append('modified=?'); values.append(now_iso())
        values.append(entry_id)
        db.execute(f'UPDATE log_entries SET {", ".join(fields)} WHERE id=?', values)
        db.commit()
    row = db.execute('SELECT * FROM log_entries WHERE id=?', (entry_id,)).fetchone()
    return json_response(log_entry_to_dict(row, odata_id))
