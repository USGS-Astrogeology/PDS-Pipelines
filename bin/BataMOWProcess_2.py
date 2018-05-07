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

import pdb


def main():

    #    pdb.set_trace()

    Key = sys.argv[-1]
    workarea = '/scratch/pds_services/' + Key + '/'

    RQ_mosaic = RedisQueue(Key + '_MosaicQueue')
    RQ_recipe = RedisQueue(Key + '_recipe_STEP2')

#******************** Setup system logging **********************
    logger = logging.getLogger(Key + '.STEP2')
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/BataMOW.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info('Starting BataMOW STEP 2 Processing')

    status = 'success'
    for element in RQ_recipe.RecipeGet():
        if status == 'error':
            break
        elif status == 'success':
            processOBJ = Process()
            process = processOBJ.JSON2Process(element)

            if 'equalizer' in processOBJ.getProcessName():
                inputlist = RQ_mosaic.ListGet()
                EQlist = workarea + 'testEQ.lis'
                with open(EQlist, "w") as f:
                    for item in inputlist:
                        print item
                        f.write(item + "\n")
                f.close()
                processOBJ.updateParameter('fromlist', EQlist)
#                processOBJ.updateParameter('tolist', workarea + 'testEQout.lis')
            elif 'automos' in processOBJ.getProcessName():

                AUTOlist = workarea + 'auto_input.lis'
                test = os.listdir(workarea)
                with open(AUTOlist, "w") as f2:
                    for item in test:
                        if '.equ.' in item:
                            print item
                            f2.write(workarea + item + "\n")
                f2.close()

                processOBJ.updateParameter('fromlist', AUTOlist)
                processOBJ.updateParameter(
                    'mosaic', workarea + 'testmosaic.cub')
                processOBJ.updateParameter('priority', 'ONTOP')

            print processOBJ.getProcess()

            for k, v in processOBJ.getProcess().items():
                func = getattr(isis, k)
                try:
                    func(**v)
                    logger.info('Process %s :: Success', k)

                    status = 'success'
                except ProcessError as e:
                    logger.error('Process %s :: Error', k)
                    logger.error(e)
                    status = 'error'

    if status == 'success':
        logger.info('Mosaic Should be GO')


if __name__ == "__main__":
    sys.exit(main())
