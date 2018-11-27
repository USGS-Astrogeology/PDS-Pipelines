#!/usr/bin/env python

import pvl
import json
from collections import OrderedDict


class MakeMap(object):
    """
    Attributes
    ----------
    mapDICT : dict
    """

    def __init__(self):

        self.mapDICT = {}
        self.mapDICT = OrderedDict()
        self.mapDICT['Group'] = 'Mapping'

    def Projection(self, proj):
        """
        Parameters
        ----------
        proj
        """
        self.mapDICT['ProjectionName'] = proj

    def CLat(self, clat):
        """
        Parameters
        ----------
        clat
        """
        self.mapDICT['CenterLatitude'] = clat

    def CLon(self, clon):
        """
        Parameters
        ----------
        clon
        """
        self.mapDICT['CenterLongitude'] = clon

    def FirstParallel(self, firstParallel):
        """
        Parameters
        ----------
        firstParallel
        """
        self.mapDICT['FirstStandardParallel'] = firstParallel

    def SecondParallel(self, secondParallel):

        """
        Parameters
        ----------
        secondParallel
        """
        self.mapDICT['SecondStandardParallel'] = secondParallel 
      

    def Target(self, target):
        """
        Parameters
        ----------
        target
        """
        self.mapDICT['TargetName'] = target

    def ERadius(self, ER):
        """
        Parameters
        ----------
        ER
        """
        self.mapDICT['EquatorialRadius'] = ER

    def PRadius(self, PR):
        """
        Parameters
        ----------
        PR
        """
        self.mapDICT['PolarRadius'] = PR

    def LatType(self, lattype):
        """
        Parameters
        ----------
        lattype
        """
        self.mapDICT['LatitudeType'] = lattype

    def LonDirection(self, londir):
        """
        Parameters
        ----------
        londir
        """
        self.mapDICT['LongitudeDirection'] = londir

    def LonDomain(self, londom):
        """
        Parameters
        ----------
        londom
        """
        self.mapDICT['LongitudeDomain'] = londom

    def MinLat(self, item):
        """
        Parameters
        ----------
        item
        """
        self.mapDICT['MinimumLatitude'] = item

    def MaxLat(self, item):
        """
        Parameters
        ----------
        item
        """
        self.mapDICT['MaximumLatitude'] = item

    def MinLon(self, item):
        """
        Parameters
        ----------
        item
        """
        self.mapDICT['MinimumLongitude'] = item

    def MaxLon(self, item):
        """
        Parameters
        ----------
        item
        """
        self.mapDICT['MaximumLongitude'] = item

    def PixelRes(self, res):
        """
        Parameters
        ----------
        res
        """
        self.mapDICT['PixelResolution'] = res

    def Map2pvl(self):
        """
        Returns
        ----------
        str
            mappvl
        """
        self.mapDICT['End_Group'] = 'Mapping'

        mappvl = pvl.dumps(self.mapDICT)
        self.mappvl = mappvl

        return mappvl

    def Map2JSON(self):
        """
        Returns
        ----------
        str
            JSONout
        """
        JSONout = json.dumps(self.mapDICT)
        return JSONout

    def Map2File(self, filename):
        """
        Parameters
        ----------
        filename
        """
        self.mapDICT['End_Group'] = 'Mapping'
        tempPVL = pvl.dumps(self.mapDICT)

        with open(filename, 'wb') as f:
            f.write(tempPVL)
