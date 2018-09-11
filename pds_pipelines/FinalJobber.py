#!/usr/bin/env python

import os
import sys
import subprocess

import logging
import shutil
import zipfile
import datetime
import json

from collections import OrderedDict
from pds_pipelines.RedisQueue import *
from pds_pipelines.PDS_DBquery import *
from pds_pipelines.HPCjob import *
from pds_pipelines.config import pds_log,slurm_log,cmd_dir, scratch



import pdb


def main():

    #   pdb.set_trace()
    #***************** Setup Logging **************
    logger = logging.getLogger('FinalJobber')
    logger.setLevel(logging.INFO)
    #logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Service.log')
    logFileHandle = logging.FileHandler(pds_log+'Service.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

#***************Look at Final queue for work************
    RQ_final = RedisQueue('FinalQueue')
    if int(RQ_final.QueueSize()) == 0:
        #        logger.info('NO Keys Found in FinalQueue')
        print 'Nothing Found in Final Queue'
    else:
        FKey = RQ_final.QueueGet()
        logger.info('Found %s in Final Queue', FKey)

# ** *************** HPC job stuff ***********************

        logger.info('HPC Cluster job Submission Starting')
        jobOBJ = HPCjob()
        jobOBJ.setJobName(FKey + '_Final')

        #jobOBJ.setStdOut('/usgs/cdev/PDS/output/' + FKey + '_%A_%a.out')
        #jobOBJ.setStdError('/usgs/cdev/PDS/output/' + FKey + '_%A_%a.err')
        jobOBJ.setStdOut(slurm_log + FKey + '_%A_%a.out')
        jobOBJ.setStdError(slurm_log + FKey + '_%A_%a.err')
        jobOBJ.setWallClock('24:00:00')
        jobOBJ.setMemory('8192')
        jobOBJ.setPartition('pds')

        cmd = cmd_dir+'ServiceFinal.py ' + FKey
        jobOBJ.setCommand(cmd)
        logger.info('HPC Command: %s', cmd)

        #SBfile = '/scratch/pds_services/' + FKey + '/' + FKey + '_final.sbatch'
        SBfile = scratch + FKey + '/' + FKey + '_final.sbatch'
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
