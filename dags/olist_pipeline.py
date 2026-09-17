import sys
from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.common.sql.operators.sql import SQLCheckOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.task_group import TaskGroup

SCRIPTS_DIR = "/opt/airflow/scripts"
sys.path.insert(0, SCRIPTS_DIR)

import ingest  # noqa: E402

# Nama file di scripts/checks/ (tanpa .sql).
# Setiap query mengembalikan satu baris boolean. Task gagal kalau ada nilai FALSE atau NULL.
QUALITY_CHECKS = [
    "marts_not_empty",
    "seller_id_unique",
    "seller_revenue_matches_raw",
    "monthly_revenue_matches_raw",
    "no_orders_lost_in_categories",
    "review_score_in_range",
]

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

    with TaskGroup(group_id="quality_checks") as quality_checks:
        for check_name in QUALITY_CHECKS:
            SQLCheckOperator(
                task_id=check_name,
                conn_id="postgres_olist",
                sql=f"checks/{check_name}.sql",
                retries=0,  # hasil check tidak berubah kalau diulang
            )

    ingest_task >> transform_task >> quality_checks