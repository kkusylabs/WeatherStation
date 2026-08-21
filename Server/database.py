import sqlite3
from pathlib import Path

DB_PATH = Path("weather.db")


def get_connection():
    """Return a connection to the weather database."""

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Create the readings table and timestamp index if they do not exist."""

    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                temperature_f REAL NOT NULL,
                humidity REAL NOT NULL,
                pressure_hpa REAL NOT NULL
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS
                idx_readings_timestamp
            ON readings(timestamp)
        """)


def save_reading(timestamp, temperature_f, humidity, pressure_hpa):
    """Save a weather reading to the database."""

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO readings (
                timestamp,
                temperature_f,
                humidity,
                pressure_hpa
            )
            VALUES (?, ?, ?, ?)
        """,
            (timestamp, temperature_f, humidity, pressure_hpa),
        )


def get_latest_reading():
    """Return the most recent reading, or None if no readings exist."""

    with get_connection() as conn:
        row = conn.execute("""
            SELECT *
            FROM readings
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()

    return dict(row) if row else None


def get_stats_between(start_time, end_time):
    """
    Return weather statistics for a half-open UTC time interval.

    The interval includes start_time and excludes end_time.
    """

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                MAX(temperature_f)
                    AS high_temperature_f,
                MIN(temperature_f)
                    AS low_temperature_f,
                MAX(humidity)
                    AS high_humidity,
                MIN(humidity)
                    AS low_humidity
            FROM readings
            WHERE timestamp >= ?
              AND timestamp < ?
        """,
            (start_time, end_time),
        ).fetchone()

    return dict(row)


def get_history_between(start_time, end_time):
    """
    Return readings in this inclusive UTC interval:

        start_time <= timestamp <= end_time
    """

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM readings
            WHERE timestamp >= ?
              AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (start_time, end_time),
        ).fetchall()

    return [dict(row) for row in rows]


def get_pressure_history_between(start_time, end_time):
    """
    Return pressure readings for the specified UTC time interval.

    The interval includes both start_time and end_time, and results
    are returned in chronological order.
    """

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                timestamp,
                pressure_hpa
            FROM readings
            WHERE timestamp >= ?
              AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (start_time, end_time),
        ).fetchall()

    return [dict(row) for row in rows]
