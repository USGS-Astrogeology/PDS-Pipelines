#!/usgs/apps/anaconda/bin/python
import os
import sys
import pvl
import logging
import json

from RedisQueue import *
from Recipe import *
from UPC_DB import *
from UPCkeywords import *

from sqlalchemy import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import mapper
from sqlalchemy import create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm.util import *
from sqlalchemy.ext.declarative import declarative_base


from geoalchemy2 import Geometry

import pdb

# def find_keyword(obj, key):
#    if key in obj:
#        return obj[key]
#    for k, v in obj.items():
#        if isinstance(v,dict):
#            F_item = find_keyword(v, key)
#            if F_item is not None:
#                return F_item


def main():

    pdb.set_trace()

    workarea = '/scratch/pds_services/workarea/'

    Base = declarative_base()
    engine = create_engine('postgresql://{}:{}@{}:{}/{}'.format(upcdev_user,
                                                                upcdev_pass,
                                                                upcdev_host,
                                                                upcdev_port,
                                                                upcdev_db))

    metadata = MetaData(bind=engine)

#    datafiles = Table('datafiles', metadata, autoload=True)
#    instrumentsmeta = Table('instruments_meta', metadata, autoload=True)

    class datafiles(Base):
        __table__ = Table('datafiles', metadata, autoload=True)

    class instruments(Base):
        __table__ = Table('instruments_meta', metadata, autoload=True)

    class targets(Base):
        __table__ = Table('targets_meta', metadata, autoload=True)

    class meta_geom(Base):
        __tablename__ = "meta_geometry"
        upcid = Column(types.BigInteger)
        typeid = Column(types.Integer)
        value = Column(Geometry(geometry_type='GEOMETRY'))

#    filesmapper = mapper(Datafiles, datafiles)
#    filesmapper = mapper(instrumentsMeta, instrumentsmeta)
    Session = sessionmaker(bind=engine)
    session = Session()

    test_QD = session.query(datafiles).filter(
        datafiles.isisid == 'MeSSEnGeR/MDIS-NAC/1/0210459695:983000').first()

    print 'test of clem: %s' % test_QD.isisid

    test_G = session.query(meta_geom).first()

    testpvl = '/scratch/pds_services/workarea/J13_049686_2145_XN_34N285W_caninfo.pvl'
#    label = pvl.load(testpvl)
    keyOBJ = UPCkeywords(testpvl)


#    test_isisid = label['Caminfo']['Parameters']['IsisId']
    test_isisid2 = keyOBJ.getKeyword('Parameters', 'IsisId')
    print 'Test of isisid: %s' % test_isisid2

    test_target = keyOBJ.getKeyword('Instrument', 'TargetName').upper()
    print 'test target: %s' % test_target

    test_QT = session.query(targets).filter(
        targets.targetname == test_target.upper()).first()
    print 'test of targetid: %s' % test_QT.targetid

#    test_input = datafiles(isisid=test_isisid)
#    session.add(test_input)
#    session.commit()


if __name__ == "__main__":
    sys.exit(main())
