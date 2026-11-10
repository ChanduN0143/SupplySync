import sqlite3
from pathlib import Path

db = Path("data/supplysync.db")
con = sqlite3.connect(db)

print("\nDATABASE TABLES AND RECORD COUNTS\n")

tables = con.execute("""
    SELECT name FROM sqlite_master
    WHERE type='table' AND name NOT LIKE 'sqlite_%'
    ORDER BY name
""").fetchall()

for (table,) in tables:
    print(f"\n--- {table} ---")

    columns = con.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    for column in columns:
        print(
            f"Column: {column[1]}, "
            f"Type: {column[2]}, "
            f"Primary key: {column[5]}"
        )

    count = con.execute(
        f'SELECT COUNT(*) FROM "{table}"'
    ).fetchone()[0]

    print("Records:", count)

print("\nFOREIGN KEY VIOLATIONS")
print(con.execute("PRAGMA foreign_key_check").fetchall())

con.close()
