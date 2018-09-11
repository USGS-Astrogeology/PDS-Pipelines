#!/usr/bin/env python

import os
import sys
import json
import logging
import argparse

from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.config import pds_info, pds_log

class Args:
    """
    Attributes
    ----------
    archive : str
    volume : str
    search : str
    """
    def __init__(self):
        pass

    def parse_args(self):

        parser = argparse.ArgumentParser(description='PDS DI Database Ingest')

        parser.add_argument('--archive', '-a', dest="archive", required=True,
                            help="Enter archive - archive to ingest")

        parser.add_argument('--volume', '-v', dest="volume",
                            help="Enter volume to Ingest")

        parser.add_argument('--verbose', help="Enable verbose logging",
                            action="store_const", dest="loglevel",
                            const=logging.INFO, default=logging.WARNING)

        parser.add_argument('--search', '-s', dest="search",
                            help="Enter string to search for")

        parser.add_argument('--link-only', dest='ingest', action='store_false')
        parser.set_defaults(ingest=True)
        args = parser.parse_args()

        self.archive = args.archive
        self.volume = args.volume
        self.loglevel= args.loglevel
        self.search = args.search
        self.ingest = args.ingest

def main():

    # pdb.set_trace()

    args = Args()
    args.parse_args()
    logging.basicConfig(level=args.loglevel)
    RQ_ingest = RedisQueue('Ingest_ReadyQueue')
    RQ_linking = RedisQueue('LinkQueue')

    # Set up logging
    
    logger = logging.getLogger(args.archive + '_INGEST')
    logger.setLevel(logging.INFO)
    logFileHandle = logging.FileHandler(pds_log + 'Ingest.log')
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
    logFileHandle.setFormatter(formatter)
    logger.addHandler(logFileHandle)

    if args.loglevel == logging.INFO:
        print("Log File: {}Ingest.log".format(pds_log))

    PDSinfoDICT = json.load(open(pds_info, 'r'))
    try:
        archivepath = PDSinfoDICT[args.archive]['path'][:-1]
    except KeyError:
        print("\nArchive '{}' not found in {}\n".format(args.archive, pds_info))
        print("The following archives are available:")
        for k in PDSinfoDICT.keys():
            print("\t{}".format(k))
        logging.error("Unable to locate {}".format(args.archive))
        exit()

    if args.volume:
        archivepath = archivepath + '/' + args.volume

    logger.info('Starting Ingest for: %s', archivepath)
    logger.info('Ingest Queue: {}'.format(str(RQ_ingest.id_name)))
    logger.info('Linking Queue: {}'.format(str(RQ_linking.id_name)))

    # Possible bug in RQ?  Can't add to queue in "if fname == voldesc"
    queue_size = RQ_ingest.QueueSize()
    voldescs = []
    for dirpath, dirs, files in os.walk(archivepath):
        for filename in files:
            fname = os.path.join(dirpath, filename)
            if args.search:
                if args.search in fname:
                    try:
                        if os.path.basename(fname) == "voldesc.cat":
                            voldescs.append(fname)
                        if args.ingest:
                            RQ_ingest.QueueAdd((fname, args.archive))
                    except:
                        logger.error('File %s NOT added to Ingest Queue', fname)
                else:
                    continue
            else:
                try:
                    if os.path.basename(fname) == "voldesc.cat":
                        voldescs.append(fname)
                    if args.ingest:
                        RQ_ingest.QueueAdd((fname, args.archive))
                except:
                    logger.error('File %s NOT added to Ingest Queue', fname)

    n_added = RQ_ingest.QueueSize() - queue_size
    for fpath in voldescs:
        RQ_linking.QueueAdd((fpath, args.archive))
    logger.info('Files added to Ingest Queue: %s', n_added)


if __name__ == "__main__":
    sys.exit(main())
