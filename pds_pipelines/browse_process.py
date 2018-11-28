#!/usr/bin/env python
import os
import sys
import pvl
import json
import datetime
import pytz
import logging
import argparse
from ast import literal_eval

from pysis import isis
from pysis.exceptions import ProcessError
from pysis.isis import getsn

from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.RedisLock import RedisLock
from pds_pipelines.Recipe import Recipe
from pds_pipelines.Process import Process
from pds_pipelines.db import db_connect
from pds_pipelines.models.upc_models import MetaString, DataFiles
from pds_pipelines.models.pds_models import ProcessRuns
from pds_pipelines.config import pds_log, pds_info, workarea, pds_db, upc_db, lock_obj
from pds_pipelines.UPC_process import get_tid

def getISISid(infile):
    serial_num = getsn(from_=infile)
    if isinstance(serial_num, bytes):
        serial_num = serial_num.decode()
    newisisSerial = serial_num.replace('\n', '')
    return newisisSerial

def scaleFactor(line, sample, jsonfile):

    infoDICT = json.load(open(jsonfile, 'r'))
    maxLine = int(infoDICT['reduced']['browse']['maxlines'])
    maxSample = int(infoDICT['reduced']['browse']['maxsamples'])
    minLine = int(infoDICT['reduced']['browse']['minlines'])
    minSample = int(infoDICT['reduced']['browse']['minsamples'])

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

        outputfile = inputfile.replace('/pds_san/PDS_Derived/UPC/images/', '$browse_server/')

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


class Args(object):
    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser(description="DI Process")

        parser.add_argument('--log', '-l', dest="log_level",
                            choice=['DEBUG', 'INFO',
                                    'WARNING', 'ERROR', 'CRITICAL'],
                            help="Set the log level.", default='INFO')

        args = parser.parse_args()
        self.log_level = args.log_level



def main():

#    pdb.set_trace()

    args = Args()
    args.parse_args()


    logger = logging.getLogger('Browse_Process')
    level = logging.getLevelName(args.log_level)
    logger.setLevel(level)
    logFileHandle = logging.FileHandler(pds_log + 'Process.log')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    RQ_main = RedisQueue('Browse_ReadyQueue')
    RQ_lock = RedisLock(lock_obj)
    RQ_lock.add({RQ_main.id_name: '1'})

    PDSinfoDICT = json.load(open(pds_info, 'r'))

    pds_session, pds_engine = db_connect(pds_db)
    upc_session, upc_engine = db_connect(upc_db)

    tid = get_tid('fullimageurl', upc_session)

    while int(RQ_main.QueueSize()) > 0 and RQ_lock.available(RQ_main.id_name):
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
            infile = workarea + os.path.splitext(os.path.basename(inputfile))[0] + '.Binput.cub'
            outfile = workarea + os.path.splitext(os.path.basename(inputfile))[0] + '.Boutput.cub'
            status = 'success'
            for item in recipeOBJ.getProcesses():
                if status == 'error':
                    logger.error("Error processing %s", inputfile)
                    break
                elif status == 'success':
                    processOBJ = Process()
                    processOBJ.ProcessFromRecipe(item, recipeOBJ.getRecipe())

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
                        final_outfile = finalpath + '/' + os.path.splitext(
                            os.path.basename(inputfile))[0] + '.browse.jpg'
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
                logger.info('Browse Process Success: %s', inputfile)
                AddProcessDB(pds_session, fid, 't')
        else:
            logger.error('File %s Not Found', inputfile)

    upc_session.close()
    pds_session.close()
    upc_engine.dispose()
    pds_engine.dispose()

if __name__ == "__main__":
    sys.exit(main())
