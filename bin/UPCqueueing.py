#!/usgs/apps/anaconda/bin/python

import os
import sys
import subprocess
import logging
import argparse
import json


import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import mapper
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm.util import *
from sqlalchemy.ext.declarative import declarative_base


from RedisQueue import *

import pdb
from config import *


class Args:
    def __init__(self):
        pass

    def parse_args(self):

        parser = argparse.ArgumentParser(description='PDS DI Data Integrity')

        parser.add_argument('--archive', '-a', dest="archive", required=True,
                            help="Enter archive - archive to ingest")

        parser.add_argument('--volume', '-v', dest="volume",
                            help="Enter voluem to Ingest")

        parser.add_argument('--search', '-s', dest="search",
                            help="Enter string to search for")

        args = parser.parse_args()

        self.archive = args.archive
        self.volume = args.volume
        self.search = args.search


def main():

    #    pdb.set_trace()
    args = Args()
    args.parse_args()

    logger = logging.getLogger('UPC_Queueing.' + args.archive)
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Process.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info('Starting Process')

    PDSinfoDICT = json.load(open('/usgs/cdev/PDS/bin/PDSinfo.json', 'r'))
    archiveID = PDSinfoDICT[args.archive]['archiveid']

    RQ = RedisQueue('UPC_ReadyQueue')

    try:
        engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format(pdsdi_user,
                                                                    pdsdi_pass,
                                                                    pdsdi_host,
                                                                    pdsdi_port,
                                                                    pdsdi_db))

        metadata = MetaData(bind=engine)
        files = Table('files', metadata, autoload=True)

        class Files(object):
            pass

        filesmapper = mapper(Files, files)
        Session = sessionmaker()
        DBsession = Session()
        print 'Database Connection Success'
    except:
        print 'Database Connection Error'

    if args.volume:
        volstr = '%' + args.volume + '%'

        Qnum = DBsession.query(Files).filter(files.c.archiveid == archiveID,
                                             files.c.filename.like(volstr),
                                             files.c.upc_required == 't').count()

        if Qnum > 0:
            print "We have files for UPC"

            qOBJ = DBsession.query(Files).filter(files.c.archiveid == archiveID,
                                                 files.c.filename.like(volstr),
                                                 files.c.upc_required == 't')
        else:
            print "No UPC files found"

    else:
        qOBJ = DBsession.query(Files).filter(files.c.archiveid == archiveid,
                                             files.c.upc_required == 't')
    if qOBJ:
        addcount = 0
        for element in qOBJ:
            Qfile = PDSinfoDICT[args.archive]['path'] + element.filename
            RQ.QueueAdd(Qfile)
            addcount = addcount + 1

        logger.info('Files Added to UPC Queue: %s', addcount)

    print "Done"


if __name__ == "__main__":
    sys.exit(main())
