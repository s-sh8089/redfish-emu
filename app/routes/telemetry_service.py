import json
import sqlite3
import uuid
from fastapi import APIRouter, Depends, Body
from ..database import get_db
from ..auth import verify_auth
from ..helpers import json_response, not_found_response, bad_request_response, created_response, no_content_response

router = APIRouter(dependencies=[Depends(verify_auth)])

BASE = '/redfish/v1/TelemetryService'


@router.get('/redfish/v1/TelemetryService/')
def telemetry_service():
    return json_response({
        '@odata.id': f'{BASE}/',
        '@odata.type': '#TelemetryService.v1_3_2.TelemetryService',
        'Id': 'TelemetryService',
        'Name': 'Telemetry Service',
        'ServiceEnabled': True,
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'MaxReports': 100,
        'MinCollectionInterval': 'PT5S',
        'MetricReportDefinitions': {'@odata.id': f'{BASE}/MetricReportDefinitions/'},
        'MetricReports': {'@odata.id': f'{BASE}/MetricReports/'},
        'Triggers': {'@odata.id': f'{BASE}/Triggers/'}
    })


@router.get('/redfish/v1/TelemetryService/MetricReportDefinitions/')
def metric_report_definitions(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute('SELECT id FROM metric_report_definitions').fetchall()
    members = [{'@odata.id': f'{BASE}/MetricReportDefinitions/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/MetricReportDefinitions/',
        '@odata.type': '#MetricReportDefinitionCollection.MetricReportDefinitionCollection',
        'Name': 'Metric Report Definition Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@router.post('/redfish/v1/TelemetryService/MetricReportDefinitions/')
def metric_report_definitions_post(
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    data = body or {}
    if not data or 'Name' not in data:
        return bad_request_response('Name is required.')
    def_id = data.get('Id', str(uuid.uuid4()).replace('-', '')[:12])
    db.execute(
        '''INSERT INTO metric_report_definitions
           (id, name, description, report_type, report_actions, metrics, schedule, status_state, status_health)
           VALUES (?,?,?,?,?,?,?,?,?)''',
        (def_id, data['Name'], data.get('Description', ''),
         data.get('MetricReportDefinitionType', 'Periodic'),
         json.dumps(data.get('ReportActions', [])),
         json.dumps(data.get('Metrics', [])),
         json.dumps(data.get('Schedule', {})),
         'Enabled', 'OK')
    )
    db.commit()
    row = db.execute('SELECT * FROM metric_report_definitions WHERE id=?', (def_id,)).fetchone()
    return created_response(_definition_to_dict(row), location=f'{BASE}/MetricReportDefinitions/{def_id}/')


@router.get('/redfish/v1/TelemetryService/MetricReportDefinitions/{def_id}/')
def metric_report_definition_get(def_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM metric_report_definitions WHERE id=?', (def_id,)).fetchone()
    if not row:
        return not_found_response()
    return json_response(_definition_to_dict(row))


@router.patch('/redfish/v1/TelemetryService/MetricReportDefinitions/{def_id}/')
def metric_report_definition_patch(
    def_id: str,
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    if not db.execute('SELECT id FROM metric_report_definitions WHERE id=?', (def_id,)).fetchone():
        return not_found_response()
    data = body or {}
    fields, values = [], []
    if 'Name' in data:
        fields.append('name=?'); values.append(data['Name'])
    if 'Description' in data:
        fields.append('description=?'); values.append(data['Description'])
    if 'MetricReportDefinitionType' in data:
        fields.append('report_type=?'); values.append(data['MetricReportDefinitionType'])
    if 'ReportActions' in data:
        fields.append('report_actions=?'); values.append(json.dumps(data['ReportActions']))
    if 'Metrics' in data:
        fields.append('metrics=?'); values.append(json.dumps(data['Metrics']))
    if 'Schedule' in data:
        fields.append('schedule=?'); values.append(json.dumps(data['Schedule']))
    if fields:
        values.append(def_id)
        db.execute(f'UPDATE metric_report_definitions SET {", ".join(fields)} WHERE id=?', values)
        db.commit()
    row = db.execute('SELECT * FROM metric_report_definitions WHERE id=?', (def_id,)).fetchone()
    return json_response(_definition_to_dict(row))


@router.delete('/redfish/v1/TelemetryService/MetricReportDefinitions/{def_id}/')
def metric_report_definition_delete(def_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM metric_report_definitions WHERE id=?', (def_id,)).fetchone():
        return not_found_response()
    db.execute('DELETE FROM metric_report_definitions WHERE id=?', (def_id,))
    db.commit()
    return no_content_response()


@router.get('/redfish/v1/TelemetryService/MetricReports/')
def metric_reports(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute('SELECT id FROM metric_reports').fetchall()
    members = [{'@odata.id': f'{BASE}/MetricReports/{row["id"]}/'} for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/MetricReports/',
        '@odata.type': '#MetricReportCollection.MetricReportCollection',
        'Name': 'Metric Report Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@router.get('/redfish/v1/TelemetryService/MetricReports/{report_id}/')
def metric_report_get(report_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM metric_reports WHERE id=?', (report_id,)).fetchone()
    if not row:
        return not_found_response()
    return json_response(_report_to_dict(row))


@router.delete('/redfish/v1/TelemetryService/MetricReports/{report_id}/')
def metric_report_delete(report_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM metric_reports WHERE id=?', (report_id,)).fetchone():
        return not_found_response()
    db.execute('DELETE FROM metric_reports WHERE id=?', (report_id,))
    db.commit()
    return no_content_response()


@router.get('/redfish/v1/TelemetryService/Triggers/')
def triggers(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute('SELECT id FROM triggers').fetchall()
    members = [{'@odata.id': f'{BASE}/Triggers/{row["id"]}/'} for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/Triggers/',
        '@odata.type': '#TriggersCollection.TriggersCollection',
        'Name': 'Triggers Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@router.post('/redfish/v1/TelemetryService/Triggers/')
def triggers_post(
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    data = body or {}
    if not data or 'Name' not in data:
        return bad_request_response('Name is required.')
    trig_id = data.get('Id', str(uuid.uuid4()).replace('-', '')[:12])
    db.execute(
        '''INSERT INTO triggers
           (id, name, description, metric_type, trigger_actions, metric_properties,
            numeric_thresholds, discrete_values, status_state, status_health)
           VALUES (?,?,?,?,?,?,?,?,?,?)''',
        (trig_id, data['Name'], data.get('Description', ''),
         data.get('MetricType', 'Numeric'),
         json.dumps(data.get('TriggerActions', [])),
         json.dumps(data.get('MetricProperties', [])),
         json.dumps(data.get('NumericThresholds', {})),
         json.dumps(data.get('DiscreteValues', [])),
         'Enabled', 'OK')
    )
    db.commit()
    row = db.execute('SELECT * FROM triggers WHERE id=?', (trig_id,)).fetchone()
    return created_response(_trigger_to_dict(row), location=f'{BASE}/Triggers/{trig_id}/')


@router.get('/redfish/v1/TelemetryService/Triggers/{trig_id}/')
def trigger_get(trig_id: str, db: sqlite3.Connection = Depends(get_db)):
    row = db.execute('SELECT * FROM triggers WHERE id=?', (trig_id,)).fetchone()
    if not row:
        return not_found_response()
    return json_response(_trigger_to_dict(row))


@router.patch('/redfish/v1/TelemetryService/Triggers/{trig_id}/')
def trigger_patch(
    trig_id: str,
    body: dict | None = Body(default=None),
    db: sqlite3.Connection = Depends(get_db),
):
    if not db.execute('SELECT id FROM triggers WHERE id=?', (trig_id,)).fetchone():
        return not_found_response()
    data = body or {}
    fields, values = [], []
    if 'Name' in data:
        fields.append('name=?'); values.append(data['Name'])
    if 'Description' in data:
        fields.append('description=?'); values.append(data['Description'])
    if 'MetricType' in data:
        fields.append('metric_type=?'); values.append(data['MetricType'])
    if 'TriggerActions' in data:
        fields.append('trigger_actions=?'); values.append(json.dumps(data['TriggerActions']))
    if 'MetricProperties' in data:
        fields.append('metric_properties=?'); values.append(json.dumps(data['MetricProperties']))
    if 'NumericThresholds' in data:
        fields.append('numeric_thresholds=?'); values.append(json.dumps(data['NumericThresholds']))
    if 'DiscreteValues' in data:
        fields.append('discrete_values=?'); values.append(json.dumps(data['DiscreteValues']))
    if fields:
        values.append(trig_id)
        db.execute(f'UPDATE triggers SET {", ".join(fields)} WHERE id=?', values)
        db.commit()
    row = db.execute('SELECT * FROM triggers WHERE id=?', (trig_id,)).fetchone()
    return json_response(_trigger_to_dict(row))


@router.delete('/redfish/v1/TelemetryService/Triggers/{trig_id}/')
def trigger_delete(trig_id: str, db: sqlite3.Connection = Depends(get_db)):
    if not db.execute('SELECT id FROM triggers WHERE id=?', (trig_id,)).fetchone():
        return not_found_response()
    db.execute('DELETE FROM triggers WHERE id=?', (trig_id,))
    db.commit()
    return no_content_response()


def _definition_to_dict(row) -> dict:
    report_actions = json.loads(row['report_actions']) if row['report_actions'] else []
    metrics = json.loads(row['metrics']) if row['metrics'] else []
    schedule = json.loads(row['schedule']) if row['schedule'] else {}
    d = {
        '@odata.id': f'{BASE}/MetricReportDefinitions/{row["id"]}/',
        '@odata.type': '#MetricReportDefinition.v1_4_2.MetricReportDefinition',
        'Id': row['id'],
        'Name': row['name'] or '',
        'Description': row['description'] or '',
        'MetricReportDefinitionType': row['report_type'] or 'Periodic',
        'ReportActions': report_actions,
        'Metrics': metrics,
        'Status': {'State': row['status_state'] or 'Enabled', 'Health': row['status_health'] or 'OK'},
        'MetricReport': {'@odata.id': f'{BASE}/MetricReports/{row["id"]}/'},
    }
    if schedule:
        d['Schedule'] = schedule
    return d


def _report_to_dict(row) -> dict:
    metric_values = json.loads(row['metric_values']) if row['metric_values'] else []
    d = {
        '@odata.id': f'{BASE}/MetricReports/{row["id"]}/',
        '@odata.type': '#MetricReport.v1_5_0.MetricReport',
        'Id': row['id'],
        'Name': row['name'] or '',
        'Description': row['description'] or '',
        'Timestamp': row['timestamp'] or '',
        'MetricValues': metric_values,
    }
    if row['definition_id']:
        d['MetricReportDefinition'] = {'@odata.id': f'{BASE}/MetricReportDefinitions/{row["definition_id"]}/'}
    return d


def _trigger_to_dict(row) -> dict:
    trigger_actions = json.loads(row['trigger_actions']) if row['trigger_actions'] else []
    metric_properties = json.loads(row['metric_properties']) if row['metric_properties'] else []
    numeric_thresholds = json.loads(row['numeric_thresholds']) if row['numeric_thresholds'] else {}
    discrete_values = json.loads(row['discrete_values']) if row['discrete_values'] else []
    d = {
        '@odata.id': f'{BASE}/Triggers/{row["id"]}/',
        '@odata.type': '#Triggers.v1_3_1.Triggers',
        'Id': row['id'],
        'Name': row['name'] or '',
        'Description': row['description'] or '',
        'MetricType': row['metric_type'] or 'Numeric',
        'TriggerActions': trigger_actions,
        'MetricProperties': metric_properties,
        'Status': {'State': row['status_state'] or 'Enabled', 'Health': row['status_health'] or 'OK'},
    }
    if numeric_thresholds:
        d['NumericThresholds'] = numeric_thresholds
    if discrete_values:
        d['DiscreteValues'] = discrete_values
    return d
