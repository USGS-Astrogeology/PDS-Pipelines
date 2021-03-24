#!/usr/bin/env python
import sys
import argparse
from pds_pipelines.queueing import IngestQueueProcess

def parse_args():
    parser = argparse.ArgumentParser(description='PDS DI Database Ingest')

    parser.add_argument('--archive', '-a', dest="archive", required=True,
                        help="Enter archive - archive to ingest")

    parser.add_argument('--volume', '-v', dest="volume",
                        help="Enter volume to Ingest")

    parser.add_argument('--log', '-l', dest="log_level",
                        choices=['DEBUG', 'INFO', 'WARNING',
                                'ERROR', 'CRITICAL'],
                        help="Set the log level.", default='INFO')

    parser.add_argument('--search', '-s', dest="search",
                        help="Enter string to search for")

    parser.add_argument('--namespace', '-n', dest="namespace",
                        help="The namespace used for this queue.")

    parser.add_argument('--link-only', dest='ingest', action='store_false')
    parser.set_defaults(ingest=True)
    parser.set_defaults(search='')

    args = parser.parse_args()
    return args


def main(user_args):
    archive = user_args.archive
    volume = user_args.volume
    search = user_args.search
    log_level = user_args.log_level
    namespace = user_args.namespace
    try:
        process = IngestQueueProcess('Ingest', archive, volume, search, log_level, namespace)
    except KeyError:
        exit()
    matching_files = process.get_matching_files()
    process.run(matching_files, False)


if __name__ == "__main__":
    sys.exit(main(parse_args()))
