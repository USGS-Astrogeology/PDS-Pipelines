#!/usr/bin/env python

import sys
import os
import argparse
import logging

from pds_pipelines.redis_queue import RedisQueue
from pds_pipelines.hpc_job import HPCjob
from pds_pipelines.config import pds_log, slurm_log, cmd_dir, workarea, default_namespace


def parse_args():
    parser = argparse.ArgumentParser(description="Final Job Manager")

    parser.add_argument('--log', '-l', dest="log_level",
                        choices=['DEBUG', 'INFO',
                                'WARNING', 'ERROR', 'CRITICAL'],
                        help="Set the log level.", default='INFO')

    parser.add_argument('--namespace',
                        '-n',
                        dest='namespace',
                        help="Queue namespace")


    args = parser.parse_args()
    return args


def main(user_args):
    log_level = user_args.log_level
    namespace = user_args.namespace

    if namespace is None:
        namespace = default_namespace

    logger = logging.getLogger('final_job_manager')
    level = logging.getLevelName(log_level)
    logger.setLevel(level)
    logFileHandle = logging.FileHandler(pds_log+'Service.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

#***************Look at Final queue for work************
    RQ_final = RedisQueue('FinalQueue', namespace)
    logger.debug("Reddis Queue: %s", RQ_final.id_name)

    if int(RQ_final.QueueSize()) == 0:
        logger.debug('Nothing Found in Final Queue')
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

        cmd = "{}service_final.py -n {} -k {}".format(cmd_dir, namespace, FKey)
        jobOBJ.setCommand(cmd)
        logger.info('HPC Command: %s', cmd)

        #SBfile = '/scratch/pds_services/' + FKey + '/' + FKey + '_final.sbatch'
        SBfile = os.path.join(workarea, FKey, (FKey + '_final.sbatch'))
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
    sys.exit(main(parse_args()))
