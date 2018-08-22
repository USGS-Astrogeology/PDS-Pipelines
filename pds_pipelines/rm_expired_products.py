import os
from datetime import datetime, timedelta
import sys
import shutil

from pds_pipelines.models import clusterjobs_models
from pds_pipelines.db import db_connect
from sqlalchemy import and_

import pds_pipelines.config as cfg

def remove(path, keys, id2task, session):
    """ Removes a job from the supplied path based on its key.
    
    Parameters
    ----------
    path : String
        The base path of pow/map2 files
    keys : list[sqlalchemy.collections.result(String, String)]
        Tuple of (typeid, key) where 'typeid' determines the path from
         which the key will be deleted and 'key' is the item to be
         deleted.
        A typeid of 1 = POW , 2 = MAP2
    id2task : dict
        A mapping between taskid and task description
    session : sqlAlchemy.Session
        A session object used to update the 'purged' column related to the
         deleted file
    """
    for item in keys:
        typeid = int(item[0])
        f_path = os.path.join(path, id2task[typeid])
        key = item[1]
        f = os.path.join(f_path, key)
        # Remove file or directory matching the key and set purged in db
        try:
            if os.path.isfile(f):
                os.remove(f)
            else:
                shutil.rmtree(f)
            set_purged(session, key)
        except OSError as e:
            print(e)


def set_purged(session, key):
    now = datetime.now()
    k = session.query(clusterjobs_models.Processing).filter(
        clusterjobs_models.Processing.key == key).update({'purged': now})
    session.commit()


def get_old_keys(session, n_days=14):
    cutoff = datetime.now() - timedelta(days=n_days)
    old = session.query(clusterjobs_models.Processing.typeid, clusterjobs_models.Processing.key).filter(
        and_(clusterjobs_models.Processing.notified < cutoff, clusterjobs_models.Processing.purged == None))
    return old


def map_type_ids(session):
    ids = session.query(clusterjobs_models.ProcessTypes.typeid, clusterjobs_models.ProcessTypes.name)
    out = dict(ids)
    return out


def main():
    path = cfg.pow_map2_base
    session, _ = db_connect('clusterjob_prd')
    id2task = map_type_ids(session)
    try:
        n_days = sys.argv[1]
    except IndexError:
        n_days = 14
    old_files = get_old_keys(session)
    remove(path, old_files, id2task, session)
    return 0


if __name__ == "__main__":
    exit(main())
