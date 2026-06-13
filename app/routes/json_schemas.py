from fastapi import APIRouter, Depends
from ..auth import verify_auth
from ..helpers import json_response, not_found_response

router = APIRouter(dependencies=[Depends(verify_auth)])

SCHEMAS = [
    'AccountService', 'Bios', 'Cable', 'Certificate', 'CertificateLocations',
    'CertificateService', 'Chassis', 'ComputerSystem', 'Drive', 'EthernetInterface',
    'EventDestination', 'EventService', 'FabricAdapter', 'Fan', 'JsonSchemaFile',
    'LogEntry', 'LogService', 'Manager', 'ManagerAccount', 'ManagerDiagnosticData',
    'ManagerNetworkProtocol', 'Memory', 'MemoryMetrics', 'Message', 'MessageRegistry',
    'MessageRegistryFile', 'PCIeDevice', 'PCIeSlots', 'Power', 'PowerSupply',
    'Processor', 'Role', 'Sensor', 'ServiceRoot', 'Session', 'SessionService',
    'SoftwareInventory', 'Storage', 'Task', 'TaskService', 'TelemetryService',
    'Thermal', 'ThermalSubsystem', 'UpdateService',
]


@router.get('/redfish/v1/JsonSchemas/')
def json_schemas():
    members = [{'@odata.id': f'/redfish/v1/JsonSchemas/{s}/'} for s in SCHEMAS]
    return json_response({
        '@odata.id': '/redfish/v1/JsonSchemas/',
        '@odata.type': '#JsonSchemaFileCollection.JsonSchemaFileCollection',
        'Name': 'JsonSchemaFile Collection',
        'Description': 'Collection of schema definitions',
        'Members@odata.count': len(members),
        'Members': members
    })


@router.get('/redfish/v1/JsonSchemas/{schema_id}/')
def json_schema(schema_id: str):
    if schema_id not in SCHEMAS:
        return not_found_response()
    return json_response({
        '@odata.id': f'/redfish/v1/JsonSchemas/{schema_id}/',
        '@odata.type': '#JsonSchemaFile.v1_1_4.JsonSchemaFile',
        'Id': schema_id,
        'Name': f'{schema_id} Schema File',
        'Description': f'Schema definition for {schema_id}',
        'Schema': f'#/definitions/{schema_id}',
        'Languages': ['en'],
        'Languages@odata.count': 1,
        'Location': [
            {
                'Language': 'en',
                'Uri': f'https://redfish.dmtf.org/schemas/v1/{schema_id}.json',
                'PublicationUri': f'https://redfish.dmtf.org/schemas/v1/{schema_id}.json'
            }
        ],
        'Location@odata.count': 1
    })
