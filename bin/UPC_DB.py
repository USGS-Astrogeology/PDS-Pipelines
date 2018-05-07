#!/usgs/apps/anaconda/bin/python

from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import mapper
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm.util import *
from sqlalchemy.ext.declarative import declarative_base


from PDS_DBsessions import *
from config import *


class UPC_DB(object):

    def __init__(self):

        Base = declarative_base()

        engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format(upcdev_user,
                                                                    upcdev_pass,
                                                                    upcdev_host,
                                                                    upcdev_port,
                                                                    upcdev_db))

        metadata = MetaData(bind=engine)

        class DataFiles(Base):
            __tablename__ = 'datafiles'
            __table__ = Table('datafiles', metadata, autoload=True)

#        class Instruments(Base):
#            __table__ = Table('instruments_meta', metadata, autoload=True)

        class Targets(Base):
            __table__ = Table('targets_meta', metadata, autoload=True)


#        datamapper = mapper(DataFiles, datafiles)
        Session = sessionmaker(bind=engine)
        self.session = Session()

        self.datafiles = self.DataFiles()
        self.targets = self.Targets()

    def testIsisId(self, isisid):

        qOBJ = self.session.query(self.datafiles).filter(
            self.datafiles.isisid == isisid).first()
        return qOBJ.isisid

    def getUPCid(self, isisid):

        qOBJ = self.session.query(self.datafiles).filter(
            self.datafiles.isisid == isisid).first()
        return qOBJ.upcid

    def getTargetID(self, target):

        qOBJ = self.session.query(self.targets).filter(
            self.targets.targetname == upper(target)).first()
        return queryObj.targetid
