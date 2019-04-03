#!/usr/bin/env python

import redis
from pds_pipelines.config import redis_info as ri
from pds_pipelines.config import default_namespace


class RedisQueue(object):
    """
    Attributes
    ----------
    _db
    id_name : str
    """

    def __init__(self, name, namespace=default_namespace):
        """
        Parameters
        ----------
        name : str
        namespace : str
        """

        # self._db=redis.Redis(host=ri['host'], port=ri['port'], db=ri['db'])
        self._db=redis.StrictRedis(host=ri['host'], port=ri['port'], db=ri['db'])
        # @TODO change back to non-local queue
        #self._db = redis.StrictRedis(host='redis')
        #self._db = redis.StrictRedis(host='localhost')
        self.id_name = '%s:%s' % (namespace, name)

    def RemoveAll(self):
        self._db.delete(self.id_name)

    def getQueueName(self):
        """
        Returns
        -------
        str
            id_name
        """
        return self.id_name

    def QueueSize(self):
        """
        Returns
        -------
        str
            _db.llen(self.id_name)
        """
        return self._db.llen(self.id_name)

    def QueueAdd(self, element):
        """
        Parameters
        ----------
        element : str
        """
        self._db.rpush(self.id_name, element)

    def QueueGet(self):
        """
        Returns
        -------
        str
            item
        """
        item = self._db.lpop(self.id_name)
        return item

    def ListGet(self):
        """
        Returns
        -------
        list
        """
        list = self._db.lrange(self.id_name, 0, -1)
        return list

    def RecipeGet(self):
        """
        Returns
        -------
        recipe : str
        """
        recipe = self._db.lrange(self.id_name, 0, -1)
        return recipe

    def QueueRemove(self, element):
        """
        Parameters
        ----------
        element : str
        """
        value = int(0)
        self._db.lrem(self.id_name, value, element)

    def Qfile2Qwork(self, popQ, pushQ):
        """
        Parameters
        ----------
        popQ : str
        pushQ : str

        Returns
        -------
        str
            item
        """
        item = self._db.rpoplpush(popQ, pushQ)
        return item
