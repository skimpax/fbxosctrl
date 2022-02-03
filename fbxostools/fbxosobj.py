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


FBXOSOBJ_VERSION = "1.0.1"

__author__ = "Alain Ferraro (aka afer92)"
__copyright__ = "Copyright 2019, Alain Ferraro"
__credits__ = []
__license__ = "GPL"
__version__ = FBXOSOBJ_VERSION
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
        },
    u'contact': {
        u'uri': u'/contact/',
        u'cols_def': {'id': {u'c_order': 0, u'c_type': u'int(11)', u'is_id': True},
                      'display_name': {u'c_order': 10, u'c_type': u'varchar(80)'},
                      'first_name': {u'c_order': 20, u'c_type': u'varchar(80)'},
                      'last_name': {u'c_order': 30, u'c_type': u'varchar(80)'},
                      'birthday': {u'c_order': 40, u'c_type': u'datetime'},
                      'company': {u'c_order': 50, u'c_type': u'varchar(80)'},
                      'photo_url': {u'c_order': 60, u'c_type': u'blob'},
                      'last_update': {u'c_order': 70, u'c_type': u'datetime'},
                      'notes': {u'c_order': 80, u'c_type': u'varchar(8192)'},
                      }
        },
    u'contact_number': {
        u'uri': u'/contact/{}/numbers/',
        u'cols_def': {'id': {u'c_order': 0, u'c_type': u'int(11)', u'is_id': True},
                      'contact_id': {u'c_order': 10, u'c_type': u'int(11)'},
                      'type': {u'c_order': 20, u'c_type': u'varchar(10)', u'c_name': u'nbr_type'},
                      'number': {u'c_order': 30, u'c_type': u'varchar(80)'},
                      'is_default': {u'c_order': 40, u'c_type': u'tinyint(1)'},
                      'is_own': {u'c_order': 50, u'c_type': u'tinyint(1)'},
                      }
        },
    u'contact_address': {
        u'uri': u'/contact/',
        u'cols_def': {'id': {u'c_order': 0, u'c_type': u'int(11)', u'is_id': True},
                      'contact_id': {u'c_order': 10, u'c_type': u'int(11)'},
                      'type': {u'c_order': 20, u'c_type': u'varchar(10)', u'c_name': u'address_type'},
                      'number': {u'c_order': 30, u'c_type': u'varchar(128)'},
                      'street': {u'c_order': 40, u'c_type': u'varchar(128)'},
                      'street2': {u'c_order': 50, u'c_type': u'varchar(128)'},
                      'city': {u'c_order': 60, u'c_type': u'varchar(80)'},
                      'zipcode': {u'c_order': 70, u'c_type': u'varchar(80)'},
                      'country': {u'c_order': 80, u'c_type': u'varchar(80)'},
                      }
        },
    u'contact_url': {
        u'uri': u'/contact/',
        u'cols_def': {'id': {u'c_order': 0, u'c_type': u'int(11)', u'is_id': True},
                      'contact_id': {u'c_order': 10, u'c_type': u'int(11)'},
                      'type': {u'c_order': 20, u'c_type': u'varchar(10)', u'c_name': u'url_type'},
                      'url': {u'c_order': 30, u'c_type': u'varchar(128)'},
                      }
        },
    u'contact_email': {
        u'uri': u'/contact/',
        u'cols_def': {'id': {u'c_order': 0, u'c_type': u'int(11)', u'is_id': True},
                      'contact_id': {u'c_order': 10, u'c_type': u'int(11)'},
                      'type': {u'c_order': 20, u'c_type': u'varchar(10)', u'c_name': u'email_type'},
                      'email': {u'c_order': 30, u'c_type': u'varchar(128)'},
                      }
        },
    u'contact_group': {
        u'uri': u'/contact/',
        u'cols_def': {'contact_id': {u'c_order': 10, u'c_type': u'int(11)', u'is_id': True},
                      'group_id': {u'c_order': 20, u'c_type': u'int(11)', u'is_id': True},
                      }
        },
    u'group': {
        u'uri': u'/group/',
        u'cols_def': {'id': {u'c_order': 10, u'c_type': u'int(11)', u'is_id': True},
                      'name': {u'c_order': 20, u'c_type': u'varchar(80)'},
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

    def __init__(self, ctrl, data, list=None):
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
        self._list = list
        self.init()
        if data is not None:
            self._init_from_data()

    def init():
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
        (query, values) = self._table.sql_build_ph(self, replace=True)
        self.ctrl.conf._db.query_update_ph(self._table, query, values)
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
            ofbx = self._o_type(self._ctrl, fbx, list=self)
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
            ofbx = self._o_type(self._ctrl, row, list=self)
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

    def __str__(self):
        result = u''
        first = True
        for item in self._list:
            if item is not None:
                if first:
                    first = False
                    result += u'\t{}'.format(item)
                else:
                    result += u'\n\t{}'.format(item)
        return result


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


class FbxGroup(FbxObj):
    """Group object"""

    def init(self):
        """Class specific initial processing"""
        self._id_name = u'id'
        self._table_name = u'group'
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
                self._name = self._data.get('name')
            else:
                self._id = self._data.id
                self._name = self._data.name

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    def __str__(self):
        data = 'id: {}, name: {}'.format(self.id, self.name)
        return data


class FbxGroups(FbxObjList):

    def __init__(self, ctrl, empty=False):
        """ Groups list"""
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxGroup
        self._ol_type = FbxGroups
        self._table_name = u'group'
        self._uri = '/group/'
        self._log = ">>> get_groups"
        # init object list
        FbxObjList.init_list(self)

    def group_add(self, name):
        """ Create new group"""
        payload = {u'id': 0, u'name': name, u'nb_contact': 0}
        resp = self._http.post(self._uri, data=payload)

        if not resp.success:
            print(u'Create group {} failed'.format(name))
            print(resp.whole_content)
        else:
            self._list.append(FbxGroup(self._ctrl, resp.result))

    def group_delete(self, id, name):
        """ Delete group"""
        for group in self._list:
            if (group.id == id) and (group.name == name):
                uri = (self._uri+u'{}').format(id)
                payload = {u'id': id, u'name': name, u'nb_contact': 0}
                resp = self._http.delete(uri, data=payload)

                if not resp.success:
                    print(u'Delete group {} failed'.format(name))
                    print(resp.whole_content)
                else:
                    self._list.remove(group)
                    return True
        return False


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
        self._reachable = False
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


class FbxContact(FbxObj):
    """Contact object"""

    def init(self):
        """Class specific initial processing"""
        self._table_name = u'contact'
        self._uri = table_defs[self.table_name][u'uri']
        self._cols_def = table_defs[self.table_name][u'cols_def']
        self._table = FbxDbTable(self._table_name, u'id', self._cols_def)
        self._emails = None
        self._numbers = None
        self._urls = None
        # self._init_from_data()
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            try:
                self._id = self._data.get('id')
                self._display_name = self._data.get('display_name')
                self._first_name = self._data.get('first_name')
                self._last_name = self._data.get('last_name')
                if (self._data.get('birthday') == u'0000-00-00') or (self._data.get('birthday') == u''):
                    self._birthday = 0.0
                else:
                    birthday = self._data.get('birthday')
                    birthday = birthday.split(u'T')[0]
                    try:
                        birthday = datetime.strptime(birthday, "%Y-%m-%d").timestamp()
                    except ValueError:
                        birthday = 0.0
                    self._birthday = birthday
                    self._company = self._data.get('company')
                self._photo_url = self._data.get('photo_url')
                self._last_update = self._data.get('last_update')
                self._notes = self._data.get('notes')

                if self._data.get('addresses') is not None:
                    self._addresses = FbxAddresses(self._ctrl, data=self._data.get('addresses'))
                else:
                    self._addresses = []

                if self._data.get('emails') is not None:
                    self._emails = FbxEmails(self._ctrl, data=self._data.get('emails'))
                else:
                    if self._emails is None:
                        self._emails = []

                if self._data.get('numbers') is not None:
                    self._numbers = FbxNumbers(self._ctrl, data=self._data.get('numbers'))
                else:
                    if self._numbers is None:
                        self._numbers = []

                if self._data.get('urls') is not None:
                    self._urls = FbxUrls(self._ctrl, data=self._data.get('urls'))
                else:
                    self._urls = []
                # get groups
                self._groups = FbxContactGroups(self._ctrl, empty=True)
                if self._list is not None:
                    if self._id in self._list._contact_in_group.keys():
                        for group_id in self._list._contact_in_group[self._id]:
                            fcg = FbxContactGroup(self._ctrl, data={u'group_id': group_id, u'contact_id': self._id})
                            self._groups.append(fcg)

            except AttributeError:
                # load from db
                self._id = self._data.id
                self._display_name = self._data.display_name
                self._first_name = self._data.first_name
                self._last_name = self._data.last_name
                self._birthday = self._data.birthday
                self._company = self._data.company
                self._photo_url = self._data.photo_url
                self._last_update = self._data.last_update
                self._notes = self._data.notes
                # self._addresses = self._data.addresses
                # self._emails = self._data.emails
                self._emails = FbxEmails(self._ctrl, empty=True)
                if self._list is not None:
                    for email in self._list._emails:
                        if email.contact_id == self._id:
                            self._emails.append(email)
                # self._numbers = self._data.numbers
                self._numbers = FbxNumbers(self._ctrl, empty=True)
                if self._list is not None:
                    for number in self._list._numbers:
                        if number.contact_id == self._id:
                            self._numbers.append(number)
                # self._urls = self._data.urls
                self._urls = FbxUrls(self._ctrl, empty=True)
                if self._list is not None:
                    for url in self._list._urls:
                        if url.contact_id == self._id:
                            self._urls.append(url)
                # self._groups
                self._groups = FbxContactGroups(self._ctrl, empty=True)
                if self._list is not None:
                    for group in self._list._cgroups:
                        if group.contact_id == self._id:
                            self._groups.append(group)
                # self._addresses = self._data.addresses
                self._addresses = FbxAddresses(self._ctrl, empty=True)
                if self._list is not None:
                    for address in self._list._addresses:
                        if address.contact_id == self._id:
                            self._addresses.append(address)

    def save_to_db(self):
        FbxObj.save_to_db(self)
        if self._numbers != []:
            self._numbers.save_to_db()
        if self._urls != []:
            self._urls.save_to_db()
        if self._emails != []:
            self._emails.save_to_db()
        if self._addresses != []:
            self._addresses.save_to_db()
        if self._groups != []:
            self._groups.save_to_db()

    def add_to_group(self, group_id):
        """ Add group to contact """
        uri = u'/contact/addtogroup'
        payload = {u'id': 1, u'group_id': group_id, u'contact_id': self._id}
        resp = self._http.post(uri, data=payload)

        if not resp.success:
            print(u'Add to group {} failed'.format(group_id))
            print(resp.whole_content)
            exit(0)
        else:
            self._list.append(FbxGroup(self._ctrl, resp.result))

    @property
    def id(self):
        return self._id

    @property
    def display_name(self):
        return self._display_name

    @property
    def first_name(self):
        return self._first_name

    @property
    def last_name(self):
        return self._last_name

    @property
    def birthday(self):
        return self._birthday

    @property
    def str_birthday(self):
        if self._birthday is None:
            return u''
        result = datetime.fromtimestamp(
                self._birthday).strftime('%d-%m-%Y %H:%M:%S')
        return result

    @property
    def company(self):
        return self._company

    @property
    def photo_url(self):
        return self._photo_url

    @property
    def last_update(self):
        return self._last_update

    @property
    def str_last_update(self):
        return datetime.fromtimestamp(
                self._last_update).strftime('%d-%m-%Y %H:%M:%S')

    @property
    def sql_last_update(self):
        return datetime.fromtimestamp(
                self._last_update).strftime('%Y-%m-%d %H:%M:%S')

    @property
    def notes(self):
        return self._notes

    @property
    def addresses(self):
        return self._addresses

    @property
    def emails(self):
        return self._emails

    @property
    def numbers(self):
        return self._numbers

    @property
    def urls(self):
        return self._urls

    @property
    def groups(self):
        return self._groups

    def __str__(self):
        if self.str_birthday == u'':
            birthday = u''
        else:
            birthday = u', bday {}'.format(self.str_birthday)
        result = '{}: dn {}, fn {}, ln {}{}\n'.format(self.id,
                                                      self.display_name,
                                                      self.first_name,
                                                      self.last_name,
                                                      birthday)
        result += '   cpny {}, updt {}\n'.format(self.company,
                                                 self.str_last_update)
        result += '   notes {}\n'.format(self.notes)
        if self.numbers is not None:
            for number in self.numbers:
                result += '   num {}\n'.format(number)

        if self.urls is not None:
            for url in self.urls:
                result += '   url {}\n'.format(url)

        if self.emails is not None:
            for email in self.emails:
                result += '   email {}\n'.format(email)

        if self.addresses is not None:
            for address in self.addresses:
                result += '   address {}\n'.format(address)

        if self.groups is not None:
            for group in self.groups:
                result += '   group {}\n'.format(group)

        return result


class FbxContacts(FbxObjList):

    def __init__(self, ctrl, empty=False):
        """ Contact list"""
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxContact
        self._ol_type = FbxContacts
        self._table_name = u'contact'
        self._uri = '/contact/'
        self._numbers = None
        self._emails = None
        self._cgroups = None
        self._addresses = None
        self._log = ">>> get_groups"
        self._groups = FbxGroups(ctrl)
        self._log = ">>> get_contact_in_groups"
        self._contact_in_group = {}
        for group in self._groups:
            uri = u'/contact/?page=1&start=0&limit=-1&filter=[{"property":"group_id","value":%s}]' % (group.id)
            resp = self._http.get(uri)
            if resp.success:
                if resp.result is not None:
                    for contact in resp.result:
                        contact_id = contact.get(u'id')
                        if contact_id not in self._contact_in_group:
                            self._contact_in_group[contact_id] = []
                        self._contact_in_group[contact_id].append(group.id)
            else:
                print(u'http.get failed: {}'.format(resp))
        self._contactGroups = FbxContactGroups(ctrl, empty=True)
        for contact_id, value in self._contact_in_group.items():
            for group_id in value:
                cg = FbxContactGroup(ctrl, data={u'contact_id': contact_id, u'group_id': group_id})
                self._contactGroups.append(cg)
        self._log = ">>> get_contacts"
        # init object list
        if empty is False:
            FbxObjList.init_list(self)

    def save_to_db(self):
        FbxObjList.save_to_db(self)
        self._groups.save_to_db()
        self._contactGroups.save_to_db()

    def load_from_db(self, ctrl, O_type, table):
        # get numbers
        self._numbers = FbxNumbers(None, empty=True)
        t_numbers = FbxDbTable(u'contact_number', u'id', table_defs[u'contact_number'][u'cols_def'])
        self._numbers.load_from_db(ctrl, FbxNumber, t_numbers)
        # get emails
        self._emails = FbxEmails(None, empty=True)
        t_emails = FbxDbTable(u'contact_email', u'id', table_defs[u'contact_email'][u'cols_def'])
        self._emails.load_from_db(ctrl, FbxEmail, t_emails)
        # get urls
        self._urls = FbxUrls(None, empty=True)
        t_urls = FbxDbTable(u'contact_url', u'id', table_defs[u'contact_url'][u'cols_def'])
        self._urls.load_from_db(ctrl, FbxUrl, t_urls)
        # get groups
        self._groups = FbxGroups(None, empty=True)
        t_groups = FbxDbTable(u'group', u'id', table_defs[u'group'][u'cols_def'])
        self._groups.load_from_db(ctrl, FbxGroup, t_groups)
        # get contact groups
        self._cgroups = FbxContactGroups(None, empty=True)
        t_cgroups = FbxDbTable(u'contact_group', u'id', table_defs[u'contact_group'][u'cols_def'])
        self._cgroups.load_from_db(ctrl, FbxContactGroup, t_cgroups)
        # get addresses
        self._addresses = FbxAddresses(None, empty=True)
        t_addresses = FbxDbTable(u'contact_address', u'id', table_defs[u'contact_address'][u'cols_def'])
        self._addresses.load_from_db(ctrl, FbxAddress, t_addresses)

        return FbxObjList.load_from_db(self, ctrl, O_type, table)

    @property
    def groups(self):
        return self._groups


class FbxNumber(FbxObj):
    """Number object"""

    def init(self):
        """Class specific initial processing"""
        self._table_name = u'contact_number'
        self._uri = table_defs[self.table_name][u'uri']
        self._cols_def = table_defs[self.table_name][u'cols_def']
        self._table = FbxDbTable(self._table_name, u'id', self._cols_def)
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            try:
                self._id = self._data.get('id')
                self._contact_id = self._data.get('contact_id')
                self._nbr_type = self._data.get('type')
                self._number = self._data.get('number')
                self._is_default = self._data.get('is_default')
                self._is_own = self._data.get('is_own')
            except AttributeError:
                self._id = self._data.id
                self._contact_id = self._data.contact_id
                self._nbr_type = self._data.nbr_type
                self._number = self._data.number
                self._is_default = self._data.is_default
                self._is_own = self._data.is_own

    @property
    def id(self):
        return self._id

    @property
    def contact_id(self):
        return self._contact_id

    @property
    def nbr_type(self):
        return self._nbr_type

    @property
    def number(self):
        return self._number

    @property
    def is_default(self):
        return self._is_default

    @property
    def is_own(self):
        return self._is_own

    def __str__(self):
        if self.is_default:
            is_default = u'is_default'
        else:
            is_default = u''
        if self.is_own:
            is_own = u'is_own'
        else:
            is_own = u''
        result = '{}: n° {} type {} {} {}'.format(
                                               self._id,
                                               self.number,
                                               self.nbr_type,
                                               is_default,
                                               is_own
                                               )

        return result


class FbxNumbers(FbxObjList):

    def __init__(self, ctrl, data=None, empty=False):
        """ Contact list"""
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxNumber
        self._ol_type = FbxNumbers
        self._table_name = u'contact'
        self._uri = '/contact/'
        self._log = ">>> get_numbers"
        self._data = data
        self._ctrl = ctrl
        # init object list
        self.init_list()

    def init_list(self):
        self._json = self._data

        if self._data is None:
            return

        for number_data in self._data:
            ofbx = self._o_type(self._ctrl, number_data)
            ofbx._src = self._ctrl._conf.freebox_address
            self.append(ofbx)


class FbxUrl(FbxObj):
    """Number object"""

    def init(self):
        """Class specific initial processing"""
        self._table_name = u'contact_url'
        self._uri = table_defs[self.table_name][u'uri']
        self._cols_def = table_defs[self.table_name][u'cols_def']
        self._table = FbxDbTable(self._table_name, u'id', self._cols_def)
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            try:
                self._id = self._data.get('id')
                self._contact_id = self._data.get('contact_id')
                self._url_type = self._data.get('type')
                self._url = self._data.get('url')
            except AttributeError:
                self._id = self._data.id
                self._contact_id = self._data.contact_id
                self._url_type = self._data.url_type
                self._url = self._data.url

    @property
    def id(self):
        return self._id

    @property
    def contact_id(self):
        return self._contact_id

    @property
    def url_type(self):
        return self._url_type

    @property
    def url(self):
        return self._url

    def __str__(self):
        result = '{}: url {} type {}'.format(
                                               self._id,
                                               self.url,
                                               self.url_type
                                               )

        return result


class FbxUrls(FbxObjList):

    def __init__(self, ctrl, data=None, empty=False):
        """ Contact list"""
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxUrl
        self._ol_type = FbxUrls
        self._table_name = u'contact'
        self._uri = '/contact/'
        self._log = ">>> get_urls"
        self._data = data
        self._ctrl = ctrl
        # init object list
        self.init_list()

    def init_list(self):
        self._json = self._data

        if self._data is None:
            return

        for number_data in self._data:
            ofbx = self._o_type(self._ctrl, number_data)
            ofbx._src = self._ctrl._conf.freebox_address
            self.append(ofbx)


class FbxEmail(FbxObj):
    """Number object"""

    def init(self):
        """Class specific initial processing"""
        self._table_name = u'contact_email'
        self._uri = table_defs[self.table_name][u'uri']
        self._cols_def = table_defs[self.table_name][u'cols_def']
        self._table = FbxDbTable(self._table_name, u'id', self._cols_def)
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            try:
                self._id = self._data.get('id')
                self._contact_id = self._data.get('contact_id')
                self._email_type = self._data.get('type')
                self._email = self._data.get('email')
            except AttributeError:
                self._id = self._data.id
                self._contact_id = self._data.contact_id
                self._email_type = self._data.email_type
                self._email = self._data.email

    @property
    def id(self):
        return self._id

    @property
    def contact_id(self):
        return self._contact_id

    @property
    def email_type(self):
        return self._email_type

    @property
    def email(self):
        return self._email

    def __str__(self):
        result = '{}: email {} type {}'.format(
                                               self._id,
                                               self.email,
                                               self.email_type
                                               )

        return result


class FbxEmails(FbxObjList):

    def __init__(self, ctrl, data=None, empty=False):
        """ Contact list"""
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxEmail
        self._ol_type = FbxEmails
        self._table_name = u'contact'
        self._uri = '/contact/'
        self._log = ">>> get_emails"
        self._data = data
        self._ctrl = ctrl
        # init object list
        self.init_list()

    def init_list(self):
        self._json = self._data

        if self._data is None:
            return

        for email_data in self._data:
            ofbx = self._o_type(self._ctrl, email_data)
            ofbx._src = self._ctrl._conf.freebox_address
            self.append(ofbx)


class FbxAddress(FbxObj):
    """Number object"""

    def init(self):
        """Class specific initial processing"""
        self._table_name = u'contact_address'
        self._uri = table_defs[self.table_name][u'uri']
        self._cols_def = table_defs[self.table_name][u'cols_def']
        self._table = FbxDbTable(self._table_name, u'id', self._cols_def)
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            try:
                self._id = self._data.get('id')
                self._contact_id = self._data.get('contact_id')
                self._address_type = self._data.get('type')
                self._number = self._data.get('number')
                self._street = self._data.get('street')
                self._street2 = self._data.get('street2')
                self._city = self._data.get('city')
                self._zipcode = self._data.get('zipcode')
                self._country = self._data.get('country')
            except AttributeError:
                self._id = self._data.id
                self._contact_id = self._data.contact_id
                self._address_type = self._data.address_type
                self._number = self._data.number
                self._street = self._data.street
                self._street2 = self._data.street2
                self._city = self._data.city
                self._zipcode = self._data.zipcode
                self._country = self._data.country

    @property
    def id(self):
        return self._id

    @property
    def contact_id(self):
        return self._contact_id

    @property
    def address_type(self):
        return self._address_type

    @property
    def number(self):
        return self._number

    @property
    def street(self):
        return self._street

    @property
    def street2(self):
        return self._street2

    @property
    def city(self):
        return self._city

    @property
    def zipcode(self):
        return self._zipcode

    @property
    def country(self):
        return self._country

    def __str__(self):
        result = '\n{} - address type: {}\n\n    {} {}\n'.format(
                                               self._id,
                                               self.address_type,
                                               self.number,
                                               self.street,
                                               )
        result += '    {}\n'.format(self.street2)
        result += '    {} {}\n'.format(self.zipcode, self.city)
        result += '    {}\n'.format(self.country)

        return result


class FbxAddresses(FbxObjList):

    def __init__(self, ctrl, data=None, empty=False):
        """ Contact list"""
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxAddress
        self._ol_type = FbxAddresses
        self._table_name = u'contact'
        self._uri = '/contact/'
        self._log = ">>> get_addresses"
        self._data = data
        self._ctrl = ctrl
        # init object list
        self.init_list()

    def init_list(self):
        self._json = self._data

        if self._data is None:
            return

        for address_data in self._data:
            ofbx = self._o_type(self._ctrl, address_data)
            ofbx._src = self._ctrl._conf.freebox_address
            self.append(ofbx)


class FbxContactGroup(FbxObj):
    """Number object"""

    def init(self):
        """Class specific initial processing"""
        self._table_name = u'contact_group'
        self._uri = table_defs[self.table_name][u'uri']
        self._cols_def = table_defs[self.table_name][u'cols_def']
        self._table = FbxDbTable(self._table_name, u'id', self._cols_def)
        # self._init_from_data()
        if self._ctrl is not None:
            self._freebox_address = self._ctrl._conf.freebox_address
        else:
            self._freebox_address = u''

    def _init_from_data(self):
        if self._data is not None:
            try:
                self._contact_id = self._data.get('contact_id')
                self._group_id = self._data.get('group_id')
            except AttributeError:
                self._contact_id = self._data.contact_id
                self._group_id = self._data.group_id

    @property
    def id(self):
        return self._id

    @property
    def contact_id(self):
        return self._contact_id

    @property
    def group_id(self):
        return self._group_id

    def __str__(self):
        result = 'contact {} group {}'.format(
                                              self.contact_id,
                                              self.group_id
                                              )
        return result


class FbxContactGroups(FbxObjList):

    def __init__(self, ctrl, data=None, empty=False):
        """ Contact list"""
        # init object
        FbxObjList.__init__(self, ctrl=ctrl, empty=empty)
        self._o_type = FbxContactGroup
        self._ol_type = FbxContactGroups
        self._table_name = u'contact'
        self._uri = '/contact/groups'
        self._log = ">>> get_contact_groups"
        self._data = data
        self._ctrl = ctrl
        # init object list
        self.init_list()

    def init_list(self):
        self._json = self._data

        if self._data is None:
            return

        for group in self._data:
            ofbx = self._o_type(self._ctrl, group)
            ofbx._src = self._ctrl._conf.freebox_address
            self.append(ofbx)


def main():

    print(u'Seems to be ok')

    return 0


if __name__ == '__main__':

    sys.exit(main())
