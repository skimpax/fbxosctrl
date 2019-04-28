fbxosctrl
=========

### Description

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
  - get contacts list
  - mark phone call as read
  - reboot the Freebox Server
  - display the system information
  - display the line ethernet information (bit rates)
  - display the line media information (xDSL/FTTH)
  - get storage status
  - get downloads status


### Dependencies
python3-requests and python3-zeroconf
You can use this command to install them:  
> apt-get install python3-requests python3-zeroconf


### Output format
By default, output is printed in human readable format (iow. formated text), potentially with partial information extracted from the FreeboxOS response.
By using option '-j', output is printed in JSON format, containing the whole FreeboxOS response. This allows further processing within upper layer scripts for instance.

Default format:
```
Server info:
 - Model:     Freebox Server (r2)
 - MAC:       68:A3:78:01:02:03
 - Firmware:  4.0.4
 - Uptime:    9 jours 51 minutes 56 secondes
 - Sensors:
   - Disque dur:          37°C
   - Température Switch:  53°C
   - Température CPU M:   63°C
   - Température CPU B:   58°C
```
JSON format:
```
{'result': {'serial': '7626000000000000', 'user_main_storage': '', 'temp_cpub': 60, 'temp_cpum': 66, 'uptime': '1 jour 1 heure 43 minutes 50 secondes', 'temp_sw': 55, 'disk_status': 'active', 'board_name': 'fbxgw2r', 'box_authenticated': True, 'firmware_version': '3.5.2', 'uptime_val': 92630, 'fan_rpm': 2570, 'box_flavor': 'full', 'mac': '68:A3:00:01:02:03'}, 'success': True}
```

### Usage

```bash
usage: fbxosctrl.py [-h] [--version] [-v] [-j] [-c CONF_PATH] [--save] [--archive]
                    (--regapp | --wrstatus | --wron | --wroff | --wpstatus | --wpon | --wpoff | --dhcpleases | --dhcpstleases | --pfwd | --clist | --cnew | --cread | --contacts | --reboot | --sinfo | --einfo | --linfo | --dlist | --dspace | --tlist)

Command line utility to control some FreeboxOS services.

optional arguments:
  -h, --help    show this help message and exit
  --version     show program's version number and exit
  -v            verbose mode
  -j            simply print Freebox Server reponse in JSON format
  -c CONF_PATH  path where to store/retrieve this app configuration files
                (default: local directory)
  --save        save to db file (clist, dhcpleases, pfwd only)
  --archive     read from db file (clist, dhcpleases, pfwd only)
  --regapp      register this app to FreeboxOS and save result in
                configuration file (to be executed only once)
  --wrstatus    get FreeboxOS current Wifi Radio status
  --wron        turn FreeboxOS Wifi Radio ON
  --wroff       turn FreeboxOS Wifi Radio OFF
  --wpstatus    get FreeboxOS current Wifi Planning status
  --wpon        turn FreeboxOS Wifi Planning ON
  --wpoff       turn FreeboxOS Wifi Planning OFF
  --dhcpleases  display the current DHCP leases info
                options [--save, --archive]
  --dhcpstleases  display the current DHCP static leases info
                options [--save, --archive, --restore]
  --pfwd        display the list of port forwardings info
                options [--save, --archive, --restore]
  --clist       display the list of received calls
                options [--save, --archive]
  --cnew        display the list of new received calls
  --cread       set read status for all received calls
  --contacts    display the list of contacts
                options [--save, --archive]
  --reboot      reboot the Freebox Server now!
  --sinfo       display the system information
  --einfo       display the line ethernet information
  --linfo       display the line media (ADSL/Fiber) information
  --dlist       display connected drives
  --dspace      display spaces (total/used/free) on connected drives
  --tlist       display downloads list
```

### Contributions

Contributions are welcome.
Just ensure it passes the flake8 tool rules. It is expected that flake8 only complains about E501 rule (line larger than 79 chars) (ancestral rule in my opinion), and a single E122 ( for literal content of RSA certificate).
All other non-conformance should be fixed.

```bash
apt-get install flake8
flake8 fbxosctrl.py
```
