import sys
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

SCRIPTS_DIR = "/opt/airflow/scripts"
sys.path.insert(0, SCRIPTS_DIR)

import ingest  

default_args = {
    "owner": "airflow",
    "retries": 1,
}

with DAG(
    dag_id="olist_elt_pipeline",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule=None,  # data CSV statis, jalankan manual
    catchup=False,
    template_searchpath=[SCRIPTS_DIR],
    tags=["olist", "elt"],
) as dag:
    ingest_task = PythonOperator(
        task_id="ingest_olist",
        python_callable=ingest.ingest_all,
    )

    transform_task = PostgresOperator(
        task_id="transform_olist",
        postgres_conn_id="postgres_olist",
        sql="transform.sql",
    )

    ingest_task >> transform_task