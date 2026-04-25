import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv


def get_db_engine():
    load_dotenv('/opt/airflow/.env')
    # load_dotenv()
    user = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    host = os.getenv("DB_HOST")
    port = os.getenv("DB_PORT")
    db = os.getenv("DB_NAME")
    engine = create_engine(
        f"postgresql://{user}:{password}@{host}:{port}/{db}"
    )
    return engine


def load_csv_to_postgres(file_path, engine):
    df = pd.read_csv(file_path)
    file_name = os.path.basename(file_path).replace(".csv", "")
    df.to_sql(file_name, engine, if_exists='replace', index=False, chunksize=1000)
    print(f"Loaded {file_name} into PostgreSQL")

def ingest_all():
    data_dir = '/opt/airflow/data'
    # data_dir = '/Users/anpabelt/Downloads/ecommerce-elt-pipeline/data'
    engine = get_db_engine()
    list_file = os.listdir(data_dir)
    for file in list_file:
        if file.endswith('.csv'):
            file_path = os.path.join(data_dir, file)
            load_csv_to_postgres(file_path, engine)
if __name__ == "__main__":
    ingest_all()