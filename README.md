fbxosctrl
=========

#### Description

Les détails de mise en oeuvre de fbxosctrl sont disponibles sur le wiki : https://github.com/skimpax/fbxosctrl/wiki


This command line utility handles some FreeboxOS commands which are sent to a
freebox server to be executed within FreeboxOS app.

Free is a French DSL operator (free.fr) providing two set-top-box :
  * Freebox Server, connected to the ADSL wire
  * Freebox Player, connected to the TV

This tool applies to the server box of Freebox v6 (aka Freebox Revolution) only with latest firmware (v3.X).
FreeboxOS is the name given by Free.fr to their software running inside the Freebox Server.

The Frebbox Server address is discovered via mDNS and HTTPS is used to dialog with it.

Supported services:
  - get current wifi radio status (ON/OFF)
  - set wifi radio ON/OFF
  - get current wifi planning status (ON/OFF)
  - set wifi planning ON/OFF
  - get current DHCP leases
  - get phone calls list (new only or all)
  - mark phone call as read
  - reboot the Freebox Server
  - display the system information
  - get storage status
  - get downloads status


#### Dependancies:
python3-requests and python3-zeroconf
You can use this command to install them:  
> apt-get install python3-requests python3-zeroconf


#### Output format:
By default, output is printed in human readable format (iow. formated text), potentially with partial information extracted from the FreeboxOS response.
By using option '-j', output is printed in JSON format, containing the whole FreeboxOS response. This allows further processing within upper layer scripts for instance.

Default format:
```
Server info:
 - MAC:       68:A3:00:01:02:03
 - Firmware:  3.5.2
 - Uptime:    1 jour 1 heure 42 minutes 52 secondes
 - Temp CPUb: 61
 - Temp CPUm: 66
 - Temp SW:   55
 - Fan speed: 2567
```
JSON format:
```
{'result': {'serial': '7626000000000000', 'user_main_storage': '', 'temp_cpub': 60, 'temp_cpum': 66, 'uptime': '1 jour 1 heure 43 minutes 50 secondes', 'temp_sw': 55, 'disk_status': 'active', 'board_name': 'fbxgw2r', 'box_authenticated': True, 'firmware_version': '3.5.2', 'uptime_val': 92630, 'fan_rpm': 2570, 'box_flavor': 'full', 'mac': '68:A3:00:01:02:03'}, 'success': True}
```

#### Usage:

```bash
usage: fbxosctrl.py [-h] [--version] [-v] [-j] [-c CONF_PATH]
                    (--regapp | --wrstatus | --wron | --wroff | --wpstatus | --wpon | --wpoff | --dhcpleases | --clist | --cnew | --cread | --reboot | --sinfo | --dlist | --dspace | --tlist)

Command line utility to control some FreeboxOS services.

optional arguments:
  -h, --help    show this help message and exit
  --version     show program's version number and exit
  -v            verbose mode
  -j            simply print Freebox Server reponse in JSON format
  -c CONF_PATH  path where to store/retrieve this app configuration files
                (default: local directory)
  --regapp      register this app to FreeboxOS and save result in
                configuration file (to be executed only once)
  --wrstatus    get FreeboxOS current Wifi Radio status
  --wron        turn FreeboxOS Wifi Radio ON
  --wroff       turn FreeboxOS Wifi Radio OFF
  --wpstatus    get FreeboxOS current Wifi Planning status
  --wpon        turn FreeboxOS Wifi Planning ON
  --wpoff       turn FreeboxOS Wifi Planning OFF
  --dhcpleases  display the current DHCP leases info
  --clist       display the list of received calls
  --cnew        display the list of new received calls
  --cread       set read status for all received calls
  --reboot      reboot the Freebox Server now!
  --sinfo       display the system information
  --dlist       display connected drives
  --dspace      display spaces (total/used/free) on connected drives
  --tlist       display downloads list
```

#### Contributions:

Contributions are welcome.
Just ensure it passes the flake8 tool rules. It is expected that flake8 only complains about E501 rule (line larger than 79 chars) (ancestral rule in my opinion), and a single E122 ( for literal content of RSA certificate).
All other non-conformance should be fixed.

```bash
apt-get install flake8
flake8 fbxosctrl.py
```