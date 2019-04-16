#!/usr/bin/env python
import argparse

from pds_pipelines.db import db_connect
from pds_pipelines.models.clusterjobs_models import Processing

class Args(object):
    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--key',
                            '-k',
                            dest='key',
                            help="Key for which timestamps will be cleared")

        args = parser.parse_args()
        self.key = args.key
        

def main():
    args = Args()
    args.parse_args()
    key = args.key

    if key is None:
        print("No key specified.\nUsage:\t python clear_timestamps.py -k <job_key>")
        exit(1)

    session, engine = db_connect('clusterjob_prd')
    record = session.query(Processing).filter(Processing.key == key).first()

    record.queued = None
    record.started = None
    record.finished = None
    record.accessed = None
    record.notified = None
    record.purged = None

    session.merge(record)
    session.flush()
    session.commit()

main()
