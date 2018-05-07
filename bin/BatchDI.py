import datetime
import pytz
import json
from FindDI_Ready import archive_expired, volume_expired
from RedisQueue import RedisQueue
from db import db_connect


def main():
    PDS_info = json.load(open('/usgs/cdev/PDS/bin/PDSinfo.json', 'r'))
    reddis_queue = RedisQueue('DI_ReadyQueue')

    try:
        session, files, archives, _ = db_connect('pdsdi')
    # @TODO Catch exceptions by type.  Bad practice to 'except Exception,' but
    #   I don't know what exception could happen here.
    except Exception as e:
        print(e)
        return 1

    for target in PDS_info:
        archive_id = PDS_info[target]['archiveid']
        td = (datetime.datetime.now(pytz.utc)
              - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        testing_date = datetime.datetime.strptime(str(td), "%Y-%m-%d %H:%M:%S")
        expired = archive_expired(session, archive_id, files, testing_date)
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
