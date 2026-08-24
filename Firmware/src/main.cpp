/**
 * @file main.cpp
 * @brief ESP32 weather station firmware.
 *
 * Reads temperature, humidity, and atmospheric pressure from a BME280
 * sensor, displays current readings and status information on an OLED,
 * and periodically uploads valid readings to the weather server.
 */

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_BME280.h>
#include <U8g2lib.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "secrets.h"

/**
 * Display a short message on the OLED.
 *
 * @param message Text to display.
 */
void showMessage(const char *message);

/**
 * Perform one complete weather update cycle.
 *
 * Reads the sensor, ensures Wi-Fi is connected, uploads a valid reading,
 * and refreshes the OLED display.
 */
void updateWeather();

/**
 * Read and validate the BME280 sensor.
 *
 * Attempts to reinitialize the sensor if it was previously unavailable.
 * Valid readings are stored in the current weather variables.
 */
void readSensor();

/**
 * Check whether sensor readings are finite and within reasonable limits.
 *
 * @param tempF Temperature in degrees Fahrenheit.
 * @param hum Relative humidity as a percentage.
 * @param pressure Atmospheric pressure in hPa.
 * @return true if all readings are valid; otherwise false.
 */
bool readingValid(float tempF, float hum, float pressure);

/**
 * Ensure the ESP32 is connected to Wi-Fi.
 *
 * If disconnected, attempts to connect for up to 10 seconds. A failed
 * connection will be retried during the next weather update cycle.
 */
void ensureWiFiConnected();

/**
 * Send the current weather reading to the server as JSON.
 *
 * Updates serverOk based on whether the HTTP request succeeds.
 */
void sendToServer();

/**
 * Display current weather readings and system status on the OLED.
 */
void updateDisplay();

Adafruit_BME280 bme;

U8G2_SH1106_128X64_NONAME_F_HW_I2C oled(
    U8G2_R0,
    U8X8_PIN_NONE);

const unsigned long READ_INTERVAL_MS = 5UL * 60UL * 1000UL; // 5 minutes
unsigned long lastReadTime = 0;

float temperatureF = 0;
float humidity = 0;
float pressureHPa = 0;

bool sensorOk = false;
bool wifiOk = false;
bool serverOk = false;

/**
 * Initialize serial output, I2C, OLED, Wi-Fi, and the first weather update.
 */
void setup()
{
  Serial.begin(9600);
  Serial.println("Booting...");

  Wire.begin();

  oled.begin();
  showMessage("Starting...");

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);

  updateWeather();

  lastReadTime = millis();
}

/**
 * Run the periodic weather update loop.
 */
void loop()
{
  unsigned long now = millis();

  if (now - lastReadTime >= READ_INTERVAL_MS)
  {
    lastReadTime = now;

    updateWeather();
  }
}

void showMessage(const char *message)
{
  oled.clearBuffer();
  oled.setFont(u8g2_font_6x12_tf);
  oled.drawStr(0, 12, message);
  oled.sendBuffer();
}

void updateWeather()
{
  readSensor();
  ensureWiFiConnected();

  if (sensorOk && wifiOk)
  {
    sendToServer();
  }
  else
  {
    serverOk = false;
  }

  updateDisplay();
}

void readSensor()
{
  if (!sensorOk)
  {
    // Try to recover if the sensor was unavailable earlier
    sensorOk = bme.begin(0x76);
  }

  if (!sensorOk)
  {
    Serial.println("Sensor unavailable");
    return;
  }

  float temperatureC = bme.readTemperature();
  float newHumidity = bme.readHumidity();
  float newPressureHPa = bme.readPressure() / 100.0F;

  float newTemperatureF = temperatureC * 9.0 / 5.0 + 32.0;

  if (!readingValid(newTemperatureF, newHumidity, newPressureHPa))
  {
    sensorOk = false;
    Serial.println("Invalid sensor reading");
    return;
  }

  temperatureF = newTemperatureF;
  humidity = newHumidity;
  pressureHPa = newPressureHPa;
  sensorOk = true;

  Serial.println("Sensor reading:");
  Serial.print("Temp: ");
  Serial.print(temperatureF);
  Serial.println(" F");

  Serial.print("Humidity: ");
  Serial.print(humidity);
  Serial.println(" %");

  Serial.print("Pressure: ");
  Serial.print(pressureHPa);
  Serial.println(" hPa");
}

bool readingValid(float tempF, float hum, float pressure)
{
  if (isnan(tempF) || isnan(hum) || isnan(pressure))
  {
    return false;
  }

  return hum >= 0 &&
         hum <= 100 &&
         pressure > 800 &&
         pressure < 1200 &&
         tempF > -40 &&
         tempF < 140;
}

void ensureWiFiConnected()
{
  if (WiFi.status() == WL_CONNECTED)
  {
    wifiOk = true;
    return;
  }

  wifiOk = false;

  Serial.println("Connecting to WiFi...");

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long startAttempt = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - startAttempt < 10000)
  {
    delay(500);
    Serial.print(".");
  }

  Serial.println();

  if (WiFi.status() == WL_CONNECTED)
  {
    wifiOk = true;

    Serial.println("WiFi connected");
    Serial.print("ESP32 IP: ");
    Serial.println(WiFi.localIP());
  }
  else
  {
    wifiOk = false;
    serverOk = false;

    Serial.println("WiFi connection failed");
  }
}

void sendToServer()
{
  if (WiFi.status() != WL_CONNECTED)
  {
    wifiOk = false;
    serverOk = false;
    Serial.println("Cannot upload: WiFi disconnected");
    return;
  }

  HTTPClient http;

  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(5000);

  char json[128];

  // Use a fixed-size buffer to avoid repeated dynamic String allocation.
  int length = snprintf(
      json,
      sizeof(json),
      "{\"temperatureF\":%.1f,\"humidity\":%.1f,\"pressureHpa\":%.1f}",
      temperatureF,
      humidity,
      pressureHPa);

  if (length < 0 || length >= sizeof(json))
  {
    serverOk = false;
    Serial.println("Failed to create JSON");
    http.end();
    return;
  }

  int responseCode = http.POST(
      reinterpret_cast<uint8_t *>(json),
      length);

  if (responseCode >= 200 && responseCode < 300)
  {
    serverOk = true;
    Serial.print("Upload OK: ");
    Serial.println(responseCode);
  }
  else
  {
    serverOk = false;
    Serial.print("Upload failed: ");
    Serial.println(responseCode);
  }

  http.end();
}

void updateDisplay()
{
  oled.clearBuffer();
  oled.setFont(u8g2_font_6x12_tf);

  oled.drawStr(0, 12, "Weather Station");

  if (sensorOk)
  {
    oled.setCursor(0, 28);
    oled.print("Temperature: ");
    oled.print(temperatureF, 1);
    oled.print(" F");

    oled.setCursor(0, 40);
    oled.print("Humidity: ");
    oled.print(humidity, 1);
    oled.print(" %");

    oled.setCursor(0, 52);
    oled.print("Pressure:");
    oled.print(pressureHPa, 0);
    oled.print(" hPa");
  }
  else
  {
    oled.drawStr(0, 32, "Sensor: FAIL");
  }

  oled.setCursor(0, 64);
  oled.print("W:");
  oled.print(wifiOk ? "OK " : "BAD ");

  oled.print("S:");
  oled.print(serverOk ? "OK" : "BAD");

  oled.sendBuffer();
}