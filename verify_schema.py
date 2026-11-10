import sqlite3

connection = sqlite3.connect(":memory:")
connection.execute("PRAGMA foreign_keys = ON")

with open("database/schema.sql", "r", encoding="utf-8") as file:
    schema = file.read()

connection.executescript(schema)

print("SCHEMA CREATED SUCCESSFULLY!")

tables = connection.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
      AND name NOT LIKE 'sqlite_%'
    ORDER BY name
""").fetchall()

print("\nTables created:")
for table in tables:
    print("-", table[0])

connection.close()