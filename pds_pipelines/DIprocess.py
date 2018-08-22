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
from pds_pipelines.config import pds_db, pds_log
from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files

import pdb


def main():
    # pdb.set_trace()

    # @TODO can these be pulled from DB? any reason to hard code?
    archiveID = {53: '/pds_san/PDS_Archive/Cassini/ISS/',
                 51: '/pds_san/PDS_Archive/Cassini/RADAR/',
                 75: '/pds_san/PDS_Archive/Cassini/VIMS/',
                 97: '/pds_san/PDS_Archive/Apollo/Metric_Camera/',
                 101: '/pds_san/PDS_Archive/Apollo/Rock_Sample_Images/',
                 50: '/pds_san/PDS_Archive/Clementine/',
                 104: '/pds_san/PDS_Archive/Chandrayaan_1/M3/',
                 119: '/pds_san/PDS_Archive/Dawn/Vesta/',
                 123: '/psa_san/PDS_Archive/Dawn/Ceres/',
                 24: '/pds_san/PDS_Archive/Galileo/NIMS/',
                 25: '/pds_san/PDS_Archive/Galileo/SSI/',
                 92: '/pds_san/PDS_Safed/Data/Kaguya/LISM/',
                 38: '/pds_san/PDS_Archive/LCROSS/',
                 79: '/pds_san/PDS_Archive/Lunar_Orbiter/',
                 116: '/pds_san/PDS_Archive/Mars_Odyssey/THEMIS/USA_NASA_PDS_ODTSDP_100XX/',
                 117: '/pds_san/PDS_Archive/Mars_Odyssey/THEMIS/USA_NASA_PDS_ODTSDP_100XX/',
                 118: '/pds_san/PDS_Archive/Mars_Odyssey/THEMIS/USA_NASA_PDS_ODTGEO_200XX/',
                 41: '/pds_san/PDS_Derived/Map_A_Planet/',
                 44: '/pds_san/PDS_Archive/Mars_Global_Surveyor/MOC/',
                 16: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/CTX/',
                 17: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/MARCI/',
                 74: '/pds_san/PDS_Archive/Lunar_Reconnaissance_Orbiter/LROC/EDR/',
                 84: '/pds_san/PDS_Archive/Lunar_Reconnaissance_Orbiter/LAMP/',
                 71: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/HiRISE/',
                 124: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/HiRISE/',
                 125: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/HiRISE/',
                 126: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/HiRISE/',
                 46: '/pds_san/PDS_Archive/Mariner_10/',
                 27: '/pds_san/PDS_Archive/Magellan/',
                 78: '/pds_san/PDS_Archive/Mars_Express/',
                 18: '/pds_san/PDS_Archive/Mars_Pathfinder/',
                 14: '/pds_san/PDS_Archive/MESSENGER/',
                 9: '/pds_san/PDS_Archive/Phoenix/',
                 7: '/pds_san/PDS_Archive/Viking_Lander/',
                 3: '/pds_san/PDS_Archive/Viking_Orbiter/',
                 30: '/pds_san/PDS_Archive/Voyager/'
                 }

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
        inputfile = RQ.QueueGet().decode('utf-8')
        try:
            Qelement = session.query(Files).filter(
                Files.filename == inputfile).one()
        except:
            logger.error('Query for File: %s', inputfile)

        cpfile = archiveID[Qelement.archiveid] + Qelement.filename
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
