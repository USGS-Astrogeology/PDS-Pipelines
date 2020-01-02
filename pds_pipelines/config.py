import os
from pathlib import Path
# Database credentials
credentials = {'upc_test': {'user': 'postgres',
                        'pass': '',
                        'host': 'localhost',
                        'port': '5432',
                        'db': 'upc_test'},
               'di_test': {'user': 'postgres',
                            'pass': '',
                            'host': 'localhost',
                            'port': '5432',
                            'db': 'di_test'}
               }

# Redis path(?) info
redis_info = {'host': 'localhost', 'port': '6379', 'db': '0'}

# POW / MAP2 base path
pow_map2_base = '/pds_san/PDS_Services/'

web_base = 'https://pdsimage.wr.usgs.gov/Missions/'
archive_base = '/pds_san/PDS_Archive/'
link_dest = '/pds_san/PDS_Archive_Links/'

# Recipe base path
# Uses the root of the project to set the base path for all necessary files
root = Path(__file__).parent.parent
recipe_base = os.path.join(root, 'recipe/new/')

pds_info = os.path.join(root, 'pds_pipelines/PDSinfo.json')

pds_log = '/home/acpaquette/repos/PDS-Pipelines/logs/'

slurm_log = '/home/acpaquette/repos/PDS-Pipelines/output/'

cmd_dir = os.path.join(root, 'pds_pipelines/')

keyword_def = os.path.join(root, 'recipe/Keyword_Definition.json')

# workarea = '/home/acpaquette/repos/PDS-Pipelines/products/'
workarea = '/home/acpaquette/repos/PDS-Pipelines/workarea/'
default_namespace = 'adampaquette_queue'

pds_db = 'di_test'
upc_db = 'upc_test'

scratch = '/scratch/pds_services/'

lock_obj = 'processes'

upc_error_queue = 'UPC_ErrorQueue'

disk_usage_ratio = 0.4

# Path where the JSON summary views are written to
summaries_path = '/home/kdlee/builds/PDS-Pipelines/json'
