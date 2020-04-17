from datetime import datetime
import json
from pvl import PVLModule

import pytest
import sqlalchemy
from shapely.geometry import Polygon
from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import from_shape, to_shape
import numpy as np
from unittest.mock import patch, PropertyMock, Mock
from unittest import mock

import pysis
from pysis import isis

# Stub in the getsn function for testing
def getsn(from_):
    return b'ISISSERIAL'
pysis.isis.getsn = getsn

# Stub in the getsn function for testing
def spiceinit(from_):
    raise ProcessError(1, ['spiceinit'], '', '')
pysis.isis.spiceinit = spiceinit

import pds_pipelines
from pds_pipelines.process import Process
from pds_pipelines.db import db_connect
from pds_pipelines import upc_process
from pds_pipelines.upc_process import *

from pds_pipelines.upc_process import create_datafiles_record, create_search_terms_record, create_json_keywords_record, get_target_id, getISISid, process, generate_processes
from pds_pipelines.models import upc_models as models

@pytest.fixture
def tables():
    _, engine = db_connect('upc_test')
    return engine.table_names()

@pytest.fixture
def session(tables, request):
    Session, _ = db_connect('upc_test')
    session = Session()

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

@pytest.fixture
def pds_label():
    return PVLModule({'^IMAGE': ('5600R.IMG', 12),
                      'SPACECRAFT_NAME': 'TEST CRAFT',
                      'INSTRUMENT_NAME': 'TEST INSTRUMENT',
                      'TARGET_NAME': 'TEST TARGET'})

cam_info_dict = {'upcid': 1,
                 'processdate': datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M"),
                 'starttime': '2019-12-18 21:36',
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

@pytest.mark.parametrize('get_key_return', [('PRODUCTID'), (b'PRODUCTID')])
@patch('pds_pipelines.upc_keywords.UPCkeywords.__init__', return_value = None)
def test_get_pds_id(mocked_init, get_key_return, pds_label):
    with patch('pds_pipelines.upc_keywords.UPCkeywords.getKeyword', return_value=get_key_return) as mocked_getkey:
        prod_id = getPDSid(pds_label)
    assert isinstance(prod_id, str)
    assert prod_id == 'PRODUCTID'

def test_get_isis_id():
    cube_path = '/Path/to/my/cube.cub'
    serial = getISISid(cube_path)
    assert serial == 'ISISSERIAL'
    assert isinstance(serial, str)

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

def test_target_insert(session, session_maker, pds_label):
    target_id = get_target_id(pds_label, session_maker)
    resp = session.query(models.Targets).filter(models.Targets.targetid==target_id).one()
    target_name = resp.targetname
    assert pds_label['TARGET_NAME'] == target_name

def test_bad_target_insert(session, session_maker):
    target_id = get_target_id(PVLModule(), session_maker)
    assert target_id == None
    with pytest.raises(sqlalchemy.orm.exc.NoResultFound):
        session.query(models.Targets).filter(models.Targets.targetid==target_id).one()

def test_instrument_insert(session, session_maker, pds_label):
    instrument_id = get_instrument_id(pds_label, session_maker)
    resp = session.query(models.Instruments).filter(models.Instruments.instrumentid == instrument_id).one()
    instrument_name = resp.instrument
    assert pds_label['INSTRUMENT_NAME'] == instrument_name

def test_bad_instrumentname_instrument_insert(session, session_maker):
    instrument_id = get_instrument_id(PVLModule(), session_maker)
    assert instrument_id == None
    with pytest.raises(sqlalchemy.orm.exc.NoResultFound):
        session.query(models.Instruments).filter(models.Instruments.instrumentid == instrument_id).one()

def test_bad_spacecraftname_instrument_insert(session, session_maker):
    instrument_id = get_instrument_id(PVLModule({'INSTRUMENT_NAME': 'TEST INSTRUMENT'}), session_maker)
    assert instrument_id == None
    with pytest.raises(sqlalchemy.orm.exc.NoResultFound):
        session.query(models.Instruments).filter(models.Instruments.instrumentid == instrument_id).one()

@patch('pds_pipelines.upc_process.getISISid', return_value = 'ISISSERIAL')
@patch('pds_pipelines.upc_process.getPDSid', return_value = 'PRODUCTID')
def test_datafiles_insert(mocked_pds_id, mocked_isis_id, session, session_maker, pds_label):
    pds_label = PVLModule({'^IMAGE': ('5600R.IMG', 12),
                           'SPACECRAFT_NAME': 'TEST CRAFT',
                           'INSTRUMENT_NAME': 'TEST INSTRUMENT',
                           'TARGET_NAME': 'TEST TARGET'})
    input_cube = '/Path/to/my/cube.cub'
    upc_id = create_datafiles_record(pds_label, '/Path/to/label/location/label.lbl', '/Path/to/my/cube.cub', session_maker)
    mocked_isis_id.assert_called_with(input_cube)
    mocked_pds_id.assert_called_with(input_cube)

    resp = session.query(models.DataFiles).filter(models.DataFiles.isisid=='ISISSERIAL').first()
    assert upc_id == resp.upcid

@patch('pds_pipelines.upc_process.getISISid', return_value = 'ISISSERIAL')
@patch('pds_pipelines.upc_process.getPDSid', return_value = 'PRODUCTID')
def test_datafiles_no_label(mocked_pds_id, mocked_isis_id, session, session_maker, pds_label):
    pds_label['^IMAGE'] = 1
    upc_id = create_datafiles_record(pds_label, '/Path/to/label/location/label.lbl', '/Path/to/my/cube.cub', session_maker)
    resp = session.query(models.DataFiles).filter(models.DataFiles.upcid==upc_id).first()
    assert resp.detached_label == None
    assert resp.source == '/Path/to/label/location/label.lbl'

@patch('pds_pipelines.upc_process.getPDSid', return_value = 'PRODUCTID')
def test_datafiles_no_isisid(mocked_pds_id, session, session_maker, pds_label):
    # Since we mock getsn above, make it throw an exception here so we can test
    # when there is no ISIS ID.
    with patch('pysis.isis.getsn', side_effect=Exception('AttributeError')):
        upc_id = create_datafiles_record(pds_label, '/Path/to/label/location/label.lbl', '/Path/to/my/cube.cub', session_maker)
    resp = session.query(models.DataFiles).filter(models.DataFiles.upcid==upc_id).first()
    assert resp.isisid == None

@patch('pds_pipelines.upc_process.getISISid', return_value = 'ISISSERIAL')
def test_datafiles_no_pdsid(mocked_isis_id, session, session_maker, pds_label):
    upc_id = create_datafiles_record(pds_label, '/Path/to/label/location/label.lbl', '/Path/to/my/cube.cub', session_maker)
    resp = session.query(models.DataFiles).filter(models.DataFiles.upcid==upc_id).first()
    assert resp.productid == None

def extract_keyword(key):
    if key == 'GisFootprint':
        return Polygon([(153.80256122853893, -32.68515128444211), (153.80256122853893, -33.18515128444211), (153.30256122853893, -33.18515128444211), (153.30256122853893, -32.68515128444211), (153.80256122853893, -32.68515128444211)]).wkt
    return cam_info_dict[key]
@patch('pds_pipelines.upc_keywords.UPCkeywords.__init__', return_value = None)
@patch('pds_pipelines.upc_keywords.UPCkeywords.getKeyword', side_effect = extract_keyword)
@patch('pds_pipelines.upc_process.getPDSid', return_value = 'PRODUCTID')
def test_search_terms_insert(mocked_product_id, mocked_keyword, mocked_init, session, session_maker, pds_label):
    upc_id = cam_info_dict['upcid']

    models.DataFiles.create(session, upcid = upc_id)

    create_search_terms_record(pds_label, '/Path/to/caminfo.pvl', upc_id, '/Path/to/my/cube.cub', session_maker)
    resp = session.query(SearchTerms).filter(SearchTerms.upcid == upc_id).first()

    for key in cam_info_dict.keys():
        resp_attribute = resp.__getattribute__(key)
        if isinstance(resp_attribute, datetime.date):
            resp_attribute = resp_attribute.strftime("%Y-%m-%d %H:%M")
        if isinstance(resp_attribute, WKBElement):
            resp_attribute = str(to_shape(resp_attribute))
        if isinstance(resp_attribute, float):
            np.testing.assert_almost_equal(resp_attribute, cam_info_dict[key], 12)
            continue
        assert cam_info_dict[key] == resp_attribute

@patch('pds_pipelines.upc_process.getPDSid', return_value = 'PRODUCTID')
def test_search_terms_keyword_exception(mocked_product_id, session, session_maker, pds_label):
    upc_id = cam_info_dict['upcid']
    models.DataFiles.create(session, upcid = upc_id)

    create_search_terms_record(pds_label, "", upc_id, '/Path/to/my/cube.cub', session_maker)
    resp = session.query(SearchTerms).filter(SearchTerms.upcid == upc_id).first()
    assert resp.starttime == None
    assert resp.solarlongitude == None
    assert resp.meangroundresolution == None
    assert resp.minimumemission == None
    assert resp.maximumemission == None
    assert resp.emissionangle == None
    assert resp.minimumincidence == None
    assert resp.maximumincidence == None
    assert resp.incidenceangle == None
    assert resp.minimumphase == None
    assert resp.maximumphase == None
    assert resp.phaseangle == None
    assert resp.isisfootprint == None
    assert resp.err_flag == True

@patch('pds_pipelines.upc_keywords.UPCkeywords.__init__', return_value = None)
@patch('pds_pipelines.upc_keywords.UPCkeywords.getKeyword', side_effect = extract_keyword)
@patch('pds_pipelines.upc_process.getPDSid', return_value = 'PRODUCTID')
def test_search_terms_no_datafile(mocked_product_id, mocked_keyword, mocked_init, session, session_maker, pds_label):
    upc_id = cam_info_dict['upcid']

    with pytest.raises(sqlalchemy.exc.IntegrityError):
        create_search_terms_record(pds_label, '/Path/to/caminfo.pvl', upc_id, '/Path/to/my/cube.cub', session_maker)

@patch('pds_pipelines.upc_keywords.UPCkeywords.__init__', return_value = None)
def test_json_keywords_insert(mocked_init, session, session_maker, pds_label):
    logger = logging.getLogger('UPC_Process')
    upc_id = cam_info_dict['upcid']

    models.DataFiles.create(session, upcid = upc_id)

    with patch('pds_pipelines.upc_keywords.UPCkeywords.label', new_callable=PropertyMock) as mocked_label:
        mocked_label.return_value = pds_label
        create_json_keywords_record(pds_label, upc_id, '/Path/to/my/cube.cub', 'No Failures', session_maker, logger)

    resp = session.query(JsonKeywords).filter(JsonKeywords.upcid == upc_id).first()
    resp_json = resp.jsonkeywords
    assert resp_json['^IMAGE'][0] == pds_label['^IMAGE'][0]
    assert resp_json['TARGET_NAME'] == pds_label['TARGET_NAME']
    assert resp_json['INSTRUMENT_NAME'] == pds_label['INSTRUMENT_NAME']
    assert resp_json['SPACECRAFT_NAME'] == pds_label['SPACECRAFT_NAME']

def test_json_keywords_exception(session, session_maker):
    logger = logging.getLogger('UPC_Process')
    upc_id = cam_info_dict['upcid']
    models.DataFiles.create(session, upcid = upc_id)

    input_cube = '/Path/to/my/cube.cub'
    error_message = 'Got to exception.'
    create_json_keywords_record("", upc_id, input_cube, error_message, session_maker, logger)
    resp = session.query(JsonKeywords).filter(JsonKeywords.upcid == upc_id).first()
    resp_json = resp.jsonkeywords
    assert resp_json['errortype'] == error_message
    assert resp_json['file'] == input_cube
    assert resp_json['errormessage'] == f'Error running {error_message} on file {input_cube}'
    assert resp_json['error'] == True

@patch('pds_pipelines.upc_keywords.UPCkeywords.__init__', return_value = None)
def test_json_keywords_no_datafile(mocked_init, session, session_maker, pds_label):
    logger = logging.getLogger('UPC_Process')
    upc_id = cam_info_dict['upcid']

    with pytest.raises(sqlalchemy.exc.IntegrityError),\
    patch('pds_pipelines.upc_keywords.UPCkeywords.label', new_callable=PropertyMock) as mocked_label:
        mocked_label.return_value = pds_label
        create_json_keywords_record(pds_label, upc_id, '/Path/to/my/cube.cub', 'No Failures', session_maker, logger)

def test_generate_processes():
    logger = logging.getLogger('UPC_Process')

    inputfile = "./pds_pipelines/tests/data/5600r.lbl"
    fid = "1"
    archive = "galileo_ssi_edr"

    processes, inputfile, caminfoOUT, pwd = generate_processes(inputfile, archive, logger)

    recipe_file = recipe_base + "/" + archive + '.json'
    with open(recipe_file) as fp:
        original_recipe = json.load(fp)['upc']['recipe']

    for k, v in processes.items():
        assert original_recipe[k].keys() == v.keys()

def test_process_isis():
    logger = logging.getLogger('UPC_Process')

    processes = {'isis.getsn': {'from_': '/Path/to/some/cube.cub'}}

    failing_command = process(processes, '/', logger)
    assert failing_command == ''

def test_bad_process_isis():
    logger = logging.getLogger('UPC_Process')

    processes = {'isis.spiceinit': {'from_': '/Path/to/some/cube.cub'}}

    failing_command = process(processes, '/', logger)
    assert failing_command == 'spiceinit'
