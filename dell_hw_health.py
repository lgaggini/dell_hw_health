#! /usr/bin/env python
#
# dell_hw_health.py, python script using Redfish API to get system hardware
# health based on GetSystemHWInventoryREDFISH.py by Texas Roemer
# <Texas_Roemer@Dell.com>
#
# _author_ = Lorenzo Gaggini  <lorenzo.gaggini@dada.eu>,
# Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2018, Dell, Inc., 2019, Lorenzo Gaggini
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import requests
import sys
import re
import argparse
from datetime import datetime
import logging

requests.packages.urllib3.disable_warnings()

logger = logging.getLogger('dell_hw_health')
logging.basicConfig()

ENDPOINT = '/redfish/v1/Systems/System.Embedded.1'


def check_supported_idrac_version():
    response = requests.get('https://%s%s' % (idrac_ip, ENDPOINT),
                            verify=False,
                            auth=(idrac_username, idrac_password))
    if response.status_code != 200:
        msg = 'WARNING, iDRAC version installed does not support ' +\
               'this feature using Redfish API'
        logger.warning(msg)
        sys.exit(3)
    else:
        pass


def get_status(data):
    return data[u'Status']['Health']


def is_healthy(status):
    if status == 'OK' or status is None:
        return True
    else:
        return False


def get_nagios_output(status, msg):
    print('%s;%s;%s - %s' % (status, HostName, datetime.now(), msg))
    sys.exit(status)


def get_report_output(msg):
    print(msg)
    f = open('hw_inventory.txt', 'a')
    f.writelines(msg)
    f.writelines('\n')
    f.close()


def get_system_information():
    global serverSN
    global HostName
    response = requests.get('https://%s%s' % (idrac_ip, ENDPOINT),
                            verify=False,
                            auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logger.error('FAIL, get command failed, error is: %s' % data)
        sys.exit(2)
    serverSN = data[u'SerialNumber']
    HostName = data[u'HostName']


def get_memory_information():
    nagios_status = 0
    nagios_msg = ''
    response = requests.get('https://%s%s/Memory' % (idrac_ip, ENDPOINT),
                            verify=False,
                            auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logger.error('FAIL, get command failed, error is: %s' % data)
        sys.exit(2)
    for i in data[u'Members']:
        dimm = i[u'@odata.id'].split('/')[-1]
        try:
            dimm_slot = re.search('DIMM.+', dimm).group()
        except:
            logger.error('FAIL, unable to get dimm slot info')
            sys.exit(2)
        response = requests.get('https://%s%s' % (idrac_ip, i[u'@odata.id']),
                                verify=False,
                                auth=(idrac_username, idrac_password))
        sub_data = response.json()
        if response.status_code != 200:
            logger.error('FAIL, get command failed, error is: %s' % sub_data)
            sys.exit(2)
        else:
            status = get_status(sub_data)
            if (is_healthy(status) and args['critical']):
                continue
            message = 'Server %s %s %s %s PN %s: %s ' % (serverSN, dimm_slot,
                                                         sub_data[u'Manufacturer'],
                                                         sub_data[u'CapacityMiB'],
                                                         sub_data[u'PartNumber'],
                                                         status)
            if args['nagios'] and not is_healthy(status):
                nagios_status = 2
                nagios_msg += message
            elif not args['nagios']:
                get_report_output(message)
    if args['nagios']:
        if nagios_status == 0:
            nagios_msg = 'Memory is OK'
        get_nagios_output(nagios_status, nagios_msg)


def get_cpu_information():
    nagios_status = 0
    nagios_msg = ''
    response = requests.get('https://%s%s/Processors' % (idrac_ip, ENDPOINT),
                            verify=False,
                            auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logger.error('FAIL, get command failed, error is: %s' % data)
        sys.exit(2)
    for i in data[u'Members']:
        cpu = i[u'@odata.id'].split('/')[-1]
        response = requests.get('https://%s%s' % (idrac_ip, i[u'@odata.id']),
                                verify=False,
                                auth=(idrac_username, idrac_password))
        sub_data = response.json()
        if response.status_code != 200:
            logger.error('FAIL, get command failed, error is: %s' % sub_data)
            sys.exit(2)
        else:
            status = get_status(sub_data)
            if (is_healthy(status) and args['critical']):
                continue
            message = 'Server %s %s %s: %s ' % (serverSN, cpu,
                                                sub_data['Model'],
                                                status)
            if args['nagios'] and not is_healthy(status):
                nagios_status = 2
                nagios_msg += message
            elif not args['nagios']:
                get_report_output(message)
    if args['nagios']:
        if nagios_status == 0:
            nagios_msg = 'CPU is OK'
        get_nagios_output(nagios_status, nagios_msg)


def get_fan_information():
    nagios_status = 0
    nagios_msg = ''
    response = requests.get('https://%s%s' % (idrac_ip, ENDPOINT),
                            verify=False,
                            auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logger.error('FAIL, get command failed, error is: %s' % data)
        sys.exit(2)
    if data[u'Links'][u'CooledBy'] == []:
        logger.warning('WARNING, no fans detected for system')
    else:
        for i in data[u'Links'][u'CooledBy']:
            response = requests.get('https://%s%s' % (idrac_ip,
                                                      i[u'@odata.id']),
                                    verify=False,
                                    auth=(idrac_username, idrac_password))
            data = response.json()
            if response.status_code != 200:
                logger.error('FAIL, get command failed, error is: %s' % data)
                sys.exit(2)
            else:
                fan = i[u'@odata.id'].split('/')[-1]
                try:
                    fan_slot = re.search('\|\|.+', fan).group().strip('|')
                except:
                    pass
                try:
                    fan_slot = re.search('7CF.+', fan).group().strip('7C')
                except:
                    pass
                status = get_status(data)
                if (is_healthy(status) and args['critical']):
                    continue
                message = 'Server %s %s %s: %s ' % (serverSN, fan_slot,
                                                    data[u'FanName'],
                                                    status)
                if args['nagios'] and not is_healthy(status):
                    nagios_status = 2
                    nagios_msg += message
                elif not args['nagios']:
                    get_report_output(message)
    if args['nagios']:
        if nagios_status == 0:
            nagios_msg = 'FANS are OK'
        get_nagios_output(nagios_status, nagios_msg)


def get_ps_information():
    nagios_status = 0
    nagios_msg = ''
    response = requests.get('https://%s%s' % (idrac_ip, ENDPOINT),
                            verify=False,
                            auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logger.error('FAIL, get command failed, error is: %s' % data)
        sys.exit(2)
    if data[u'Links'][u'PoweredBy'] == []:
        logger.warning('WARNING, no power supplies detected for system')
    else:
        for i in data[u'Links'][u'PoweredBy']:
            response = requests.get('https://%s%s' % (idrac_ip,
                                                      i[u'@odata.id']),
                                    verify=False,
                                    auth=(idrac_username, idrac_password))
            data = response.json()
            if response.status_code != 200:
                logger.error('FAIL, get command failed, error is: %s' % data)
                sys.exit(2)
            else:
                ps = i[u'@odata.id'].split('/')[-1]
                status = get_status(data)
                if (is_healthy(status) and args['critical']):
                    continue
                message = 'Server %s %s %s %s PN %s: %s ' % (serverSN, ps,
                                                             data[u'Manufacturer'],
                                                             data[u'Model'],
                                                             data[u'PartNumber'],
                                                             status)
                if args['nagios'] and not is_healthy(status):
                    nagios_status = 2
                    nagios_msg += message
                elif not args['nagios']:
                    get_report_output(message)
    if args['nagios']:
        if nagios_status == 0:
            nagios_msg = 'PSU are OK'
        get_nagios_output(nagios_status, nagios_msg)


def get_storage_controller_information(quiet=False):
    nagios_status = 0
    nagios_msg = ''
    global controller_list
    response = requests.get('https://%s%s/Storage' % (idrac_ip, ENDPOINT),
                            verify=False,
                            auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logger.error('FAIL, get command failed, error is: %s' % data)
        sys.exit(2)
    controller_list = []
    for i in data[u'Members']:
        controller_list.append(i[u'@odata.id'][46:])
    for i in controller_list:
        response = requests.get('https://%s%s/Storage/%s' % (idrac_ip,
                                                             ENDPOINT, i),
                                verify=False,
                                auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            logger.error('FAIL, get command failed, error is: %s' % data)
            sys.exit(2)
        if u'StorageControllers' not in data:
            continue
        status = get_status(data[u'StorageControllers'][0])
        if (is_healthy(status) and args['critical']):
            continue
        message = 'Server %s %s: %s ' % (serverSN, i, status)
        if args['nagios'] and not is_healthy(status):
            nagios_status = 2
            nagios_msg += message
        elif not args['nagios'] and not quiet:
            get_report_output(message)
    if args['nagios'] and not quiet:
        if nagios_status == 0:
            nagios_msg = 'CONTROLLERS are OK'
        get_nagios_output(nagios_status, nagios_msg)


def get_storage_disks_information():
    nagios_status = 0
    nagios_msg = ''
    for i in controller_list:
        response = requests.get('https://%s%s/Storage/%s' % (idrac_ip,
                                                             ENDPOINT, i),
                                verify=False,
                                auth=(idrac_username, idrac_password))
        data = response.json()
        if response.status_code != 200:
            logger.error('FAIL, get command failed, error is: %s' % data)
            sys.exit(2)
        drive_list = []
        if data[u'Drives'] == []:
            message = 'WARNING, no drives detected for %s' % i
        else:
            pass
            for ii in data[u'Drives']:
                drive_list.append(ii[u'@odata.id'][53:])
        for iii in drive_list:
            response = requests.get('https://%s%s/Storage/Drives/%s' % (idrac_ip,
                                                                        ENDPOINT,
                                                                        iii),
                                    verify=False,
                                    auth=(idrac_username, idrac_password))
            data = response.json()
            if response.status_code != 200:
                logger.error('\n- FAIL, get command failed, error is: %s' %
                             data)
                sys.exit(2)
            status = get_status(data)
            if (is_healthy(status) and args['critical']):
                continue
            message = 'Server %s %s %s %s PN %s: %s ' % (serverSN, iii,
                                                         data[u'Manufacturer'],
                                                         data[u'Description'],
                                                         data[u'PartNumber'],
                                                         status)
            if args['nagios'] and not is_healthy(status):
                nagios_status = 2
                nagios_msg += message
            elif not args['nagios']:
                get_report_output(message)
    if args['nagios']:
        if nagios_status == 0:
            nagios_msg = 'DISKS are OK'
        get_nagios_output(nagios_status, nagios_msg)


def get_backplane_information():
    nagios_status = 0
    nagios_msg = ''
    response = requests.get('https://%s/redfish/v1/Chassis' % (idrac_ip),
                            verify=False,
                            auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code != 200:
        logger.error('FAIL, get command failed, error is: %s' % data)
        sys.exit(2)
    backplane_URI_list = []
    for i in data[u'Members']:
        backplane = i[u'@odata.id']
        if 'Enclosure' in backplane:
            backplane_URI_list.append(backplane)
    if backplane_URI_list == []:
        message = '- WARNING, no backplane information detected for system\n'
        print(message)
        sys.exit(2)
    for i in backplane_URI_list:
        response = requests.get('https://%s%s' % (idrac_ip, i), verify=False,
                                auth=(idrac_username, idrac_password))
        data = response.json()
        status = get_status(data)
        if (is_healthy(status) and args['critical']):
            continue
        message = '%s %s %s: %s ' % (serverSN, data[u'Id'], data[u'Name'],
                                     status)
        if args['nagios'] and not is_healthy(status):
            nagios_status = 2
            nagios_msg += message
        elif not args['nagios']:
            get_report_output(message)
    if args['nagios']:
        if nagios_status == 0:
            nagios_msg = 'BACKPLANE is OK'
        get_nagios_output(nagios_status, nagios_msg)

def get_temperature_information():
    nagios_status = 0
    nagios_msg = ''
    response = requests.get('https://%s/redfish/v1/Chassis/System.Embedded.1/Thermal' % (idrac_ip),
                            verify=False,
                            auth=(idrac_username, idrac_password))
    data = response.json()

    if response.status_code != 200:
        logger.error('FAIL, get command failed, error is: %s' % data)
        sys.exit(2)

    for i in data[u'Temperatures']:
        status = get_status(i)
        if (is_healthy(status) and args['critical']):
            continue
        message = '%s %s %s: %s' % (i[u'PhysicalContext'], i[u'MemberId'], i[u'Name'],
                                    status)
        if args['nagios'] and not is_healthy(status):
            nagios_status = 2
            nagios_msg += message
        elif not args['nagios']:
            get_report_output(message)
    if args['nagios']:
        if nagios_status == 0:
            nagios_msg = 'TEMPERATURE is OK'
        get_nagios_output(nagios_status, nagios_msg)



if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Python script using ' +
                                     'Redfish API to get system hardware' +
                                     'Health')
    parser.add_argument('-ip', help='iDRAC IP address', required=True)
    parser.add_argument('-u', help='iDRAC username', required=True)
    parser.add_argument('-p', help='iDRAC password', required=True)
    parser.add_argument('-m', help='Get memory information', required=False,
                        action='store_true')
    parser.add_argument('-c', help='Get processor information', required=False,
                        action='store_true')
    parser.add_argument('-f', help='Get fan information', required=False,
                        action='store_true')
    parser.add_argument('-ps', help='Get power supply information',
                        required=False,
                        action='store_true')
    parser.add_argument('-s', help='Get storage controllers information only',
                        required=False,
                        action='store_true')
    parser.add_argument('-d', help='Get disks information only',
                        required=False,
                        action='store_true')
    parser.add_argument('-b', help='Get backplane information only',
                        required=False,
                        action='store_true')
    parser.add_argument('-t', help='Get temperature information only',
                        required=False,
                        action='store_true')
    parser.add_argument('-a', help='Get all information',
                        required=False,
                        action='store_true')
    parser.add_argument('-critical', help='Retrieve only failure for report',
                        required=False,
                        action='store_true')
    parser.add_argument('-nagios', help='Nagios output check mode' +
                        ', only the first option is used',
                        required=False,
                        action='store_true')

    args = vars(parser.parse_args())

    idrac_ip = args['ip']
    idrac_username = args['u']
    idrac_password = args['p']

    check_supported_idrac_version()

    get_system_information()
    if args['m']:
        get_memory_information()
    if args['c']:
        get_cpu_information()
    if args['f']:
        get_fan_information()
    if args['ps']:
        get_ps_information()
    if args['s']:
        get_storage_controller_information()
    if args['d']:
        get_storage_controller_information(quiet=True)
        get_storage_disks_information()
    if args['b']:
        get_backplane_information()
    if args['t']:
        get_temperature_information()
    if args['a'] and not args['nagios']:
        get_memory_information()
        get_cpu_information()
        get_fan_information()
        get_ps_information()
        get_storage_controller_information()
        get_storage_disks_information()
        get_backplane_information()
        get_temperature_information()
    else:
        logger.warning('-a option is not enabled in nagios mode')
