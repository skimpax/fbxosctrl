#!/usr/bin/env python3

# -*- coding: utf-8 -*-
########################################################################
# Nothing expected to be modified below this line... unless bugs fix ;-)
########################################################################

from collections import namedtuple
import os
import sys
import sqlite3
from datetime import datetime


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


def log(what):
    """Logger function"""
    global g_log_enabled
    if g_log_enabled:
        print(what)


def enable_log(is_enabled):
    """Update log state"""
    global g_log_enabled
    g_log_enabled = is_enabled


class FbxDbLite:
    """"Service base class"""

    def __init__(self, db_file):
        """Constructor"""
        self._db_file = db_file
        self._conn = None
        self._tables = {}
        if os.path.exists(self._db_file):
            self._to_init = False
            self._to_init = True
            try:
                self._conn = sqlite3.connect(self._db_file)
                self._conn.row_factory = sqlite3.Row
            except sqlite3.OperationalError:
                pass
        else:
            self._to_init = True

    def add_table(self, db_table):
        self._tables[db_table.table_name] = db_table

    def init_base(self):
        if self._to_init:
            try:
                self._conn = sqlite3.connect(self._db_file)
                self._conn.row_factory = sqlite3.Row
                c = self._conn.cursor()
            except sqlite3.OperationalError:
                return
            for k, db_table in self._tables.items():
                try:
                    c.executescript(db_table.sql_table_create)
                except sqlite3.OperationalError:
                    print(db_table.sql_table_create)
                    return
            self._conn.commit()
            self._to_init = False

    def query_update_ph(self, db_table, query, values):
        db_table_name = u'`{}`'.format(db_table.table_name)
        query = query.format(db_table_name)
        log('>>> Query: {}'.format(query))
        try:
            c = self._conn.cursor()
            rc = c.execute(query, values)
            self._conn.commit()
            c.close()
        except sqlite3.OperationalError:
            print(query, u'\n\t', values)
            return None
        return rc

    def query_update(self, db_table, query):
        db_table_name = u'`{}`'.format(db_table.table_name)
        query = query.format(db_table_name)
        log('>>> Query: {}'.format(query))
        try:
            c = self._conn.cursor()
            rc = c.execute(query)
            self._conn.commit()
            c.close()
        except sqlite3.OperationalError:
            print(query)
            return rc
        return rc

    def query_select(self, db_table, query, process_row=None):
        db_table_name = u'`{}`'.format(db_table.table_name)
        query = query.format(db_table_name)
        O_row = db_table.Tuple
        field_names = db_table._get_dbfield_names_ordered()
        result = []

        log('>>> Query: {}'.format(query))

        try:
            c = self._conn.cursor()
            rows = c.execute(query)
        except sqlite3.OperationalError:
            print(query)
            return(None, None)

        for row in rows:
            row_keys = row.keys()
            datas = []
            if process_row is not None:
                process_row(self, row)
            for field_name in field_names:
                field_name = field_name.replace('`', '')
                if field_name in row_keys:
                    if db_table._cols_def[field_name][u'c_type'] == u'tinyint(1)':
                        data = (row[field_name] == 1)
                    elif db_table._cols_def[field_name][u'c_type'] == u'datetime':
                        if len(row[field_name]) == '':
                            data = None
                        elif len(row[field_name]) == 19:
                            data = datetime.strptime(row[field_name], u'%Y-%m-%d %H:%M:%S').timestamp()
                        else:
                            try:
                                data = datetime.strptime(row[field_name], u'%Y-%m-%d %H:%M:%S.%f').timestamp()
                            except ValueError:
                                data = None
                        # data = datetime.strptime(row[field_name], u'%Y-%m-%d %H:%M:%S')
                        # data = (data - datetime(1970, 1, 1)).total_seconds()
                        # data = row[field_name]
                    else:
                        data = row[field_name]
                else:
                    data = None
                datas.append(data)
            result.append(O_row._make(datas))

        return result


class FbxDbTable:
    """"Service base class"""

    def __init__(self, table_name, id_name, cols_def):
        """Constructor"""
        self._cols_def = cols_def
        self._table_name = table_name
        self._id_name = id_name
        self.init()

    def init(self):
        """Constructor"""
        pass

    def _get_fields_ordered(self):
        """Fields definition indexed by order"""
        fields = {}
        for field, value in self._cols_def.items():
            value[u'c_field'] = field
            fields[str(value[u'c_order'])] = value
        return fields

    def _get_field_names_ordered(self):
        """Fields names indexed by order"""
        field_names = []
        fields = self._get_fields_ordered()
        for k in sorted(fields.keys()):
            if u'c_name' in fields[k]:
                field_names.append(fields[k][u'c_name'])
            else:
                field_names.append(fields[k][u'c_field'])
        return field_names

    def _get_dbfield_names_ordered(self):
        """Fields db names indexed by order"""
        result = []
        fields = self._get_fields_ordered()
        for k, v in sorted(fields.items()):
            result.append(v[u'c_field'])
        return result

    def primary_keys(self):
        """ get primary keys """
        result = []
        for field, value in self._cols_def.items():
            if (u'is_id' in value.keys()) and (value[u'is_id']):
                result.append(u'`{}`'.format(field))
        return result

    def _sql_build_table_create(self):
        """Create sql INSERT or REPLACE with FbxObj properties"""
        fields = self._get_fields_ordered()
        p_keys = self.primary_keys()
        if len(p_keys) > 0:
            p_keys_str = u','.join(p_keys)
            p_keys_str = u'  PRIMARY KEY ({})'.format(p_keys_str)
        else:
            p_keys_str = u''

        lines = ["CREATE TABLE IF NOT EXISTS `{}` (".format(self.table_name)]

        for k in sorted(fields.keys()):
            lines.append(u"  `{}` {} NOT NULL,".format(fields[k][u'c_field'], fields[k][u'c_type']))
        if p_keys_str != u'':
            lines.append(u"  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,")
            lines.append(p_keys_str)
        else:
            lines.append(u"  `UpdatedInDB` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP")
        lines.append(u");")

        return u'\n'.join(lines)

    def sql_build_ph(self, ofbx, replace=False):
        """Create sql INSERT or REPLACE with FbxObj properties"""
        str_replace = u'REPLACE' if replace else u'INSERT'
        field_names = self._get_dbfield_names_ordered()
        field_values = []
        field_phs = []
        fields = self._get_fields_ordered()
        for k in sorted(fields.keys()):
            if u'c_name' in fields[k]:
                f_from = u'c_name'
            else:
                f_from = u'c_field'

            field_phs.append(u'?')
            if fields[k][u'c_type'] in [u'int(11)']:
                field_values.append(u"{}".format(getattr(ofbx, fields[k][f_from], 0)))
            elif fields[k][u'c_type'] in [u'tinyint(1)']:
                value = 1 if getattr(ofbx, fields[k][f_from], 0) else 0
                field_values.append(u"{}".format(value))
            elif fields[k][u'c_type'] in [u'datetime']:
                value = getattr(ofbx, fields[k][f_from], None)
                if value is None:
                    value = u''
                else:
                    value = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S.%f')
                field_values.append(u"{}".format(value))
            else:
                field_values.append(u"{}".format(getattr(ofbx, fields[k][f_from], u'')))

        fields = u','.join(field_names)
        phs = u','.join(field_phs)
        # Table name not defined here, to be done by caller
        query = "%s INTO {} (%s) " % (str_replace, fields)
        query += "VALUES ({});".format(phs)
        # print(query, field_values)
        return (query, field_values)

    def sql_build(self, ofbx, replace=False):
        """Create sql INSERT or REPLACE with FbxObj properties"""
        str_replace = u'REPLACE' if replace else u'INSERT'
        field_names = self._get_dbfield_names_ordered()
        field_values = []
        fields = self._get_fields_ordered()
        for k in sorted(fields.keys()):
            if u'c_name' in fields[k]:
                f_from = u'c_name'
            else:
                f_from = u'c_field'

            if fields[k][u'c_type'] in [u'int(11)']:
                field_values.append(u"{}".format(getattr(ofbx, fields[k][f_from], 0)))
            elif fields[k][u'c_type'] in [u'tinyint(1)']:
                value = 1 if getattr(ofbx, fields[k][f_from], 0) else 0
                field_values.append(u"{}".format(value))
            elif fields[k][u'c_type'] in [u'datetime']:
                value = getattr(ofbx, fields[k][f_from], None)
                if value is None:
                    value = u''
                else:
                    value = datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S.%f')
                field_values.append(u"'{}'".format(value))
            else:
                field_values.append(u"'{}'".format(getattr(ofbx, fields[k][f_from], u'')))

        fields = u','.join(field_names)
        values = u','.join(field_values)
        # Table name not defined here, to be done by caller
        query = "%s INTO {} (%s) " % (str_replace, fields)
        values = "VALUES ({});".format(values)
        # print(query+values)
        return query+values

    def _sql_select(self):
        field_names = self._get_dbfield_names_ordered()
        fields = u','.join(field_names)
        query = u'SELECT %s FROM {};' % (fields)
        return query

    def _sql_build_cond(self, field_name, value):
        id_type = self._cols_def[field_name][u'c_type']
        if id_type in [u'int(11)']:
            cond = u"`{}` = {}".format(field_name, value)
        elif id_type in [u'tinyint(1)']:
            if id:
                cond = u"`{}` = 1".format(field_name, value)
            else:
                cond = u"`{}` = 0".format(field_name, value)
        else:
            cond = u"`{}` = '{}'".format(field_name, value)
        return cond

    def _sql_get_by_id(self, id):
        field_names = self._get_dbfield_names_ordered()
        fields = u','.join(field_names)
        cond = self._sql_build_cond(self._id_name, id)
        query = u'SELECT %s FROM {} WHERE %s;' % (fields, cond)
        return query

    def _sql_delete_by_id(self, id):
        cond = self._sql_build_cond(self._id_name, id)
        query = u'DELETE FROM {} WHERE %s;' % (cond)
        return query

    @property
    def table_name(self):
        return self._table_name

    @property
    def id_name(self):
        return self._id_name

    @property
    def cols_def(self):
        return self._cols_def

    @property
    def sql_table_create(self):
        return self._sql_build_table_create()

    @property
    def sql_select(self):
        return self._sql_select()

    @property
    def Tuple(self):
        return namedtuple(u'T'+self._table_name, self._get_field_names_ordered())


def main():

    db_file = u'fbxosctrl_.db'

    if os.path.exists(db_file):
        os.remove(db_file)

    cols_def_calls = {'id': {u'c_order': 0, u'c_type': u'int(11)', u'is_id': True},
                      'type': {u'c_order': 10, u'c_type': u'varchar(11)', u'c_name': u'status'},
                      'datetime': {u'c_order': 20, u'c_type': u'datetime', u'c_name': u'timestamp'},
                      'number': {u'c_order': 30, u'c_type': u'varchar(40)'},
                      'name': {u'c_order': 40, u'c_type': u'varchar(80)'},
                      'duration': {u'c_order': 50, u'c_type': u'int(11)'},
                      'new': {u'c_order': 60, u'c_type': u'tinyint(1)'},
                      'contact_id': {u'c_order': 70, u'c_type': u'int(11)'},
                      'src': {u'c_order': 80, u'c_type': u'varchar(40)'},
                      }

    cols_def_static_leases = {'id': {u'c_order': 0, u'c_type': u'varchar(17)', u'is_id': True},
                              'mac': {u'c_order': 10, u'c_type': u'varchar(17)'},
                              'comment': {u'c_order': 20, u'c_type': u'varchar(40)'},
                              'hostname': {u'c_order': 30, u'c_type': u'varchar(40)'},
                              'ip': {u'c_order': 40, u'c_type': u'varchar(27)'},
                              'last_activity': {u'c_order': 50, u'c_type': u'datetime'},
                              'last_time_reachable': {u'c_order': 60, u'c_type': u'datetime'},
                              'src': {u'c_order': 70, u'c_type': u'varchar(40)'},
                              }

    cols_def_dynatic_leases = {'mac': {u'c_order': 0, u'c_type': u'varchar(17)', u'is_id': True},
                               'hostname': {u'c_order': 10, u'c_type': u'varchar(40)'},
                               'ip': {u'c_order': 20, u'c_type': u'varchar(27)'},
                               'lease_remaining': {u'c_order': 30, u'c_type': u'int(11)'},
                               'assign_time': {u'c_order': 40, u'c_type': u'datetime'},
                               'refresh_time': {u'c_order': 50, u'c_type': u'datetime'},
                               'is_static': {u'c_order': 60, u'c_type': u'tinyint(1)'},
                               'comment': {u'c_order': 70, u'c_type': u'varchar(40)'},
                               'src': {u'c_order': 80, u'c_type': u'varchar(40)'},
                               }

    cols_def_fw_redir = {'id': {u'c_order': 0, u'c_type': u'int(11)'},
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

    db = FbxDbLite(db_file)

    t_calls = FbxDbTable(u'calls', u'id', cols_def_calls)
    log(t_calls.sql_table_create)
    log(t_calls.sql_select)

    O_call = t_calls.Tuple
    call = O_call(9999, 'in', datetime.now().timestamp(), '0144444444', 'John', 3600, True, 25, 'Test')
    log(t_calls.sql_build(call, replace=True))

    log(t_calls._sql_get_by_id(9999))
    log(t_calls._sql_delete_by_id(9999))

    t_static_leases = FbxDbTable(u'static_leases', u'id', cols_def_static_leases)
    t_dynamic_leases = FbxDbTable(u'dynamic_leases', u'mac', cols_def_dynatic_leases)
    t_fw_redir = FbxDbTable(u'fw_redir', u'id', cols_def_fw_redir)
    db.add_table(t_calls)
    db.add_table(t_static_leases)
    db.add_table(t_dynamic_leases)
    db.add_table(t_fw_redir)
    db.init_base()

    db.query_update(t_calls, t_calls.sql_build(call, replace=True))

    def process_row(self, row):
        log(u"-> row[u'id']: {}".format(row[u'id']))

    rows = db.query_select(t_calls, t_calls.sql_select, process_row=process_row)
    rows = db.query_select(t_calls, t_calls.sql_select)
    log(u'->{}\n->{}'.format(call, rows[0]))
    assert str(rows[0]) == str(call), u'Write db failed'
    log(t_calls._sql_get_by_id(9999))
    db.query_update(t_calls, t_calls._sql_delete_by_id(9999))
    rows = db.query_select(t_calls, t_calls.sql_select)
    assert len(rows) == 0, u'Delete from table failed'

    print(u'Seems to be ok')

    return 0


if __name__ == '__main__':

    sys.exit(main())
