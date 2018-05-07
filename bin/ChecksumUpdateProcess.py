#!/usgs/apps/anaconda/bin/python

import os
import sys
import subprocess
import datetime
import pytz
import logging
import hashlib
import shutil

from RedisQueue import *
from PDS_DBquery import *

import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import mapper
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm.util import *
from sqlalchemy.ext.declarative import declarative_base


import pdb
from db import Files, db_connect


def main():
    #    pdb.set_trace()

    archiveID = {16: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/CTX/',
                 74: '/pds_san/PDS_Archive/Lunar_Reconnaissance_Orbiter/LROC/EDR/',
                 124: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/HiRISE/',
                 101: '/pds_san/PDS_Archive/Apollo/Rock_Sample_Images/'
                 }

# ********* Set up logging *************
    logger = logging.getLogger('DI_Process')
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/DI.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info('Starting DI Process')

    try:
        # Throws away archive and engine information
        session, files, _, _ = db_connect('pdsdi')
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
            files.c.filename == inputfile).one()
        cpfile = archiveID[Qelement.archiveid] + Qelement.filename
        if os.path.isfile(cpfile):

            CScmd = 'md5sum ' + cpfile
            process = subprocess.Popen(
                CScmd, stdout=subprocess.PIPE, shell=True)
            (stdout, stderr) = process.communicate()
            temp_checksum = stdout.split()[0]

#             temp_checksum = hashlib.md5(open(tempfile, 'rb').read()).hexdigest()
#             os.remove(tempfile)

            if temp_checksum != Qelement.checksum:
                Qelement.checksum = temp_checksum
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
        logger.error('Error durint commit')
    logger.info("End Commit DI process to Database: Success")
    logger.info('Checksum for %s Files Updated', str(index))


if __name__ == "__main__":
    sys.exit(main())
