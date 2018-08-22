#!/usgs/apps/anaconda/bin/python

import os
import sys
import datetime
import pytz

from pds_pipelines.PDS_DBsessions import *


class PDS_DBquery(PDS_DBsessions):
    """
    Parameters
    ----------
    PDS_DBsessions
    """
    def jobKey(self):
        """
        Returns
        ------
        str
            key
        """

        queryOBJ = self.session.query(self.processingTAB.key).filter(
            self.processingTAB.queued == None).order_by(self.processingTAB.submitted).first()

        for key in queryOBJ:
            return key

    def jobXML4Key(self, key):
        """
        Parameters
        ----------
        key

        Returns
        -------
        xml
            queryOBJ.xml
        """
        queryOBJ = self.session.query(self.processingTAB.xml).filter(
            self.processingTAB.key == key).first()
        return queryOBJ.xml

    def setJobsQueued(self, inkey):
        """
        Parameters
        ----------
        inkey

        Returns
        -------
        str
            Success is succesful, Error otherwise
        """
        date = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
        try:
            queryOBJ = self.session.query(self.processingTAB).filter(
                self.processingTAB.key == inkey).one()
            queryOBJ.queued = date
            self.session.commit()
            return 'Success'
        except:
            return 'Error'

    def setJobsStarted(self, inkey):
        """
        Parameters
        ----------
        inkey

        Returns
        -------
        str
            Success is succesful, Error otherwise
        """
        date = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
        try:
            queryOBJ = self.session.query(self.processingTAB).filter(
                self.processingTAB.key == inkey).one()
            queryOBJ.started = date
            self.session.commit()
            return 'Success'
        except:
            return 'Error'

    def setJobsFinished(self, inkey):
        """
        Parameters
        ----------
        inkey

        Reurns
        ------
        str
            Success is succesful, Error otherwise
        """
        date = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S.%f")
        try:
            queryOBJ = self.session.query(self.processingTAB).filter(
                self.processingTAB.key == inkey).one()
            queryOBJ.finished = date
            self.session.commit()
            return 'Success'
        except:
            return 'Error'

    def addErrors(self, key, errorxml):
        """
        Parameters
        ----------
        key
        errorxml

        Returns
        -------
        str
            Success is succesful, Error otherwise
        """
        try:
            queryOBJ = self.session.query(self.processingTAB).filter(
                self.processingTAB.key == key).one()
            queryOBJ.error = errorxml
            self.session.commit()
            return 'Success'
        except:
            return 'Error'
