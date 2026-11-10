import json

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR))

from backend.app.database import get_connection, DB_PATH
from business_rules import (
    detect_anomalies,
    classify_change,
    schedule_impact
)


app = FastAPI(
    title="SupplySync API",
    description="Supplier acknowledgement and supply-chain workflow management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
# --------------------------------------------------
# PURCHASE ORDER REQUEST MODELS
# --------------------------------------------------

class PurchaseOrderLineInput(BaseModel):
    item_code: str = Field(min_length=1, max_length=100)
    description: str | None = None
    requested_qty: float = Field(gt=0)
    unit_price: float = Field(ge=0)
    required_date: date


class PurchaseOrderCreate(BaseModel):
    supplier_id: str
    order_date: date
    status: Literal[
        "OPEN",
        "PARTIAL",
        "COMPLETED",
        "CANCELLED"
    ] = "OPEN"
    lines: list[PurchaseOrderLineInput] = Field(min_length=1)


class PurchaseOrderUpdate(BaseModel):
    supplier_id: str | None = None
    order_date: date | None = None
    status: Literal[
        "OPEN",
        "PARTIAL",
        "COMPLETED",
        "CANCELLED"
    ] | None = None


@app.get("/")
def root():
    return {
        "application": "SupplySync",
        "message": "SupplySync API is running",
        "documentation": "/docs"
    }


@app.get("/api/health")
def health():
    try:
        connection = get_connection()

        connection.execute("SELECT 1")
        connection.close()

        return {
            "status": "healthy",
            "database": "connected",
            "database_path": str(DB_PATH)
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {error}"
        )


@app.get("/api/summary")
def summary():
    connection = get_connection()

    try:
        tables = [
            "suppliers",
            "purchase_orders",
            "po_lines",
            "acknowledgements",
            "promise_dates",
            "change_requests",
            "approvals",
            "inventory_plans",
            "production_orders",
            "notifications",
            "audit_events",
            "anomaly_cases"
        ]

        counts = {}

        for table in tables:
            counts[table] = connection.execute(
                f"SELECT COUNT(*) FROM {table}"
            ).fetchone()[0]

        statuses = {}

        for status in ["PENDING", "APPROVED", "REJECTED"]:
            statuses[status.lower()] = connection.execute(
                """
                SELECT COUNT(*)
                FROM change_requests
                WHERE status = ?
                """,
                (status,)
            ).fetchone()[0]

        return {
            "counts": counts,
            "change_status": statuses
        }

    finally:
        connection.close()


@app.get("/api/orders")
def orders(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    q: str | None = None,
    status: str | None = None,
    supplier_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None
):
    connection = get_connection()

    try:
        query = """
            SELECT
                p.po_id,
                p.supplier_id,
                s.supplier_name,
                p.order_date,
                p.status,
                COUNT(l.po_line_id) AS line_count,
                COALESCE(SUM(l.requested_qty), 0)
                    AS requested_quantity,
                COALESCE(
                    SUM(l.requested_qty * l.unit_price), 0
                ) AS total_amount
            FROM purchase_orders p
            JOIN suppliers s
                ON s.supplier_id = p.supplier_id
            LEFT JOIN po_lines l
                ON l.po_id = p.po_id
            WHERE 1=1
        """

        params = []

        if q:
            query += """
                AND (
                    p.po_id LIKE ?
                    OR s.supplier_name LIKE ?
                )
            """
            search_value = f"%{q.strip()}%"
            params.extend([search_value, search_value])

        if status:
            allowed_statuses = {
                "OPEN", "PARTIAL", "COMPLETED", "CANCELLED"
            }

            normalized_status = status.upper()

            if normalized_status not in allowed_statuses:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid purchase order status"
                )

            query += " AND p.status = ?"
            params.append(normalized_status)

        if supplier_id:
            query += " AND p.supplier_id = ?"
            params.append(supplier_id)

        if start_date:
            query += " AND p.order_date >= ?"
            params.append(start_date.isoformat())

        if end_date:
            query += " AND p.order_date <= ?"
            params.append(end_date.isoformat())

        query += """
            GROUP BY p.po_id
            ORDER BY p.order_date DESC, p.po_id DESC
            LIMIT ? OFFSET ?
        """

        params.extend([limit, offset])

        rows = connection.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()

@app.get("/api/orders/{po_id}")
def order_details(po_id: str):
    connection = get_connection()

    try:
        order = connection.execute(
            """
            SELECT
                p.*,
                s.supplier_name,
                s.email,
                s.contact_number,
                s.status AS supplier_status
            FROM purchase_orders p
            JOIN suppliers s
                ON s.supplier_id = p.supplier_id
            WHERE p.po_id = ?
            """,
            (po_id,)
        ).fetchone()

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Purchase order not found"
            )

        result = dict(order)

        lines = connection.execute(
            """
            SELECT *
            FROM po_lines
            WHERE po_id = ?
            ORDER BY po_line_id
            """,
            (po_id,)
        ).fetchall()

        result["lines"] = []

        for line in lines:
            line_data = dict(line)

            acknowledgements = connection.execute(
                """
                SELECT *
                FROM acknowledgements
                WHERE po_line_id = ?
                ORDER BY revision DESC
                """,
                (line["po_line_id"],)
            ).fetchall()

            line_data["acknowledgements"] = []

            for acknowledgement in acknowledgements:
                ack_data = dict(acknowledgement)

                promises = connection.execute(
                    """
                    SELECT *
                    FROM promise_dates
                    WHERE ack_id = ?
                    ORDER BY revision DESC
                    """,
                    (acknowledgement["ack_id"],)
                ).fetchall()

                ack_data["promise_dates"] = [
                    dict(promise) for promise in promises
                ]

                line_data["acknowledgements"].append(ack_data)

            result["lines"].append(line_data)

        return result

    finally:
        connection.close()

@app.post("/api/orders", status_code=201)
def create_order(payload: PurchaseOrderCreate):
    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        supplier = connection.execute(
            """
            SELECT supplier_id, status
            FROM suppliers
            WHERE supplier_id = ?
            """,
            (payload.supplier_id,)
        ).fetchone()

        if not supplier:
            raise HTTPException(
                status_code=404,
                detail="Supplier not found"
            )

        if supplier["status"] != "ACTIVE":
            raise HTTPException(
                status_code=400,
                detail="Cannot create an order for an inactive supplier"
            )

        latest = connection.execute(
            """
            SELECT COALESCE(
                MAX(CAST(SUBSTR(po_id, 3) AS INTEGER)), 0
            ) AS max_id
            FROM purchase_orders
            WHERE po_id GLOB 'PO[0-9]*'
            """
        ).fetchone()

        next_number = latest["max_id"] + 1
        po_id = f"PO{next_number:06d}"

        connection.execute(
            """
            INSERT INTO purchase_orders (
                po_id,
                supplier_id,
                order_date,
                status
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                po_id,
                payload.supplier_id,
                payload.order_date.isoformat(),
                payload.status
            )
        )

        created_lines = []

        for index, line in enumerate(payload.lines, start=1):
            po_line_id = f"{po_id}-L{index:02d}"

            connection.execute(
                """
                INSERT INTO po_lines (
                    po_line_id,
                    po_id,
                    item_code,
                    description,
                    requested_qty,
                    unit_price,
                    required_date
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    po_line_id,
                    po_id,
                    line.item_code.strip(),
                    line.description,
                    line.requested_qty,
                    line.unit_price,
                    line.required_date.isoformat()
                )
            )

            created_lines.append(po_line_id)

        connection.execute(
            """
            INSERT INTO audit_events (
                entity_type,
                entity_id,
                event_type,
                actor,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                "PURCHASE_ORDER",
                po_id,
                "CREATED",
                "PLANNER",
                json.dumps({
                    "supplier_id": payload.supplier_id,
                    "line_count": len(payload.lines),
                    "line_ids": created_lines
                })
            )
        )

        connection.commit()

        return {
            "message": "Purchase order created successfully",
            "po_id": po_id,
            "line_ids": created_lines
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Purchase order creation failed: {error}"
        )

    finally:
        connection.close()

@app.put("/api/orders/{po_id}")
def update_order(
    po_id: str,
    payload: PurchaseOrderUpdate
):
    connection = get_connection()

    try:
        connection.execute("BEGIN IMMEDIATE")

        existing = connection.execute(
            """
            SELECT *
            FROM purchase_orders
            WHERE po_id = ?
            """,
            (po_id,)
        ).fetchone()

        if not existing:
            raise HTTPException(
                status_code=404,
                detail="Purchase order not found"
            )

        updates = payload.model_dump(exclude_unset=True)

        if not updates:
            raise HTTPException(
                status_code=400,
                detail="No update fields provided"
            )

        if "supplier_id" in updates:
            if not updates["supplier_id"]:
                raise HTTPException(
                    status_code=400,
                    detail="Supplier ID cannot be empty"
                )

            supplier = connection.execute(
                """
                SELECT status
                FROM suppliers
                WHERE supplier_id = ?
                """,
                (updates["supplier_id"],)
            ).fetchone()

            if not supplier or supplier["status"] != "ACTIVE":
                raise HTTPException(
                    status_code=400,
                    detail="Supplier does not exist or is inactive"
                )

        changes = {}

        for field, value in updates.items():
            if value is not None:
                if field == "order_date":
                    value = value.isoformat()

                changes[field] = value

        if not changes:
            raise HTTPException(
                status_code=400,
                detail="No valid update values provided"
            )

        set_clause = ", ".join(
            f"{field} = ?" for field in changes
        )

        values = list(changes.values())
        values.append(po_id)

        connection.execute(
            f"""
            UPDATE purchase_orders
            SET {set_clause}
            WHERE po_id = ?
            """,
            values
        )

        connection.execute(
            """
            INSERT INTO audit_events (
                entity_type,
                entity_id,
                event_type,
                actor,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                "PURCHASE_ORDER",
                po_id,
                "UPDATED",
                "PLANNER",
                json.dumps({
                    "previous_values": {
                        field: existing[field]
                        for field in changes
                    },
                    "new_values": changes
                })
            )
        )

        connection.commit()

        return {
            "message": "Purchase order updated successfully",
            "po_id": po_id,
            "updated_fields": changes
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Purchase order update failed: {error}"
        )

    finally:
        connection.close()
# ==========================================================
# PHASE 2A: SUPPLIER ACKNOWLEDGEMENTS AND PROMISE DATES
# ==========================================================

class AcknowledgementCreate(BaseModel):
    po_id: str
    po_line_id: str
    accepted_qty: float = Field(ge=0)
    rejected_qty: float = Field(ge=0)
    promised_date: date


def generate_next_id(connection, table, column, prefix, width=6):
    # Table and column names are internal constants, not user input.
    row = connection.execute(
        f"""
        SELECT MAX(CAST(SUBSTR({column}, ?) AS INTEGER)) AS max_id
        FROM {table}
        WHERE {column} LIKE ?
        """,
        (len(prefix) + 1, prefix + "%")
    ).fetchone()

    next_number = (row["max_id"] or 0) + 1
    return f"{prefix}{next_number:0{width}d}"


@app.get("/api/acknowledgements")
def get_acknowledgements(
    po_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500)
):
    connection = get_connection()

    try:
        sql = """
            SELECT
                a.*,
                l.item_code,
                l.description,
                l.requested_qty,
                p.promised_date,
                p.promise_id
            FROM acknowledgements a
            JOIN po_lines l ON l.po_line_id = a.po_line_id
            LEFT JOIN promise_dates p ON p.ack_id = a.ack_id
            WHERE 1 = 1
        """
        params = []

        if po_id:
            sql += " AND a.po_id = ?"
            params.append(po_id)

        sql += " ORDER BY a.submitted_at DESC LIMIT ?"
        params.append(limit)

        rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    finally:
        connection.close()


@app.post("/api/acknowledgements", status_code=201)
def create_acknowledgement(payload: AcknowledgementCreate):
    connection = get_connection()

    try:
        line = connection.execute(
            """
            SELECT
                l.*,
                p.order_date,
                p.supplier_id
            FROM po_lines l
            JOIN purchase_orders p ON p.po_id = l.po_id
            WHERE l.po_line_id = ? AND l.po_id = ?
            """,
            (payload.po_line_id, payload.po_id)
        ).fetchone()

        if not line:
            raise HTTPException(
                status_code=404,
                detail="Purchase order line not found for this PO"
            )

        if payload.accepted_qty + payload.rejected_qty > line["requested_qty"]:
            raise HTTPException(
                status_code=400,
                detail="Accepted and rejected quantities cannot exceed requested quantity"
            )

        if payload.promised_date < date.fromisoformat(line["order_date"]):
            raise HTTPException(
                status_code=400,
                detail="Promised date cannot be before purchase order date"
            )

        revision_row = connection.execute(
            """
            SELECT COALESCE(MAX(revision), 0) AS revision
            FROM acknowledgements
            WHERE po_line_id = ?
            """,
            (payload.po_line_id,)
        ).fetchone()

        revision = revision_row["revision"] + 1

        if payload.accepted_qty == 0 and payload.rejected_qty > 0:
            status = "REJECTED"
        elif payload.rejected_qty > 0:
            status = "PARTIAL"
        elif payload.accepted_qty == line["requested_qty"]:
            status = "ACCEPTED"
        else:
            status = "SUBMITTED"

        ack_id = generate_next_id(
            connection, "acknowledgements", "ack_id", "ACK"
        )

        promise_id = generate_next_id(
            connection, "promise_dates", "promise_id", "PRM"
        )

        connection.execute(
            """
            INSERT INTO acknowledgements (
                ack_id, po_id, po_line_id, revision,
                accepted_qty, rejected_qty, status, submitted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                ack_id,
                payload.po_id,
                payload.po_line_id,
                revision,
                payload.accepted_qty,
                payload.rejected_qty,
                status
            )
        )

        connection.execute(
            """
            INSERT INTO promise_dates (
                promise_id, ack_id, promised_date, revision, created_at
            )
            VALUES (?, ?, ?, 1, CURRENT_TIMESTAMP)
            """,
            (
                promise_id,
                ack_id,
                payload.promised_date.isoformat()
            )
        )

        connection.execute(
            """
            INSERT INTO audit_events (
                entity_type, entity_id, event_type,
                actor, details, created_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                "ACKNOWLEDGEMENT",
                ack_id,
                "SUBMITTED",
                "SUPPLIER",
                json.dumps({
                    "po_id": payload.po_id,
                    "po_line_id": payload.po_line_id,
                    "revision": revision,
                    "accepted_qty": payload.accepted_qty,
                    "rejected_qty": payload.rejected_qty,
                    "promised_date": payload.promised_date.isoformat(),
                    "status": status
                })
            )
        )

        connection.execute(
            """
            INSERT INTO notifications (
                notification_id, po_id, recipient_role, message, status
            )
            VALUES (?, ?, ?, ?, 'UNREAD')
            """,
            (
                generate_next_id(
                    connection, "notifications",
                    "notification_id", "NOT"
                ),
                payload.po_id,
                "PLANNER",
                f"Supplier submitted acknowledgement {ack_id} with status {status}"
            )
        )

        connection.commit()

        return {
            "message": "Acknowledgement submitted successfully",
            "ack_id": ack_id,
            "promise_id": promise_id,
            "revision": revision,
            "status": status
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Acknowledgement creation failed: {error}"
        )

    finally:
        connection.close()


@app.get("/api/promise-dates")
def get_promise_dates(
    po_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500)
):
    connection = get_connection()

    try:
        sql = """
            SELECT
                d.*,
                a.po_id,
                a.po_line_id,
                a.revision AS acknowledgement_revision,
                a.accepted_qty,
                a.rejected_qty,
                a.status AS acknowledgement_status
            FROM promise_dates d
            JOIN acknowledgements a ON a.ack_id = d.ack_id
            WHERE 1 = 1
        """
        params = []

        if po_id:
            sql += " AND a.po_id = ?"
            params.append(po_id)

        sql += " ORDER BY d.created_at DESC LIMIT ?"
        params.append(limit)

        rows = connection.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    finally:
        connection.close()


# ============================================================
# PHASE 2B: SUPPLIER CHANGE REQUESTS AND PLANNER APPROVALS
# ============================================================

class ChangeRequestCreate(BaseModel):
    po_id: str
    po_line_id: str
    new_qty: float | None = Field(default=None, gt=0)
    new_price: float | None = Field(default=None, ge=0)
    new_date: date | None = None
    reason: str | None = None


class ChangeDecision(BaseModel):
    decision: Literal["APPROVED", "REJECTED"]
    comments: str | None = None


def apply_approved_change(connection, change):
    """
    Apply an approved change to the PO and inventory plan.
    Recalculate production statuses for linked production orders.
    """

    connection.execute(
        """
        UPDATE po_lines
        SET requested_qty = ?,
            unit_price = ?,
            required_date = ?
        WHERE po_line_id = ?
        """,
        (
            change["new_qty"],
            change["new_price"],
            change["new_date"],
            change["po_line_id"]
        )
    )

    plan = connection.execute(
        """
        SELECT plan_id
        FROM inventory_plans
        WHERE po_line_id = ?
        """,
        (change["po_line_id"],)
    ).fetchone()

    if plan:
        plan_id = plan["plan_id"]

        connection.execute(
            """
            UPDATE inventory_plans
            SET projected_qty = ?,
                projected_date = ?,
                last_change_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE po_line_id = ?
            """,
            (
                change["new_qty"],
                change["new_date"],
                change["change_id"],
                change["po_line_id"]
            )
        )

    else:
        plan_id = f"PLAN-{change['po_line_id']}"

        connection.execute(
            """
            INSERT INTO inventory_plans (
                plan_id, po_line_id, projected_qty,
                projected_date, last_change_id, updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                plan_id,
                change["po_line_id"],
                change["new_qty"],
                change["new_date"],
                change["change_id"]
            )
        )

    production_rows = connection.execute(
        """
        SELECT production_id, required_qty, required_date
        FROM production_orders
        WHERE plan_id = ?
        """,
        (plan_id,)
    ).fetchall()

    for production in production_rows:
        impact = schedule_impact(
            production["required_date"],
            change["new_date"],
            production["required_qty"],
            change["new_qty"]
        )

        connection.execute(
            """
            UPDATE production_orders
            SET status = ?
            WHERE production_id = ?
            """,
            (
                impact["status"],
                production["production_id"]
            )
        )

    return len(production_rows)


@app.post("/api/change-requests", status_code=201)
def create_change_request(payload: ChangeRequestCreate):

    connection = get_connection()

    try:
        line = connection.execute(
            """
            SELECT
                l.*,
                p.order_date
            FROM po_lines l
            JOIN purchase_orders p ON p.po_id = l.po_id
            WHERE l.po_line_id = ?
              AND l.po_id = ?
            """,
            (payload.po_line_id, payload.po_id)
        ).fetchone()

        if not line:
            raise HTTPException(
                status_code=404,
                detail="Purchase order line not found"
            )

        if (
            payload.new_qty is None
            and payload.new_price is None
            and payload.new_date is None
        ):
            raise HTTPException(
                status_code=400,
                detail="Provide at least one field to change"
            )

        old_qty = float(line["requested_qty"])
        old_price = float(line["unit_price"])
        old_date = line["required_date"]

        new_qty = (
            payload.new_qty
            if payload.new_qty is not None
            else old_qty
        )

        new_price = (
            payload.new_price
            if payload.new_price is not None
            else old_price
        )

        new_date = (
            payload.new_date.isoformat()
            if payload.new_date is not None
            else old_date
        )

        if new_date < line["order_date"]:
            raise HTTPException(
                status_code=400,
                detail="New delivery date cannot be before PO order date"
            )

        changed_fields = []

        if new_qty != old_qty:
            changed_fields.append("QUANTITY")

        if new_price != old_price:
            changed_fields.append("PRICE")

        if new_date != old_date:
            changed_fields.append("DATE")

        if not changed_fields:
            raise HTTPException(
                status_code=400,
                detail="No actual change detected"
            )

        change_type = (
            changed_fields[0]
            if len(changed_fields) == 1
            else "MULTIPLE"
        )

        approval_type = classify_change(
            old_qty,
            new_qty,
            old_price,
            new_price,
            old_date,
            new_date
        )

        status = (
            "AUTO_APPROVED"
            if approval_type == "AUTO_APPROVAL"
            else "PENDING"
        )

        change_id = generate_next_id(
            connection,
            "change_requests",
            "change_id",
            "CHG"
        )

        connection.execute(
            """
            INSERT INTO change_requests (
                change_id, po_id, po_line_id, change_type,
                old_qty, new_qty, old_price, new_price,
                old_date, new_date, reason, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                change_id,
                payload.po_id,
                payload.po_line_id,
                change_type,
                old_qty,
                new_qty,
                old_price,
                new_price,
                old_date,
                new_date,
                payload.reason,
                status
            )
        )

        production_updates = 0

        if status == "AUTO_APPROVED":

            change = connection.execute(
                """
                SELECT *
                FROM change_requests
                WHERE change_id = ?
                """,
                (change_id,)
            ).fetchone()

            production_updates = apply_approved_change(
                connection,
                change
            )

        else:
            approval_id = generate_next_id(
                connection,
                "approvals",
                "approval_id",
                "APR"
            )

            connection.execute(
                """
                INSERT INTO approvals (
                    approval_id, change_id,
                    approver_role, decision
                )
                VALUES (?, ?, 'PLANNER', 'PENDING')
                """,
                (approval_id, change_id)
            )

        message = (
            f"Change request {change_id} "
            f"was {status}. Type: {change_type}"
        )

        connection.execute(
            """
            INSERT INTO notifications (
                notification_id, po_id,
                recipient_role, message, status
            )
            VALUES (?, ?, ?, ?, 'UNREAD')
            """,
            (
                generate_next_id(
                    connection,
                    "notifications",
                    "notification_id",
                    "NOT"
                ),
                payload.po_id,
                "PLANNER" if status == "PENDING" else "SUPPLIER",
                message
            )
        )

        connection.execute(
            """
            INSERT INTO audit_events (
                entity_type, entity_id, event_type,
                actor, details, created_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                "CHANGE_REQUEST",
                change_id,
                status,
                "SUPPLIER",
                json.dumps({
                    "po_id": payload.po_id,
                    "po_line_id": payload.po_line_id,
                    "change_type": change_type,
                    "old_qty": old_qty,
                    "new_qty": new_qty,
                    "old_price": old_price,
                    "new_price": new_price,
                    "old_date": old_date,
                    "new_date": new_date,
                    "reason": payload.reason
                })
            )
        )

        connection.commit()

        return {
            "message": "Change request submitted successfully",
            "change_id": change_id,
            "change_type": change_type,
            "status": status,
            "production_orders_updated": production_updates
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Change request failed: {error}"
        )

    finally:
        connection.close()


@app.get("/api/change-requests")
def get_change_requests(
    po_id: str | None = None,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500)
):

    connection = get_connection()

    try:
        sql = """
            SELECT
                c.*,
                a.approval_id,
                a.approver_role,
                a.decision,
                a.comments,
                a.decided_at
            FROM change_requests c
            LEFT JOIN approvals a
                ON a.change_id = c.change_id
            WHERE 1 = 1
        """

        params = []

        if po_id:
            sql += " AND c.po_id = ?"
            params.append(po_id)

        if status:
            sql += " AND c.status = ?"
            params.append(status.upper())

        sql += " ORDER BY c.created_at DESC LIMIT ?"
        params.append(limit)

        rows = connection.execute(sql, params).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


@app.post("/api/change-requests/{change_id}/decision")
def decide_change_request(
    change_id: str,
    payload: ChangeDecision
):

    connection = get_connection()

    try:
        change = connection.execute(
            """
            SELECT *
            FROM change_requests
            WHERE change_id = ?
            """,
            (change_id,)
        ).fetchone()

        if not change:
            raise HTTPException(
                status_code=404,
                detail="Change request not found"
            )

        if change["status"] != "PENDING":
            raise HTTPException(
                status_code=400,
                detail=f"Request is already {change['status']}"
            )

        approval = connection.execute(
            """
            SELECT *
            FROM approvals
            WHERE change_id = ?
              AND decision = 'PENDING'
            """,
            (change_id,)
        ).fetchone()

        if not approval:
            raise HTTPException(
                status_code=400,
                detail="Pending planner approval not found"
            )

        production_updates = 0

        if payload.decision == "APPROVED":

            connection.execute(
                """
                UPDATE change_requests
                SET status = 'APPROVED'
                WHERE change_id = ?
                """,
                (change_id,)
            )

            updated_change = connection.execute(
                """
                SELECT *
                FROM change_requests
                WHERE change_id = ?
                """,
                (change_id,)
            ).fetchone()

            production_updates = apply_approved_change(
                connection,
                updated_change
            )

        else:
            connection.execute(
                """
                UPDATE change_requests
                SET status = 'REJECTED'
                WHERE change_id = ?
                """,
                (change_id,)
            )

        connection.execute(
            """
            UPDATE approvals
            SET decision = ?,
                comments = ?,
                decided_at = CURRENT_TIMESTAMP
            WHERE approval_id = ?
            """,
            (
                payload.decision,
                payload.comments,
                approval["approval_id"]
            )
        )

        connection.execute(
            """
            INSERT INTO audit_events (
                entity_type, entity_id, event_type,
                actor, details, created_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                "CHANGE_REQUEST",
                change_id,
                payload.decision,
                "PLANNER",
                json.dumps({
                    "comments": payload.comments,
                    "production_orders_updated": production_updates
                })
            )
        )

        connection.execute(
            """
            INSERT INTO notifications (
                notification_id, po_id,
                recipient_role, message, status
            )
            VALUES (?, ?, 'SUPPLIER', ?, 'UNREAD')
            """,
            (
                generate_next_id(
                    connection,
                    "notifications",
                    "notification_id",
                    "NOT"
                ),
                change["po_id"],
                f"Change request {change_id} was {payload.decision}"
            )
        )

        connection.commit()

        return {
            "message": f"Change request {payload.decision.lower()} successfully",
            "change_id": change_id,
            "decision": payload.decision,
            "production_orders_updated": production_updates
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Approval decision failed: {error}"
        )

    finally:
        connection.close()


@app.get("/api/anomalies")
def get_anomalies(
    severity: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500)
):
    connection = get_connection()

    try:
        anomalies = detect_anomalies(connection)

        severity_counts = {
            "CRITICAL": sum(1 for a in anomalies if a["severity"] == "CRITICAL"),
            "HIGH": sum(1 for a in anomalies if a["severity"] == "HIGH"),
            "MEDIUM": sum(1 for a in anomalies if a["severity"] == "MEDIUM")
        }

        filtered = anomalies

        if severity:
            filtered = [
                a for a in anomalies
                if a["severity"] == severity.upper()
            ]

        return {
            "total_detected": len(anomalies),
            "severity_counts": severity_counts,
            "returned": min(len(filtered), limit),
            "anomalies": filtered[:limit]
        }

    finally:
        connection.close()


@app.get("/api/audit-events")
def get_audit_events(
    limit: int = Query(default=8, ge=1, le=100)
):
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT event_id, entity_type, entity_id,
                   event_type, actor, details, created_at
            FROM audit_events
            ORDER BY event_id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


@app.get("/api/audit-events")
def get_audit_events(
    limit: int = Query(default=8, ge=1, le=100)
):
    connection = get_connection()

    try:
        rows = connection.execute(
            """
            SELECT event_id, entity_type, entity_id,
                   event_type, actor, details, created_at
            FROM audit_events
            ORDER BY event_id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()

@app.get("/api/suppliers")
def get_suppliers(
    limit: int = Query(default=100, ge=1, le=500)
):
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT supplier_id, supplier_name, email,
                   contact_number, status
            FROM suppliers
            ORDER BY supplier_name
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


@app.get("/api/approvals")
def get_approvals(
    limit: int = Query(default=100, ge=1, le=500)
):
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT a.approval_id, a.change_id, a.approver_role,
                   a.decision, a.comments, a.decided_at,
                   c.po_id, c.po_line_id, c.change_type,
                   c.old_qty, c.new_qty, c.old_date, c.new_date,
                   c.reason, c.status AS change_status
            FROM approvals a
            LEFT JOIN change_requests c
                ON a.change_id = c.change_id
            ORDER BY a.approval_id DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


@app.get("/api/inventory-plans")
def get_inventory_plans(
    limit: int = Query(default=100, ge=1, le=500)
):
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT ip.plan_id, ip.po_line_id, pl.po_id,
                   po.supplier_id, s.supplier_name,
                   pl.item_code, pl.description,
                   ip.projected_qty, ip.projected_date,
                   ip.last_change_id, ip.updated_at
            FROM inventory_plans ip
            LEFT JOIN po_lines pl
                ON ip.po_line_id = pl.po_line_id
            LEFT JOIN purchase_orders po
                ON pl.po_id = po.po_id
            LEFT JOIN suppliers s
                ON po.supplier_id = s.supplier_id
            ORDER BY ip.updated_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()


@app.get("/api/production-orders")
def get_production_orders(
    limit: int = Query(default=100, ge=1, le=500)
):
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT p.production_id, p.plan_id,
                   ip.po_line_id, pl.po_id,
                   s.supplier_name,
                   p.required_qty, p.required_date, p.status,
                   ip.projected_qty, ip.projected_date
            FROM production_orders p
            LEFT JOIN inventory_plans ip
                ON p.plan_id = ip.plan_id
            LEFT JOIN po_lines pl
                ON ip.po_line_id = pl.po_line_id
            LEFT JOIN purchase_orders po
                ON pl.po_id = po.po_id
            LEFT JOIN suppliers s
                ON po.supplier_id = s.supplier_id
            ORDER BY p.production_id
            LIMIT ?
            """,
            (limit,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        connection.close()
