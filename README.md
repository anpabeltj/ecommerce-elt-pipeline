# 🛒 Olist E-Commerce ELT Pipeline

An end-to-end **ELT (Extract, Load, Transform)** pipeline built on the [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce). Raw CSV files are loaded into PostgreSQL, transformed into analytics-ready mart tables with SQL, validated by automated data quality checks, and served through a Metabase dashboard that is provisioned automatically. Everything is orchestrated by Apache Airflow and runs in Docker Compose.

---

## ✨ Highlights

- **One command setup.** `docker compose up -d` starts the full stack. The Airflow connection, the Metabase admin account, the database connection, three analytical questions and a dashboard are all created automatically.
- **Data quality gates.** Six SQL checks run after every transform and fail the DAG if the marts are wrong.
- **Grain-aware modeling.** Marts are built at an explicit grain to avoid join fan-out. See [Data Model](#-data-model) for the profiling that drove this.

---

## 📐 Architecture Overview

```
┌──────────────────────────── Docker Compose ─────────────────────────────┐
│                                                                          │
│                ┌──────────── Airflow (orchestrator) ────────────┐        │
│                │  ingest_olist >> transform_olist >> quality_checks       │
│                └──────┬─────────────────┬─────────────────┬─────┘        │
│                       ┆ trigger         ┆ trigger         ┆ trigger      │
│  ┌────────┐     ┌─────▼─────┐   ┌───────▼─────── PostgreSQL (olist_db) ─┐│
│  │ 9 CSV  │────▶│ ingest.py │──▶│  raw tables ──SQL──▶ mart tables      ││
│  │ (/data)│     └───────────┘   │                  ▲                    ││
│  └────────┘                     │           6 quality checks            ││
│                                 └──────────────────┬────────────────────┘│
│                                                    │                     │
│                     metabase-setup ┄┄┄▶  Metabase (dashboard)            │
└──────────────────────────────────────────────────────────────────────────┘
```

A few design notes:

- **Airflow only orchestrates.** Data never flows through Airflow. It triggers the Python ingest and sends SQL to PostgreSQL.
- **Transformations run inside PostgreSQL.** Raw and mart tables live in the same database, which is what makes this ELT rather than ETL.
- **`metabase-setup` is a one-off container** that configures Metabase through its REST API and then exits.

---

## 🏗️ Tech Stack

| Layer            | Tool                                 |
| ---------------- | ------------------------------------ |
| Orchestration    | Apache Airflow 2.8.1 (LocalExecutor) |
| Storage          | PostgreSQL 15                        |
| Ingestion        | Python, pandas, SQLAlchemy           |
| Transformation   | SQL (PostgresOperator)               |
| Data quality     | SQL (SQLCheckOperator)               |
| Visualisation    | Metabase v0.63.18                    |
| Containerisation | Docker Compose                       |

---

## 📂 Project Structure

```
ecommerce-elt-pipeline/
├── dags/
│   └── olist_pipeline.py              # Airflow DAG definition
├── scripts/
│   ├── ingest.py                      # CSV to PostgreSQL loader
│   ├── transform.sql                  # Mart table definitions
│   ├── metabase_setup.py              # Auto provisions Metabase via REST API
│   ├── checks/                        # Data quality checks (one query per file)
│   │   ├── marts_not_empty.sql
│   │   ├── seller_id_unique.sql
│   │   ├── seller_revenue_matches_raw.sql
│   │   ├── monthly_revenue_matches_raw.sql
│   │   ├── no_orders_lost_in_categories.sql
│   │   └── review_score_in_range.sql
│   └── metabase_questions/            # SQL behind each dashboard chart
│       ├── 01_monthly_revenue_trend.sql
│       ├── 02_top_10_categories.sql
│       └── 03_late_delivery_vs_review.sql
├── data/                              # Olist CSV files (not committed)
├── docs/                              # Architecture and dashboard images
├── logs/                              # Airflow task logs (auto-generated)
├── .env.example                       # Template for environment variables
├── docker-compose.yml                 # Service definitions
└── README.md
```

---

## 📦 Dataset

The **Olist Brazilian E-Commerce** dataset contains real anonymised orders placed between 2016 and 2018. The CSV files are not committed to this repository. Download them from Kaggle into `data/`.

| File                                  | Rows (approx.) | Description                    |
| ------------------------------------- | -------------- | ------------------------------ |
| olist_customers_dataset.csv           | ~99 k          | Customer location              |
| olist_orders_dataset.csv              | ~99 k          | Order lifecycle and timestamps |
| olist_order_items_dataset.csv         | ~112 k         | Items within each order        |
| olist_order_payments_dataset.csv      | ~103 k         | Payment method and value       |
| olist_order_reviews_dataset.csv       | ~99 k          | Customer review scores         |
| olist_products_dataset.csv            | ~33 k          | Product attributes             |
| olist_sellers_dataset.csv             | ~3 k           | Seller location                |
| olist_geolocation_dataset.csv         | ~1 M           | Zip code geo coordinates       |
| product_category_name_translation.csv | ~70            | PT to EN category mapping      |

---

## 🔄 Pipeline Flow

The DAG `olist_elt_pipeline` runs three stages in sequence:

```
ingest_olist  ➡️  transform_olist  ➡️  quality_checks (6 checks in parallel)
```

### Step 1 🔽 Ingest (`ingest_olist`)

`scripts/ingest.py`:

1. Builds a SQLAlchemy engine from environment variables (credentials are URL-escaped with `URL.create`)
2. Reads every `.csv` file in `DATA_DIR`
3. Parses date columns so timestamps land in PostgreSQL as `TIMESTAMP` instead of `TEXT`
4. Loads each file with `to_sql` using `if_exists="replace"`, `chunksize=1000` and multi-row inserts
5. Names each table after its file name

### Step 2 🔁 Transform (`transform_olist`)

`scripts/transform.sql` rebuilds three mart tables with `DROP TABLE IF EXISTS` followed by `CREATE TABLE AS SELECT`, so every run is idempotent. Orders with status `canceled` or `unavailable` are excluded from all marts.

| Mart                          | Grain              | Answers                                                       |
| ----------------------------- | ------------------ | ------------------------------------------------------------- |
| `mart_revenue_by_month`       | 1 row per month    | How much revenue do we make each month?                       |
| `mart_top_product_categories` | 1 row per category | Which categories sell the most?                               |
| `mart_seller_performance`     | 1 row per seller   | Which sellers bring the most revenue, and how are they rated? |

### Step 3 ✅ Data Quality Checks (`quality_checks`)

Each file in `scripts/checks/` returns a single row of booleans. `SQLCheckOperator` fails the task if any value is `FALSE` or `NULL`, and each check is its own task so failures are easy to spot in the Airflow UI.

| Check                          | What it protects against                                    |
| ------------------------------ | ----------------------------------------------------------- |
| `marts_not_empty`              | A transform that silently produces no rows                  |
| `seller_id_unique`             | Duplicate rows in the seller scorecard                      |
| `seller_revenue_matches_raw`   | **Join fan-out** inflating seller revenue                   |
| `monthly_revenue_matches_raw`  | Revenue drift between the monthly mart and raw payments     |
| `no_orders_lost_in_categories` | Orders dropped by an inner join on the category translation |
| `review_score_in_range`        | Review averages outside 1 to 5                              |

> 🐛 **Why these checks exist.** An earlier version of `mart_seller_performance` joined payments, items and reviews at the same time. Orders with several items or payments were counted multiple times, which inflated seller revenue by about 26% (20.19M vs 15.74M BRL). `seller_revenue_matches_raw` and `monthly_revenue_matches_raw` both fail against that old query, so the bug cannot come back unnoticed.

### Step 4 📊 Visualise (Metabase)

On startup, `metabase-setup` calls the Metabase API to:

1. Create the admin account, skipping the setup wizard
2. Connect the `postgres-olist` database
3. Create three saved questions from `scripts/metabase_questions/`
4. Arrange them in the **Olist E-Commerce Overview** dashboard under _Our analytics_

Every step is skipped if it already exists, so the container is safe to rerun. Layout changes you make by hand in Metabase are not overwritten.

![Dashboard](docs/dashboard.png)

---

## 💡 Key Insights

| Question                                | Finding                                                                                                                                                     |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| How is monthly revenue trending?        | Revenue grew steadily through 2017 into 2018. November 2017 jumped about 53% month over month, likely driven by Black Friday.                               |
| Which categories drive the most orders? | `bed_bath_table`, `health_beauty` and `sports_leisure` lead. The top 3 account for about 26% of orders.                                                     |
| Does late delivery hurt reviews?        | **Yes, strongly.** Late orders average a 2.57 review score with 54% bad reviews (score 2 or lower). On-time orders average 4.29 with only 9.2% bad reviews. |

---

## 🧩 Data Model

### Current model

```
raw (9 tables, CSV as-is)  ──▶  mart (3 aggregated tables)
```

Marts are built directly from raw tables, with the grain of each mart made explicit in SQL (for example, seller revenue is first aggregated to one row per seller per order, and reviews to one row per order, before joining).

### Source grain issues

Profiling the raw data shows why joining Olist tables naively is risky:

| Finding                                  | Count            | Risk if joined directly                                                 |
| ---------------------------------------- | ---------------- | ----------------------------------------------------------------------- |
| Orders with more than 1 item             | 9,803            | Order-level values get duplicated                                       |
| Orders with more than 1 payment row      | 2,961            | Revenue counted multiple times                                          |
| Orders with more than 1 seller           | 1,278            | `payment_value` cannot be attributed to a seller                        |
| Orders with more than 1 review           | 547              | Order counts grow after joining reviews                                 |
| Duplicate `review_id` values             | 789              | `review_id` is not a valid primary key                                  |
| Zip prefixes with more than 1 coordinate | 17,972           | Joining geolocation explodes row counts                                 |
| `customer_id` rows vs unique customers   | 99,441 vs 96,096 | `customer_id` is per order, so use `customer_unique_id` to count people |

Because of this, seller revenue is calculated from `price + freight_value` in order items rather than from payments, and reviews are averaged per order before any join.

### Future improvement

The next evolution is a layered model with a star schema in the middle, ideally built with dbt:

```
raw  ──▶  staging  ──▶  core (star schema)  ──▶  mart
```

| Table              | Grain                                                               |
| ------------------ | ------------------------------------------------------------------- |
| `fact_order_items` | 1 row per item in an order                                          |
| `fact_orders`      | 1 row per order (payments summed, reviews averaged, `is_late` flag) |
| `dim_customers`    | 1 row per `customer_unique_id`                                      |
| `dim_products`     | 1 row per product, with English category                            |
| `dim_sellers`      | 1 row per seller                                                    |
| `dim_date`         | 1 row per calendar date                                             |

With two facts at different grains, every mart becomes a simple `SELECT ... GROUP BY` and fan-out is prevented by design.

---

## ⚙️ Prerequisites

- **Docker** and **Docker Compose**
- About **4 GB of RAM** allocated to Docker (Airflow, two PostgreSQL instances and Metabase run together)
- The Olist CSV files in `data/`

---

## 🚀 Getting Started

### 1️⃣ Clone the repository

```bash
git clone https://github.com/anpabeltj/ecommerce-elt-pipeline.git
cd ecommerce-elt-pipeline
```

### 2️⃣ Download the dataset

Download the dataset from [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) and extract all nine CSV files into `data/`. With the Kaggle CLI:

```bash
kaggle datasets download -d olistbr/brazilian-ecommerce -p data --unzip
```

### 3️⃣ Configure environment variables

```bash
cp .env.example .env
```

```env
# Olist database credentials (avoid @ : / in the password)
DB_USER=olist_user
DB_PASS=olist_pass
DB_NAME=olist_db

# Metabase admin account, created automatically
MB_ADMIN_EMAIL=admin@example.com
MB_ADMIN_PASSWORD=OlistAdmin2026

# Only used when running ingest.py directly on your machine
DB_HOST=localhost
DB_PORT=5435
DATA_DIR=./data
```

Inside Docker, `DB_HOST` and `DB_PORT` are overridden in `docker-compose.yml`, so the values above do not affect the containers.

### 4️⃣ Start all services

```bash
docker compose up -d
```

| Container          | Purpose                                   | Port          |
| ------------------ | ----------------------------------------- | ------------- |
| `postgres-airflow` | Airflow metadata database                 | internal only |
| `postgres-olist`   | Olist raw and mart tables                 | 5435          |
| `airflow`          | Scheduler and webserver                   | 8080          |
| `metabase`         | BI dashboard                              | 3000          |
| `metabase-setup`   | One-off Metabase provisioning, then exits | none          |

The Airflow connection `postgres_olist` is created automatically from the `AIRFLOW_CONN_POSTGRES_OLIST` environment variable. No manual setup in the UI is needed.

### 5️⃣ Run the pipeline

Open http://localhost:8080 (login `admin` / `admin`), find **olist_elt_pipeline** and click ▶️ **Trigger DAG**.

### 6️⃣ Open the dashboard

Check that provisioning finished:

```bash
docker compose logs metabase-setup
```

When the log ends with `Selesai`, open http://localhost:3000, log in with `MB_ADMIN_EMAIL` and `MB_ADMIN_PASSWORD`, and go to **Our analytics > Olist E-Commerce Overview**.

> The dashboard queries the mart tables, so run the DAG at least once before opening it.

### 🔗 Service access

| Service            | URL                   | Credentials                            |
| ------------------ | --------------------- | -------------------------------------- |
| Airflow UI         | http://localhost:8080 | admin / admin                          |
| Metabase           | http://localhost:3000 | `MB_ADMIN_EMAIL` / `MB_ADMIN_PASSWORD` |
| PostgreSQL (olist) | localhost:5435        | as set in `.env`                       |

---

## 🗓️ DAG Schedule

The DAG uses `schedule=None`, so it only runs when triggered manually. The source is a static dataset, and reloading it on a schedule would add work without adding new data. For a live source, switch to a cron schedule such as `@daily`.

---

## 📊 Mart Tables Reference

### `mart_revenue_by_month`

| Column          | Type    | Description                                    |
| --------------- | ------- | ---------------------------------------------- |
| `date`          | DATE    | First day of the month                         |
| `total_revenue` | NUMERIC | Sum of payments for valid orders in that month |

### `mart_top_product_categories`

| Column                | Type   | Description                                                   |
| --------------------- | ------ | ------------------------------------------------------------- |
| `category_english`    | TEXT   | English name, falls back to Portuguese or `unknown`           |
| `category_portuguese` | TEXT   | Original Portuguese name, or `unknown`                        |
| `total_orders`        | BIGINT | Distinct orders containing at least one item in this category |

### `mart_seller_performance`

| Column                 | Type    | Description                                            |
| ---------------------- | ------- | ------------------------------------------------------ |
| `seller_id`            | TEXT    | Unique seller identifier                               |
| `total_orders`         | BIGINT  | Distinct orders containing this seller's items         |
| `total_revenue`        | NUMERIC | Sum of `price + freight_value` for this seller's items |
| `average_review_score` | NUMERIC | Mean review score (1 to 5), averaged per order first   |

---

## 🛠️ Troubleshooting

| Problem                                                   | Fix                                                                                                                                                                                                                            |
| --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Bind for 0.0.0.0:3000 failed: port is already allocated` | Another container uses port 3000. Stop it with `docker stop <name>` or change the Metabase port mapping to `"3001:3000"`.                                                                                                      |
| Metabase exits with `Cannot run without an instance id`   | Already handled with `hostname` and a fixed Quartz `instanceId` in `docker-compose.yml`. If it happened before the fix, remove the broken volume with `docker volume rm ecommerce-elt-pipeline_metabase_data` and start again. |
| Metabase still shows the setup wizard                     | Provisioning may not have finished. Run `docker compose up metabase-setup` and reload http://localhost:3000.                                                                                                                   |
| A quality check task fails                                | Open the task log in Airflow. The failing check name tells you which mart and which rule broke.                                                                                                                                |

---

## 🛑 Stopping the Stack

```bash
docker compose down
```

To also remove all volumes (database data, Airflow metadata and Metabase dashboards):

```bash
docker compose down -v
```
