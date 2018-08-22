#!/usgs/apps/anaconda/bin/python

import os
import sys
import subprocess
import datetime
import pytz
import argparse
import json

import sqlalchemy

from sqlalchemy import Date, cast

from sqlalchemy import *
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm.util import *
from sqlalchemy.ext.declarative import declarative_base

from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files, Archives 
from pds_pipelines.config import pds_info, pds_db

import pdb


class Args:
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

        args = parser.parse_args()
        self.archive = args.archive
        self.volume = args.volume


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
    if testing_date == None:
        td = (datetime.datetime.now(pytz.utc)
              - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

        testing_date = datetime.datetime.strptime(str(td), "%Y-%m-%d %H:%M:%S")

    expired = session.query(Files).filter(
        Files.archiveid == archiveID).filter(or_(
            cast(Files.di_date, Date) < testing_date,
            cast(Files.di_date, Date) == None))

    return expired


def volume_expired(session, archiveID, testing_date=None):
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
    if testing_date == None:
        td = (datetime.datetime.now(pytz.utc)
              - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

        testing_date = datetime.datetime.strptime(str(td), "%Y-%m-%d %H:%M:%S")

    volstr = '%' + args.volume + '%'
    expired = session.query(Files).filter(Files.archiveid == archiveID,
                                          Files.filename.like(volstr)).filter(or_(
                                              cast(Files.di_date,
                                                   Date) < testing_date,
                                              cast(Files.di_date, Date) == None))

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

    try:
        # Throws away 'engine' information
        session, _ = db_connect(pds_db)
        print(args.archive)
        print('Database Connection Success')
    except Exception as e:
        print(e)
    else:
        # if db connection fails, there's no sense in doing this part
        td = (datetime.datetime.now(pytz.utc)
              - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        testing_date = datetime.datetime.strptime(str(td), "%Y-%m-%d %H:%M:%S")

        if args.volume:
            expired = volume_expired(session, archiveID, testing_date)
            if expired.count():
                print('Volume {} DI Ready: {} Files'.format(
                    args.volume, str(expired.count())))
            else:
                print('Volume {} DI Current'.format(args.volume))
        else:
            expired = archive_expired(session, archiveID, testing_date)
            if expired.count():
                print('Archive {} DI Ready: {} Files'.format(
                    args.archive, str(expired.count())))
            else:
                print('Archive {} DI Current'.format(args.archive))


if __name__ == "__main__":
    sys.exit(main())
