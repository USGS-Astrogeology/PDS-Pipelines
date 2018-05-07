#!/usgs/apps/anaconda/bin/python

import os
import sys
import pvl
import subprocess
import logging
import shutil

from pysis import isis
from pysis.exceptions import ProcessError

from RedisQueue import *
from RedisHash import *
from Recipe import *
from Loggy import *
from SubLoggy import *
from HPCjob import *

import pdb


def main():

    #    pdb.set_trace()

    Key = sys.argv[-1]

    workarea = '/scratch/pds_services/' + Key + '/'

# *********Redis Queue Setups *************
    RQ_file = RedisQueue(Key + '_FileQueue')
    RQ_work = RedisQueue(Key + '_WorkQueue')
    RQ_mosaic = RedisQueue(Key + '_MosaicQueue')
    RQ_recipe = RedisQueue(Key + '_recipe_STEP1')
    RH_info = RedisHash(Key + '_MOWinfo')

    if int(RQ_file.QueueSize()) == 0:
        print "No Files Found in Redis Queue"
    else:
        jobFile = RQ_file.Qfile2Qwork(
            RQ_file.getQueueName(), RQ_work.getQueueName())

#******************** Setup system logging **********************
        basename = os.path.splitext(os.path.basename(jobFile))[0]
        logger = logging.getLogger(Key + '.' + basename)
        logger.setLevel(logging.INFO)

        logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/BataMOW.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
        logFileHandle.setFormatter(formatter)
        logger.addHandler(logFileHandle)

        logger.info('Starting BataMOW STEP 1 Processing')

        infile = workarea + \
            os.path.splitext(os.path.basename(jobFile))[0] + '.input.cub'
        outfile = workarea + \
            os.path.splitext(os.path.basename(jobFile))[0] + '.output.cub'

        status = 'success'
        for element in RQ_recipe.RecipeGet():
            if status == 'error':
                break
            elif status == 'success':
                processOBJ = Process()
                process = processOBJ.JSON2Process(element)

                if '2isis' in processOBJ.getProcessName():
                    processOBJ.updateParameter('from_', jobFile)
                    processOBJ.updateParameter('to', outfile)
                elif 'spice' in processOBJ.getProcessName():
                    processOBJ.updateParameter('from_', infile)
                elif 'ctxevenodd' in processOBJ.getProcessName():
                    label = pvl.load(infile)
                    SS = label['IsisCube']['Instrument']['SpatialSumming']
                    print SS
                    if SS != 1:
                        break
                    else:
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', outfile)
                elif 'mocevenodd' in processOBJ.getProcessName():
                    label = pvl.load(infile)
                    CTS = label['IsisCube']['Instrument']['CrosstrackSumming']
                    print CTS
                    if CTS != 1:
                        continue
                    else:
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', outfile)
                elif 'cam2map' in processOBJ.getProcessName():
                    processOBJ.updateParameter('from_', infile)
                    processOBJ.updateParameter('to', outfile)

                    camrangeOUT = workarea + basename + '_camrange.txt'
                    isis.camrange(from_=infile,
                                  to=camrangeOUT)
                    camlab = pvl.load(camrangeOUT)

                    if camlab['UniversalGroundRange']['MinimumLatitude'] > float(RH_info.getMinLat()):
                        minlat = camlab['UniversalGroundRange']['MinimumLatitude']
                    else:
                        minlat = RH_info.getMinLat()

                    if camlab['UniversalGroundRange']['MaximumLatitude'] < float(RH_info.getMaxLat()):
                        maxlat = camlab['UniversalGroundRange']['MaximumLatitude']
                    else:
                        maxlat = RH_info.getMaxLat()

                    if camlab['UniversalGroundRange']['MinimumLongitude'] > float(RH_info.getMinLon()):
                        minlon = camlab['UniversalGroundRange']['MinimumLongitude']
                    else:
                        minlon = RH_info.getMinLon()

                    if camlab['UniversalGroundRange']['MaximumLongitude'] < float(RH_info.getMaxLon()):
                        maxlon = camlab['UniversalGroundRange']['MaximumLongitude']
                    else:
                        maxlon = RH_info.getMaxLon()

                    processOBJ.AddParameter('minlat', minlat)
                    processOBJ.AddParameter('maxlat', maxlat)
                    processOBJ.AddParameter('minlon', minlon)
                    processOBJ.AddParameter('maxlon', maxlon)
                    os.remove(camrangeOUT)

                else:
                    processOBJ.updateParameter('from_', infile)
                    processOBJ.updateParameter('to', outfile)

                for k, v in processOBJ.getProcess().items():
                    func = getattr(isis, k)
                    try:
                        func(**v)
                        logger.info('Process %s :: Success', k)

                        if os.path.isfile(outfile):
                            os.rename(outfile, infile)
                        status = 'success'
                    except ProcessError as e:
                        logger.error('Process %s :: Error', k)
                        logger.error(e)
                        status = 'error'

        if status == 'success':

            finalfile = infile.replace('.input.cub', '_proj.cub')
            shutil.move(infile, finalfile)

            try:
                RQ_mosaic.QueueAdd(finalfile)
                logger.info('File %s Added to mosaic Queue', finalfile)
                RQ_work.QueueRemove(jobFile)
            except:
                logger.error(
                    'File %s **NOT** Added to mosaic Queue', finalfile)

            if RQ_file.QueueSize() == 0 and RQ_work.QueueSize() == 0:

                logger.info('HPC Cluster BataMOW 2 job Submission Starting')
                jobOBJ = HPCjob()
                jobOBJ.setJobName(Key + '_BataMOW2')
                jobOBJ.setStdOut('/usgs/cdev/PDS/output/' +
                                 Key + '_BM2_%A_%a.out')
                jobOBJ.setStdError(
                    '/usgs/cdev/PDS/output/' + Key + '_BM2_%A_%a.err')
                jobOBJ.setWallClock('02:00:00')
                jobOBJ.setMemory('4096')
                jobOBJ.setPartition('pds')
                jobOBJ.setJobArray(1)
                cmd = '/usgs/cdev/PDS/bin/BataMOWProcess_2.py ' + Key
                logger.info('HPC Command: %s', cmd)
                jobOBJ.setCommand(cmd)

                SBfile = workarea + '/' + Key + '_BM2.sbatch'
                jobOBJ.MakeJobFile(SBfile)

                try:
                    sb = open(SBfile)
                    sb.close
                    logger.info('SBATCH File %s Creation: Success', SBfile)
                except IOError as e:
                    logger.error('SBATCH File %s Not Found', SBfile)

                try:
                    jobOBJ.Run()
                    logger.info('Job Submission to HPC: Success')
                except IOError as e:
                    logger.error('Jobs NOT Submitted to HPC')


if __name__ == "__main__":
    sys.exit(main())
