#!/usgs/apps/anaconda/bin/python

import os
import sys
import subprocess
import datetime
import pytz

import logging
import argparse
import json

from pds_pipelines.RedisQueue import *
from pds_pipelines.HPCjob import *
from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files
from pds_pipelines.config import pds_info, pds_db, pds_log

from sqlalchemy import Date, cast

import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm.util import *

from sqlalchemy import or_

import pdb


class Args:
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

        args = parser.parse_args()

        self.archive = args.archive
        self.volume = args.volume
        self.jobarray = args.jobarray

def main():


    #pdb.set_trace()

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

# ********* Set up logging *************
    logger = logging.getLogger('DI_Queueing.' + args.archive)
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler(pds_log + 'DI.log')
    #logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/DI.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info('Starting %s DI Queueing', args.archive)
    if args.volume:
        logger.info('Queueing %s Volume', args.volume)

    try:
        # @TODO switch back to prd
        session, _ = db_connect(pds_db)

        logger.info('DataBase Connecton: Success')
    except:
        logger.error('DataBase Connection: Error')

# ************* date stuff ***************

    td = (datetime.datetime.now(pytz.utc) -
          datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    testing_date = datetime.datetime.strptime(str(td), "%Y-%m-%d %H:%M:%S")

    if args.volume:
        volstr = '%' + args.volume + '%'

        testcount = session.query(Files).filter(
            Files.archiveid == archiveID, Files.filename.like(volstr)).filter(
                or_(cast(Files.di_date, Date) < testing_date,
                    cast(Files.di_date, Date) == None)).count()
#        logger.info('Query Count %s', testcount)
        testQ = session.query(Files).filter(
            Files.archiveid == archiveID, Files.filename.like(volstr)).filter(
                or_(cast(Files.di_date, Date) < testing_date,
                    cast(Files.di_date, Date) == None))
    else:
        testcount = session.query(Files).filter(Files.archiveid == archiveID).filter(
            or_(cast(Files.di_date, Date) < testing_date,
                cast(Files.di_date, Date) == None)).count()
        testQ = session.query(Files).filter(Files.archiveid == archiveID).filter(
            or_(cast(Files.di_date, Date) < testing_date,
                cast(Files.di_date, Date) == None))

    addcount = 0
    for element in testQ:
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
