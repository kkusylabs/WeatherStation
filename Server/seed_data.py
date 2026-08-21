from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import math
import random
import database

LOCAL_TZ = ZoneInfo("America/Chicago")


def generate_temperature(timestamp):
    """Generate a simulated temperature for the given local time."""

    hour = timestamp.hour + timestamp.minute / 60

    daily_cycle = math.sin((hour - 6) * math.pi / 12)

    base_temp = 72
    daily_swing = 12
    noise = random.uniform(-1.5, 1.5)

    return round(base_temp + daily_swing * daily_cycle + noise, 1)


def generate_humidity(temperature_f):
    """Generate simulated humidity based on temperature."""

    base_humidity = 55

    temp_effect = (72 - temperature_f) * 0.8
    noise = random.uniform(-4, 4)

    humidity = base_humidity + temp_effect + noise

    humidity = max(20, min(95, humidity))

    return round(humidity, 1)


def generate_pressure(timestamp):
    """Generate simulated atmospheric pressure for the given local time."""

    day_number = timestamp.timetuple().tm_yday

    weather_pattern = math.sin(day_number * math.pi / 5)

    base_pressure = 1013
    swing = 6
    noise = random.uniform(-0.3, 0.3)

    return round(base_pressure + swing * weather_pattern + noise, 2)


def seed_database(days=30, interval_minutes=5):
    """Generate and store simulated weather readings for testing."""

    database.init_database()

    # Generate timestamps in UTC
    start_time = datetime.now(timezone.utc) - timedelta(days=days)

    total_readings = int((days * 24 * 60) / interval_minutes)

    for i in range(total_readings):
        # This timestamp remains UTC
        timestamp = start_time + timedelta(minutes=i * interval_minutes)

        # Convert to local time for weather calculations
        local_timestamp = timestamp.astimezone(LOCAL_TZ)

        temperature_f = generate_temperature(local_timestamp)

        humidity = generate_humidity(temperature_f)

        pressure_hpa = generate_pressure(local_timestamp)

        # Store timestamp as ISO 8601 UTC with Z
        timestamp_utc = format_utc_timestamp(timestamp)

        database.save_reading(timestamp_utc, temperature_f, humidity, pressure_hpa)

    print(f"Inserted {total_readings} fake readings.")


def format_utc_timestamp(value):
    """Format a datetime as an ISO 8601 UTC timestamp ending in Z."""

    return (
        value.astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


if __name__ == "__main__":
    seed_database()
