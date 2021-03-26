import sqlalchemy

from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy_utils import database_exists, create_database
from sqlalchemy import (Column, Integer, Float, Time, String, Boolean,
                        ForeignKey, CHAR, DateTime)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry

import datetime

from pds_pipelines.db import db_connect
from pds_pipelines.config import upc_db

Base = declarative_base()

class BaseMixin(object):
    @classmethod
    def create(cls, session, **kw):
        obj = cls(**kw)
        session.add(obj)
        session.commit()
        return obj

    @staticmethod
    def bulkadd(iterable):
        session = Session()
        session.add_all(iterable)
        session.commit()
        session.close()


def create_table(keytype, *args, **kwargs):
    """ Returns a table based on the keytype description.

    Parameters
    ----------
    keytype : str
        A type description of the table's value.

    Returns
    -------
    out : :class:`.Instruments or :class:`.DataFiles or :class:`.Targets
        A SQLAlchemy table with type specific column specification.
    """

    try:
        return class_map[keytype.lower()](**kwargs)
    except NameError:
        print('Keytype {} not found\n'.format(keytype))


class DataFiles(BaseMixin, Base):
    __tablename__ = 'datafiles'
    upcid = Column(Integer, primary_key=True, autoincrement = True)
    isisid = Column(String(256))
    productid = Column(String(256))
    source = Column(String(1024))
    detached_label = Column(String(1024))
    instrumentid = Column(Integer, ForeignKey("instruments.instrumentid"), index=True)
    targetid = Column(Integer, ForeignKey("targets.targetid"), index=True)
    search_terms = relationship('SearchTerms', backref="DataFiles", uselist=True, cascade="save-update, merge, delete, delete-orphan")
    json_keyword = relationship('JsonKeywords', backref="DataFiles", uselist=True, cascade="save-update, merge, delete, delete-orphan")
    level = Column(CHAR(1))


class Instruments(BaseMixin, Base):
    __tablename__ = 'instruments'
    instrumentid = Column(Integer, primary_key=True, autoincrement = True)
    instrument = Column(String(256), nullable=False)
    displayname = Column(String(256))
    mission = Column(String(256))
    spacecraft = Column(String(256))
    description = Column(String(256))
    search_terms = relationship('SearchTerms', backref="instruments", uselist=False)
    datafiles = relationship('DataFiles', backref="instruments", uselist=False)
    #product_type = Column(String(8))


class Targets(BaseMixin, Base):
    __tablename__ = 'targets'
    targetid = Column(Integer, primary_key = True, autoincrement = True)
    naifid = Column(Integer)
    targetname = Column(String(20), nullable = False)
    system = Column(String(20), nullable = False)
    displayname = Column(String(20))
    aaxisradius = Column(Float)
    baxisradius = Column(Float)
    caxisradius = Column(Float)
    description = Column(String(1024))
    search_term = relationship('SearchTerms', backref="targets", uselist=False)
    datafiles = relationship('DataFiles', backref="targets", uselist=False)
    #iau_mean_radius = Column(Float)


class NewStats(BaseMixin, Base):
    __tablename__ = 'new_stats'
    instrumentid = Column(Integer, primary_key=True)
    targetid = Column(Integer, primary_key=True)
    targetname = Column(String(256))
    system = Column(String(20))
    instrument = Column(String(256))
    mission = Column(String(256))
    spacecraft = Column(String(256))
    displayname = Column(String(256))
    start_date = Column(Time)
    stop_date = Column(Time)
    last_published = Column(Time)
    bands = Column(Integer)
    total = Column(Integer)
    errors = Column(Integer)


class SearchTerms(BaseMixin, Base):
    __tablename__ = 'search_terms'
    upcid = Column(Integer, ForeignKey('datafiles.upcid'), primary_key=True)
    processdate = Column(DateTime)
    starttime = Column(DateTime, index=True)
    solarlongitude = Column(Float)
    meangroundresolution = Column(Float)
    minimumemission = Column(Float)
    maximumemission = Column(Float)
    emissionangle = Column(Float)
    minimumincidence = Column(Float)
    maximumincidence = Column(Float)
    incidenceangle = Column(Float)
    minimumphase = Column(Float)
    maximumphase = Column(Float)
    phaseangle = Column(Float)
    targetid = Column(Integer, ForeignKey('targets.targetid'), index=True)
    instrumentid = Column(Integer, ForeignKey('instruments.instrumentid'), index=True)
    pdsproductid = Column(String(256))
    err_flag = Column(Boolean)
    isisfootprint = Column(Geometry())


class JsonKeywords(BaseMixin, Base):
    __tablename__ = "json_keywords"
    upcid = Column(Integer, ForeignKey('datafiles.upcid'), primary_key=True)
    jsonkeywords = Column(MutableDict.as_mutable(JSONB))

class_map = {
    'datafiles': DataFiles,
    'instruments': Instruments,
    'targets' : Targets,
    'search_terms': SearchTerms
}

try:
    Session, engine = db_connect(upc_db)
except:
    Session = None
    engine = None

if isinstance(Session, sqlalchemy.orm.sessionmaker):

    # Create the database
    if not database_exists(engine.url):
        create_database(engine.url, template='template_postgis')  # This is a hardcode to the local template

    Base.metadata.bind = engine
    # If the table does not exist, this will create it. This is used in case a
    # user has manually dropped a table so that the project is not wrecked.
    Base.metadata.create_all(tables=[DataFiles.__table__,
                                     Instruments.__table__,
                                     Targets.__table__,
                                     SearchTerms.__table__,
                                     JsonKeywords.__table__])
