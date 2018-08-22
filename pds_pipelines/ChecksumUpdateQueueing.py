#!/usgs/apps/anaconda/bin/python

import os
import sys
import subprocess
import datetime
import pytz

import logging
import argparse

from pds_pipelines.RedisQueue import *
from pds_pipelines.HPCjob import *

import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm.util import *
from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files
from pds_pipelines.config import pds_db

import pdb


class Args:
    """    
    Attributes
    ----------
    archive
    volume
    """
    def __init__(self):
        pass

    def parse_args(self):

        parser = argparse.ArgumentParser(description='PDS DI Data Integrity')

        parser.add_argument('--archive', '-a', dest="archive", required=True,
                            help="Enter archive - archive to ingest")

        parser.add_argument('--volume', '-v', dest="volume",
                            help="Enter volume to Ingest")

        args = parser.parse_args()

        self.archive = args.archive
        self.volume = args.volume


def main():

    #    pdb.set_trace()

    args = Args()
    args.parse_args()

    RQ = RedisQueue('ChecksumUpdate_Queue')

    archiveDICT = {'cassiniISS': '/pds_san/PDS_Archive/Cassini/ISS',
                   'mroCTX': '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/CTX',
                   'mroHIRISE': '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/HiRISE',
                   'LROLRC_EDR': '/pds_san/PDS_Archive/Lunar_Reconnaissance_Orbiter/LROC/EDR/'
                   }

    archiveID = {'cassiniISS': 'cassini_iss_edr',
                 'mroCTX': 16,
                 'mroHIRISE_EDR': '124',
                 'LROLRC_EDR': 74
                 }


# ********* Set up logging *************
    logger = logging.getLogger('ChecksumUpdate_Queueing.' + args.archive)
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/DI.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info('Starting %s Checksum update Queueing', args.archive)
    if args.volume:
        logger.info('Queueing %s Volume', args.volume)

    try:
        # Throws away engine information
        session, _ = db_connect(pds_db)
        logger.info('DataBase Connecton: Success')
    except:
        logger.error('DataBase Connection: Error')
        return 1

    if args.volume:
        volstr = '%' + args.volume + '%'
        QueryOBJ = session.query(Files).filter(
            Files.archiveid == archiveID[args.archive], Files.filename.like(volstr))
    else:
        QueryOBJ = session.query(Files).filter(
            Files.archiveid == archiveID[args.archive])
    addcount = 0
    for element in QueryOBJ:
        try:
            RQ.QueueAdd(element.filename)
            addcount = addcount + 1
        except:
            logger.error('File %s Not Added to DI_ReadyQueue',
                         element.filename)

    logger.info('Files Added to Queue %s', addcount)

    logger.info('DI Queueing Complete')


if __name__ == "__main__":
    sys.exit(main())
