from datetime import datetime, timedelta 
from flask import Flask, jsonify, request
import database
from database import get_connection, init_database

app = Flask(__name__, static_folder="../Dashboard", static_url_path="")

app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # Disable caching for static files

@app.get("/")
def index():
    return app.send_static_file("index.html")

@app.post("/api/readings")
def add_reading():
    data = request.get_json()

    if data is None:
        return jsonify({"error": "JSON body is required"}), 400

    try:
        temperature_f = float(data["temperatureF"])
        humidity = float(data["humidity"])
        pressure_hpa = float(data["pressureHpa"])
    except KeyError as e:
        return jsonify({"error": f"Missing field: {e.args[0]}"}), 400
    except ValueError:
        return jsonify({"error": "Temperature, humidity, and pressure must be numbers"}), 400

    timestamp = datetime.now().isoformat(timespec="seconds")

    print(f"Received reading: {timestamp} - Temp: {temperature_f} F, Humidity: {humidity} %, Pressure: {pressure_hpa} hPa")

    database.insert_reading(timestamp, temperature_f, humidity, pressure_hpa)

    return jsonify({"status": "ok"}), 201


@app.get("/api/weather/dashboard")
def get_dashboard():
    current = database.get_current_reading()

    if current is None:
        return jsonify({
            "current": None,
            "stats": None
        })

    today = datetime.now().date().isoformat()
    stats = database.get_today_stats(today)

    pressure_rows = database.get_recent_pressures()

    pressure_trend = "steady"

    if len(pressure_rows) == 2:
        latest = pressure_rows[0]["pressure_hpa"]
        previous = pressure_rows[1]["pressure_hpa"]

        if latest > previous:
            pressure_trend = "rising"
        elif latest < previous:
            pressure_trend = "falling"

    return jsonify({
        "current": {
            "temperatureF": current["temperature_f"],
            "humidity": current["humidity"],
            "pressureHpa": current["pressure_hpa"],
            "timestamp": current["timestamp"]
        },
        "stats": {
            "highTemperatureF": stats["high_temperature_f"],
            "lowTemperatureF": stats["low_temperature_f"],
            "highHumidity": stats["high_humidity"],
            "lowHumidity": stats["low_humidity"],
            "pressureTrend": pressure_trend
        }
    })

@app.get("/api/weather/history")
def get_history():
    range_value = request.args.get("range", "24h")

    if range_value == "24h":
        start_time = datetime.now() - timedelta(hours=24)
    elif range_value == "7d":
        start_time = datetime.now() - timedelta(days=7)
    else:
        return jsonify({"error": "range must be 24h or 7d"}), 400

    rows = database.get_history_since(
        start_time.isoformat(timespec="seconds")
    )

    readings = []

    for row in rows:
        readings.append({
            "timestamp": row["timestamp"],
            "temperatureF": row["temperature_f"],
            "humidity": row["humidity"],
            "pressureHpa": row["pressure_hpa"]
        })

    return jsonify({
        "range": range_value,
        "readings": readings
    })


if __name__ == "__main__":
    init_database()
    app.run(host="0.0.0.0", port=5000, debug=True)