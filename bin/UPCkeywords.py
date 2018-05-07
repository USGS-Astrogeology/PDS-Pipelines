#!/usgs/apps/anaconda/bin/python

import os
import sys
import pvl


def find_keyword(obj, key):
    if key in obj:
        return obj[key]
    for k, v in obj.items():
        if isinstance(v, dict):
            F_item = find_keyword(v, key)
            if F_item is not None:
                return F_item


class UPCkeywords(object):

    def __init__(self, pvlfile):

        self.label = pvl.load(pvlfile)

    def getKeyword(self, group, keyword):

        Gget = find_keyword(self.label, group)
        Gkey = find_keyword(Gget, keyword)
        return Gkey

    def getPolygonKeyword(self, keyword):

        get1 = find_keyword(self.label, 'Polygon')
        Gkey = find_keyword(get1, keyword)
        if keyword == 'CentroidRadius':
            Gkey = Gkey[0]
        return Gkey
