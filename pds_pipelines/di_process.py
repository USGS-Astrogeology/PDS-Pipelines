#!/usr/bin/env python

import os
import sys
import datetime
import logging
import hashlib
import json
import argparse
import pytz

from ast import literal_eval
from pds_pipelines.redis_queue import RedisQueue
from pds_pipelines.redis_lock import RedisLock
from pds_pipelines.config import pds_db, pds_log, pds_info, lock_obj, upc_error_queue
from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files

def parse_args():
    parser = argparse.ArgumentParser(description="DI Process")

    parser.add_argument('--log', '-l', dest="log_level",
                        choices=['DEBUG', 'INFO',
                                'WARNING', 'ERROR', 'CRITICAL'],
                        help="Set the log level.", default='INFO')

    args = parser.parse_args()
    return args

def main(user_args):
    log_level = user_args.log_level

    PDSinfoDICT = json.load(open(pds_info, 'r'))

    # Set up logging
    logger = logging.getLogger('DI_Process')
    level = logging.getLevelName(log_level)
    logger.setLevel(level)
    logFileHandle = logging.FileHandler(pds_log + 'DI.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info('Starting DI Process')

    try:
        Session, engine = db_connect(pds_db)
        session = Session()
        logger.info('DataBase Connecton: Success')
    except Exception as e:
        logger.error('DataBase Connection Error: %s', str(e))
        return 1

    RQ = RedisQueue('DI_ReadyQueue')
    RQ_error = RedisQueue(upc_error_queue)
    RQ_lock = RedisLock(lock_obj)
    RQ_lock.add({RQ.id_name: '1'})
    index = 0

    logger.info("DI Queue: %s", RQ.id_name)

    while int(RQ.QueueSize()) > 0 and RQ_lock.available(RQ.id_name):
        item = literal_eval(RQ.QueueGet())
        inputfile = item[0]
        archive = item[1]
        logger.debug("%s - %s", inputfile, archive)
        try:
            Qelement = session.query(Files).filter(
                Files.filename == inputfile).one()
        except Exception as e:
            logger.warning('Filename query failed for inputfile %s: %s', inputfile, str(e))
            continue

        archive_path = PDSinfoDICT[archive]['path']

        cpfile = archive_path + Qelement.filename
        if os.path.isfile(cpfile):
            f_hash = hashlib.md5()
            with open(cpfile, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    f_hash.update(chunk)
            checksum = f_hash.hexdigest()

            Qelement.di_pass = checksum == Qelement.checksum
            if not Qelement.di_pass:
                logger.warning('File %s checksum %s does not match the database entry checksum %s',
                            cpfile, checksum, Qelement.checksum)

            Qelement.di_date = datetime.datetime.now(
                pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
            session.flush()
            index = index + 1
            if index > 50:
                session.commit()
                logger.info('Session Commit for 50 Records: Success')
                index = 0
        else:
            RQ_error.QueueAdd(f'Unable to locate or access {inputfile} during DI processing')
            logger.warning('File %s Not Found', cpfile)
    try:
        session.commit()
        logger.info("End Commit DI process to Database: Success")
        index = 1
    except Exception as e:
        logger.warning("Unable to commit changes to database\n\n%s", e)
        session.rollback()

    # Close connection to database
    session.close()
    engine.dispose()


if __name__ == "__main__":
    sys.exit(main(parse_args()))
