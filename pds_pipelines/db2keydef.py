import argparse
from pds_pipelines.db import db_connect
from pds_pipelines.models.upc_models import Keywords

import json

class Args:
    def __init__(self):
        pass

    def parse_args(self):

        parser = argparse.ArgumentParser(description='Database to JSON keyword skeleton generator')

        parser.add_argument('--instrument', '-i', nargs='+', dest="instrument", required=True,
                          help="A space-separated list of instrument ids such as -i 1 2 3 5 8 13")

        parser.add_argument('--out', '-o', dest="out", required=True, help="Fully qualified path to the desired output destination.  JSON will be writen here.")

        args = parser.parse_args()

        self.instrument = args.instrument
        self.out = args.out

def main():
    args = Args()
    args.parse_args()
    out = args.out
    session, _ = db_connect('upcdev')
    out_dict = {'instrument': {}}
    for iid in args.instrument:
        out_dict['instrument'][iid] = {}
        keywords = session.query(Keywords).filter(
            Keywords.instrumentid == iid).all()
        for row in keywords:
            out_dict['instrument'][iid][row.typename] = {}
            out_dict['instrument'][iid][row.typename]['type'] = row.datatype
            out_dict['instrument'][iid][row.typename]['displayname'] = row.displayname
            out_dict['instrument'][iid][row.typename]['keyword'] = ""

    with open(out, 'w') as f:
        json.dump(out_dict, f, indent=4)

    

if __name__ == "__main__":
    main()
