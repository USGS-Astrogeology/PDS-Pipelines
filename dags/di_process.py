import datetime
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.subdag_operator import SubDagOperator
from airflow.operators.dagrun_operator import TriggerDagRunOperator

from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files
from pds_pipelines.RedisQueue import RedisQueue

import hashlib
import shutil
import os
import pytz


# @TODO this is terrible and should be refactored.
archiveID = {53: '/pds_san/PDS_Archive/Cassini/ISS/',
                51: '/pds_san/PDS_Archive/Cassini/RADAR/',
                75: '/pds_san/PDS_Archive/Cassini/VIMS/',
                97: '/pds_san/PDS_Archive/Apollo/Metric_Camera/',
                101: '/pds_san/PDS_Archive/Apollo/Rock_Sample_Images/',
                50: '/pds_san/PDS_Archive/Clementine/',
                104: '/pds_san/PDS_Archive/Chandrayaan_1/M3/',
                119: '/pds_san/PDS_Archive/Dawn/Vesta/',
                123: '/psa_san/PDS_Archive/Dawn/Ceres/',
                24: '/pds_san/PDS_Archive/Galileo/NIMS/',
                25: '/pds_san/PDS_Archive/Galileo/SSI/',
                92: '/pds_san/PDS_Safed/Data/Kaguya/LISM/',
                38: '/pds_san/PDS_Archive/LCROSS/',
                79: '/pds_san/PDS_Archive/Lunar_Orbiter/',
                116: '/pds_san/PDS_Archive/Mars_Odyssey/THEMIS/USA_NASA_PDS_ODTSDP_100XX/',
                117: '/pds_san/PDS_Archive/Mars_Odyssey/THEMIS/USA_NASA_PDS_ODTSDP_100XX/',
                118: '/pds_san/PDS_Archive/Mars_Odyssey/THEMIS/USA_NASA_PDS_ODTGEO_200XX/',
                41: '/pds_san/PDS_Derived/Map_A_Planet/',
                44: '/pds_san/PDS_Archive/Mars_Global_Surveyor/MOC/',
                16: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/CTX/',
                17: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/MARCI/',
                74: '/pds_san/PDS_Archive/Lunar_Reconnaissance_Orbiter/LROC/EDR/',
                84: '/pds_san/PDS_Archive/Lunar_Reconnaissance_Orbiter/LAMP/',
                71: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/HiRISE/',
                124: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/HiRISE/',
                125: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/HiRISE/',
                126: '/pds_san/PDS_Archive/Mars_Reconnaissance_Orbiter/HiRISE/',
                46: '/pds_san/PDS_Archive/Mariner_10/',
                27: '/pds_san/PDS_Archive/Magellan/',
                78: '/pds_san/PDS_Archive/Mars_Express/',
                18: '/pds_san/PDS_Archive/Mars_Pathfinder/',
                14: '/pds_san/PDS_Archive/MESSENGER/',
                9: '/pds_san/PDS_Archive/Phoenix/',
                7: '/pds_san/PDS_Archive/Viking_Lander/',
                3: '/pds_san/PDS_Archive/Viking_Orbiter/',
                30: '/pds_san/PDS_Archive/Voyager/'
                }


dag = DAG('di_process', description='Data integrity check for PDS products',
          schedule_interval='0 12 * * *',
          start_date=datetime.datetime.now())


def get_items(ds, **kwargs):
    outlist = list()
    n_items = kwargs.get('n_items')
    rq = kwargs.get('rq')
    while (rq.QueueSize() > 0 and n_items > 0):
        inputfile = rq.QueueGet().decode('utf-8')
        outlist.append(inputfile)
        n_items -= 1
    return outlist


def file_lookup(ds, **kwargs):
    ti = kwargs['ti']
    upstream_tid = kwargs['task'].upstream_task_ids[0]
    in_list = ti.xcom_pull(upstream_tid)
    if in_list is None : return
    session = kwargs['session']
    out = list()
    for item in in_list:
        Qelement = session.query(Files).filter(Files.filename == item).one()
        out.append(Qelement)
    return out


def hash_file(ds, **kwargs):
    ti = kwargs['ti']
    upstream_tid = kwargs['task'].upstream_task_ids[0]
    archiveID = kwargs['archiveID']
    in_list = ti.xcom_pull(upstream_tid)
    if in_list is None : return
    out = list()
    for item in in_list:
        cpfile = archiveID[item.archiveid] + item.filename
        if os.path.isfile(cpfile):
            f_hash = hashlib.md5()
            with open(cpfile, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    f_hash.update(chunk)
                out.append((item,f_hash.hexdigest()))
        else:
            print('Unable to locate {}'.format(cpfile))
            out.append((item,0))
    return out

def cmp_checksum(ds, **kwargs):
    ti = kwargs['ti']
    upstream_tid = kwargs['task'].upstream_task_ids[0]
    in_list = ti.xcom_pull(upstream_tid)
    if in_list is None : return
    session = kwargs['session']
    for old, new in in_list:
        if old.checksum == new:
            old.di_pass = True
        else:
            old.di_pass = False
        old.di_date = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
        session.merge(old)
    session.flush()
    session.commit()


def process_subdag(parent_dag_name, child_dag_name, **kwargs):
    schedule_interval = '@once'
    session = kwargs['session']
    archiveID = kwargs['archiveID']
    n_procs = int(kwargs['n_procs'])
    rq =  kwargs['rq']
    start_date = datetime.datetime.now()
    dag = DAG(
            '%s.%s' % (parent_dag_name, child_dag_name),
            schedule_interval=schedule_interval,
            start_date = start_date,
            )
    for i in range(n_procs):
        get_items_operator = PythonOperator(task_id='get_items_{}'.format(i),
                provide_context=True,
                python_callable=get_items,
                op_kwargs={'n_items':50, 'rq':rq},
                dag=dag)
        file_lookup_operator = PythonOperator(task_id='file_lookup_{}'.format(i),
                provide_context=True,
                python_callable=file_lookup,
                op_kwargs={'session':session},
                dag=dag)
        hash_file_operator = PythonOperator(task_id='hash_file_{}'.format(i),
                provide_context=True,
                python_callable=hash_file,
                op_kwargs={'session':session, 'archiveID':archiveID},
                dag=dag)

        cmp_checksum_operator = PythonOperator(task_id='cmp_checksum_{}'.format(i),
                provide_context=True,
                python_callable=cmp_checksum,
                op_kwargs={'session':session},
                dag=dag)

        get_items_operator >> file_lookup_operator >> hash_file_operator >> cmp_checksum_operator
    return dag

def repeat_dag(context, dag_run_obj):
    rq = context['params']['rq']
    if rq.QueueSize() > 0:
        return dag_run_obj



# @TODO find a way to make these separate tasks.  Difficult because they
#  can't be pickled, therefore they can't be returned via a task.
session, _ = db_connect('pdsdi_dev')
rq = RedisQueue('DI_ReadyQueue')




process_operator = SubDagOperator(
        subdag = process_subdag('di_process',
            'di_checksum',
            session=session,
            archiveID=archiveID,
            n_procs=5,
            rq=rq),
        task_id='di_checksum',
        dag=dag)


loop_operator = TriggerDagRunOperator(task_id='loop',
        provide_context=True,
        params={'rq':rq},
        trigger_dag_id='di_process',
        python_callable=repeat_dag,
        dag=dag)


process_operator >> loop_operator
