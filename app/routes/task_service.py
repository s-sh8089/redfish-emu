import json
from flask import Blueprint
from ..database import get_db
from ..helpers import json_response

bp = Blueprint('task_service', __name__)


@bp.route('/redfish/v1/TaskService/')
def task_service():
    db = get_db()
    count = db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0]
    return json_response({
        '@odata.id': '/redfish/v1/TaskService/',
        '@odata.type': '#TaskService.v1_2_0.TaskService',
        'Id': 'TaskService',
        'Name': 'Task Service',
        'ServiceEnabled': True,
        'CompletedTaskOverWritePolicy': 'Oldest',
        'LifeCycleEventOnTaskStateChange': True,
        'DateTime': '2024-01-01T00:00:00Z',
        'Status': {'State': 'Enabled', 'Health': 'OK'},
        'Tasks': {'@odata.id': '/redfish/v1/TaskService/Tasks/'}
    })


@bp.route('/redfish/v1/TaskService/Tasks/')
def tasks():
    db = get_db()
    rows = db.execute('SELECT id FROM tasks').fetchall()
    members = [{'@odata.id': f'/redfish/v1/TaskService/Tasks/{row["id"]}/'}
               for row in rows]
    return json_response({
        '@odata.id': '/redfish/v1/TaskService/Tasks/',
        '@odata.type': '#TaskCollection.TaskCollection',
        'Name': 'Task Collection',
        'Members@odata.count': len(members),
        'Members': members
    })
