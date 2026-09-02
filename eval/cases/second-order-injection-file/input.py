import sqlite3


def register(conn, display_name):
    conn.execute("INSERT INTO users (display_name) VALUES (?)", (display_name,))
    conn.commit()


def usage_report(conn):
    """Per-user activity totals for the admin dashboard."""
    rows = conn.execute("SELECT display_name FROM users").fetchall()
    report = []
    for (name,) in rows:
        query = "SELECT COUNT(*) FROM events WHERE actor = '" + name + "'"
        report.append((name, conn.execute(query).fetchone()[0]))
    return report
