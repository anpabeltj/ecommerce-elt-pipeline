import logging
import os

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Kolom tanggal per file, supaya masuk Postgres sebagai TIMESTAMP bukan TEXT
DATE_COLUMNS = {
    "olist_orders_dataset": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "olist_order_items_dataset": ["shipping_limit_date"],
    "olist_order_reviews_dataset": ["review_creation_date", "review_answer_timestamp"],
}


def get_db_engine():
    # Di Docker, env var sudah diisi oleh docker-compose.
    # Saat dijalankan lokal, nilai diambil dari file .env.
    load_dotenv()
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME"),
    )
    return create_engine(url)


def load_csv_to_postgres(file_path, engine):
    table_name = os.path.splitext(os.path.basename(file_path))[0]
    date_cols = DATE_COLUMNS.get(table_name, [])

    df = pd.read_csv(file_path, parse_dates=date_cols)
    df.to_sql(
        table_name,
        engine,
        if_exists="replace",
        index=False,
        chunksize=1000,
        method="multi",
    )
    logger.info("Loaded %s rows into %s", len(df), table_name)


def ingest_all():
    data_dir = os.getenv("DATA_DIR", "/opt/airflow/data")
    engine = get_db_engine()

    csv_files = sorted(f for f in os.listdir(data_dir) if f.endswith(".csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {data_dir}")

    for file_name in csv_files:
        load_csv_to_postgres(os.path.join(data_dir, file_name), engine)


if __name__ == "__main__":
    ingest_all()