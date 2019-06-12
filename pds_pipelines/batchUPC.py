#!/usr/bin/env python

import json
import logging
import argparse
from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files, Archives
from pds_pipelines.config import pds_info, pds_db, pds_log


class Args(object):
    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser(description="DI Process")

        parser.add_argument('--log', '-l', dest="log_level",
                            choices=['DEBUG', 'INFO',
                                    'WARNING', 'ERROR', 'CRITICAL'],
                            help="Set the log level.", default='INFO')

        args = parser.parse_args()
        self.log_level = args.log_level


def main():
    args = Args()
    args.parse_args()

    PDS_info = json.load(open(pds_info, 'r'))
    reddis_queue = RedisQueue('UPC_ReadyQueue')
    logger = logging.getLogger('UPC_Queueing')
    level = logging.getLevelName(args.log_level)
    logger.setLevel(level)
    logFileHandle = logging.FileHandler(pds_log + 'Process.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info("UPC Queue: %s", reddis_queue.id_name)

    try:
        session, _ = db_connect(pds_db)
    except Exception as e:
        logger.error("%s", e)
        return 1

    # For each archive in the db, test if there are files that are ready to
    #  process
    for archive_id in session.query(Files.archiveid).distinct():
        result = session.query(Files).filter(Files.archiveid == archive_id,
                                             Files.upc_required == 't')

        # Get filepath from archive id
        archive_name = session.query(Archives.archive_name).filter(
            Archives.archiveid == archive_id).first()

        # No archive name = no path.  Skip these values.
        if (archive_name is None):
            logger.warn("No archive name found for archive id: %s", archive_id)
            continue
        try:
            # Since results are returned as lists, we have to access the 0th
            #  element to pull out the string archive name.
            fpath = PDS_info[archive_name[0]]['path']
        except KeyError:
            logger.warn("Unable to locate file path for archive id %s",
                        archive_id)
            continue

        # Add each file in the archive to the redis queue.
        for element in result:
            fname = fpath + element.filename
            fid = element.fileid
            reddis_queue.QueueAdd((fname, fid, archive_name[0]))

        logger.info("Added %s files from %s", result.count(), archive_name)
    return 0


if __name__ == "__main__":
    main()
