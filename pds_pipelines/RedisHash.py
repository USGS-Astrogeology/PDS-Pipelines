#!/usr/bin/env python

import redis
from pds_pipelines.config import redis_info as ri


class RedisHash(object):

    def __init__(self, name, namespace='user'):
        """
        Parameters
        ----------
        name : str
        namespace : str
        """

        self._db = redis.StrictRedis(
            host=ri['host'], port=ri['port'], db=ri['db'])
        self.id_name = '%s:%s' % (namespace, name)

    def IsInHash(self, element):
        """
        Parameters
        ----------
        element : str

        Returns
        ------
        str
            test
        """
        test = self._db.hexists(self.id_name, element)
        return test

    def HashCount(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hlen(self.id_name)
        return item

    def AddHash(self, element):
        """
        Parameters
        ----------
        element : str
        """
        self._db.hmset(self.id_name, element)

    def RemoveAll(self):
        self._db.delete(self.id_name)

    def Status(self, element):
        """
        Parameters
        ----------
        element : str
        """
        self._db.hset(self.id_name, 'status', element)

    def MAPname(self, element):
        """
        Parameters
        ----------
        element : str
        """
        self._db.hset(self.id_name, 'MAPname', element)

    def getMAPname(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hget(self.id_name, 'MAPname')
        return item

    def getStatus(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hget(self.id_name, 'status')
        return item

    def FileCount(self, element):
        """
        Parameters
        ----------
        element : str
        """
        self._db.hset(self.id_name, 'filecount', element)

    def getFileCount(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hget(self.id_name, 'filecount')
        return item

    def Service(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hget(self.id_name, 'service')
        return item

    def Format(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hget(self.id_name, 'fileformat')
        return item

    def OutBit(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hget(self.id_name, 'outbit')
        return item

    def getGRtype(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hget(self.id_name, 'grtype')
        return item

    def getMinLat(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hget(self.id_name, 'minlat')
        return item

    def getMaxLat(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hget(self.id_name, 'maxlat')
        return item

    def getMinLon(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hget(self.id_name, 'minlon')
        return item

    def getMaxLon(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hget(self.id_name, 'maxlon')
        return item

    def addError(self, infile, error):
        """
        Parameters
        ----------
        infile : str
        error : str

        Returns
        ------
        str
            item
        """
        self._db.hset(self.id_name, infile, error)

    def getKeys(self):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hkeys(self.id_name)
        return item

    def getError(self, file):
        """
        Returns
        ------
        str
            item
        """
        item = self._db.hget(self.id_name, file)
        return item
