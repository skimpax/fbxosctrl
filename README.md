fbxosctrl
=========

This command line utility handles some FreeboxOS commands which are sent to a
freebox server to be executed within FreeboxOS app.
Supported services:
  - set wifi ON
  - set wifi OFF
  - get current wifi status (ON/OFF)
  - reboot the Freebox Server

###### Dependancies:
python-requests and python-simplejson.  
You can use this command to install them:  
> apt-get install python-requests python-simplejson


```bash
usage: fbxosctrl.py [-h] [--version] [-v] [-c C]
                    (--regapp | --wifistatus | --wifion | --wifioff | --reboot)

Command line utility to control some FreeboxOS services.

optional arguments:
  -h, --help    show this help message and exit
  --version     show program's version number and exit
  -v            verbose mode
  -c C          configuration file to store/retrieve FreeboxOS registration
                parameters
  --regapp      register this app to FreeboxOS and save result in
                configuration file (to be executed only once)
  --wifistatus  get FreeboxOS current wifi status
  --wifion      turn FreeboxOS wifi ON
  --wifioff     turn FreeboxOS wifi OFF
  --reboot      reboot the Freebox Server now!
```


