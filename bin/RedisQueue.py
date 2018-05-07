#!/usgs/apps/anaconda/bin/python

import redis
from config import redis_info as ri


class RedisQueue(object):
    """
    Attributes
    ----------
    __db
    id_name : str
    """

    def __init__(self, name, namespace='queue'):
        """
        Parameters
        ----------
        name : str
        namespace : str
        """

        # self.__db=redis.Redis(host=ri['host'], port=ri['port'], db=ri['db'])
        #self.__db=redis.StrictRedis(host=ri['host'], port=ri['port'], db=ri['db'])
        self.__db = redis.StrictRedis()
        self.id_name = '%s:%s' % (namespace, name)

    def RemoveAll(self):
        self.__db.delete(self.id_name)

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
            __db.llen(self.id_name)
        """
        return self.__db.llen(self.id_name)

    def QueueAdd(self, element):
        """
        Parameters
        ----------
        element : str
        """
        self.__db.rpush(self.id_name, element)

    def QueueGet(self):
        """
        Returns
        -------
        str
            item
        """
        item = self.__db.rpop(self.id_name)
        return item

    def ListGet(self):
        """
        Returns
        -------
        list
        """
        list = self.__db.lrange(self.id_name, 0, -1)
        return list

    def RecipeGet(self):
        """
        Returns
        -------
        recipe : str
        """
        recipe = self.__db.lrange(self.id_name, 0, -1)
        return recipe

    def QueueRemove(self, element):
        """
        Parameters
        ----------
        element : str
        """
        value = int(0)
        self.__db.lrem(self.id_name, value, element)

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
        item = self.__db.rpoplpush(popQ, pushQ)
        return item
