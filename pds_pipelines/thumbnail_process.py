#!/usgs/apps/anaconda/bin/python
import os
import sys
import pvl
import json
import datetime
import pytz
import logging
from pysis import isis
from pysis.exceptions import ProcessError

from pysis.isis import getsn
from ast import literal_eval

from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.Recipe import Recipe
from pds_pipelines.Process import Process
from pds_pipelines.db import db_connect
from pds_pipelines.models.upc_models import MetaString, DataFiles
from pds_pipelines.models.pds_models import ProcessRuns
from pds_pipelines.config import pds_log, pds_info, workarea, pds_db, upc_db
from pds_pipelines.UPC_process import get_tid

def getISISid(infile):
    serial_num = getsn(from_=infile)
    if isinstance(serial_num, bytes):
        serial_num = serial_num.decode()
    newisisSerial = serial_num.replace('\n', '')
    return newisisSerial


def scaleFactor(line, sample, jsonfile):

#    pdb.set_trace()

    infoDICT = json.load(open(jsonfile, 'r'))

    maxLine = int(infoDICT['reduced']['thumbnail']['maxlines'])
    maxSample = int(infoDICT['reduced']['thumbnail']['maxsamples'])
    minLine = int(infoDICT['reduced']['thumbnail']['minlines'])
    minSample = int(infoDICT['reduced']['thumbnail']['minsamples'])

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

    if scalefactor < 1:
        scalefactor = 1
    return scalefactor


def makedir(inputfile):
#    pdb.set_trace()

    temppath = os.path.dirname(inputfile).lower()
    # @TODO change finalpath back to production path
    #finalpath = temppath.replace('/pds_san/pds_archive/', '/home/arsanders/PDS-Pipelines/products/thumb/')
    finalpath = temppath.replace('/pds_san/pds_archive/', '/pds_san/PDS_Derived/UPC/images/')

    if not os.path.exists(finalpath):
        try:
            os.makedirs(finalpath, exist_ok=True)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    return finalpath

def DB_addURL(session, isisSerial, inputfile, tid):
    # pdb.set_trace()
    newisisSerial = isisSerial.split(':')[0]
    likestr = '%' + newisisSerial + '%'
    Qobj = session.query(DataFiles).filter(DataFiles.isisid.like(likestr)).first()

    if str(Qobj.isisid) == str(isisSerial):

        outputfile = inputfile.replace('/pds_san/PDS_Derived/UPC/images/', '$thumbnail_server/')

        print(Qobj.upcid)
        DBinput = MetaString(upcid=Qobj.upcid,
                             typeid=tid,
                             value=outputfile)

        try:
            session.merge(DBinput)
            session.commit()
            return 'SUCCESS'
        except:
            return 'ERROR'


def AddProcessDB(session, fid, outvalue):
    # pdb.set_trace()
    date = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")

    processDB = ProcessRuns(fileid=fid,
                            process_date=date,
                            process_typeid='5',
                            process_out=outvalue)

    try:
        session.merge(processDB)
        session.commit()
        return 'SUCCESS'
    except:
        return 'ERROR'


def main():

#    pdb.set_trace()

    ##***************** Set up logging *****************
    logger = logging.getLogger('Thumbnail_Process')
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler(pds_log + 'Process.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)    

    RQ_main = RedisQueue('Thumbnail_ReadyQueue')

    PDSinfoDICT = json.load(open(pds_info, 'r'))

    # @TODO change to production servers
    pds_session, _ = db_connect(pds_db)
    upc_session, _ = db_connect(upc_db)

    tid = get_tid('thumbnailurl', upc_session)

    while int(RQ_main.QueueSize()) > 0:
        item = literal_eval(RQ_main.QueueGet().decode("utf-8"))
        inputfile = item[0]
        fid = item[1]
        archive = item[2]
        if os.path.isfile(inputfile):
            logger.info('Starting Process: %s', inputfile)

            finalpath = makedir(inputfile)                  

            recipeOBJ = Recipe()
            recip_json = recipeOBJ.getRecipeJSON(archive)
            recipeOBJ.AddJsonFile(recip_json, 'reduced')
            infile = workarea + os.path.splitext(os.path.basename(inputfile))[0] + '.Tinput.cub'
            outfile = workarea + os.path.splitext(os.path.basename(inputfile))[0] + '.Toutput.cub'
            status = 'success'
            for item in recipeOBJ.getProcesses():
                if status == 'error':
                    break
                elif status == 'success':
                    processOBJ = Process()
                    processR = processOBJ.ProcessFromRecipe(item, recipeOBJ.getRecipe())

                    if '2isis' in item:
                        processOBJ.updateParameter('from_', inputfile)
                        processOBJ.updateParameter('to', outfile)
                    elif item == 'spiceinit':
                        processOBJ.updateParameter('from_', infile)
                    elif item == 'cubeatt':
                        label = pvl.load(infile)
                        bands = PDSinfoDICT[archive]['bandorder']
                        query_bands = label['IsisCube']['BandBin'][PDSinfoDICT[archive]['bandbinQuery']]
                        # Create a set from the list / single value
                        try:
                            query_band_set = set(query_bands)
                        except:
                            query_band_set = set([query_bands])
                        
                        # Iterate through 'bands' and grab the first value that is present in the
                        #  set defined by 'bandbinquery' -- if not present, default to 1
                        exband = next((band for band in bands if band in query_band_set), 1)

                        band_infile = infile + '+' + str(exband)
                        processOBJ.updateParameter('from_', band_infile)
                        processOBJ.updateParameter('to', outfile)

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
                        Nline = int(Nline)
                        Nsample = int(Nsample)
                        Sfactor = scaleFactor(Nline, Nsample, recip_json)
                        processOBJ.updateParameter('lscale', Sfactor)
                        processOBJ.updateParameter('sscale', Sfactor)
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', outfile)

                    elif item == 'isis2std':
                        final_outfile = finalpath + '/' + os.path.splitext(os.path.basename(inputfile))[0] + '.thumbnail.jpg'
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', final_outfile)

                    else:
                        processOBJ.updateParameter('from_', infile)
                        processOBJ.updateParameter('to', outfile)

                    for k, v in processOBJ.getProcess().items():
                        func = getattr(isis, k)
                        try:
                            func(**v)
                            logger.info('Process %s :: Success', k)
                            if os.path.isfile(outfile):
                                if '.cub' in outfile:
                                    os.rename(outfile, infile)
                            status = 'success'
                            if '2isis' in item:
                                isisSerial = getISISid(infile)
                        except ProcessError as e:
                            print(e)
                            logger.error('Process %s :: Error', k)
                            status = 'error'
            if status == 'success':
                DB_addURL(upc_session, isisSerial, final_outfile, tid)
                os.remove(infile)
                logger.info('Thumbnail Process Success: %s', inputfile)

                AddProcessDB(pds_session, fid, 't')  
        else:
            logger.error('File %s Not Found', inputfile)

if __name__ == "__main__":
    sys.exit(main())
