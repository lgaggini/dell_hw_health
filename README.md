# dell_hw_health

dell_hw_healt is a python script to check the health status of Dell harware by iDRAC Redfish protocol, inspired by [Dell official python examples](https://github.com/https://github.com/dell/iDRAC-Redfish-Scripting/tree/master/Redfish%20Python).
It can be used as Nagios/Naemon check or in a report mode.

## Quickstart
## Install
### Requirements
* python request

### Git
```
pip install requests
git clone
```

## Usage
```
usage: dell_hw_health.py [-h] -ip IP -u U -p P [-m] [-c] [-f] [-ps] [-s] [-d]
                         [-b] [-a] [-critical] [-nagios]

Python script using Redfish API to get system hardwareHealth

optional arguments:
  -h, --help  show this help message and exit
  -ip IP      iDRAC IP address
  -u U        iDRAC username
  -p P        iDRAC password
  -m          Get memory information
  -c          Get processor information
  -f          Get fan information
  -ps         Get power supply information
  -s          Get storage controllers information only
  -d          Get disks information only
  -b          Get backplane information only
  -a          Get all information
  -critical   Retrieve only failure for report
  -nagios     Nagios output check mode, only the first option is used
```
