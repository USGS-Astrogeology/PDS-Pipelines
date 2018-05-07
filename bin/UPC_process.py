#!/usgs/apps/anaconda/bin/python
import os
import sys
import pvl
import subprocess
import datetime
import pytz
import logging
import json

from pysis import isis
from pysis.exceptions import ProcessError
from pysis.isis import getsn

from RedisQueue import *
from Recipe import *
from UPCkeywords import *
from UPC_test import *
from db import db_connect
from models import upc_models, pds_models


from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import mapper
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm.util import *
from sqlalchemy.ext.declarative import declarative_base
from geoalchemy2 import Geometry
# from geoalchemy2.shape import to_shape


import pdb


def getMission(inputfile):

    if 'Mars_Reconnaissance_Orbiter/CTX' in inputfile:
        mission = 'mroCTX'
    elif 'USA_NASA_PDS_ODTSDP_100XX' in inputfile and 'odtie1' in inputfile:
        mission = 'themisIR_EDR'
    elif 'USA_NASA_PDS_ODTSDP_100XX' in inputfile and 'odtve1' in inputfile:
        mission = 'themisVIS_EDR'
    elif 'Lunar_Reconnaissance_Orbiter/LROC/EDR/' in inputfile:
        mission = 'lrolrcEDR'
    elif 'Cassini/ISS/' in inputfile:
        mission = 'cassiniISS'

    return mission


def getISISid(infile):

    SerialNum = getsn(from_=infile)
    newisisSerial = SerialNum.replace('\n', '')
    return newisisSerial


def find_keyword(obj, key):
    if key in obj:
        return obj[key]
    for k, v in obj.items():
        if isinstance(v, dict):
            F_item = find_keyword(v, key)
            if F_item is not None:
                return F_item


def AddProcessDB(inputfile, outvalue):

    # pdb.set_trace()

    Base = declarative_base()
    session, _, _, engine = db_connect('pdsdi_dev')
    metadata = MetaData(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    parts = inputfile.split("/")

    testfile = parts[-3] + "/" + parts[-2] + "/" + parts[-1]
    testfile2 = '%' + testfile + '%'

    fileQobj = session.query(pds_models.Files).filter(
        pds_models.Files.filename.like(testfile2)).first()
    fileid = fileQobj.fileid

    date = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")

    processDB = pds_models.ProcessRuns(fileid=fileQobj.fileid,
                             process_date=date,
                             process_typeid='5',
                             process_out=outvalue)

    try:
        session.add(processDB)
        session.commit()
        return 'SUCCESS'
    except:
        return 'ERROR'


def main():

    # pdb.set_trace()

    workarea = '/scratch/pds_services/workarea/'

    Base = declarative_base()

    # Connect to database - ignore archive and volume information
    session, _, _, engine = db_connect('upcdev')
    metadata = MetaData(bind=engine)

    # ***************** Set up logging *****************
    logger = logging.getLogger('UPC_Process')
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler('/usgs/cdev/PDS/logs/Process.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    PDSinfoDICT = json.load(open('/usgs/cdev/PDS/bin/PDSinfo.json', 'r'))

    # Redis Queue Objects
    RQ_main = RedisQueue('UPC_ReadyQueue')
    RQ_thumbnail = RedisQueue('Thumbnail_ReadyQueue')
    RQ_browse = RedisQueue('Browse_ReadyQueue')

    # while there are items in the redis queue
    while int(RQ_main.QueueSize()) > 0:

        # get a file from the queue
        inputfile = RQ_main.QueueGet()
        if os.path.isfile(inputfile):
            logger.info('Starting Process: %s', inputfile)

            recipeOBJ = Recipe()
            recip_json = recipeOBJ.getRecipeJSON(getMission(inputfile), 'upc')
            recipeOBJ.AddJsonFile(recip_json)

            infile = workarea + os.path.splitext(
                os.path.basename(inputfile))[0] + '.UPCinput.cub'
            outfile = workarea + os.path.splitext(
                os.path.basename(inputfile))[0] + '.UPCoutput.cub'
            caminfoOUT = workarea + os.path.splitext(
                os.path.basename(inputfile))[0] + '_caninfo.pvl'
            EDRsource = inputfile.replace(
                '/pds_san/PDS_Archive/',
                'https://pdsimage.wr.ugs.gov/Missions/')

            status = 'success'
            # Iterate through each process listed in the recipe
            for item in recipeOBJ.getProcesses():
                # If any of the processes failed, discontinue processing
                if status == 'error':
                    break
                elif status == 'success':
                    processOBJ = Process()
                    processR = processOBJ.ProcessFromRecipe(
                        item, recipeOBJ.getRecipe())

                    # Handle processing based on string description.
                    if '2isis' in item:
                        processOBJ.updateParameter('from_', inputfile)
                        processOBJ.updateParameter('to', outfile)
                    elif item == 'thmproc':
                        processOBJ.updateParameter('from_', inputfile)
                        processOBJ.updateParameter('to', outfile)
                        thmproc_odd = workarea
                        + os.path.splitext(os.path.basename(inputfile))[0]
                        + '.UPCoutput.raw.odd.cub'
                        thmproc_even = workarea
                        + os.path.splitext(os.path.basename(inputfile))[0]
                        + '.UPCoutput.raw.even.cub'
                    elif item == 'handmos':
                        processOBJ.updateParameter('from_', thmproc_even)
                        processOBJ.updateParameter('mosaic', thmproc_odd)
                    elif item == 'spiceinit':
                        processOBJ.updateParameter('from_', infile)
                    elif item == 'cubeatt':
                        exband = 'none'
                        for item1 in PDSinfoDICT[getMission(inputfile)]['bandorder']:
                            print('test of item1: %s' % item1)
                            bandcount = 1
                            for item2 in label['IsisCube']['BandBin'][PDSinfoDICT[getMission(inputfile)]['bandbinQuery']]:
                                print('test of item2: %s' % item2)
                                if str(item1) == str(item2):
                                    exband = bandcount
                                    break
                                bandcount = bandcount + 1
                            if exband != 'none':
                                break

                        band_infile = infile + '+' + str(exband)
                        processOBJ.updateParameter('from_', band_infile)
                        processOBJ.updateParameter('to', outfile)
                    elif item == 'footprintinit':
                        processOBJ.updateParameter('from_', infile)
                    elif item == 'caminfo':
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', caminfoOUT)
                    else:
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', outfile)

                    # test of process
                    print(processOBJ.getProcess())

                    # iterate through functions listed in process obj
                    for k, v in processOBJ.getProcess().items():
                        # load a function into func
                        func = getattr(isis, k)
                        try:
                            # execute function
                            func(**v)
                            if item == 'handmos':
                                if os.path.isfile(thmproc_odd):
                                    os.rename(thmproc_odd, infile)
                            else:
                                if os.path.isfile(outfile):
                                    os.rename(outfile, infile)
                            status = 'success'
                            if '2isis' in item:
                                RQ_thumbnail.QueueAdd(inputfile)
                                RQ_browse.QueueAdd(inputfile)
                                label = pvl.load(infile)
                                infile_bandlist = label['IsisCube']['BandBin'][PDSinfoDICT[getMission(
                                    inputfile)]['bandbinQuery']]
                                infile_centerlist = label['IsisCube']['BandBin']['Center']
                            elif item == 'thmproc':
                                RQ_thumbnail.QueueAdd(inputfile)
                                RQ_browse.QueueAdd(inputfile)
                            elif item == 'handmos':
                                label = pvl.load(infile)
                                infile_bandlist = label['IsisCube']['BandBin'][PDSinfoDICT[getMission(
                                    inputfile)]['bandbinQuery']]
                                infile_centerlist = label['IsisCube']['BandBin']['Center']

                        except ProcessError as e:
                            status = 'error'
                            processError = item

            # keyword definitions
            if status == 'success':
                keywordsOBJ = UPCkeywords(caminfoOUT)

                if session.query(datafiles).filter(
                        datafiles.isisid == keywordsOBJ.getKeyword(
                            'Parameters', 'IsisId')).first() == None:

                    target_Qobj = session.query(targets).filter(
                        targets.targetname == keywordsOBJ.getKeyword(
                            'Instrument', 'TargetName').upper()).first()

                    instrument_Qobj = session.query(instruments).filter(
                        instruments.instrument == keywordsOBJ.getKeyword(
                            'Instrument', 'InstrumentId')).first()

                    PVL_productid = keywordsOBJ.getKeyword(
                        'Archive', 'ProductId')
                    print('Test of productid: %s' % PVL_productid)

                    test_input = datafiles(
                        isisid=keywordsOBJ.getKeyword('Parameters', 'IsisId'),
                        productid=keywordsOBJ.getKeyword(
                            'Archive', 'ProductId'),
                        edr_source=EDRsource,
                        edr_detached_label='',
                        instrumentid=instrument_Qobj.instrumentid,
                        targetid=target_Qobj.targetid)

                    session.add(test_input)
                    session.commit()

                Qobj = session.query(datafiles).filter(
                    datafiles.isisid == keywordsOBJ.getKeyword(
                        'Parameters', 'IsisId')).first()

                UPCid = Qobj.upcid
# block to add band information to meta_bands
                if type(infile_bandlist) == list:
                    index = 0
                    while index < len(infile_bandlist):
                        print('test of filter: %s' %
                              str(infile_bandlist[index]))
                        print('test of center: %s' %
                              str(infile_centerlist[index]))
                        B_DBinput = meta_bands(upcid=UPCid,
                                               filter=infile_bandlist[index],
                                               centerwave=infile_centerlist[index])
                        session.add(B_DBinput)
                        index = index + 1
                else:
                    B_DBinput = meta_bands(upcid=UPCid,
                                           filter=infile_bandlist,
                                           centerwave=float(infile_centerlist[0]))
                    session.add(B_DBinput)
                session.commit()

#  Block to add common keywords
                testjson = json.load(
                    open('/usgs/cdev/PDS/recipe/Keyword_Definition.json', 'r'))
                for element_1 in testjson['instrument']['COMMON']:
                    keyvalue = ""
                    print('Inside element_1 test: %s' % element_1)
                    keytype = testjson['instrument']['COMMON'][element_1]['type']
                    print('test of keytype: %s' % keytype)
                    keygroup = testjson['instrument']['COMMON'][element_1]['group']
                    print('test of keygroup: %s' % keygroup)
                    keyword = testjson['instrument']['COMMON'][element_1]['keyword']
                    print('test of keyword: %s' % keyword)

                    keyword_Qobj = session.query(
                        keywords).filter(keywords.typename == element_1).first()
                    print('test of keyword typeid: %s' %
                          str(keyword_Qobj.typeid))

                    if keygroup == 'Polygon':
                        print('Polygon Keyword')
                        keyvalue = keywordsOBJ.getPolygonKeyword(keyword)
                    else:
                        keyvalue = keywordsOBJ.getKeyword(keygroup, keyword)
                    print('test of keyvalue: %s' % keyvalue)

                    DBinput = upc_models.create_table(keytype,
                                                  upcid=UPCid,
                                                  typeid=keyword_Qobj.typeid,
                                                  value=keyvalue)

                    session.add(DBinput)
                session.commit()

                # geometry stuff
                G_centroid = 'point ({} {})'.format(
                    str(keywordsOBJ.getKeyword(
                        'Polygon', 'CentroidLongitude')),
                    str(keywordsOBJ.getKeyword(
                        'Polygon', 'CentroidLatitude')))

                G_keyword_Qobj = session.query(keywords).filter(
                    keywords.typename == 'isiscentroid').first()
                G_DBinput = meta_geometry(upcid=UPCid,
                                          typeid=G_keyword_Qobj.typeid,
                                          value=G_centroid)
                session.add(G_DBinput)

                G_footprint = keywordsOBJ.getKeyword('Polygon', 'GisFootprint')
                G_footprint_Qobj = session.query(keywords).filter(
                    keywords.typename == 'isisfootprint').first()
                G_DBinput = meta_geometry(upcid=UPCid,
                                          typeid=G_footprint_Qobj.typeid,
                                          value=G_footprint)
                session.add(G_DBinput)
                session.commit()

                # block to deal with mission keywords
                for element_2 in testjson['instrument'][getMission(inputfile)]:
                    print('Inside element_2 test: %s' % element_2)
                    M_keytype = testjson['instrument'][getMission(
                        inputfile)][element_2]['type']
                    M_keygroup = testjson['instrument'][getMission(
                        inputfile)][element_2]['group']
                    M_keyword = testjson['instrument'][getMission(
                        inputfile)][element_2]['keyword']

                    M_keyword_Qobj = session.query(keywords).filter(
                        keywords.typename == element_2).first()

                    if M_keygroup == 'Polygon':
                        print('Polygon Keyword')
                        M_keyvalue = keywordsOBJ.getPolygonKeyword(M_keyword)
                    else:
                        M_keyvalue = keywordsOBJ.getKeyword(
                            M_keygroup, M_keyword)
                    print('Mission keyvalue is: %s' % M_keyvalue)

                    DBinput = upc_models.create_table(M_keytype,
                                                  upcid=UPCid,
                                                  typeid=M_keyword_Qobj.typeid,
                                                  value=M_keyvalue)

                    session.add(DBinput)
                session.commit()

                CScmd = 'md5sum ' + inputfile
                process = subprocess.Popen(CScmd,
                                           stdout=subprocess.PIPE, shell=True)
                (stdout, stderr) = process.communicate()
                checksum = stdout.split()[0]

                # set typeid to 5 on the prod DB - 101 for dev
                # production typeid 5 = checksum
                # dev typeid 101 = checksum
                DBinput = meta_string(upcid=UPCid,
                                      typeid='101',
                                      value=checksum)
                session.add(DBinput)
                # add error keyword to UPC
                # typeid 595 = error flag
                DBinput = meta_boolean(upcid=UPCid,
                                       typeid='595',
                                       value='false')
                session.add(DBinput)
                session.commit()
                AddProcessDB(inputfile, 't')
                os.remove(infile)
                os.remove(caminfoOUT)

            elif status == 'error':
                date = datetime.datetime.now(pytz.utc).strftime(
                    "%Y-%m-%d %H:%M:%S")

                if '2isis' in processError or processError == 'thmproc':

                    testspacecraft = PDSinfoDICT[getMission(
                        inputfile)]['UPCerrorSpacecraft']
                    testinst = PDSinfoDICT[getMission(
                        inputfile)]['UPCerrorInstrument']

                    if session.query(datafiles).filter(
                            datafiles.edr_source == EDRsource).first() == None:
                        target_Qobj = session.query(targets).filter(
                            targets.targetname == keywordsOBJ.getKeyword(
                                'Instrument', 'TargetName').upper()).first()

                        instrument_Qobj = session.query(instruments).filter(
                            instruments.instrument == keywordsOBJ.getKeyword(
                                'Instrument', 'InstrumentId')).first()

                        error1_input = datafiles(isisid='1',
                                                 edr_source=EDRsource)
                        session.add(error1_input)
                        session.commit()

                    EQ1obj = session.query(datafiles).filter(
                        datafiles.edr_source == EDRsource).first()
                    UPCid = EQ1obj.upcid

                    errorMSG = 'Error running {} on file {}'.format(
                        processError, inputfile)

                    # typeid 84 = processdate
                    DBinput = MetaTime(upcid=UPCid,
                                       typeid='84',  # 84 in prod
                                       value=date)
                    session.add(DBinput)

                    # typeid 673 = errortype
                    DBinput = MetaString(upcid=UPCid,
                                         typeid='673',  # 673 in prod
                                         value=processError)
                    session.add(DBinput)

                    # typeid 596 = errormessage
                    DBinput = MetaString(upcid=UPCid,
                                         typeid='596',  # 596 in prod
                                         value=errorMSG)
                    session.add(DBinput)

                    # typeid 595 = error
                    DBinput = MetaBoolean(upcid=UPCid,
                                          typeid='595',  # 595 in prod
                                          value='true')
                    session.add(DBinput)

                    # typeid 597 = isisfootprint
                    DBinput = MetaGeometry(upcid=UPCid,
                                           typeid='597',  # 597 in prod
                                           value='POINT(361 0)')
                    session.add(DBinput)

                    # typeid 598 = isiscentroid
                    DBinput = MetaGeometry(upcid=UPCid,
                                           typeid='598',  # 598 in prod
                                           value='POINT(361 0)')
                    session.add(DBinput)

                    session.commit()

                else:
                    label = pvl.load(infile)

                    isisSerial = getISISid(infile)

                    if session.query(datafiles).filter(
                            datafiles.isisid == isisSerial).first() == None:
                        target_Qobj = session.query(targets).filter(
                            targets.targetname == str(
                                label['IsisCube']['Instrument']['TargetName'])
                            .upper()).first()
                        instrument_Qobj = session.query(instruments).filter(
                            instruments.instrument == str(
                                label['IsisCube']
                                ['Instrument']
                                ['InstrumentId'])).first()

                        error2_input = datafiles(isisid=isisSerial,
                                                 productid=label['IsisCube']['Archive']['ProductId'],
                                                 edr_source=EDRsource,
                                                 instrumentid=instrument_Qobj.instrumentid,
                                                 targetid=target_Qobj.targetid)
                    session.add(error2_input)
                    session.commit()

                    EQ2obj = session.query(datafiles).filter(
                        datafiles.isisid == isisSerial).first()
                    UPCid = EQ2obj.upcid
                    errorMSG = 'Error running {} on file {}'.format(
                        processError, inputfile)

                    # typeid 84 = processdate
                    DBinput = MetaTime(upcid=UPCid,
                                       typeid='84',  # 84 in prod
                                       value=date)
                    session.add(DBinput)

                    # typeid 673 = errortype
                    DBinput = MetaString(upcid=UPCid,
                                         typeid='673',  # 673 in prod
                                         value=processError)
                    session.add(DBinput)

                    # typeid 596 = errormessage
                    DBinput = MetaString(upcid=UPCid,
                                         typeid='596',  # 596 in prod
                                         value=errorMSG)
                    session.add(DBinput)

                    # typeid 595 = error flag
                    DBinput = MetaBoolean(upcid=UPCid,
                                          typeid='595',  # 595 in prod
                                          value='true')
                    session.add(DBinput)

                    # typeid 597 = isisfootprint
                    DBinput = MetaGeometry(upcid=UPCid,
                                           typeid='597',  # 597 in prod
                                           value='POINT(361 0)')
                    session.add(DBinput)

                    # typeid 598 = isiscentroid
                    DBinput = MetaGeometry(upcid=UPCid,
                                           typeid='598',  # 598 in prod
                                           value='POINT(361 0)')
                    session.add(DBinput)

                    # typeid 52 = starttime
                    DBinput = MetaTime(upcid=UPCid,
                                       typeid='52',  # 52 in prod
                                       value=label['IsisCube']['Instrument']['StartTime'])
                    session.add(DBinput)

                    # typeid 47 = stoptime
                    DBinput = MetaTime(upcid=UPCid,
                                       typeid='47',  # 47 in prod
                                       value=label['IsisCube']['Instrument']['StopTime'])
                    session.add(DBinput)

                    session.commit()

                AddProcessDB(inputfile, 'f')
                os.remove(infile)


if __name__ == "__main__":
    sys.exit(main())
