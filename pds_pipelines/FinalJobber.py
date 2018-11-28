#!/usr/bin/env python

import sys
import argparse
import logging

from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.HPCjob import HPCjob
from pds_pipelines.config import pds_log, slurm_log, cmd_dir, scratch


class Args(object):
    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser(description="DI Process")

        parser.add_argument('--log', '-l', dest="log_level",
                            choice=['DEBUG', 'INFO',
                                    'WARNING', 'ERROR', 'CRITICAL'],
                            help="Set the log level.", default='INFO')

        args = parser.parse_args()
        self.log_level = args.log_level


def main():
    args = Args()
    args.parse_args()

    logger = logging.getLogger('FinalJobber')
    level = logging.getLevelName(args.log_level)
    logger.setLevel(level)
    logFileHandle = logging.FileHandler(pds_log+'Service.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

#***************Look at Final queue for work************
    RQ_final = RedisQueue('FinalQueue')
    logger.info("Reddis Queue: %s", RQ_final.id_name)

    if int(RQ_final.QueueSize()) == 0:
        logging.info('Nothing Found in Final Queue')
    else:
        FKey = RQ_final.QueueGet()
        logger.info('Found %s in Final Queue', str(FKey))

# ** *************** HPC job stuff ***********************

        logger.info('HPC Cluster job Submission Starting')
        jobOBJ = HPCjob()
        jobOBJ.setJobName(FKey + '_Final')
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
            sb.close()
            logger.info('SBATCH File Creation: Success')
        except IOError as e:
            logger.error('SBATCH File %s Not Found', SBfile)

        try:
            jobOBJ.Run()
            logger.info('Job Submission to HPC: Success')
        except IOError as e:
            logger.error('Jobs NOT Submitted to HPC\n%s', e)


if __name__ == "__main__":
    sys.exit(main())
