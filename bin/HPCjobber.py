#!/usgs/apps/anaconda/bin/python

import os
import sys
import subprocess
import datetime
import pytz

import argparse
import logging

from HPCjob import *

import pdb


class Args:
    """
    Attributes
    ----------
    process : str
    jobarray : str
    """
    def __init__(self):
        pass

    def parse_args(self):

        parser = argparse.ArgumentParser(description='PDS HPC Job Submission')

        parser.add_argument('--process', '-p', dest="process", required=True,
                            help="Enter process - di or ingest")

        parser.add_argument('--jobarray', '-j', dest="jobarray",
                            help="Enter string to set job array size")

        args = parser.parse_args()

        self.process = args.process
        self.jobarray = args.jobarray


def main():

    #    pdb.set_trace()

    args = Args()
    args.parse_args()

# ************* Logging Stuff ***********

    if args.process == 'di':
        logger = logging.getLogger('DIprocess_HPCjob')
        logger.setLevel(logging.INFO)
        logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/DI.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
        logFileHandle.setFormatter(formatter)
        logger.addHandler(logFileHandle)
    elif args.process == 'checksumupdate':
        logger = logging.getLogger('ChceksumUpdateprocess_HPCjob')
        logger.setLevel(logging.INFO)
        logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/DI.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
        logFileHandle.setFormatter(formatter)
        logger.addHandler(logFileHandle)
    elif args.process == 'ingest':
        logger = logging.getLogger('INGESTprocess_HPCjob')
        logger.setLevel(logging.INFO)
        logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Ingest.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
        logFileHandle.setFormatter(formatter)
        logger.addHandler(logFileHandle)
    elif args.process == 'thumbnail':
        logger = logging.getLogger('Thumbnailprocess_HPCjob')
        logger.setLevel(logging.INFO)
        logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Process.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
        logFileHandle.setFormatter(formatter)
        logger.addHandler(logFileHandle)
    elif args.process == 'browse':
        logger = logging.getLogger('Browseprocess_HPCjob')
        logger.setLevel(logging.INFO)
        logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Process.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
        logFileHandle.setFormatter(formatter)
        logger.addHandler(logFileHandle)
    elif args.process == 'projectionbrowse':
        logger = logging.getLogger('ProjectionBrowseprocess_HPCjob')
        logger.setLevel(logging.INFO)
        logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Process.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
        logFileHandle.setFormatter(formatter)
        logger.addHandler(logFileHandle)

    date = datetime.datetime.now(pytz.utc).strftime("%Y%m%d%M")
    jobOBJ = HPCjob()
    if args.process == 'di':
        logger.info('Starting DI Process HPC Job Submission')
        jobOBJ.setJobName('PDS_DIprocess')
        jobOBJ.setStdOut('/usgs/cdev/PDS/output/DIprocess_%A_%a.out')
        jobOBJ.setStdError('/usgs/cdev/PDS/output/DIprocess_%A_%a.err')
        jobOBJ.setMemory('8192')
        jobOBJ.setWallClock('240:00:00')
        jobOBJ.setPartition('pds')
        cmd = '/usgs/cdev/PDS/bin/DIprocess.py'
        SBfile = '/usgs/cdev/PDS/output/DIhpc' + date + '.sbatch'

    elif args.process == 'checksumupdate':
        logger.info('Starting Checksum Update Process HPC Job Submission')
        jobOBJ.setJobName('PDS_CSUprocess')
        jobOBJ.setStdOut('/usgs/cdev/PDS/output/CSUprocess_%A_%a.out')
        jobOBJ.setStdError('/usgs/cdev/PDS/output/CSUprocess_%A_%a.err')
        jobOBJ.setMemory('8192')
        jobOBJ.setWallClock('20:00:00')
        jobOBJ.setPartition('pds')
        cmd = '/usgs/cdev/PDS/bin/ChecksumUpdateProcess.py'
        SBfile = '/usgs/cdev/PDS/output/CSUhpc' + date + '.sbatch'

    elif args.process == 'ingest':
        logger.info('Starting INGEST process HPC Job Submission')
        jobOBJ.setJobName('PDS_INGESTprocess')
        jobOBJ.setStdOut('/usgs/cdev/PDS/output/INGESTprocess_%A_%a.out')
        jobOBJ.setStdError('/usgs/cdev/PDS/output/INGESTprocess_%A_%a.err')
        jobOBJ.setMemory('8192')
        jobOBJ.setWallClock('240:00:00')
        jobOBJ.setPartition('pds')
        cmd = '/usgs/cdev/PDS/bin/IngestProcess.py'
        SBfile = '/usgs/cdev/PDS/output/INGESThpc' + date + '.sbatch'

    elif args.process == 'thumbnail':
        logger.info('Starting Thumbnail process HPC Job Submission')
        jobOBJ.setJobName('PDS_Thumbnailprocess')
        jobOBJ.setStdOut('/usgs/cdev/PDS/output/Thumbnailprocess_%A_%a.out')
        jobOBJ.setStdError('/usgs/cdev/PDS/output/Thumbnailprocess_%A_%a.err')
        jobOBJ.setMemory('8192')
        jobOBJ.setWallClock('20:00:00')
        jobOBJ.setPartition('pds')
        cmd = '/usgs/cdev/PDS/bin/thumbnail_process.py'
        SBfile = '/usgs/cdev/PDS/output/Thpc' + date + '.sbatch'

    elif args.process == 'browse':
        logger.info('Starting Browse process HPC Job Submission')
        jobOBJ.setJobName('PDS_Browseprocess')
        jobOBJ.setStdOut('/usgs/cdev/PDS/output/Browseprocess_%A_%a.out')
        jobOBJ.setStdError('/usgs/cdev/PDS/output/Browseprocess_%A_%a.err')
        jobOBJ.setMemory('8192')
        jobOBJ.setWallClock('20:00:00')
        jobOBJ.setPartition('pds')
        cmd = '/usgs/cdev/PDS/bin/browse_process.py'
        SBfile = '/usgs/cdev/PDS/output/Bhpc' + date + '.sbatch'

    elif args.process == 'projectionbrowse':
        logger.info('Starting Projection Browse process HPC Job Submission')
        jobOBJ.setJobName('PDS_ProjBrowseprocess')
        jobOBJ.setStdOut('/usgs/cdev/PDS/output/ProjBrowseprocess_%A_%a.out')
        jobOBJ.setStdError('/usgs/cdev/PDS/output/ProjBrowseprocess_%A_%a.err')
        jobOBJ.setMemory('8192')
        jobOBJ.setWallClock('20:00:00')
        jobOBJ.setPartition('pds')
        cmd = '/usgs/cdev/PDS/bin/projectionbrowse_process.py'
        SBfile = '/usgs/cdev/PDS/output/Phpc' + date + '.sbatch'

    if args.jobarray:
        JA = args.jobarray
    else:
        JA = 1

    jobOBJ.setJobArray(JA)
    jobOBJ.setCommand(cmd)
    jobOBJ.MakeJobFile(SBfile)

    try:
        sb = open(SBfile)
        sb.close
        logger.info('SBATCH File Creation: Success')
    except IOError as e:
        logger.error('SBATCH File %s Not Found', SBfile)

    try:
        jobOBJ.Run()
        logger.info('Job Submission to HPC: Success')
    except IOError as e:
        logger.error('Jobs NOT Submitted to HPC')


if __name__ == "__main__":
    sys.exit(main())
