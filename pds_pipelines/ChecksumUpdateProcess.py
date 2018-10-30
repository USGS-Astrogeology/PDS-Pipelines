#!/usr/bin/env python

import os
import sys
import datetime
import pytz
import logging
import hashlib
import argparse

from pds_pipelines.RedisQueue import RedisQueue

from sqlalchemy import *
from sqlalchemy.orm.util import *

from pds_pipelines.db import db_connect
from pds_pipelines.config import pds_db, pds_log
from pds_pipelines.models.pds_models import Files


class Args:
    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser(description="DI Process")

        parser.add_argument('--log', '-l', dest="log_level",
                            choice=['DEBUG', 'INFO',
                                    'WARNING', 'ERROR', 'CRITICAL'],
                            help="Set the log level.", default='INFO')
        args = parser.parse_args()
        self.log_level = args.log_level

def main():
    #    pdb.set_trace()

    archiveID = {16: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/CTX/',
                 74: '/pds_san/PDS_Archive/Lunar_Reconnaissance_Orbiter/LROC/EDR/',
                 124: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/HiRISE/',
                 101: '/pds_san/PDS_Archive/Apollo/Rock_Sample_Images/'
                 }

    args = Args()
    args.parse_args()

    logger = logging.getLogger('DI_Process')
    level = argparse.getLevelName(args.log_level)
    logger.setLevel(level)
    logFileHandle = logging.FileHandler(pds_log + 'DI.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info('Starting DI Process')

    try:
        # Throws away engine information
        session, _ = db_connect(pds_db)
        logger.info('DataBase Connecton: Success')
    except:
        logger.error('DataBase Connection: Error')
        return 1
    RQ = RedisQueue('ChecksumUpdate_Queue')
    index = 0
    count = 0

    while int(RQ.QueueSize()) > 0:
        inputfile = RQ.QueueGet()
        Qelement = session.query(Files).filter(
            Files.filename == inputfile).one()
        cpfile = archiveID[Qelement.archiveid] + Qelement.filename
        if os.path.isfile(cpfile):
            # Calculate checksum in chunks of 4096
            f_hash = hashlib.md5()
            with open(cpfile, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    f_hash.update(chunk)
            checksum = f_hash.hexdigest()

            if checksum != Qelement.checksum:
                Qelement.checksum = checksum
                Qelement.di_pass = 't'
                Qelement.di_date = datetime.datetime.now(
                    pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
                session.flush()
                index = index + 1
                count = count + 1
                logger.info('Update Checksum %s: Success', inputfile)

            if count > 25:
                session.commit()
                logger.info('Session Commit for 25 Records: Success')
                count = 0

        else:
            logger.error('File %s Not Found', cpfile)

    try:
        session.commit()
    except:
        session.rollback()
        logger.error('Error during commit')
    logger.info("End Commit DI process to Database: Success")
    logger.info('Checksum for %s Files Updated', str(index))


if __name__ == "__main__":
    sys.exit(main())
