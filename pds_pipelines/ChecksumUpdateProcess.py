#!/usgs/apps/anaconda/bin/python

import os
import sys
import datetime
import pytz
import logging
import hashlib
import shutil

from pds_pipelines.RedisQueue import *
from pds_pipelines.PDS_DBquery import *

import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm.util import *

import pdb
from pds_pipelines.db import db_connect
from pds_pipelines.config import pds_db
from pds_pipelines.models.pds_models import Files


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

            """
            CScmd = 'md5sum ' + cpfile
            process = subprocess.Popen(
                CScmd, stdout=subprocess.PIPE, shell=True)
            (stdout, stderr) = process.communicate()
            temp_checksum = stdout.split()[0]

#             temp_checksum = hashlib.md5(open(tempfile, 'rb').read()).hexdigest()
#             os.remove(tempfile)
            """

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
        logger.error('Error durint commit')
    logger.info("End Commit DI process to Database: Success")
    logger.info('Checksum for %s Files Updated', str(index))


if __name__ == "__main__":
    sys.exit(main())
