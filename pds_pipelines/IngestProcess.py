#!/usr/bin/env python
import os
import sys
import datetime
import logging
import json
import argparse
import hashlib
import pytz

from ast import literal_eval
from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.RedisLock import RedisLock
from pds_pipelines.db import db_connect
from pds_pipelines.config import pds_info, pds_log, pds_db, archive_base, web_base, lock_obj
from pds_pipelines.models.pds_models import Files


class Args(object):
    def __init__(self):
        pass

    def parse_args(self):

        parser = argparse.ArgumentParser(description='PDS DI Database Ingest')

        parser.add_argument('--override', dest='override', action='store_true')
        parser.set_defaults(override=False)

        parser.add_argument('--log', '-l', dest="log_level",
                            choices=['DEBUG', 'INFO',
                                    'WARNING', 'ERROR', 'CRITICAL'],
                            help="Set the log level.", default='INFO')

        args = parser.parse_args()
        self.log_level = args.log_level
        self.override = args.override


def main():

    args = Args()
    args.parse_args()
    override = args.override
    logger = logging.getLogger('Ingest_Process')
    level = logging.getLevelName(args.log_level)
    logger.setLevel(level)
    logFileHandle = logging.FileHandler(pds_log + 'Ingest.log')
    print("Log File: {}Ingest.log".format(pds_log))
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info("Starting Ingest Process")
    PDSinfoDICT = json.load(open(pds_info, 'r'))

    RQ_main = RedisQueue('Ingest_ReadyQueue')
    RQ_lock = RedisLock(lock_obj)
    RQ_lock.add({RQ_main.id_name: '1'})
    RQ_work = RedisQueue('Ingest_WorkQueue')

    RQ_upc = RedisQueue('UPC_ReadyQueue')
    RQ_thumb = RedisQueue('Thumbnail_ReadyQueue')
    RQ_browse = RedisQueue('Browse_ReadyQueue')

    logger.info("UPC Queue: %s", RQ_upc.id_name)
    logger.info("Thumbnail Queue: %s", RQ_thumb.id_name)
    logger.info("Browse Queue: %s", RQ_browse.id_name)

    try:
        session, engine = db_connect(pds_db)
        logger.info('DataBase Connecton: Success')
    except:
        logger.error('DataBase Connection: Error')
        return 1

    index = 1

    while int(RQ_main.QueueSize()) > 0 and RQ_lock.available(RQ_main.id_name):

        item = literal_eval(RQ_main.QueueGet())
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
        if QOBJ is None or filechecksum != QOBJ.checksum:
            runflag = True

        if runflag or override:
            date = datetime.datetime.now(
                pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
            fileURL = inputfile.replace(archive_base, web_base)

            # If all upc requirements are in 'inputfile,' flag for upc
            upcflag = all(x in inputfile for x in PDSinfoDICT[archive]['upc_reqs'])
            filesize = os.path.getsize(inputfile)

            try:
                # If we found an existing file and want to overwrite the data
                if QOBJ is not None and override:
                    ingest_entry = QOBJ
                # If the file was not found, create a new entry
                else:
                    ingest_entry = Files()
                    ingest_entry.archiveid = PDSinfoDICT[archive]['archiveid']
                    ingest_entry.filename = subfile
                    ingest_entry.entry_date = date
                    ingest_entry.checksum = filechecksum
                    ingest_entry.upc_required = upcflag
                    ingest_entry.validation_required = True
                    ingest_entry.header_only = False
                    ingest_entry.release_date = date
                    ingest_entry.file_url = fileURL
                    ingest_entry.file_size = filesize
                    ingest_entry.di_pass = True
                    ingest_entry.di_date = date

                session.merge(ingest_entry)
                session.flush()

                if upcflag:
                    RQ_upc.QueueAdd((inputfile, ingest_entry.fileid, archive))
                    RQ_thumb.QueueAdd((inputfile, ingest_entry.fileid, archive))
                    RQ_browse.QueueAdd((inputfile, ingest_entry.fileid, archive))
                    #RQ_pilotB.QueueAdd((inputfile,ingest_entry.fileid, archive))

                RQ_work.QueueRemove(inputfile)

                index = index + 1

            except Exception as e:
                logger.error("Error During File Insert %s : %s", str(subfile), str(e))

        elif not runflag and not override:
            RQ_work.QueueRemove(inputfile)
            logger.warn("Not running ingest: file %s already present"
                        " in database and no override flag supplied", inputfile)

        if index >= 250:
            try:
                session.commit()
                logger.info("Commit 250 files to Database: Success")
                index = 1
            except Exception as e:
                session.rollback()
                logger.warn("Unable to commit to database: %s", str(e))
    else:
        logger.info("No Files Found in Ingest Queue")
        try:
            session.commit()
            logger.info("Commit to Database: Success")
        except Exception as e:
            logger.error("Unable to commit to database: %s", str(e))
            session.rollback()


    # Close connection to database
    session.close()
    engine.dispose()

    if RQ_main.QueueSize() == 0 and RQ_work.QueueSize() == 0:
        logger.info("Process Complete All Queues Empty")
    elif RQ_main.QueueSize() == 0 and RQ_work.QueueSize() != 0:
        logger.warning("Process Done Work Queue NOT Empty Contains %s Files", str(
            RQ_work.QueueSize()))

    logger.info("Ingest Complete")


if __name__ == "__main__":
    sys.exit(main())
