#!/usgs/apps/anaconda/bin/python

import datetime
import pytz
import json
from pds_pipelines.FindDI_Ready import archive_expired, volume_expired
from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files
from pds_pipelines.config import pds_info, pds_db


def main():
    PDS_info = json.load(open(pds_info, 'r'))
    reddis_queue = RedisQueue('DI_ReadyQueue')

    try:
        session, _ = db_connect(pds_db)
    except Exception as e:
        print(e)
        return 1

    for target in PDS_info:
        archive_id = PDS_info[target]['archiveid']
        td = (datetime.datetime.now(pytz.utc)
              - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        testing_date = datetime.datetime.strptime(str(td), "%Y-%m-%d %H:%M:%S")
        expired = archive_expired(session, archive_id, testing_date)
        # If any files within the archive are expired, send them to the queue
        if expired.count():
            # @TODO get rid of print statements or enable with --verbose?
            for f in expired:
                reddis_queue.QueueAdd(f.filename)
            print('Archive {} DI Ready: {} Files'.format(
                target, str(expired.count())))
        else:
            print('Archive {} DI Current'.format(target))
    return 0


if __name__ == "__main__":
    main()
