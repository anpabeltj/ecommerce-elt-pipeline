# 🛒 Olist E-Commerce ELT Pipeline

An end-to-end **ELT (Extract, Load, Transform)** pipeline built on top of the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Raw CSV files are ingested into PostgreSQL, transformed into analytics-ready mart tables, and visualised through Metabase — all orchestrated by Apache Airflow running in Docker.

---

## 📐 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Source Layer                             │
│   CSV Files (9 datasets, ~1.5M total rows in /data folder)      │
└────────────────────────────┬────────────────────────────────────┘
                             │ Extract + Load (Python + pandas)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Raw Layer  🗄️                               │
│            PostgreSQL  (olist_db)                               │
│   olist_customers_dataset        olist_orders_dataset           │
│   olist_order_items_dataset      olist_order_payments_dataset   │
│   olist_order_reviews_dataset    olist_products_dataset         │
│   olist_sellers_dataset          olist_geolocation_dataset      │
│   product_category_name_translation                             │
└────────────────────────────┬────────────────────────────────────┘
                             │ Transform (SQL)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Mart Layer  📊                              │
│            PostgreSQL  (olist_db)                               │
│   mart_revenue_by_month                                         │
│   mart_top_product_categories                                   │
│   mart_seller_performance                                       │
└────────────────────────────┬────────────────────────────────────┘
                             │ Visualise
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Presentation Layer  📈                         │
│                      Metabase                                   │
│            (dashboards & business insights)                     │
└─────────────────────────────────────────────────────────────────┘
```

Everything is **orchestrated by Apache Airflow** on a daily `@daily` schedule. Docker Compose ties all services together so the entire stack spins up with a single command.

---

## 🏗️ Tech Stack

| Layer            | Tool                           |
| ---------------- | ------------------------------ |
| Orchestration    | Apache Airflow 2.8.1           |
| Storage          | PostgreSQL 15                  |
| Ingestion        | Python 3.8, pandas, SQLAlchemy |
| Transformation   | SQL (PostgresOperator)         |
| Visualisation    | Metabase                       |
| Containerisation | Docker Compose                 |

---

## 📂 Project Structure

```
ecommerce-elt-pipeline/
├── dags/
│   └── olist_pipeline.py       # Airflow DAG definition
├── scripts/
│   ├── ingest.py               # CSV to PostgreSQL loader
│   └── transform.sql           # SQL mart table definitions
├── data/
│   ├── olist_customers_dataset.csv
│   ├── olist_geolocation_dataset.csv
│   ├── olist_order_items_dataset.csv
│   ├── olist_order_payments_dataset.csv
│   ├── olist_order_reviews_dataset.csv
│   ├── olist_orders_dataset.csv
│   ├── olist_products_dataset.csv
│   ├── olist_sellers_dataset.csv
│   └── product_category_name_translation.csv
├── logs/                       # Airflow task logs (auto-generated)
├── .env                        # Local secrets (not committed)
├── .env.example                # Template for environment variables
├── docker-compose.yml          # Service definitions
└── README.md
```

---

## 📦 Dataset

The dataset is the publicly available **Olist Brazilian E-Commerce** dataset hosted on Kaggle. It contains real anonymised commercial orders placed between 2016 and 2018.

| File                                  | Rows (approx.) | Description                    |
| ------------------------------------- | -------------- | ------------------------------ |
| olist_customers_dataset.csv           | ~99 k          | Customer demographics          |
| olist_orders_dataset.csv              | ~99 k          | Order lifecycle and timestamps |
| olist_order_items_dataset.csv         | ~112 k         | Items within each order        |
| olist_order_payments_dataset.csv      | ~103 k         | Payment method and value       |
| olist_order_reviews_dataset.csv       | ~104 k         | Customer review scores         |
| olist_products_dataset.csv            | ~32 k          | Product attributes             |
| olist_sellers_dataset.csv             | ~3 k           | Seller location data           |
| olist_geolocation_dataset.csv         | ~1 M           | Zip code geo coordinates       |
| product_category_name_translation.csv | ~70            | PT to EN category mapping      |

---

## 🔄 Pipeline Flow

### Step 1 🔽 Ingest (`ingest_olist` task)

`scripts/ingest.py` is a Python script that:

1. Reads database credentials from the `.env` file via `python-dotenv`
2. Creates a SQLAlchemy engine targeting `postgres-olist`
3. Iterates over every `.csv` file inside the `/data` directory
4. Loads each file into PostgreSQL using `pandas.DataFrame.to_sql` with `if_exists='replace'` and a `chunksize=1000` to avoid memory exhaustion on large datasets
5. Table names are derived directly from the file name (minus the `.csv` extension)

### Step 2 🔁 Transform (`transform_olist` task)

`scripts/transform.sql` runs after the ingest step completes. It uses `PostgresOperator` with the connection ID `postgres_olist` to execute three `CREATE TABLE AS SELECT` statements:

#### 📅 `mart_revenue_by_month`

Aggregates total payment value per calendar month by joining `olist_orders_dataset` with `olist_order_payments_dataset`. Useful for trend analysis and revenue forecasting.

#### 🏷️ `mart_top_product_categories`

Ranks product categories by total order volume. Joins order items, products, and the translation table to provide English category names alongside Portuguese originals.

#### 🧑‍💼 `mart_seller_performance`

Produces a seller scorecard with three KPIs per seller: total orders, total revenue, and average customer review score. Joins five source tables together.

Each mart table is fully recreated on every DAG run (`DROP TABLE IF EXISTS` before `CREATE TABLE AS SELECT`), keeping the logic simple and idempotent.

### Step 3 📊 Visualise (Metabase)

Metabase connects directly to `postgres-olist` and queries the mart tables. Analysts build charts and dashboards without writing SQL.

---

## ⚙️ Prerequisites

- **Docker** and **Docker Compose** installed on your machine
- The `data/` folder populated with the Olist CSV files (download from Kaggle)

---

## 🚀 Getting Started

### 1️⃣ Clone the repository

```bash
git clone <your-repo-url>
cd ecommerce-elt-pipeline
```

### 2️⃣ Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Open `.env` and set the following:

```env
DB_USER=olist_user
DB_PASS=olist_pass
DB_NAME=olist_db
DB_HOST=postgres-olist
DB_PORT=5432
```

> 💡 Use `DB_HOST=localhost` and `DB_PORT=5435` only when running `ingest.py` directly outside Docker.

### 3️⃣ Place the dataset

Make sure all nine CSV files are inside the `data/` directory before starting the stack.

### 4️⃣ Start all services

```bash
docker compose up -d
```

This command starts four containers:

| Container          | Purpose                   | Port          |
| ------------------ | ------------------------- | ------------- |
| `postgres-airflow` | Airflow metadata database | internal only |
| `postgres-olist`   | Olist data warehouse      | 5435          |
| `airflow`          | Scheduler + Webserver     | 8080          |
| `metabase`         | BI visualisation          | 3000          |

### 5️⃣ Access the services

| Service            | URL                   | Credentials             |
| ------------------ | --------------------- | ----------------------- |
| Airflow UI         | http://localhost:8080 | admin / admin           |
| Metabase           | http://localhost:3000 | set on first login      |
| PostgreSQL (olist) | localhost:5435        | olist_user / olist_pass |

### 6️⃣ Configure the Airflow connection

In the Airflow UI navigate to **Admin > Connections** and create a new connection:

| Field           | Value            |
| --------------- | ---------------- |
| Connection ID   | `postgres_olist` |
| Connection Type | `Postgres`       |
| Host            | `postgres-olist` |
| Schema          | `olist_db`       |
| Login           | `olist_user`     |
| Password        | `olist_pass`     |
| Port            | `5432`           |

### 7️⃣ Trigger the DAG

In the Airflow UI find **olist_elt_pipeline** and click the ▶️ **Trigger DAG** button. The two tasks will run sequentially:

```
ingest_olist  ➡️  transform_olist
```

### 8️⃣ Connect Metabase to PostgreSQL

On first launch Metabase walks you through adding a database. Point it at:

- **Host:** `postgres-olist`
- **Port:** `5432`
- **Database:** `olist_db`
- **User:** `olist_user`
- **Password:** `olist_pass`

Then explore the three mart tables to build your dashboards 📈

---

## 🗓️ DAG Schedule

The DAG is configured with `schedule='@daily'` and `catchup=False`. This means:

- It runs automatically once per day starting from the current date
- Historical backfill is **disabled** by default
- Manual runs can be triggered at any time from the Airflow UI

---

## 📊 Mart Tables Reference

### `mart_revenue_by_month`

| Column          | Type    | Description                       |
| --------------- | ------- | --------------------------------- |
| `date`          | DATE    | First day of the month            |
| `total_revenue` | NUMERIC | Sum of all payments in that month |

### `mart_top_product_categories`

| Column                | Type   | Description                       |
| --------------------- | ------ | --------------------------------- |
| `category_english`    | TEXT   | English category name             |
| `category_portuguese` | TEXT   | Original Portuguese name          |
| `total_orders`        | BIGINT | Number of orders in this category |

### `mart_seller_performance`

| Column                 | Type    | Description                      |
| ---------------------- | ------- | -------------------------------- |
| `seller_id`            | TEXT    | Unique seller identifier         |
| `total_orders`         | BIGINT  | Total orders fulfilled           |
| `total_revenue`        | NUMERIC | Sum of payments received         |
| `average_review_score` | NUMERIC | Mean customer review score (1–5) |

---

## 🛑 Stopping the Stack

```bash
docker compose down
```

To also remove all persisted data volumes:

```bash
docker compose down -v
```
