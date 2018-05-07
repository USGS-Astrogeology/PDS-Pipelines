#!/usgs/apps/anaconda/bin/python

import os
import sys
import subprocess
import datetime
import pytz
import json
import logging
import argparse

from RedisQueue import *
from HPCjob import *

import pdb


class Args:
    """
    Attributes
    ----------
    archive : str
    volume : str
    search : str
    """
    def __init__(self):
        pass

    def parse_args(self):

        parser = argparse.ArgumentParser(description='PDS DI Database Ingest')

        parser.add_argument('--archive', '-a', dest="archive", required=True,
                            help="Enter archive - archive to ingest")

        parser.add_argument('--volume', '-v', dest="volume",
                            help="Enter voluem to Ingest")

        parser.add_argument('--search', '-s', dest="search",
                            help="Enter string to search for")

        args = parser.parse_args()

        self.archive = args.archive
        self.volume = args.volume
        self.search = args.search


def main():

    #    pdb.set_trace()

    args = Args()
    args.parse_args()

    RQ = RedisQueue('Ingest_ReadyQueue')

# ********* Set up logging *************
    logger = logging.getLogger(args.archive + '_INGEST')
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Ingest.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    PDSinfoDICT = json.load(open('/usgs/cdev/PDS/bin/PDSinfo.json', 'r'))

    archivepath = PDSinfoDICT[args.archive]['path'][:-1]
    if args.volume:
        archivepath = archivepath + '/' + args.volume

    logger.info('Starting Ingest for: %s', archivepath)

    for dirpath, dirs, files in os.walk(archivepath):
        for filename in files:
            fname = os.path.join(dirpath, filename)
            if args.search:
                if args.search in fname:
                    try:
                        RQ.QueueAdd(fname)
                    except:
                        logger.error(
                            'File %s NOT added to Ingest Queue', fname)
                else:
                    continue
            else:
                try:
                    RQ.QueueAdd(fname)
                except:
                    logger.error('File %s NOT added to Ingest Queue', fname)

    Qsize = RQ.QueueSize()
    logger.info('Files added to Ingest Queue: %s', Qsize)

    logger.info('IngestJobber Complete')


if __name__ == "__main__":
    sys.exit(main())
