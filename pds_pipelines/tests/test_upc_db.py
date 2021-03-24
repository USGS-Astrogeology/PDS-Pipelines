from datetime import datetime
import pytz
from pvl import PVLModule
import logging

import pytest
import sqlalchemy
from shapely.geometry import Polygon

from pds_pipelines.db import db_connect
from pds_pipelines.models import upc_models as models

from unittest.mock import patch, PropertyMock, Mock
from unittest import mock

models.create_upc_database()

@pytest.fixture
def pds_label():
    return PVLModule({'^IMAGE': ('5600R.IMG', 12),
                      'SPACECRAFT_NAME': 'TEST CRAFT',
                      'INSTRUMENT_NAME': 'TEST INSTRUMENT',
                      'TARGET_NAME': 'TEST TARGET'})

cam_info_dict = {'upcid': 1,
                 'processdate': datetime.now(pytz.utc).strftime("%Y-%m-%d %H"),
                 'starttime': '2019-12-18 21',
                 'solarlongitude': 66.210772203754,
                 'meangroundresolution': 4.409120557106079,
                 'minimumemission': 4.541800232653493,
                 'maximumemission': 8.541800232653493,
                 'emissionangle': 6.541800232653493,
                 'minimumincidence': 61.821788119170066,
                 'maximumincidence': 65.82178811917007,
                 'incidenceangle': 63.821788119170066,
                 'minimumphase': 76.58058078942486,
                 'maximumphase': 80.58058078942486,
                 'phaseangle': 78.58058078942486,
                 'targetid': 1,
                 'instrumentid': 1,
                 'pdsproductid': 'PRODUCTID',
                 'err_flag': False,
                 'isisfootprint': Polygon([(153.80256122853893, -32.68515128444211),
                                           (153.80256122853893, -33.18515128444211),
                                           (153.30256122853893, -33.18515128444211),
                                           (153.30256122853893, -32.68515128444211),
                                           (153.80256122853893, -32.68515128444211)]).wkt}

@pytest.fixture
def tables():
    _, engine = db_connect('upc_test')
    return engine.table_names()

@pytest.fixture
def session(tables, request):
    Session, _ = db_connect('upc_test')
    session = Session()

    models.Targets.create(session, targetname='FAKE_TARGET', system='FAKE_SYSTEM')
    models.Instruments.create(session, instrument='FAKE_CAMERA', spacecraft='FAKE_CRAFT')
    models.DataFiles.create(session, instrumentid=1, targetid=1, source='/Path/to/pds/file.img')
    models.SearchTerms.create(session, upcid=1, instrumentid=1, targetid=1)
    models.JsonKeywords.create(session, upcid=1)

    session.commit()
    session.flush()

    def cleanup():
        session.rollback()  # Necessary because some tests intentionally fail
        for t in reversed(tables):
            # Skip the srid table
            if t != 'spatial_ref_sys':
                session.execute(f'TRUNCATE TABLE {t} CASCADE')
            # Reset the autoincrementing
            if t in ['datafiles', 'instruments', 'targets']:
                if t == 'datafiles':
                    column = f'{t}_upcid_seq'
                if t == 'instruments':
                    column = f'{t}_instrumentid_seq'
                if t == 'targets':
                    column = f'{t}_targetid_seq'

                session.execute(f'ALTER SEQUENCE {column} RESTART WITH 1')
        session.commit()

    request.addfinalizer(cleanup)

    return session

@pytest.fixture
def session_maker(tables, request):
    Session, _ = db_connect('upc_test')
    return Session

def test_datafiles_exists(tables):
    assert models.DataFiles.__tablename__ in tables

def test_instruments_exists(tables):
    assert models.Instruments.__tablename__ in tables

def test_targets_exists(tables):
    assert models.Targets.__tablename__ in tables

def test_search_terms_exists(tables):
    assert models.SearchTerms.__tablename__ in tables

def test_json_keywords_exists(tables):
    assert models.JsonKeywords.__tablename__ in tables

@pytest.mark.parametrize("target_name, display_name, system",
                        [('EXAMPLE_TARGET','DISPLAY_NAME', 'SYSTEM'),
                         pytest.param('TARGET', None, None, marks=pytest.mark.xfail),])
def test_target_insert(session, system, display_name, target_name):
    models.Targets.create(session, targetname=target_name,
                                   displayname=display_name,
                                   system=system)
    obj = session.query(models.Targets).filter(models.Targets.targetname==target_name).first()
    assert obj.targetid == 2

def test_target_double_insert(session):
    target_name = "EXAMPLE_TARGET"
    obj = models.Targets.create(session, targetname=target_name,
                                   displayname=target_name.title(),
                                   system=target_name)

    obj = models.Targets.create(session, targetname=obj.targetname,
                                         displayname=obj.displayname,
                                         system=obj.system)
    assert obj.targetid == 2

@pytest.mark.parametrize("instrument_name, spacecraft_name",
                        [('SOME_INSTRUMENT','SOME_SPACECRAFT'),
                         pytest.param(None, None, marks=pytest.mark.xfail),])
def test_instrument_insert(session, spacecraft_name, instrument_name):
    models.Instruments.create(session, instrument=instrument_name,
                                       spacecraft=spacecraft_name)
    obj = session.query(models.Instruments).filter(models.Instruments.instrument==instrument_name).first()
    assert obj.instrumentid == 2

def test_instrument_double_insert(session):
    instrument_name = "SOME_INSTRUMENT"
    spacecraft_name = "SOME_SPACECRAFT"
    obj = models.Instruments.create(session, instrument=instrument_name,
                                             spacecraft=spacecraft_name)
    obj = models.Instruments.create(session, instrument=obj.instrument,
                                             spacecraft=obj.spacecraft)
    assert obj.instrumentid == 2

def test_datafiles_insert(session):
    datafile_attributes = {'upcid':None, 'source': '/Path/to/the/file.img'}
    datafile_qobj = models.DataFiles.create(session, **datafile_attributes)

    assert datafile_qobj.upcid == 2

def test_search_terms_insert(session):
    datafile_attributes = {'upcid': None, 'source': '/Path/to/the/file.img'}
    datafile_qobj = models.DataFiles.create(session, **datafile_attributes)

    search_term_attributes = {'upcid': 2}
    search_terms_qobj = models.SearchTerms.create(session, **search_term_attributes)

    assert search_terms_qobj.upcid == 2

def test_search_terms_no_datafile(session):
    search_term_attributes = {'upcid': 2}
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        search_terms_qobj = models.SearchTerms.create(session, **search_term_attributes)

def test_json_keywords_insert(session):
    datafile_attributes = {'upcid': None, 'source': '/Path/to/the/file.img'}
    datafile_qobj = models.DataFiles.create(session, **datafile_attributes)

    json_keywords_attributes = {'upcid': 2}
    search_terms_qobj = models.JsonKeywords.create(session, **json_keywords_attributes)

    assert search_terms_qobj.upcid == 2

def test_json_keywords_no_datafile(session):
    json_keywords_attributes = {'upcid': 2}
    with pytest.raises(sqlalchemy.exc.IntegrityError):
        search_terms_qobj = models.JsonKeywords.create(session, **json_keywords_attributes)
