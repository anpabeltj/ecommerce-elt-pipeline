"""
Setup otomatis Metabase:
1. Membuat akun admin (melewati setup wizard)
2. Menambahkan database olist
3. Membuat saved questions dari file SQL di scripts/metabase_queries/
4. Menyusun ketiga question dalam satu dashboard

Aman dijalankan berulang kali. Admin, database, question, atau dashboard yang sudah ada akan dilewati.
Hanya memakai library bawaan Python, jadi tidak perlu pip install.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

MB_URL = os.getenv("MB_URL", "http://metabase:3000")
ADMIN_EMAIL = os.environ["MB_ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["MB_ADMIN_PASSWORD"]
DATABASE_NAME = "Olist"
DASHBOARD_NAME = "Olist E-Commerce Overview"
DASHBOARD_DESCRIPTION = "Tren revenue, kategori terlaris, dan dampak keterlambatan pengiriman terhadap review."
QUESTIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "metabase_queries")

# Daftar question yang dibuat di "Our analytics".
# display: jenis chart Metabase (line, bar, row, table, dll)
# layout: posisi di dashboard. Grid dashboard Metabase lebarnya 24 kolom.
QUESTIONS = [
    {
        "file": "monthly_revenue_trend.sql",
        "name": "Monthly revenue trend",
        "description": "Bagaimana tren revenue bulanan dan pertumbuhannya dibanding bulan sebelumnya?",
        "display": "line",
        "visualization_settings": {
            "graph.dimensions": ["month"],
            "graph.metrics": ["total_revenue"],
        },
        "layout": {"row": 0, "col": 0, "size_x": 24, "size_y": 7},
    },
    {
        "file": "top_10_categories.sql",
        "name": "Top 10 product categories by orders",
        "description": "Kategori produk apa yang paling banyak dibeli, dan berapa porsinya dari total order?",
        "display": "row",
        "visualization_settings": {
            "graph.dimensions": ["category"],
            "graph.metrics": ["total_orders"],
        },
        "layout": {"row": 7, "col": 0, "size_x": 12, "size_y": 8},
    },
    {
        "file": "late_delivery_vs_review.sql",
        "name": "Late delivery vs review score",
        "description": "Apakah pengiriman yang terlambat membuat review pelanggan lebih buruk?",
        "display": "bar",
        "visualization_settings": {
            "graph.dimensions": ["delivery_status"],
            "graph.metrics": ["bad_review_pct"],
        },
        "layout": {"row": 7, "col": 12, "size_x": 12, "size_y": 8},
    },
]


def call_api(method, path, body=None, session_id=None):
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = urllib.request.Request(MB_URL + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if session_id:
        request.add_header("X-Metabase-Session", session_id)

    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8")
        if raw:
            return json.loads(raw)
        return None


def unwrap_list(result):
    # Beberapa endpoint versi baru membungkus hasil di key "data"
    if isinstance(result, dict):
        return result.get("data", [])
    return result


def wait_for_metabase(max_wait_seconds=600):
    print("Menunggu Metabase siap...")
    waited = 0
    while waited < max_wait_seconds:
        try:
            health = call_api("GET", "/api/health")
            if health and health.get("status") == "ok":
                print("Metabase siap")
                return
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass
        time.sleep(5)
        waited += 5
    sys.exit("Metabase tidak siap dalam batas waktu")


def create_admin_if_needed():
    properties = call_api("GET", "/api/session/properties")
    if properties.get("has-user-setup"):
        print("Admin sudah ada, setup wizard dilewati")
        return

    body = {
        "token": properties["setup-token"],
        "user": {
            "first_name": "Admin",
            "last_name": "Olist",
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD,
            "site_name": "Olist Analytics",
        },
        "prefs": {
            "site_name": "Olist Analytics",
            "site_locale": "en",
        },
    }
    call_api("POST", "/api/setup", body)
    print(f"Admin dibuat: {ADMIN_EMAIL}")


def login():
    body = {"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    session = call_api("POST", "/api/session", body)
    return session["id"]


def find_database_id(session_id):
    databases = unwrap_list(call_api("GET", "/api/database", session_id=session_id))
    for database in databases:
        if database["name"] == DATABASE_NAME:
            return database["id"]
    return None


def add_database_if_needed(session_id):
    database_id = find_database_id(session_id)
    if database_id is not None:
        print(f"Database {DATABASE_NAME} sudah terhubung")
        return database_id

    body = {
        "engine": "postgres",
        "name": DATABASE_NAME,
        "details": {
            "host": "postgres-olist",
            "port": 5432,
            "dbname": os.environ["DB_NAME"],
            "user": os.environ["DB_USER"],
            "password": os.environ["DB_PASS"],
            "ssl": False,
        },
    }
    database = call_api("POST", "/api/database", body, session_id=session_id)
    print(f"Database {DATABASE_NAME} berhasil ditambahkan")
    return database["id"]


def get_existing_card_ids(session_id):
    cards = unwrap_list(call_api("GET", "/api/card", session_id=session_id))
    card_ids = {}
    for card in cards:
        if not card.get("archived"):
            card_ids[card["name"]] = card["id"]
    return card_ids


def read_sql(file_name):
    with open(os.path.join(QUESTIONS_DIR, file_name), encoding="utf-8") as sql_file:
        return sql_file.read()


def create_questions_if_needed(session_id, database_id):
    card_ids = get_existing_card_ids(session_id)

    for question in QUESTIONS:
        if question["name"] in card_ids:
            print(f"Question sudah ada: {question['name']}")
            continue

        body = {
            "name": question["name"],
            "description": question["description"],
            "display": question["display"],
            "visualization_settings": question["visualization_settings"],
            "collection_id": None,  # None = Our analytics
            "type": "question",
            "dataset_query": {
                "type": "native",
                "database": database_id,
                "native": {"query": read_sql(question["file"])},
            },
        }
        card = call_api("POST", "/api/card", body, session_id=session_id)
        card_ids[question["name"]] = card["id"]
        print(f"Question dibuat: {question['name']}")

    return card_ids


def find_dashboard_id(session_id):
    results = unwrap_list(
        call_api("GET", "/api/search?models=dashboard", session_id=session_id)
    )
    for item in results:
        if item.get("name") == DASHBOARD_NAME and not item.get("archived"):
            return item["id"]
    return None


def create_dashboard_if_needed(session_id, card_ids):
    dashboard_id = find_dashboard_id(session_id)

    if dashboard_id is None:
        body = {
            "name": DASHBOARD_NAME,
            "description": DASHBOARD_DESCRIPTION,
            "collection_id": None,  # None = Our analytics
        }
        dashboard = call_api("POST", "/api/dashboard", body, session_id=session_id)
        dashboard_id = dashboard["id"]
        print(f"Dashboard dibuat: {DASHBOARD_NAME}")
    else:
        dashboard = call_api("GET", f"/api/dashboard/{dashboard_id}", session_id=session_id)
        if dashboard.get("dashcards"):
            print(f"Dashboard sudah ada: {DASHBOARD_NAME}")
            return

    # Id negatif menandakan dashcard baru untuk Metabase
    dashcards = []
    new_id = -1
    for question in QUESTIONS:
        layout = question["layout"]
        dashcards.append(
            {
                "id": new_id,
                "card_id": card_ids[question["name"]],
                "row": layout["row"],
                "col": layout["col"],
                "size_x": layout["size_x"],
                "size_y": layout["size_y"],
                "parameter_mappings": [],
                "visualization_settings": {},
            }
        )
        new_id -= 1

    call_api(
        "PUT",
        f"/api/dashboard/{dashboard_id}",
        {"dashcards": dashcards},
        session_id=session_id,
    )
    print(f"{len(dashcards)} chart ditambahkan ke dashboard")


def main():
    wait_for_metabase()
    try:
        create_admin_if_needed()
        session_id = login()
        database_id = add_database_if_needed(session_id)
        card_ids = create_questions_if_needed(session_id, database_id)
        create_dashboard_if_needed(session_id, card_ids)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8")
        sys.exit(f"API error {error.code}: {detail}")
    print(f"Selesai. Login di http://localhost:3000 dengan {ADMIN_EMAIL}")


if __name__ == "__main__":
    main()