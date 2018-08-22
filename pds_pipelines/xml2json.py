import sys
import os
from json import dump
from xmljson import badgerfish as bf
from xml.etree.ElementTree import fromstring, ParseError
import keyword
import glob
from collections import OrderedDict


def set_instrument(in_dict, out_dict):
    out_dict['inst'] = in_dict['instrument']['name']['$']


def set_upc(in_dict, out_dict):
    out_dict['upc'] = {'recipe': OrderedDict()}
    excluded = set(['isis2std', 'reduce'])
    try:
        for proc in in_dict['instrument']['upc']['process']:
            k =  in_dict['instrument']['upc']['process'][proc]['command']['name']['$']
            if k in excluded:
                continue
            out_dict['upc']['recipe'][k] = {}
            for val in list(in_dict['instrument']['upc']['process'][proc]['command']['param']):
                # trim the '=' off of each parameter's name
                arg = val['argument']['$'][0:-1]
                # parameters that are python keywords have an affixed '_', e.g. from = from_
                if keyword.iskeyword(arg):
                    arg = arg + '_'
                value = str(val['value']['$'])
                # values surrounded by % are considered variables.  New recipes simply use the
                #  word 'value' as a keyword for variables
                if value.startswith('%'):
                    value = 'value'
                out_dict['upc']['recipe'][k][arg] = value
    except KeyError as e:
        pass


def set_pow(in_dict, out_dict):
    # @TODO may need to iterate through <pow> to grab additional processes?
    out_dict['pow'] = {'recipe':{}}
    # Copy the "*2isis" and spice init steps from the upc dictionary
    for i in range(2):
        try:
            k,v = list(out_dict['upc']['recipe'].items())[i]
        except IndexError as e:
            break
        out_dict['pow']['recipe'].update({k:v})

    try:
        for proc in in_dict['instrument']['pow']['process']:
            k =  in_dict['instrument']['pow']['process'][proc]['command']['name']['$']
            out_dict['pow']['recipe'][k] = {}
            for val in list(in_dict['instrument']['pow']['process'][proc]['command']['param']):
                # trim the '=' off of each parameter's name
                arg = val['argument']['$'][0:-1]
                # parameters that are python keywords have an affixed '_', e.g. from = from_
                if keyword.iskeyword(arg):
                    arg = arg + '_'
                value = str(val['value']['$'])
                # values surrounded by % are considered variables.  New recipes simply use the
                #  word 'value' as a keyword for variables
                if value.startswith('%'):
                    value = 'value'
                out_dict['pow']['recipe'][k][arg] = value
    except KeyError as e:
        return


    set_cal(in_dict, out_dict, 'pow')
    set_default_c2m(in_dict, out_dict, 'pow')


def set_default_c2m(in_dict, out_dict, group_name):
    out_dict[group_name]['recipe']['cam2map'] = {'from': 'value',
                                                 'to': 'value',
                                                 'map':'value',
                                                 'matchmap':'no',
                                                 'pixres':'value',
                                                 'defaultrange':'value'}


def set_thumbnail(in_dict, out_dict):
    out_dict['reduced'] = {'recipe':{}}
    # Copy the "*2isis" and spice init steps from the upc dictionary
    for i in range(2):
        try:
            k,v = list(out_dict['upc']['recipe'].items())[i]
        except IndexError as e:
            break
        out_dict['reduced']['recipe'].update({k:v})

    set_cal(in_dict, out_dict, 'reduced')
    set_even_odd(in_dict, out_dict, 'reduced')
    set_reduce(in_dict, out_dict, 'reduced')
    set_i2s(in_dict, out_dict, 'reduced')


def set_projected(in_dict, out_dict):
    out_dict['projected'] = {'recipe':{}}
    # Copy the "*2isis" and spice init steps from the upc dictionary
    for i in range(2):
        try:
            k,v = list(out_dict['upc']['recipe'].items())[i]
        except IndexError as e:
            break
        out_dict['projected']['recipe'].update({k:v})

    set_cal(in_dict, out_dict, 'projected')
    set_even_odd(in_dict, out_dict, 'projected')

    # @TODO cam2map + parameters

    set_i2s(in_dict, out_dict, 'projected')


def set_reduce(in_dict, out_dict, group_name):
    try:
        r = in_dict['instrument']['upc']['process']['runbrowsereduce']['command']
    except KeyError:
        return
    r_name = r['name']['$']
    out_dict[group_name]['recipe'][r_name] = {}
    for val in list(r['param']):
        arg = val['argument']['$'][0:-1]
        if keyword.iskeyword(arg):
            arg = arg + '_'
        value = str(val['value']['$'])
        if value.startswith('%'):
            value = 'value'
        out_dict[group_name]['recipe'][r_name][arg] = value


def set_even_odd(in_dict, out_dict, group_name):
    try:
        ctx_eo = in_dict['instrument']['upc']['process']['ctxevenodd']['command']
    except KeyError:
        return
    ctx_eo_name = ctx_eo['name']['$']
    out_dict[group_name]['recipe'][ctx_eo_name] = {}
    for val in list(ctx_eo['param']):
        arg = val['argument']['$'][0:-1]
        if keyword.iskeyword(arg):
            arg = arg + '_'
        value = str(val['value']['$'])
        if value.startswith('%'):
            value = 'value'
        out_dict[group_name]['recipe'][ctx_eo_name][arg] = value 


def set_i2s(in_dict, out_dict, group_name):
    try:
        i2s = in_dict['instrument']['upc']['process']['runbrowse2std']['command']
    except KeyError:
        return
    i2s_name = i2s['name']['$']
    out_dict[group_name]['recipe'][i2s_name] = {}
    for val in list(i2s['param']):
        arg = val['argument']['$'][0:-1]
        if keyword.iskeyword(arg):
            arg = arg + '_'
        value = str(val['value']['$'])
        if value.startswith('%'):
            value = 'value'
        out_dict[group_name]['recipe'][i2s_name][arg] = value
    

def set_cal(in_dict, out_dict, group_name):
    try:
        cal = in_dict['instrument']['pow']['process']['runcalibration']['command']
    except KeyError:
        return
    cal_name = cal['name']['$']
    out_dict[group_name]['recipe'][cal_name] = {}
    for val in list(cal['param']):
        arg = val['argument']['$'][0:-1]
        if keyword.iskeyword(arg):
            arg = arg+'_'
        value = str(val['value']['$'])
        if value.startswith('%'):
            value = 'value'
        out_dict[group_name]['recipe'][cal_name][arg] = value


def writejson(out_file, out_dict):
    with open(out_file,'w+') as f:
        dump(out_dict,f, indent=4)

def main():
    try:
        infile = sys.argv[1]
    except IndexError:
        print("Please specify an input file:\nUsage:\n\t xml2json.py <inputfile.xml> <outputfile.json | outputdirectory>")
        return 1

    out = None
    try:
        out = sys.argv[2]
    except IndexError:
        print("No output file specified -- writing output in input directory.")
        out = os.path.dirname(os.path.realpath(infile))

    for xmlfile in glob.glob(infile):
        out = os.path.dirname(os.path.realpath(xmlfile))
        with open(xmlfile) as f:
            if os.path.isdir(out):
                outfile = os.path.join(out, str(os.path.basename(xmlfile)).replace(".xml",".json"))
            else:
                outfile = out
            try:
                data = f.read()
                xml = bf.data(fromstring(data))
            except ParseError:
                continue
        print(xmlfile)

        recipe = {}
        set_instrument(xml, recipe)
        set_upc(xml, recipe)
        set_pow(xml, recipe)
        set_thumbnail(xml, recipe)
        set_projected(xml, recipe)

        writejson(outfile, recipe)


if __name__ == "__main__":
    main()
