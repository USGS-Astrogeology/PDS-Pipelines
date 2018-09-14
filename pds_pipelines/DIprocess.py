#!/usr/bin/env python

import os
import sys
import datetime
import pytz
import logging
import hashlib
import json
from ast import literal_eval

from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.PDS_DBquery import *

from sqlalchemy import *
from sqlalchemy.orm.util import *
from pds_pipelines.config import pds_db, pds_log, pds_info
from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files


def main():
    # pdb.set_trace()

    PDSinfoDICT = json.load(open(pds_info, 'r'))

# ********* Set up logging *************
    logger = logging.getLogger('DI_Process')
    logger.setLevel(logging.INFO)
    #logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/DI.log')
    logFileHandle = logging.FileHandler(pds_log + 'DI.log')
    #logFileHandle = logging.FileHandler('/home/arsanders/PDS-Pipelines/logs/DI.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info('Starting DI Process')

    try:
        # ignores engine information
        session, _ = db_connect(pds_db)
        logger.info('DataBase Connecton: Success')
    except:
        logger.error('DataBase Connection: Error')

    RQ = RedisQueue('DI_ReadyQueue')
    index = 0

    while int(RQ.QueueSize()) > 0:
        item = literal_eval(RQ.QueueGet().decode("utf-8"))
        inputfile = item[0]
        archive = item[1]
        try:
            Qelement = session.query(Files).filter(
                Files.filename == inputfile).one()
        except:
            logger.error('Query for File: %s', inputfile)

        archive_path = PDSinfoDICT[archive]['path']

        cpfile = archive_path + Qelement.filename
        if os.path.isfile(cpfile):
            f_hash = hashlib.md5()
            with open(cpfile, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    f_hash.update(chunk)
            checksum = f_hash.hexdigest()

            if checksum == Qelement.checksum:
                Qelement.di_pass = True
            else:
                Qelement.di_pass = False
            Qelement.di_date = datetime.datetime.now(
                pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
            session.flush()
            index = index + 1
            if index > 50:
                session.commit()
                logger.info('Session Commit for 50 Records: Success')
                index = 0
        else:
            logger.error('File %s Not Found', cpfile)
    try:
        session.commit()
        logger.info("End Commit DI process to Database: Success")
        index = 1
    except:
        session.rollback()


if __name__ == "__main__":
    sys.exit(main())
