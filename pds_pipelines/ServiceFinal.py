#!/usr/bin/env python

import os
import sys
import subprocess
import logging
import shutil
import datetime
import json
import argparse
import xml.etree.ElementTree as ET

from io import BytesIO
from collections import OrderedDict
from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.RedisHash import RedisHash
from pds_pipelines.PDS_DBquery import PDS_DBquery
from pds_pipelines.config import pds_log, pow_map2_base, scratch
from pysis import ISIS_VERSION as isis_version



def renderError(errorhash):
    """
    Parameters
    ----------
    errorhash
    """
    for key in errorhash.getKeys():
        print(key)


class Args(object):
    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser(description="DI Process")

        parser.add_argument('--log', '-l', dest="log_level",
                            choices=['DEBUG', 'INFO',
                                    'WARNING', 'ERROR', 'CRITICAL'],
                            help="Set the log level.", default='INFO')

        parser.add_argument('--namespace',
                            '-n',
                            dest='namespace',
                            help="Queue namespace")

        parser.add_argument('--key',
                            '-k',
                            dest='key',
                            help='Job key')

        args = parser.parse_args()
        self.log_level = args.log_level
        self.namespace = args.namespace
        self.key = args.key


def main():

    args = Args()
    args.parse_args()
    namespace = args.namespace
    key = args.key

#***************** Setup Logging **************
    logger = logging.getLogger('ServiceFinal_' + key)
    level = logging.getLevelName(args.log_level)
    logger.setLevel(level)
    logFileHandle = logging.FileHandler(pds_log+'Service.log')

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info('Starting Final Process')
#************Set up REDIS Queues ****************
    zipQueue = RedisQueue(key + '_ZIP', namespace)
    loggyQueue = RedisQueue(key + '_loggy', namespace)
    infoHash = RedisHash(key + '_info')
    recipeQueue = RedisQueue(key + '_recipe', namespace)
    errorHash = RedisHash(key + '_error')

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
        testval = DBQO.addErrors(key , fh.getvalue())
        if testval == 'Success':
            logger.info('Error XML add to JOBS DB')
        elif testval == 'Error':
            logger.error('Addin Error XML to JOBS DB: Error')
        print(fh.getvalue())

    Fdir = pow_map2_base + infoHash.Service() + '/' + key 
    Wpath = scratch + key 

    # Make final directory
    if not os.path.exists(Fdir):
        try:
            os.makedirs(Fdir)
            logger.info('Final Location Success: %s', Fdir)
        except:
            logger.error('Error Making Final Directory')

    # Block to build job log file

    outputLOG = Wpath + "/" + key + '.log'
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
    logOBJ.write("     JOB KEY:         " + key + "\n")
    logOBJ.write("     PROCESSING DATE: " +
                 datetime.datetime.now().strftime("%Y-%m-%d %H:%M") + "\n")

    logOBJ.write("     ISIS VERSION:   " + isis_version)
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
            for proc, _ in procDICT[infile].items():
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
    Zfile = Wpath + '/' + key + '.zip'
    logger.info('Making Zip File %s', Zfile)

# log file stuff
    try:
        Lfile = key + '.log'
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

    # Add map file to zip
    try:
        map_file = Wpath + "/" + key + '.map'
        Zcmd = 'zip -j ' + Zfile + " -q " + map_file
        process = subprocess.Popen(
            Zcmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        (stdout, stderr) = process.communicate()

        logger.info('Map file %s added to zip file: Success', map_file)
        logger.info('zip stdout: ' + stdout)
        logger.info('zip stderr: ' + stderr)
    except:
        logger.error('Map File %s NOT added to Zip File', map_file)

    try:
        shutil.copyfile(map_file, Fdir + "/" + key + '.map')
        logger.info('Copied map file %s to final area: success', key + '.map')
    except IOError as e:
        logger.error('Map file %s NOT COPIED to final area', key + '.map')
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
        shutil.copy(Zfile, Fdir + '/' + key + '.zip')
        os.remove(Zfile)
        logger.info('Zip File Copied to Final Directory')
    except IOError as e:
        logger.error('Error During Zip File Copy Operation')
        logger.error(e)

#************** Clean up *******************
    os.remove(Wpath + '/' + key + '.map')
    os.remove(Wpath + '/' + key + '.sbatch')
    try:
        #        os.rmdir(Wpath)
        shutil.rmtree(Wpath)
        logger.info('Working Directory Removed: Success')
    except:
        logger.error('Working Directory NOT Removed')

    DBQO2 = PDS_DBquery('JOBS')
    DBQO2.setJobsFinished(key )

    infoHash.RemoveAll()
    loggyQueue.RemoveAll()
    zipQueue.RemoveAll()
    recipeQueue.RemoveAll()

    logger.info('Job %s is Complete', key)


if __name__ == "__main__":
    sys.exit(main())
