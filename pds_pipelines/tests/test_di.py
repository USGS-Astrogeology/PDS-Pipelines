import pytest
import sqlalchemy
from shapely.geometry import Polygon
from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import from_shape, to_shape
from unittest.mock import patch, PropertyMock
from unittest import mock

from pds_pipelines.db import db_connect
from pds_pipelines.models import pds_models as models

models.create_pds_database()

@pytest.fixture
def tables():
    _, engine = db_connect('di_test')
    return engine.table_names()

@pytest.fixture
def session(tables, request):
    Session, _ = db_connect('di_test')
    session = Session()

    def cleanup():
        session.rollback()  # Necessary because some tests intentionally fail
        for t in reversed(tables):
            # Skip the srid table
            if t != 'spatial_ref_sys':
                session.execute(f'TRUNCATE TABLE {t} CASCADE')
            # Reset the autoincrementing
            if t in ['process_runs', 'files', 'archives']:
                if t == 'process_runs':
                    column = f'{t}_processid_seq'
                if t == 'files':
                    column = f'{t}_fileid_seq'
                if t == 'archives':
                    column = f'{t}_archiveid_seq'

                session.execute(f'ALTER SEQUENCE {column} RESTART WITH 1')
        session.commit()

    request.addfinalizer(cleanup)

    return session

@pytest.fixture
def session_maker(tables, request):
    Session, _ = db_connect('di_test')
    return Session

@pytest.fixture
def process_run_attributes():
    process_run_attributes = {'processid': 1,
                              'fileid': 1,
                              'process_date': '2019-01-01 12:00:00',
                              'process_typeid': 1,
                              'process_out': True}
    return process_run_attributes

@pytest.fixture
def file_attributes():
    file_attributes = {'fileid': 1,
                       'archiveid': 1,
                       'filename': '/Path/to/my/file.img',
                       'entry_date': '2019-01-01 12:00:00',
                       'checksum': 'aaaaa',
                       'upc_required': False,
                       'validation_required': False,
                       'header_only': True,
                       'release_date': '2019-01-01 12:00:00',
                       'file_url': 'https://SomeURL/to/this/file.img',
                       'isis_errors': False,
                       'di_pass': True,
                       'di_date': '2019-01-01 12:00:00'}
    return file_attributes

@pytest.fixture
def archive_attributes():
    archive_attributes = {'archive_name': 'go_0017',
                          'missionid': 1,
                          'pds_archive': True,
                          'primary_node': 'USGS'}
    return archive_attributes

def test_datafiles_exists(tables):
    assert models.ProcessRuns.__tablename__ in tables

def test_instruments_exists(tables):
    assert models.Files.__tablename__ in tables

def test_targets_exists(tables):
    assert models.Archives.__tablename__ in tables

def test_archive_insert(session, archive_attributes):
    models.Archives.create(session, **archive_attributes)

def test_files_insert_with_archive(session, archive_attributes, file_attributes):
    models.Archives.create(session, **archive_attributes)
    models.Files.create(session, **file_attributes)

def test_files_insert_without_archive(session, file_attributes):
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        models.Files.create(session, **file_attributes)

def test_process_run_insert_without_file(session, process_run_attributes):
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        models.ProcessRuns.create(session, **process_run_attributes)

def test_process_run_insert_with_file(session, archive_attributes, file_attributes, process_run_attributes):
    models.Archives.create(session, **archive_attributes)
    models.Files.create(session, **file_attributes)
    models.ProcessRuns.create(session, **process_run_attributes)
