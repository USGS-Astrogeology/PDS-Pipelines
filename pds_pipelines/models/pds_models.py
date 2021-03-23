import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TIMESTAMP
from sqlalchemy import (Column, Integer, Float, String, Boolean,
                        PrimaryKeyConstraint, ForeignKey)
from sqlalchemy.orm import relationship
from sqlalchemy_utils import database_exists, create_database

from pds_pipelines.db import db_connect
from pds_pipelines.config import pds_db

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

class ProcessRuns(BaseMixin, Base):
    __tablename__ = 'process_runs'
    processid = Column(Integer, primary_key=True)
    fileid = Column(Integer, ForeignKey('files.fileid'))
    process_date = Column(TIMESTAMP)
    process_typeid = Column(Integer)
    process_out = Column(Boolean)


class Files(BaseMixin, Base):
    __tablename__ = 'files'
    fileid = Column(Integer, primary_key=True)
    archiveid = Column(Integer, ForeignKey('archives.archiveid'))
    filename = Column(String(2048))
    entry_date = Column(TIMESTAMP)
    checksum = Column(String(35))
    upc_required = Column(Boolean)
    validation_required = Column(Boolean)
    header_only= Column(Boolean)
    release_date = Column(TIMESTAMP)
    file_url = Column(String(2048))
    isis_errors = Column(Boolean, default=False)
    file_size = Column(Integer)
    di_pass = Column(Boolean)
    di_date = Column(TIMESTAMP)
    process_run = relationship('ProcessRuns', backref='files', uselist=True, cascade="save-update, merge, delete, delete-orphan")


class Archives(BaseMixin, Base):
    __tablename__ = 'archives'
    archiveid = Column(Integer, primary_key=True, autoincrement=True)
    archive_name = Column(String(1024))
    missionid = Column(Integer)
    pds_archive = Column(Boolean)
    primary_node = Column(String(64))
    file = relationship('Files', backref='archives', uselist=False)


def create_pds_database():
    try:
        Session, engine = db_connect(pds_db)
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
        Base.metadata.create_all(tables=[ProcessRuns.__table__,
                                         Files.__table__,
                                         Archives.__table__])
