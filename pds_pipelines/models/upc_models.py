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
from pds_pipelines.utils import reprocess

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
    instrumentid = Column(Integer, ForeignKey("instruments.instrumentid"))
    targetid = Column(Integer, ForeignKey("targets.targetid"))
    search_terms = relationship('SearchTerms', backref="DataFiles", uselist=True, cascade="save-update, merge, delete, delete-orphan")
    json_keyword = relationship('JsonKeywords', backref="DataFiles", uselist=True, cascade="save-update, merge, delete, delete-orphan")
    level = Column(CHAR(1))

    @reprocess
    def create(session, **kw):
        datafile_qobj = session.query(DataFiles).filter(
            DataFiles.source == kw['source']).first()

        if datafile_qobj is None:
            datafile_qobj = DataFiles(**kw)
            session.add(datafile_qobj)
        else:
            upc_id = kw.pop('upcid')
            session.query(DataFiles).\
                filter(DataFiles.upcid == upc_id).\
                update(kw)
        session.commit()

        return datafile_qobj


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

    @reprocess
    def create(session, **kw):
        # Get the instrument from the instruments table.
        instrument_qobj = session.query(Instruments).filter(
            Instruments.instrument == kw['instrument'],
            Instruments.spacecraft == kw['spacecraft']).first()

        # If no matching instrument is found, create the entry in the database
        #  and access the new instance.
        if instrument_qobj is None:
            instrument_qobj = Instruments(**kw)
            session.add(instrument_qobj)
            session.commit()
        return instrument_qobj


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

    @reprocess
    def create(session, **kw):
        target_qobj = session.query(Targets).filter(
            Targets.targetname == kw['targetname'].upper()).first()

        # If no matching table is found, create the entry in the database and
        #  access the new instance.
        if target_qobj is None:
            target_qobj = Targets(**kw)
            session.add(target_qobj)
            session.commit()
        return target_qobj


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
    starttime = Column(DateTime)
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
    targetid = Column(Integer, ForeignKey('targets.targetid'))
    instrumentid = Column(Integer, ForeignKey('instruments.instrumentid'))
    pdsproductid = Column(String(256))
    err_flag = Column(Boolean)
    isisfootprint = Column(Geometry('MULTIPOLYGON'))

    @reprocess
    def create(session, **kw):
        search_terms_qobj = session.query(SearchTerms).filter(
            SearchTerms.upcid == kw['upcid']).first()

        if search_terms_qobj is None:
            search_terms_qobj = SearchTerms(**kw)
            session.add(search_terms_qobj)
        else:
            upc_id = kw.pop('upcid')
            session.query(SearchTerms).\
                filter(SearchTerms.upcid == upc_id).\
                update(kw)
        session.commit()

        return search_terms_qobj


class JsonKeywords(BaseMixin, Base):
    __tablename__ = "json_keywords"
    upcid = Column(Integer, ForeignKey('datafiles.upcid'), primary_key=True)
    jsonkeywords = Column(MutableDict.as_mutable(JSONB))

    @reprocess
    def create(session, **kw):
        json_keywords_qobj = session.query(JsonKeywords).filter(
            JsonKeywords.upcid == kw['upcid']).first()

        if json_keywords_qobj is None:
            json_keywords_qobj = JsonKeywords(**kw)
            session.add(json_keywords_qobj)
        else:
            upc_id = kw.pop('upcid')
            session.query(JsonKeywords).\
                filter(JsonKeywords.upcid == upc_id).\
                update(kw)
        session.commit()

        return json_keywords_qobj

class_map = {
    'datafiles': DataFiles,
    'instruments': Instruments,
    'targets' : Targets,
    'search_terms': SearchTerms
}

def create_upc_database():
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
