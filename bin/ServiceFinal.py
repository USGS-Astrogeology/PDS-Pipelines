#!/usgs/apps/anaconda/bin/python

import os
import sys
import subprocess
import logging
import shutil
import zipfile
import datetime
import json

from io import BytesIO
from collections import OrderedDict
from RedisQueue import *
from RedisHash import *
from PDS_DBquery import *

#from xml.etree.ElementTree import Element, SubElement, Comment, tostring

import xml.etree.ElementTree as ET
import lxml.etree as etree

import pdb


def renderError(errorhash):
    """
    Parameters
    ----------
    errorhash
    """
    for key in errorhash.getKeys():
        print key
        print val


def main():

    #    pdb.set_trace()
    FKey = sys.argv[-1]
#    FKey = "0f9ce6e5d6c9f241a3e4c2704d9e2c83"

#***************** Setup Logging **************
    logger = logging.getLogger('ServiceFinal.' + FKey)
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Service.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info('Starting Final Process')
#************Set up REDIS Queues ****************
    zipQueue = RedisQueue(FKey + '_ZIP')
    loggyQueue = RedisQueue(FKey + '_loggy')
    infoHash = RedisHash(FKey + '_info')
    recipeQueue = RedisQueue(FKey + '_recipe')
    errorHash = RedisHash(FKey + '_error')

    DBQO = PDS_DBquery('JOBS')

    if errorHash.HashCount() > 0:
        root = ET.Element('errors')

        test = errorHash.getKeys()
        for key in test:
            sub = ET.Element('error')
            root.append(sub)

            field1 = ET.SubElement(sub, 'file')
            field1.text = key

            Eval = errorHash.getError(key)

            field2 = ET.SubElement(sub, 'message')
            field2.text = Eval

        tree = ET.ElementTree(root)

#        testfile = 'test.xml'
#        with open(testfile, "w") as fh:

        fh = BytesIO()
        tree.write(fh, encoding='utf-8', xml_declaration=True)
        testval = DBQO.addErrors(FKey, fh.getvalue())
        if testval == 'Success':
            logger.info('Error XML add to JOBS DB')
        elif testval == 'Error':
            logger.error('Addin Error XML to JOBS DB: Error')
        print(fh.getvalue())

    Fdir = '/pds_san/PDS_Services/' + infoHash.Service() + '/' + FKey
#    Fdir = '/scratch/bsucharski/PDS_service/' + FKey
    Wpath = '/scratch/pds_services/' + FKey
#********* Make final directory ************
    if not os.path.exists(Fdir):
        try:
            os.makedirs(Fdir)
            logger.info('Final Location Success: %s', Fdir)
        except:
            logger.error('Error Making Final Directory')

#********** Block to build job log file **************

    outputLOG = Wpath + "/" + FKey + '.log'
    logOBJ = open(outputLOG, "w")

    logOBJ.write("       U.S. Geological Survey Cloud Processing Services\n")
    logOBJ.write("                http://astrocloud.wr.usgs.gov\n\n")

    if infoHash.Service() == 'POW':
        logOBJ.write("                 Processing On the Web(POW)\n\n")

    logOBJ.write("       Processing Provided by ASTROGEOLOGY USGS Flagstaff\n")
    logOBJ.write("              Contact Information: astroweb@usgs.gov\n\n")
    logOBJ.write(
        "____________________________________________________________________\n\n")

    logOBJ.write("JOB INFORMATION\n\n")
    logOBJ.write("     SERVICE:         " + infoHash.Service() + "\n")
    logOBJ.write("     JOB KEY:         " + FKey + "\n")
    logOBJ.write("     PROCESSING DATE: " +
                 datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + "\n")

    isisV = subprocess.check_output(['ls', '-la',  '/usgs/pkgs/isis3'])
    isisA = isisV.split('>')
    logOBJ.write("     ISIS VERSION:   " + isisA[-1])
    if infoHash.getStatus() == 'ERROR':
        logOBJ.write("     JOB STATUS:      " +
                     infoHash.getStatus() + " See Details Below\n")
    else:
        logOBJ.write("     JOB STATUS:      " + infoHash.getStatus() + "\n")
    logOBJ.write("     FILE COUNT:      " + infoHash.getFileCount() + "\n\n")
    logOBJ.write(
        "_____________________________________________________________________\n\n")

    logOBJ.write("PROCESSING INFORMATION\n\n")
    for element in loggyQueue.ListGet():
        procDICT = json.loads(element, object_pairs_hook=OrderedDict)
        for infile in procDICT:
            logOBJ.write("     IMAGE: " + infile + "\n")
            for proc, testD in procDICT[infile].items():
                logOBJ.write("          PROCESS:  " + str(proc) + "\n")
                for k, val in procDICT[infile][proc].items():
                    if k == 'status':
                        logOBJ.write(
                            "               STATUS:     " + val + "\n")
                    elif k == 'command':
                        logOBJ.write(
                            "               COMMAND:    " + val + "\n")
                    elif k == 'helplink':
                        logOBJ.write(
                            "               HELP LINK:  " + val + "\n\n")
                    elif k == 'error':
                        logOBJ.write(
                            "               ERROR:      " + val + "\n\n")

    logOBJ.write("END-PROCESSING\n")
    logOBJ.close()

#******** Block for to copy and zip files to final directory ******
    Zfile = Wpath + '/' + FKey + '.zip'
    logger.info('Making Zip File %s', Zfile)

# log file stuff
    try:
        Lfile = FKey + '.log'
        Zcmd = 'zip -j ' + Zfile + " -q " + outputLOG
        process = subprocess.Popen(
            Zcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        (stdout, stderr) = process.communicate()
#        zOBJ.write(outputLOG, arcname=Lfile)
        logger.info('Log file %s Added to Zip File: Success', Lfile)
        logger.info('zip stdout: ' + stdout)
        logger.info('zip stderr: ' + stderr)
    except:
        logger.error('Log File %s NOT Added to Zip File', Lfile)

    try:
        shutil.copyfile(outputLOG, Fdir + "/" + Lfile)
        logger.info('Copied Log File %s to Final Area: Success', Lfile)
        os.remove(outputLOG)
    except IOError as e:
        logger.error('Log File %s NOT COPIED to Final Area', Lfile)
        logger.error(e)

# file stuff
    for Lelement in zipQueue.ListGet():
        Pfile = os.path.basename(Lelement)
#        auxfile = os.path.basename(Lelement) + '.aux.xml'
        auxfile = Wpath + '/' + os.path.basename(Lelement) + '.aux.xml'

        try:
            Zcmd = 'zip -j ' + Zfile + " -q " + Lelement
            process = subprocess.Popen(
                Zcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            (stdout, stderr) = process.communicate()
            logger.info('File %s Added to Zip File: Success', Pfile)
            if os.path.isfile(auxfile):
                Zcmd = 'zip -j ' + Zfile + " -q " + auxfile
                process = subprocess.Popen(
                    Zcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                (stdout, stderr) = process.communicate()
                logger.info('File %s Added to Zip File: Success',
                            os.path.basename(Lelement) + '.aux.xml')
        except:
            logger.error('Error During Zip Operation')

        try:
            shutil.copyfile(Wpath + '/' + Pfile, Fdir + '/' + Pfile)
            logger.info('Copy File %s : Success', Pfile)
            os.remove(Wpath + "/" + Pfile)
            if os.path.isfile(auxfile):
                shutil.copyfile(auxfile, Fdir + '/' +
                                os.path.basename(Lelement) + '.aux.xml')
                logger.info('Copy File %s : Success',
                            os.path.basename(Lelement) + '.aux.xml')
                os.remove(auxfile)
        except IOError as e:
            logger.error('Error During File Copy Operation')
            logger.error(e)

#    zOBJ.close()

    try:
        shutil.copy(Zfile, Fdir + '/' + FKey + '.zip')
        os.remove(Zfile)
        logger.info('Zip File Copied to Final Directory')
    except IOError as e:
        logger.error('Error During Zip File Copy Operation')
        logger.error(e)

#************** Clean up *******************
    os.remove(Wpath + '/' + FKey + '.map')
    os.remove(Wpath + '/' + FKey + '.sbatch')
    try:
        #        os.rmdir(Wpath)
        shutil.rmtree(Wpath)
        logger.info('Working Directory Removed: Success')
    except:
        logger.error('Working Directory NOT Removed')

    DBQO2 = PDS_DBquery('JOBS')
    DBQO2.setJobsFinished(FKey)

    infoHash.RemoveAll()
    loggyQueue.RemoveAll()
    zipQueue.RemoveAll()
    recipeQueue.RemoveAll()

    logger.info('Job %s is Complete', FKey)


if __name__ == "__main__":
    sys.exit(main())
