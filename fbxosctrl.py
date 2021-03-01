#!/usr/bin/env python3

# -*- coding: utf-8 -*-
########################################################################
# Nothing expected to be modified below this line... unless bugs fix ;-)
########################################################################

import argparse
import os
import sys
import requests
from datetime import timedelta

from fbxostools.fbxosbase import FbxConfiguration, FbxHttp
from fbxostools.fbxosbase import log, enable_log, fbx_question_yn
# from fbxostools.fbxosbase import FreeboxOSCtrlBase
from fbxostools.fbxosbase import FbxException
from fbxostools.fbxosobj import table_defs
from fbxostools.fbxosobj import FbxCall, FbxCalls
from fbxostools.fbxosobj import FbxContact, FbxContacts
from fbxostools.fbxosobj import FbxPortForwarding, FbxPortForwardings
from fbxostools.fbxosobj import FbxDhcpStaticLeasesX, FbxDhcpDynamicLeasesX
from fbxostools.fbxosobj import FbxDhcpDynamicLease, FbxDhcpStaticLease
from fbxostools.fbxosobj import FbxDhcpDynamicLeases, FbxDhcpStaticLeases
from fbxostools.fbxosdb import FbxDbTable

FBXOSCTRL_VERSION = "2.4.5"

__author__ = "Christophe Lherieau (aka skimpax)"
__copyright__ = "Copyright 2019, Christophe Lherieau"
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


class FbxService:
    """"Service base class"""

    def __init__(self, http, conf, ctrl=None):
        """Constructor"""
        self._ctrl = ctrl
        self._http = http
        self._conf = conf
        self._cols_def = {}
        self._db_table_name = u''
        self.init()

    def init(self):
        pass


class FbxServiceAuth(FbxService):
    """"Authentication domain"""

    def __init__(self, http, conf):
        """Constructor"""
        super().__init__(http, conf)
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


class FbxServiceSystem(FbxService):
    """System domain"""

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
        print(' - Model:     {}'.format(resp.result['model_info']['pretty_name']))
        print(' - MAC:       {}'.format(resp.result['mac']))
        print(' - Firmware:  {}'.format(resp.result['firmware_version']))
        print(' - Uptime:    {}'.format(resp.result['uptime']))
        print(' - Sensors:')
        for sensor in resp.result['sensors']:
            unit = '°C' if sensor['id'].startswith('temp_') else ''
            print('   - {:20} {}{}'.format(sensor['name'] + ':', sensor['value'], unit))
        return True


class FbxServiceConnection(FbxService):
    """Connection domain"""

    @staticmethod
    def rate_to_human_readable(bps):
        """Convert bits per seconds to human readable format"""
        if bps > 1000000:
            return '{:.2f} Mb/s ({:.1f} MB/s)'.format(bps/1000000, bps/1000000/8)
        elif bps > 1000:
            return '{:.1f} Kb/s ({:.1f} KB/s)'.format(bps/1000, bps/1000/8)
        elif bps:
            return '{} b/s ({} B/s)'.format(bps, bps/8)

    def get_line_ethernet_info(self):
        uri = '/connection'
        resp = self._http.get(uri)

        if self._conf.resp_as_json:
            return resp.whole_content

        print('Ethernet info:')
        print(' - Info:')
        print('   - IPv4:   {}'.format(resp.result['ipv4']))
        print('   - IPv6:   {}'.format(resp.result['ipv6']))
        print('   - Media:  {}'.format(resp.result['media']))
        print('   - State:  {}'.format(resp.result['state']))
        print(' - Down:')
        print(
            '   - Bandwidth:     {}'
            .format(FbxServiceConnection.rate_to_human_readable(resp.result['bandwidth_down'])))
        print(
            '   - Current rate:  {}'
            .format(FbxServiceConnection.rate_to_human_readable(resp.result['rate_down'])))
        print(' - Up:')
        print(
            '   - Bandwidth:     {}'
            .format(FbxServiceConnection.rate_to_human_readable(resp.result['bandwidth_up'])))
        print(
            '   - Current rate:  {}'
            .format(FbxServiceConnection.rate_to_human_readable(resp.result['rate_up'])))
        return True

    def get_line_media_info(self):
        """Retieve xDSL or FTTH info"""
        uri = '/connection'
        resp = self._http.get(uri)

        if resp.result['media'] == 'ftth':
            return self._get_ftth_info()
        else:
            return self._get_xdsl_info()

    def _get_xdsl_info(self):
        """Retrieve the xDSL info"""
        uri = '/connection/xdsl'
        resp = self._http.get(uri)

        if self._conf.resp_as_json:
            return resp.whole_content

        print('xDSL info:')
        print(' - Status:')
        for k, v in resp.result['status'].items():
            print('   - {:13} {}'.format(k+':', v))
        down = resp.result['down']
        print(' - Down:')
        print(
            '   - Max Rate:     {}'
            .format(FbxServiceConnection.rate_to_human_readable(down['rate']*1000)))
        print('   - Attenuation:  {} dB'.format(down['attn_10']/10))
        print('   - Noise magin:  {} dB'.format(down['snr_10']/10))
        up = resp.result['up']
        print(' - Up:')
        print(
            '   - Max Rate:     {}'
            .format(FbxServiceConnection.rate_to_human_readable(up['rate']*1000)))
        print('   - Attenuation:  {} dB'.format(up['attn_10']/10))
        print('   - Noise magin:  {} dB'.format(up['snr_10']/10))
        return True

    def _get_ftth_info(self):
        """Retrieve the FTTH info"""
        uri = '/connection/ftth'
        resp = self._http.get(uri)

        if self._conf.resp_as_json:
            return resp.whole_content

        print('Server info:')
        print(' - Model:     {}'.format(resp.result['model_info']['pretty_name']))
        print(' - MAC:       {}'.format(resp.result['mac']))
        print(' - Firmware:  {}'.format(resp.result['firmware_version']))
        print(' - Uptime:    {}'.format(resp.result['uptime']))
        print(' - Sensors:')
        for k, v in resp.result.items():
            print(' - {:25} {}'.format(k, v))
        return True


class FbxServiceStorage(FbxService):
    """Storage domain"""

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


class FbxServiceWifi(FbxService):
    """Wifi domain"""

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


class FbxServiceDhcp(FbxService):
    """DHCP domain"""

    def init(self):
        pass

    def get_static_leases(self):
        """ List the DHCP leases on going"""

        log(">>> get_static_leases")
        self._dyn_leases = FbxDhcpDynamicLeases(self._ctrl)

        def load_from_archive(svc):
            st_leases = FbxDhcpStaticLeases(svc._ctrl, empty=True)
            t_st_leases = FbxDbTable(u'static_lease', u'id', table_defs[u'static_lease'][u'cols_def'])
            st_leases.load_from_db(svc._ctrl, FbxDhcpStaticLease, t_st_leases)
            return st_leases

        if self._conf.resp_archive:
            self._st_leases = load_from_archive(self)
        else:
            self._st_leases = FbxDhcpStaticLeasesX(self._ctrl, self._dyn_leases)

        if self._conf.resp_restore:
            self._st_leases_arc = load_from_archive(self)
            # look for missing static leases
            print(u'\nMissing leases')
            for st_lease_arc in self._st_leases_arc:
                st_lease_fbx = self._st_leases.get_by_id(st_lease_arc.mac)
                if st_lease_fbx is None:
                    print(st_lease_arc)
                    if fbx_question_yn(u'Restore'):
                        data = {u"mac": st_lease_arc.mac, u"ip": st_lease_arc.ip, u"comment": st_lease_arc.comment}
                        print(u'Restore', data)
                        url = u'/dhcp/static_lease/'
                        resp = self._http.post(url, data=data)
                        if not resp.success:
                            raise FbxException('Request failure: {}'.format(resp))

            # look for leases to update
            print(u'\nLeases to update')
            for st_lease_arc in self._st_leases_arc:
                st_lease_fbx = self._st_leases.get_by_id(st_lease_arc.mac)
                if st_lease_fbx is not None:
                    data = {u"mac": st_lease_arc.mac}
                    to_restore = False
                    for key in [u'ip', u'comment']:
                        if getattr(st_lease_arc, key) != getattr(st_lease_fbx, key):
                            to_restore = True
                            data[key] = getattr(st_lease_arc, key)
                    if to_restore:
                        print(st_lease_arc)
                        print(st_lease_fbx)
                        print(data)
                        if fbx_question_yn(u'Update'):
                            print(u'Update', data)
                            url = u'/dhcp/static_lease/{}'.format(st_lease_arc.mac)
                            resp = self._http.put(url, data=data)
                            if not resp.success:
                                raise FbxException('Request failure: {}'.format(resp))
            return 0

        if self._conf.resp_save:
            self._st_leases.save_to_db()

        if self._conf.resp_as_json and self._conf.resp_archive is False:
            return self._st_leases.json

        count = 0
        # for new call only, we display new calls only
        for st_lease in self._st_leases:
            # if new_only and call.new is False:
            #     continue
            count += 1
            # st_lease to be displayed
            print(u'{}# {}'.format(count, st_lease))

        return count > 0

    def get_config(self):
        """Get the current DHCP config"""
        uri = '/dhcp/config/'
        resp = self._http.get(uri)
        return resp

    def get_dhcp_leases(self):
        """ List the DHCP dynamic leases on going"""

        log(">>> get_dynamic_leases")
        self._st_leases = FbxDhcpStaticLeases(self._ctrl)

        if self._conf.resp_archive:
            self._dyn_leases = FbxDhcpDynamicLeases(self._ctrl, empty=True)
            t_dyn_leases = FbxDbTable(u'dynamic_lease', u'mac', table_defs[u'dynamic_lease'][u'cols_def'])
            self._dyn_leases.load_from_db(self._ctrl, FbxDhcpDynamicLease, t_dyn_leases)
        else:
            self._dyn_leases = FbxDhcpDynamicLeasesX(self._ctrl, self._st_leases)

        if len(self._dyn_leases) == 0:
            print('No DHCP leases')
            return 0

        if self._conf.resp_as_json is False:
            print('{} DHCP leases'.format(len(self._dyn_leases)))

        if self._conf.resp_save:
            self._dyn_leases.save_to_db()

        if self._conf.resp_as_json and self._conf.resp_archive is False:
            return self._dyn_leases.json

        tcount = 0
        count = 0

        print('\nList of reachable leases:')
        for dyn_lease in self._dyn_leases:
            if dyn_lease.reachable is False:
                continue
            count += 1
            tcount += 1
            # st_lease to be displayed
            print(u'{}# {}'.format(count, dyn_lease))

        count = 0

        print('\nList of unreachable leases:')
        for dyn_lease in self._dyn_leases:
            if dyn_lease.reachable:
                continue
            count += 1
            tcount += 1
            # st_lease to be displayed
            print(u'{}# {}'.format(count, dyn_lease))

        return tcount > 0

        return

        if self._conf.resp_restore:
            for k, v in self._arc_o_dict.items():
                """ Create static lease"""
                if (k not in self._fbx_o_dict.keys()) and v.is_static:
                    print(v)
                    """ Restore Y/N"""
                    to_restore = False
                    answer = None
                    while answer not in ("y", "n", "Y", "N", "o", "O"):
                        answer = input(u"Restore Y/N): ")
                        if answer in ("y", "Y", "o", "O"):
                            to_restore = True
                        elif answer in ("n", "N"):
                            to_restore = False
                    if to_restore:
                        """ Create missing static lease"""
                        uri = u'/dhcp/static_lease/'
                        data = {"mac": v.mac, "ip": v.ip, "comment": v.comment}
                        resp = self._http.post(uri, data)
                        if not resp.success:
                            uri = u'/dhcp/static_lease/{}'.format(v.mac)
                            data = {"ip": v.ip, "comment": v.comment}
                            resp = self._http.put(uri, data)
                            if not resp.success:
                                print(u'Create failed')
                            print(u'Updated')
                            continue
                        print(u'Created')
                """ Update static lease"""
                if (k in self._fbx_o_dict.keys()) and v.is_static:
                    # todo : compare v with self._fbx_o_dict[k]
                    to_update = False
                    ofbx = self._fbx_o_dict[k]
                    # print(ofbx.comment, v.comment)
                    if (ofbx.comment != v.comment) or (ofbx.ip != v.ip):
                        to_update = True
                    if to_update:
                        print(v, u'\n Archive:\n', ofbx)
                        to_restore = False
                        answer = None
                        while answer not in ("y", "n", "Y", "N", "o", "O"):
                            answer = input(u"Update Y/N): ")
                            if answer in ("y", "Y", "o", "O"):
                                to_restore = True
                            elif answer in ("n", "N"):
                                to_restore = False
                        if to_restore:
                            """ Create missing static lease"""
                            uri = u'/dhcp/static_lease/{}'.format(v.mac)
                            data = {"ip": v.ip, "comment": v.comment}
                            resp = self._http.put(uri, data)
                            if not resp.success:
                                print(u'Update failed')
            return

        log(">>> get_dhcp_leases")
        # GET dhcp leases
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

        count = self.save_to_archive(FbxDhcpDynamicLease, leases)

        count = 1

        # To do : use self._fbx_o_dict

        for olease in self._fbx_o_dict.values():
            print(u'  #{}: {}'.format(count, olease))
            count += 1

        return

        count = 1

        for lease in leases:
            if 'host' in lease and lease.get('host').get('reachable'):
                olease = FbxDhcpDynamicLease(self, lease)
                print(u'  #{}: {}'.format(count, olease))
                count += 1

        count = 1
        print('List of unreachable leases:')
        for lease in leases:
            if 'host' in lease and not lease.get('host').get('reachable'):
                olease = FbxDhcpDynamicLease(self, lease)
                print(u'  #{}: {}'.format(count, olease))
                count += 1

        count = 1
        print('List of other leases:')
        for lease in leases:
            if 'host' not in lease:
                olease = FbxDhcpDynamicLease(self, lease)
                print(u'  #{}: {}'.format(count, olease))
                count += 1
        return 0


class FbxServicePortForwarding(FbxService):
    """Port Forwarding"""

    def init(self):
        pass

    def get_port_forwardings(self):
        """ List the port forwarding on going"""

        def load_from_archive(svc):
            pfwds = FbxPortForwardings(svc._ctrl, empty=True)
            t_pfwds = FbxDbTable(u'fw_redir', u'id', table_defs[u'fw_redir'][u'cols_def'])
            pfwds.load_from_db(svc._ctrl, FbxPortForwarding, t_pfwds)
            return pfwds

        if self._conf.resp_archive:
            self._pfwds = load_from_archive(self)
        else:
            self._pfwds = FbxPortForwardings(self._ctrl)

        if len(self._pfwds) == 0:
            print('No port forwardings')
            return 0

        if self._conf.resp_restore:
            self._pfwds_arc = load_from_archive(self)
            # look for missing port forwardings
            print(u'\nMissing port forwardings')
            for pwd_arc in self._pfwds_arc:
                pwd_fbx = self._pfwds.get_by_id(pwd_arc.id)
                if pwd_fbx is None:
                    print(pwd_arc)
                    if fbx_question_yn(u'Restore'):
                        data = {u"enabled": pwd_arc.enabled,
                                u"comment": pwd_arc.comment,
                                u"lan_port": pwd_arc.lan_port,
                                u"wan_port_end": pwd_arc.wan_port_end,
                                u"wan_port_start": pwd_arc.wan_port_start,
                                u"lan_ip": pwd_arc.lan_ip,
                                u"ip_proto": pwd_arc.ip_proto,
                                u"src_ip": pwd_arc.src_ip,
                                }
                        print(u'Restore', data)
                        url = u'/fw/redir/'
                        resp = self._http.post(url, data=data)
                        if not resp.success:
                            raise FbxException('Request failure: {}'.format(resp))

            return 0

        if self._conf.resp_as_json is False:
            print('{} port forwardings'.format(len(self._pfwds)))

        if self._conf.resp_save:
            # todo : save to archive
            self._pfwds.save_to_db()

        if self._conf.resp_as_json and self._conf.resp_archive is False:
            return self._pfwds.json

        tcount = 0

        log(">>> get_enabled_port_forwarding")
        print(u'Enabled port forwardings')
        count = 0
        for pfwd in self._pfwds:
            if pfwd.enabled is False:
                continue
            count += 1
            tcount += 1
            # pfwd to be displayed
            print(u'{}# {}'.format(count, pfwd))

        log(">>> get_disabled_port_forwarding")
        print(u'Disabled port forwardings')
        count = 0
        for pfwd in self._pfwds:
            if pfwd.enabled is True:
                continue
            count += 1
            tcount += 1
            # pfwd to be displayed
            print(u'{}# {}'.format(count, pfwd))

        return tcount > 0


class FbxServiceContact(FbxService):
    """Contact"""

    def init(self):
        pass

    def get_contacts(self):
        """ List the port forwarding on going"""

        def load_from_archive(svc):
            contacts = FbxContacts(svc._ctrl, empty=True)
            t_contacts = FbxDbTable(u'contact', u'id', table_defs[u'contact'][u'cols_def'])
            contacts.load_from_db(svc._ctrl, FbxContact, t_contacts)
            return contacts

        if self._conf.resp_archive:
            self._contacts = load_from_archive(self)
        else:
            self._contacts = FbxContacts(self._ctrl)

        if len(self._contacts) == 0:
            if not self._conf.resp_restore:
                print('No port contacts')
                return 0

        if self._conf.resp_restore:
            self._contacts = FbxContacts(self._ctrl)
            # clean before populate
            for contact in self._contacts:
                data = {}
                url = u'/contact/{}'.format(contact.id)
                resp = self._http.delete(url, data=data)
            self._contacts = load_from_archive(self)
            i = 0
            for contact in self._contacts:
                i += 1
                # populate
                data = {u"display_name": contact.display_name,
                        u"first_name": contact.first_name,
                        u"last_name": contact.last_name,
                        u"birthday": contact.birthday,
                        u"notes": contact.notes,
                        u"company": contact.company,
                        u"photo_url": contact.photo_url,
                        }
                # print(u'Restore', data)
                url = u'/contact/'
                resp = self._http.post(url, data=data)
                client_id = resp.result['id']

                # print(resp.result)
                # print(client_id)
                if not resp.success:
                    raise FbxException('Request failure: {}'.format(resp))
                if contact.numbers is not None:
                    for number in contact.numbers:
                        # print(u'number: {}'.format(number))
                        data = {u"contact_id": client_id,
                                u"number": number.number,
                                u"type": number.nbr_type,
                                u"is_default": number.is_default,
                                u"is_own": number.is_own,
                                }
                        url = u'/number/'
                        resp = self._http.post(url, data=data)
                        print(resp.result)
                if contact.addresses is not None:
                    for address in contact.addresses:
                        # print(u'address: {}'.format(address))
                        data = {u"contact_id": client_id,
                                u"street": address.street,
                                u"type": address.address_type,
                                u"city": address.city,
                                u"zipcode": address.zipcode,
                                u"number": address.number,
                                u"country": address.country,
                                u"street2": address.street2,
                                }
                        url = u'/address/'
                        resp = self._http.post(url, data=data)
                        print(resp.result)
                if contact.emails is not None:
                    for email in contact.emails:
                        # print(u'email: {}'.format(email))
                        data = {u"contact_id": client_id,
                                u"email": email.email,
                                u"type": email.email_type,
                                }
                        url = u'/email/'
                        resp = self._http.post(url, data=data)
                        print(resp.result)
                if contact.urls is not None:
                    for url in contact.urls:
                        # print(u'url: {}'.format(url))
                        data = {u"contact_id": client_id,
                                u"url": url.url,
                                u"type": url.url_type,
                                }
                        url = u'/url/'
                        resp = self._http.post(url, data=data)
                        print(resp.result)
                # if i > 5: exit(0)
            return 0

        if self._conf.resp_as_json is False:
            print('{} contacts'.format(len(self._contacts)))

        if self._conf.resp_save:
            # todo : save to archive
            self._contacts.save_to_db()

        if self._conf.resp_as_json and self._conf.resp_archive is False:
            return self._contacts.json

        tcount = 0

        log(">>> get_contacts")
        print(u'Contacts')
        count = 0
        for contact in self._contacts:
            count += 1
            tcount += 1
            print(u'{}# {}'.format(count, contact))

        return tcount > 0


class FbxServiceCall(FbxService):
    """Call domain"""

    def init(self):
        pass

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

        if self._conf.resp_archive:
            self._calls = FbxCalls(self._ctrl, empty=True)
            t_calls = FbxDbTable(u'call_log', u'id', table_defs[u'call_log'][u'cols_def'])
            self._calls.load_from_db(self._ctrl, FbxCall, t_calls)
        else:
            self._calls = FbxCalls(self._ctrl)

        if len(self._calls) == 0:
            print('No calls')
            return 0

        if self._conf.resp_as_json is False:
            print('{} calls'.format(len(self._calls)))

        if self._conf.resp_save:
            # todo : save to archive
            self._calls.save_to_db()

        if self._conf.resp_as_json and self._conf.resp_archive is False:
            return self._calls.json

        count = 0
        # for new call only, we display new calls only
        for call in self._calls:
            if new_only and call.new is False:
                continue
            count += 1
            # call to be displayed
            print(u'{}# {}'.format(count, call))

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


class FbxServiceDownload(FbxService):
    """Download domain"""

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
        self._srv_connection = FbxServiceConnection(self._http, self._conf)
        self._srv_storage = FbxServiceStorage(self._http, self._conf)
        self._srv_download = FbxServiceDownload(self._http, self._conf)
        self._srv_wifi = FbxServiceWifi(self._http, self._conf)
        self._srv_dhcp = FbxServiceDhcp(self._http, self._conf, self)
        self._srv_call = FbxServiceCall(self._http, self._conf, self)
        self._srv_contact = FbxServiceContact(self._http, self._conf, self)
        self._srv_pfw = FbxServicePortForwarding(self._http, self._conf, self)

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
    def srv_contact(self):
        return self._srv_contact

    @property
    def srv_port(self):
        return self._srv_pfw


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
            '--archive',
            action='store_true',
            help='read archive')
        self._parser.add_argument(
            '--save',
            action='store_true',
            help='store in archive')
        self._parser.add_argument(
            '--restore',
            action='store_true',
            help='restore from archive')
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
            '--dhcpstleases',
            default=argparse.SUPPRESS,
            action='store_true',
            help='display the current DHCP static leases info')
        group.add_argument(
            '--pfwd',
            default=argparse.SUPPRESS,
            action='store_true',
            help='display the list of port forwardings info')
        group.add_argument(
            '--clist',
            default=argparse.SUPPRESS,
            action='store_true',
            help='display the list of received calls')
        group.add_argument(
            '--contacts',
            default=argparse.SUPPRESS,
            action='store_true',
            help='display the list contacts')
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
            '--einfo',
            default=argparse.SUPPRESS,
            action='store_true',
            help='display the line ethernet information')
        group.add_argument(
            '--linfo',
            default=argparse.SUPPRESS,
            action='store_true',
            help='display the line media (ADSL/Fiber) information')
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
            'dhcpstleases': self._ctrl.srv_dhcp.get_static_leases,
            'pfwd': self._ctrl.srv_port.get_port_forwardings,
            'clist': self._ctrl.srv_call.get_all_calls_list,
            'contacts': self._ctrl.srv_contact.get_contacts,
            'cnew': self._ctrl.srv_call.get_new_calls_list,
            'cread': self._ctrl.srv_call.mark_calls_as_read,
            'reboot': self._ctrl.srv_system.reboot,
            'sinfo': self._ctrl.srv_system.get_system_info,
            'einfo': self._ctrl.srv_connection.get_line_ethernet_info,
            'linfo': self._ctrl.srv_connection.get_line_media_info,
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

        # Activate read from archive
        if argsdict.get('archive'):
            self._ctrl.conf.resp_archive = True
        del argsdict['archive']

        # Activate write to archive
        if argsdict.get('save'):
            self._ctrl.conf.resp_save = True
        del argsdict['save']

        # Activate restore from archive
        if argsdict.get('restore'):
            self._ctrl.conf.resp_restore = True
        del argsdict['restore']

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


def main():
    ctrl = FreeboxOSCtrl()
    cli = FreeboxOSCli(ctrl)

    args = cli.parse_args(sys.argv[1:])

    want_regapp = True if 'regapp' in args else False
    ctrl.conf.load(want_regapp)

    rc = cli.dispatch(args)

    sys.exit(rc)


if __name__ == '__main__':
    main()
    """
    ctrl = FreeboxOSCtrl()
    cli = FreeboxOSCli(ctrl)

    args = cli.parse_args(sys.argv[1:])

    want_regapp = True if 'regapp' in args else False
    ctrl.conf.load(want_regapp)

    rc = cli.dispatch(args)

    sys.exit(rc)
    """
