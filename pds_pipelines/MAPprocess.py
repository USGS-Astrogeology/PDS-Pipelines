#!/usgs/apps/anaconda/bin/python

import os
import sys
import subprocess
import logging
import shutil

from pysis import isis
from pysis.exceptions import ProcessError
from pysis.isis import map2map

from pds_pipelines.RedisQueue import *
from pds_pipelines.RedisHash import *
from pds_pipelines.Recipe import *
from pds_pipelines.Loggy import *
from pds_pipelines.SubLoggy import *


import pdb


def main():

    #    pdb.set_trace()

    Key = sys.argv[-1]

    workarea = '/scratch/pds_services/' + Key + '/'

    RQ_file = RedisQueue(Key + '_FileQueue')
    RQ_work = RedisQueue(Key + '_WorkQueue')
    RQ_zip = RedisQueue(Key + '_ZIP')
    RQ_loggy = RedisQueue(Key + '_loggy')
    RQ_final = RedisQueue('FinalQueue')
    RHash = RedisHash(Key + '_info')
    RHerror = RedisHash(Key + '_error')

    if int(RQ_file.QueueSize()) == 0:
        print "No Files Found in Redis Queue"
    else:
        jobFile = RQ_file.Qfile2Qwork(
            RQ_file.getQueueName(), RQ_work.getQueueName())

#******************** Setup system logging **********************
        basename = os.path.splitext(os.path.basename(jobFile))[0]
        logger = logging.getLogger(Key + '.' + basename)
        logger.setLevel(logging.INFO)

        logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Service.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
        logFileHandle.setFormatter(formatter)
        logger.addHandler(logFileHandle)

        logger.info('Starting MAP Processing')

        loggyOBJ = Loggy(basename)

# *************** File Naming ***************
        infile = workarea + \
            os.path.splitext(os.path.basename(jobFile))[0] + '.input.cub'
        outfile = workarea + \
            os.path.splitext(os.path.basename(jobFile))[0] + '.output.cub'

# *********** Recipe Stuff ********************

        RQ_recipe = RedisQueue(Key + '_recipe')

        status = 'success'

        for element in RQ_recipe.RecipeGet():

            if status == 'error':
                break
            elif status == 'success':
                processOBJ = Process()
                process = processOBJ.JSON2Process(element)

                if 'gdal_translate' not in processOBJ.getProcessName():

                    if 'cubeatt-band' in processOBJ.getProcessName():
                        if '+' in jobFile:
                            #                            bandSplit = jobFile.split('+')
                         #                           infileB = infile + '+' + bandSplit[1]
                            processOBJ.updateParameter('from_', jobFile)
                            processOBJ.updateParameter('to', outfile)
                            processOBJ.ChangeProcess('cubeatt')
                        else:
                            continue

                    elif 'map2map' in processOBJ.getProcessName():
                        if '+' in jobFile:
                            processOBJ.updateParameter('from_', infile)
                        else:
                            processOBJ.updateParameter('from_', jobFile)
                        processOBJ.updateParameter('to', outfile)

                    elif 'cubeatt-bit' in processOBJ.getProcessName():
                        if RHash.OutBit() == 'unsignedbyte':
                            temp_outfile = outfile + '+lsb+tile+attached+unsignedbyte+1:254'
                        elif RHash.OutBit() == 'signedword':
                            temp_outfile = outfile + '+lsb+tile+attached+signedword+-32765:32765'
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', temp_outfile)
                        processOBJ.ChangeProcess('cubeatt')

                    elif 'isis2pds' in processOBJ.getProcessName():
                        #                        finalfile = infile.replace('.input.cub', '_final.img')
                        finalfile = workarea + RHash.getMAPname() + '.img'
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', finalfile)

                    else:
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', outfile)

                    print processOBJ.getProcess()

                    for k, v in processOBJ.getProcess().items():
                        func = getattr(isis, k)
                        subloggyOBJ = SubLoggy(k)
                        try:
                            func(**v)
                            logger.info('Process %s :: Success', k)
                            subloggyOBJ.setStatus('SUCCESS')
                            subloggyOBJ.setCommand(processOBJ.LogCommandline())
                            subloggyOBJ.setHelpLink(processOBJ.LogHelpLink())
                            loggyOBJ.AddProcess(subloggyOBJ.getSLprocess())

                            if os.path.isfile(outfile):
                                os.rename(outfile, infile)
                            status = 'success'

                        except ProcessError as e:
                            logger.error('Process %s :: Error', k)
                            logger.error(e)
                            status = 'error'
                            eSTR = 'Error Executing ' + k + \
                                ' Standard Error: ' + str(e)
                            RHerror.addError(os.path.splitext(
                                os.path.basename(jobFile))[0], eSTR)
                            subloggyOBJ.setStatus('ERROR')
                            subloggyOBJ.setCommand(processOBJ.LogCommandline())
                            subloggyOBJ.setHelpLink(processOBJ.LogHelpLink())
                            subloggyOBJ.errorOut(eSTR)
                            loggyOBJ.AddProcess(subloggyOBJ.getSLprocess())

                else:

                    GDALcmd = ""
                    for process, v, in processOBJ.getProcess().items():
                        subloggyOBJ = SubLoggy(process)
                        GDALcmd += process
                        for key, value in v.items():
                            GDALcmd += ' ' + key + ' ' + value

                    if RHash.Format() == 'GeoTiff-BigTiff':
                        fileext = 'tif'
                    elif RHash.Format() == 'GeoJPEG-2000':
                        fileext = 'jp2'
                    elif RHash.Format() == 'JPEG':
                        fileext = 'jpg'
                    elif RHash.Format() == 'PNG':
                        fileext = 'png'
                    elif RHash.Format() == 'GIF':
                        fileext = 'gif'

                    logGDALcmd = GDALcmd + ' ' + basename + '.input.cub ' + RHash.getMAPname() + \
                        '.' + fileext
                    finalfile = workarea + RHash.getMAPname() + '.' + fileext
#                    finalfile = infile.replace('.input.cub', '_final.' + fileext)
                    GDALcmd += ' ' + infile + ' ' + finalfile
                    print GDALcmd
                    try:
                        result = subprocess.call(GDALcmd, shell=True)
                        logger.info('Process GDAL translate :: Success')
                        status = 'success'
                        subloggyOBJ.setStatus('SUCCESS')
                        subloggyOBJ.setCommand(logGDALcmd)
                        subloggyOBJ.setHelpLink(
                            'www.gdal.org/gdal_translate.html')
                        loggyOBJ.AddProcess(subloggyOBJ.getSLprocess())
                        os.remove(infile)
                    except OSError, e:
                        logger.error('Process GDAL translate :: Error')
                        logger.error(e.stderr)
                        status = 'error'
                        RHerror.addError(os.path.splitext(os.path.basename(jobFile))[
                                         0], 'Process GDAL translate :: Error')
                        subloggyOBJ.setStatus('ERROR')
                        subloggyOBJ.setCommand(logGDALcmd)
                        subloggyOBJ.setHelpLink(
                            'http://www.gdal.org/gdal_translate.html')
                        subloggyOBJ.errorOut(e.stderr)
                        loggyOBJ.AddProcess(subloggyOBJ.getSLprocess())

        if status == 'success':
            if RHash.Format() == 'ISIS3':
                finalfile = workarea + RHash.getMAPname() + '.cub'
#                finalfile = infile.replace('.input.cub', '_final.cub')
                shutil.move(infile, finalfile)
            if RHash.getStatus() != 'ERROR':
                RHash.Status('SUCCESS')

            try:
                RQ_zip.QueueAdd(finalfile)
                logger.info('File Added to ZIP Queue')
            except:
                logger.error('File NOT Added to ZIP Queue')

            try:
                RQ_loggy.QueueAdd(loggyOBJ.Loggy2json())
                logger.info('JSON Added to Loggy Queue')
            except:
                logger.error('JSON NOT Added to Loggy Queue')

            RQ_work.QueueRemove(jobFile)
        elif status == 'error':
            RHash.Status('ERROR')
            if os.path.isfile(infile):
                os.remove(infile)

        if RQ_file.QueueSize() == 0 and RQ_work.QueueSize() == 0:
            try:
                RQ_final.QueueAdd(Key)
                logger.info('Key %s Added to Final Queue: Success', Key)
                logger.info('Job Complete')
            except:
                logger.error('Key NOT Added to Final Queue')
        else:
            logger.warning('Queues Not Empty: filequeue = %s  work queue = %s', str(
                RQ_file.QueueSize()), str(RQ_work.QueueSize()))


if __name__ == "__main__":
    sys.exit(main())
