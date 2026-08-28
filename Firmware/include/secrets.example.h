#pragma once

// Set to 1 to use the local development server.
// Set to 0 to use the production server.
#define USE_LOCAL_SERVER 1

// Wi-Fi credentials
const char *WIFI_SSID = "your-wifi-name";
const char *WIFI_PASSWORD = "your-wifi-password";

#if USE_LOCAL_SERVER

// Local development server
const char *SERVER_URL =
    "http://192.168.1.100:5000/api/readings";

const char *API_KEY =
    "your-development-api-key";

#else

// Production server
const char *SERVER_URL =
    "https://your-server.example.com/api/readings";

const char *API_KEY =
    "your-production-api-key";

#endif