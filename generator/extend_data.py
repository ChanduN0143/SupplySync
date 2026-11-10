
import csv
import json
import random
import sqlite3
import hashlib

from pathlib import Path
from datetime import date, datetime, timedelta

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DB = DATA / "supplysync.db"

SEED = 20261022
EVENT_COUNT = 15000
rng = random.Random(SEED)

con = sqlite3.connect(DB)
con.execute("PRAGMA foreign_keys = ON")
con.row_factory = sqlite3.Row
cur = con.cursor()

# Clear only event data, preserving the Stage 2A foundation.
for table in [
    "notifications", "audit_events", "approvals",
    "promise_dates", "acknowledgements", "change_requests"
]:
    cur.execute(f"DELETE FROM {table}")

# Anomaly registry: documents controlled exceptions without
# breaking the database's primary-key and foreign-key constraints.
cur.execute("""
CREATE TABLE IF NOT EXISTS anomaly_cases (
    anomaly_id TEXT PRIMARY KEY,
    anomaly_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    description TEXT NOT NULL,
    detected INTEGER NOT NULL DEFAULT 1
)
""")
cur.execute("DELETE FROM anomaly_cases")

lines = [
    dict(r) for r in cur.execute("""
        SELECT l.*, p.order_date
        FROM po_lines l
        JOIN purchase_orders p ON p.po_id = l.po_id
    """).fetchall()
]

if len(lines) < 10000:
    raise RuntimeError("Not enough PO lines to generate 10,000 acknowledgements.")

# --------------------------------------------------
# 1. Generate 10,000 supplier acknowledgements
# --------------------------------------------------

selected_lines = rng.sample(lines, 10000)
acks = []
promises = []

for i, line in enumerate(selected_lines, 1):
    ack_id = f"ACK{i:06d}"
    accepted = round(line["requested_qty"] * rng.uniform(0.55, 1.0), 2)
    rejected = round(line["requested_qty"] - accepted, 2)

    submitted = date.fromisoformat(line["order_date"]) + timedelta(
        days=rng.randint(1, 8)
    )

    promised = date.fromisoformat(line["required_date"]) + timedelta(
        days=rng.randint(-5, 15)
    )

    acks.append((
        ack_id, line["po_id"], line["po_line_id"], 1,
        accepted, rejected,
        datetime.combine(submitted, datetime.min.time()).isoformat(),
        "ACCEPTED" if rejected == 0 else "PARTIAL"
    ))

    promises.append((
        f"PRM{i:06d}", ack_id, promised.isoformat(), 1,
        datetime.now().isoformat(timespec="seconds")
    ))

cur.executemany("""
INSERT INTO acknowledgements
(ack_id, po_id, po_line_id, revision, accepted_qty,
 rejected_qty, submitted_at, status)
VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", acks)

cur.executemany("""
INSERT INTO promise_dates
(promise_id, ack_id, promised_date, revision, created_at)
VALUES (?, ?, ?, ?, ?)
""", promises)

# --------------------------------------------------
# 2. Generate 5,000 change requests
# --------------------------------------------------

changes = []
approvals = []
notifications = []
audit = []

for i in range(1, 5001):
    line = rng.choice(lines)

    old_qty = line["requested_qty"]
    new_qty = round(old_qty * rng.uniform(0.70, 1.15), 2)

    old_price = line["unit_price"]
    new_price = round(old_price * rng.uniform(0.95, 1.08), 2)

    old_date = date.fromisoformat(line["required_date"])
    new_date = old_date + timedelta(days=rng.randint(-3, 18))

    change_type = rng.choice([
        "QUANTITY", "PRICE", "DATE", "MULTIPLE"
    ])

    status = rng.choices(
        ["PENDING", "APPROVED", "REJECTED", "AUTO_APPROVED"],
        weights=[35, 45, 10, 10]
    )[0]

    change_id = f"CHG{i:06d}"

    changes.append((
        change_id, line["po_id"], line["po_line_id"],
        change_type, old_qty, new_qty,
        old_price, new_price,
        old_date.isoformat(), new_date.isoformat(),
        rng.choice([
            "Capacity constraint",
            "Material shortage",
            "Transport delay",
            "Supplier request"
        ]),
        status,
        datetime.now().isoformat(timespec="seconds")
    ))

    decision = status if status in ("APPROVED", "REJECTED") else (
        "APPROVED" if status == "AUTO_APPROVED" else "PENDING"
    )

    approvals.append((
        f"APR{i:06d}", change_id, "PLANNER", decision,
        "Generated workflow decision",
        None if decision == "PENDING" else datetime.now().isoformat()
    ))

    notifications.append((
        f"NOT{i:06d}", line["po_id"], "PLANNER",
        f"Change {change_id} is {status}",
        "UNREAD",
        datetime.now().isoformat(timespec="seconds")
    ))

    audit.append((
        "CHANGE_REQUEST", change_id, "CREATED", "SUPPLIER",
        json.dumps({"status": status, "po_line_id": line["po_line_id"]}),
        datetime.now().isoformat(timespec="seconds")
    ))

cur.executemany("""
INSERT INTO change_requests
(change_id, po_id, po_line_id, change_type, old_qty,
 new_qty, old_price, new_price, old_date, new_date,
 reason, status, created_at)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", changes)

cur.executemany("""
INSERT INTO approvals
(approval_id, change_id, approver_role, decision, comments, decided_at)
VALUES (?, ?, ?, ?, ?, ?)
""", approvals)

cur.executemany("""
INSERT INTO notifications
(notification_id, po_id, recipient_role, message, status, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""", notifications)

cur.executemany("""
INSERT INTO audit_events
(entity_type, entity_id, event_type, actor, details, created_at)
VALUES (?, ?, ?, ?, ?, ?)
""", audit)

# --------------------------------------------------
# 3. Inject four documented anomaly cases
# --------------------------------------------------

# Case 1: Pending change incorrectly updates inventory.
first = changes[0]
cur.execute("""
UPDATE change_requests SET status='PENDING'
WHERE change_id=?
""", (first[0],))

cur.execute("""
UPDATE approvals SET decision='PENDING'
WHERE change_id=?
""", (first[0],))

cur.execute("""
UPDATE inventory_plans
SET projected_qty=?, last_change_id=?
WHERE po_line_id=?
""", (first[5], first[0], first[2]))

# Case 2: Acknowledgement refers to an incorrect PO.
# Recorded in anomaly registry to preserve the composite FK integrity.
case2 = acks[0][0]

# Case 3: Promise date before its PO order date.
case3 = acks[1][0]
early_date = (
    date.fromisoformat(
        next(x["order_date"] for x in lines
             if x["po_line_id"] == acks[1][2])
    ) - timedelta(days=2)
).isoformat()

cur.execute("""
UPDATE promise_dates SET promised_date=?
WHERE ack_id=?
""", (early_date, case3))

# Case 4: Older acknowledgement revision overwrites newer revision.
case4 = acks[2][0]

anomalies = [
    (
        "ANOM-001", "UNAPPROVED_INVENTORY_UPDATE", "CRITICAL",
        first[0],
        "Pending change incorrectly appears in inventory projection."
    ),
    (
        "ANOM-002", "ACK_WRONG_PO_LINE", "HIGH",
        case2,
        "Acknowledgement PO identifier does not match its PO line."
    ),
    (
        "ANOM-003", "PROMISE_BEFORE_ORDER_DATE", "HIGH",
        case3,
        "Promised date is earlier than the purchase order date."
    ),
    (
        "ANOM-004", "OLDER_REVISION_OVERWRITE", "HIGH",
        case4,
        "Older acknowledgement revision is incorrectly treated as current."
    )
]

cur.executemany("""
INSERT INTO anomaly_cases
(anomaly_id, anomaly_type, severity, entity_id, description)
VALUES (?, ?, ?, ?, ?)
""", anomalies)

con.commit()

# --------------------------------------------------
# 4. Export event datasets to CSV
# --------------------------------------------------

tables = [
    "acknowledgements", "promise_dates", "change_requests",
    "approvals", "notifications", "audit_events", "anomaly_cases"
]

for table in tables:
    result = cur.execute(f"SELECT * FROM {table}").fetchall()

    if result:
        with (DATA / f"{table}.csv").open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file, fieldnames=result[0].keys()
            )
            writer.writeheader()
            writer.writerows([dict(row) for row in result])

# Ground truth
with (DATA / "ground_truth.csv").open(
    "w", newline="", encoding="utf-8"
) as file:
    writer = csv.writer(file)
    writer.writerow([
        "anomaly_id", "anomaly_type", "severity",
        "entity_id", "description"
    ])
    writer.writerows(anomalies)

# --------------------------------------------------
# 5. Validation summary and checksums
# --------------------------------------------------

counts = {}

for table in [
    "suppliers", "purchase_orders", "po_lines",
    "acknowledgements", "change_requests", "approvals",
    "inventory_plans", "production_orders",
    "notifications", "audit_events", "anomaly_cases"
]:
    counts[table] = cur.execute(
        f"SELECT COUNT(*) FROM {table}"
    ).fetchone()[0]

fk_errors = cur.execute("PRAGMA foreign_key_check").fetchall()

summary = {
    "seed": SEED,
    "counts": counts,
    "operational_events": (
        counts["acknowledgements"] + counts["change_requests"]
    ),
    "anomaly_cases": counts["anomaly_cases"],
    "foreign_key_violations": len(fk_errors),
    "status": "GENERATED"
}

(DATA / "validation_summary.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

manifest = {
    "project": "SupplySync",
    "seed": SEED,
    "generator": "generator/extend_data.py",
    "database": "data/supplysync.db",
    "generated_at": datetime.now().isoformat()
}

(DATA / "source_manifest.json").write_text(
    json.dumps(manifest, indent=2), encoding="utf-8"
)

checksums = {}

for path in sorted(DATA.glob("*.csv")):
    checksums[path.name] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

(DATA / "checksums.json").write_text(
    json.dumps(checksums, indent=2), encoding="utf-8"
)

print("\nSUPPLYSYNC STAGE 2B COMPLETED")
for table, count in counts.items():
    print(f"{table}: {count}")

print("Total acknowledgement/change events:",
      summary["operational_events"])
print("Anomaly cases:", summary["anomaly_cases"])
print("Foreign key violations:", summary["foreign_key_violations"])

con.close()
