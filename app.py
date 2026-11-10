import json
import sqlite3
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from db import connect, ROOT
from business_rules import detect_anomalies

STATIC_DIR = ROOT / "static"


class SupplySyncHandler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length) or b"{}")

    def do_GET(self):
        path = urlparse(self.path).path

        if path.startswith("/api/"):
            self.handle_api_get(path)
            return

        if path == "/":
            path = "/index.html"

        file_path = (STATIC_DIR / path.lstrip("/")).resolve()

        if not str(file_path).startswith(str(STATIC_DIR.resolve())):
            self.send_error(403)
            return

        if not file_path.is_file():
            self.send_error(404)
            return

        content = file_path.read_bytes()
        content_type = {
            ".html": "text/html",
            ".css": "text/css",
            ".js": "application/javascript"
        }.get(file_path.suffix, "application/octet-stream")

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def handle_api_get(self, path):
        connection = connect()

        try:
            if path == "/api/health":
                self.send_json({"status": "healthy", "application": "SupplySync"})
                return

            if path == "/api/summary":
                tables = [
                    "suppliers",
                    "purchase_orders",
                    "po_lines",
                    "acknowledgements",
                    "change_requests",
                    "approvals",
                    "notifications",
                    "audit_events"
                ]

                counts = {}

                for table in tables:
                    counts[table] = connection.execute(
                        f"SELECT COUNT(*) FROM {table}"
                    ).fetchone()[0]

                pending = connection.execute("""
                    SELECT COUNT(*) FROM change_requests
                    WHERE status = 'PENDING'
                """).fetchone()[0]

                approved = connection.execute("""
                    SELECT COUNT(*) FROM change_requests
                    WHERE status = 'APPROVED'
                """).fetchone()[0]

                rejected = connection.execute("""
                    SELECT COUNT(*) FROM change_requests
                    WHERE status = 'REJECTED'
                """).fetchone()[0]

                self.send_json({
                    "counts": counts,
                    "pending_changes": pending,
                    "approved_changes": approved,
                    "rejected_changes": rejected
                })
                return

            if path == "/api/changes":
                rows = connection.execute("""
                    SELECT
                        cr.change_id,
                        cr.po_id,
                        cr.po_line_id,
                        cr.change_type,
                        cr.old_qty,
                        cr.new_qty,
                        cr.old_price,
                        cr.new_price,
                        cr.old_date,
                        cr.new_date,
                        cr.reason,
                        cr.status,
                        cr.created_at,
                        p.supplier_id,
                        s.supplier_name
                    FROM change_requests cr
                    JOIN purchase_orders p ON p.po_id = cr.po_id
                    JOIN suppliers s ON s.supplier_id = p.supplier_id
                    ORDER BY
                        CASE cr.status WHEN 'PENDING' THEN 0 ELSE 1 END,
                        cr.created_at DESC
                    LIMIT 100
                """).fetchall()

                self.send_json([dict(row) for row in rows])
                return

            if path == "/api/anomalies":
                self.send_json(detect_anomalies(connection))
                return

            if path == "/api/orders":
                rows = connection.execute("""
                    SELECT
                        p.po_id,
                        p.order_date,
                        p.status,
                        s.supplier_name,
                        COUNT(l.po_line_id) AS line_count,
                        SUM(l.requested_qty) AS requested_quantity
                    FROM purchase_orders p
                    JOIN suppliers s ON s.supplier_id = p.supplier_id
                    JOIN po_lines l ON l.po_id = p.po_id
                    GROUP BY p.po_id
                    ORDER BY p.order_date DESC
                    LIMIT 30
                """).fetchall()

                self.send_json([dict(row) for row in rows])
                return

            if path == "/api/audit":
                rows = connection.execute("""
                    SELECT *
                    FROM audit_events
                    ORDER BY created_at DESC
                    LIMIT 30
                """).fetchall()

                self.send_json([dict(row) for row in rows])
                return

            self.send_json({"error": "API endpoint not found"}, 404)

        except Exception as error:
            self.send_json({"error": str(error)}, 500)

        finally:
            connection.close()

    def do_POST(self):
        path = urlparse(self.path).path

        prefix = "/api/changes/"
        suffix = "/decision"

        if not (path.startswith(prefix) and path.endswith(suffix)):
            self.send_json({"error": "Endpoint not found"}, 404)
            return

        change_id = path[len(prefix):-len(suffix)].strip("/")

        if not change_id:
            self.send_json({"error": "Missing change ID"}, 400)
            return

        try:
            payload = self.read_json()
            decision = payload.get("decision", "").upper()

            if decision not in ("APPROVED", "REJECTED"):
                self.send_json({
                    "error": "Decision must be APPROVED or REJECTED"
                }, 400)
                return

            connection = connect()

            try:
                change = connection.execute("""
                    SELECT * FROM change_requests
                    WHERE change_id = ?
                """, (change_id,)).fetchone()

                if not change:
                    self.send_json({"error": "Change request not found"}, 404)
                    return

                if change["status"] != "PENDING":
                    self.send_json({
                        "error": "This change request has already been processed"
                    }, 409)
                    return

                now = datetime.now().isoformat(timespec="seconds")

                connection.execute("""
                    UPDATE change_requests
                    SET status = ?
                    WHERE change_id = ?
                """, (decision, change_id))

                # Update inventory only after approval.
                if decision == "APPROVED":
                    connection.execute("""
                        UPDATE inventory_plans
                        SET
                            projected_qty = ?,
                            projected_date = ?,
                            last_change_id = ?,
                            updated_at = ?
                        WHERE po_line_id = ?
                    """, (
                        change["new_qty"],
                        change["new_date"],
                        change_id,
                        now,
                        change["po_line_id"]
                    ))

                # Update the generated approval record, if one exists.
                approval = connection.execute("""
                    SELECT approval_id
                    FROM approvals
                    WHERE change_id = ?
                    LIMIT 1
                """, (change_id,)).fetchone()

                if approval:
                    connection.execute("""
                        UPDATE approvals
                        SET decision = ?, decided_at = ?
                        WHERE approval_id = ?
                    """, (decision, now, approval["approval_id"]))
                else:
                    connection.execute("""
                        INSERT INTO approvals
                        (change_id, approver_role, decision, comments, decided_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        change_id,
                        "PLANNER",
                        decision,
                        "Decision recorded in SupplySync dashboard",
                        now
                    ))

                connection.execute("""
                    INSERT INTO audit_events
                    (entity_type, entity_id, event_type, actor, details, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    "CHANGE_REQUEST",
                    change_id,
                    decision,
                    "PLANNER",
                    json.dumps({"decision": decision}),
                    now
                ))

                connection.execute("""
                    INSERT INTO notifications
                    (po_id, recipient_role, message, status, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    change["po_id"],
                    "PLANNER",
                    f"Change {change_id} was {decision.lower()}",
                    "SENT",
                    now
                ))

                connection.commit()

                self.send_json({
                    "success": True,
                    "change_id": change_id,
                    "decision": decision,
                    "inventory_updated": decision == "APPROVED"
                })

            except Exception:
                connection.rollback()
                raise

            finally:
                connection.close()

        except Exception as error:
            self.send_json({"error": str(error)}, 500)


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 8000), SupplySyncHandler)

    print("SupplySync is running!")
    print("Dashboard: http://127.0.0.1:8000")
    print("API health: http://127.0.0.1:8000/api/health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSupplySync server stopped.")
        server.server_close()