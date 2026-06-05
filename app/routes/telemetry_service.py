from flask import Blueprint
from ..database import get_db
from ..helpers import json_response

bp = Blueprint('telemetry_service', __name__)

BASE = '/redfish/v1/TelemetryService'


@bp.route('/redfish/v1/TelemetryService/')
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


@bp.route('/redfish/v1/TelemetryService/MetricReportDefinitions/')
def metric_report_definitions():
    db = get_db()
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


@bp.route('/redfish/v1/TelemetryService/MetricReports/')
def metric_reports():
    db = get_db()
    rows = db.execute('SELECT id FROM metric_reports').fetchall()
    members = [{'@odata.id': f'{BASE}/MetricReports/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/MetricReports/',
        '@odata.type': '#MetricReportCollection.MetricReportCollection',
        'Name': 'Metric Report Collection',
        'Members@odata.count': len(members),
        'Members': members
    })


@bp.route('/redfish/v1/TelemetryService/Triggers/')
def triggers():
    db = get_db()
    rows = db.execute('SELECT id FROM triggers').fetchall()
    members = [{'@odata.id': f'{BASE}/Triggers/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': f'{BASE}/Triggers/',
        '@odata.type': '#TriggersCollection.TriggersCollection',
        'Name': 'Triggers Collection',
        'Members@odata.count': len(members),
        'Members': members
    })
