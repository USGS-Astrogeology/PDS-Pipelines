#!/usr/bin/env python

import argparse
import logging
import json

from pds_pipelines.models.upc_models import (MetaTime, MetaGeometry, MetaString,
                                             MetaBoolean, MetaBands,
                                             MetaPrecision, MetaInteger,
                                             DataFiles, Instruments, Keywords,
                                             Targets, NewStats)
from pds_pipelines.db import db_connect
from pds_pipelines.config import upc_db
from sqlalchemy import func, and_, select, join

class Autodict(dict):
    """
    A dictionary that auto fills missing intermediate keys.
    """
    def __missing__(self, key):
        value = self[key] = type(self)()
        return value


class Args(object):
    def __init__(self):
        self.date = None
        self.instrument = None
        self.spacecraft = None
        self.database = None
        self.target = None
        self.loglevel = None
        self.statistics = None


    def parse_args(self):
        parser = argparse.ArgumentParser(description='Database synchronization tool')

        parser.add_argument('-p', dest="date",
                            help="Sync data processed after the specified date")

        parser.add_argument('-i', dest="instrument",
                            help="Sync data for the specified instrument")

        parser.add_argument('-s', dest="spacecraft",
                            help="Sync data for the specified spacecraft")

        parser.add_argument('-d', dest="database",
                            help="Sync only to the specified database on the destination server")

        parser.add_argument('-t', dest="target",
                            help="Sync for the target, ignore UPC records on other targets")

        parser.add_argument('-v', dest="loglevel",
                            help="Enable verbose output", action="store_const",
                            const=logging.INFO, default=logging.WARNING)

        parser.add_argument('-S', dest="statistics",
                            help="Only display statistics, do not sync data",
                            action="store_true")

        args = parser.parse_args()

        self.date = args.date
        self.instrument = args.instrument
        self.spacecraft = args.spacecraft
        self.database = args.database
        self.target = args.target
        self.loglevel = args.loglevel
        self.statistics = args.statistics


def main():
    args = Args()
    args.parse_args()
    logging.basicConfig(level=args.loglevel)
    source_session, _ = db_connect(upc_db)

    upc_ids = get_upc_ids(source_session, args.date, args.instrument,
                          args.spacecraft, args.target)

    if args.statistics:
        get_stats(source_session, upc_ids)
        return

    targets = ['public_mars', 'public_moon', 'public_other']
    #targets = ['upcdev_mars', 'upcdev_moon', 'upcdev_other']

    target_sessions = {}

    for target in targets:
        session, _ = db_connect(target)
        target_sessions[target] = session

    instrument = get_instrument(source_session, args.instrument,
                                args.spacecraft)

    for target_session in target_sessions.values():
        sync_instrument(target_session, instrument)

    instrument_keywords = get_keywords(source_session, args.instrument,
                                       args.spacecraft)
    common_keywords = get_keywords(source_session, 'COMMON')

    # Sync keywords, instruments with all databases
    for target_session in target_sessions.values():
        #sync_instrument(target_session, instrument)
        sync_keywords(target_session, instrument_keywords)
        sync_keywords(target_session, common_keywords)
        target_session.commit()

    meta_types = [MetaTime, MetaString, MetaGeometry, MetaBoolean, MetaBands,
                  MetaPrecision, MetaInteger]

    for upc_id in upc_ids:
        sync_upc_id(source_session, target_sessions, upc_id, meta_types)


def get_stats(session, upc_ids):
    """
    Prints statistics regarding the list of supplied upc ids.

    Parameters
    ----------
    session : sqlalchemy session
        The sqlalchemy session with which we will query the database.
    upc_ids : list
        The list of upc_ids about which we will print statistics.

    Returns
    -------
    None
    """
    j = join(Targets, DataFiles, Targets.targetid == DataFiles.targetid)
    j = j.join(Instruments, DataFiles.instrumentid == Instruments.instrumentid)

    # Get total number of files matching criteria
    stmt = select([func.count("DataFiles.*"), Instruments.instrument,
                   Instruments.spacecraft, Targets.targetname]).select_from(
                       j).group_by(Instruments.instrument,
                                   Instruments.spacecraft, Targets.targetname)

    stmt = stmt.where(DataFiles.upcid.in_(upc_ids))

    j = j.join(MetaBoolean, DataFiles.upcid == MetaBoolean.upcid)
    # Get error information
    stmt_err = select([func.count("DataFiles.*"), Instruments.instrument,
                       Instruments.spacecraft, Targets.targetname]).select_from(
                           j).group_by(Instruments.instrument,
                                       Instruments.spacecraft, Targets.targetname)

    stmt_err = stmt_err.where(DataFiles.upcid.in_(upc_ids))
    stmt_err = stmt_err.where(Keywords.typename == 'error')
    stmt_err = stmt_err.where(MetaBoolean.value)

    errors = session.execute(stmt_err)

    # Dict that 'autovivifies' intermediate levels
    out = Autodict()
    for i in errors:
        out[i.spacecraft][i.instrument][i.targetname]['errors'] = i.count_1

    totals = session.execute(stmt)

    for i in totals:
        out[i.spacecraft][i.instrument][i.targetname]['totals'] = i.count_1

    j = join(Targets, DataFiles, Targets.targetid == DataFiles.targetid)
    j = j.join(Instruments, DataFiles.instrumentid == Instruments.instrumentid)
    j = j.join(MetaTime, MetaTime.upcid == DataFiles.upcid)
    j = j.join(Keywords, Keywords.typeid == MetaTime.typeid)

    stmt = select([func.min(MetaTime.value), func.max(MetaTime.value),
                   Instruments.instrument, Instruments.spacecraft,
                   Targets.targetname]).select_from(j).group_by(
                       Instruments.instrument, Instruments.spacecraft,
                       Targets.targetname)

    stmt = stmt.where(DataFiles.upcid.in_(upc_ids))

    min_max = session.execute(stmt)

    for i in min_max:
        out[i.spacecraft][i.instrument][i.targetname]['oldest'] = i.min_1
        out[i.spacecraft][i.instrument][i.targetname]['newest'] = i.max_1

    print(json.dumps(out, indent=1, default=str))


def get_upc_ids(session, date=None, instrument=None, spacecraft=None, target=None):
    """
    Get the upc ids that match the specified arguments

    Parameters
    ----------
    session : sqlalchemy session
        A connected session on which we will query the database.

    date : datetime.date
        Used to specify the start date of the query.

    instrument : str
        The instrument name with on we filter our query.

    spacecraft : str
        The name of the spacecraft on which we filter our query.

    target : str
        The name of the target on which we filter our query.

    Returns
    -------
    out : list
        The list of upc ids matching the specified criteria.
    """
    j = join(MetaTime, Keywords, MetaTime.typeid == Keywords.typeid)
    j = j.join(DataFiles, MetaTime.upcid == DataFiles.upcid)
    j = j.join(Instruments, DataFiles.instrumentid == Instruments.instrumentid)
    j = j.join(Targets, DataFiles.targetid == Targets.targetid)

    stmt = select([MetaTime.upcid]).select_from(j)
    if date:
        processdateid = session.query(Keywords.typeid).filter(
            Keywords.typename == 'processdate')
        stmt = stmt.where(and_(MetaTime.typeid == processdateid,
                               MetaTime.value > date))
    if instrument:
        stmt = stmt.where(Instruments.instrument == instrument)
    if spacecraft:
        stmt = stmt.where(Instruments.spacecraft == spacecraft)
    if target:
        stmt = stmt.where(Targets.targetname == target)

    result = session.execute(stmt)
    ids = [x.upcid for x in result]

    return ids


def get_keywords(session, instrument=None, spacecraft=None):
    """
    Gets all keywords associated with the supplied instrument and spacecraft.

    Parameters
    ----------
    session : sqlalchemy session
        The sqlalchemy session with which we will query the database.

    instrument : str
        The instrument name by which we will filter the query.

    spacecraft : str
        The spacecraft name by which we will filter the query.

    returns:
    out : sqlalchemy query
        The keywords associated with the instrument or spacecraft.  If instrument and
         spacecraft are both None, this contains all keywords.
    """
    stmt = select([Keywords])
    if instrument:
        instrumentids = session.query(Instruments.instrumentid).filter(
            Instruments.instrument == instrument)
        stmt = stmt.where(Keywords.instrumentid.in_(instrumentids))
    if spacecraft:
        instrumentids = session.query(Instruments.instrumentid).filter(
            Instruments.spacecraft == spacecraft)
        stmt = stmt.where(Keywords.instrumentid.in_(instrumentids))

    result = session.query(Keywords).from_statement(stmt)

    return result


def get_instrument(session, instrument=None, spacecraft=None):
    """
    Gets all instruments associated with the given instrument name or spacecraft.

    Parameters
    ----------
    session : sqlalchemy session
        The sqlalchemy session with which we will query the database.

    instrument : str
        The instrument name by which we will filter the query.

    spacecraft : str
        The spacecraft name by which we will filter the query.

    returns:
    out : sqlalchemy query
        The instruments associated with the instrument name or spacecraft. 
         If instrument and spacecraft are both None, this contains all instruments.
    """

    stmt = select([Instruments])

    if spacecraft is not None:
        stmt = stmt.where(Instruments.spacecraft == spacecraft)
    if instrument is not None:
        stmt = stmt.where(Instruments.instrument == instrument)

    result = session.query(Instruments).from_statement(stmt)
    return result

def sync_instrument(target_session, instruments):
    """
    Inserts / updates all supplied instruments into the target database.

    Parameters
    ----------
    target_session : sqlalchemy session
        The sqlalchemy session into which we will insert instruments.

    instrument : list
        The list of instruments that we wish to insert / update in the target
         database.

    returns:
    None
    """
    for i in instruments:
        target_session.merge(i)
    target_session.commit()


def sync_keywords(target_session, keywords):
    """
    Inserts / updates all supplied keywords into the target database.

    Parameters
    ----------
    target_session : sqlalchemy session
        The sqlalchemy session into which we will insert instruments.

    keywords : list
        The list of keywords that we wish to insert / update in the target
         database.

    returns:
    None
    """
    for keyword in keywords:
        target_session.merge(keyword)
    target_session.commit()


def get_dest_session(target_id, dest_sessions):
    """
    Inserts / updates all supplied keywords into the target database.

    Parameters
    ----------
    target_id : int
        The numeric id associated with the target of the product.

    dest_sessions : list[sqlalchemy sessions]
        A list of candidate sessions.

    returns:
    out : sqlalchemy session
        A sqlalchemy session connected to the database best suited for the
         supplied data.
    """
    for _, session in dest_sessions.items():
        target_found = session.query(NewStats).filter(NewStats.targetid == target_id).all()
        if target_found:
            return session
    return dest_sessions['public_other']


def sync_upc_id(source_session, dest_sessions, upc_id, meta_types):
    """
    Synchronize the DataFiles and keywords associated with the supplied upc id.
    
    Parameters
    ----------
    source_session : sqlalchemy session
        A sqlalchemy session connected to the source database.

    dest_sessions : list[sqlalchemy sessions]
        A list containing sessions that are candidate targets for synchronization.

    upc_id : int
        The upc_id of the files + keywords that we wish to syncronize to the target
         database.

    meta_types: list
        A list of datatypes that will be synchronized on the target database, e.g.
         MetaString, MetaInteger, MetaGeometry, etc.  These classes must be mapped
         as part of the ORM.
    """
    data_file = source_session.query(DataFiles).filter(DataFiles.upcid == upc_id).all()
    for i in data_file:
        dest_session = get_dest_session(i.targetid, dest_sessions)
        dest_session.merge(i)
        for datatype in meta_types:
            keywords = source_session.query(datatype).filter(datatype.upcid == upc_id)
            for keyword in keywords:
                dest_session.merge(keyword)

        dest_session.commit()


if __name__ == "__main__":
    main()

