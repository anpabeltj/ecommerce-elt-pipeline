from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import sys
sys.path.insert(0, '/opt/airflow/scripts')
import ingest as i
from airflow.providers.postgres.operators.postgres import PostgresOperator



default_args = {
    'owner': 'airflow',
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
}

with open('/opt/airflow/scripts/transform.sql', 'r') as f:
        sql_query = f.read()
with DAG('olist_elt_pipeline', default_args=default_args, schedule='@daily', catchup=False) as dag:
    ingest_task = PythonOperator(
        task_id = 'ingest_olist',
        python_callable = i.ingest_all
    )
    transform_task = PostgresOperator(
        task_id = 'transform_olist',
        postgres_conn_id = 'postgres_olist',
        sql = sql_query
    )


    ingest_task >> transform_task