#!/usgs/apps/anaconda/bin/python
import os
import sys
import pvl
import logging
import shutil
from pysis import isis
from pysis.exceptions import ProcessError

from RedisQueue import *
from Recipe import *

import pdb


def scaleFactor(line, sample):
    """
    Parameters
    ----------
    line : int
    sample : int

    Returns
    -------
    int
        scalefactor - ratio of sample and minSample or line and minLine
    """
    maxLine = 1000
    maxSample = 1000
    minLine = 50
    minSample = 50

    if sample < line:
        scalefactor = line/maxLine
        testsamp = int(sample/scalefactor)

        if testsamp < minSample:
            scalefactor = sample/minSample

    else:
        scalefactor = sample/maxSample
        testline = int(line/scalefactor)

        if testline < minLine:
            scalefactor = line/minLine

    return scalefactor


def makedir(inputfile):
    """
    Parameters
    ----------
    inputfile : str

    Returns
    -------
    str
        finalpath
    """

    temppath = os.path.dirname(inputfile).lower()
    finalpath = temppath.replace(
        '/pds_san/pds_archive/', '/pds_san/PDS_Derived/UPC/images/')

    if not os.path.exists(finalpath):
        try:
            os.makedirs(finalpath, 0755)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    return finalpath


def main():

    #    pdb.set_trace()

    workarea = '/scratch/pds_services/workarea/'

# ***************** Set up logging *****************
    logger = logging.getLogger('ProjectionBrowse_Process')
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Process.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    RQ_main = RedisQueue('PilotB_ReadyQueue')

    while int(RQ_main.QueueSize()) > 0:

        inputfile = RQ_main.QueueGet()
        if os.path.isfile(inputfile):
            logger.info('Starting Process: %s', inputfile)

            if 'Mars_Reconnaissance_Orbiter/CTX/' in inputfile:
                mission = 'CTX'

# ********** Derived DIR path Stuff **********************
            finalpath = makedir(inputfile)

            recipeOBJ = Recipe()
            recipe_json = recipeOBJ.getRecipeJSON(mission, 'projectionbrowse')
            recipeOBJ.AddJsonFile(recipe_json)

            infile = workarea + \
                os.path.splitext(os.path.basename(inputfile))[
                    0] + '.Pinput.cub'
            outfile = workarea + \
                os.path.splitext(os.path.basename(inputfile))[
                    0] + '.Poutput.cub'

            status = 'success'
            for item in recipeOBJ.getProcesses():
                if status == 'error':
                    break
                elif status == 'success':
                    processOBJ = Process()
                    processR = processOBJ.ProcessFromRecipe(
                        item, recipeOBJ.getRecipe())

                    if '2isis' in item:
                        processOBJ.updateParameter('from_', inputfile)
                        processOBJ.updateParameter('to', outfile)
                    elif item == 'spiceinit':
                        processOBJ.updateParameter('from_', infile)

                    elif item == 'ctxevenodd':
                        label = pvl.load(infile)
                        SS = label['IsisCube']['Instrument']['SpatialSumming']
                        if SS != 1:
                            break
                        else:
                            processOBJ.updateParameter('from_', infile)
                            processOBJ.updateParameter('to', outfile)

                    elif item == 'reduce':
                        label = pvl.load(infile)
                        Nline = label['IsisCube']['Core']['Dimensions']['Lines']
                        Nsample = label['IsisCube']['Core']['Dimensions']['Samples']
                        Sfactor = scaleFactor(Nline, Nsample)
                        processOBJ.updateParameter('lscale', Sfactor)
                        processOBJ.updateParameter('sscale', Sfactor)
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', outfile)

                    elif item == 'isis2std':
                        outfile = finalpath + '/' + \
                            os.path.splitext(os.path.basename(inputfile))[
                                0] + '.projectionbrowse.png'
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', outfile)

                    else:
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', outfile)

                    print processOBJ.getProcess()

                    for k, v in processOBJ.getProcess().items():
                        func = getattr(isis, k)
                        try:
                            func(**v)
                            logger.info('Process %s :: Success', k)
                            if os.path.isfile(outfile):
                                if '.cub' in outfile:
                                    os.rename(outfile, infile)
                            status = 'success'
                        except ProcessError as e:
                            logger.error('Process %s :: Error', k)
                            status = 'error'

            if status == 'success':
                os.remove(infile)
                logger.info('Browse Process Success: %s', inputfile)
        else:
            logger.error('File %s Not Found', inputfile)


if __name__ == "__main__":
    sys.exit(main())
