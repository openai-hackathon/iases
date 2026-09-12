"""Durable epoch allocation separate from the active lease row."""
import sqlite3
def connect(path):
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE IF NOT EXISTS epoch (id INTEGER PRIMARY KEY CHECK(id=1), value INTEGER);
        INSERT OR IGNORE INTO epoch VALUES (1, 0);
        CREATE TABLE IF NOT EXISTS lease (id INTEGER PRIMARY KEY CHECK(id=1), owner TEXT, token INTEGER, expires INTEGER);
        CREATE TABLE IF NOT EXISTS output (id INTEGER PRIMARY KEY CHECK(id=1), value TEXT);
        INSERT OR IGNORE INTO output VALUES (1, NULL);
    """)
    return connection
def allocate(connection):
    token = (connection.execute("SELECT COALESCE(MAX(token),0) FROM lease").fetchone()[0]) + 1
    connection.execute("UPDATE epoch SET value=? WHERE id=1", (token,))
    return token
