fbxosctrl
=========

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


###### Dependancies:
python-requests and python3-zeroconf
You can use this command to install them:  
> apt-get install python-requests python3-zeroconf


###### Usage:

```bash
usage: fbxosctrl.py [-h] [--version] [-v] [-c C] [-j]
                    (--regapp | --wrstatus | --wron | --wroff | --wpstatus | --wpon | --wpoff | --dhcpleases | --clist | --cnew | --cread | --reboot)

Command line utility to control some FreeboxOS services.

optional arguments:
  -h, --help    show this help message and exit
  --version     show program's version number and exit
  -v            verbose mode
  -c C          configuration file to store/retrieve FreeboxOS registration
                parameters
  -j            display the Frebbox Server command response in JSON format
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
  --cread       mark all received calls as read
  --reboot      reboot the Freebox Server now!
```


