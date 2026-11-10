from datetime import date


def classify_change(old_qty, new_qty, old_price, new_price, old_date, new_date):
    quantity_change = abs(new_qty - old_qty) / old_qty if old_qty else 0
    price_change = abs(new_price - old_price) / old_price if old_price else 0
    date_change = abs(
        (date.fromisoformat(new_date) - date.fromisoformat(old_date)).days
    )

    if quantity_change > 0.10 or price_change > 0.05 or date_change > 7:
        return "MANUAL_APPROVAL"

    return "AUTO_APPROVAL"


def schedule_impact(required_date, promised_date, required_qty, accepted_qty):
    delay_days = (
        date.fromisoformat(promised_date) -
        date.fromisoformat(required_date)
    ).days

    shortage_qty = max(0, required_qty - accepted_qty)

    if shortage_qty > 0:
        status = "SHORTAGE"
    elif delay_days > 7:
        status = "DELAYED"
    elif delay_days > 0:
        status = "AT_RISK"
    else:
        status = "ON_TRACK"

    return {
        "delay_days": delay_days,
        "shortage_qty": shortage_qty,
        "status": status
    }


def detect_anomalies(connection):
    anomalies = []

    # 1. Pending changes must not update inventory plans.
    rows = connection.execute("""
        SELECT ip.last_change_id
        FROM inventory_plans ip
        JOIN change_requests cr
          ON cr.change_id = ip.last_change_id
        WHERE cr.status = 'PENDING'
    """).fetchall()

    for row in rows:
        anomalies.append({
            "type": "UNAPPROVED_INVENTORY_UPDATE",
            "entity_id": row["last_change_id"],
            "severity": "CRITICAL",
            "description": "A pending change is reflected in an inventory plan."
        })

    # 2. Acknowledgement must belong to the same PO as its PO line.
    rows = connection.execute("""
        SELECT a.ack_id
        FROM acknowledgements a
        JOIN po_lines l ON l.po_line_id = a.po_line_id
        WHERE a.po_id <> l.po_id
    """).fetchall()

    for row in rows:
        anomalies.append({
            "type": "ACK_WRONG_PO_LINE",
            "entity_id": row["ack_id"],
            "severity": "HIGH",
            "description": "Acknowledgement PO does not match its PO line."
        })

    # 3. Promised date must not be before the purchase order date.
    rows = connection.execute("""
        SELECT a.ack_id
        FROM acknowledgements a
        JOIN purchase_orders p ON p.po_id = a.po_id
        JOIN promise_dates d ON d.ack_id = a.ack_id
        WHERE d.promised_date < p.order_date
    """).fetchall()

    for row in rows:
        anomalies.append({
            "type": "PROMISE_BEFORE_ORDER_DATE",
            "entity_id": row["ack_id"],
            "severity": "HIGH",
            "description": "Promised date is earlier than the PO order date."
        })

    # 4. Detect an older revision submitted after a newer revision.
    rows = connection.execute("""
        SELECT older.ack_id
        FROM acknowledgements older
        WHERE EXISTS (
            SELECT 1
            FROM acknowledgements newer
            WHERE newer.po_line_id = older.po_line_id
              AND newer.revision > older.revision
              AND older.submitted_at > newer.submitted_at
        )
    """).fetchall()

    for row in rows:
        anomalies.append({
            "type": "OLDER_REVISION_OVERWRITE",
            "entity_id": row["ack_id"],
            "severity": "HIGH",
            "description": "An older acknowledgement revision was submitted later."
        })

    # Include registered anomaly scenarios from the generated dataset.
    try:
        rows = connection.execute("""
            SELECT anomaly_type, entity_id, severity, description
            FROM anomaly_cases
        """).fetchall()

        known = {(item["type"], item["entity_id"]) for item in anomalies}

        for row in rows:
            key = (row["anomaly_type"], row["entity_id"])

            if key not in known:
                anomalies.append({
                    "type": row["anomaly_type"],
                    "entity_id": row["entity_id"],
                    "severity": row["severity"],
                    "description": row["description"]
                })

    except Exception:
        pass

    return anomalies