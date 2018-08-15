import datetime
import json
import pytz

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.operators.dummy_operator import DummyOperator

from pds_pipelines.db import db_connect
from pds_pipelines.models.pds_models import Files
from pds_pipelines.RedisQueue import RedisQueue
from pds_pipelines.FindDI_Ready import archive_expired, volume_expired


dag = DAG('di_queueing', description='Enqueues any files that are due for a data integrity check.',
          schedule_interval='0 12 * * *',
          start_date=datetime.datetime.now())

def load_json(ds, **kwargs):
    path = kwargs['path']
    return json.load(open(path, 'r'))

def queue_items(ds, **kwargs):
    ti = kwargs['ti']
    pds_info = ti.xcom_pull(task_ids='load_json')
    session = kwargs['session']
    for target in pds_info:
        archive_id = pds_info[target]['archiveid']
        td = (datetime.datetime.now(pytz.utc) - datetime.timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
        testing_date = datetime.datetime.strptime(str(td), "%Y-%m-%d %H:%M:%S")
        expired = archive_expired(session, archive_id, testing_date)
        if expired.count():
            for f in expired:
                rq.QueueAdd(f.filename)
    return 0

session, _ = db_connect('pdsdi_dev')
rq = RedisQueue('DI_ReadyQueue')


dummy_operator = DummyOperator(task_id='dummy_task', retries=3, dag=dag)

load_json_operator = PythonOperator(task_id='load_json',
        provide_context=True,
        python_callable=load_json,
        op_kwargs={'path':'/app/pds_pipelines/PDSinfo.json'},
        dag=dag)

queue_items_operator = PythonOperator(task_id='queue_items',
        provide_context=True,
        python_callable=queue_items,
        op_kwargs={'session':session, 'rq':rq},
        dag=dag)

load_json_operator.set_upstream(dummy_operator)
queue_items_operator.set_upstream(load_json_operator)
