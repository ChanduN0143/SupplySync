
import csv
import random
import sqlite3
from pathlib import Path
from datetime import date, timedelta

# -----------------------------------------
# CONFIGURATION
# -----------------------------------------

SEED = 20261022
TOTAL_SUPPLIERS = 500
TOTAL_PURCHASE_ORDERS = 10000

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "supplysync.db"
SCHEMA_PATH = ROOT / "database" / "schema.sql"

random.seed(SEED)
DATA_DIR.mkdir(exist_ok=True)


# -----------------------------------------
# HELPER FUNCTIONS
# -----------------------------------------

def random_date(start, end):
    days = (end - start).days
    return start + timedelta(days=random.randint(0, days))


def export_csv(filename, rows):
    if not rows:
        return

    filepath = DATA_DIR / filename

    with open(filepath, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Created {filename}: {len(rows)} records")


# -----------------------------------------
# DATABASE INITIALIZATION
# -----------------------------------------

if DB_PATH.exists():
    DB_PATH.unlink()

connection = sqlite3.connect(DB_PATH)
connection.execute("PRAGMA foreign_keys = ON")

with open(SCHEMA_PATH, "r", encoding="utf-8") as file:
    connection.executescript(file.read())

cursor = connection.cursor()


# -----------------------------------------
# 1. GENERATE SUPPLIERS
# -----------------------------------------

suppliers = []

for i in range(1, TOTAL_SUPPLIERS + 1):
    supplier = {
        "supplier_id": f"SUP{i:05d}",
        "supplier_name": f"Supplier Company {i:04d}",
        "email": f"supplier{i:04d}@example.com",
        "contact_number": f"90000{i:05d}",
        "status": random.choices(
            ["ACTIVE", "INACTIVE"],
            weights=[95, 5]
        )[0]
    }
    suppliers.append(supplier)

cursor.executemany("""
    INSERT INTO suppliers
    (supplier_id, supplier_name, email, contact_number, status)
    VALUES (:supplier_id, :supplier_name, :email,
            :contact_number, :status)
""", suppliers)


# -----------------------------------------
# 2. GENERATE PURCHASE ORDERS
# -----------------------------------------

purchase_orders = []
po_lines = []
inventory_plans = []
production_orders = []

today = date(2026, 11, 10)
start_date = date(2026, 1, 1)

item_codes = [
    "ITEM-1001", "ITEM-1002", "ITEM-1003",
    "ITEM-1004", "ITEM-1005", "ITEM-1006",
    "ITEM-1007", "ITEM-1008", "ITEM-1009"
]

for i in range(1, TOTAL_PURCHASE_ORDERS + 1):

    po_id = f"PO{i:06d}"
    supplier = random.choice(suppliers)

    order_date = random_date(start_date, today)
    order_status = random.choices(
        ["OPEN", "PARTIAL", "COMPLETED", "CANCELLED"],
        weights=[35, 30, 30, 5]
    )[0]

    purchase_orders.append({
        "po_id": po_id,
        "supplier_id": supplier["supplier_id"],
        "order_date": order_date.isoformat(),
        "status": order_status
    })

    # Each purchase order contains 1 to 3 lines.
    number_of_lines = random.randint(1, 3)

    for line_number in range(1, number_of_lines + 1):

        po_line_id = f"{po_id}-L{line_number:02d}"

        requested_qty = random.randint(10, 1000)
        unit_price = round(random.uniform(10, 5000), 2)

        required_date = order_date + timedelta(
            days=random.randint(7, 60)
        )

        po_lines.append({
            "po_line_id": po_line_id,
            "po_id": po_id,
            "item_code": random.choice(item_codes),
            "description": f"Product for {po_line_id}",
            "requested_qty": requested_qty,
            "unit_price": unit_price,
            "required_date": required_date.isoformat()
        })

        # Initial inventory projection is based on the PO.
        plan_id = f"PLAN-{po_line_id}"

        inventory_plans.append({
            "plan_id": plan_id,
            "po_line_id": po_line_id,
            "projected_qty": requested_qty,
            "projected_date": required_date.isoformat(),
            "last_change_id": None
        })

        production_orders.append({
            "production_id": f"PROD-{po_line_id}",
            "plan_id": plan_id,
            "required_qty": round(requested_qty * 0.7, 2),
            "required_date": (
                required_date - timedelta(days=3)
            ).isoformat(),
            "status": "ON_TRACK"
        })


# -----------------------------------------
# 3. INSERT PURCHASE ORDERS
# -----------------------------------------

cursor.executemany("""
    INSERT INTO purchase_orders
    (po_id, supplier_id, order_date, status)
    VALUES (:po_id, :supplier_id, :order_date, :status)
""", purchase_orders)


# -----------------------------------------
# 4. INSERT PURCHASE ORDER LINES
# -----------------------------------------

cursor.executemany("""
    INSERT INTO po_lines
    (po_line_id, po_id, item_code, description,
     requested_qty, unit_price, required_date)
    VALUES (:po_line_id, :po_id, :item_code, :description,
            :requested_qty, :unit_price, :required_date)
""", po_lines)


# -----------------------------------------
# 5. INSERT INVENTORY PLANS
# -----------------------------------------

cursor.executemany("""
    INSERT INTO inventory_plans
    (plan_id, po_line_id, projected_qty,
     projected_date, last_change_id)
    VALUES (:plan_id, :po_line_id, :projected_qty,
            :projected_date, :last_change_id)
""", inventory_plans)


# -----------------------------------------
# 6. INSERT PRODUCTION ORDERS
# -----------------------------------------

cursor.executemany("""
    INSERT INTO production_orders
    (production_id, plan_id, required_qty,
     required_date, status)
    VALUES (:production_id, :plan_id, :required_qty,
            :required_date, :status)
""", production_orders)


# -----------------------------------------
# 7. EXPORT CSV FILES
# -----------------------------------------

export_csv("suppliers.csv", suppliers)
export_csv("purchase_orders.csv", purchase_orders)
export_csv("po_lines.csv", po_lines)
export_csv("inventory_plans.csv", inventory_plans)
export_csv("production_orders.csv", production_orders)


# -----------------------------------------
# 8. VERIFY GENERATED DATA
# -----------------------------------------

connection.commit()

print("\nDATABASE VERIFICATION")

tables = [
    "suppliers",
    "purchase_orders",
    "po_lines",
    "inventory_plans",
    "production_orders"
]

for table in tables:
    count = cursor.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

    print(f"{table}: {count}")

connection.close()

print("\nSTAGE 2A COMPLETED SUCCESSFULLY!")
print(f"Random seed used: {SEED}")
