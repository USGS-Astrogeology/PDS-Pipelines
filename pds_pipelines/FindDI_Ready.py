#!/usr/bin/env python

import sys
import datetime
import argparse
import json
import logging
import pytz

from sqlalchemy import Date, cast

from sqlalchemy.orm.util import *
from sqlalchemy import or_

from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files
from pds_pipelines.config import pds_info, pds_db, pds_log

class Args(object):
    """
    Attributes
    ----------
    archive
    volume
    """
    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser(description='Find Arcives for DI')

        parser.add_argument('--archive', '-a', dest="archive",
                            help="Enter archive to test for DI")

        parser.add_argument('--volume', '-v', dest="volume",
                            help="Enter Volume to Test")

        parser.add_argument('--log', '-l', dest="log_level",
                            choice=['DEBUG', 'INFO',
                                    'WARNING', 'ERROR', 'CRITICAL'],
                            help="Set the log level.", default='INFO')


        args = parser.parse_args()
        self.archive = args.archive
        self.volume = args.volume
        self.log_level = args.log_level


def archive_expired(session, archiveID, testing_date=None):
    """
    Checks to see if archive is expired

    Parameters
    ----------
    session
    archiveID
    testing_date

    Returns
    -------
    expired
    """
    if testing_date is None:
        td = (datetime.datetime.now(pytz.utc)
              - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

        testing_date = datetime.datetime.strptime(str(td), "%Y-%m-%d %H:%M:%S")

    expired = session.query(Files).filter(
        Files.archiveid == archiveID).filter(or_(
            cast(Files.di_date, Date) < testing_date,
            cast(Files.di_date, Date) is None))

    return expired


def volume_expired(session, archiveID, volume, testing_date=None):
    """
    Checks to see if the volume is expired

    Parameters
    ----------
    session
    archiveID
    testing_date

    Returns
    -------
    expired
    """
    if testing_date is None:
        td = (datetime.datetime.now(pytz.utc)
              - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

        testing_date = datetime.datetime.strptime(str(td), "%Y-%m-%d %H:%M:%S")

    volstr = '%' + volume + '%'
    expired = session.query(Files).filter(Files.archiveid == archiveID,
                                          Files.filename.like(volstr)).filter(or_(
                                              cast(Files.di_date,
                                                   Date) < testing_date,
                                              cast(Files.di_date, Date) is None))

    return expired


def main():

    args = Args()
    args.parse_args()

    PDSinfoDICT = json.load(open(pds_info, 'r'))
    try:
        archiveID = PDSinfoDICT[args.archive]['archiveid']
    except KeyError:
        print("\nArchive '{}' not found in {}\n".format(args.archive, pds_info))
        print("The following archives are available:")
        for k in PDSinfoDICT.keys():
            print("\t{}".format(k))
        exit()

    logger = logging.getLogger('DI_Ready.' + args.archive)
    level = logging.getLevelName(args.log_level)
    logger.setLevel(level)
    logFileHandle = logging.FileHandler(pds_log + 'DI.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    try:
        # Throws away 'engine' information
        session, _ = db_connect(pds_db)
        logger.info("%s", args.archive)
        logger.info("Database Connection Success")
    except Exception as e:
        logger.error("%s", e)
    else:
        # if db connection fails, there's no sense in doing this part
        td = (datetime.datetime.now(pytz.utc)
              - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        testing_date = datetime.datetime.strptime(str(td), "%Y-%m-%d %H:%M:%S")

        if args.volume:
            expired = volume_expired(session, archiveID, args.volume, testing_date)
            if expired.count():
                logger.info("Volume %s DI Ready: %s Files", args.volume,
                            str(expired.count()))
            else:
                logger.info('Volume %s DI Current', args.volume)
        else:
            expired = archive_expired(session, archiveID, testing_date)
            if expired.count():
                logger.info('Archive %s DI Ready: %s Files', args.archive,
                            str(expired.count()))
            else:
                logger.info('Archive %s DI Current', args.archive)


if __name__ == "__main__":
    sys.exit(main())
