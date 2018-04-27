#!/usr/bin/env python3

# -*- coding: utf-8 -*-
########################################################################
# Nothing expected to be modified below this line... unless bugs fix ;-)
########################################################################

import argparse
import os
import sys
import json
import requests
import hmac
from zeroconf import Zeroconf
from datetime import datetime, timedelta


FBXOSCTRL_VERSION = "2.3.0"

__author__ = "Christophe Lherieau (aka skimpax)"
__copyright__ = "Copyright 2018, Christophe Lherieau"
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
g_app_desc = {
    "app_id": "fr.freebox.fbxosctrl",
    "app_name": "Skimpax FbxOSCtrl",
    "app_version": "2.0.0",
    "device_name": "FbxOS Client"
}


g_log_enabled = False


def log(what):
    """Logger function"""
    global g_log_enabled
    if g_log_enabled:
        print(what)


def enable_log(is_enabled):
    """Update log state"""
    global g_log_enabled
    g_log_enabled = is_enabled


class FbxException(Exception):
    """ Exception for FreeboxOS domain """

    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason


class FbxConfiguration:
    """Configuration/registration management"""

    def __init__(self, app_desc):
        """Constructor"""
        self._app_desc = app_desc
        self._addr_file = 'fbxosctrl_addressing.txt'
        self._reg_file = 'fbxosctrl_registration.txt'
        self._addr_params = None
        self._reg_params = None
        self._resp_as_json = False
        self._conf_path = '.'

    @property
    def freebox_address(self):
        url = '{}://{}:{}'.format(
            self._addr_params['protocol'],
            self._addr_params['api_domain'],
            self._addr_params['port'])
        return url

    @property
    def app_desc(self):
        return self._app_desc

    @property
    def reg_file(self):
        return self._reg_file

    @reg_file.setter
    def reg_file(self, reg_file):
        self._reg_file = reg_file

    @property
    def reg_params(self):
        return self._reg_params

    @reg_params.setter
    def reg_params(self, reg_params):
        self._reg_params = reg_params
        self._save_registration_params()

    @property
    def resp_as_json(self):
        return self._resp_as_json

    @resp_as_json.setter
    def resp_as_json(self, resp_as_json):
        self._resp_as_json = resp_as_json

    @property
    def conf_path(self):
        return self._conf_path

    @conf_path.setter
    def conf_path(self, conf_path):
        log('>>> conf_path: {}'.format(conf_path))
        if conf_path.endswith('/'):
            conf_path = conf_path[:-1]
        self._conf_path = conf_path
        self._addr_file = self._conf_path + '/' + self._addr_file
        self._reg_file = self._conf_path + '/' + self._reg_file

    def load(self, want_regapp):
        """Load configuration params"""
        log('>>> load')
        self._load_addressing_params()
        self._load_registration_params()

        if self._reg_params is None:
            if not want_regapp:
                print('No registration params found in directory: {}'.format(self._conf_path))
                print("You should launch 'fbxosctrl --regapp' once to register to the Freebox Server first.")
                sys.exit(0)
            else:
                # use wants to register: this is normal not having reg params yet
                pass
        else:
            url = self.freebox_address
            if not self.resp_as_json:
                # print only if not in JSON format
                print('Freebox Server is accessible via: {}'.format(url))

    def has_registration_params(self):
        """ Indicate whether registration params look initialized """
        log('>>> has_registration_params')
        if (self._reg_params and
                self._reg_params.get('track_id') is not None and
                self._reg_params.get('app_token') is not ''):
            return True
        else:
            return False

    def api_address(self, api_url=None):
        """Build the full API URL based on the mDNS info"""
        url = '{freebox_addr}{api_base_url}v{major_api_version}'.format(
            freebox_addr=self.freebox_address,
            api_base_url=self._addr_params['api_base_url'],
            major_api_version=self._addr_params['api_version'][:1])
        if api_url:
            if api_url[0] != '/':
                url += '/'
            url += '{}'.format(api_url)
        return url

    def _fetch_fbx_mdns_info_via_mdns(self):
        print('Querying mDNS about Freebox Server information...')
        r = Zeroconf()
        info = r.get_service_info('_fbx-api._tcp.local.', 'Freebox Server._fbx-api._tcp.local.')
        r.close()
        return info

    def _save_registration_params(self):
        """ Save registration parameters (app_id/token) to a local file """
        log('>>> save_registration_params')
        with open(self._reg_file, 'w') as of:
            json.dump(self._reg_params, of, indent=True, sort_keys=True)

    def _load_addressing_params(self):
        """Load existing addressing params or get the via mDNS"""
        if os.path.exists(self._addr_file):
            with open(self._addr_file) as infile:
                self._addr_params = json.load(infile)

        elif self._addr_params is None:
            mdns_info = self._fetch_fbx_mdns_info_via_mdns()
            log('Freebox mDNS info: {}'.format(mdns_info))
            self._addr_params = {}
            self._addr_params['protocol'] = 'https' if mdns_info.properties[b'https_available'].decode() else 'http'
            self._addr_params['api_domain'] = mdns_info.properties[b'api_domain'].decode()
            self._addr_params['port'] = mdns_info.properties[b'https_port'].decode()
            self._addr_params['api_base_url'] = mdns_info.properties[b'api_base_url'].decode()
            self._addr_params['api_version'] = mdns_info.properties[b'api_version'].decode()
            with open(self._addr_file, 'w') as of:
                json.dump(self._addr_params, of, indent=True, sort_keys=True)

    def _load_registration_params(self):
        log('>>> load_registration_params: file: {}'.format(self._reg_file))
        if os.path.exists(self._reg_file):
            with open(self._reg_file) as infile:
                self._reg_params = json.load(infile)


class FbxResponse:
    """"Response from Freebox"""

    @staticmethod
    def build(jsonresp):
        """Constructor"""
        return FbxResponse(jsonresp)

    def __init__(self, jsonresp):
        """Constructor"""
        # convert to obj
        self._resp = json.loads(jsonresp)
        # expected content checks
        if self._resp.get('success') is None:
            raise FbxException('Mandatory field missing: success')
        elif self._resp.get('success') is not True and self._resp['success'] is not False:
            raise FbxException('Field success must be either true or false')

        if self._resp['success'] is False:
            if self._resp.get('msg') is None:
                raise FbxException('Mandatory error field missing: msg')
            if self._resp.get('error_code') is None:
                raise FbxException('Mandatory error field missing: error_code')

    @property
    def whole_content(self):
        """Return operation whole response"""
        return self._resp

    @property
    def success(self):
        """Return operation success status"""
        return self._resp.get('success')

    @property
    def result(self):
        """Return operation success result"""
        return self._resp.get('result')

    @property
    def error_msg(self):
        """Return operation error message"""
        return self._resp.get('msg')

    @property
    def error_code(self):
        """Return operation error code"""
        return self._resp.get('error_code')


class FbxHttp():
    """"HTTP transporter"""

    def __init__(self, conf):
        """Constructor"""
        self._conf = conf
        self._http_timeout = 30
        self._is_logged_in = False
        self._challenge = None
        self._session_token = None
        self._certificates_file = 'fbxosctrl_certificates.txt'
        self._make_certificate_chain()

    def __del__(self):
        """Logout on deletion"""
        if self._is_logged_in:
            try:
                self._logout()
            except Exception:
                pass

    @property
    def headers(self):
        """Build headers"""
        h = {'Content-type': 'application/json', 'Accept': 'application/json'}
        if self._session_token is not None:
            h['X-Fbx-App-Auth'] = self._session_token
        return h

    def get(self, uri, timeout=None, no_login=False):
        """GET request"""
        log(">>> get")
        if not no_login:
            self._login()

        url = self._conf.api_address(uri)
        log('GET url: {}'.format(url))

        r = requests.get(
            url,
            verify=self._certificates_file,
            headers=self.headers,
            timeout=timeout if timeout is not None else self._http_timeout)
        log('GET response: {}'.format(r.text))

        # ensure status_code is 200, else raise exception
        if requests.codes.ok != r.status_code:
            raise FbxException('GET error - http_status: {} {}'.format(r.status_code, r.text))

        return FbxResponse.build(r.text)

    def put(self, uri, data, timeout=None, no_login=False):
        """PUT request"""
        log(">>> put")
        if not no_login:
            self._login()

        url = self._conf.api_address(uri)
        jdata = json.dumps(data)
        log('PUT url: {} data: {}'.format(url, jdata))

        r = requests.put(
            url,
            verify=self._certificates_file,
            data=jdata,
            headers=self.headers,
            timeout=timeout if timeout is not None else self._http_timeout)
        log('PUT response: {}'.format(r.text))

        # ensure status_code is 200, else raise exception
        if requests.codes.ok != r.status_code:
            raise FbxException('PUT error - http_status: {} {}'.format(r.status_code, r.text))

        return FbxResponse.build(r.text)

    def post(self, uri, data, timeout=None, no_login=False):
        """POST request"""
        log(">>> post")
        if not no_login:
            self._login()

        url = self._conf.api_address(uri)
        jdata = json.dumps(data)
        log('POST url: {} data: {}'.format(url, jdata))

        r = requests.post(
            url,
            verify=self._certificates_file,
            data=jdata,
            headers=self.headers,
            timeout=timeout if timeout is not None else self._http_timeout)
        log('POST response: {}'.format(r.text))

        # ensure status_code is 200, else raise exception
        if requests.codes.ok != r.status_code:
            raise FbxException('POST error - http_status: {} {}'.format(r.status_code, r.text))

        return FbxResponse.build(r.text)

    def _login(self):
        """ Login to FreeboxOS using API credentials """
        log(">>> _login")
        if not self._is_logged_in:
            self._session_token = None

            # 1st stage: get challenge
            resp = self.get('/login', no_login=True)

            if resp.success:
                if not resp.result.get('logged_in'):
                    self._challenge = resp.result.get('challenge')
            else:
                raise FbxException('Challenge failure: {}'.format(resp))

            # 2nd stage: open a session
            app_token = self._conf.reg_params.get('app_token')
            log('challenge: {}, apptoken: {}'.format(self._challenge, app_token))
            # Hashing token with key
            password = hmac.new(app_token.encode(), self._challenge.encode(), 'sha1').hexdigest()
            uri = '/login/session/'
            payload = {'app_id': self._conf.app_desc.get('app_id'), 'password': password}
            # post it
            resp = self.post(uri, payload, no_login=True)

            if resp.success:
                self._session_token = resp.result.get('session_token')
                permissions = resp.result.get('permissions')
                log('Permissions: {}'.format(permissions))
                if not permissions.get('settings'):
                    print(
                        "Warning: permission 'settings' has not been allowed yet" +
                        ' in FreeboxOS server. This script may fail!')
            else:
                raise FbxException('Session failure: {}'.format(resp))

            # set headers for next dialogs
            self._is_logged_in = True

    def _logout(self):
        """ logout from FreeboxOS """
        log(">>> _logout")
        if self._is_logged_in:
            url = self._conf.api_address('/login/logout/')
            resp = self._http.post(url, headers=self.headers)

            # reset headers as no more dialogs expected
            self._http_headers = None

            if not resp.success:
                raise FbxException('Logout failure: {}'.format(resp))
        self._session_token = None
        self._is_logged_in = False

    def _make_certificate_chain(self):
        """Store the certificate chain required for HTTPS"""
        with open(self._certificates_file, 'w') as of:
            of.write(
                # see https://dev.freebox.fr/sdk/os/# for content below
"""-----BEGIN CERTIFICATE-----
MIICWTCCAd+gAwIBAgIJAMaRcLnIgyukMAoGCCqGSM49BAMCMGExCzAJBgNVBAYT
AkZSMQ8wDQYDVQQIDAZGcmFuY2UxDjAMBgNVBAcMBVBhcmlzMRMwEQYDVQQKDApG
cmVlYm94IFNBMRwwGgYDVQQDDBNGcmVlYm94IEVDQyBSb290IENBMB4XDTE1MDkw
MTE4MDIwN1oXDTM1MDgyNzE4MDIwN1owYTELMAkGA1UEBhMCRlIxDzANBgNVBAgM
BkZyYW5jZTEOMAwGA1UEBwwFUGFyaXMxEzARBgNVBAoMCkZyZWVib3ggU0ExHDAa
BgNVBAMME0ZyZWVib3ggRUNDIFJvb3QgQ0EwdjAQBgcqhkjOPQIBBgUrgQQAIgNi
AASCjD6ZKn5ko6cU5Vxh8GA1KqRi6p2GQzndxHtuUmwY8RvBbhZ0GIL7bQ4f08ae
JOv0ycWjEW0fyOnAw6AYdsN6y1eNvH2DVfoXQyGoCSvXQNAUxla+sJuLGICRYiZz
mnijYzBhMB0GA1UdDgQWBBTIB3c2GlbV6EIh2ErEMJvFxMz/QTAfBgNVHSMEGDAW
gBTIB3c2GlbV6EIh2ErEMJvFxMz/QTAPBgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB
/wQEAwIBhjAKBggqhkjOPQQDAgNoADBlAjA8tzEMRVX8vrFuOGDhvZr7OSJjbBr8
gl2I70LeVNGEXZsAThUkqj5Rg9bV8xw3aSMCMQCDjB5CgsLH8EdZmiksdBRRKM2r
vxo6c0dSSNrr7dDN+m2/dRvgoIpGL2GauOGqDFY=
-----END CERTIFICATE-----
-----BEGIN CERTIFICATE-----
MIIFmjCCA4KgAwIBAgIJAKLyz15lYOrYMA0GCSqGSIb3DQEBCwUAMFoxCzAJBgNV
BAYTAkZSMQ8wDQYDVQQIDAZGcmFuY2UxDjAMBgNVBAcMBVBhcmlzMRAwDgYDVQQK
DAdGcmVlYm94MRgwFgYDVQQDDA9GcmVlYm94IFJvb3QgQ0EwHhcNMTUwNzMwMTUw
OTIwWhcNMzUwNzI1MTUwOTIwWjBaMQswCQYDVQQGEwJGUjEPMA0GA1UECAwGRnJh
bmNlMQ4wDAYDVQQHDAVQYXJpczEQMA4GA1UECgwHRnJlZWJveDEYMBYGA1UEAwwP
RnJlZWJveCBSb290IENBMIICIjANBgkqhkiG9w0BAQEFAAOCAg8AMIICCgKCAgEA
xqYIvq8538SH6BJ99jDlOPoyDBrlwKEp879oYplicTC2/p0X66R/ft0en1uSQadC
sL/JTyfgyJAgI1Dq2Y5EYVT/7G6GBtVH6Bxa713mM+I/v0JlTGFalgMqamMuIRDQ
tdyvqEIs8DcfGB/1l2A8UhKOFbHQsMcigxOe9ZodMhtVNn0mUyG+9Zgu1e/YMhsS
iG4Kqap6TGtk80yruS1mMWVSgLOq9F5BGD4rlNlWLo0C3R10mFCpqvsFU+g4kYoA
dTxaIpi1pgng3CGLE0FXgwstJz8RBaZObYEslEYKDzmer5zrU1pVHiwkjsgwbnuy
WtM1Xry3Jxc7N/i1rxFmN/4l/Tcb1F7x4yVZmrzbQVptKSmyTEvPvpzqzdxVWuYi
qIFSe/njl8dX9v5hjbMo4CeLuXIRE4nSq2A7GBm4j9Zb6/l2WIBpnCKtwUVlroKw
NBgB6zHg5WI9nWGuy3ozpP4zyxqXhaTgrQcDDIG/SQS1GOXKGdkCcSa+VkJ0jTf5
od7PxBn9/TuN0yYdgQK3YDjD9F9+CLp8QZK1bnPdVGywPfL1iztngF9J6JohTyL/
VMvpWfS/X6R4Y3p8/eSio4BNuPvm9r0xp6IMpW92V8SYL0N6TQQxzZYgkLV7TbQI
Hw6v64yMbbF0YS9VjS0sFpZcFERVQiodRu7nYNC1jy8CAwEAAaNjMGEwHQYDVR0O
BBYEFD2erMkECujilR0BuER09FdsYIebMB8GA1UdIwQYMBaAFD2erMkECujilR0B
uER09FdsYIebMA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgGGMA0GCSqG
SIb3DQEBCwUAA4ICAQAZ2Nx8mWIWckNY8X2t/ymmCbcKxGw8Hn3BfTDcUWQ7GLRf
MGzTqxGSLBQ5tENaclbtTpNrqPv2k6LY0VjfrKoTSS8JfXkm6+FUtyXpsGK8MrLL
hZ/YdADTfbbWOjjD0VaPUoglvo2N4n7rOuRxVYIij11fL/wl3OUZ7GHLgL3qXSz0
+RGW+1oZo8HQ7pb6RwLfv42Gf+2gyNBckM7VVh9R19UkLCsHFqhFBbUmqwJgNA2/
3twgV6Y26qlyHXXODUfV3arLCwFoNB+IIrde1E/JoOry9oKvF8DZTo/Qm6o2KsdZ
dxs/YcIUsCvKX8WCKtH6la/kFCUcXIb8f1u+Y4pjj3PBmKI/1+Rs9GqB0kt1otyx
Q6bqxqBSgsrkuhCfRxwjbfBgmXjIZ/a4muY5uMI0gbl9zbMFEJHDojhH6TUB5qd0
JJlI61gldaT5Ci1aLbvVcJtdeGhElf7pOE9JrXINpP3NOJJaUSueAvxyj/WWoo0v
4KO7njox8F6jCHALNDLdTsX0FTGmUZ/s/QfJry3VNwyjCyWDy1ra4KWoqt6U7SzM
d5jENIZChM8TnDXJzqc+mu00cI3icn9bV9flYCXLTIsprB21wVSMh0XeBGylKxeB
S27oDfFq04XSox7JM9HdTt2hLK96x1T7FpFrBTnALzb7vHv9MhXqAT90fPR/8A==
-----END CERTIFICATE-----
""")


class FbxServiceAuth:
    """"Authentication domain"""

    def __init__(self, http, conf):
        """Constructor"""
        self._http = http
        self._conf = conf
        self._registered = False

    def is_registered(self):
        """ Check that the app is currently registered (granted) """
        log(">>> is_registered")
        if self._registered:
            return True
        self._registered = (self.get_registration_status() == 'granted')
        return self._registered

    def get_registration_status(self):
        """ Get the current registration status thanks to the track_id """
        log(">>> get_registration_status")
        if self._conf.has_registration_params():
            uri = '/login/authorize/{}'.format(self._conf.reg_params.get('track_id'))
            resp = self._http.get(uri, no_login=True)

            return resp.result.get('status')
        else:
            return "Not registered yet!"

    def get_registration_status_diagnostic(self):
        """ Get the current registration status and display diagnosic """
        log(">>> get_registration_status_diagnostic")
        status = self.get_registration_status()
        track_id = self._conf.reg_params.get('track_id')
        if 'granted' == status:
            print(
                'This app is already granted on Freebox Server' +
                ' (track_id={}).'.format(track_id) + ' You can now dialog with it.')
        elif 'pending' == status:
            print(
                'This app grant is still pending: user should grant it' +
                ' on Freebox Server lcd/touchpad (track_id = {}).'
                .format(track_id))
        elif 'unknown' == status:
            print(
                'This track_id ({}) is unknown by Freebox Server: '.format(track_id) +
                'you have to register again to Freebox Server to get a new app_id.')
        elif 'denied' == status:
            print(
                'This app has been denied by user on Freebox Server (track_id = {}).'
                .format(self._conf.reg_params.get('track_id')))
        elif 'timeout' == status:
            print(
                'Timeout occured for this app_id: you have to register again' +
                ' to Freebox Server to get a new app_id (current track_id = {}).'
                .format(track_id))
        else:
            print('Unexpected response: {}'.format(status))
        return status

    def register_app(self):
        """ Register this app to FreeboxOS to that user grants this apps via Freebox Server
LCD screen. This command shall be executed only once. """
        log(">>> register_app")
        register = True
        if self._conf.has_registration_params():
            status = self.get_registration_status_diagnostic()
            if 'granted' == status:
                register = False

        if register:
            self._conf._load_addressing_params()
            uri = '/login/authorize/'
            data = self._conf.app_desc
            # post it
            resp = self._http.post(uri, data=data, no_login=True)

            # save registration params
            if resp.success:
                params = {
                    'app_token': resp.result.get('app_token'),
                    'track_id': resp.result.get('track_id')}
                self._conf.reg_params = params
                print(
                    'Now you have to accept this app on your Freebox server:' +
                    ' take a look on its LCD screen.')
                print(input('Press Enter key once you have accepted on LCD screen: '))
                # check new status (it seems to be mandatory to reach in 'granted' state)
                status = self.get_registration_status_diagnostic()
                print('{}'.format('OK' if 'granted' == status else 'NOK'))
            else:
                print('NOK')


class FbxServiceSystem:
    """System domain"""

    def __init__(self, http, conf):
        """Constructor"""
        self._http = http
        self._conf = conf

    def reboot(self):
        """ Reboot the freebox server now! """
        log(">>> reboot")
        uri = '/system/reboot/'
        self._http.post(uri, timeout=3)
        return True

    def get_system_info(self):
        """Retrieve the system info"""
        uri = '/system'
        resp = self._http.get(uri)

        if self._conf.resp_as_json:
            return resp.whole_content

        print('Server info:')
        print(' - MAC:       {}'.format(resp.result['mac']))
        print(' - Firmware:  {}'.format(resp.result['firmware_version']))
        print(' - Uptime:    {}'.format(resp.result['uptime']))
        print(' - Temp CPUb: {}'.format(resp.result['temp_cpub']))
        print(' - Temp CPUm: {}'.format(resp.result['temp_cpum']))
        print(' - Temp SW:   {}'.format(resp.result['temp_sw']))
        print(' - Fan speed: {}'.format(resp.result['fan_rpm']))
        return True


class FbxServiceStorage:
    """Storage domain"""

    def __init__(self, http, conf):
        """Constructor"""
        self._http = http
        self._conf = conf

    def get_connected_drives(self):
        """Retrieve the spining state for drives"""
        uri = '/storage/disk/'
        resp = self._http.get(uri)

        if self._conf.resp_as_json:
            return resp.whole_content

        print('Drives connected :')
        for drive in resp.result:
            model = drive['model']
            serial = drive['serial']

            if model == '':
                model = '_no_brand_'
            if serial == '':
                serial = '_no_serial_'

            temp = drive['temp']
            spinning = drive['spinning']

            print(' - {} ({}) | temp: {} | spining: {}'.format(model, serial, temp, spinning))
        return True

    def get_storage_status(self):
        """Retrieve the storage partitions and spaces"""
        uri = '/storage/disk/'
        resp = self._http.get(uri)

        if self._conf.resp_as_json:
            return resp.whole_content

        print('Storage info:')
        for drive in resp.result:
            model = drive['model']
            if model == '':
                model = '_no_brand_'

            print(' - {}'.format(model))
            for part in drive['partitions']:
                if part['total_bytes'] > pow(1024, 3):
                    total = part['total_bytes'] / pow(1024, 3)
                    avail = part['free_bytes'] / pow(1024, 3)
                    used = part['used_bytes'] / pow(1024, 3)
                    unit = 'Go'
                else:
                    total = part['total_bytes'] / pow(1024, 2)
                    avail = part['free_bytes'] / pow(1024, 2)
                    used = part['used_bytes'] / pow(1024, 2)
                    unit = 'Mo'
                free_percent = avail * 100 / total
                print(
                    '    #{:15s} :\t'.format(part['label']) +
                    'total: {value:4.0f}{unit} |'.format(value=total, unit=unit) +
                    ' used: {value:4.0f}{unit} |'.format(value=used, unit=unit) +
                    ' free: {value:4.0f}{unit}'.format(value=avail, unit=unit) +
                    ' ({value:.1f}{unit} free)'.format(value=free_percent, unit='%'))

        return True


class FbxServiceWifi:
    """Wifi domain"""

    def __init__(self, http, conf):
        """Constructor"""
        self._http = http
        self._conf = conf

    def get_wifi_config(self):
        """Get the current wifi config"""
        uri = '/wifi/config/'
        resp = self._http.get(uri)
        return resp

    def get_wifi_radio_state(self):
        """ Get the current status of wifi radio: 1 means ON, 0 means OFF """
        log('>>> get_wifi_radio_state')
        uri = '/wifi/config/'
        resp = self._http.get(uri)

        if self._conf.resp_as_json:
            return resp.whole_content

        is_on = resp.success and resp.result.get('enabled')
        print('Wifi is {}'.format('ON' if is_on else 'OFF'))
        return is_on

    def set_wifi_radio_on(self):
        self._set_wifi_radio_state(True)

    def set_wifi_radio_off(self):
        self._set_wifi_radio_state(False)

    def _set_wifi_radio_state(self, set_on):
        """ Utility to activate or deactivate wifi radio module """
        log('>>> set_wifi_radio_state {}'.format('ON' if set_on else 'OFF'))
        # PUT wifi status
        uri = '/wifi/config/'
        data = {'enabled': True} if set_on else {'enabled': False}
        timeout = 3 if not set_on else None

        # PUT
        try:
            resp = self._http.put(uri, data=data, timeout=timeout)
        except requests.exceptions.Timeout as exc:
            if not set_on:
                # If we are connected using wifi, disabling wifi will close connection
                # thus PUT response will never be received: a timeout is expected
                print('Wifi radio is now OFF')
                return 0
            else:
                # Forward timeout exception as should not occur
                raise exc

        if not resp.success:
            raise FbxException('Request failure: {}'.format(resp))

        if self._conf.resp_as_json:
            return resp.whole_content

        is_on = resp.result.get('enabled')
        print('Wifi radio is now {}'.format('ON' if is_on else 'OFF'))
        return is_on

    def get_wifi_planning(self):
        """ Get the current status of wifi: 1 means planning enabled, 0 means no planning """
        log('>>> get_wifi_planning')
        uri = '/wifi/planning/'
        resp = self._http.get(uri)

        if self._conf.resp_as_json:
            return resp.whole_content

        is_on = resp.success and resp.result.get('use_planning')
        print('Wifi planning is {}'.format('ON' if is_on else 'OFF'))
        return is_on

    def set_wifi_planning_on(self):
        self._set_wifi_planning(True)

    def set_wifi_planning_off(self):
        self._set_wifi_planning(False)

    def _set_wifi_planning(self, set_on):
        """ Utility to activate or deactivate wifi planning mode """
        log('>>> set_wifi_planning {}'.format('ON' if set_on else 'OFF'))
        # PUT wifi planning
        url = '/wifi/planning/'
        data = {'use_planning': True} if set_on else {'use_planning': False}

        resp = self._http.put(url, data=data)

        if not resp.success:
            raise FbxException('Request failure: {}'.format(resp))

        if self._conf.resp_as_json:
            return resp.whole_content

        is_on = resp.result.get('use_planning')
        print('Wifi planning is now {}'.format('ON' if is_on else 'OFF'))
        return is_on


class FbxServiceDhcp:
    """DHCP domain"""

    def __init__(self, http, conf):
        """Constructor"""
        self._http = http
        self._conf = conf

    def get_config(self):
        """Get the current DHCP config"""
        uri = '/dhcp/config/'
        resp = self._http.get(uri)
        return resp

    def get_dhcp_leases(self):
        """ List the DHCP leases on going"""
        log(">>> get_dhcp_leases")
        # GET wifi status
        uri = '/dhcp/dynamic_lease/'
        resp = self._http.get(uri)

        if not resp.success:
            raise FbxException('Request failure: {}'.format(resp))

        # json response format
        if self._conf.resp_as_json:
            return resp.whole_content

        # human response format
        leases = resp.result
        if leases is None:
            print('No DHCP leases')
            return 0

        count = 1
        print('List of reachable leases:')
        for lease in leases:
            if lease.get('host').get('reachable'):
                print(
                    '  #{}: mac: {}, ip: {}, hostname: {}, static: {}'
                    .format(
                        count, lease.get('mac'), lease.get('ip'),
                        lease.get('hostname'), lease.get('is_static')))
                count += 1

        count = 1
        print('List of unreachable leases:')
        for lease in leases:
            if lease.get('host').get('reachable') is False:
                print(
                    '  #{}: mac: {}, ip: {}, hostname: {}, static: {}'
                    .format(
                        count, lease.get('mac'), lease.get('ip'),
                        lease.get('hostname'), lease.get('is_static')))
                count += 1
        return 0


class FbxServiceCall:
    """Call domain"""

    def __init__(self, http, conf):
        """Constructor"""
        self._http = http
        self._conf = conf

    def get_new_calls_list(self):
        """ List new calls """
        log(">>> get_new_calls_list")
        return self._get_calls_list(True)

    def get_all_calls_list(self):
        """ List all the calls """
        log(">>> get_all_calls_list")
        return self._get_calls_list(False)

    def _get_calls_list(self, new_only):
        """ List all the calls """
        uri = '/call/log/'
        resp = self._http.get(uri)

        if not resp.success:
            raise FbxException('Request failure: {}'.format(resp))

        # json response format
        if self._conf.resp_as_json:
            return resp.whole_content

        count = 0
        calls = resp.result
        for call in calls:
            # for new call only, we display new calls only
            if new_only and call.get('new') is False:
                continue

            count += 1
            # call to be displayed
            timestamp = call.get('datetime')
            duration = call.get('duration')
            number = call.get('number')
            name = call.get('name')

            strdate = datetime.fromtimestamp(
                timestamp).strftime('%d-%m-%Y %H:%M:%S')
            strdur = datetime.fromtimestamp(
                duration).strftime('%M:%S')

            status = call.get('type')
            tag = '<' if status == 'outgoing'else '!' if status == 'missed' else '>'
            naming = ' ({})'.format(name) if number != name else ''
            dur = ' - {}'.format(strdur) if status != "missed" and duration else ''
            print('{} {} {}{}{}'.format(strdate, tag, number, naming, dur))

        return count > 0

    def mark_calls_as_read(self):
        """ Mark all the calls as read """
        log(">>> mark_calls_as_read")

        uri = '/call/log/mark_all_as_read/'
        data = {}
        resp = self._http.post(uri, data)

        if not resp.success:
            raise FbxException('Request failure: {}'.format(resp))

        # json response format
        if self._conf.resp_as_json:
            return resp.whole_content

        return 0


class FbxServiceDownload:
    """Download domain"""

    def __init__(self, http, conf):
        """Constructor"""
        self._http = http
        self._conf = conf

    def get_downloads_list(self):
        """ List downloads """
        uri = '/downloads/'
        resp = self._http.get(uri)

        if not resp.success:
            raise FbxException('Request failure: {}'.format(resp))

        # json response format
        if self._conf.resp_as_json:
            return resp.whole_content

        count = 0
        dls = resp.result
        if dls:
            dl = {}
            dl['Torrents'] = [x for x in dls if x.get('type') == 'bt']
            dl['HTTPs'] = [x for x in dls if x.get('type') == 'http']
            dl['FTPs'] = [x for x in dls if x.get('type') == 'ftp']
            dl['NewsGp'] = [x for x in dls if x.get('type') == 'nzb']
            for dl_type in ['Torrents', 'HTTPs', 'FTPs', 'NewsGp']:
                nb = 0
                if len(dl[dl_type]):
                    for data in dl[dl_type]:
                        nb += 1
                        eta = timedelta(seconds=data.get('eta')).__str__()
                        rx_rate = data.get('rx_rate')
                        if rx_rate > 1000000:
                            rx_rate /= 1000000
                            rx_unit = 'Mo/s'
                        elif rx_rate > 1000:
                            rx_rate /= 1000
                            rx_unit = 'Ko/s'
                        else:
                            rx_unit = 'o/s'
                        completion = data.get('rx_bytes') * 100 / data.get('size')
                        print('{}:'.format(dl_type))
                        print(
                            '  #{}: name: {} |'.format(nb, data.get('name')) +
                            ' tx_bytes: {} |'.format(data.get('tx_bytes')) +
                            ' rx_bytes: {} ({:.1f}%) |'.format(data.get('rx_bytes'), completion) +
                            ' rx_rate: {:.1f}{} |'.format(rx_rate, rx_unit) +
                            ' ETA: {}'.format(eta))
                else:
                    print('{}:\t--'.format(dl_type))
                count += nb
        else:
            print('No download currently.')

        return count > 0


class FreeboxOSCtrl:
    """"""
    def __init__(self):
        """Constructor"""
        self._conf = FbxConfiguration(g_app_desc)
        self._http = FbxHttp(self._conf)
        self._srv_auth = FbxServiceAuth(self._http, self._conf)
        self._srv_system = FbxServiceSystem(self._http, self._conf)
        self._srv_storage = FbxServiceStorage(self._http, self._conf)
        self._srv_download = FbxServiceDownload(self._http, self._conf)
        self._srv_wifi = FbxServiceWifi(self._http, self._conf)
        self._srv_dhcp = FbxServiceDhcp(self._http, self._conf)
        self._srv_call = FbxServiceCall(self._http, self._conf)

    @property
    def conf(self):
        return self._conf

    @property
    def srv_auth(self):
        return self._srv_auth

    @property
    def srv_system(self):
        return self._srv_system

    @property
    def srv_storage(self):
        return self._srv_storage

    @property
    def srv_download(self):
        return self._srv_download

    @property
    def srv_wifi(self):
        return self._srv_wifi

    @property
    def srv_dhcp(self):
        return self._srv_dhcp

    @property
    def srv_call(self):
        return self._srv_call


class FreeboxOSCli:
    """ Command line (cli) interpreter and dispatch commands to controller """

    def __init__(self, controller):
        """ Constructor """
        self._ctrl = controller
        # Configure parser
        self._parser = argparse.ArgumentParser(
            description='Command line utility to control some FreeboxOS services.')
        # CLI related actions
        self._parser.add_argument(
            '--version',
            action='version',
            version="%(prog)s " + __version__)
        self._parser.add_argument(
            '-v',
            action='store_true',
            help='verbose mode')
        self._parser.add_argument(
            '-j',
            action='store_true',
            help='simply print Freebox Server reponse in JSON format')
        self._parser.add_argument(
            '-c',
            nargs=1,
            dest='conf_path',
            default='.',
            help='path where to store/retrieve this app configuration files (default: local directory)')
        # Real freeboxOS actions
        group = self._parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            '--regapp',
            default=argparse.SUPPRESS,
            action='store_true',
            help='register this app to FreeboxOS and save result in configuration file' +
            ' (to be executed only once)')
        group.add_argument(
            '--wrstatus',
            default=argparse.SUPPRESS,
            action='store_true',
            help='get FreeboxOS current Wifi Radio status')
        group.add_argument(
            '--wron',
            default=argparse.SUPPRESS,
            action='store_true',
            help='turn FreeboxOS Wifi Radio ON')
        group.add_argument(
            '--wroff',
            default=argparse.SUPPRESS,
            action='store_true',
            help='turn FreeboxOS Wifi Radio OFF')
        group.add_argument(
            '--wpstatus',
            default=argparse.SUPPRESS,
            action='store_true',
            help='get FreeboxOS current Wifi Planning status')
        group.add_argument(
            '--wpon',
            default=argparse.SUPPRESS,
            action='store_true',
            help='turn FreeboxOS Wifi Planning ON')
        group.add_argument(
            '--wpoff',
            default=argparse.SUPPRESS,
            action='store_true',
            help='turn FreeboxOS Wifi Planning OFF')
        group.add_argument(
            '--dhcpleases',
            default=argparse.SUPPRESS,
            action='store_true',
            help='display the current DHCP leases info')
        group.add_argument(
            '--clist',
            default=argparse.SUPPRESS,
            action='store_true',
            help='display the list of received calls')
        group.add_argument(
            '--cnew',
            default=argparse.SUPPRESS,
            action='store_true',
            help='display the list of new received calls')
        group.add_argument(
            '--cread',
            default=argparse.SUPPRESS,
            action='store_true',
            help='set read status for all received calls')
        group.add_argument(
            '--reboot',
            default=argparse.SUPPRESS,
            action='store_true',
            help='reboot the Freebox Server now!')
        group.add_argument(
            '--sinfo',
            default=argparse.SUPPRESS,
            action='store_true',
            help='display the system information')
        group.add_argument(
            '--dlist',
            default=argparse.SUPPRESS,
            action='store_true',
            help='display connected drives')
        group.add_argument(
            '--dspace',
            default=argparse.SUPPRESS,
            action='store_true',
            help='display spaces (total/used/free) on connected drives')
        group.add_argument(
            '--tlist',  # 't' stands for 'téléchargement'
            default=argparse.SUPPRESS,
            action='store_true',
            help='display downloads list')

        # Configure cmd=>callback association
        self._cmd_handlers = {
            'regapp': self._ctrl.srv_auth.register_app,
            'wrstatus': self._ctrl.srv_wifi.get_wifi_radio_state,
            'wron': self._ctrl.srv_wifi.set_wifi_radio_on,
            'wroff': self._ctrl.srv_wifi.set_wifi_radio_off,
            'wpstatus': self._ctrl.srv_wifi.get_wifi_planning,
            'wpon': self._ctrl.srv_wifi.set_wifi_planning_on,
            'wpoff': self._ctrl.srv_wifi.set_wifi_planning_off,
            'dhcpleases': self._ctrl.srv_dhcp.get_dhcp_leases,
            'clist': self._ctrl.srv_call.get_all_calls_list,
            'cnew': self._ctrl.srv_call.get_new_calls_list,
            'cread': self._ctrl.srv_call.mark_calls_as_read,
            'reboot': self._ctrl.srv_system.reboot,
            'sinfo': self._ctrl.srv_system.get_system_info,
            'dlist': self._ctrl.srv_storage.get_connected_drives,
            'dspace': self._ctrl.srv_storage.get_storage_status,
            'tlist': self._ctrl.srv_download.get_downloads_list,
        }

    def parse_args(self, argv):
        """ Parse the parameters and execute the associated command """
        args = self._parser.parse_args(argv)
        argsdict = vars(args)

        # Activate verbose mode if requested
        if argsdict.get('v'):
            enable_log(True)
        del argsdict['v']

        # Activate json output if requested
        if argsdict.get('j'):
            self._ctrl.conf.resp_as_json = True
        del argsdict['j']

        # Set configuration path (local directory by default)
        conf_path = argsdict.get('conf_path')[0]
        if not os.path.isdir(conf_path):
            print('Configuration direcory does not exist: {}'.format(conf_path))
            sys.exit(1)
        self._ctrl.conf.conf_path = conf_path
        del argsdict['conf_path']

        return argsdict

    def dispatch(self, args):
        """ Call controller action """
        for cmd in args:
            # retrieve callback associated to cmd and execute it, if not found
            # display help
            return self._cmd_handlers.get(cmd, self._parser.print_help)()


if __name__ == '__main__':
        ctrl = FreeboxOSCtrl()
        cli = FreeboxOSCli(ctrl)

        args = cli.parse_args(sys.argv[1:])

        want_regapp = True if 'regapp' in args else False
        ctrl.conf.load(want_regapp)

        rc = cli.dispatch(args)

        sys.exit(rc)
