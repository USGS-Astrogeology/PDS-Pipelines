#!/usgs/apps/anaconda/bin/python

import os
import sys
import subprocess
import datetime
import pytz

import argparse
import logging

from pds_pipelines.HPCjob import *

import pdb
from pds_pipelines.jobconfig import jobconfig, log_format


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

    # pdb.set_trace()

    args = Args()
    args.parse_args()

    # Grab the proper nested dict from config file
    job = jobconfig[args.process]

    # Set up logging
    logger = logging.getLogger(job['logger'])
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler(job['handle'])
    formatter = logging.Formatter(log_format)
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)
    logger.info(job['info'])

    # Parametrize the HPC job using the configuration file
    date = datetime.datetime.now(pytz.utc).strftime("%Y%m%d%M")
    jobOBJ = HPCjob()
    jobOBJ.setJobName(job['name'])
    jobOBJ.setStdOut(job['stdout'])
    jobOBJ.setStdError(job['stderr'])
    jobOBJ.setMemory(job['memory'])
    jobOBJ.setWallClock(job['wallclock'])
    jobOBJ.setPartition(job['partition'])

    # Date doesn't fit well with the recipe style config, so it includes
    #  a @date@ tag that we replace with the current date
    SBfile = job['SBfile'].replace('@date@', date)
    cmd = job['cmd']

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
