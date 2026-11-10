import unittest
from db import connect


class TestSupplySyncDatabase(unittest.TestCase):

    def test_required_tables_exist(self):
        connection = connect()
        try:
            rows = connection.execute("""
                SELECT name FROM sqlite_master WHERE type = 'table'
            """).fetchall()
            tables = {row["name"] for row in rows}

            required = {
                "suppliers", "purchase_orders", "po_lines",
                "acknowledgements", "promise_dates", "change_requests",
                "approvals", "inventory_plans", "production_orders",
                "notifications", "audit_events"
            }
            self.assertTrue(required.issubset(tables))
        finally:
            connection.close()

    def test_generated_data_exists(self):
        connection = connect()
        try:
            po_count = connection.execute(
                "SELECT COUNT(*) FROM purchase_orders"
            ).fetchone()[0]

            ack_count = connection.execute(
                "SELECT COUNT(*) FROM acknowledgements"
            ).fetchone()[0]

            change_count = connection.execute(
                "SELECT COUNT(*) FROM change_requests"
            ).fetchone()[0]

            self.assertGreaterEqual(po_count, 10000)
            self.assertGreaterEqual(ack_count, 10000)
            self.assertGreaterEqual(change_count, 5000)
        finally:
            connection.close()

    def test_foreign_keys(self):
        connection = connect()
        try:
            violations = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
            self.assertEqual(len(violations), 0)
        finally:
            connection.close()


if __name__ == "__main__":
    unittest.main()
