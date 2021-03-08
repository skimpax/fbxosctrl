#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os
import sys
import json
from pathlib import Path
import logging
import logging.handlers
import queue
import argparse
import mysql.connector
from mysql.connector import errorcode
from fbxostools.fbxosbase import FreeboxOSCtrlBase
from fbxostools.fbxosobj import FbxDhcpDynamicLeases

pgm_version = u'20190429_1332'

__author__ = "Alain Ferraro (aka afer92)"
__copyright__ = "Copyright 2019, Alain Ferraro"
__credits__ = []
__license__ = "GPL"
__version__ = pgm_version
__maintainer__ = "afer92"
__email__ = ""
__status__ = "Production"

DEBUG = 0
DEVEL = 0

home = str(Path.home())
hostname = os.uname()[1]
mod_path = sys.modules['__main__'].__file__
mod_name = os.path.basename(mod_path).split(u'.')[0]


if DEVEL:
    trtlog = u'/opt/af/log/%s.log' % (mod_name)
    dbfile = u'/opt/af/params/fbxosctrl.db'
    params = u'/opt/af/params/freebox'
else:
    trtlog = u'/opt/pi/log/%s.log' % (mod_name)
    dbfile = u'/opt/pi/params/fbxosctrl.db'
    params = u'/opt/pi/params/freebox'

# get mysql connection params

sqlparams = params + '/dbsqlparams.json'
fp = open(sqlparams)
sqlpc = json.load(fp)
fp.close()

if DEBUG:
    print(u'libpath: {}\ntrtlog: {}\ndbfile: {}\nparams{}'.format(libpath,
          trtlog, dbfile, params))
    print(sys.path)


class MyLogger(object):

    def __init__(self, handler, name, level=logging.WARNING):
        self.que = queue.Queue(-1)  # no limit on size
        self.queue_handler = logging.handlers.QueueHandler(self.que)
        self.handler = handler
        self.listener = logging.handlers.QueueListener(self.que, self.handler)
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.addHandler(self.queue_handler)
        strformat = '%(asctime)s : %(threadName)s/%(name)-12s %(levelname)-8s %(message)s'
        self.formatter = logging.Formatter(strformat, datefmt='%d/%m/%Y %H:%M:%S')
        self.handler.setFormatter(self.formatter)


logLevel = logging.INFO
logfile = logging.handlers.TimedRotatingFileHandler(trtlog, when='D',
                                                    interval=1,
                                                    backupCount=7,
                                                    delay=True)
logger = MyLogger(logfile, mod_name, level=logLevel)
log = logger.logger


def get_cursor(sqlpc):
    try:
        cnx = mysql.connector.connect(user=sqlpc['user'],
                                      password=sqlpc['password'],
                                      host=sqlpc['host'],
                                      database=sqlpc['database'])
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)
        return (0, 0)
    else:
        cursor = cnx.cursor()
    return (cnx, cursor)


def db_update(sqlpc, query):
    (cnx, cursor) = get_cursor(sqlpc)
    cursor.execute(query)
    cnx.commit()
    cnx.close()


def main():
    #
    # parse arguments
    #
    loglevel = logging.INFO
    parser = argparse.ArgumentParser(description='Test module hwgsmapi.')
    parser.add_argument(u'--debug', u'-d', help='Logging debug',
                        action="store_true")
    parser.add_argument(u'--warning', u'-w', help='Logging warning',
                        action="store_true")
    parser.add_argument(u'--critical', u'-c', help='Logging critical',
                        action="store_true")
    parser.add_argument(u'--update_db', u'-u', help='Update db',
                        action="store_true")
    parser.add_argument(u'--quiet', u'-q', help='Quiet',
                        action="store_true")
    parser.add_argument(u'--save', u'-s', help='Save archive',
                        action="store_true")
    parser.add_argument(u'--verbose', u'-v', help='Verbose',
                        action="store_true")
    args = parser.parse_args()

    if args.debug:
        loglevel = logging.DEBUG
    if args.warning:
        loglevel = logging.WARNING
    if args.critical:
        loglevel = logging.CRITICAL

    # go

    log.setLevel(loglevel)
    log.addHandler(logging.StreamHandler())
    logger.listener.start()
    log.info(u'Start')

    ctrl = FreeboxOSCtrlBase()
    ctrl.conf.conf_path = params
    ctrl.conf.load(False)

    nbupdated = 0
    nbignored = 0
    nbleases = 0

    # FbxDhcpDynamicLease

    leases = FbxDhcpDynamicLeases(ctrl)
    if args.quiet is False:
        print(u'\nLeases from freebox:')
    for lease in leases:
        nbleases += 1
        query = lease.sql_replace.replace(u'`dynamic_lease`',
                                          u'`FREEBOX_NEW`.`dynamic_lease`')
        log.info(query)
        db_update(sqlpc, query)
        nbupdated += 1
        if args.quiet is False:
            print(lease)

    if args.save:
        leases.save_to_db()

    if args.verbose:
        print(u'%3d lease(s)' % (nbleases))
        print(u'%3d record(s) updated' % (nbupdated))
        print(u'%3d record(s) skipped' % (nbignored))

    log.info(u'%3d lease(s)' % (nbleases))
    log.info(u'%3d record(s) updated' % (nbupdated))
    log.info(u'%3d record(s) skipped' % (nbignored))

    log.info(u'Stop')

    return 0


if __name__ == '__main__':
    rc = main()
    exit(rc)
