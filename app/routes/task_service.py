import json
import uuid
from datetime import datetime, timezone
from flask import Blueprint, request
from ..database import get_db
from ..helpers import json_response, not_found_response, no_content_response

bp = Blueprint('task_service', __name__)


def create_task(db, messages=None):
    """Create a Running task and return its ID."""
    task_id = str(uuid.uuid4()).replace('-', '')[:12]
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        'INSERT INTO tasks (id, task_state, task_status, start_time, end_time, messages) VALUES (?,?,?,?,?,?)',
        (task_id, 'Running', 'OK', now, None, json.dumps(messages or []))
    )
    db.commit()
    return task_id


def complete_task(db, task_id, messages=None, status='OK'):
    now = datetime.now(timezone.utc).isoformat()
    db.execute(
        'UPDATE tasks SET task_state="Completed", task_status=?, end_time=?, messages=? WHERE id=?',
        (status, now, json.dumps(messages or []), task_id)
    )
    db.commit()


@bp.route('/redfish/v1/TaskService/')
def task_service():
    return json_response({
        '@odata.id': '/redfish/v1/TaskService/',
        '@odata.type': '#TaskService.v1_2_0.TaskService',
        'Id': 'TaskService',
        'Name': 'Task Service',
        'ServiceEnabled': True,
        'CompletedTaskOverWritePolicy': 'Oldest',
        'LifeCycleEventOnTaskStateChange': True,
        'DateTime': datetime.now(timezone.utc).isoformat(),
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


@bp.route('/redfish/v1/TaskService/Tasks/<task_id>/', methods=['GET', 'DELETE'])
def task(task_id):
    db = get_db()
    row = db.execute('SELECT * FROM tasks WHERE id=?', (task_id,)).fetchone()
    if not row:
        return not_found_response()
    if request.method == 'DELETE':
        db.execute('DELETE FROM tasks WHERE id=?', (task_id,))
        db.commit()
        return no_content_response()
    msgs = json.loads(row['messages']) if row['messages'] else []
    return json_response({
        '@odata.id': f'/redfish/v1/TaskService/Tasks/{task_id}/',
        '@odata.type': '#Task.v1_7_0.Task',
        'Id': task_id,
        'Name': f'Task {task_id}',
        'TaskState': row['task_state'],
        'TaskStatus': row['task_status'],
        'StartTime': row['start_time'],
        'EndTime': row['end_time'],
        'Messages': msgs
    })
