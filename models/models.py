from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import (Table, MetaData, Column, Integer, Float,
                        Time, String, Boolean, PrimaryKeyConstraint)
from geoalchemy2 import Geometry

Base = declarative_base()


def create_table(keytype, *args, **kwargs):
    """ Returns a table based on the keytype description.

    Parameters
    ----------
    keytype : str
        A type description of the table's value.

    Returns
    -------
    out : :class:`.MetaString` or :class:`.MetaPrecision` or
          :class:`.MetaInteger` or :class:`.MetaTime` or
          :class:`.MetaBoolean` or :class:`.Instruments or
          :class:`.DataFiles or :class:`.Keywords or :class:`.Targets
        A SQLAlchemy table with type specific column specification.
    """

    try:
        return class_map[keytype.lower()](**kwargs)
    except NameError:
        print('Keytype {} not found\n'.format(keytype))


# @TODO Bob/Scott/J ask about primary key
class DataFiles(Base):
    __tablename__ = 'datafiles'
    # @TODO add default = nextval('datafiles_upcid_seq'::regclass)
    upcid = Column(Integer, primary_key=True)
    isisid = Column(String(256))
    productid = Column(String(256))
    edr_source = Column(String(1024))
    edr_detached_label = Column(String(1024))
    instrumentid = Column(Integer)
    targetid = Column(Integer)


class Instruments(Base):
    __tablename__ = 'instruments_meta'
    # @TODO add default nextval('instruments_meta_instrumentid_seq'::regclass)
    instrumentid = Column(Integer, primary_key=True)
    instrument = Column(String(256), nullable=False)
    displayname = Column(String(256))
    mission = Column(String(256))
    spacecraft = Column(String(256))
    description = Column(String(256))
    product_type = Column(String(8))


# @TODO
"""
class Targets(Base):
    __table__ = Table('targets_meta', metadata, autoload=True)
"""


class Keywords(Base):
    __tablename__ = 'keywords'
    # @TODO add default nextval('keywords_typeid_seq'::regclass)
    typeid = Column(Integer, primary_key=True)
    instrumentid = Column(Integer)
    datatype = Column(String(20), nullable=False)
    typename = Column(String(256))
    displayname = Column(String(256))
    description = Column(String(2048))
    shapecol = Column(String(10))
    unitid = Column(Integer)


class Meta(object):
    # Enforce compound primary key constraint
    __table_args__ = (PrimaryKeyConstraint('upcid', 'typeid'),)
    upcid = Column(Integer)
    typeid = Column(Integer)


class MetaPrecision(Meta, Base):
    __tablename__ = 'meta_precision'
    value = Column(Float)


class MetaTime(Meta, Base):
    __tablename__ = 'meta_time'
    value = Column(Time)


class MetaString(Meta, Base):
    __tablename__ = 'meta_string'
    value = Column(String)
    hibernate_ver = Column(Integer, default=0)


class MetaInteger(Meta, Base):
    __tablename__ = 'meta_integer'
    value = Column(Integer)


class MetaBoolean(Meta, Base):
    __tablename__ = 'meta_boolean'
    value = Column(Boolean)


class MetaGeometry(Meta, Base):
    __tablename__ = 'meta_geometry'
    value = Column(Geometry('geometry'))


class_map = {
    'string': MetaString,
    'double': MetaPrecision,
    'time': MetaTime,
    'integer': MetaInteger,
    'boolean': MetaBoolean,
    'datafiles': DataFiles,
    'keywords': Keywords,
    'instruments': Instruments
}