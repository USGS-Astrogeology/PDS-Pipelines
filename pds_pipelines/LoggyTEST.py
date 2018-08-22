#!/usgs/apps/anaconda/bin/python

import os
import sys
import subprocess

from RedisQueue import *
from RedisHash import *
from collections import OrderedDict

import datetime
import pytz
import json

from PDS_DBquery import *

import pdb


def main():

    pdb.set_trace()

#    RQ_final = RedisQueue('FinalQueue')

#    FKey = RQ_final.QueueGet()

    utc_tz = pytz.timezone('UTC')
    utc_dt = datetime.datetime.now(utc_tz)

    print utc_dt

    print datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

    DBQO = PDS_DBquery('JOBS')

    key = 'd01a2bcaa4c3d0ec3a56bb46f0c42626'
    result = DBQO.setJobsQuered(key)

    print result

    zipQueue = RedisQueue(FKey + '_ZIP')
    loggyQueue = RedisQueue(FKey + '_loggy')
    infoHash = RedisHash(FKey + '_info')
    recipeQueue = RedisQueue(FKey + '_recipe')

#    infoHash.RemoveAll()
#    recipeQueue.RemoveAll()


#    for element in loggyQueue.ListGet():
#
#        testDICT = json.loads(element, object_pairs_hook=OrderedDict)
#        print testDICT
#
#        print ""
#        print ""
#        for testfile in testDICT:
#            print testfile


if __name__ == "__main__":
    sys.exit(main())
