#!/usgs/apps/anaconda/bin/python

from collections import OrderedDict


class SubLoggy(object):
    """
    Parameters
    ----------
    process
    """
    def __init__(self, process):
    
        self.process = process
        self.PDict = {}
        self.PDict[self.process] = OrderedDict()

    def setStatus(self, stat):
        """
        Parameters
        ----------
        stat : str
        """
  
        self.PDict[self.process]['status'] = stat 

    def setCommand(self, cmd):
        """
        Parameters
        ----------
        cmd : str
        """
        self.PDict[self.process]['command'] = cmd

    def setHelpLink(self, Hlink):
        """
        Parameters
        ----------
        Hlink : str
        """
        self.PDict[self.process]['helplink'] = Hlink

    def errorOut(self, error):
        """
        Parameters
        ----------
        error : str
        """
        self.PDict[self.process]['error'] = error

    def getSLprocess(self):
        """
        Returns
        ----------
        self.PDict : dict
        """
        return self.PDict 
