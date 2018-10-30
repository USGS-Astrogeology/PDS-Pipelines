#!/usr/bin/env python

import sys
import datetime
import logging
import argparse
import json
import pytz

from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files
from pds_pipelines.config import pds_info, pds_db, pds_log
from sqlalchemy import Date, cast
from sqlalchemy.orm.util import *
from sqlalchemy import or_


class Args(object):
    """
    Objects that have the attributes described below

    Attributes
    ----------
    archive : str
    volume : str
    jobarray : str
    """
    def __init__(self):
        pass

    def parse_args(self):
        """
        Defines how to parse command-line arguments

        Parameters
        ----------
        name : str
              name of argument

        dest : str
            Name of attribute to be added to parser

        required : str
            Makes optional arguments required

        help : _helper
            Contains brief description of argument

        Returns
        -------
        Namespace
            args
        """

        parser = argparse.ArgumentParser(description='PDS DI Data Integrity')

        parser.add_argument('--archive', '-a', dest="archive", required=True,
                            help="Enter archive - archive to ingest")

        parser.add_argument('--volume', '-v', dest="volume",
                            help="Enter volume to Ingest")

        parser.add_argument('--jobarray', '-j', dest="jobarray",
                            help="Enter string to set job array size")

        parser.add_argument('--log', '-l', dest="log_level",
                            choice=['DEBUG', 'INFO',
                                    'WARNING', 'ERROR', 'CRITICAL'],
                            help="Set the log level.", default='INFO')

        args = parser.parse_args()

        self.archive = args.archive
        self.volume = args.volume
        self.jobarray = args.jobarray
        self.log_level = args.log_level

def main():
    args = Args()
    args.parse_args()

    RQ = RedisQueue('DI_ReadyQueue')

    PDSinfoDICT = json.load(open(pds_info, 'r'))
    try:
        archiveID = PDSinfoDICT[args.archive]['archiveid']
    except KeyError:
        print("\nArchive '{}' not found in {}\n".format(args.archive, pds_info))
        print("The following archives are available:")
        for k in PDSinfoDICT.keys():
            print("\t{}".format(k))
        exit()

    logger = logging.getLogger('DI_Queueing.' + args.archive)
    level = logging.getLevelName(args.log_level)
    logger.setLevel(level)
    logFileHandle = logging.FileHandler(pds_log + 'DI.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info("DI Queue: %s", RQ.id_name)
    
    logger.info('Starting %s DI Queueing', args.archive)
    if args.volume:
        logger.info('Queueing %s Volume', args.volume)

    try:
        session, _ = db_connect(pds_db)
        logger.info('DataBase Connecton: Success')
    except:
        logger.error('DataBase Connection: Error')
        return 1

    td = (datetime.datetime.now(pytz.utc) -
          datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    testing_date = datetime.datetime.strptime(str(td), "%Y-%m-%d %H:%M:%S")

    if args.volume:
        volstr = '%' + args.volume + '%'
        testQ = session.query(Files).filter(
            Files.archiveid == archiveID, Files.filename.like(volstr)).filter(
                or_(cast(Files.di_date, Date) < testing_date,
                    cast(Files.di_date, Date) is None))
    else:
        testQ = session.query(Files).filter(Files.archiveid == archiveID).filter(
            or_(cast(Files.di_date, Date) < testing_date,
                cast(Files.di_date, Date) is None))

    addcount = 0
    for element in testQ:
        try:
            RQ.QueueAdd((element.filename, args.archive))
            addcount = addcount + 1
        except:
            logger.warn('File %s Not Added to DI_ReadyQueue',
                         element.filename)

    logger.info('Files Added to Queue %s', addcount)
    logger.info('DI Queueing Complete')


if __name__ == "__main__":
    sys.exit(main())
