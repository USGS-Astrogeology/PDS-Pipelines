import os, sys
import pvl
import json
import argparse
import urllib.request


def load_pvl(pvl_file_path):
    with open(pvl_file_path, 'r') as f:
        f.readline()
        data = f.read()
    voldesc = pvl.loads(data)
    return voldesc

class Args:
    def __init__(self):
        pass

    def parse_args(self):
        parser = argparse.ArgumentParser()
        group = parser.add_mutually_exclusive_group()
        group.add_argument('local', nargs = '?', help='Input local Voldesc File path or URL (point to a single Voldesc file)')
        group.add_argument('--textfile','-f',help='Input text file path (file should contain a list of paths or URLs)')
        parser.add_argument('--output','-o',help='Output file path (outputs to json)')
        args = parser.parse_args()
        self.local = args.local
        self.textfile = args.textfile
        self.output = args.output

def ds_count(voldescPvl):
    args = Args()
    args.parse_args()
    vol_val = {}
    dataset_id = voldescPvl['VOLUME']['DATA_SET_ID']
    volume_name = voldescPvl['VOLUME']['VOLUME_NAME']
    if isinstance(dataset_id, (list, tuple, set)):
        vol_val[volume_name] = len(dataset_id)
    else:
        vol_val[volume_name]= 1
    return vol_val
    
def main():
    args = Args()
    args.parse_args()
    a = {}

    if args.textfile is not None:
        filePath = open(args.textfile,'r')
        lines = filePath.readlines()
        length = len(lines)
        
        for n in range(length):
            if 'https' in lines[n] or 'http' in lines[n] or 'ftp' in lines[n]:
                voldesc = urllib.request.urlopen(lines[n])
                voldescPvl = pvl.load(voldesc)     
            else:
                voldescPvl = load_pvl(lines[n].rstrip())
            a.update(ds_count(voldescPvl))    
    else:
        if 'https' in args.local or 'http' in args.local or 'ftp' in args.local:
            voldesc = urllib.request.urlopen(args.local)
            voldescPvl = pvl.load(voldesc)
        else:
            filePath = open(str(args.local), 'r')
            voldescPvl = load_pvl(str(args.local))
        a.update(ds_count(voldescPvl))
    


    if args.output is not None:
        f = open(args.output,'w')
        f.write(str(json.dumps(a)))
    else:
        print(json.dumps(a))

if __name__ == '__main__':
    main()