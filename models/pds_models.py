from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TIMESTAMP
from sqlalchemy import (Column, Integer, Float, String, Boolean,
                        PrimaryKeyConstraint)

Base = declarative_base()

class ProcessRuns(Base):
    __tablename__ = 'process_runs'
    processid = Column(Integer, primary_key=True)
    fileid = Column(Integer)
    process_date = Column(TIMESTAMP)
    process_typeid = Column(Integer)
    process_out = Column(Boolean)


class Files(Base):
    __tablename__ = 'files'
    fileid = Column(Integer, primary_key=True)
    # @TODO set as foreign key for archive
    archiveid = Column(Integer)
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
