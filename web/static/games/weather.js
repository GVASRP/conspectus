/* Conspectus · Погода (Open-Meteo, без API-ключей) */
(function () {
  "use strict";
  var G = window.G;
  var GEO = "https://geocoding-api.open-meteo.com/v1/search";
  var MET = "https://api.open-meteo.com/v1/forecast";
  var QUICK = [
    { name: "Москва", lat: 55.7558, lon: 37.6173 },
    { name: "Санкт-Петербург", lat: 59.9386, lon: 30.3141 },
    { name: "Сочи", lat: 43.6028, lon: 39.7342 },
    { name: "Казань", lat: 55.7887, lon: 49.1221 },
    { name: "Новосибирск", lat: 55.0084, lon: 82.9357 },
    { name: "Владивосток", lat: 43.1155, lon: 131.8855 },
  ];
  var CODES = {
    0: ["Ясно", "☀️"], 1: ["Преимущественно ясно", "🌤️"], 2: ["Переменная облачность", "⛅"],
    3: ["Пасмурно", "☁️"], 45: ["Туман", "🌫️"], 48: ["Изморозь", "🌫️"],
    51: ["Лёгкий дождь", "🌦️"], 53: ["Морось", "🌦️"], 55: ["Дождь", "🌧️"],
    56: ["Ледяной дождь", "🌧️"], 57: ["Ледяной дождь", "🌧️"],
    61: ["Небольшой дождь", "🌧️"], 63: ["Дождь", "🌧️"], 65: ["Сильный дождь", "🌧️"],
    66: ["Ледяной дождь", "🌧️"], 67: ["Ледяной дождь", "🌧️"],
    71: ["Небольшой снег", "🌨️"], 73: ["Снег", "🌨️"], 75: ["Сильный снег", "❄️"],
    77: ["Снежная крупа", "🌨️"],
    80: ["Ливень", "🌦️"], 81: ["Ливень", "🌦️"], 82: ["Сильный ливень", "⛈️"],
    85: ["Снегопад", "🌨️"], 86: ["Сильный снегопад", "🌨️"],
    95: ["Гроза", "⛈️"], 96: ["Гроза с градом", "⛈️"], 99: ["Гроза с градом", "⛈️"],
  };
  var DAYS = ["вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"];

  function weather(code, isNight) {
    var r = CODES[code] || ["Непонятно", "🌡️"];
    if (isNight && (code === 0 || code === 1 || code === 2)) r[1] = "🌙";
    return r;
  }

  var saved = null;

  function getSaved() {
    try { saved = JSON.parse(localStorage.getItem("csp_weather")); } catch (e) { saved = null; }
    return saved;
  }

  function save(city) {
    saved = city;
    try { localStorage.setItem("csp_weather", JSON.stringify(city)); } catch (e) {}
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  async function fetchJson(url) {
    var res = await fetch(url);
    if (!res.ok) throw new Error("HTTP " + res.status);
    return res.json();
  }

  async function showWeather(city) {
    var root = G.$("#w-main");
    root.style.display = "none";
    var load = G.$("#w-load");
    load.style.display = "block";
    if (city.name) document.querySelector("#w-current").textContent = esc(city.name);
    try {
      var p = new URLSearchParams({
        latitude: city.lat, longitude: city.lon,
        current: "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m",
        daily: "weather_code,temperature_2m_max,temperature_2m_min",
        timezone: "auto", forecast_days: "4",
      });
      var d = await fetchJson(MET + "?" + p.toString());
      if (d.current && city.name) save(city);
      render(d);
    } catch (e) {
      load.textContent = "Не получилось получить прогноз: " + e.message + " Проверь интернет и попробуй снова.";
      return;
    }
    load.style.display = "none";
    root.style.display = "block";
  }

  function fmtDay(iso) {
    var dt = new Date(iso + "T12:00:00");
    return DAYS[dt.getDay()] + " " + dt.getDate();
  }

  function render(d) {
    var c = d.current;
    var w = weather(c.weather_code, c.is_day === 0);
    var days = (d.daily.weather_code || []).slice(1).map(function (code, i) {
      var wd = weather(code, false);
      return '<div class="w-day"><div class="d">' + fmtDay(d.daily.time[i + 1]) + "</div>" +
        '<div class="e">' + wd[1] + "</div>" +
        '<div class="t"><i>' + Math.round(d.daily.temperature_2m_min[i + 1]) +
        "°</i> <b>" + Math.round(d.daily.temperature_2m_max[i + 1]) + "°</b></div></div>";
    }).join("");
    G.$("#w-body").innerHTML =
      '<div class="w-city">' + esc(saved ? saved.name : "Сейчас здесь") + "</div>" +
      '<div class="w-time">обновлено ' + new Date().toLocaleTimeString("ru-RU", { hour: "2-digit", minute: "2-digit" }) + "</div>" +
      '<div class="w-now"><span class="w-emoji">' + w[1] + "</span>" +
      '<span class="w-temp">' + Math.round(c.temperature_2m) + "°</span></div>" +
      '<div class="w-desc">' + w[0] + ", ощущается как " + Math.round(c.apparent_temperature) + "°</div>" +
      '<div class="w-stats">' +
      '<span class="w-stat">Влажность <b>' + Math.round(c.relative_humidity_2m) + "%</b></span>" +
      '<span class="w-stat">Ветер <b>' + Math.round(c.wind_speed_10m) + " км/ч</b></span>" +
      '<span class="w-stat">Осадки <b>' + (c.precipitation || 0) + " мм</b></span>" +
      "</div>" +
      '<div class="w-days">' + days + "</div>";
  }

  async function search(q) {
    var res = G.$("#w-results");
    res.innerHTML = "";
    if (q.trim().length < 2) return;
    try {
      var d = await fetchJson(GEO + "?name=" + encodeURIComponent(q.trim()) +
        "&count=5&language=ru&format=json");
      var list = d.results || [];
      if (!list.length) {
        res.innerHTML = '<div class="g-msg">Ничего не нашлось по «' + esc(q.trim()) + "».</div>";
        return;
      }
      list.forEach(function (it) {
        var b = document.createElement("button");
        b.className = "w-city-btn";
        b.textContent = it.name + (it.admin1 ? ", " + it.admin1 : "") + (it.country ? ", " + it.country : "");
        b.addEventListener("click", function () {
          res.innerHTML = "";
          showWeather({ name: it.name, lat: it.lat, lon: it.lon });
        });
        res.appendChild(b);
      });
    } catch (e) {
      res.innerHTML = '<div class="g-msg">Поиск не сработал: ' + esc(e.message) + "</div>";
    }
  }

  function curPos() {
    if (!navigator.geolocation) {
      showWeather({ name: "", lat: 55.7558, lon: 37.6173 });
      return;
    }
    G.$("#w-load").style.display = "block";
    navigator.geolocation.getCurrentPosition(
      function (p) {
        showWeather({ name: "Моя геопозиция", lat: p.coords.latitude, lon: p.coords.longitude });
      },
      function () {
        G.$("#w-load").style.display = "none";
        var s = getSaved();
        if (s) showWeather(s);
        else showWeather(QUICK[0]);
      }, { timeout: 8000 });
  }

  function boot() {
    var root = G.$("#g-root");
    G.sub("Погода для тех, кто собирается выходить из-за конспектов. Без ключей и рекламы.");
    var qc = QUICK.map(function (c) {
      return '<button class="w-city-btn" data-lat="' + c.lat + '" data-lon="' + c.lon +
        '" data-name="' + c.name + '">' + c.name + "</button>";
    }).join("");
    root.innerHTML =
      '<div class="w-search">' +
      '<input class="input" id="w-input" type="search" placeholder="Найди город…" autocomplete="off">' +
      '<button class="btn" id="w-locate">📍 Моя геопозиция</button>' +
      "</div>" +
      '<div class="w-quick">' + qc + "</div>" +
      '<div class="w-results" id="w-results"></div>' +
      '<div class="w-loading" id="w-load"></div>' +
      '<div class="weather-main" id="w-main"><div id="w-body"></div></div>';
    G.$("#w-main").style.display = "none";
    var debounce = null;
    G.$("#w-input").addEventListener("input", function () {
      clearTimeout(debounce);
      debounce = setTimeout(function () { search(G.$("#w-input").value); }, 450);
    });
    var curName = document.createElement("span");
    curName.id = "w-current";
    curName.style.display = "none";
    document.body.appendChild(curName);
    var posBtn = G.$("#w-locate");
    posBtn.addEventListener("click", function () { posBtn.textContent = "Ищу…"; curPos(); setTimeout(function () { posBtn.textContent = "📍 Моя геопозиция"; }, 6000); });
    document.querySelectorAll(".w-city-btn").forEach(function (b) {
      b.addEventListener("click", function () {
        showWeather({ name: b.dataset.name, lat: parseFloat(b.dataset.lat), lon: parseFloat(b.dataset.lon) });
      });
    });
    var s = getSaved();
    showWeather(s || QUICK[0]);
  }

  boot();
})();