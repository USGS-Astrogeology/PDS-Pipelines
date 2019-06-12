#!/usr/bin/env python

import os
import sys
import pvl
import lxml.etree as ET
import logging
import argparse
import json

from pds_pipelines.PDS_DBquery import PDS_DBquery
from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.RedisHash import RedisHash
from pds_pipelines.Recipe import Recipe
from pds_pipelines.Process import Process
from pds_pipelines.MakeMap import MakeMap
from pds_pipelines.HPCjob import HPCjob
from pds_pipelines.config import recipe_base, pds_log, scratch, archive_base, default_namespace, slurm_log, cmd_dir, pds_info


class jobXML(object):

    def __init__(self, xml):
        """
        Parameters
        ----------
        xml
        """
        self.pds_info = json.load(open(pds_info, 'r'))
        self.root = ET.fromstring(xml.encode())

    def getInst(self):
        """
        Returns
        -------
        str
            inst
        """
        for info in self.root.findall('.//Process'):
            inst = info.find('.//instrument').text
            return inst

    def getCleanName(self):
        """ Get the internally consistent representation of the instrument name.

        Searches the PDSinfo dict for the 'clean name' that matches the recipes.  This function essentially
        maps URL->file path->internally consistent name.
        """
        # @TODO Fix after refactor
        # NOTE: I know this is really, really bad.  We're kind of backed into a corner here,
        #  and partial string matching on a value-based lookup of a nested dict is the temporary solution.

        # Get any file listed.  Assumes that all files are from the same instrument
        file_name = self.getFileList()[0]
        file_name = file_name.replace('http://pdsimage.wr.usgs.gov/Missions/', archive_base)

        candidates = []

        for key in self.pds_info:
            if file_name.startswith(self.pds_info[key]['path']):
                candidates.append(key)

        # try to filter list based on upc_reqs.  If upc_reqs isn't specified, just skip the filtering step
        # ps can't use 'filter' because not all elements have upc_reqs, so they may raise exceptions.
        for item in candidates:
            try:
                if not all(x in file_name for x in self.pds_info[item]['upc_reqs']):
                    candidates.remove(item)
            except KeyError:
                # Intentionally left blank.  Unspecified upc_reqs is valid -- there's just nothing to do for those elements
                pass
                
        # If multiple candidates still exist, then it is not possible to uniquely identify the clean name
        if len(candidates) > 1:
            raise(RuntimeError('Multiple candidates found for {} with no resolvable clean name'.format(file_name)))

        try:
            return candidates[0]
        except IndexError:
            raise(KeyError('No key found in PDSInfo dict for path {}'.format(file_name)))


            
    def getProcess(self):
        """
        Returns
        -------
        str
            PT
        """
        for info in self.root.findall('Process'):
            PT = info.find('ProcessName').text
            return PT

    def getTargetName(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//TargetName')' is None
        str
            otherwise return 'info.find('.//TargetName').text'
        """
        for info in self.root.iter('Target'):
            if info.find('.//TargetName') is None:
                return None
            else:
                return info.find('.//TargetName').text

    def getERadius(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//EquatorialRadius')' is None
        str
            Otherwise return 'info.find('.//EquatorialRadius').text'
        """
        for info in self.root.iter('Target'):
            if info.find('.//EquatorialRadius') is None:
                return None
            else:
                return info.find('.//EquatorialRadius').text

    def getPRadius(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//PolarRadius')' is None
        str
            Otherwise return 'info.find('.//PolarRadius').text'
        """
        for info in self.root.iter('Target'):
            if info.find('.//PolarRadius') is None:
                return None
            else:
                return info.find('.//PolarRadius').text

    def getLatType(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//LatitudeType')' is None
        str
            Otherwise return 'LT'
        """
        for info in self.root.iter('Target'):
            if info.find('.//LatitudeType') is None:
                return None
            else:
                temp_LT = info.find('.//LatitudeType').text
                if temp_LT == 'planetocentric':
                    LT = 'Planetocentric'
                elif temp_LT == 'planetographic':
                    LT = 'Planetographic'
            return LT

    def getLonDirection(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//LongitudeDirection')' is None
        str
            Otherwise return 'LD'
        """
        for info in self.root.iter('Target'):
            if info.find('.//LongitudeDirection') is None:
                return None
            else:
                temp_LD = info.find('.//LongitudeDirection').text
                if temp_LD == 'POSITIVEEAST':
                    LD = 'PositiveEast'
                elif temp_LD == 'POSITIVEWEST':
                    LD = 'PositiveWest'
            return LD

    def getLonDomain(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//LongitudeDomain')' is None
        str
            otherwise return 'info.find('.//LongitudeDomain').text'
        """
        for info in self.root.iter('Target'):
            if info.find('.//LongitudeDomain') is None:
                return None
            else:
                return info.find('.//LongitudeDomain').text

    def getProjection(self):
        """
        Returns
        -------
        NoneType
            'None' if 'proj' is None
        str
            Otherwise 'info.find('ProjName').text'
        """
        for info in self.root.iter('Projection'):
            proj = info.find('ProjName').text
            if proj is None:
                return None
            else:
                return info.find('ProjName').text

    def getClon(self):
        """
        Returns
        -------
        NoneType
            'None' if 'clon' is None
        str
            Otherwise 'info.find('CenterLongitude').text'
        """
        for info in self.root.iter('Projection'):
            clon = info.find('CenterLongitude')
            if clon is None:
                return None
            else:
                return info.find('CenterLongitude').text

    def getClat(self):
        """
        Returns
        -------
        NoneType
            'None' if 'clat' is None
        str
            Otherwise 'info.find('CenterLatitude').text'
        """
        for info in self.root.iter('Projection'):
            clat = info.find('CenterLatitude')
            if clat is None:
                return None
            else:
                return info.find('CenterLatitude').text

    def getFirstParallel(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//FirstStandardParallel')' is None
        str
            Otherwise 'info.find('.//FirstStandardParallel').text'
        """
        for info in self.root.iter('Projection'):
            if info.find('.//FirstStandardParallel') is None:
                return None
            else:
                return info.find('.//FirstStandardParallel').text

    def getSecondParallel(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//SecondStandardParallel')' is None
        str
            Otherwise 'info.find('.//SecondStandardParallel').text'
        """
        for info in self.root.iter('Projection'):
            if info.find('.//SecondStandardParallel') is None:
                return None
            else:
                return info.find('.//SecondStandardParallel').text

    def OutputGeometry(self):
        """
        Returns
        -------
        NoneType
            None if 'info' is None
        bool
            True if 'info' is not None
        """
        for info in self.root.iter('OutputGeometry'):
            if info is None:
                return None
            elif info is not None:
                return True

    def getRangeType(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//extentType')' is None
        str
            Otherwise 'info.find('.//extentType').text'
        """
        for info in self.root.iter('extents'):
            if info.find('.//extentType') is None:
                return None
            else:
                return info.find('.//extentType').text

    def getMinLat(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//MinLatitude')' is None
        str
            Otherwise 'info.find('.//MinLatitude').text'
        """
        for info in self.root.iter('extents'):
            if info.find('.//MinLatitude') is None:
                return None
            else:
                return info.find('.//MinLatitude').text

    def getMaxLat(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//MaxLatitude')' is None
        str
            Otherwise 'info.find('.//MaxLatitude').text'
        """
        for info in self.root.iter('extents'):
            if info.find('.//MaxLatitude') is None:
                return None
            else:
                return info.find('.//MaxLatitude').text

    def getMinLon(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//MinLongitude')' is None
        str
            Otherwise 'info.find('.//MinLongitude').text'
        """
        for info in self.root.iter('extents'):
            if info.find('.//MinLongitude') is None:
                return None
            else:
                return info.find('.//MinLongitude').text

    def getMaxLon(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//MaxLongitude')' is None
        str
            Otherwise 'info.find('.//MaxLongitude').text'
        """
        for info in self.root.iter('extents'):
            if info.find('.//MaxLongitude') is None:
                return None
            else:
                return info.find('.//MaxLongitude').text

    def getResolution(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//OutputResolution')' is None
        str
            Otherwise 'info.find('.//OutputResolution').text'
        """
        for info in self.root.iter('OutputOptions'):
            if info.find('.//OutputResolution') is None:
                return None
            else:
                return info.find('.//OutputResolution').text

    def getGridInterval(self):
        """
        Returns
        -------
        NoneType
            'None' if 'info.find('.//interval')' is None
        str
            Otherwise 'info.find('.//interval').text'
        """
        for info in self.root.iter('grid'):
            if info.find('.//interval') is None:
                return None
            else:
                return info.find('.//interval').text

    def getOutBit(self):
        """
        Returns
        -------
        str
            'input' if 'info.find('.//BitType')' is None,
            otherwise 'info.find('.//BitType').text'
        """
        for info in self.root.findall('.//OutputType'):
            if info.find('.//BitType') is None:
                return 'input'
            else:
                return info.find('.//BitType').text

    def getOutFormat(self):
        """
        Returns
        -------
        str
            outputFormat
        """
        for info in self.root.findall('.//OutputType'):
            outputFormat = info.find('.//Format').text
            return outputFormat

    def STR_Type(self):
        """
        Returns
        -------
        NoneType
            None
        str
            'StretchPercent', 'HistogramEqualization', 'GaussStretch',
            "SigmaStretch'
        """
        for info in self.root.findall('.//Process'):
            if info.find('.//stretch') is None:
                return None
            elif info.find('.//StretchPercent') is not None:
                return 'StretchPercent'
            elif info.find('.//HistogramEqualization') is not None:
                return 'HistogramEqualization'
            elif info.find('.//GaussStretch') is not None:
                return 'GaussStretch'
            elif info.find('.//SigmaStretch') is not None:
                return 'SigmaStretch'

    def STR_PercentMin(self):
        """
        Returns
        -------
        NoneType
            None
        str
            info.find('.//min').text
        """
        for info in self.root.findall('.//Process'):
            if info.find('.//min') is None:
                return None
            else:
                return info.find('.//min').text

    def STR_PercentMax(self):
        """
        Returns
        -------
        NoneType
            None
        str
            info.find('.//max').text
        """
        for info in self.root.findall('.//Process'):
            if info.find('.//max') is None:
                return None
            else:
                return info.find('.//max').text

    def STR_GaussSigma(self):
        """
        Returns
        -------
        str
            info.find('.//gsigma').text
        """
        for info in self.root.findall('.//Process'):
            return info.find('.//gsigma').text

    def STR_SigmaVariance(self):
        """
        Returns
        -------
        str
            info.find('.//variance').text
        """
        for info in self.root.findall('.//Process'):
            return info.find('.//variance').text

    def getBand(self):
        for info in self.root.iter('bands'):
            testband = info.findall('.//bandfilter')
            print(len(testband))
            for test in testband:
                print("test")
                print(test.text)

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

    def getMFileListWB(self):
        """
        Returns
        -------
        list
            listArray
        """
        listArray = []
        for info in self.root.iter('ImageList'):
            Mfile = info.find('.//internalpath').text
            testband = info.findall('.//band')
            if len(testband) == 1:
                fileout = Mfile + "+" + testband[0].text
            elif len(testband) == 3:
                fileout = Mfile + "+" + \
                    testband[0].text + "," + \
                    testband[1].text + "," + testband[2].text
            else:
                fileout = Mfile

            listArray.append(fileout)

        return listArray

    def getFileList(self):
        """
        Returns
        -------
        list
            listArray
        """
        listArray = []
        for info in self.root.iter('ImageUrl'):
            fileUrl = info.find('url').text
            listArray.append(fileUrl)

        return listArray


class Args(object):

    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser(description='Service job manager')
        parser.add_argument('--key',
                            '-k',
                            dest='key',
                            help="Target key -- if blank, process first element in queue")
        parser.add_argument('--namespace',
                            '-n',
                            dest='namespace',
                            help="Queue namespace")
        parser.add_argument('--norun',
                            help="Set up queues and write out SBATCH script, but do not submit it to SLURM",
                            action="store_true")

        args = parser.parse_args()
        self.key = args.key
        self.namespace = args.namespace
        self.norun = args.norun

def main():
    args = Args()
    args.parse_args()
    key = args.key
    namespace = args.namespace

    if namespace is None:
        namespace = default_namespace

    # Set up logging
    logger = logging.getLogger(key)
    logger.setLevel(logging.INFO)

    logFileHandle = logging.FileHandler(pds_log + 'Service.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    # Connect to database and access 'jobs' table
    DBQO = PDS_DBquery('JOBS')
    if key is None:
        # If no key is specified, grab the first key
        try:
            key = DBQO.jobKey()
            try:
                key = key.decode('utf-8')
            except:
                pass
        # If the queue is empty, it'll throw a type error.
        except TypeError:
            logger.debug('No keys found in clusterjobs database')
            exit(1)
    try:
        # Set the 'queued' column to current time i.e. prep for processing
        DBQO.setJobsQueued(key)
    except KeyError as e:
        logger.error('%s', e)
        exit(1)

    logger.info('Starting Process')

    xmlOBJ = jobXML(DBQO.jobXML4Key(key))

    # Make directory if it doesn't exist
    directory = scratch + key
    if not os.path.exists(directory):
        os.makedirs(directory)

    logger.info('Working Area: %s', directory)


    # Set up Redis Hash for ground range
    RedisH = RedisHash(key + '_info')
    RedisH.RemoveAll()
    RedisErrorH = RedisHash(key + '_error')
    RedisErrorH.RemoveAll()
    RedisH_DICT = {}
    RedisH_DICT['service'] = xmlOBJ.getProcess()
    RedisH_DICT['fileformat'] = xmlOBJ.getOutFormat()
    RedisH_DICT['outbit'] = xmlOBJ.getOutBit()
    if xmlOBJ.getRangeType() is not None:
        RedisH_DICT['grtype'] = xmlOBJ.getRangeType()
        RedisH_DICT['minlat'] = xmlOBJ.getMinLat()
        RedisH_DICT['maxlat'] = xmlOBJ.getMaxLat()
        RedisH_DICT['minlon'] = xmlOBJ.getMinLon()
        RedisH_DICT['maxlon'] = xmlOBJ.getMaxLon()

    if RedisH.IsInHash('service'):
        pass
    else:
        RedisH.AddHash(RedisH_DICT)
    if RedisH.IsInHash('service'):
        logger.info('Redis info Hash: Success')
    else:
        logger.error('Redis info Hash Not Found')

    # End ground range

    RQ_recipe = RedisQueue(key + '_recipe', namespace)
    RQ_recipe.RemoveAll()
    RQ_file = RedisQueue(key + '_FileQueue', namespace)
    RQ_file.RemoveAll()
    RQ_WorkQueue = RedisQueue(key + '_WorkQueue', namespace)
    RQ_WorkQueue.RemoveAll()
    RQ_loggy = RedisQueue(key + '_loggy', namespace)
    RQ_loggy.RemoveAll()
    RQ_zip = RedisQueue(key + '_ZIP', namespace)
    RQ_zip.RemoveAll()

    if xmlOBJ.getProcess() == 'POW':
        fileList = xmlOBJ.getFileListWB()
    elif xmlOBJ.getProcess() == 'MAP2':
        fileList = xmlOBJ.getMFileListWB()

    for List_file in fileList:

        # Input and output file naming and path stuff
        if xmlOBJ.getProcess() == 'POW':
            if xmlOBJ.getInst() == 'THEMIS_IR':
                Input_file = List_file.replace('odtie1_', 'odtir1_')
                Input_file = Input_file.replace('xxedr', 'xxrdr')
                Input_file = Input_file.replace('EDR.QUB', 'RDR.QUB')
                Input_file = Input_file.replace(
                    'http://pdsimage.wr.usgs.gov/Missions/', archive_base)
            elif xmlOBJ.getInst() == 'ISSNA':
                Input_file = List_file.replace('.IMG', '.LBL')
                Input_file = Input_file.replace(
                    'http://pdsimage.wr.usgs.gov/Missions/', archive_base)
            elif xmlOBJ.getInst() == 'ISSWA':
                Input_file = List_file.replace('.IMG', '.LBL')
                Input_file = Input_file.replace(
                    'http://pdsimage.wr.usgs.gov/Missions/', archive_base)
            elif xmlOBJ.getInst() == 'SOLID STATE IMAGING SYSTEM':
                Input_file = List_file.replace('.img', '.lbl')
                Input_file = Input_file.replace(
                    'http://pdsimage.wr.usgs.gov/Missions/', archive_base)
            else:
                Input_file = List_file.replace(
                    'http://pdsimage.wr.usgs.gov/Missions/', archive_base)

        elif xmlOBJ.getProcess() == 'MAP2':
            Input_file = List_file.replace('file://pds_san', '/pds_san')

            if '+' in Input_file:
                tempsplit = Input_file.split('+')
                tempFile = tempsplit[0]
            else:
                tempFile = Input_file
            label = pvl.load(tempFile)
    # Output final file naming
            Tbasename = os.path.splitext(os.path.basename(tempFile))[0]
            splitBase = Tbasename.split('_')

            labP = xmlOBJ.getProjection()
            if labP == 'INPUT':
                lab_proj = label['IsisCube']['Mapping']['ProjectionName'][0:4]
            else:
                lab_proj = labP[0:4]

            if xmlOBJ.getClat() is None or xmlOBJ.getClon() is None:
                basefinal = splitBase[0] + splitBase[1] + \
                    splitBase[2] + '_MAP2_' + lab_proj.upper()
            else:
                lab_clat = float(xmlOBJ.getClat())
                if lab_clat >= 0:
                    labH = 'N'
                elif lab_clat < 0:
                    labH = 'S'
                lab_clon = float(xmlOBJ.getClon())

                basefinal = splitBase[0] + splitBase[1] + splitBase[2] + '_MAP2_' + str(
                    lab_clat) + labH + str(lab_clon) + '_' + lab_proj.upper()
            RedisH.MAPname(basefinal)

        try:
            RQ_file.QueueAdd(Input_file)
            logger.info('File %s Added to Redis Queue', Input_file)
        except Exception as e:
            logger.warn('File %s NOT Added to Redis Queue', Input_file)
            print('Redis Queue Error', e)
    RedisH.FileCount(RQ_file.QueueSize())
    logger.info('Count of Files Queue: %s', str(RQ_file.QueueSize()))

    # Map Template Stuff
    logger.info('Making Map File')
    mapOBJ = MakeMap()

    if xmlOBJ.getProcess() == 'MAP2' and xmlOBJ.getProjection() == 'INPUT':
        proj = label['IsisCube']['Mapping']['ProjectionName']
        mapOBJ.Projection(proj)
    else:
        mapOBJ.Projection(xmlOBJ.getProjection())

    if xmlOBJ.getClon() is not None:
        mapOBJ.CLon(float(xmlOBJ.getClon()))
    if xmlOBJ.getClat() is not None:
        mapOBJ.CLat(float(xmlOBJ.getClat()))
    if xmlOBJ.getFirstParallel() is not None:
        mapOBJ.FirstParallel(float(xmlOBJ.getFirstParallel()))
    if xmlOBJ.getSecondParallel() is not None:
        mapOBJ.SecondParallel(float(xmlOBJ.getSecondParallel()))
    if xmlOBJ.getResolution() is not None:
        mapOBJ.PixelRes(float(xmlOBJ.getResolution()))
    if xmlOBJ.getTargetName() is not None:
        mapOBJ.Target(xmlOBJ.getTargetName())
    if xmlOBJ.getERadius() is not None:
        mapOBJ.ERadius(float(xmlOBJ.getERadius()))
    if xmlOBJ.getPRadius() is not None:
        mapOBJ.PRadius(float(xmlOBJ.getPRadius()))
    if xmlOBJ.getLatType() is not None:
        mapOBJ.LatType(xmlOBJ.getLatType())
    if xmlOBJ.getLonDirection() is not None:
        mapOBJ.LonDirection(xmlOBJ.getLonDirection())
    if xmlOBJ.getLonDomain() is not None:
        mapOBJ.LonDomain(int(xmlOBJ.getLonDomain()))

    if xmlOBJ.getProcess() == 'MAP2':
        if xmlOBJ.getMinLat() is not None:
            mapOBJ.MinLat(float(xmlOBJ.getMinLat()))
        if xmlOBJ.getMaxLat() is not None:
            mapOBJ.MaxLat(float(xmlOBJ.getMaxLat()))
        if xmlOBJ.getMinLon() is not None:
            mapOBJ.MinLon(float(xmlOBJ.getMinLon()))
        if xmlOBJ.getMaxLon() is not None:
            mapOBJ.MaxLon(float(xmlOBJ.getMaxLon()))

    mapOBJ.Map2pvl()

    MAPfile = directory + "/" + key + '.map'
    mapOBJ.Map2File(MAPfile)

    try:
        f = open(MAPfile)
        f.close
        logger.info('Map File Creation: Success')
    except IOError as e:
        logger.error('Map File %s Not Found', MAPfile)

    # ** End Map Template Stuff **

    logger.info('Building Recipe')
    recipeOBJ = Recipe()
    if xmlOBJ.getProcess() == 'POW':
        recipeOBJ.AddJsonFile(recipe_base + xmlOBJ.getCleanName() + '.json', "pow")
    elif xmlOBJ.getProcess() == 'MAP2':
        recipeOBJ.AddJsonFile(recipe_base + "map2_process.json", "map")
    # Test for stretch and add to recipe
    # if MAP2 and 8 or 16 bit run stretch to set range

    if xmlOBJ.getOutBit() == 'input':
        testBitType = str(label['IsisCube']['Core']['Pixels']['Type']).upper()
    else:
        testBitType = xmlOBJ.getOutBit().upper()

    if xmlOBJ.getProcess() == 'MAP2' and xmlOBJ.STR_Type() is None:
        if str(label['IsisCube']['Core']['Pixels']['Type']).upper() != xmlOBJ.getOutBit().upper() and str(label['IsisCube']['Core']['Pixels']['Type']).upper() != 'REAL':
            if str(label['IsisCube']['Core']['Pixels']['Type']).upper() == 'SIGNEDWORD':
                strpairs = '0:-32765 0:-32765 100:32765 100:32765'
            elif str(label['IsisCube']['Core']['Pixels']['Type']).upper() == 'UNSIGNEDBYTE':
                strpairs = '0:1 0:1 100:254 100:254'

            STRprocessOBJ = Process()
            STRprocessOBJ.newProcess('stretch')
            STRprocessOBJ.AddParameter('from_', 'value')
            STRprocessOBJ.AddParameter('to', 'value')
            STRprocessOBJ.AddParameter('usepercentages', 'yes')
            STRprocessOBJ.AddParameter('pairs', strpairs)
            recipeOBJ.AddProcess(STRprocessOBJ.getProcess())

    strType = xmlOBJ.STR_Type()
    if strType == 'StretchPercent' and xmlOBJ.STR_PercentMin() is not None and xmlOBJ.STR_PercentMax() is not None and testBitType != 'REAL':
        if float(xmlOBJ.STR_PercentMin()) != 0 and float(xmlOBJ.STR_PercentMax()) != 100:
            if testBitType == 'UNSIGNEDBYTE':
                strpairs = '0:1 ' + xmlOBJ.STR_PercentMin() + ':1 ' + \
                    xmlOBJ.STR_PercentMax() + ':254 100:254'
            elif testBitType == 'SIGNEDWORD':
                strpairs = '0:-32765 ' + xmlOBJ.STR_PercentMin() + ':-32765 ' + \
                    xmlOBJ.STR_PercentMax() + ':32765 100:32765'

            STRprocessOBJ = Process()
            STRprocessOBJ.newProcess('stretch')
            STRprocessOBJ.AddParameter('from_', 'value')
            STRprocessOBJ.AddParameter('to', 'value')
            STRprocessOBJ.AddParameter('usepercentages', 'yes')
            STRprocessOBJ.AddParameter('pairs', strpairs)
            recipeOBJ.AddProcess(STRprocessOBJ.getProcess())

    elif strType == 'GaussStretch':
        STRprocessOBJ = Process()
        STRprocessOBJ.newProcess('gaussstretch')
        STRprocessOBJ.AddParameter('from_', 'value')
        STRprocessOBJ.AddParameter('to', 'value')
        STRprocessOBJ.AddParameter('gsigma', xmlOBJ.STR_GaussSigma())
        recipeOBJ.AddProcess(STRprocessOBJ.getProcess())

    elif strType == 'HistogramEqualization':
        STRprocessOBJ = Process()
        STRprocessOBJ.newProcess('histeq')
        STRprocessOBJ.AddParameter('from_', 'value')
        STRprocessOBJ.AddParameter('to', 'value')
        if xmlOBJ.STR_PercentMin() is None:
            STRprocessOBJ.AddParameter('minper', '0')
        else:
            STRprocessOBJ.AddParameter('minper', xmlOBJ.STR_PercentMin())
        if xmlOBJ.STR_PercentMax() is None:
            STRprocessOBJ.AddParameter('maxper', '100')
        else:
            STRprocessOBJ.AddParameter('maxper', xmlOBJ.STR_PercentMax())
        recipeOBJ.AddProcess(STRprocessOBJ.getProcess())

    elif strType == 'SigmaStretch':
        STRprocessOBJ = Process()
        STRprocessOBJ.newProcess('sigmastretch')
        STRprocessOBJ.AddParameter('from_', 'value')
        STRprocessOBJ.AddParameter('to', 'value')
        STRprocessOBJ.AddParameter('variance', xmlOBJ.STR_SigmaVariance())
        recipeOBJ.AddProcess(STRprocessOBJ.getProcess())


    # Test for output bit type and add to recipe
    if xmlOBJ.getProcess() == 'POW':
        if xmlOBJ.getOutBit().upper() == 'UNSIGNEDBYTE' or xmlOBJ.getOutBit().upper() == 'SIGNEDWORD':
            CAprocessOBJ = Process()
            CAprocessOBJ.newProcess('cubeatt-bit')
            CAprocessOBJ.AddParameter('from_', 'value')
            CAprocessOBJ.AddParameter('to', 'value')
            recipeOBJ.AddProcess(CAprocessOBJ.getProcess())
    elif xmlOBJ.getProcess() == 'MAP2':
        if xmlOBJ.getOutBit().upper() != 'INPUT':
            if xmlOBJ.getOutBit().upper() == 'UNSIGNEDBYTE' or xmlOBJ.getOutBit().upper() == 'SIGNEDWORD':
                if str(label['IsisCube']['Core']['Pixels']['Type']).upper() != xmlOBJ.getOutBit().upper():
                    CAprocessOBJ = Process()
                    CAprocessOBJ.newProcess('cubeatt-bit')
                    CAprocessOBJ.AddParameter('from_', 'value')
                    CAprocessOBJ.AddParameter('to', 'value')
                    recipeOBJ.AddProcess(CAprocessOBJ.getProcess())

    # Add Grid(MAP2)
    if xmlOBJ.getGridInterval() is not None:
        GprocessOBJ = Process()
        GprocessOBJ.newProcess('grid')
        GprocessOBJ.AddParameter('from_', 'value')
        GprocessOBJ.AddParameter('to', 'value')
        GprocessOBJ.AddParameter('latinc', xmlOBJ.getGridInterval())
        GprocessOBJ.AddParameter('loninc', xmlOBJ.getGridInterval())
        GprocessOBJ.AddParameter('outline', 'yes')
        GprocessOBJ.AddParameter('boundary', 'yes')
        GprocessOBJ.AddParameter('linewidth', '3')
        recipeOBJ.AddProcess(GprocessOBJ.getProcess())

    # OUTPUT FORMAT
    # Test for GDAL and add to recipe
    Oformat = xmlOBJ.getOutFormat()
    if Oformat == 'GeoTiff-BigTiff' or Oformat == 'GeoJPEG-2000' or Oformat == 'JPEG' or Oformat == 'PNG':
        if Oformat == 'GeoJPEG-2000':
            Oformat = 'JP2KAK'
        if Oformat == 'GeoTiff-BigTiff':
            Oformat = 'GTiff'
        GDALprocessOBJ = Process()
        GDALprocessOBJ.newProcess('gdal_translate')
        if xmlOBJ.getOutBit() != 'input':
            GDALprocessOBJ.AddParameter(
                '-ot', GDALprocessOBJ.GDAL_OBit(xmlOBJ.getOutBit()))
        GDALprocessOBJ.AddParameter('-of', Oformat)

        if Oformat == 'GTiff' or Oformat == 'JP2KAK' or Oformat == 'JPEG':
            GDALprocessOBJ.AddParameter(
                '-co', GDALprocessOBJ.GDAL_Creation(Oformat))

        recipeOBJ.AddProcess(GDALprocessOBJ.getProcess())
    # set up pds2isis and add to recipe
    elif Oformat == 'PDS':
        pdsProcessOBJ = Process()
        pdsProcessOBJ.newProcess('isis2pds')
        pdsProcessOBJ.AddParameter('from_', 'value')
        pdsProcessOBJ.AddParameter('to', 'value')
        if xmlOBJ.getOutBit() == 'unsignedbyte':
            pdsProcessOBJ.AddParameter('bittype', '8bit')
        elif xmlOBJ.getOutBit() == 'signedword':
            pdsProcessOBJ.AddParameter('bittype', 's16bit')

        recipeOBJ.AddProcess(pdsProcessOBJ.getProcess())

    for item in recipeOBJ.getProcesses():
        processOBJ = Process()
        processOBJ.ProcessFromRecipe(item, recipeOBJ.getRecipe())

        if item == 'cam2map':

            processOBJ.updateParameter('map', MAPfile)

            if xmlOBJ.getResolution() is None:
                processOBJ.updateParameter('pixres', 'CAMERA')
            else:
                processOBJ.updateParameter('pixres', 'MAP')

            if xmlOBJ.getRangeType() is None:
                processOBJ.updateParameter('defaultrange', 'MINIMIZE')
            elif xmlOBJ.getRangeType() == 'smart' or xmlOBJ.getRangeType() == 'fill':
                processOBJ.updateParameter('defaultrange', 'CAMERA')
                processOBJ.AddParameter('trim', 'YES')

        elif item == 'map2map':
            processOBJ.updateParameter('map', MAPfile)
            if xmlOBJ.getResolution() is None:
                processOBJ.updateParameter('pixres', 'FROM')
            else:
                processOBJ.updateParameter('pixres', 'MAP')

            if xmlOBJ.OutputGeometry() is not None:
                processOBJ.updateParameter('defaultrange', 'MAP')
                processOBJ.AddParameter('trim', 'YES')
            else:
                processOBJ.updateParameter('defaultrange', 'FROM')

        processJSON = processOBJ.Process2JSON()
        try:
            RQ_recipe.QueueAdd(processJSON)
            logger.info('Recipe Element Added to Redis: %s : Success', item)
        except Exception as e:
            logger.warn('Recipe Element NOT Added to Redis: %s', item)

    # HPC job stuff
    logger.info('HPC Cluster job Submission Starting')
    jobOBJ = HPCjob()
    jobOBJ.setJobName(key + '_Service')
    jobOBJ.setStdOut(slurm_log + key + '_%A_%a.out')
    jobOBJ.setStdError(slurm_log + key + '_%A_%a.err')
    jobOBJ.setWallClock('24:00:00')
    jobOBJ.setMemory('24576')
    jobOBJ.setPartition('pds')
    JAsize = RQ_file.QueueSize()
    jobOBJ.setJobArray(JAsize)
    logger.info('Job Array Size : %s', str(JAsize))

    # @TODO replace with source activate <env>
    #jobOBJ.addPath('/usgs/apps/anaconda/bin')

    # Whether or not we use the default namespace, this guarantees that the POW/MAP queues will match the namespace
    #  used in the job manager.
    if xmlOBJ.getProcess() == 'POW':
        cmd = cmd_dir + "POWprocess.py -k {} -n {}".format(key, namespace)
    elif xmlOBJ.getProcess() == 'MAP2':
        cmd = cmd_dir + "MAPprocess.py -k {} -n {}".format(key, namespace)

    logger.info('HPC Command: %s', cmd)
    jobOBJ.setCommand(cmd)

    SBfile = directory + '/' + key + '.sbatch'
    jobOBJ.MakeJobFile(SBfile)

    try:
        sb = open(SBfile)
        sb.close
        logger.info('SBATCH File Creation: Success')
    except IOError as e:
        logger.error('SBATCH File %s Not Found', SBfile)


    if args.norun:
        logger.info('No-run mode, will not submit HPC job.')
    else:
        try:
            jobOBJ.Run()
            logger.info('Job Submission to HPC: Success')
            DBQO.setJobsStarted(key)
        except IOError as e:
            logger.error('Jobs NOT Submitted to HPC')


if __name__ == "__main__":
    sys.exit(main())
