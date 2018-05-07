#!/usgs/apps/anaconda/bin/python

import os
import subprocess
import sys
import datetime
import pytz

import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import mapper
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm.util import *
from sqlalchemy.orm import eagerload

from sqlalchemy.ext.declarative import declarative_base
from db import db_connect


class PDS_DBsessions(object):

    def __init__(self, database):
        """
        Parameters
        -----------
        database : str
        """
        if database == "JOBS":

            # files and archives are returned, but we don't care about them so we throw them away
            self.session, _, _, engine = db_connect('clusterjob_prd')
            DBsession = self.session
            Base = automap_base()
            Base.prepare(engine, reflect=True)
            self.processingTAB = Base.classes.processing
        elif database == "DI":
            base = automap_base()
            # files and archives are returned, but we don't care about them so we throw them away
            self.session, _, _, engine = db_connect('pdsdi')
            base.prepare(engine, reflect=True)
            self.files = base.classes.files
            self.archives = base.classes.archives
            DBsession = self.session
            self.DB_files = self.files

#        elif database == "UPC":

#            base = automap_base()

            # engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format(upcprd_user,
            # upcprd_pass,
            # upcprd_host,
            # upcprd_port,
            # upcprd_db))

            # engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format(upcdev_user,
            # upcdev_pass,
            # upcdev_host,
            # upcdev_port,
            # upcdev_db))

#            mymetadata = MetaData()
#            print mymetadata.tables

#            mymetadata = MetaData(engine, reflect=True)
#            print mymetadata.tables

#            filesmapper = mapper(
#            Session = sessionmaker(bind=engine)
#            self.DBsession = Session()

#            metadata = MetaData(bind=engine)
#            datafiles = Table('datafiles', metadata, autoload=True)
#            class Datafiles(object):
#                pass
#
#            filesmapper = mapper(Datafiles, datafiles)
#            Session = sessionmaker()
#            self.DBsession = Session()

#            base.prepare(engine, reflect=True)
#
#            self.datafilesTAB = base.classes.datafiles
#            self.targetsTAB = base.classes.targets_meta
#            self.instrumentsmetaTAB = base.classes.instrumentsmeta
#
#            Session = sessionmaker(bind=engine)
#            self.session = Session()
#            DBsession = self.session

    def closeDB(self):

        self.session.close()

    def AddFile(self, Tfile):
        """
        Parameters
        ----------
        Tfile
        """
        date = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")

        insert = self.files(filename=str(Tfile),
                            entry_date=date)

        self.session.add(insert)
        self.session.commit()
