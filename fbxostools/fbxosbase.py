#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import requests
import hmac
from zeroconf import Zeroconf
from time import sleep

FBXOSCTRL_VERSION = "2.4.3"

__author__ = "Christophe Lherieau (aka skimpax)"
__copyright__ = "Copyright 2019, Christophe Lherieau"
__credits__ = []
__license__ = "GPL"
__version__ = FBXOSCTRL_VERSION
__maintainer__ = "skimpax"
__email__ = "skimpax@gmail.com"
__status__ = "Production"


g_log_enabled = False
g_test_conf_path = u'/home/alain/scripts/fbxosctrl/'

########################################################################
# Nothing expected to be modified below this line... unless bugs fix ;-)
########################################################################


def log(what):
    """Logger function"""
    global g_log_enabled
    if g_log_enabled:
        print(what)


def enable_log(is_enabled):
    """Update log state"""
    global g_log_enabled
    g_log_enabled = is_enabled


def fbx_question_yn(question):
    result = False
    answer = None
    while answer not in ("y", "n", "Y", "N", "o", "O"):
        answer = input(u"{} Y/N): ".format(question))
        if answer in ("y", "Y", "o", "O"):
            result = True
        elif answer in ("n", "N"):
            result = False
    return result


class FbxException(Exception):
    """ Exception for FreeboxOS domain """

    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason


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
        self._resp_archive = False
        self._resp_save = False
        self._resp_restore = False
        self._conf_path = '.'
        self._db_file = 'fbxosctrl.db'
        self._db = None

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
    def db_file(self):
        return self._db_file

    @db_file.setter
    def db_file(self, db_file):
        self._db_file = db_file

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
    def resp_archive(self):
        return self._resp_archive

    @resp_archive.setter
    def resp_archive(self, resp_archive):
        self._resp_archive = resp_archive

    @property
    def resp_save(self):
        return self._resp_save

    @resp_save.setter
    def resp_save(self, resp_save):
        self._resp_save = resp_save

    @property
    def resp_restore(self):
        return self._resp_restore

    @resp_restore.setter
    def resp_restore(self, resp_restore):
        self._resp_restore = resp_restore

    @property
    def conf_path(self):
        return self._conf_path

    @property
    def db(self):
        return self._db

    @conf_path.setter
    def conf_path(self, conf_path):
        log('>>> conf_path: {}'.format(conf_path))
        if conf_path.endswith('/'):
            conf_path = conf_path[:-1]
        self._conf_path = conf_path
        self._addr_file = self._conf_path + '/' + self._addr_file
        self._reg_file = self._conf_path + '/' + self._reg_file
        self._db_file = self._conf_path + '/' + self._db_file

    def load(self, want_regapp):
        """Load configuration params"""
        log('>>> load')
        try:
            from fbxosdb import FbxDbLite
        except:
            from fbxostools.fbxosdb import FbxDbLite
        self._db = FbxDbLite(self._db_file)
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
            self._create_db_file()

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
        info = {}
        try:
            r = Zeroconf()
            serv_info = r.get_service_info('_fbx-api._tcp.local.', 'Freebox Server._fbx-api._tcp.local.')
            info['api_domain'] = serv_info.properties[b'api_domain'].decode()
            info['https_available'] = True if serv_info.properties[b'https_available'] == b'1' else False
            info['https_port'] = int(serv_info.properties[b'https_port'])
            info['api_base_url'] = serv_info.properties[b'api_base_url'].decode()
            info['api_version'] = serv_info.properties[b'api_version'].decode()
            r.close()
        except Exception:
            print('Unable to retrieve configuration, assuming bridged mode')
            d = requests.get("http://mafreebox.freebox.fr/api_version")
            data = d.json()
            info['api_domain'] = data['api_domain']
            info['https_available'] = data['https_available']
            info['https_port'] = data['https_port']
            info['api_base_url'] = data['api_base_url']
            info['api_version'] = data['api_version']
        return info

    def _save_registration_params(self):
        """ Save registration parameters (app_id/token) to a local file """
        log('>>> save_registration_params')
        with open(self._reg_file, 'w') as of:
            json.dump(self._reg_params, of, indent=True, sort_keys=True)

    def _load_addressing_params(self):
        """Load existing addressing params or get them via mDNS"""
        if os.path.exists(self._addr_file):
            with open(self._addr_file) as infile:
                self._addr_params = json.load(infile)

        elif self._addr_params is None:
            mdns_info = self._fetch_fbx_mdns_info_via_mdns()
            log('Freebox mDNS info: {}'.format(mdns_info))
            self._addr_params = {}
            self._addr_params['protocol'] = 'https' if mdns_info['https_available'] else 'http'
            self._addr_params['api_domain'] = mdns_info['api_domain']
            self._addr_params['port'] = mdns_info['https_port']
            self._addr_params['api_base_url'] = mdns_info['api_base_url']
            self._addr_params['api_version'] = mdns_info['api_version']
            with open(self._addr_file, 'w') as of:
                json.dump(self._addr_params, of, indent=True, sort_keys=True)

    def _load_registration_params(self):
        log('>>> load_registration_params: file: {}'.format(self._reg_file))
        if os.path.exists(self._reg_file):
            with open(self._reg_file) as infile:
                self._reg_params = json.load(infile)

    def _create_db_file(self):
        # if os.path.exists(self._db_file):
            # return
        # else:
        log('>>> create_db_file: {}'.format(self._db_file))
        try:
            from fbxostools.fbxosdb import FbxDbTable
            from fbxostools.fbxosobj import table_defs
        except ImportError:
            from fbxosdb import FbxDbTable
            from fbxosobj import table_defs

        # Add tables

        for tbl in table_defs.keys():
            t_tbl = FbxDbTable(tbl, u'id', table_defs[tbl][u'cols_def'])
            self._db.add_table(t_tbl)

        self._db.init_base()


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

    def get_do(self, uri, timeout=None, no_login=False):
        """GET request"""
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
        return r

    def get(self, uri, timeout=None, no_login=False):
        """GET request"""
        log(">>> get")
        try_cpt = 0

        while try_cpt < 5:
            try_cpt += 1
            r = self.get_do(uri, timeout=timeout, no_login=no_login)

            # ensure status_code is 200, else raise exception
            if requests.codes.ok != r.status_code:
                if r.status_code == 403:
                    self._logout()
                    sleep(15)
                    self.__init__(self._conf)
                    self._login()
                    print(u'self._session_token', self._session_token)
                    print('err 403, retry')
                    continue
                raise FbxException('POST error - http_status: {} {}'.format(r.status_code, r.text))
            else:
                break

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

    def post_do(self, uri, data={}, timeout=None, no_login=False):
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
        return r

    def post(self, uri, data={}, timeout=None, no_login=False):
        """POST request"""
        log(">>> post")
        try_cpt = 0

        while try_cpt < 5:
            try_cpt += 1
            r = self.post_do(uri, data=data, timeout=timeout, no_login=no_login)
            log('POST response: {}'.format(r.text))

            if requests.codes.ok != r.status_code:
                if r.status_code == 403:
                    self._logout()
                    sleep(15)
                    self.__init__(self._conf)
                    self._login()
                    print(u'self._challenge', self._challenge)
                    print(u'self._session_token', self._session_token)
                    print('err 403, retry')
                    continue
                raise FbxException('POST error - http_status: {} {}'.format(r.status_code, r.text))
            else:
                break

        # ensure status_code is 200, else raise exception
        if requests.codes.ok != r.status_code:
            raise FbxException('POST error - http_status: {} {}'.format(r.status_code, r.text))

        return FbxResponse.build(r.text)

    def delete(self, uri, data={}, timeout=None, no_login=False):
        """POST request"""
        log(">>> delete")
        if not no_login:
            self._login()

        url = self._conf.api_address(uri)
        jdata = json.dumps(data)
        log('DELETE url: {} data: {}'.format(url, jdata))
        print('DELETE url: {} data: {}'.format(url, jdata))

        r = requests.delete(
            url,
            verify=self._certificates_file,
            data=jdata,
            headers=self.headers,
            timeout=timeout if timeout is not None else self._http_timeout)
        log('DELETE response: {}'.format(r.text))

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
            # resp = self._http.post(url, headers=self.headers)
            resp = self.post(url, headers=self.headers)

            # reset headers as no more dialogs expected
            # self._http_headers = None

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


class FreeboxOSCtrlBase:
    """ Base class """
    def __init__(self):
        """Constructor"""
        self._conf = FbxConfiguration(g_app_desc)
        self._http = FbxHttp(self._conf)
        # self._srv_auth = FbxServiceAuth(self._http, self._conf)
        # self._srv_system = FbxServiceSystem(self._http, self._conf)
        # self._srv_connection = FbxServiceConnection(self._http, self._conf)
        # self._srv_storage = FbxServiceStorage(self._http, self._conf)
        # self._srv_download = FbxServiceDownload(self._http, self._conf)
        # self._srv_wifi = FbxServiceWifi(self._http, self._conf)
        # self._srv_dhcp = FbxServiceDhcp(self._http, self._conf)
        # self._srv_call = FbxServiceCall(self._http, self._conf)
        # self._srv_pfw = FbxServicePortForwarding(self._http, self._conf)

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
    def srv_connection(self):
        return self._srv_connection

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

    @property
    def srv_port(self):
        return self._srv_pfw


def main():

    from fbxosobj import FbxCalls, FbxCall
    from fbxosobj import FbxContacts, FbxContact
    from fbxosobj import FbxGroups, FbxGroup
    from fbxosobj import FbxDhcpStaticLeases, FbxDhcpStaticLease
    from fbxosobj import FbxDhcpStaticLeasesX, FbxDhcpDynamicLeasesX
    from fbxosobj import FbxDhcpDynamicLeases, FbxDhcpDynamicLease
    from fbxosobj import FbxPortForwardings, FbxPortForwarding
    from fbxosobj import table_defs
    from fbxosdb import FbxDbTable

    ctrl = FreeboxOSCtrlBase()
    ctrl.conf.conf_path = g_test_conf_path
    ctrl.conf.load(False)
    # ctrl.conf.db_file = u'/home/alain/scripts/dev/fbxosctrl/test.db'
    print(ctrl.conf.db_file)

    def test_FbxCall():
        # FbxCall
        calls = FbxCalls(ctrl)
        print(u'\nCalls from freebox:')
        for call in calls:
            pass
            print(call)
        print(u'\nSave calls into database:')
        calls.save_to_db()

        calls = FbxCalls(ctrl, empty=True)
        t_calls = FbxDbTable(u'call_log', u'id', table_defs[u'call_log'][u'cols_def'])
        calls.load_from_db(ctrl, FbxCall, t_calls)
        print(u'\nCalls from database:')
        for call in calls:
            pass
            print(call)

        print(u'\nCalls update test:')

        for call in calls:
            if call.new:
                break
        call.new = False
        c_id = call.id
        print(call)
        call_new = calls.get_by_id(c_id)
        print(call_new, call_new.new)
        try:
            assert call_new.new is False, u'Update call failed'
        except AssertionError:
            print(u'AssertionError: Update call failed')
        call_new.new = True
        call_new = calls.get_by_id(c_id)
        print(call_new, call_new.new)
        try:
            assert call_new.new is True, u'Update call failed'
        except AssertionError:
            print(u'AssertionError: Update call failed')

    def test_FbxDhcpStaticLease():
        # FbxDhcpStaticLease

        static_leases = FbxDhcpStaticLeases(ctrl)
        print(u'\nStatic leases from freebox:')
        for static_lease in static_leases:
            pass
            print(static_lease)
        print(u'\nSave static leases into database:')
        static_leases.save_to_db()

        static_leases = FbxDhcpStaticLeases(ctrl, empty=True)
        t_static_leases = FbxDbTable(u'static_lease', u'mac', table_defs[u'static_lease'][u'cols_def'])
        static_leases.load_from_db(ctrl, FbxDhcpStaticLease, t_static_leases)
        print(u'\nStatic leases from database:')
        for static_lease in static_leases:
            pass
            print(static_lease)

        # FbxDhcpStaticLease (extended)

        dynamic_leases = FbxDhcpDynamicLeases(ctrl)
        static_leasesx = FbxDhcpStaticLeasesX(ctrl, dynamic_leases)
        print(u'\nStatic leases from freebox (extended):')
        for static_lease in static_leasesx:
            pass
            print(static_lease)

    def test_FbxPortForwarding():
        # FbxPortForwarding

        port_forwardings = FbxPortForwardings(ctrl)
        print(u'\nPort forwardings from freebox:')
        for port_forwarding in port_forwardings:
            print(port_forwarding)
        print(u'\nSave port forwardings into database:')
        port_forwardings.save_to_db()

        port_forwardings = FbxPortForwardings(ctrl, empty=True)
        t_port_forwardings = FbxDbTable(u'fw_redir', u'id', table_defs[u'fw_redir'][u'cols_def'])
        port_forwardings.load_from_db(ctrl, FbxPortForwarding, t_port_forwardings)
        print(u'\nPort forwardings from database:')
        for port_forwarding in port_forwardings:
            pass
            print(port_forwarding)

        print(u'\nPortforwarding update test:')

        #
        # Todo : create a port forwarding for test
        # {u"id":33,
        # u"src_ip": "0.0.0.0",
        # u"ip_proto": "tcp",
        # u"wan_port_start": 993,
        # u"wan_port_end": 1001,
        # u"lan_port": 993,
        # "lan_ip": "192.168.0.61",
        # "hostname": "domoticz",
        # "enabled": false,
        # "comment": "Test1"
        # }
        #

        for port_forwarding in port_forwardings:
            if port_forwarding.comment[0:5] == u'Test1':
                print(port_forwarding)
                break
        print(port_forwarding)
        comment = port_forwarding.comment
        comment_new = comment+u'.'
        p_id = port_forwarding.id
        port_forwarding.comment = comment_new
        print(port_forwarding, u'\n', port_forwarding.comment)
        port_forwarding_new = port_forwardings.get_by_id(p_id)
        print(port_forwarding_new, u'\n', port_forwarding_new.comment)
        try:
            assert port_forwarding_new.comment == comment_new, u'Update call failed'
        except AssertionError:
            print(u'AssertionError: Update call failed')
        port_forwarding.comment = u'Test1'

    def test_FbxDhcpDynamicLease():
        # FbxDhcpDynamicLease

        dynamic_leases = FbxDhcpDynamicLeases(ctrl)
        static_leases = FbxDhcpStaticLeases(ctrl)
        print(u'\nDynamic leases from freebox:')
        for dynamic_lease in dynamic_leases:
            print(dynamic_lease)
        print(u'\nSave dynamic leases into database:')
        dynamic_leases.save_to_db()

        dynamic_leases = FbxDhcpDynamicLeases(ctrl, empty=True)
        t_dynamic_leases = FbxDbTable(u'dynamic_lease', u'mac', table_defs[u'dynamic_lease'][u'cols_def'])
        dynamic_leases.load_from_db(ctrl, FbxDhcpDynamicLease, t_dynamic_leases)
        print(u'\nDynamic leases from database:')
        for dynamic_lease in dynamic_leases:
            pass
            print(dynamic_lease)

        print(u'\nDynamic leases from freebox (extended):')
        dynamic_leasesx = FbxDhcpDynamicLeasesX(ctrl, static_leases)
        for dynamic_lease in dynamic_leasesx:
            print(dynamic_lease)

    def test_FbxGroup():
        # FbxGroup

        print(u'\nGroups from freebox:')
        groups = FbxGroups(ctrl)
        for group in groups:
            pass
            print(group)
        print(u'\nCreate group Test:')
        groups.group_add('Test')
        print(u'\nDelete group Test:')
        for group in groups:
            if group.name == u'Test':
                if groups.group_delete(group.id, group.name):
                    print(u'{} deleted'.format(group))
                else:
                    print(u'{} not deleted'.format(group))
        print(u'\nSave groups into database:')
        groups.save_to_db()

        groups = FbxGroups(ctrl, empty=True)
        t_groups = FbxDbTable(u'group', u'id', table_defs[u'group'][u'cols_def'])
        groups.load_from_db(ctrl, FbxGroup, t_groups)
        print(u'\nGroups from database:')
        for group in groups:
            pass
            print(group)

    def test_FbxContact():
        FbxContact

        print(u'\nContacts from freebox:')
        contacts = FbxContacts(ctrl)
        for contact in contacts:
            print(contact)
            if u'Hôtel' in contact.display_name:
                to_add = True
                for group in contact.groups:
                    if group.group_id == 134:
                        to_add = False
                if to_add:
                    contact.add_to_group(134)

        print(u'groups:\n{}'.format(contacts.groups))

        print(u'\nSave contacts into database:')
        contacts.save_to_db()

        contacts = FbxContacts(ctrl, empty=True)
        t_contacts = FbxDbTable(u'contact', u'id', table_defs[u'contact'][u'cols_def'])
        contacts.load_from_db(ctrl, FbxContact, t_contacts)
        print(u'\nContacts from database:')
        for contact in contacts:
            print(contact)

    # test_FbxCall()
    # test_FbxDhcpStaticLease()
    # test_FbxDhcpDynamicLease()
    # test_FbxPortForwarding()
    # test_FbxGroup()
    test_FbxContact()

    print(u'Seems to be ok')

    return 0


if __name__ == '__main__':

    sys.exit(main())
