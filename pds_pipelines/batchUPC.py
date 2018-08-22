#!/usgs/apps/anaconda/bin/python

import json
from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files, Archives
from pds_pipelines.config import pds_info, pds_db


def main():
    PDS_info = json.load(open(pds_info, 'r'))
    reddis_queue = RedisQueue('UPC_ReadyQueue')

    try:
        # Safe to use prd database here because there are no writes/edits.
        session, _ = db_connect(pds_db)

    # @TODO Catch exceptions by type.  Bad practice to 'except Exception,' but
    #   I don't know what exception could happen here.
    except Exception as e:
        print(e)
        return 1

    # For each archive in the db, test if there are files that are ready to
    #  process
    for archive_id in session.query(Files.archiveid).distinct():
        result = session.query(Files).filter(Files.archiveid == archive_id,
                                             Files.upc_required == 't')

        # Get filepath from archive id
        archive_name = session.query(Archives.archive_name).filter(
            Archives.archiveid == archive_id).first()

        # No archive name = no path.  Skip these values.
        if (archive_name is None):
            # @TODO log an error
            continue

        try:
            # Since results are returned as lists, we have to access the 0th
            #  element to pull out the string archive name.
            fpath = PDS_info[archive_name[0]]['path']
        except KeyError:
            continue

        # Add each file in the archive to the redis queue.
        for element in result:
            fname = fpath + element.filename
            fid = element.fileid
            reddis_queue.QueueAdd((fname, fid, archive_name[0]))
    return 0


if __name__ == "__main__":
    main()
