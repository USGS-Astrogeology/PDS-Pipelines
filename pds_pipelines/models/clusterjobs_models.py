from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import (Column, Integer, Float,
                        Time, String, Boolean, PrimaryKeyConstraint, ForeignKey)

Base = declarative_base()

class Processing(Base):
    __tablename__ = 'processing'
    processingid = Column(Integer, primary_key=True, autoincrement=True)
    customerid = Column(Integer)
    submitted = Column(Time)
    queued = Column(Time)
    started = Column(Time)
    finished = Column(Time)
    accessed = Column(Time)
    typeid = Column(Integer)
    save = Column(Time)
    xml = Column(String)
    error = Column(String)
    key = Column(String(64))
    notified = Column(Time)
    title = Column(String(256))
    description = Column(String)
    purged = Column(Time)
    template = Column(Boolean)


class ProcessTypes(Base):
    __tablename__ = 'processtypes'
    typeid = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64))
