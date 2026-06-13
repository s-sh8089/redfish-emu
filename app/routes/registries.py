from fastapi import APIRouter, Depends
from ..auth import verify_auth
from ..helpers import json_response, not_found_response

router = APIRouter(dependencies=[Depends(verify_auth)])

REGISTRIES = {
    'Base': {
        'name': 'Base',
        'description': 'Base Message Registry',
        'registry': 'Base.1.0.0',
        'languages': ['en'],
    },
    'CommonMessages': {
        'name': 'CommonMessages',
        'description': 'Common Messages Registry',
        'registry': 'CommonMessages.1.0.0',
        'languages': ['en'],
    },
    'EventingMessages': {
        'name': 'EventingMessages',
        'description': 'Eventing Messages Registry',
        'registry': 'EventingMessages.1.0.0',
        'languages': ['en'],
    },
    'TaskEvent': {
        'name': 'TaskEvent',
        'description': 'Task Event Registry',
        'registry': 'TaskEvent.1.0.0',
        'languages': ['en'],
    },
}


@router.get('/redfish/v1/Registries/')
def registries():
    members = [{'@odata.id': f'/redfish/v1/Registries/{k}/'} for k in REGISTRIES]
    return json_response({
        '@odata.id': '/redfish/v1/Registries/',
        '@odata.type': '#MessageRegistryFileCollection.MessageRegistryFileCollection',
        'Name': 'Message Registry File Collection',
        'Description': 'List of message registries',
        'Members@odata.count': len(members),
        'Members': members
    })


@router.get('/redfish/v1/Registries/{registry_id}/')
def registry(registry_id: str):
    reg = REGISTRIES.get(registry_id)
    if not reg:
        return not_found_response()
    return json_response({
        '@odata.id': f'/redfish/v1/Registries/{registry_id}/',
        '@odata.type': '#MessageRegistryFile.v1_1_4.MessageRegistryFile',
        'Id': registry_id,
        'Name': reg['name'],
        'Description': reg['description'],
        'Registry': reg['registry'],
        'Languages': reg['languages'],
        'Languages@odata.count': len(reg['languages']),
        'Location': [
            {
                'Language': 'en',
                'Uri': f'/redfish/v1/Registries/{registry_id}/{registry_id}.json',
                'PublicationUri': f'https://redfish.dmtf.org/registries/v1/{registry_id}.json'
            }
        ],
        'Location@odata.count': 1
    })
