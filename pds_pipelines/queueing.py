import argparse
import json
import logging
import pathlib
import glob
import datetime
import pytz
import os

from shutil import copy2, disk_usage
from sqlalchemy import Date, cast
from sqlalchemy import or_
from os.path import getsize, dirname, splitext, exists, basename, join

from pds_pipelines.models import session_scope
from pds_pipelines.models.pds_models import Files
from pds_pipelines.db import db_connect
from pds_pipelines.redis_queue import RedisQueue
from pds_pipelines.config import pds_info, pds_log, pds_db, workarea, disk_usage_ratio, archive_base

def parse_args():
    parser = argparse.ArgumentParser(description='UPC Queueing')

    parser.add_argument('--archive', '-a', dest="archive", required=True,
                        help="Enter archive - archive to ingest")

    parser.add_argument('--volume', '-v', dest="volume",
                        help="Enter volume to Ingest")

    parser.add_argument('--search', '-s', dest="search",
                        help="Enter string to search for")

    parser.add_argument('--log', '-l', dest="log_level",
                        choices=['DEBUG', 'INFO',
                                'WARNING', 'ERROR', 'CRITICAL'],
                        help="Set the log level.", default='INFO')

    parser.add_argument('--namespace', '-n', dest="namespace",
                        help="The namespace used for this queue.")

    args = parser.parse_args()
    return args


def copy_files(fname, src_dir, dest_dir):
    """ Globs files with shared filename in src_dir and copies them to dest_dir

    Parameters
    ----------
    fname : str
        The name of the file

    src_dir : str
        The directory from which to copy the files

    dest_dir : str
        The directory to which to copy the files

    Returns
    -------
    str
        The destination of the file

    """
    dest_path = dirname(fname)
    dest_path = dest_path.replace(src_dir, dest_dir)
    pathlib.Path(dest_path).mkdir(parents=True, exist_ok=True)
    for f in glob.glob(splitext(fname)[0] + r'.*'):
        copy2(f, dest_path)
    return join(dest_path, basename(fname))


def has_space(elements, src_path, dest_path, ratio):
    """ Calculate if dest_path has room to hold the specified elements.

    Determine whether or not dest_path will exceed the specified usage ratio
    (used:total space) after adding the specified elements.

    Parameters
    ----------
    elements : sqlalchemy.orm.query.Query
        The elements to be added to the destination directory

    src_path : str
        The path in which the elements are currently stored

    dest_path : str
        The path to which the elements would be moved.

    ratio : double
        The allowed ratio of used:total space.

    Returns
    -------
    True if adding "elements" to "dest_path" does not increase the ratio past its
      threshold.  Else false.

    """
    if elements:
        addcount = 0
        size = 0
        for element in elements:
            fname = src_path + element.filename
            size += getsize(fname)

        size_free = disk_usage(dest_path).free
        if size >= (disk_usage_ratio * size_free ):
            return False
    return True


class QueueProcess():
    def __init__(self, process_name, archive, volume=None, search=None, log_level='INFO', namespace=None):
        self.process_name = process_name
        self.archive = archive
        self.logger = self.get_logger(log_level)
        self.archive_info = json.load(open(pds_info, 'r'))
        try:
            self.archive_id = self.get_archive_att('archiveid')
        except KeyError:
            self.logger.error("Archive %s not found in %s", archive, pds_info)
            raise
        self.volume = volume
        self.search = search
        self.namespace = namespace
        self.ready_queue= RedisQueue(f"{process_name}_ReadyQueue", namespace)
        self.error_queue = RedisQueue(f"{process_name}_ErrorQueue", namespace)
        self.logger.info("%s queue: %s", process_name, self.ready_queue.id_name)

        try:
            pds_session_maker, _ = db_connect(pds_db)
            self.logger.info('Database Connection Success')
        except Exception as e:
            self.logger.error('Database Connection Error\n\n%s', e)
            raise

        self.session_maker = pds_session_maker


    def get_logger(self, log_level):
        """ Instantiate and return a logger based on process information.
        Parameters
        ----------
        log_level : str
            The string descriptor of the log level (critical, error, warning, info, debug)

        Returns
        -------
        logger : logging.Logger
            The parameterized logger
        """
        if not hasattr(self, "logger"):
            logger = logging.getLogger(f"{self.process_name}_Queueing.{self.archive}")
            level = logging.getLevelName(log_level)
            logger.setLevel(level)
            logFileHandle = logging.FileHandler(pds_log + 'Process.log')
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s, %(message)s')
            logFileHandle.setFormatter(formatter)
            logger.addHandler(logFileHandle)
            self.logger = logger
        return self.logger


    def get_matching_files(self):
        """ Get the files matching the process characteristics.  Overridden by child classes."""
        raise NotImplementedError()


    def enqueue(self, element):
        """ Add an element to the queue.  Overridden by child classes."""
        raise NotImplementedError()


    def run(self, elements=None, copy=True):
        """ Copies and queues a set of elements into the process's queue(s)

        Parameters
        ----------
        elements : sqlalchemy.orm.query.Query or list
            The elements to be processed

        copy : boolean
            If true, copies files to the work area.  If false, skips copying step.

        Returns
        -------
        None
        """
        source_path = self.get_archive_att('path')
        if copy and not has_space(elements, source_path, workarea, disk_usage_ratio):
            self.logger.error("Unable to copy files: Insufficient disk space in %s.", workarea)
            raise IOError(f"Insufficient disk space in {workarea}.")

        addcount=0
        for element in elements:
            try:
                try:
                    fname = element.filename
                except:
                    fname = element
                fname = join(source_path, fname)
                if copy:
                    fname = copy_files(fname, archive_base, workarea)
                self.enqueue(fname)
                addcount = addcount + 1
            except Exception as e:
                self.error_queue.QueueAdd(f'Unable to copy / queue {fname}: {e}')
                self.logger.error('Unable to copy / queue %s: %s', fname, e)
        self.logger.info('Files Added to %s Queue: %s', self.process_name, addcount)


    def get_archive_att(self, att):
        """ Get the archive id from this process's archive name

        Returns
        -------
        archive_id : int
            The integer value associated with the archive name.

        """
        try:
            archive_att = self.archive_info[self.archive][att]
        except KeyError:
            msg = "\nArchive '{}' not found in {}\n".format(self.archive, pds_info)
            msg += "The following archives are available:\n"
            for k in self.archive_info.keys():
                msg += "\t{}\n".format(k)
            print(msg)
            raise

        return archive_att


class DIQueueProcess(QueueProcess):
    def get_matching_files(self):
        """ Gets the files matching the processing parameters.

        Returns
        -------
        results : sqlalchemy.orm.query.Query
            A collection of files represented as a sqlalchemy query object.
        """
        with session_scope(self.session_maker) as session:
            td = (datetime.datetime.now(pytz.utc) -
                  datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
            testing_date = datetime.datetime.strptime(str(td), "%Y-%m-%d %H:%M:%S")
            if self.volume:
                volstr = '%' + self.volume + '%'
                results = session.query(Files).filter(
                    Files.archiveid == self.archive_id, Files.filename.like(volstr)).filter(
                        or_(cast(Files.di_date, Date) < testing_date,
                            cast(Files.di_date, Date) is None))
            else:
                results = session.query(Files).filter(Files.archiveid == self.archive_id).filter(
                    or_(cast(Files.di_date, Date) < testing_date,
                        cast(Files.di_date, Date) is None))

        return results

    def enqueue(self, element):
        """ Enqueue a single element

        Parameters
        ----------
        element : str
            The filename to be enqueued

        Returns
        -------
        None
        """
        path = self.get_archive_att('path')
        fname = path+element.filename
        self.ready_queue.QueueAdd((element.filename, self.archive))


class UPCQueueProcess(QueueProcess):
    def get_matching_files(self):
        """ Gets the files matching the processing parameters.

        Returns
        -------
        results : sqlalchemy.orm.query.Query
            A collection of files represented as a sqlalchemy query object.
        """
        with session_scope(self.session_maker) as session:
            if self.volume:
                volstr = '%' + self.volume + '%'
                results = session.query(Files).filter(Files.archiveid == self.archive_id,
                                                   Files.filename.like(volstr),
                                                   Files.upc_required == 't')
            else:
                results = session.query(Files).filter(Files.archiveid == self.archive_id,
                                                   Files.upc_required == 't')
            if self.search:
                qf = '%' + self.search + '%'
                results = results.filter(Files.filename.like(qf))

        return results

    def enqueue(self, element):
        """ Enqueue a single element

        Parameters
        ----------
        element : str
            The filename to be enqueued

        Returns
        -------
        None
        """
        self.ready_queue.QueueAdd((element, self.archive))


class IngestQueueProcess(QueueProcess):
    def __init__(self, *args, link_only=False, **kwargs):
        super().__init__(*args, **kwargs)
        # Default to empty string if falsy value specified
        self.search = self.search or ''
        self.link_only = link_only
        self.link_queue = RedisQueue('LinkQueue', self.namespace)


    def get_matching_files(self):
        """ Gets the files matching the processing parameters.

        Returns
        -------
        results : list
            A list of files
        """
        archivepath = self.get_archive_att('path')
        if self.volume:
            archivepath = join(archivepath, self.volume)
        results = []
        for dirpath, _, files in os.walk(archivepath):
            for filename in files:
                fname = join(dirpath, filename)
                if self.search in filename:
                    results.append(join(dirpath, filename))

        return results


    def enqueue(self, element):
        """ Enqueue a single element

        Parameters
        ----------
        element : str
            The filename to be enqueued

        Returns
        -------
        None
        """
        if basename(element.lower()) == "voldesc.cat":
            self.link_queue.QueueAdd(element)
        if not self.link_only:
            self.ready_queue.QueueAdd((element, self.archive))
