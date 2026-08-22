from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import Flask, jsonify, request

import os
import database

PRESSURE_TREND_WINDOW_HOURS = 3
PRESSURE_TREND_MINIMUM_SPAN_HOURS = 2
PRESSURE_TREND_THRESHOLD_HPA = 0.5

STATION_NAME = os.getenv("STATION_NAME", "Backyard Weather Station")

STATION_TIMEZONE = os.getenv("STATION_TIMEZONE", "America/Chicago")

station_tz = ZoneInfo(STATION_TIMEZONE)

app = Flask(__name__, static_folder="../Dashboard", static_url_path="")
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # Disable caching for static files


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/station")
def get_station():
    return jsonify({"name": STATION_NAME, "timeZone": STATION_TIMEZONE})


@app.post("/api/readings")
def add_reading():
    """Validate and store a weather station reading."""

    data = request.get_json()

    if data is None:
        return jsonify({"error": "JSON body is required"}), 400

    try:
        temperature_f = float(data["temperatureF"])
        humidity = float(data["humidity"])
        pressure_hpa = float(data["pressureHpa"])
    except KeyError as e:
        return jsonify({"error": f"Missing field: {e.args[0]}"}), 400
    except (TypeError, ValueError):
        return (
            jsonify({"error": "Temperature, humidity, and pressure must be numbers"}),
            400,
        )

    timestamp = format_utc_timestamp(datetime.now(timezone.utc))

    print(
        f"Received reading: {timestamp} - Temp: {temperature_f} F, Humidity: {humidity} %, Pressure: {pressure_hpa} hPa"
    )

    database.save_reading(timestamp, temperature_f, humidity, pressure_hpa)

    return jsonify({"status": "ok"}), 201


@app.get("/api/weather/dashboard")
def get_dashboard():
    """
    Return the latest reading and statistics associated with its local day.

    Statistics are based on the date of the latest reading rather than the
    current time so historical data remains available when the station is offline.
    """

    current = database.get_latest_reading()

    if current is None:
        return jsonify({"current": None, "stats": None})

    current_utc = datetime.fromisoformat(current["timestamp"])

    local_date, day_start_utc, day_end_utc = get_local_day_utc_range(current_utc)

    stats = database.get_stats_between(
        format_utc_timestamp(day_start_utc), format_utc_timestamp(day_end_utc)
    )

    pressure_start_utc = current_utc - timedelta(hours=PRESSURE_TREND_WINDOW_HOURS)

    pressure_rows = database.get_pressure_history_between(
        format_utc_timestamp(pressure_start_utc), format_utc_timestamp(current_utc)
    )

    pressure_trend = calculate_pressure_trend(pressure_rows)

    return jsonify(
        {
            "current": reading_to_json(current),
            "stats": {
                "date": local_date.isoformat(),
                "highTemperatureF": stats["high_temperature_f"],
                "lowTemperatureF": stats["low_temperature_f"],
                "highHumidity": stats["high_humidity"],
                "lowHumidity": stats["low_humidity"],
                "pressureTrend": pressure_trend,
            },
        }
    )


@app.get("/api/weather/history")
def get_history():
    """
    Return weather history ending at the latest available reading.

    The range may be 24 hours or 7 days.
    """

    range_value = request.args.get("range", "24h")

    if range_value == "24h":
        range_length = timedelta(hours=24)
    elif range_value == "7d":
        range_length = timedelta(days=7)
    else:
        return jsonify({"error": "range must be 24h or 7d"}), 400

    latest = database.get_latest_reading()

    if latest is None:
        return jsonify({"range": range_value, "readings": []})

    end_utc = datetime.fromisoformat(latest["timestamp"])

    start_utc = end_utc - range_length

    rows = database.get_history_between(
        format_utc_timestamp(start_utc), format_utc_timestamp(end_utc)
    )

    readings = [reading_to_json(row) for row in rows]

    return jsonify({"range": range_value, "readings": readings})


def format_utc_timestamp(value):
    """Format a datetime as an ISO 8601 UTC timestamp ending in Z."""

    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def get_local_day_utc_range(utc_datetime):
    """
    Return the local date and UTC boundaries for the station's local day.

    The UTC interval includes the start of the local day and excludes
    the start of the next local day.
    """

    local_datetime = utc_datetime.astimezone(station_tz)
    local_date = local_datetime.date()

    local_start = datetime(
        local_date.year, local_date.month, local_date.day, tzinfo=station_tz
    )

    next_local_date = local_date + timedelta(days=1)

    local_end = datetime(
        next_local_date.year,
        next_local_date.month,
        next_local_date.day,
        tzinfo=station_tz,
    )

    utc_start = local_start.astimezone(timezone.utc)
    utc_end = local_end.astimezone(timezone.utc)

    return local_date, utc_start, utc_end


def calculate_pressure_trend(pressure_rows):
    """
    Calculate the pressure trend from a sequence of pressure readings.

    Return rising, falling, or steady when the readings span the minimum
    required time. Return None when there is insufficient data.
    """

    if len(pressure_rows) < 2:
        return None

    first_row = pressure_rows[0]
    last_row = pressure_rows[-1]

    first_time = datetime.fromisoformat(first_row["timestamp"])
    last_time = datetime.fromisoformat(last_row["timestamp"])

    if last_time - first_time < timedelta(hours=PRESSURE_TREND_MINIMUM_SPAN_HOURS):
        return None

    pressure_change = last_row["pressure_hpa"] - first_row["pressure_hpa"]

    if pressure_change > PRESSURE_TREND_THRESHOLD_HPA:
        return "rising"

    if pressure_change < -PRESSURE_TREND_THRESHOLD_HPA:
        return "falling"

    return "steady"


def reading_to_json(row):
    """Convert a database reading to the API response format."""

    return {
        "timestamp": row["timestamp"],
        "temperatureF": row["temperature_f"],
        "humidity": row["humidity"],
        "pressureHpa": row["pressure_hpa"],
    }


if __name__ == "__main__":
    database.init_database()
    app.run(host="0.0.0.0", port=5000, debug=True)
