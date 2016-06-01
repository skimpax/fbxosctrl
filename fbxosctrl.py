#! /usr/bin/env python

""" This utility handles some FreeboxOS commands which are sent to a
freebox server to be executed within FreeboxOS app.
Supported services:
- set wifi ON
- set wifi OFF
- set wifi auto
- reboot the Freebox Server

Note: once granted, this app must have 'settings' permissions set
to True in FreeboxOS webgui to be able to modify the configuration. """

import sys
import os
import argparse
import requests
import hmac
import simplejson as json
from hashlib import sha1


# fbxosctrl is a command line utility to get/set dialogs with FreeboxOS
#
# Copyright (C) 2013 Christophe Lherieau (aka skimpax)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

# FreeboxOS API is available here: http://dev.freebox.fr/sdk/os


########################################################################
# Configure parameters below on your own configuration
########################################################################

# your own password configured on your Freebox Server
MAFREEBOX_PASSWD = '!0freebox0!'

# Set to True to enable logging to stdout
gVerbose = False


########################################################################
# Nothing expected to be modified below this line... unless bugs fix ;-)
########################################################################

FBXOSCTRL_VERSION = "1.0.5"

__author__ = "Christophe Lherieau (aka skimpax)"
__copyright__ = "Copyright 2013, Christophe Lherieau"
__credits__ = []
__license__ = "GPL"
__version__ = FBXOSCTRL_VERSION
__maintainer__ = "skimpax"
__email__ = "skimpax@gmail.com"
__status__ = "Production"


# Return code definitions
RC_OK = 0
RC_WIFI_OFF = 0
RC_WIFI_ON = 1

# Descriptor of this app presented to FreeboxOS server to be granted
gAppDesc = {
    "app_id": "fr.freebox.fbxosctrl",
    "app_name": "Skimpax FbxOSCtrl",
    "app_version": FBXOSCTRL_VERSION,
    "device_name": "FbxOS Client"
}


def log(what):
    """ Log to stdout if verbose mode is enabled """
    if True == gVerbose:
        print what


class FbxOSException(Exception):

    """ Exception for FreeboxOS domain """

    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason


class FreeboxOSCtrl:

    """ This class handles connection and dialog with FreeboxOS thanks to
its exposed REST API """

    def __init__(self, fbxAddress="http://mafreebox.freebox.fr",
                 regSaveFile="fbxosctrl_registration.txt"):
        """ Constructor """
        self.fbxAddress = fbxAddress
        self.isLoggedIn = False
        self.registrationSaveFile = regSaveFile
        self.registration = {'app_token': '', 'track_id': None}
        self.challenge = None
        self.sessionToken = None
        self.permissions = None

    def _saveRegistrationParams(self):
        """ Save registration parameters (app_id/token) to a local file """
        log(">>> _saveRegistrationParams")
        with open(self.registrationSaveFile, 'wb') as outfile:
            json.dump(self.registration, outfile)

    def _loadRegistrationParams(self):
        log(">>> _loadRegistrationParams: file: %s" % self.registrationSaveFile)
        if os.path.exists(self.registrationSaveFile):
            with open(self.registrationSaveFile) as infile:
                self.registration = json.load(infile)

    def _login(self):
        """ Login to FreeboxOS using API credentials """
        log(">>> _login")
        if not self.isLoggedIn:
            if not self.isRegistered():
                raise FbxOSException("This app is not registered yet: you have to register it first!")

            # 1st stage: get challenge
            url = self.fbxAddress + "/api/v1/login/"
            # GET
            log("GET url: %s" % url)
            r = requests.get(url, timeout=3)
            log("GET response: %s" % r.text)
            # ensure status_code is 200, else raise exception
            if requests.codes.ok != r.status_code:
                raise FbxOSException("Get error: %s" % r.text)
            # rc is 200 but did we really succeed?
            resp = json.loads(r.text)
            #log("Obj resp: %s" % resp)
            if resp.get('success'):
                if not resp.get('result').get('logged_in'):
                    self.challenge = resp.get('result').get('challenge')
            else:
                raise FbxOSException("Challenge failure: %s" % resp)

            # 2nd stage: open a session
            global gAppDesc
            apptoken = self.registration.get('app_token')
            key = self.challenge
            log("challenge: " + key + ", apptoken: " + apptoken)
            # Encode to plain string as some python versions seem disturbed else (cf. issue#2)
            if type(key) == unicode:
                key = key.encode()
            # Encode to plain string as some python versions seem disturbed else (cf. issue#3)
            if type(apptoken) == unicode:
                apptoken = apptoken.encode()
            # Hashing token with key
            h = hmac.new(apptoken, key, sha1)
            password = h.hexdigest()
            url = self.fbxAddress + "/api/v1/login/session/"
            headers = {'Content-type': 'application/json',
                       'charset': 'utf-8', 'Accept': 'text/plain'}
            payload = {'app_id': gAppDesc.get('app_id'), 'password': password}
            #log("Payload: %s" % payload)
            data = json.dumps(payload)
            log("POST url: %s data: %s" % (url, data))
            # post it
            r = requests.post(url, data, headers=headers, timeout=3)
            # ensure status_code is 200, else raise exception
            log("POST response: %s" % r.text)
            if requests.codes.ok != r.status_code:
                raise FbxOSException("Post response error: %s" % r.text)
            # rc is 200 but did we really succeed?
            resp = json.loads(r.text)
            #log("Obj resp: %s" % resp)
            if resp.get('success'):
                self.sessionToken = resp.get('result').get('session_token')
                self.permissions = resp.get('result').get('permissions')
                log("Permissions: %s" % self.permissions)
                if not self.permissions.get('settings'):
                    print "Warning: permission 'settings' has not been allowed yet \
in FreeboxOS server. This script may fail!"
            else:
                raise FbxOSException("Session failure: %s" % resp)
            self.isLoggedIn = True

    def _logout(self):
        """ logout from FreeboxOS """
        # Not documented yet in the API
        log(">>> _logout")
        if self.isLoggedIn:
            headers = {'X-Fbx-App-Auth': self.sessionToken, 'Accept': 'text/plain'}
            url = self.fbxAddress + "/api/v1/login/logout/"
            # POST
            log("POST url: %s" % url)
            r = requests.post(url, headers=headers, timeout=3)
            log("POST response: %s" % r.text)
            # ensure status_code is 200, else raise exception
            if requests.codes.ok != r.status_code:
                raise FbxOSException("Post error: %s" % r.text)
            # rc is 200 but did we really succeed?
            resp = json.loads(r.text)
            #log("Obj resp: %s" % resp)
            if not resp.get('success'):
                raise FbxOSException("Logout failure: %s" % resp)
        self.isLoggedIn = False

    def _setWifiStatus(self, putOn):
        """ Utility to activate or deactivate wifi radio module """
        log(">>> _setWifiStatus")
        self._login()
        # PUT wifi status
        headers = {'X-Fbx-App-Auth': self.sessionToken, 'Accept': 'text/plain'}
        if putOn:
            data = {'ap_params': {'enabled': True}}
        else:
            data = {'ap_params': {'enabled': False}}
        url = self.fbxAddress + "/api/v1/wifi/config/"
        log("PUT url: %s data: %s" % (url, json.dumps(data)))
        # PUT
        try:
            r = requests.put(url, data=json.dumps(data), headers=headers, timeout=1)
            log("PUT response: %s" % r.text)
        except requests.exceptions.Timeout as timeoutExcept:
            if not putOn:
                # If we are connected using wifi, disabling wifi will close connection
                # thus PUT response will never be received: a timeout is expected
                print "Wifi is now OFF"
                return 0
            else:
                # Forward timeout exception as should not occur
                raise timeoutExcept
        # Response received
        # ensure status_code is 200, else raise exception
        if requests.codes.ok != r.status_code:
            raise FbxOSException("Put error: %s" % r.text)
        # rc is 200 but did we really succeed?
        resp = json.loads(r.text)
        #log("Obj resp: %s" % resp)
        isOn = False
        if True == resp.get('success'):
            if resp.get('result').get('ap_params').get('enabled'):
                print "Wifi is now ON"
                isOn = True
            else:
                print "Wifi is now OFF"
        else:
            raise FbxOSException("Challenge failure: %s" % resp)
        self._logout()
        return isOn

    def _setWifiPlanning(self, putOn):
        """ Utility to activate or deactivate wifi planning mode """
        log(">>> _setWifiPlanning")
        self._login()
        # PUT wifi status
        headers = {'X-Fbx-App-Auth': self.sessionToken, 'Accept': 'text/plain'}
        if putOn:
            data = {'use_planning': True}
        else:
            data = {'use_planning': False}
        url = self.fbxAddress + "/api/v3/wifi/planning"
        log("PUT url: %s data: %s" % (url, json.dumps(data)))
        # PUT
        try:
            r = requests.put(url, data=json.dumps(data), headers=headers, timeout=1)
            log("PUT response: %s" % r.text)
        except requests.exceptions.Timeout as timeoutExcept:
            # Forward timeout exception as should not occur
            raise timeoutExcept
        # Response received
        # ensure status_code is 200, else raise exception
        if requests.codes.ok != r.status_code:
            raise FbxOSException("Put error: %s" % r.text)
        # rc is 200 but did we really succeed?
        resp = json.loads(r.text)
        #log("Obj resp: %s" % resp)
        isOn = False
        if True == resp.get('success'):
            if resp.get('result').get('use_planning'):
                print "Wifi planning is now ON"
                isOn = True
            else:
                print "Wifi planning is now OFF"
        else:
            raise FbxOSException("Challenge failure: %s" % resp)
        self._logout()
        return isOn

    def hasRegistrationParams(self):
        """ Indicate whether registration params look initialized """
        log(">>> hasRegistrationParams")
        if None != self.registration.get('track_id') and '' != self.registration.get('app_token'):
            return True
        else:
            self._loadRegistrationParams()
            return None != self.registration.get('track_id') and '' != self.registration.get('app_token')

    def getRegistrationStatus(self):
        """ Get the current registration status thanks to the track_id """
        log(">>> getRegistrationStatus")
        if self.hasRegistrationParams():
            url = self.fbxAddress + \
                "/api/v1/login/authorize/%s" % self.registration.get('track_id')
            log(url)
            # GET
            log("GET url: %s" % url)
            r = requests.get(url, timeout=3)
            log("GET response: %s" % r.text)
            # ensure status_code is 200, else raise exception
            if requests.codes.ok != r.status_code:
                raise FbxOSException("Get error: %s" % r.text)
            resp = json.loads(r.text)
            return resp.get('result').get('status')
        else:
            return "Not registered yet!"

    def isRegistered(self):
        """ Check that the app is currently registered (granted) """
        log(">>> isRegistered")
        if self.hasRegistrationParams() and 'granted' == self.getRegistrationStatus():
            return True
        else:
            return False

    def registerApp(self):
        """ Register this app to FreeboxOS to that user grants this apps via Freebox Server
LCD screen. This command shall be executed only once. """
        log(">>> registerApp")
        register = True
        if self.hasRegistrationParams():
            status = self.getRegistrationStatus()
            if 'granted' == status:
                print "This app is already granted on Freebox Server (app_id = %s). You can now dialog with it." % self.registration.get('track_id')
                register = False
            elif 'pending' == status:
                print "This app grant is still pending: user should grant it on Freebox Server lcd/touchpad (app_id = %s)." % self.registration.get('track_id')
                register = False
            elif 'unknown' == status:
                print "This app_id (%s) is unknown by Freebox Server: you have to register again to Freebox Server to get a new app_id." % self.registration.get('track_id')
            elif 'denied' == status:
                print "This app has been denied by user on Freebox Server (app_id = %s)." % self.registration.get('track_id')
                register = False
            elif 'timeout' == status:
                print "Timeout occured for this app_id: you have to register again to Freebox Server to get a new app_id (current app_id = %s)." % self.registration.get('track_id')
            else:
                print "Unexpected response: %s" % status

        if register:
            global gAppDesc
            url = self.fbxAddress + "/api/v1/login/authorize/"
            data = json.dumps(gAppDesc)
            headers = {
                'Content-type': 'application/json', 'Accept': 'text/plain'}
            # post it
            log("POST url: %s data: %s" % (url, data))
            r = requests.post(url, data=data, headers=headers, timeout=3)
            log("POST response: %s" % r.text)
            # ensure status_code is 200, else raise exception
            if requests.codes.ok != r.status_code:
                raise FbxOSException("Post error: %s" % r.text)
            # rc is 200 but did we really succeed?
            resp = json.loads(r.text)
            #log("Obj resp: %s" % resp)
            if True == resp.get('success'):
                self.registration['app_token'] = resp.get('result').get('app_token')
                self.registration['track_id'] = resp.get('result').get('track_id')
                self._saveRegistrationParams()
                print "Now you have to accept this app on your Freebox server: take a look on its lcd screen."
            else:
                print "NOK"

    def reboot(self):
        """ Reboot the freebox server now! """
        log(">>> reboot")
        self._login()
        headers = {'X-Fbx-App-Auth': self.sessionToken, 'Accept': 'text/plain'}
        url = self.fbxAddress + "/api/v1/system/reboot/"
        # POST
        log("POST url: %s" % url)
        r = requests.post(url, headers=headers, timeout=3)
        log("POST response: %s" % r.text)
        # ensure status_code is 200, else raise exception
        if requests.codes.ok != r.status_code:
            raise FbxOSException("Post error: %s" % r.text)
        # rc is 200 but did we really succeed?
        resp = json.loads(r.text)
        #log("Obj resp: %s" % resp)
        if not resp.get('success'):
            raise FbxOSException("Logout failure: %s" % resp)
        print "Freebox Server is now rebooting."
        self.isLoggedIn = False
        return True

    def getWifiPlanning(self):
        """ Get the current status of wifi: 1 means planning enabled, 0 means no planning """
        log(">>> getWifiPlanning")
        self._login()
        # GET wifi planning
        headers = {
            'X-Fbx-App-Auth': self.sessionToken, 'Accept': 'text/plain'}
        url = self.fbxAddress + "/api/v1/wifi/planning"
        # GET
        log("GET url: %s" % url)
        r = requests.get(url, headers=headers, timeout=1)
        log("GET response: %s" % r.text)
        # ensure status_code is 200, else raise exception
        if requests.codes.ok != r.status_code:
            raise FbxOSException("Get error: %s" % r.text)
        # rc is 200 but did we really succeed?
        resp = json.loads(r.text)
        #log("Obj resp: %s" % resp)
        isOn = True
        if True == resp.get('success'):
            if resp.get('result').get('use_planning'):
                print "Wifi planning is ON"
                isOn = True
            else:
                print "Wifi planning is OFF"
                isOn = False
        else:
            raise FbxOSException("Challenge failure: %s" % resp)
        self._logout()
        return isOn

    def setWifiPlanningOn(self):
        """ Activate (turn-on) wifi planning mode """
        log(">>> setWifiPlanningOn")
        return self._setWifiPlanning(True)

    def setWifiPlanningOff(self):
        """ Deactivate (turn-off) wifi planning mode """
        log(">>> setWifiPlanningOff")
        return self._setWifiPlanning(False)

    def getWifiStatus(self):
        """ Get the current status of wifi: 1 means ON, 0 means OFF """
        log(">>> getWifiStatus")
        self._login()
        # GET wifi status
        headers = {
            'X-Fbx-App-Auth': self.sessionToken, 'Accept': 'text/plain'}
        url = self.fbxAddress + "/api/v1/wifi/"
        # GET
        log("GET url: %s" % url)
        r = requests.get(url, headers=headers, timeout=1)
        log("GET response: %s" % r.text)
        # ensure status_code is 200, else raise exception
        if requests.codes.ok != r.status_code:
            raise FbxOSException("Get error: %s" % r.text)
        # rc is 200 but did we really succeed?
        resp = json.loads(r.text)
        #log("Obj resp: %s" % resp)
        isOn = True
        if True == resp.get('success'):
            if resp.get('result').get('active'):
                print "Wifi is ON"
                isOn = True
            else:
                print "Wifi is OFF"
                isOn = False
        else:
            raise FbxOSException("Challenge failure: %s" % resp)
        self._logout()
        return isOn

    def setWifiOn(self):
        """ Activate (turn-on) wifi radio module """
        log(">>> setWifiOn")
        return self._setWifiStatus(True)

    def setWifiOff(self):
        """ Deactivate (turn-off) wifi radio module """
        log(">>> setWifiOff")
        return self._setWifiStatus(False)

    def getDhcpLeases(self):
        """ List the DHCP leases on going """
        log(">>> getDhcpLeases")
        self._login()
        # GET wifi status
        headers = {
            'X-Fbx-App-Auth': self.sessionToken, 'Accept': 'text/plain'}
        url = self.fbxAddress + "/api/v1/dhcp/dynamic_lease/"
        # GET
        log("GET url: %s" % url)
        r = requests.get(url, headers=headers, timeout=1)
        log("GET response: %s" % r.text)
        # ensure status_code is 200, else raise exception
        if requests.codes.ok != r.status_code:
            raise FbxOSException("Get error: %s" % r.text)
        # rc is 200 but did we really succeed?
        resp = json.loads(r.text)
        count=1
        if True == resp.get('success'):
            leases = resp.get('result')
            print "List of reachable leases:"
            for lease in leases:
                #print "LEASE: "+str(lease.get('host').get('reachable'))
                if True == lease.get('host').get('reachable'):
                    print "  ["+repr(count)+"]: mac: "+lease.get('mac')+", ip: "+lease.get('ip')+", hostname: "+lease.get('hostname')
                    count += 1
            count = 1
            print "List of unreachable leases:"
            for lease in leases:
                #print "LEASE: "+str(lease)
                if True != lease.get('host').get('reachable'):
                    print "  ["+repr(count)+"]: mac: "+lease.get('mac')+", ip: "+lease.get('ip')+", hostname: "+lease.get('hostname')
                    count += 1
        else:
            raise FbxOSException("Dynamic lease failure: %s" % resp)
        self._logout()
        return 0

class FreeboxOSCli:

    """ Command line (cli) interpreter and dispatch commands to controller """

    def __init__(self, controller):
        """ Constructor """
        self.controller = controller
        # Configure parser
        self.parser = argparse.ArgumentParser(
            description='Command line utility to control some FreeboxOS services.')
        # CLI related actions
        self.parser.add_argument(
            '--version', action='version', version="%(prog)s " + __version__)
        self.parser.add_argument(
            '-v', action='store_true', help='verbose mode')
        self.parser.add_argument(
            '-c', nargs=1, help='configuration file to store/retrieve FreeboxOS registration parameters')
        # Real freeboxOS actions
        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--regapp', default=argparse.SUPPRESS, action='store_true',
            help='register this app to FreeboxOS and save result in configuration file (to be executed only once)')
        group.add_argument('--wifistatus', default=argparse.SUPPRESS,
                           action='store_true', help='get FreeboxOS current wifi status')
        group.add_argument(
            '--won', default=argparse.SUPPRESS, action='store_true', help='turn FreeboxOS wifi ON')
        group.add_argument(
            '--woff', default=argparse.SUPPRESS, action='store_true', help='turn FreeboxOS wifi OFF')
        group.add_argument('--wifiplan', default=argparse.SUPPRESS,
                           action='store_true', help='get FreeboxOS current wifi planning status')
        group.add_argument(
            '--wpon', default=argparse.SUPPRESS, action='store_true', help='turn FreeboxOS wifi planning ON')
        group.add_argument(
            '--wpoff', default=argparse.SUPPRESS, action='store_true', help='turn FreeboxOS wifi planning OFF')
        group.add_argument(
            '--reboot', default=argparse.SUPPRESS, action='store_true', help='reboot the Freebox Server now!')
        group.add_argument(
            '--dhcpleases', default=argparse.SUPPRESS, action='store_true', help='display the current DHCP leases info')
        # Configure cmd=>callback association
        self.cmdCallbacks = {
            'regapp': self.controller.registerApp,
            'wifistatus': self.controller.getWifiStatus,
            'woff': self.controller.setWifiOn,
            'won': self.controller.setWifiOff,
            'wifiplan': self.controller.getWifiPlanning,
            'wpon': self.controller.setWifiPlanningOn,
            'wpoff': self.controller.setWifiPlanningOff,
            'reboot': self.controller.reboot,
            'dhcpleases': self.controller.getDhcpLeases,
        }

    def cmdExec(self, argv):
        """ Parse the parameters and execute the associated command """
        args = self.parser.parse_args(argv)
        argsdict = vars(args)
        # Activate verbose mode if requested
        if True == argsdict.get('v'):
            global gVerbose
            gVerbose = True
        #log("Args dict: %s" % argsdict)
        if argsdict.get('c'):
            self.controller.registrationSaveFile = argsdict.get('c')[0]
        # Suppress '-v' command as not a FreeboxOS cmd
        del argsdict['v']
        del argsdict['c']
        # Let's execute FreeboxOS cmd
        return self.dispatch(argsdict.keys())

    def dispatch(self, args):
        """ Call controller action """
        for cmd in args:
            # retrieve callback associated to cmd and execute it, if not found
            # display help
            return self.cmdCallbacks.get(cmd, self.parser.print_help)()


if __name__ == '__main__':
        controller = FreeboxOSCtrl()
        cli = FreeboxOSCli(controller)
        rc = cli.cmdExec(sys.argv[1:])
        sys.exit(rc)
