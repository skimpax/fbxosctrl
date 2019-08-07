#!/usr/bin/env python3

# -*- coding: utf-8 -*-
########################################################################
# Nothing expected to be modified below this line... unless bugs fix ;-)
########################################################################

import sys
from datetime import datetime
import requests

try:
    from fbxosdb import FbxDbTable
except:
    from fbxostools.fbxosdb import FbxDbTable


FBXOSDB_VERSION = "1.0.0"

__author__ = "Alain Ferraro (aka afer92)"
__copyright__ = "Copyright 2019, Alain Ferraro"
__credits__ = []
__license__ = "GPL"
__version__ = FBXOSDB_VERSION
__maintainer__ = "afer92"
__email__ = ""
__status__ = "Production"


g_log_enabled = False


def log(what, end='\n', flush=False):
    """Logger function"""
    global g_log_enabled
    if g_log_enabled:
        print(what, end=end, flush=False)


def enable_log(is_enabled):
    """Update log state"""
    global g_log_enabled
    g_log_enabled = is_enabled


table_defs = {
    u'call_log': {
        u'uri': u'/call/log/',
        u'cols_def': {
            'id': {u'c_order': 0, u'c_type': u'int(11)', u'is_id': True},
            'type': {u'c_order': 10, u'c_type': u'varchar(11)', u'c_name': u'status'},
            'datetime': {u'c_order': 20, u'c_type': u'datetime', u'c_name': u'timestamp'},
            'number': {u'c_order': 30, u'c_type': u'varchar(40)'},
            'name': {u'c_order': 40, u'c_type': u'varchar(80)'},
            'duration': {u'c_order': 50, u'c_type': u'int(11)'},
            'new': {u'c_order': 60, u'c_type': u'tinyint(1)'},
            'contact_id': {u'c_order': 70, u'c_type': u'int(11)'},
            'src': {u'c_order': 80, u'c_type': u'varchar(40)'},
            }
    },
    u'static_lease': {
        u'uri': u'/dhcp/static_lease/',
        u'cols_def': {
            'id': {u'c_order': 10, u'c_type': u'varchar(17)', u'is_id': True},
            'mac': {u'c_order': 20, u'c_type': u'varchar(17)'},
            'comment': {u'c_order': 30, u'c_type': u'varchar(40)'},
            'hostname': {u'c_order': 40, u'c_type': u'varchar(40)'},
            'ip': {u'c_order': 50, u'c_type': u'varchar(27)'},
            'reachable': {u'c_order': 60, u'c_type': u'tinyint(1)'},
            'last_activity': {u'c_order': 70, u'c_type': u'datetime'},
            'last_time_reachable': {u'c_order': 80, u'c_type': u'datetime'},
            'src': {u'c_order': 90, u'c_type': u'varchar(40)'},
            }
    },
    u'fw_redir': {
        u'uri': u'/fw/redir/',
        u'cols_def': {'id': {u'c_order': 0, u'c_type': u'int(11)', u'is_id': True},
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
    },
    u'dynamic_lease': {
        u'uri': u'/dhcp/dynamic_lease/',
        u'cols_def': {'mac': {u'c_order': 0, u'c_type': u'varchar(17)', u'is_id': True},
                      'hostname': {u'c_order': 10, u'c_type': u'varchar(40)'},
                      'ip': {u'c_order': 20, u'c_type': u'varchar(27)'},
                      'lease_remaining': {u'c_order': 30, u'c_type': u'int(11)'},
                      'assign_time': {u'c_order': 40, u'c_type': u'datetime'},
                      'refresh_time': {u'c_order': 50, u'c_type': u'datetime'},
                      'is_static': {u'c_order': 60, u'c_type': u'tinyint(1)'},
                      'comment': {u'c_order': 70, u'c_type': u'varchar(40)'},
                      'src': {u'c_order': 99, u'c_type': u'varchar(40)'},
                      }
        }
    }


class FbxException(Exception):
    """ Exception for FreeboxOS domain """

    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return self.reason


class FbxObj:
    """Fbx generic object"""

    def __init__(self, ctrl, data):
        """Constructor"""
        try:
            from fbxosbase import FbxHttp
        except:
            from fbxostools.fbxosbase import FbxHttp
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
        self._json = u''
        self._cols_def = {}
        self._table = None
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
        self._json = resp.whole_content
        self._init_from_data()
        self._src = self._ctrl._conf.freebox_address

    def sql_build(self, replace=False):
        sql_update = self._table.sql_build(self, replace=True)
        table_name = u'`%s`' % (self._table.table_name)
        sql_update = sql_update.format(table_name)
        return sql_update

    def save_to_db(self):
        query = self.sql_build(replace=True)
        self.ctrl.conf._db.query_update(self, query)
        return

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

    @property
    def src(self):
        return self._src

    @property
    def json(self):
        return self._json


class FbxObjList:
    """Fbx generic object list"""

    def __init__(self, ctrl=None, empty=False):
        """Constructor"""
        try:
            from fbxosbase import FbxHttp
        except:
            from fbxostools.fbxosbase import FbxHttp
        self._list = []
        self._json = u''
        self._o_type = None
        self._ol_type = None
        self._ctrl = empty
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
        if (self._ctrl is None) or ():
            return
        log(self._log)
        uri = self._uri
        resp = self._http.get(uri)

        if not resp.success:
            return

        fbxs = resp.result
        if fbxs is None:
            return

        self._json = resp.whole_content

        for fbx in fbxs:
            ofbx = self._o_type(self._ctrl, fbx)
            ofbx._src = self._ctrl._conf.freebox_address
            self.append(ofbx)

    def load_from_db(self, ctrl, O_type, table):
        try:
            from fbxosbase import FbxHttp
        except:
            from fbxostools.fbxosbase import FbxHttp
        log(self._log)
        log(u'>>>> load_from_db')
        if ctrl is not None:
            self._ctrl = ctrl
            self._conf = ctrl._conf
            self._http = FbxHttp(self._conf)
            self._o_type = O_type
            self._ol_type = type(self)
        sql_select = table.sql_select
        table_name = u'`%s`' % (table.table_name)
        sql_select = sql_select.format(table_name)
        rows = ctrl.conf._db.query_select(table, sql_select)
        for row in rows:
            ofbx = self._o_type(self._ctrl, row)
            ofbx._src = 'database'
            self._list.append(ofbx)
        return len(rows)

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

    def save_to_db(self):
        for obx in self._list:
            log('.', end='', flush=True)
            obx.save_to_db()

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

    @property
    def json(self):
        return self._json

    def __len__(self):
        return len(self._list)


class FbxCall(FbxObj):
    """Call object"""

    def init(self):
        """Class specific initial processing"""
        self._table_name = u'call_log'
        self._uri = table_defs[self.table_name][u'uri']
        self._cols_def = table_defs[self.table_name][u'cols_def']
        self._table = FbxDbTable(self._table_name, u'id', self._cols_def)
        self._init_from_data()
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            try:
                self._timestamp = self._data.get('datetime')
                self._duration = self._data.get('duration')
                self._number = self._data.get('number')
                self._name = self._data.get('name')
                self._id = self._data.get('id')
                self._new = self._data.get('new')
                self._status = self._data.get('type')
                self._contact_id = self._data.get('contact_id')
            except AttributeError:
                self._timestamp = self._data.timestamp
                self._duration = self._data.duration
                self._number = self._data.number
                self._name = self._data.name
                self._id = self._data.id
                self._new = self._data.new
                self._status = self._data.status
                self._contact_id = self._data.contact_id
                self._src = self._data.src

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

    def __init__(self, ctrl, empty=False):
        """ Phone call list"""
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxCall
        self._ol_type = FbxCalls
        self._table_name = u'call_log'
        self._uri = '/call/log/'
        self._log = ">>> get_phone_calls"
        # init object list
        FbxObjList.init_list(self)


class FbxDhcpStaticLease(FbxObj):
    """Call object"""

    def init(self):
        """Class specific initial processing"""
        self._id_name = u'id'
        self._table_name = u'static_lease'
        self._uri = table_defs[self.table_name][u'uri']
        self._cols_def = table_defs[self.table_name][u'cols_def']
        self._table = FbxDbTable(self._table_name, u'id', self._cols_def)
        self._init_from_data()
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            if isinstance(self._data, dict):
                self._id = self._data.get('id')
                self._mac = self._data.get('mac')
                self._comment = self._data.get('comment')
                self._hostname = self._data.get('hostname')
                self._ip = self._data.get('ip')
                if 'host' in self._data and self._data.get('host').get('reachable'):
                    self._reachable = True
                    self._last_activity = self._data.get('host').get('last_activity')
                    self._last_time_reachable = self._data.get('host').get('last_time_reachable')
                else:
                    self._reachable = False
                    self._last_activity = None
                    self._last_time_reachable = None
            else:
                self._id = self._data.id
                self._mac = self._data.mac
                self._comment = self._data.comment
                self._hostname = self._data.hostname
                self._ip = self._data.ip
                self._reachable = self._data.reachable
                self._last_activity = self._data.last_activity
                self._last_time_reachable = self._data.last_time_reachable
                self._src = self._data.src

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
    def comment(self):
        return self._comment

    @property
    def hostname(self):
        return self._hostname

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
    def src(self):
        return self._src

    def __str__(self):
        data = 'id: {}, mac: {}, ip: {}, hostname: {}\n       reachable: {}, comment: {}'
        data += '\n       last_activity: {}, last_time_reachable: {}'
        data = data.format(self.id, self.mac, self.ip, self.hostname,
                           self.reachable, self.comment, self.str_last_activity,
                           self.str_last_time_reachable)
        return data


class FbxDhcpStaticLeases(FbxObjList):

    def __init__(self, ctrl, empty=False):
        """ Phone call list"""
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxDhcpStaticLease
        self._ol_type = FbxDhcpStaticLeases
        self._table_name = u'static_lease'
        self._uri = '/dhcp/static_lease/'
        self._log = ">>> get_static_leases"
        # init object list
        FbxObjList.init_list(self)


class FbxDhcpStaticLeaseX(FbxDhcpStaticLease):

    def __init__(self, ctrl, data, dyn_leases):
        self._dyn_leases = dyn_leases
        self._comment = u''
        self._lease_remaining = 0
        self._assign_time = None
        self._refresh_time = None
        FbxDhcpDynamicLease.__init__(self, ctrl, data)
        """ List the DHCP leases on going"""
        self.init()

    def init(self):
        FbxDhcpStaticLease.init(self)
        if (self._data is not None):
            dyn_lease = self._dyn_leases.get_by_id(self._mac)
            if dyn_lease is not None:
                self._lease_remaining = dyn_lease._lease_remaining
                self._assign_time = dyn_lease._assign_time
                self._refresh_time = dyn_lease._refresh_time

    @property
    def lease_remaining(self):
        return self._lease_remaining

    @property
    def assign_time(self):
        return self._assign_time

    @property
    def str_assign_time(self):
        if self._assign_time is None:
            return ''
        return datetime.fromtimestamp(
                self._assign_time).strftime('%d-%m-%Y %H:%M:%S')

    @property
    def refresh_time(self):
        return self._refresh_time

    @property
    def str_refresh_time(self):
        if self._refresh_time is None:
            return ''
        return datetime.fromtimestamp(
                self._refresh_time).strftime('%d-%m-%Y %H:%M:%S')

    def __str__(self):
        data = FbxDhcpStaticLease.__str__(self)
        datax = '\n       lease_remaining : {}, assign_time : {}, refresh_time  : {}'
        datax = datax.format(self.lease_remaining,
                             self.str_assign_time,
                             self.str_refresh_time
                             )
        return data+datax


class FbxDhcpStaticLeasesX(FbxObjList):

    def __init__(self, ctrl, dyn_leases, empty=False):
        """ Phone call list"""
        self._dyn_leases = dyn_leases
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxDhcpStaticLeaseX
        self._ol_type = FbxDhcpStaticLeasesX
        self._table_name = u'static_lease'
        self._uri = '/dhcp/static_lease/'
        self._log = ">>> get_static_leases"
        # init object list
        self.init_list()

    def init_list(self):
        if (self._ctrl is None) or ():
            return
        log(self._log)
        uri = self._uri
        resp = self._http.get(uri)

        if not resp.success:
            return

        fbxs = resp.result
        if fbxs is None:
            return

        self._json = resp.whole_content

        for fbx in fbxs:
            ofbx = self._o_type(self._ctrl, fbx, self._dyn_leases)
            ofbx._src = self._ctrl._conf.freebox_address
            self.append(ofbx)


class FbxPortForwarding(FbxObj):
    """Call object"""

    def init(self):
        """Class specific initial processing"""
        self._table_name = u'fw_redir'
        self._uri = table_defs[self.table_name][u'uri']
        self._cols_def = table_defs[self.table_name][u'cols_def']
        self._table = FbxDbTable(self._table_name, u'id', self._cols_def)
        self._init_from_data()
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            try:
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
            except AttributeError:
                self._id = self._data.id
                self._src_ip = self._data.src_ip
                self._ip_proto = self._data.ip_proto
                self._wan_port_start = self._data.wan_port_start
                self._wan_port_end = self._data.wan_port_end
                self._lan_port = self._data.lan_port
                self._lan_ip = self._data.lan_ip
                self._hostname = self._data.hostname
                self._enabled = self._data.enabled
                self._comment = self._data.comment
                self._src = self._data.src

    @property
    def id(self):
        return self._id

    @property
    def src_ip(self):
        return self._src_ip

    @property
    def ip_proto(self):
        return self._ip_proto

    @property
    def wan_port_start(self):
        return self._wan_port_start

    @property
    def wan_port_end(self):
        return self._wan_port_end

    @property
    def lan_port(self):
        return self._lan_port

    @property
    def lan_ip(self):
        return self._lan_ip

    @property
    def hostname(self):
        return self._hostname

    @property
    def enabled(self):
        return self._enabled

    @property
    def comment(self):
        return self._comment

    @comment.setter
    def comment(self, value):
        self._set_property_by_id(self._uri, self._id, {u'comment': value})
        self._comment = value

    @property
    def src(self):
        return self._src

    def __str__(self):

        data = '  #{}: enabled: {}, hostname: {}, comment: {},\n'
        data += '       lan_port: {}, wan_port_start: {}, wan_port_end: {}\n'
        data += '       src_ip: {}, lan_ip: {}, ip_proto: {}'
        return data.format(self.id, self.enabled, self.hostname,
                           self.comment, self.lan_port, self.wan_port_start,
                           self.wan_port_end, self.src_ip,
                           self.lan_ip, self.ip_proto)


class FbxPortForwardings(FbxObjList):

    def __init__(self, ctrl, empty=False):
        """ Phone call list"""
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxPortForwarding
        self._ol_type = FbxPortForwardings
        self._table_name = u'fw_redir'
        self._uri = '/fw/redir/'
        self._log = ">>> get_fw_redirs"
        # init object list
        FbxObjList.init_list(self)


class FbxDhcpDynamicLease(FbxObj):
    """Call object"""

    def init(self):
        """Class specific initial processing"""
        self._id_name = u'mac'
        self._table_name = u'dynamic_lease'
        self._uri = table_defs[self.table_name][u'uri']
        self._cols_def = table_defs[self.table_name][u'cols_def']
        self._table = FbxDbTable(self._table_name, u'id', self._cols_def)
        self._comment = u''
        self._init_from_data()
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            try:
                self._mac = self._data.get('mac', '')
                self._hostname = self._data.get('hostname', '')
                if 'host' in self._data and self._data.get('host').get('reachable'):
                    self._reachable = True
                    self._last_activity = self._data.get('host').get('last_activity')
                    self._last_time_reachable = self._data.get('host').get('last_time_reachable')
                else:
                    self._reachable = False
                    self._last_activity = None
                    self._last_time_reachable = None
                self._ip = self._data.get('ip', '')
                self._lease_remaining = self._data.get('lease_remaining', 0)
                self._assign_time = self._data.get('assign_time', None)
                self._refresh_time = self._data.get('refresh_time', None)
                self._is_static = self._data.get('is_static', False)
                self._comment = self._data.get('comment', '')
            except AttributeError:
                self._mac = self._data.mac
                self._hostname = self._data.hostname
                self._ip = self._data.ip
                self._lease_remaining = self._data.lease_remaining
                self._assign_time = self._data.assign_time
                self._refresh_time = self._data.refresh_time
                self._is_static = self._data.is_static
                self._comment = self._data.comment
                self._src = self._data.src

    @property
    def mac(self):
        return self._mac

    @property
    def hostname(self):
        return self._hostname

    @property
    def ip(self):
        return self._ip

    @property
    def lease_remaining(self):
        return self._lease_remaining

    @property
    def assign_time(self):
        return self._assign_time

    @property
    def str_assign_time(self):
        if self._assign_time is None:
            return ''
        return datetime.fromtimestamp(
                self._assign_time).strftime('%d-%m-%Y %H:%M:%S')

    @property
    def refresh_time(self):
        return self._refresh_time

    @property
    def str_refresh_time(self):
        if self._refresh_time is None:
            return ''
        return datetime.fromtimestamp(
                self._refresh_time).strftime('%d-%m-%Y %H:%M:%S')

    @property
    def is_static(self):
        return self._is_static

    @property
    def comment(self):
        return self._comment

    @property
    def reachable(self):
        return self._reachable

    @property
    def src(self):
        return self._src

    def __str__(self):
        data = 'id: {}, mac: {}, ip: {}, hostname: {}\n       is_static: {}, reachable: {}, comment: {}'
        data += '\n       lease_remaining : {}, assign_time : {}, refresh_time  : {}'
        data = data.format(self.mac, self.mac, self.ip, self.hostname,
                           self.is_static, self._reachable, self.comment,
                           self.lease_remaining,
                           self.str_assign_time,
                           self.str_refresh_time
                           )
        return data


class FbxDhcpDynamicLeases(FbxObjList):

    def __init__(self, ctrl, empty=False):
        """ Phone call list"""
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxDhcpDynamicLease
        self._ol_type = FbxDhcpDynamicLeases
        self._table_name = u'dynamic_lease'
        self._uri = '/dhcp/dynamic_lease/'
        self._log = ">>> get_dynamic_leases"
        # init object list
        FbxObjList.init_list(self)


class FbxDhcpDynamicLeaseX(FbxDhcpDynamicLease):

    def __init__(self, ctrl, data, st_leases):
        self._st_leases = st_leases
        self._comment = u''
        FbxDhcpDynamicLease.__init__(self, ctrl, data)
        """ List the DHCP leases on going"""
        self.init()

    def init(self):
        FbxDhcpDynamicLease.init(self)
        if (self._data is not None) and self._is_static:
            st_lease = self._st_leases.get_by_id(self._mac)
            if st_lease is not None:
                self._comment = st_lease.comment


class FbxDhcpDynamicLeasesX(FbxObjList):

    def __init__(self, ctrl, st_leases, empty=False):
        # """ Phone call list"""
        self._st_leases = st_leases
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxDhcpDynamicLeaseX
        self._ol_type = FbxDhcpDynamicLeasesX
        self._table_name = u'dynamic_lease'
        self._uri = '/dhcp/dynamic_lease/'
        self._log = ">>> get_dynamic_leases"
        # init object list
        self.init_list()

    def init_list(self):
        if (self._ctrl is None) or ():
            return
        log(self._log)
        uri = self._uri
        resp = self._http.get(uri)

        if not resp.success:
            return

        fbxs = resp.result
        if fbxs is None:
            return

        self._json = resp.whole_content

        for fbx in fbxs:
            ofbx = self._o_type(self._ctrl, fbx, self._st_leases)
            ofbx._src = self._ctrl._conf.freebox_address
            self.append(ofbx)


def main():

    print(u'Seems to be ok')

    return 0


if __name__ == '__main__':

    sys.exit(main())
