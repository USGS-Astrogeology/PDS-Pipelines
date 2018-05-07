#!/usgs/apps/anaconda/bin/python

import os
import subprocess
import sys
import datetime

import sqlalchemy
from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm.util import *
from sqlalchemy.orm import eagerload

from config import *


class UPC_test(object):

    def __init__(self):

        Base = declarative_base()
        engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format(upcdev_user,
                                                                    upcdev_pass,
                                                                    upcdev_host,
                                                                    upcdev_port,
                                                                    upcdev_db))

        metadata = MetaData(bind=engine)
        Session = sessionmaker(bind=engine)
        self.session = Session

        Base = automap_base()
        Base.prepare(engine, reflect=True)

        self.DBT_keywords = Base.classes.keywords

    def get_keyword_typeid(self, key):

        Qobj = self.session.query(self.DBT_keywords).filter(
            self.DBT_keywords.typename == key).first()
        return Qobj.typeid
