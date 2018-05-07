#!/usgs/apps/anaconda/bin/python

import os
import subprocess
import sys
import pvl
import xml.etree.ElementTree as ET
import lxml.etree as ET
import json
import logging

from hashlib import md5
from collections import OrderedDict

from PDS_DBquery import *
from RedisQueue import *
from RedisHash import *
from Recipe import *
from MakeMap import *
from HPCjob import *

import pdb


class jobXML(object):

    def __init__(self, xml):

        self.root = ET.fromstring(str(xml))

    def getInst(self):
        for info in self.root.findall('.//Process'):
            inst = info.find('.//instrument').text
            return inst

    def getProcess(self):
        for info in self.root.findall('Process'):
            PT = info.find('ProcessName').text
            return PT

    def getTargetName(self):
        for info in self.root.iter('Target'):
            if info.find('.//TargetName') is None:
                return None
            else:
                return info.find('.//TargetName').text

    def getERadius(self):
        for info in self.root.iter('Target'):
            if info.find('.//EquatorialRadius') is None:
                return None
            else:
                return info.find('.//EquatorialRadius').text

    def getPRadius(self):
        for info in self.root.iter('Target'):
            if info.find('.//PolarRadius') is None:
                return None
            else:
                return info.find('.//PolarRadius').text

    def getLatType(self):
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
        for info in self.root.iter('Target'):
            if info.find('.//LongitudeDomain') is None:
                return None
            else:
                return info.find('.//LongitudeDomain').text

    def getProjection(self):
        for info in self.root.iter('Projection'):
            proj = info.find('ProjName').text
            if proj is None:
                return None
            else:
                return info.find('ProjName').text

    def getClon(self):
        for info in self.root.iter('Projection'):
            clon = info.find('CenterLongitude')
            if clon is None:
                return None
            else:
                return info.find('CenterLongitude').text

    def getClat(self):
        for info in self.root.iter('Projection'):
            clat = info.find('CenterLatitude')
            if clat is None:
                return None
            else:
                return info.find('CenterLatitude').text

    def getFirstParallel(self):
        for info in self.root.iter('Projection'):
            if info.find('.//FirstStandardParallel') is None:
                return None
            else:
                return info.find('.//FirstStandardParallel').text

    def getSecondParallel(self):
        for info in self.root.iter('Projection'):
            if info.find('.//SecondStandardParallel') is None:
                return None
            else:
                return info.find('.//SecondStandardParallel').text

    def OutputGeometry(self):
        for info in self.root.iter('OutputGeometry'):
            if info is None:
                return None
            elif info is not None:
                return True

    def getRangeType(self):
        for info in self.root.iter('extents'):
            if info.find('.//extentType') is None:
                return None
            else:
                return info.find('.//extentType').text

    def getMinLat(self):
        for info in self.root.iter('extents'):
            if info.find('.//MinLatitude') is None:
                return None
            else:
                return info.find('.//MinLatitude').text

    def getMaxLat(self):
        for info in self.root.iter('extents'):
            if info.find('.//MaxLatitude') is None:
                return None
            else:
                return info.find('.//MaxLatitude').text

    def getMinLon(self):
        for info in self.root.iter('extents'):
            if info.find('.//MinLongitude') is None:
                return None
            else:
                return info.find('.//MinLongitude').text

    def getMaxLon(self):
        for info in self.root.iter('extents'):
            if info.find('.//MaxLongitude') is None:
                return None
            else:
                return info.find('.//MaxLongitude').text

    def getResolution(self):
        for info in self.root.iter('OutputOptions'):
            if info.find('.//OutputResolution') is None:
                return None
            else:
                return info.find('.//OutputResolution').text

    def getGridInterval(self):
        for info in self.root.iter('grid'):
            if info.find('.//interval') is None:
                return None
            else:
                return info.find('.//interval').text

    def getOutBit(self):
        for info in self.root.findall('.//OutputType'):
            if info.find('.//BitType') is None:
                return 'input'
            else:
                return info.find('.//BitType').text

    def getOutFormat(self):
        for info in self.root.findall('.//OutputType'):
            outputFormat = info.find('.//Format').text
            return outputFormat

    def STR_Type(self):
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
        for info in self.root.findall('.//Process'):
            if info.find('.//min') is None:
                return None
            else:
                return info.find('.//min').text

    def STR_PercentMax(self):
        for info in self.root.findall('.//Process'):
            if info.find('.//max') is None:
                return None
            else:
                return info.find('.//max').text

    def STR_GaussSigma(self):
        for info in self.root.findall('.//Process'):
            return info.find('.//gsigma').text

    def STR_SigmaVariance(self):
        for info in self.root.findall('.//Process'):
            return info.find('.//variance').text

    def getBand(self):
        for info in self.root.iter('bands'):
            #            for info2 in self.root.iter('bands'):
            testband = info.findall('.//bandfilter')
            print len(testband)
            for test in testband:
                print "test"
                print test.text
#            return bandF

    def getFileListWB(self):
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
        listArray = []
        for info in self.root.iter('ImageUrl'):
            fileUrl = info.find('url').text
            listArray.append(fileUrl)

        return listArray


def main():

    #    pdb.set_trace()

    DBQO = PDS_DBquery('JOBS')
    Key = DBQO.jobKey()
#    Key = '2d7379497fed4c092046b2a06f5471a5'
    DBQO.setJobsQueued(Key)

#*************** Setup logging ******************
    logger = logging.getLogger(Key)
    logger.setLevel(logging.INFO)

    logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Service.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    logger.info('Starting Process')

    xmlOBJ = jobXML(DBQO.jobXML4Key(Key))

# ********** Test if Directory exists and make it if not *******

    directory = '/scratch/pds_services/' + Key
    if not os.path.exists(directory):
        os.makedirs(directory)

    logger.info('Working Area: %s', directory)

    recipeDICT = {'ISSNA': '/usgs/cdev/PDS/recipe/POWrecipeISSNA.json',
                  'ISSWA': '/usgs/cdev/PDS/recipe/POWrecipeISSWA.json',
                  'CTX': '/usgs/cdev/PDS/recipe/POWrecipeCTX.json',
                  'SOLID STATE IMAGING SYSTEM': '/usgs/cdev/PDS/recipe/POWrecipe_galileoSSI.json',
                  'NIR': '/usgs/cdev/PDS/recipe/POWrecipeCLEM_NIR.json',
                  'LWIR': '/usgs/cdev/PDS/recipe/POWrecipeCLEM_LWIR.json',
                  'HIRES': '/usgs/cdev/PDS/recipe/POWrecipeCLEM_HIRES.json',
                  'HRSC': '/usgs/cdev/PDS/recipe/POWrecipeMEX_HRSC.json',
                  'UVVIS': '/usgs/cdev/PDS/recipe/POWrecipeCLEM_UVVIS.json',
                  'THEMIS_IR': '/usgs/cdev/PDS/recipe/POWrecipeTHMIR.json',
                  'NACL': '/usgs/cdev/PDS/recipe/POWrecipeLRO_NACL.json',
                  'NACR': '/usgs/cdev/PDS/recipe/POWrecipeLRO_NACR.json',
                  'MOC-NA': '/usgs/cdev/PDS/recipe/POWrecipe_MOCNA.json',
                  'MOC-WA': '/usgs/cdev/PDS/recipe/POWrecipe_MOCWA.json',
                  'MDIS-NAC': '/usgs/cdev/PDS/recipe/POWrecipeMDIS_NAC.json',
                  'MDIS-WAC': '/usgs/cdev/PDS/recipe/POWrecipeMDIS_WAC.json',
                  'MOC-WA': '/usgs/cdev/PDS/recipe/POWrecipeMGS_MOCWA.json',
                  'VISUAL_IMAGING_SUBSYSTEM_CAMERA_A': '/usgs/cdev/PDS/recipe/POWrecipeVikVisA.json',
                  'VISUAL_IMAGING_SUBSYSTEM_CAMERA_B': '/usgs/cdev/PDS/recipe/POWrecipeVikVisB.json',
                  'MAP': '/usgs/cdev/PDS/recipe/MAPrecipe.json'
                  }

# ******************** Setup Redis Hash for ground range *********

    RedisH = RedisHash(Key + '_info')
    RedisH.RemoveAll()
    RedisErrorH = RedisHash(Key + '_error')
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

# ***end ground range **

    RQ_recipe = RedisQueue(Key + '_recipe')
    RQ_recipe.RemoveAll()
    RQ_file = RedisQueue(Key + '_FileQueue')
    RQ_file.RemoveAll()
    RQ_WorkQueue = RedisQueue(Key + '_WorkQueue')
    RQ_WorkQueue.RemoveAll()
    RQ_loggy = RedisQueue(Key + '_loggy')
    RQ_loggy.RemoveAll()
    RQ_zip = RedisQueue(Key + '_ZIP')
    RQ_zip.RemoveAll()

    if xmlOBJ.getProcess() == 'POW':
        fileList = xmlOBJ.getFileListWB()
    elif xmlOBJ.getProcess() == 'MAP2':
        fileList = xmlOBJ.getMFileListWB()

    for List_file in fileList:

        ######### Input and output file naming and path stuff ############

        if xmlOBJ.getProcess() == 'POW':
            if xmlOBJ.getInst() == 'THEMIS_IR':
                Input_file = List_file.replace('odtie1_', 'odtir1_')
                Input_file = Input_file.replace('xxedr', 'xxrdr')
                Input_file = Input_file.replace('EDR.QUB', 'RDR.QUB')
                Input_file = Input_file.replace(
                    'http://pdsimage.wr.usgs.gov/Missions/', '/pds_san/PDS_Archive/')
            elif xmlOBJ.getInst() == 'ISSNA':
                Input_file = List_file.replace('.IMG', '.LBL')
                Input_file = Input_file.replace(
                    'http://pdsimage.wr.usgs.gov/Missions/', '/pds_san/PDS_Archive/')
            elif xmlOBJ.getInst() == 'ISSWA':
                Input_file = List_file.replace('.IMG', '.LBL')
                Input_file = Input_file.replace(
                    'http://pdsimage.wr.usgs.gov/Missions/', '/pds_san/PDS_Archive/')
            elif xmlOBJ.getInst() == 'SOLID STATE IMAGING SYSTEM':
                Input_file = List_file.replace('.img', '.lbl')
                Input_file = Input_file.replace(
                    'http://pdsimage.wr.usgs.gov/Missions/', '/pds_san/PDS_Archive/')
            else:
                Input_file = List_file.replace(
                    'http://pdsimage.wr.usgs.gov/Missions/', '/pds_san/PDS_Archive/')

        elif xmlOBJ.getProcess() == 'MAP2':
            Input_file = List_file.replace('file://pds_san', '/pds_san')

            if '+' in Input_file:
                tempsplit = Input_file.split('+')
                tempFile = tempsplit[0]
            else:
                tempFile = Input_file
            label = pvl.load(tempFile)
#*********Output final file naming **************
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

# ************* Map Template Stuff ******************
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

    testPVL = mapOBJ.Map2pvl()

    MAPfile = directory + "/" + Key + '.map'
    mapOBJ.Map2File(MAPfile)

    try:
        f = open(MAPfile)
        f.close
        logger.info('Map File Creation: Success')
    except IOError as e:
        logger.error('Map File %s Not Found', MAPfile)

# ** End Map Template Stuff **


# *************************************************
    logger.info('Building Recipe')
    recipeOBJ = Recipe()
    if xmlOBJ.getProcess() == 'POW':
        recipeOBJ.AddJsonFile(recipeDICT[xmlOBJ.getInst()])
    elif xmlOBJ.getProcess() == 'MAP2':
        recipeOBJ.AddJsonFile(recipeDICT['MAP'])
# ************** Test for stretch and add to recipe **********************
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


# ************* Test for output bit type and add to recipe *************
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

# **************** Add Grid(MAP2) *************
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

# ********OUTPUT FORMAT ***************
# ************* Test for GDAL and add to recipe *************************
    Oformat = xmlOBJ.getOutFormat()
    if Oformat == 'GeoTiff-BigTiff' or Oformat == 'GeoJPEG-2000' or Oformat == 'JPEG' or Oformat == 'PNG':
        if Oformat == 'GeoJPEG-2000':
            Oformat = 'JP2KAK'
        if Oformat == 'GeoTiff-BigTiff':
            Oformat = 'GTiff'
        GDALprocessOBJ = Process()
#        GDALprocessOBJ.newProcess('/usgs/dev/contrib/bin/FWTools-linux-x86_64-3.0.3/bin_safe/gdal_translate')
        GDALprocessOBJ.newProcess('/usgs/apps/anaconda/bin/gdal_translate')
        if xmlOBJ.getOutBit() != 'input':
            GDALprocessOBJ.AddParameter(
                '-ot', GDALprocessOBJ.GDAL_OBit(xmlOBJ.getOutBit()))
        GDALprocessOBJ.AddParameter('-of', Oformat)

        if Oformat == 'GTiff' or Oformat == 'JP2KAK' or Oformat == 'JPEG':
            GDALprocessOBJ.AddParameter(
                '-co', GDALprocessOBJ.GDAL_Creation(Oformat))

        recipeOBJ.AddProcess(GDALprocessOBJ.getProcess())
# **************** set up pds2isis and add to recipe
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
        processR = processOBJ.ProcessFromRecipe(item, recipeOBJ.getRecipe())

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

# ** *************** HPC job stuff ***********************
    logger.info('HPC Cluster job Submission Starting')
    jobOBJ = HPCjob()
    jobOBJ.setJobName(Key + '_Service')
    jobOBJ.setStdOut('/usgs/cdev/PDS/output/' + Key + '_%A_%a.out')
    jobOBJ.setStdError('/usgs/cdev/PDS/output/' + Key + '_%A_%a.err')
    jobOBJ.setWallClock('10:00:00')
#    jobOBJ.setMemory('8192')
#    jobOBJ.setMemory('16384')
    jobOBJ.setMemory('24576')
    jobOBJ.setPartition('pds')
    JAsize = RQ_file.QueueSize()
    jobOBJ.setJobArray(JAsize)
    logger.info('Job Array Size : %s', str(JAsize))

    jobOBJ.addPath('/usgs/apps/anaconda/bin')

    if xmlOBJ.getProcess() == 'POW':
        cmd = '/usgs/cdev/PDS/bin/POWprocess.py ' + Key
    elif xmlOBJ.getProcess() == 'MAP2':
        cmd = '/usgs/cdev/PDS/bin/MAPprocess.py ' + Key

    logger.info('HPC Command: %s', cmd)
    jobOBJ.setCommand(cmd)

    SBfile = directory + '/' + Key + '.sbatch'
    jobOBJ.MakeJobFile(SBfile)

    try:
        sb = open(SBfile)
        sb.close
        logger.info('SBATCH File Creation: Success')
    except IOError as e:
        logger.error('SBATCH File %s Not Found', SBfile)

    try:
        jobOBJ.Run()
        logger.info('Job Submission to HPC: Success')
        DBQO.setJobsStarted(Key)
    except IOError as e:
        logger.error('Jobs NOT Submitted to HPC')


if __name__ == "__main__":
    sys.exit(main())
