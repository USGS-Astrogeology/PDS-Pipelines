#!/usgs/apps/anaconda/bin/python
import os
import sys
import subprocess
import datetime
import pytz
import logging
import json
from RedisQueue import *
from PDS_DBquery import *

import hashlib
import shutil

import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import mapper
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm.util import *
from sqlalchemy.ext.declarative import declarative_base


import pdb


def getArchiveID(inputfile):
    """
    Parameters
    ----------
    inputfile : str

    Returns
    -------
    str
        archive
    """
    if 'Mars_Reconnaissance_Orbiter/CTX' in inputfile:
        archive = 'mroCTX'
    elif 'Mars_Reconnaissance_Orbiter/MARCI' in inputfile:
        archive = 'mroMARCI'
    elif 'Cassini/RADAR' in inputfile:
        archive = 'cassiniRADAR'
    elif 'Cassini/ISS' in inputfile:
        archive = 'cassiniISS'
    elif 'Cassini/VIMS' in inputfile:
        archive = 'cassiniVIMS'
    elif 'Dawn/Vesta' in inputfile:
        archive = 'dawnVesta'
    elif 'Dawn/Ceres' in inputfile:
        archive = 'dawnCeres'
    elif 'MESSENGER' in inputfile:
        archive = 'messenger'
    elif 'THEMIS/USA_NASA_PDS_ODTSDP_100XX' in inputfile:
        if 'odtvb1' in inputfile or 'odtve1' in inputfile or 'odtvr1' in inputfile:
            archive = 'themisVIS_EDR'
        else:
            archive = 'themisIR_EDR'
    elif 'USA_NASA_PDS_ODTGEO_200XX' in inputfile:
        archive = 'themisGEO'
    elif 'Lunar_Reconnaissance_Orbiter/LROC/EDR' in inputfile:
        archive = 'lrolrcEDR'
    elif 'Lunar_Reconnaissance_Orbiter/LAMP' in inputfile:
        archive = 'lroLAMP'
    elif 'Lunar_Orbiter' in inputfile:
        archive = 'lunarOrbiter'
    elif 'Mars_Reconnaissance_Orbiter/HiRISE' in inputfile:
        if 'HiRISE/EDR/' in inputfile:
            archive = 'mroHIRISE_EDR'
        elif 'HiRISE/RDR/' in inputfile:
            archive = 'mroHIRISE_RDR'
        elif 'HiRISE/EXTRAS/' in inputfile:
            archive = 'mroHIRISE_EXTRAS'
        else:
            archive = 'mroHIRISE'
    elif 'Apollo/Rock_Sample_Images' in inputfile:
        archive = 'apolloRock'

    return archive


def main():

    #    pdb.set_trace()

    arch = sys.argv[-1]

# ********* Set up logging *************
    logger = logging.getLogger('Ingest_Process')
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Ingest.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info("Starting Process")
    PDSinfoDICT = json.load(open('/usgs/cdev/PDS/bin/PDSinfo.json', 'r'))

    RQ_main = RedisQueue('Ingest_ReadyQueue')
    RQ_work = RedisQueue('Ingest_WorkQueue')

    RQ_upc = RedisQueue('UPC_ReadyQueue')
    RQ_thumb = RedisQueue('Thumbnail_ReadyQueue')
    RQ_browse = RedisQueue('Browse_ReadyQueue')
    RQ_pilotB = RedisQueue('PilotB_ReadyQueue')

    try:
        engine = create_engine('postgresql://pdsdi:dataInt@dino.wr.usgs.gov:3309/pds_di_prd')
        metadata = MetaData(bind=engine)
        files = Table('files', metadata, autoload=True)
        archives = Table('archives', metadata, autoload=True)

        class Files(object):
            pass
        class Archives(object):
            pass

        filesmapper = mapper(Files, files)
        archivesmapper = mapper(Archives, archives)
        Session = sessionmaker()
        session = Session()
        logger.info('DataBase Connecton: Success')
    except:
        logger.error('DataBase Connection: Error')

    index = 1

    while int(RQ_main.QueueSize()) > 0:

        inputfile = RQ_main.Qfile2Qwork(
            RQ_main.getQueueName(), RQ_work.getQueueName())
        archive = getArchiveID(inputfile)
        subfile = inputfile.replace(PDSinfoDICT[archive]['path'], '')

# Gen a checksum from input file
        CScmd = 'md5sum ' + inputfile
        process = subprocess.Popen(CScmd, stdout=subprocess.PIPE, shell=True)
        (stdout, stderr) = process.communicate()
        filechecksum = stdout.split()[0]

        QOBJ = session.query(Files).filter_by(filename=subfile).first()

        runflag = 'false'
        if QOBJ is None:
            runflag = 'true'
        elif filechecksum != QOBJ.checksum:
            runflag = 'true'

        if runflag == 'true':
            date = datetime.datetime.now(
                pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
            fileURL = inputfile.replace(
                '/pds_san/PDS_Archive/', 'pdsimage.wr.usgs.gov/Missions/')
            upcflag = 'f'
            if int(PDSinfoDICT[archive]['archiveid']) == 124:
                if '.IMG' in inputfile:
                    upcflag = 't'
            elif int(PDSinfoDICT[archive]['archiveid']) == 74:
                if '/DATA/' in inputfile and '/NAC/' in inputfile and '.IMG' in inputfile:
                    upcflag = 't'
            elif int(PDSinfoDICT[archive]['archiveid']) == 16:
                if '/data/' in inputfile and '.IMG' in inputfile:
                    upcflag = 't'
            elif int(PDSinfoDICT[archive]['archiveid']) == 53:
                if '/data/' in inputfile and '.LBL' in inputfile:
                    upcflag = 't'
            elif int(PDSinfoDICT[archive]['archiveid']) == 116:
                if '/data/odtie1' in inputfile and '.QUB' in inputfile:
                    upcflag = 't'
            elif int(PDSinfoDICT[archive]['archiveid']) == 117:
                if '/data/odtve1' in inputfile and '.QUB' in inputfile:
                    upcflag = 't'

            if upcflag == 't':
                RQ_upc.QueueAdd(inputfile)
                RQ_thumb.QueueAdd(inputfile)
                RQ_browse.QueueAdd(inputfile)
                RQ_pilotB.QueueAdd(inputfile)

            filesize = os.path.getsize(inputfile)

            try:
                testIN = Files()
                testIN.archiveid = PDSinfoDICT[archive]['archiveid']
                testIN.filename = subfile
                testIN.entry_date = date
                testIN.checksum = filechecksum
                testIN.upc_required = upcflag
                testIN.validation_required = 't'
                testIN.header_only = 'f'
                testIN.release_date = date
                testIN.file_url = fileURL
                testIN.file_size = filesize
                testIN.di_pass = 't'
                testIN.di_date = date

                session.add(testIN)
                session.flush()

                RQ_work.QueueRemove(inputfile)

                index = index + 1

            except:
                logger.error("Error During File Insert %s", subfile)

        elif runflag == 'false':
            RQ_work.QueueRemove(inputfile)

        if index >= 250:
            try:
                session.commit()
#                logger.info("Commit 250 files to Database: Success")
                index = 1
            except:
                session.rollback()
                logger.error("Something Went Wrong During DB Insert")
    else:
        logger.info("No Files Found in Inget Queue")
        try:
            session.commit()
            logger.info("Commit to Database: Success")
        except:
            session.rollback()

    if RQ_main.QueueSize() == 0 and RQ_work.QueueSize() == 0:
        logger.info("Process Complete All Queues Empty")
    elif RQ_main.QueueSize() == 0 and RQ_work.QueueSize() != 0:
        logger.warning("Process Done Work Queue NOT Empty Contains %s Files", str(
            RQ_work.QueueSize()))

    logger.info("Ingest Complete")


if __name__ == "__main__":
    sys.exit(main())
