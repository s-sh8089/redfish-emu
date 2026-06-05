import sqlite3
import os
import json
import uuid
from datetime import datetime, timezone
from flask import g, current_app


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DB_PATH'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA journal_mode=WAL')
    return g.db


def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def _create_tables(db):
    db.executescript('''
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role_id TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            locked INTEGER DEFAULT 0,
            password_change_required INTEGER DEFAULT 0,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS roles (
            id TEXT PRIMARY KEY,
            description TEXT,
            is_predefined INTEGER DEFAULT 1,
            assigned_privileges TEXT
        );

        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            token TEXT UNIQUE NOT NULL,
            client_origin_ip TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chassis (
            id TEXT PRIMARY KEY,
            chassis_type TEXT DEFAULT 'RackMount',
            power_state TEXT DEFAULT 'On',
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK'
        );

        CREATE TABLE IF NOT EXISTS systems (
            id TEXT PRIMARY KEY,
            manufacturer TEXT,
            model TEXT,
            sub_model TEXT,
            serial_number TEXT,
            part_number TEXT,
            asset_tag TEXT,
            bios_version TEXT,
            power_state TEXT DEFAULT 'On',
            boot_source_override_target TEXT DEFAULT 'None',
            boot_source_override_enabled TEXT DEFAULT 'Disabled',
            boot_source_override_mode TEXT DEFAULT 'Legacy',
            power_restore_policy TEXT DEFAULT 'LastState',
            power_mode TEXT DEFAULT 'MaximumPerformance',
            system_type TEXT DEFAULT 'Physical',
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK'
        );

        CREATE TABLE IF NOT EXISTS processors (
            id TEXT PRIMARY KEY,
            system_id TEXT,
            socket TEXT,
            processor_type TEXT DEFAULT 'CPU',
            processor_architecture TEXT DEFAULT 'x86',
            instruction_set TEXT DEFAULT 'x86-64',
            manufacturer TEXT,
            model TEXT,
            max_speed_mhz INTEGER,
            total_cores INTEGER,
            total_threads INTEGER,
            serial_number TEXT,
            part_number TEXT,
            spare_part_number TEXT,
            version TEXT,
            processor_id TEXT,
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK'
        );

        CREATE TABLE IF NOT EXISTS memory_modules (
            id TEXT PRIMARY KEY,
            system_id TEXT,
            base_module_type TEXT DEFAULT 'RDIMM',
            capacity_mib INTEGER,
            data_width_bits INTEGER DEFAULT 64,
            bus_width_bits INTEGER DEFAULT 72,
            error_correction TEXT DEFAULT 'MultiBitECC',
            manufacturer TEXT,
            model TEXT,
            serial_number TEXT,
            part_number TEXT,
            spare_part_number TEXT,
            operating_speed_mhz INTEGER,
            allowed_speeds_mhz TEXT,
            rank_count INTEGER,
            firmware_revision TEXT,
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK'
        );

        CREATE TABLE IF NOT EXISTS storage (
            id TEXT PRIMARY KEY,
            system_id TEXT,
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK'
        );

        CREATE TABLE IF NOT EXISTS drives (
            id TEXT PRIMARY KEY,
            storage_id TEXT,
            chassis_id TEXT,
            capacity_bytes INTEGER,
            encryption_status TEXT DEFAULT 'Unencrypted',
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK'
        );

        CREATE TABLE IF NOT EXISTS ethernet_interfaces (
            id TEXT PRIMARY KEY,
            parent_type TEXT,
            parent_id TEXT,
            mac_address TEXT,
            fqdn TEXT,
            hostname TEXT,
            interface_enabled INTEGER DEFAULT 1,
            link_status TEXT DEFAULT 'LinkUp',
            speed_mbps INTEGER DEFAULT 1000,
            ipv4_addresses TEXT,
            ipv4_static_addresses TEXT,
            ipv6_addresses TEXT,
            ipv6_static_addresses TEXT,
            ipv6_default_gateway TEXT,
            name_servers TEXT,
            static_name_servers TEXT,
            dhcpv4 TEXT,
            dhcpv6 TEXT,
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK'
        );

        CREATE TABLE IF NOT EXISTS vlans (
            id TEXT PRIMARY KEY,
            ethernet_interface_id TEXT,
            vlan_enable INTEGER DEFAULT 1,
            vlan_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS managers (
            id TEXT PRIMARY KEY,
            manager_type TEXT DEFAULT 'BMC',
            firmware_version TEXT,
            model TEXT,
            manufacturer TEXT,
            serial_number TEXT,
            part_number TEXT,
            spare_part_number TEXT,
            description TEXT,
            power_state TEXT DEFAULT 'On',
            datetime TEXT,
            datetime_local_offset TEXT DEFAULT '+00:00',
            last_reset_time TEXT,
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK',
            uuid TEXT,
            service_entry_point_uuid TEXT
        );

        CREATE TABLE IF NOT EXISTS log_entries (
            id TEXT PRIMARY KEY,
            log_service_id TEXT,
            parent_type TEXT,
            entry_type TEXT DEFAULT 'Event',
            severity TEXT DEFAULT 'OK',
            message TEXT,
            message_id TEXT,
            message_args TEXT,
            created TEXT,
            modified TEXT,
            resolved INTEGER DEFAULT 0,
            sensor_type TEXT,
            entry_code TEXT,
            additional_data_uri TEXT
        );

        CREATE TABLE IF NOT EXISTS event_subscriptions (
            id TEXT PRIMARY KEY,
            destination TEXT NOT NULL,
            context TEXT,
            protocol TEXT DEFAULT 'Redfish',
            event_types TEXT,
            origin_resources TEXT
        );

        CREATE TABLE IF NOT EXISTS firmware_inventory (
            id TEXT PRIMARY KEY,
            description TEXT,
            version TEXT,
            updateable INTEGER DEFAULT 1,
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK',
            related_item TEXT
        );

        CREATE TABLE IF NOT EXISTS certificates (
            id TEXT PRIMARY KEY,
            parent_path TEXT,
            certificate_string TEXT,
            description TEXT,
            issuer TEXT,
            subject TEXT,
            key_usage TEXT,
            valid_not_before TEXT,
            valid_not_after TEXT
        );

        CREATE TABLE IF NOT EXISTS sensors (
            id TEXT PRIMARY KEY,
            chassis_id TEXT,
            name TEXT,
            reading REAL,
            reading_type TEXT,
            reading_units TEXT,
            reading_range_max REAL,
            reading_range_min REAL,
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK',
            thresholds TEXT
        );

        CREATE TABLE IF NOT EXISTS temperatures (
            member_id TEXT PRIMARY KEY,
            chassis_id TEXT,
            name TEXT,
            reading_celsius REAL,
            upper_threshold_non_critical REAL,
            upper_threshold_critical REAL,
            lower_threshold_non_critical REAL,
            lower_threshold_critical REAL,
            min_reading_range REAL,
            max_reading_range REAL,
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK'
        );

        CREATE TABLE IF NOT EXISTS fans (
            member_id TEXT PRIMARY KEY,
            chassis_id TEXT,
            name TEXT,
            reading INTEGER,
            reading_units TEXT DEFAULT 'RPM',
            upper_threshold_non_critical INTEGER,
            upper_threshold_critical INTEGER,
            lower_threshold_non_critical INTEGER,
            lower_threshold_critical INTEGER,
            min_reading_range INTEGER,
            max_reading_range INTEGER,
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK'
        );

        CREATE TABLE IF NOT EXISTS voltages (
            member_id TEXT PRIMARY KEY,
            chassis_id TEXT,
            name TEXT,
            reading_volts REAL,
            upper_threshold_non_critical REAL,
            upper_threshold_critical REAL,
            lower_threshold_non_critical REAL,
            lower_threshold_critical REAL,
            min_reading_range REAL,
            max_reading_range REAL,
            physical_context TEXT,
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK'
        );

        CREATE TABLE IF NOT EXISTS power_supplies (
            member_id TEXT PRIMARY KEY,
            chassis_id TEXT,
            model TEXT,
            manufacturer TEXT,
            firmware_version TEXT,
            serial_number TEXT,
            part_number TEXT,
            line_input_voltage REAL,
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK'
        );

        CREATE TABLE IF NOT EXISTS power_controls (
            member_id TEXT PRIMARY KEY,
            chassis_id TEXT,
            power_consumed_watts REAL,
            power_metrics_interval_min INTEGER DEFAULT 20,
            power_metrics_min_consumed_watts REAL,
            power_metrics_max_consumed_watts REAL,
            power_metrics_avg_consumed_watts REAL
        );

        CREATE TABLE IF NOT EXISTS cables (
            id TEXT PRIMARY KEY,
            cable_type TEXT,
            length_meters REAL
        );

        CREATE TABLE IF NOT EXISTS pcie_devices (
            id TEXT PRIMARY KEY,
            system_id TEXT,
            lanes_in_use INTEGER
        );

        CREATE TABLE IF NOT EXISTS pcie_slots (
            id TEXT PRIMARY KEY,
            chassis_id TEXT,
            hotpluggable INTEGER DEFAULT 0,
            lanes INTEGER,
            pcie_type TEXT,
            slot_type TEXT
        );

        CREATE TABLE IF NOT EXISTS fabric_adapters (
            id TEXT PRIMARY KEY,
            system_id TEXT,
            model TEXT,
            part_number TEXT,
            serial_number TEXT,
            spare_part_number TEXT,
            status_state TEXT DEFAULT 'Enabled',
            status_health TEXT DEFAULT 'OK'
        );

        CREATE TABLE IF NOT EXISTS aggregation_sources (
            id TEXT PRIMARY KEY,
            hostname TEXT,
            password TEXT
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            task_state TEXT DEFAULT 'Running',
            task_status TEXT DEFAULT 'OK',
            start_time TEXT,
            end_time TEXT,
            messages TEXT
        );

        CREATE TABLE IF NOT EXISTS metric_report_definitions (
            id TEXT PRIMARY KEY,
            name TEXT,
            report_type TEXT DEFAULT 'Periodic'
        );

        CREATE TABLE IF NOT EXISTS metric_reports (
            id TEXT PRIMARY KEY,
            name TEXT,
            timestamp TEXT
        );

        CREATE TABLE IF NOT EXISTS triggers (
            id TEXT PRIMARY KEY,
            name TEXT,
            metric_type TEXT
        );
    ''')
    db.commit()


def _seed_data(db):
    now = datetime.now(timezone.utc).isoformat()

    # Roles
    if db.execute('SELECT COUNT(*) FROM roles').fetchone()[0] == 0:
        roles = [
            ('Administrator', 'Administrator Role', 1,
             json.dumps(['Login', 'ConfigureManager', 'ConfigureUsers', 'ConfigureSelf', 'ConfigureComponents'])),
            ('Operator', 'Operator Role', 1,
             json.dumps(['Login', 'ConfigureComponents', 'ConfigureSelf'])),
            ('ReadOnly', 'ReadOnly Role', 1,
             json.dumps(['Login', 'ConfigureSelf'])),
        ]
        db.executemany(
            'INSERT INTO roles (id, description, is_predefined, assigned_privileges) VALUES (?,?,?,?)',
            roles
        )

    # Accounts
    if db.execute('SELECT COUNT(*) FROM accounts').fetchone()[0] == 0:
        accounts = [
            ('admin', 'admin', 'password', 'Administrator', 1, 0, 0, 'Administrator Account'),
            ('operator1', 'operator1', 'password', 'Operator', 1, 0, 0, 'Operator Account'),
            ('readonly1', 'readonly1', 'password', 'ReadOnly', 1, 0, 0, 'ReadOnly Account'),
        ]
        db.executemany(
            'INSERT INTO accounts (id, username, password, role_id, enabled, locked, password_change_required, description) VALUES (?,?,?,?,?,?,?,?)',
            accounts
        )

    # Chassis
    if db.execute('SELECT COUNT(*) FROM chassis').fetchone()[0] == 0:
        db.execute(
            'INSERT INTO chassis (id, chassis_type, power_state, status_state, status_health) VALUES (?,?,?,?,?)',
            ('chassis1', 'RackMount', 'On', 'Enabled', 'OK')
        )

    # System
    if db.execute('SELECT COUNT(*) FROM systems').fetchone()[0] == 0:
        db.execute('''
            INSERT INTO systems (id, manufacturer, model, sub_model, serial_number, part_number,
                asset_tag, bios_version, power_state, boot_source_override_target,
                boot_source_override_enabled, boot_source_override_mode,
                power_restore_policy, power_mode, system_type, status_state, status_health)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', ('system', 'Dell Inc.', 'PowerEdge R750', None, 'SN-ABCD1234',
              'PN-08XXXX', 'ASSET-001', '2.4.8', 'On', 'None', 'Disabled', 'Legacy',
              'LastState', 'MaximumPerformance', 'Physical', 'Enabled', 'OK'))

    # Processors
    if db.execute('SELECT COUNT(*) FROM processors').fetchone()[0] == 0:
        processors = [
            ('CPU1', 'system', 'CPU 1', 'CPU', 'x86', 'x86-64',
             'Intel Corporation', 'Intel Xeon Gold 6338', 3200, 32, 64,
             'SN-CPU1', 'PN-CPU1', 'SPARE-CPU1', '2.6 GHz', 'BFEBFBFF000806D7',
             'Enabled', 'OK'),
            ('CPU2', 'system', 'CPU 2', 'CPU', 'x86', 'x86-64',
             'Intel Corporation', 'Intel Xeon Gold 6338', 3200, 32, 64,
             'SN-CPU2', 'PN-CPU2', 'SPARE-CPU2', '2.6 GHz', 'BFEBFBFF000806D7',
             'Enabled', 'OK'),
        ]
        db.executemany('''
            INSERT INTO processors (id, system_id, socket, processor_type, processor_architecture,
                instruction_set, manufacturer, model, max_speed_mhz, total_cores, total_threads,
                serial_number, part_number, spare_part_number, version, processor_id,
                status_state, status_health)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', processors)

    # Memory
    if db.execute('SELECT COUNT(*) FROM memory_modules').fetchone()[0] == 0:
        memory_modules = [
            ('Memory0', 'system', 'RDIMM', 32768, 64, 72, 'MultiBitECC',
             'Samsung', 'M393A4K40EB3-CWE', 'SN-MEM0', 'M393A4K40EB3', 'SPARE-MEM0',
             3200, json.dumps([2133, 2400, 2666, 2933, 3200]), 2, '1.0', 'Enabled', 'OK'),
            ('Memory1', 'system', 'RDIMM', 32768, 64, 72, 'MultiBitECC',
             'Samsung', 'M393A4K40EB3-CWE', 'SN-MEM1', 'M393A4K40EB3', 'SPARE-MEM1',
             3200, json.dumps([2133, 2400, 2666, 2933, 3200]), 2, '1.0', 'Enabled', 'OK'),
            ('Memory2', 'system', 'RDIMM', 32768, 64, 72, 'MultiBitECC',
             'Samsung', 'M393A4K40EB3-CWE', 'SN-MEM2', 'M393A4K40EB3', 'SPARE-MEM2',
             3200, json.dumps([2133, 2400, 2666, 2933, 3200]), 2, '1.0', 'Enabled', 'OK'),
            ('Memory3', 'system', 'RDIMM', 32768, 64, 72, 'MultiBitECC',
             'Samsung', 'M393A4K40EB3-CWE', 'SN-MEM3', 'M393A4K40EB3', 'SPARE-MEM3',
             3200, json.dumps([2133, 2400, 2666, 2933, 3200]), 2, '1.0', 'Enabled', 'OK'),
        ]
        db.executemany('''
            INSERT INTO memory_modules (id, system_id, base_module_type, capacity_mib,
                data_width_bits, bus_width_bits, error_correction, manufacturer, model,
                serial_number, part_number, spare_part_number, operating_speed_mhz,
                allowed_speeds_mhz, rank_count, firmware_revision, status_state, status_health)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', memory_modules)

    # Storage
    if db.execute('SELECT COUNT(*) FROM storage').fetchone()[0] == 0:
        db.execute(
            'INSERT INTO storage (id, system_id, status_state, status_health) VALUES (?,?,?,?)',
            ('Storage0', 'system', 'Enabled', 'OK')
        )

    # Drives
    if db.execute('SELECT COUNT(*) FROM drives').fetchone()[0] == 0:
        drives = [
            ('Drive0', 'Storage0', 'chassis1', 480103981056, 'Unencrypted', 'Enabled', 'OK'),
            ('Drive1', 'Storage0', 'chassis1', 480103981056, 'Unencrypted', 'Enabled', 'OK'),
        ]
        db.executemany(
            'INSERT INTO drives (id, storage_id, chassis_id, capacity_bytes, encryption_status, status_state, status_health) VALUES (?,?,?,?,?,?,?)',
            drives
        )

    # Manager
    if db.execute('SELECT COUNT(*) FROM managers').fetchone()[0] == 0:
        bmc_uuid = str(uuid.uuid4())
        sepu_uuid = str(uuid.uuid4())
        db.execute('''
            INSERT INTO managers (id, manager_type, firmware_version, model, manufacturer,
                serial_number, part_number, spare_part_number, description,
                power_state, datetime, datetime_local_offset, last_reset_time,
                status_state, status_health, uuid, service_entry_point_uuid)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', ('bmc', 'BMC', '2.71.71.71-711', 'iDRAC9', 'Dell Inc.',
              'SN-BMC001', 'PN-BMC001', 'SPARE-BMC001', 'BMC',
              'On', now, '+00:00', now,
              'Enabled', 'OK', bmc_uuid, sepu_uuid))

    # Ethernet Interfaces (BMC)
    if db.execute("SELECT COUNT(*) FROM ethernet_interfaces WHERE parent_type='manager'").fetchone()[0] == 0:
        eth0_ipv4 = json.dumps([{
            'Address': '192.168.1.100',
            'SubnetMask': '255.255.255.0',
            'Gateway': '192.168.1.1',
            'AddressOrigin': 'Static'
        }])
        eth0_ipv6 = json.dumps([{
            'Address': 'fe80::1',
            'PrefixLength': 64,
            'AddressOrigin': 'LinkLocal'
        }])
        dhcpv4 = json.dumps({'DHCPEnabled': False, 'UseDNSServers': True, 'UseGateway': True, 'UseNTPServers': True})
        dhcpv6 = json.dumps({'OperatingMode': 'Disabled', 'UseDNSServers': True})
        dns = json.dumps(['192.168.1.1', '8.8.8.8'])
        db.executemany('''
            INSERT INTO ethernet_interfaces (id, parent_type, parent_id, mac_address, fqdn, hostname,
                interface_enabled, link_status, speed_mbps, ipv4_addresses, ipv4_static_addresses,
                ipv6_addresses, ipv6_static_addresses, ipv6_default_gateway,
                name_servers, static_name_servers, dhcpv4, dhcpv6, status_state, status_health)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', [
            ('eth0', 'manager', 'bmc', 'AA:BB:CC:DD:EE:00',
             'bmc.example.com', 'bmc', 1, 'LinkUp', 1000,
             eth0_ipv4, eth0_ipv4, eth0_ipv6, json.dumps([]),
             '::', dns, dns, dhcpv4, dhcpv6, 'Enabled', 'OK'),
            ('eth1', 'manager', 'bmc', 'AA:BB:CC:DD:EE:01',
             'bmc-mgmt.example.com', 'bmc-mgmt', 1, 'LinkUp', 1000,
             json.dumps([{'Address': '10.0.0.100', 'SubnetMask': '255.255.0.0',
                         'Gateway': '10.0.0.1', 'AddressOrigin': 'Static'}]),
             json.dumps([]), eth0_ipv6, json.dumps([]),
             '::', dns, dns, dhcpv4, dhcpv6, 'Enabled', 'OK'),
        ])

    # VLANs
    if db.execute('SELECT COUNT(*) FROM vlans').fetchone()[0] == 0:
        db.execute(
            'INSERT INTO vlans (id, ethernet_interface_id, vlan_enable, vlan_id) VALUES (?,?,?,?)',
            ('vlan100', 'eth0', 1, 100)
        )

    # Temperatures
    if db.execute('SELECT COUNT(*) FROM temperatures').fetchone()[0] == 0:
        temps = [
            ('CPU1 Temp', 'chassis1', 'CPU1 Temp', 45.0, 85.0, 95.0, 0.0, 0.0, 0.0, 100.0, 'Enabled', 'OK'),
            ('CPU2 Temp', 'chassis1', 'CPU2 Temp', 43.0, 85.0, 95.0, 0.0, 0.0, 0.0, 100.0, 'Enabled', 'OK'),
            ('Inlet Temp', 'chassis1', 'Inlet Temp', 22.0, 40.0, 50.0, 0.0, 0.0, 0.0, 60.0, 'Enabled', 'OK'),
            ('Outlet Temp', 'chassis1', 'Outlet Temp', 35.0, 60.0, 70.0, 0.0, 0.0, 0.0, 80.0, 'Enabled', 'OK'),
        ]
        db.executemany('''
            INSERT INTO temperatures (member_id, chassis_id, name, reading_celsius,
                upper_threshold_non_critical, upper_threshold_critical,
                lower_threshold_non_critical, lower_threshold_critical,
                min_reading_range, max_reading_range, status_state, status_health)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        ''', temps)

    # Fans
    if db.execute('SELECT COUNT(*) FROM fans').fetchone()[0] == 0:
        fans = [
            ('Fan1', 'chassis1', 'Fan1', 5400, 'RPM', 6000, 6500, 500, 1000, 500, 7000, 'Enabled', 'OK'),
            ('Fan2', 'chassis1', 'Fan2', 5200, 'RPM', 6000, 6500, 500, 1000, 500, 7000, 'Enabled', 'OK'),
            ('Fan3', 'chassis1', 'Fan3', 5600, 'RPM', 6000, 6500, 500, 1000, 500, 7000, 'Enabled', 'OK'),
            ('Fan4', 'chassis1', 'Fan4', 5300, 'RPM', 6000, 6500, 500, 1000, 500, 7000, 'Enabled', 'OK'),
            ('Fan5', 'chassis1', 'Fan5', 5500, 'RPM', 6000, 6500, 500, 1000, 500, 7000, 'Enabled', 'OK'),
            ('Fan6', 'chassis1', 'Fan6', 5100, 'RPM', 6000, 6500, 500, 1000, 500, 7000, 'Enabled', 'OK'),
        ]
        db.executemany('''
            INSERT INTO fans (member_id, chassis_id, name, reading, reading_units,
                upper_threshold_non_critical, upper_threshold_critical,
                lower_threshold_non_critical, lower_threshold_critical,
                min_reading_range, max_reading_range, status_state, status_health)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', fans)

    # Voltages
    if db.execute('SELECT COUNT(*) FROM voltages').fetchone()[0] == 0:
        voltages = [
            ('12V', 'chassis1', '12V', 12.1, 12.6, 13.0, 11.4, 11.0, 11.0, 13.0, 'SystemBoard', 'Enabled', 'OK'),
            ('5V', 'chassis1', '5V', 5.05, 5.25, 5.5, 4.75, 4.5, 4.5, 5.5, 'SystemBoard', 'Enabled', 'OK'),
            ('3.3V', 'chassis1', '3.3V', 3.31, 3.47, 3.6, 3.13, 3.0, 3.0, 3.6, 'SystemBoard', 'Enabled', 'OK'),
            ('CPU1 VCore', 'chassis1', 'CPU1 VCore', 1.82, 1.96, 2.0, 1.5, 1.4, 1.4, 2.0, 'CPU', 'Enabled', 'OK'),
            ('CPU2 VCore', 'chassis1', 'CPU2 VCore', 1.80, 1.96, 2.0, 1.5, 1.4, 1.4, 2.0, 'CPU', 'Enabled', 'OK'),
        ]
        db.executemany('''
            INSERT INTO voltages (member_id, chassis_id, name, reading_volts,
                upper_threshold_non_critical, upper_threshold_critical,
                lower_threshold_non_critical, lower_threshold_critical,
                min_reading_range, max_reading_range, physical_context, status_state, status_health)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', voltages)

    # Power Controls
    if db.execute('SELECT COUNT(*) FROM power_controls').fetchone()[0] == 0:
        db.execute('''
            INSERT INTO power_controls (member_id, chassis_id, power_consumed_watts,
                power_metrics_interval_min, power_metrics_min_consumed_watts,
                power_metrics_max_consumed_watts, power_metrics_avg_consumed_watts)
            VALUES (?,?,?,?,?,?,?)
        ''', ('System Power Control', 'chassis1', 380.0, 20, 250.0, 500.0, 360.0))

    # Power Supplies
    if db.execute('SELECT COUNT(*) FROM power_supplies').fetchone()[0] == 0:
        psus = [
            ('PSU1', 'chassis1', 'PWR-750-AC', 'Dell Inc.', '1.0', 'SN-PSU1', 'PN-PSU1', 215.0, 'Enabled', 'OK'),
            ('PSU2', 'chassis1', 'PWR-750-AC', 'Dell Inc.', '1.0', 'SN-PSU2', 'PN-PSU2', 214.0, 'Enabled', 'OK'),
        ]
        db.executemany('''
            INSERT INTO power_supplies (member_id, chassis_id, model, manufacturer,
                firmware_version, serial_number, part_number, line_input_voltage,
                status_state, status_health)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        ''', psus)

    # Sensors
    if db.execute('SELECT COUNT(*) FROM sensors').fetchone()[0] == 0:
        thresholds = json.dumps({
            'UpperCaution': {'Reading': 85.0, 'Activation': 'Increasing'},
            'UpperCritical': {'Reading': 95.0, 'Activation': 'Increasing'}
        })
        sensors = [
            ('sensor_cpu1_temp', 'chassis1', 'CPU1 Temperature', 45.0, 'Temperature', 'Cel', 100.0, 0.0, 'Enabled', 'OK', thresholds),
            ('sensor_cpu2_temp', 'chassis1', 'CPU2 Temperature', 43.0, 'Temperature', 'Cel', 100.0, 0.0, 'Enabled', 'OK', thresholds),
            ('sensor_fan1', 'chassis1', 'Fan1 Speed', 5400.0, 'Rotational', 'RPM', 7000.0, 0.0, 'Enabled', 'OK', json.dumps({})),
            ('sensor_power', 'chassis1', 'System Power', 380.0, 'Power', 'W', 800.0, 0.0, 'Enabled', 'OK', json.dumps({})),
        ]
        db.executemany('''
            INSERT INTO sensors (id, chassis_id, name, reading, reading_type, reading_units,
                reading_range_max, reading_range_min, status_state, status_health, thresholds)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        ''', sensors)

    # PCIe Slots
    if db.execute('SELECT COUNT(*) FROM pcie_slots').fetchone()[0] == 0:
        slots = [
            ('Slot1', 'chassis1', 1, 16, 'Gen4', 'FullLength'),
            ('Slot2', 'chassis1', 1, 8, 'Gen4', 'HalfLength'),
            ('Slot3', 'chassis1', 0, 4, 'Gen3', 'HalfLength'),
        ]
        db.executemany(
            'INSERT INTO pcie_slots (id, chassis_id, hotpluggable, lanes, pcie_type, slot_type) VALUES (?,?,?,?,?,?)',
            slots
        )

    # PCIe Devices
    if db.execute('SELECT COUNT(*) FROM pcie_devices').fetchone()[0] == 0:
        db.execute(
            'INSERT INTO pcie_devices (id, system_id, lanes_in_use) VALUES (?,?,?)',
            ('PCIeDevice0', 'system', 16)
        )

    # Fabric Adapters
    if db.execute('SELECT COUNT(*) FROM fabric_adapters').fetchone()[0] == 0:
        db.execute('''
            INSERT INTO fabric_adapters (id, system_id, model, part_number, serial_number,
                spare_part_number, status_state, status_health)
            VALUES (?,?,?,?,?,?,?,?)
        ''', ('FA0', 'system', 'Mellanox ConnectX-6', 'PN-FA0', 'SN-FA0', 'SPARE-FA0', 'Enabled', 'OK'))

    # Firmware Inventory
    if db.execute('SELECT COUNT(*) FROM firmware_inventory').fetchone()[0] == 0:
        fw_items = [
            ('BMC', 'BMC Firmware', '2.71.71.71-711', 1, 'Enabled', 'OK',
             json.dumps([{'@odata.id': '/redfish/v1/Managers/bmc'}])),
            ('BIOS', 'System BIOS', '2.4.8', 1, 'Enabled', 'OK',
             json.dumps([{'@odata.id': '/redfish/v1/Systems/system'}])),
            ('ME', 'Management Engine Firmware', '5.0.4.45', 0, 'Enabled', 'OK',
             json.dumps([{'@odata.id': '/redfish/v1/Systems/system'}])),
            ('CPLD', 'Complex Programmable Logic Device', '0.49', 1, 'Enabled', 'OK',
             json.dumps([{'@odata.id': '/redfish/v1/Chassis/chassis1'}])),
        ]
        db.executemany('''
            INSERT INTO firmware_inventory (id, description, version, updateable,
                status_state, status_health, related_item)
            VALUES (?,?,?,?,?,?,?)
        ''', fw_items)

    # Certificates
    if db.execute('SELECT COUNT(*) FROM certificates').fetchone()[0] == 0:
        cert_data = '''-----BEGIN CERTIFICATE-----
MIICpDCCAYwCCQDU+pQ4pHgSpDANBgkqhkiG9w0BAQsFADAUMRIwEAYDVQQDDAls
b2NhbGhvc3QwHhcNMjMwMTAxMDAwMDAwWhcNMjQwMTAxMDAwMDAwWjAUMRIwEAYD
VQQDDAlsb2NhbGhvc3QwggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQC7
-----END CERTIFICATE-----'''
        issuer = json.dumps({'CommonName': 'localhost', 'Organization': ['Example Corp']})
        subject = json.dumps({'CommonName': 'localhost', 'Organization': ['Example Corp']})
        key_usage = json.dumps(['KeyEncipherment', 'DigitalSignature'])
        db.execute('''
            INSERT INTO certificates (id, parent_path, certificate_string, description,
                issuer, subject, key_usage, valid_not_before, valid_not_after)
            VALUES (?,?,?,?,?,?,?,?,?)
        ''', ('1', '/redfish/v1/Managers/bmc/NetworkProtocol/HTTPS/Certificates',
              cert_data, 'HTTPS Certificate',
              issuer, subject, key_usage,
              '2023-01-01T00:00:00Z', '2024-01-01T00:00:00Z'))

    # Cables
    if db.execute('SELECT COUNT(*) FROM cables').fetchone()[0] == 0:
        cables = [
            ('Cable0', 'QSFP28', 3.0),
            ('Cable1', 'SFP+', 1.0),
        ]
        db.executemany(
            'INSERT INTO cables (id, cable_type, length_meters) VALUES (?,?,?)',
            cables
        )

    # Log Entries
    if db.execute('SELECT COUNT(*) FROM log_entries').fetchone()[0] == 0:
        log_ts = '2024-01-01T00:00:00+00:00'
        entries = [
            ('eventlog1', 'EventLog', 'system', 'Event', 'OK',
             'System started successfully', 'Base.1.0.Success', json.dumps([]),
             log_ts, log_ts, 1, None, None, None),
            ('eventlog2', 'EventLog', 'system', 'Event', 'Warning',
             'Temperature threshold exceeded', 'ThermalEvents.1.0.TemperatureAboveUpperCautionThreshold',
             json.dumps(['CPU1 Temp', '87']), log_ts, log_ts, 0, None, None, None),
            ('sel1', 'SEL', 'system', 'SEL', 'OK',
             'System Event', 'IPMI.1.0.SELEntry', json.dumps([]),
             log_ts, log_ts, 1, 'Temperature', 'Lower Non-critical going low', None),
            ('redfishlog1', 'RedfishLog', 'manager', 'Event', 'OK',
             'BMC startup complete', 'Base.1.0.Success', json.dumps([]),
             log_ts, log_ts, 1, None, None, None),
        ]
        db.executemany('''
            INSERT INTO log_entries (id, log_service_id, parent_type, entry_type, severity,
                message, message_id, message_args, created, modified, resolved,
                sensor_type, entry_code, additional_data_uri)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', entries)

    # Tasks
    if db.execute('SELECT COUNT(*) FROM tasks').fetchone()[0] == 0:
        db.execute('''
            INSERT INTO tasks (id, task_state, task_status, start_time, end_time, messages)
            VALUES (?,?,?,?,?,?)
        ''', ('task1', 'Completed', 'OK', '2024-01-01T00:00:00Z', '2024-01-01T00:01:00Z',
              json.dumps([{'Message': 'Firmware update completed successfully.', 'Severity': 'OK'}])))

    # Metric Report Definitions
    if db.execute('SELECT COUNT(*) FROM metric_report_definitions').fetchone()[0] == 0:
        db.execute(
            'INSERT INTO metric_report_definitions (id, name, report_type) VALUES (?,?,?)',
            ('PowerMetrics', 'Power Metrics Report Definition', 'Periodic')
        )

    # Metric Reports
    if db.execute('SELECT COUNT(*) FROM metric_reports').fetchone()[0] == 0:
        db.execute(
            'INSERT INTO metric_reports (id, name, timestamp) VALUES (?,?,?)',
            ('PowerMetrics', 'Power Metrics Report', '2024-01-01T00:00:00Z')
        )

    # Triggers
    if db.execute('SELECT COUNT(*) FROM triggers').fetchone()[0] == 0:
        db.execute(
            'INSERT INTO triggers (id, name, metric_type) VALUES (?,?,?)',
            ('TempTrigger', 'Temperature Trigger', 'Numeric')
        )

    # Aggregation Sources
    if db.execute('SELECT COUNT(*) FROM aggregation_sources').fetchone()[0] == 0:
        db.execute(
            'INSERT INTO aggregation_sources (id, hostname, password) VALUES (?,?,?)',
            ('AggSource1', 'remote-bmc.example.com', 'password')
        )

    db.commit()


def init_db(app):
    db_path = app.config['DB_PATH']
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    _create_tables(db)
    _seed_data(db)
    db.close()
