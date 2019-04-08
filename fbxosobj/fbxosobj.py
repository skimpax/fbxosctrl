#!/usr/bin/env python3

# -*- coding: utf-8 -*-
########################################################################
# Nothing expected to be modified below this line... unless bugs fix ;-)
########################################################################

import os
import sys
import json
import requests
import hmac
from zeroconf import Zeroconf
from datetime import datetime
import sqlite3

# Descriptor of this app presented to FreeboxOS server to be granted
g_app_desc = {
    "app_id": "fr.freebox.fbxosctrl",
    "app_name": "Skimpax FbxOSCtrl",
    "app_version": "2.0.0",
    "device_name": "FbxOS Client"
}


g_log_enabled = False

sql_create_tables = \
"""
CREATE TABLE `fwredir` (
  `id` int(11) PRIMARY KEY,
  `src_ip` varchar(15) NOT NULL,
  `ip_proto` varchar(10) NOT NULL,
  `wan_port_start` int(11) NOT NULL,
  `wan_port_end` int(11) NOT NULL,
  `lan_port` int(11) NOT NULL,
  `lan_ip` varchar(15) NOT NULL,
  `hostname` varchar(40) NOT NULL,
  `enabled` varchar(5) NOT NULL,
  `comment` varchar(80) NOT NULL,
  `src` varchar(40) NOT NULL,
  `UpdatedInDb` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE `calls` (
  `id` int(11) PRIMARY KEY,
  `type` varchar(11) NOT NULL,
  `datetime` datetime NOT NULL,
  `number` varchar(40) NOT NULL,
  `name` varchar(80) NOT NULL,
  `duration` int(11) NOT NULL,
  `new` tinyint(1) NOT NULL,
  `contact_id` int(11) NOT NULL,
  `src` varchar(40) NOT NULL,
  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE `static_leases` (
  `mac` varchar(17) PRIMARY KEY,
  `hostname` varchar(40) NOT NULL DEFAULT '',
  `ip` varchar(27) NOT NULL ,
  `lease_remaining` int(11) NOT NULL DEFAULT 0,
  `assign_time` datetime DEFAULT NULL DEFAULT 0,
  `refresh_time` datetime DEFAULT NULL DEFAULT 0,
  `is_static` tinyint(1) NOT NULL DEFAULT 1,
  `comment` varchar(40) NOT NULL  DEFAULT '',
  `src` varchar(40) NOT NULL,
  `UpdatedInDb` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


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
        self._resp_archive = False
        self._resp_save = False
        self._resp_restore = False
        self._conf_path = '.'
        self._db_file = 'fbxosctrl.db'

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
        if os.path.exists(self._db_file):
            return
        else:
            log('>>> create_db_file: {}'.format(self._db_file))
            queries = []
            call = FbxCall(None, None)
            queries.append(call.sql_build_table_create())
            stl = FbxDhcpStaticLease(None, None)
            queries.append(stl.sql_build_table_create())
            dyl = FbxDhcpDynamicLease(None, None)
            queries.append(dyl.sql_build_table_create())
            pfwd = FbxPortForwarding(None, None)
            queries.append(pfwd.sql_build_table_create())
            query = u'\n'.join(queries)
            
            conn = sqlite3.connect(self._db_file)
            c = conn.cursor()
            c.executescript(sql_create_tables)
            conn.commit()
            c.close()
            conn.close()


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

    def post(self, uri, data={}, timeout=None, no_login=False):
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


class FreeboxOSCtrl:
    """"""
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


class FbxObj:
    """Fbx generic object"""

    def __init__(self, ctrl, data):
        """Constructor"""
        self._ctrl = ctrl
        if ctrl is not None:
            self._http = FbxHttp(self._ctrl._conf)
        else:
            self._http = None
        self._id_name = u'id'
        self._data = data
        self._table_name = u''
        self._uri = u''
        self._src = u''
        self._cols_def = {}
        self.init()
        if data is not None:
            self._init_from_data()

    def init(self):
        """Class specific initial processing"""
        pass

    def _set_property_by_id(self, uri, id, data):

        # PUT new value
        uri = '{}{}'.format(uri, self.id)

        # PUT
        try:
            resp = self._http.put(uri, data=data, no_login=False)
        except requests.exceptions.Timeout as exc:
            raise exc

        if not resp.success:
            raise FbxException('Request failure: {}'.format(resp))

    def _init_from_data(self):
        pass

    def _get_by_id(self, uri, id):

        # GET freebox object
        uri = '{}{}'.format(uri, id)

        # GET
        try:
            resp = self._http.get(uri, no_login=False)
        except requests.exceptions.Timeout as exc:
            raise exc

        if not resp.success:
            raise FbxException('Request failure: {}\nid:{}, uri:{}'.format(resp.whole_content, id, uri))

        self._data = resp.result
        self._init_from_data()
        self._src = self._ctrl._conf.freebox_address

    def sql_build(self, replace=False):
        """Create sql INSERT or REPLACE with FbxObj properties"""
        str_replace = u'REPLACE' if replace else u'INSERT'
        field_names = []
        field_values = []
        for field in self._cols_def.keys():
            if u'c_name' in self._cols_def[field].keys():
                field_name = self._cols_def[field][u'c_name']
            else:
                field_name = field
            field_names.append(u'`{}`'.format(field))
            if field == u'src':
                field_values.append(u"'{}'".format(self._src))
            elif self._cols_def[field][u'c_type'] in [u'int(11)']:
                field_values.append(u"{}".format(getattr(self, field_name, 0)))
            elif self._cols_def[field][u'c_type'] in [u'tinyint(1)']:
                value = 1 if getattr(self, field_name) else 0
                field_values.append(u"{}".format(value))
            elif self._cols_def[field][u'c_type'] in [u'datetime']:
                value = datetime.fromtimestamp(getattr(self, field_name)).strftime('%Y-%m-%d %H:%M:%S')
                field_values.append(u"'{}'".format(value))
            else:
                field_values.append(u"'{}'".format(getattr(self, field_name, None)))
        fields = u','.join(field_names)
        values = u','.join(field_values)
        # Table name not defined here, to be done by caller
        query = "%s INTO {} (%s) " % (str_replace, fields)
        values = "VALUES ({})".format(values)
        return query+values

    def sql_build_table_create(self):
        """Create sql INSERT or REPLACE with FbxObj properties"""
        fields = {}
        for field, value in self._cols_def.items():
            value[u'c_field'] = field
            fields[str(value[u'c_order'])] = value
        lines = ["CREATE TABLE `{}` (".format(self.table_name)]
        for k in sorted(fields.keys()):
            if fields[k][u'c_field'] == self._id_name:
                lines.append(u"  `{}` {} PRIMARY KEY,".format(fields[k][u'c_field'], fields[k][u'c_type']))
            else:
                lines.append(u"  `{}` {} NOT NULL,".format(fields[k][u'c_field'], fields[k][u'c_type']))

        lines.append(u"  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP")
        lines.append(u");")

        return u'\n'.join(lines)

    def get_by_id(self, id):
        return self._get_by_id(self._uri, id)

    def _set_table_name(self, table_name):
        return

    @property
    def sql_insert(self):
        return self.sql_build()

    @property
    def id_name(self):
        return self._id_name

    @property
    def sql_replace(self):
        return self.sql_build(replace=True)

    @property
    def ctrl(self):
        return self._ctrl

    @property
    def table_name(self):
        return self._table_name

    @table_name.setter
    def table_name(self, value):
        self._set_table_name(value)
        self._table_name = value

    @property
    def uri(self):
        return self._uri

    @uri.setter
    def uri(self, value):
        self._uri = value


class FbxObjList:
    """Fbx generic object list"""

    def __init__(self, ctrl=None):
        """Constructor"""
        self._list = []
        self._o_type = None
        self._ol_type = None
        for ppty in [u'_table_name', u'_uri', u'_log']:
            setattr(self, ppty, u'')
        if ctrl is not None:
            self._ctrl = ctrl
            self._conf = ctrl._conf
            self._http = FbxHttp(self._conf)
        else:
            self._ctrl = None
            self._conf = None
            self._http = None
        self.init()

    def init(self):
        pass

    def init_list(self):
        if self._ctrl is None:
            return
        log(self._log)
        uri = self._uri
        resp = self._http.get(uri)

        if not resp.success:
            return

        fbxs = resp.result
        if fbxs is None:
            return

        for fbx in fbxs:
            ofbx = self._o_type(self._ctrl, fbx)
            self.append(ofbx)

    def __iter__(self):
        return iter(self._list)

    def append(self, ofbx):
        self._list.append(ofbx)

    def get_by_id(self, id):
        for ofbx in self._list:
            if getattr(ofbx, ofbx.id_name) == id:
                return ofbx
        return None

    def get_by_attr(self, attr, value):
        result = []
        for ofbx in self._list:
            if getattr(ofbx, attr) == value:
                result.append(ofbx)
        return result

    @property
    def table_name(self):
        return self._table_name

    @table_name.setter
    def table_name(self, value):
        self._set_table_name(value)
        self._table_name = value

    @property
    def uri(self):
        return self._uri

    @uri.setter
    def uri(self, value):
        self._uri = value


class FbxCall(FbxObj):
    """Call object"""

    def init(self):
        """Class specific initial processing"""
        self.table_name = u'calls'
        self._uri = u'/call/log/'
        self._cols_def = {'id': {u'c_order': 0, u'c_type': u'int(11)'},
                          'type': {u'c_order': 10, u'c_type': u'varchar(11)', u'c_name': u'status'},
                          'datetime': {u'c_order': 20, u'c_type': u'datetime', u'c_name': u'timestamp'},
                          'number': {u'c_order': 30, u'c_type': u'varchar(40)'},
                          'name': {u'c_order': 40, u'c_type': u'varchar(80)'},
                          'duration': {u'c_order': 50, u'c_type': u'int(11)'},
                          'new': {u'c_order': 60, u'c_type': u'tinyint(1)'},
                          'contact_id': {u'c_order': 70, u'c_type': u'int(11)'},
                          'src': {u'c_order': 80, u'c_type': u'varchar(40)'},
                          }
        self._init_from_data()
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            self._timestamp = self._data.get('datetime')
            self._duration = self._data.get('duration')
            self._number = self._data.get('number')
            self._name = self._data.get('name')
            self._id = self._data.get('id')
            self._new = self._data.get('new')
            self._status = self._data.get('type')
            self._contact_id = self._data.get('contact_id')

    def _set_new(self, value):
        data = {'new': value}
        self._set_property_by_id(self._uri, self._id, data)

    @property
    def timestamp(self):
        return self._timestamp

    @property
    def duration(self):
        return self._duration

    @property
    def number(self):
        return self._number

    @property
    def name(self):
        return self._name

    @property
    def id(self):
        return self._id

    @property
    def new(self):
        return self._new

    @new.setter
    def new(self, value):
        self._set_new(value)
        self._new = value

    @property
    def status(self):
        return self._status

    @property
    def strdate(self):
        return datetime.fromtimestamp(
                self._timestamp).strftime('%d-%m-%Y %H:%M:%S')

    @property
    def sqldate(self):
        return datetime.fromtimestamp(
                self._timestamp).strftime('%Y-%m-%d %H:%M:%S')

    @property
    def tag(self):
        return '<' if self._status == 'outgoing'\
               else '!' if self._status == 'missed' else '>'

    @property
    def naming(self):
        return self._name if self._number != self._name else ''

    @property
    def strdur(self):
        return datetime.fromtimestamp(
                self._duration).strftime('%M:%S')

    @property
    def strnew(self):
        return 'N' if self._new else 'O'

    @property
    def contact_id(self):
        return self._contact_id

    def __str__(self):
        return '{}:{} {} {} {} {} {}'.format(self.id, self.strdate,
                                             self.strnew,
                                             self.tag, self.number,
                                             self.strdur, self.naming)


class FbxCalls(FbxObjList):

    def __init__(self, ctrl):
        """ Phone call list"""
        self._ctrl = ctrl
        self._conf = ctrl._conf
        self._http = FbxHttp(self._conf)
        # init object
        FbxObjList.__init__(self, ctrl=ctrl)
        self._o_type = FbxCall
        self._ol_type = FbxCalls
        self._table_name = u'calls'
        self._uri = '/call/log/'
        self._log = ">>> get_phone_calls"
        # init object list
        FbxObjList.init_list(self)


class FbxDhcpLease(FbxObj):

    def __init__(self, ctrl, data):
        """Constructor"""
        self._id_name = u'mac'
        self._comment = u''
        self._mac = u''
        self._ip = u''
        super().__init__(ctrl, data)

    def init(self):
        """Class specific initial processing"""
        self._id_name = u'mac'

    @property
    def id_name(self):
        return self._id_name


class FbxDhcpStaticLease(FbxDhcpLease):

    def init(self):
        """Class specific initial processing"""
        self.table_name = u'static_leases'
        self._cols_def = {'id': {u'c_order': 0, u'c_type': u'varchar(17)'},
                          'mac': {u'c_order': 10, u'c_type': u'varchar(17)'},
                          'comment': {u'c_order': 20, u'c_type': u'varchar(40)'},
                          'hostname': {u'c_order': 30, u'c_type': u'varchar(40)'},
                          'ip': {u'c_order': 40, u'c_type': u'varchar(27)'},
                          'last_activity': {u'c_order': 50, u'c_type': u'datetime'},
                          'last_time_reachable': {u'c_order': 60, u'c_type': u'datetime'},
                          'src': {u'c_order': 70, u'c_type': u'varchar(40)'},
                          }
        self._init_from_data()
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        self._is_static = True
        if self._data is not None:
            self._last_activity = None
            self._last_time_reachable = None
            if self._data is not None:
                self._id = self._data.get('id')
                self._mac = self._data.get('mac')
                self._ip = self._data.get('ip')
                self._comment = self._data.get('comment')
                self._hostname = self._data.get('hostname')
                if 'host' in self._data and self._data.get('host').get('reachable'):
                    self._reachable = True
                    self._last_activity = self._data.get('host').get('last_activity')
                    self._last_time_reachable = self._data.get('host').get('last_time_reachable')
                else:
                    self._reachable = False

    def get_by_id(self, id):
        return self._get_by_id(u'/dhcp/static_lease/', id)

    def _set_comment(self, value):
        data = {'comment': value}
        self._set_property_by_id(u'/dhcp/static_lease/', self._id, data)

    @property
    def id(self):
        return self._id

    @property
    def mac(self):
        return self._mac

    @property
    def ip(self):
        return self._ip

    @property
    def hostname(self):
        return self._hostname

    @property
    def comment(self):
        return self._comment

    @comment.setter
    def comment(self, value):
        self._set_comment(value)
        self._comment = value

    @property
    def reachable(self):
        return self._reachable

    @property
    def last_activity(self):
        return self._last_activity

    @property
    def str_last_activity(self):
        if self._last_activity is None:
            return ''
        return datetime.fromtimestamp(
                self._last_activity).strftime('%d-%m-%Y %H:%M:%S')

    @property
    def last_time_reachable(self):
        return self._last_time_reachable

    @property
    def str_last_time_reachable(self):
        if self._last_time_reachable is None:
            return ''
        return datetime.fromtimestamp(
                self._last_time_reachable).strftime('%d-%m-%Y %H:%M:%S')

    @property
    def is_static(self):
        return True

    def __str__(self):
        data = 'id: {}, mac: {}, ip: {}, hostname: {}\n       reachable: {}, comment: {}'
        data += '\n       last_activity: {}, last_time_reachable: {}'
        data = data.format(self.id, self.mac, self.ip, self.hostname,
                           self.reachable, self.comment, self.str_last_activity,
                           self.str_last_time_reachable)
        return data


class FbxDhcpStaticLeases(FbxObjList):

    def __init__(self, ctrl):
        """ List the DHCP leases on going"""
        self._ctrl = ctrl
        self._conf = ctrl._conf
        self._http = FbxHttp(self._conf)
        FbxObjList.__init__(self)

    def init(self):
        """ List the DHCP leases on going"""

        log(">>> get_static_leases")
        uri = '/dhcp/static_lease/'
        resp = self._http.get(uri)

        if not resp.success:
            return

        leases = resp.result
        if leases is None:
            return

        for lease in leases:
            olease = FbxDhcpStaticLease(self._ctrl, lease)
            self.append(olease)


class FbxDhcpDynamicLease(FbxDhcpLease):

    def __init__(self, ctrl, data, static_leases=None):
        self._static_leases = static_leases
        self._data = data
        if ctrl is None:
            self._conf = None
            self._http = None
        else:
            self._conf = ctrl.conf
            self._http = FbxHttp(self._conf)
        FbxDhcpLease.__init__(self, ctrl, data)

    def init(self):
        """Class specific initial processing"""
        self.table_name = u'dynamic_leases'
        self._id_name = u'mac'
        self._cols_def = {'mac': {u'c_order': 0, u'c_type': u'varchar(17)'},
                          'hostname': {u'c_order': 10, u'c_type': u'varchar(40)'},
                          'ip': {u'c_order': 20, u'c_type': u'varchar(27)'},
                          'lease_remaining': {u'c_order': 30, u'c_type': u'int(11)'},
                          'assign_time': {u'c_order': 40, u'c_type': u'datetime'},
                          'refresh_time': {u'c_order': 50, u'c_type': u'datetime'},
                          'is_static': {u'c_order': 60, u'c_type': u'tinyint(1)'},
                          'comment': {u'c_order': 70, u'c_type': u'varchar(40)'},
                          'src': {u'c_order': 80, u'c_type': u'varchar(40)'},
                          }
        # self._init_from_data()
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            sys.stdout.flush()
            self._id = self._data.get(self._id_name)
            self._mac = self._data.get('mac')
            self._hostname = self._data.get('hostname')
            self._ip = self._data.get('ip')
            self._lease_remaining = self._data.get('lease_remaining')
            self._assign_time = self._data.get('assign_time')
            self._refresh_time = self._data.get('refresh_time')
            self._is_static = self._data.get('is_static')
            if 'host' in self._data and self._data.get('host').get('reachable'):
                self._reachable = True
                self._last_activity = self._data.get('host').get('last_activity')
                self._last_time_reachable = self._data.get('host').get('last_time_reachable')
            else:
                self._reachable = False
                self._last_activity = None
                self._last_time_reachable = None
            if self._is_static:
                staticLease = self._static_leases.get_by_id(self._id)
                # staticLease = FbxDhcpStaticLease(self.ctrl, None)
                # staticLease._get_by_id(u'/dhcp/static_lease/', self._id)
                self._comment = staticLease.comment
                self._last_activity = staticLease.last_activity
                self._last_time_reachable = staticLease.last_time_reachable

    def get_by_id(self, id):
        return self._get_by_id(u'/dhcp/dynamic_lease/', id)

    @property
    def id(self):
        return self._id

    @property
    def mac(self):
        return self._mac

    @property
    def ip(self):
        return self._ip

    @property
    def hostname(self):
        return self._hostname

    @property
    def comment(self):
        return self._comment

    @property
    def assign_time(self):
        return self._assign_time

    @property
    def str_assign_time(self):
        return datetime.fromtimestamp(
                self._assign_time).strftime('%d-%m-%Y %H:%M:%S')

    @property
    def refresh_time(self):
        return self._refresh_time

    @property
    def str_refresh_time(self):
        return datetime.fromtimestamp(
                self._refresh_time).strftime('%d-%m-%Y %H:%M:%S')

    @property
    def is_static(self):
        return self._is_static

    @property
    def last_activity(self):
        return self._last_activity

    @property
    def str_last_activity(self):
        if (self._last_activity is None) or (self._last_activity == 0.0):
            return u''
        return datetime.fromtimestamp(
                self._last_activity).strftime('%d-%m-%Y %H:%M:%S')

    @property
    def last_time_reachable(self):
        return self._last_time_reachable

    @property
    def str_last_time_reachable(self):
        if (self._last_time_reachable is None) or (self._last_time_reachable == 0.0):
            return u''
        return datetime.fromtimestamp(
                self._last_time_reachable).strftime('%d-%m-%Y %H:%M:%S')

    @property
    def reachable(self):
        return self._reachable

    @property
    def static_leases(self):
        return self._static_leases

    def __str__(self):
        data = 'id: {}, mac: {}, ip: {}, hostname: {}\n       is_static: {}, reachable: {}, comment: {}'
        data += '\n       last_activity: {}, last_time_reachable: {}'
        data = data.format(self.id, self.mac, self.ip, self.hostname,
                           self.is_static, self.reachable, self.comment,
                           self.str_last_activity,
                           self.str_last_time_reachable
                           )
        return data


class FbxDhcpDynamicLeases(FbxObjList):

    def __init__(self, ctrl):
        """ List the DHCP leases on going"""
        self._ctrl = ctrl
        self._conf = ctrl._conf
        self._http = FbxHttp(self._conf)
        self._static_leases = None
        FbxObjList.__init__(self)
        self._o_type = FbxDhcpDynamicLease
        self._ol_type = FbxDhcpDynamicLeases
        self._table_name = u'fwredir'
        self._uri = '/dhcp/dynamic_lease/'
        self._log = ">>> get_static_leases"
        # init object
        FbxObjList.__init__(self, ctrl=ctrl)
        # init object list
        def process_row(olease):
            if self._static_leases is None:
                self._static_leases = olease._static_leases
        FbxObjList.init_list(self, process_row)

    def init_save(self):
        """ List the DHCP leases on going"""

        log(">>> get_static_leases")
        uri = '/dhcp/dynamic_lease/'
        resp = self._http.get(uri)

        if not resp.success:
            return

        leases = resp.result
        if leases is None:
            return

        for lease in leases:
            olease = FbxDhcpDynamicLease(self._ctrl, lease, static_leases=self._static_leases)
            self.append(olease)
            if self._static_leases is None:
                self._static_leases = olease._static_leases

    @property
    def static_leases(self):
        return self._static_leases


class FbxPortForwarding(FbxObj):
    """Port Forwarding object"""

    def init(self):
        """Class specific initial processing"""
        self.table_name = u'fwredir'
        self._cols_def = {'id': {u'c_order': 0, u'c_type': u'int(11)'},
                          'src_ip': {u'c_order': 10, u'c_type': u'varchar(15)'},
                          'ip_proto': {u'c_order': 20, u'c_type': u'varchar(10)'},
                          'wan_port_start': {u'c_order': 30, u'c_type': u'int(11)'},
                          'wan_port_end': {u'c_order': 40, u'c_type': u'int(11)'},
                          'lan_port': {u'c_order': 50, u'c_type': u'int(11)'},
                          'lan_ip': {u'c_order': 60, u'c_type': u'varchar(15)'},
                          'hostname': {u'c_order': 70, u'c_type': u'varchar(40)'},
                          'enabled': {u'c_order': 80, u'c_type': u'tinyint(1)'},
                          'comment': {u'c_order': 90, u'c_type': u'varchar(80)'},
                          'src': {u'c_order': 99, u'c_type': u'varchar(40)'},
                          }
        self._init_from_data()
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            self._id = self._data.get('id')
            self._src_ip = self._data.get('src_ip')
            self._ip_proto = self._data.get('ip_proto')
            self._wan_port_start = self._data.get('wan_port_start')
            self._wan_port_end = self._data.get('wan_port_end')
            self._lan_port = self._data.get('lan_port')
            self._lan_ip = self._data.get('lan_ip')
            self._hostname = self._data.get('hostname')
            self._enabled = self._data.get('enabled')
            self._comment = self._data.get('comment')

    @property
    def sql_insert(self):
        return self.sql_build()

    @property
    def sql_replace(self):
        return self.sql_build(replace=True)

    def _set_property(self, ppty, name, value):

        if ppty == value:
            return

        # PUT new value
        uri = '/fw/redir/{}'.format(self.id)
        if name in [u'wan_port_start', u'lan_port']:
            data = {u'wan_port_start': value, u'lan_port': value}
        else:
            data = {name: value}

        # PUT
        try:
            resp = self._ctrl._http.put(uri, data=data, no_login=False)
        except requests.exceptions.Timeout as exc:
            raise exc

        if not resp.success:
            raise FbxException('Request failure: {}'.format(resp))

        ppty = value

    def get_by_id(self, id):
        return self._get_by_id(u'/fw/redir/', id)

    def __str__(self):

        data = '  #{}: enabled: {}, hostname: {}, comment: {},\n'
        data += '       lan_port: {}, wan_port_start: {}, wan_port_end: {}\n'
        data += '       src_ip: {}, lan_ip: {}, ip_proto: {}'
        return data.format(self.id, self.enabled, self.hostname,
                           self.comment, self.lan_port, self.wan_port_start,
                           self.wan_port_end, self.src_ip,
                           self.lan_ip, self.ip_proto)

    @property
    def id(self):
        return self._id

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._set_property(self._enabled, u'enabled', value)

    @property
    def ip_proto(self):
        return self._ip_proto

    @property
    def wan_port_start(self):
        return self._wan_port_start

    @wan_port_start.setter
    def wan_port_start(self, value):
        self._set_property(self._wan_port_start, u'wan_port_start', value)

    @property
    def wan_port_end(self):
        return self._wan_port_end

    @wan_port_end.setter
    def wan_port_end(self, value):
        self._set_property(self._wan_port_end, u'wan_port_end', value)

    @property
    def lan_ip(self):
        return self._lan_ip

    @lan_ip.setter
    def lan_ip(self, value):
        self._set_property(self._lan_ip, u'lan_ip', value)

    @property
    def lan_port(self):
        return self._lan_port

    @lan_port.setter
    def lan_port(self, value):
        self._set_property(self._lan_port, u'lan_port', value)

    @property
    def hostname(self):
        return self._hostname

    @property
    def src_ip(self):
        return self._src_ip

    @src_ip.setter
    def src_ip(self, value):
        self._set_property(self._src_ip, u'src_ip', value)

    @property
    def comment(self):
        return self._comment

    @comment.setter
    def comment(self, value):
        self._set_property(self._comment, u'comment', value)


class FbxPortForwardings(FbxObjList):

    def __init__(self, ctrl):
        """ List the DHCP leases on going"""
        self._ctrl = ctrl
        self._conf = ctrl._conf
        self._http = FbxHttp(self._conf)
        FbxObjList.__init__(self)
        self._o_type = FbxPortForwarding
        self._ol_type = FbxPortForwardings
        self._table_name = u'fwredir'
        self._uri = '/fw/redir/'
        self._log = ">>> get_firewall_redirections"
        # init object
        FbxObjList.__init__(self, ctrl=ctrl)
        # init object list
        FbxObjList.init_list(self)


def main():
        ctrl = FreeboxOSCtrl()
        ctrl.conf.conf_path = u'/home/alain/scripts/fbxosctrl/'
        ctrl.conf.load(False)

        if False:
            calls = FbxCalls(ctrl)
            for call in calls:
                print(call)

        if False:
            call = FbxCall(ctrl, None)
            print(call.sql_build_table_create())
            call.get_by_id(u'4300')
            print(call)
            call.new = False
            call.get_by_id(u'4300')
            print(call)
            call.new = True
            call.get_by_id(u'4300')
            print(call)
            print(call.sql_replace)

        if False:
            staticLease = FbxDhcpStaticLease(ctrl, None)
            print(staticLease.sql_build_table_create())
            staticLease.get_by_id(u'B8:27:EB:0B:85:4F')
            print(staticLease)
            staticLease.comment = u'alain-pi3-ub Domoticz...'
            print(staticLease)
            staticLease.comment = u'alain-pi3-ub Domoticz'
            print(staticLease)
            print(staticLease.sql_replace)

        if False:
            st_leases = FbxDhcpStaticLeases(ctrl)
            for lease in st_leases:
                print(u'\nstatic lease:\n', lease)

        if False:
            dyn_leases = FbxDhcpDynamicLeases(ctrl)
            for lease in dyn_leases:
                print(u'\ndynamic lease:\n', lease)

        pfwd = FbxPortForwarding(ctrl, None)
        print(pfwd.sql_build_table_create())
        pfwd.get_by_id(u'10')
        print(pfwd)
        print(pfwd.sql_replace)

        pfwds = FbxPortForwardings(ctrl)
        for pfwd in pfwds:
            print(pfwd)

        if False:
            # GET dhcp leases
            uri = '/dhcp/dynamic_lease/'
            resp = staticLease._http.get(uri)

            if not resp.success:
                raise FbxException('Request failure: {}'.format(resp))

            leases = resp.result
            if leases is None:
                print('No DHCP leases')
                return 0

            dynLeases = FbxObjList()
            static_leases = None
            for lease in leases:
                oDynamicLease = FbxDhcpDynamicLease(ctrl, lease, static_leases=static_leases)
                dynLeases.append(oDynamicLease)
                if static_leases is None:
                    static_leases = oDynamicLease.static_leases
                # oDynamicLease._init_from_data()

                print(u'\n\ndynamic lease:\n', oDynamicLease)
                odl = dynLeases.get_by_id(oDynamicLease.mac)
                print(u'\n\nBy id:\n', odl)
                for odl in dynLeases.get_by_attr(u'ip', oDynamicLease.ip):
                    print(u'\n\nBy ip:\n', odl)

                print(u'\n\n', odl.sql_replace)
                # break
            print(oDynamicLease.sql_build_table_create())


if __name__ == '__main__':
    main()
    sys.exit(0)
