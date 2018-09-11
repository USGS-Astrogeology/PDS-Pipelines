#!/usr/bin/env python
import os
import sys
import datetime
import pytz
import logging
import json
import argparse


import hashlib
from ast import literal_eval

from sqlalchemy import *
from sqlalchemy.orm.util import *

from pds_pipelines.RedisQueue import *
from pds_pipelines.PDS_DBquery import *
from pds_pipelines.db import db_connect
from pds_pipelines.config import pds_info, pds_log, pds_db, archive_base, web_base
from pds_pipelines.models.pds_models import Files


class Args:
    def __init__(self):
        pass

    def parse_args(self):

        parser = argparse.ArgumentParser(description='PDS DI Database Ingest')

        parser.add_argument('--override', dest='override', action='store_true')
        parser.set_defaults(override=False)
        args = parser.parse_args()

        self.override = args.override



def main():
    args = Args()
    args.parse_args()
    override = args.override
    # ********* Set up logging *************
    logger = logging.getLogger('Ingest_Process')
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler(pds_log + 'Ingest.log')

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info("Starting Process")
    PDSinfoDICT = json.load(open(pds_info, 'r'))

    RQ_main = RedisQueue('Ingest_ReadyQueue')
    RQ_work = RedisQueue('Ingest_WorkQueue')

    RQ_upc = RedisQueue('UPC_ReadyQueue')
    RQ_thumb = RedisQueue('Thumbnail_ReadyQueue')
    RQ_browse = RedisQueue('Browse_ReadyQueue')
    #RQ_pilotB = RedisQueue('PilotB_ReadyQueue')

    try:
        session, _ = db_connect(pds_db)
        logger.info('DataBase Connecton: Success')
    except:
        logger.error('DataBase Connection: Error')

    index = 1

    while int(RQ_main.QueueSize()) > 0:

        item = literal_eval(RQ_main.QueueGet().decode("utf-8"))
        inputfile = item[0]
        archive = item[1]
        RQ_work.QueueAdd(inputfile)
        
        subfile = inputfile.replace(PDSinfoDICT[archive]['path'], '')
        # Calculate checksum in chunks of 4096
        f_hash = hashlib.md5()
        with open(inputfile, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                f_hash.update(chunk)
        filechecksum = f_hash.hexdigest()

        QOBJ = session.query(Files).filter_by(filename=subfile).first()

        runflag = False
        if QOBJ is None:
            runflag = True
        elif filechecksum != QOBJ.checksum:
            runflag = True

        if runflag == True or override == True:
            date = datetime.datetime.now(
                pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
            fileURL = inputfile.replace(archive_base, web_base)

            # If all upc requirements are in 'inputfile,' flag for upc
            upcflag =  all(x in inputfile for x in PDSinfoDICT[archive]['upc_reqs'])
            filesize = os.path.getsize(inputfile)

            try:
                # If we found an existing file and want to overwrite the data
                if QOBJ is not None and override == True:
                    testIN = QOBJ
                # If the file was not found, create a new entry
                else:
                    testIN = Files()
                testIN.archiveid = PDSinfoDICT[archive]['archiveid']
                testIN.filename = subfile
                testIN.entry_date = date
                testIN.checksum = filechecksum
                testIN.upc_required = upcflag
                testIN.validation_required = True
                testIN.header_only = False
                testIN.release_date = date
                testIN.file_url = fileURL
                testIN.file_size = filesize
                testIN.di_pass = True
                testIN.di_date = date

                session.merge(testIN)
                session.flush()

                if upcflag == True:
                    RQ_upc.QueueAdd((inputfile, testIN.fileid, archive))
                    RQ_thumb.QueueAdd((inputfile, testIN.fileid, archive))
                    RQ_browse.QueueAdd((inputfile, testIN.fileid, archive))
                    #RQ_pilotB.QueueAdd((inputfile, testIN.fileid, archive))


                RQ_work.QueueRemove(inputfile)

                index = index + 1

            except Exception as e:
                print(e)
                logger.error("Error During File Insert %s", subfile)

        elif runflag == False:
            RQ_work.QueueRemove(inputfile)

        if index >= 250:
            try:
                session.commit()
                logger.info("Commit 250 files to Database: Success")
                index = 1
            except:
                session.rollback()
                logger.error("Something Went Wrong During DB Insert")
    else:
        logger.info("No Files Found in Ingest Queue")
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
