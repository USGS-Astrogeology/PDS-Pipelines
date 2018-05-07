#!/usgs/apps/anaconda/bin/python

import os
import subprocess
import sys
import pvl
import xml.etree.ElementTree as ET
import lxml.etree as ET
import json
import logging

from PDS_DBquery import *
from RedisQueue import *
from RedisHash import *
from Recipe import *
from MakeMap import *
from HPCjob import *

import pdb


class jobXML(object):
    """
    Information extraction from XML file

    Attributes
    ----------
    root : str
        parses an XML section from a string constant
        returns an Element instance
    """

    def __init__(self, xml):
        """
        Converts XML file to a string

        Parameters
        ----------
        xml
        """

        self.root = ET.fromstring(str(xml))

    def getInst(self):
        """
        Finds all './/Process' in 'root'

        Returns
        -------
        str
            info.find('.//instrument').text
        """

        for info in self.root.findall('.//Process'):
            inst = info.find('.//instrument').text
            return inst

    def getProjection(self):
        """
        Finds 'ProjName' in the XML file

        Returns
        -------
        str
            info.find('ProjName').text if sucessful, None otherwise
        """

        for info in self.root.iter('Projection'):
            proj = info.find('ProjName').text
            if proj is None:
                return None
            else:
                return info.find('ProjName').text

    def getClon(self):
        """
        Finds 'CenterLongitude' in the XML file 

        Returns
        -------
        str
            info.find('CenterLongitude').text if successful, None otherwise
        """

        for info in self.root.iter('Projection'):
            clon = info.find('CenterLongitude')
            if clon is None:
                return None
            else:
                return info.find('CenterLongitude').text

    def getClat(self):
        """
        Finds 'CenterLatitude' in the XML file

        Returns
        -------
        str
            info.find('CenterLatitude').text if successful, None otherwise
        """

        for info in self.root.iter('Projection'):
            clat = info.find('CenterLatitude')
            if clat is None:
                return None
            else:
                return info.find('CenterLatitude').text

    def getMinLat(self):
        """
        Finds './/MinLatitude' in the XML file

        Returns
        -------
        str
            info.find('.//MinLatitude').text if successful, None otherwise
        """

        for info in self.root.iter('extents'):
            if info.find('.//MinLatitude') is None:
                return None
            else:
                return info.find('.//MinLatitude').text

    def getMaxLat(self):
        """
        Finds './/MaxLatitude' in the XML file

        Returns
        -------
        str
            info.find('.//MaxLatitude').text if successful, None otherwise
        """

        for info in self.root.iter('extents'):
            if info.find('.//MaxLatitude') is None:
                return None
            else:
                return info.find('.//MaxLatitude').text

    def getMinLon(self):
        """
        Finds './/MinLongitude' in the XML file

        Returns
        -------
        str
            info.find('.//MinLongitude').text if successful, None otherwise
        """

        for info in self.root.iter('extents'):
            if info.find('.//MinLongitude') is None:
                return None
            else:
                return info.find('.//MinLongitude').text

    def getMaxLon(self):
        """
        Finds './/MaxLongitude' in the XML file

        Returns
        -------
        str
            info.find('.//MaxLongitude').text if successful, None otherwise
        """

        for info in self.root.iter('extents'):
            if info.find('.//MaxLongitude') is None:
                return None
            else:
                return info.find('.//MaxLongitude').text

    def getResolution(self):
        """
        Finds './/OutputResolution' in the XML file

        Returns
        -------
        str
            info.find('.//OutputResolution').text if successful, None
            otherwise
        """

        for info in self.root.iter('OutputOptions'):
            if info.find('.//OutputResolution') is None:
                return None
            else:
                return info.find('.//OutputResolution').text

    def getOutFormat(self):
        """
        Finds './/MaxLatitude' in the XML file

        Returns
        -------
        str
           outputFormat if successful, None otherwise
        """
        for info in self.root.findall('.//OutputType'):
            outputFormat = info.find('.//Format').text
            return outputFormat

    def getFileListWB(self):
        """
        Returns
        -------
        list
            listArray
        """
        
        listArray = []
        for info in self.root.iter('ImageUrl'):
            fileUrl = info.find('url').text
            testband = info.findall('.//bandfilter')
            if len(testband) == 1:
                fileout = fileUrl + "+" + testband[0].text
            elif len(testband) == 3:
                fileout = fileUrl + "+" + \
                    testband[0].text + "," + \
                    testband[1].text + "," + testband[2].text
            else:
                fileout = fileUrl

            listArray.append(fileout)

        return listArray


def main():

    #    pdb.set_trace()

    DBQO = PDS_DBquery('JOBS')
    Key = '682c4db174f41db7cb6a661ea9342d61'

    xmlOBJ = jobXML(DBQO.jobXML4Key(Key))

#*************** Setup logging ******************
    logger = logging.getLogger(Key)
    logger.setLevel(logging.INFO)

    logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/BataMOW.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info('Starting Process')

    directory = '/scratch/pds_services/' + Key
    if not os.path.exists(directory):
        os.makedirs(directory)

    logger.info('Working Area: %s', directory)

#    recipeDICT = {'CTX': '/usgs/cdev/PDS/recipe/BataMOWrecipe.json'}
    recipe = '/usgs/cdev/PDS/recipe/BataMOWrecipe.json'

    RQ_file = RedisQueue(Key + '_FileQueue')

    fileList = xmlOBJ.getFileListWB()

    for List_file in fileList:

        Input_file = List_file.replace(
            'http://pdsimage.wr.usgs.gov/Missions/', '/pds_san/PDS_Archive/')

        try:
            RQ_file.QueueAdd(Input_file)
            logger.info('File %s Added to Redis Queue', Input_file)
        except Exception as e:
            logger.warn('File %s NOT Added to Redis Queue', Input_file)
            print('Redis Queue Error', e)

    logger.info('Count of Files Queue: %s', str(RQ_file.QueueSize()))

# ************* Redis info Hash stuff ***************

    RedisH = RedisHash(Key + '_MOWinfo')
    RedisH_DICT = {}
    RedisH_DICT['minlat'] = xmlOBJ.getMinLat()
    RedisH_DICT['maxlat'] = xmlOBJ.getMaxLat()
    RedisH_DICT['minlon'] = xmlOBJ.getMinLon()
    RedisH_DICT['maxlon'] = xmlOBJ.getMaxLon()
    RedisH.AddHash(RedisH_DICT)

# ************* Map Template Stuff ******************

    mapOBJ = MakeMap()

    mapOBJ.Projection(xmlOBJ.getProjection())

    if xmlOBJ.getClon() is not None:
        mapOBJ.CLon(float(xmlOBJ.getClon()))
    if xmlOBJ.getClat() is not None:
        mapOBJ.CLat(float(xmlOBJ.getClat()))
    if xmlOBJ.getResolution() is not None:
        mapOBJ.PixelRes(float(xmlOBJ.getResolution()))

    MAPfile = directory + "/" + Key + '.map'
    mapOBJ.Map2File(MAPfile)

    try:
        f = open(MAPfile)
        f.close
        logger.info('Map File Creation: Success')
    except IOError as e:
        logger.error('Map File %s Not Found', MAPfile)

# ** End Map Template Stuff **

    testRecipeOBJ = Recipe()
    testSlist = testRecipeOBJ.TestgetStep(recipe)

    for stepitem in testSlist:
        RQ_recipe = RedisQueue(Key + '_recipe_' + stepitem)
        logger.info('Building %s Recipe', stepitem)
        subRecipeOBJ = Recipe()
        subRecipeOBJ.TestRecipe(recipe, str(stepitem))

        for processItem in subRecipeOBJ.getProcesses():
            processOBJ = Process()
            testPR = processOBJ.ProcessFromRecipe(
                processItem, subRecipeOBJ.getRecipe())

            if processItem == 'cam2map':

                processOBJ.updateParameter('map', MAPfile)

            processJSON = processOBJ.Process2JSON()

            try:
                RQ_recipe.QueueAdd(processJSON)
                logger.info(
                    'Recipe Element Added to Redis: %s : Success', processItem)
            except Exception as e:
                logger.warn(
                    'Recipe Element NOT Added to Redis: %s', processItem)
    logger.info('END: %s Recipe Build', stepitem)


# *******HPC Job submit stuff ************
    logger.info('HPC Cluster job Submission Starting')
    jobOBJ = HPCjob()
    jobOBJ.setJobName(Key + '_BataMOW')
    jobOBJ.setStdOut('/usgs/cdev/PDS/output/' + Key + '_BM1_%A_%a.out')
    jobOBJ.setStdError('/usgs/cdev/PDS/output/' + Key + '_BM1_%A_%a.err')
    jobOBJ.setWallClock('02:00:00')
    jobOBJ.setMemory('4096')
    jobOBJ.setPartition('pds')
    JAsize = RQ_file.QueueSize()
    jobOBJ.setJobArray(JAsize)
    logger.info('Job Array Size : %s', str(JAsize))
    cmd = '/usgs/cdev/PDS/bin/BataMOWProcess_1.py ' + Key
    logger.info('HPC Command: %s', cmd)
    jobOBJ.setCommand(cmd)

    SBfile = directory + '/' + Key + '_BM1.sbatch'
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
