let currentRange = "24h";

let temperatureChart;
let humidityChart;
let pressureChart;


window.addEventListener('load', () => {
    createCharts();

    loadDashboard();
    loadHistory(currentRange);

    document.getElementById("range24h").addEventListener("click", () => {
        changeRange("24h");
    });

    document.getElementById("range7d").addEventListener("click", () => {
        changeRange("7d");
    });

    setInterval(loadDashboard, 60000);

    setInterval(() => {
        loadHistory(currentRange);
    }, 300000);

});

function createCharts() {
  temperatureChart = createLineChart("temperatureChart", "Temperature (°F)");
  humidityChart = createLineChart("humidityChart", "Humidity (%)");
  pressureChart = createLineChart("pressureChart", "Pressure (hPa)");
}

function createLineChart(canvasId, label) {
  const canvas = document.getElementById(canvasId);

  return new Chart(canvas, {
    type: "line",
    data: {
      labels: [],
      datasets: [
        {
          label: label,
          data: [],
          tension: 0.25,
          pointRadius: 2
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      scales: {
        x: {
          ticks: {
            maxTicksLimit: 8
          }
        },
        y: {
          beginAtZero: false
        }
      }
    }
  });
}


async function loadDashboard() {
  try {
    const response = await fetch("/api/weather/dashboard");

    if (!response.ok) {
      throw new Error("Failed to load dashboard");
    }

    const data = await response.json();

    if (data.current) {
      updateCurrentConditions(data.current);
    }

    if (data.stats) {
      updateDailyStats(data.stats);
    }
  } catch (error) {
    console.error(error);
  }
}


async function loadHistory(range) {
  try {
    const response = await fetch(`/api/weather/history?range=${range}`);

    if (!response.ok) {
      throw new Error("Failed to load history");
    }

    const data = await response.json();

    updateGraphs(data.readings);
  } catch (error) {
    console.error(error);
  }
}


function updateCurrentConditions(current) {
  document.getElementById("temperatureValue").textContent =
    `${current.temperatureF.toFixed(1)}°F`;

  document.getElementById("humidityValue").textContent =
    `${current.humidity.toFixed(0)}%`;

  document.getElementById("pressureValue").textContent =
    `${current.pressureHpa.toFixed(1)} hPa`;

  document.getElementById("lastUpdated").textContent =
    formatLastUpdated(current.timestamp);
}

function updateDailyStats(stats) {
  document.getElementById("highTemp").textContent =
    `${stats.highTemperatureF.toFixed(1)}°F`;

  document.getElementById("lowTemp").textContent =
    `${stats.lowTemperatureF.toFixed(1)}°F`;

  document.getElementById("highHumidity").textContent =
    `${stats.highHumidity.toFixed(0)}%`;

  document.getElementById("lowHumidity").textContent =
    `${stats.lowHumidity.toFixed(0)}%`;

  document.getElementById("pressureTrend").textContent =
    capitalize(stats.pressureTrend);
}


function updateGraphs(readings) {
  const labels = readings.map(reading => formatTimestamp(reading.timestamp));

  updateChart(
    temperatureChart,
    labels,
    readings.map(reading => reading.temperatureF)
  );

  updateChart(
    humidityChart,
    labels,
    readings.map(reading => reading.humidity)
  );

  updateChart(
    pressureChart,
    labels,
    readings.map(reading => reading.pressureHpa)
  );
}

function updateChart(chart, labels, values) {
  chart.data.labels = labels;
  chart.data.datasets[0].data = values;
  chart.update();
}

function changeRange(range) {
  currentRange = range;
  setActiveRangeButton();
  loadHistory(currentRange);
}

function setActiveRangeButton() {
  document.getElementById("range24h").classList.toggle(
    "active",
    currentRange === "24h"
  );

  document.getElementById("range7d").classList.toggle(
    "active",
    currentRange === "7d"
  );
}


function formatTimestamp(timestamp) {
  const date = new Date(timestamp);

  if (currentRange === "7d") {
    return date.toLocaleDateString([], {
      month: "short",
      day: "numeric"
    });
  }

  return date.toLocaleTimeString([], {
    hour: "numeric",
    minute: "2-digit"
  });
}

function formatLastUpdated(timestamp) {
    return new Date(timestamp).toLocaleTimeString([], {
        hour: "numeric",
        minute: "2-digit"
    });
}

function capitalize(value) {
  if (!value) {
    return "--";
  }

  return value.charAt(0).toUpperCase() + value.slice(1);
}