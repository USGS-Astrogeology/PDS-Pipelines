#!/usgs/apps/anaconda/bin/python

import os
import subprocess
import sys

import redis
import json
from collections import OrderedDict

from Process import *
from RedisQueue import *


class Recipe(Process):
    """
    Parameters
    ----------
    Process

    Attributes
    ----------
    recipe : list
    """

    def __init__(self):

        self.recipe = []

    def AddJsonFile(self, file):
        """
        Parameters
        ----------
        file : str
        """

        testjson = json.loads(open(file).read(), object_pairs_hook=OrderedDict)

        for IP in testjson['recipe']:
            process = str(IP)
            processDict = {}
            processDict[process] = OrderedDict()
            for k, v in testjson['recipe'][process].items():
                processDict[process][str(k)] = str(v)

            self.recipe.append(processDict)

    def getRecipe(self):
        """
        Returns
        -------
        list
            self.recipe
        """
        return self.recipe

    def getRecipeJSON(self, mission, process):
        """
        Parameters
        ----------
        mission : str
        process : str

        Returns
        -------
        str
            output
        """

        if process == 'service':
            servicedict = {'ISSNA': '/usgs/cdev/PDS/recipe/POWrecipeISSNA.json',
                           'CTX': '/usgs/cdev/PDS/recipe/POWrecipeCTX.json',
                           'SSI': '/usgs/cdev/PDS/recipe/POWrecipe_galileoSSI.json',
                           'NIR': '/usgs/cdev/PDS/recipe/POWrecipeCLEM_NIR.json',
                           'LWIR': '/usgs/cdev/PDS/recipe/POWrecipeCLEM_LWIR.json',
                           'HIRES': '/usgs/cdev/PDS/recipe/POWrecipeCLEM_HIRES.json',
                           'UVVIS': '/usgs/cdev/PDS/recipe/POWrecipeCLEM_UVVIS.json',
                           'THEMIS_IR': '/usgs/cdev/PDS/recipe/POWrecipeTHMIR.json',
                           'NACL': '/usgs/cdev/PDS/recipe/POWrecipeLRO_NACL.json',
                           'NACR': '/usgs/cdev/PDS/recipe/POWrecipeLRO_NACR.json',
                           'MOC-NA': '/usgs/cdev/PDS/recipe/POWrecipe_MOCNA.json',
                           'MOC_WA': '/usgs/cdev/PDS/recipe/POWrecipe_MOCWA.json',
                           'MDIS-NAC': '/usgs/cdev/PDS/recipe/POWrecipeMDIS_NAC.json',
                           'MDIS-WAC': '/usgs/cdev/PDS/recipe/POWrecipeMDIS_WAC.json',
                           'MOC-WA': '/usgs/cdev/PDS/recipe/POWrecipeMGS_MOCWA.json',
                           'VISUAL_IMAGING_SUBSYSTEM_CAMERA_A': '/usgs/cdev/PDS/recipe/POWrecipeVikVisA.json',
                           'VISUAL_IMAGING_SUBSYSTEM_CAMERA_B': '/usgs/cdev/PDS/recipe/POWrecipeVikVisB.json',
                           'MAP': '/usgs/cdev/PDS/recipe/MAPrecipe.json'
                           }
            output = servicedict[mission]
        elif process == 'upc':
            upcdict = {'CTX': '/usgs/cdev/PDS/recipe/UPCrecipeCTX.json',
                       'themisIR_EDR': '/usgs/cdev/PDS/recipe/UPCrecipeTHMIR.json'
                       }
            output = upcdict[mission]

        elif process == 'thumbnail':
            thumbdict = {'CTX': '/usgs/cdev/PDS/recipe/thumbnailrecipeCTX.json',
                         'NACL': '/usgs/cdev/PDS/recipe/thumbnailrecipeLRO_NACL.json'
                         }
            output = thumbdict[mission]

        elif process == 'browse':
            browsedict = {'CTX': '/usgs/cdev/PDS/recipe/browserecipeCTX.json',
                          'NACL': '/usgs/cdev/PDS/recipe/browserecipeLRO_NACL.json'
                          }
            output = browsedict[mission]

        elif process == 'projectionbrowse':
            projectionbrowsedict = {'CTX': '/usgs/cdev/PDS/recipe/projectionbrowserecipeCTX.json',
                                    'NACL': '/usgs/cdev/PDS/recipe/projectionbrowserecipeLRO_NACL.json'
                                    }
            output = projectionbrowsedict[mission]

        return output

    def getProcesses(self):
        """
        Returns
        -------
        list
            processList
        """

        processList = []
        for Tkey in self.recipe:
            for key, value in Tkey.items():
                processList.append(key)

        return processList

    def AddProcess(self, process):
        """
        Parameters
        ----------
        process : str
        """
        self.recipe.append(process)

    def TestgetStep(self, file):
        """
        Parameters
        ----------
        file : str

        Returns
        -------
        list
            stepList
        """
        stepList = []
        testjson = json.loads(open(file).read(), object_pairs_hook=OrderedDict)

        for IP in testjson['recipe']:
            stepList.append(IP)

        return stepList

    def TestRecipe(self, file, element):
        """
        Parameters
        ----------
        file : str
        element : str
        """
        testjson = json.loads(open(file).read(), object_pairs_hook=OrderedDict)

        for IP in testjson['recipe'][element]:
            process = str(IP)
            processDict = {}
            processDict[process] = OrderedDict()
            for k, v in testjson['recipe'][element][process].items():
                processDict[process][str(k)] = str(v)

            self.recipe.append(processDict)
