/* Conspectus · комната развлечений — гаджеты хаба */
(function () {
  "use strict";

  var FACTS = [
    "Словарный запас конспекта растёт, пока ты делаешь перерыв.",
    "Человек забывает 50% новой информации уже за час, если её не повторять.",
    "Мозг лучше запоминает то, что читает перед сном.",
    "Рука с ручкой пишет примерно 30–40 слов в минуту.",
    "Перерыв в 25 минут возвращает концентрацию почти на исходный уровень.",
    "Приём помодоро называется так из-за кухонного таймера в виде помидора.",
    "Смотреть на свои старые конспекты — всё равно что читать письма самому себе.",
    "Наша короткая память помещает всего 7±2 объекта одновременно.",
    "Быстрые игры между делом — отличная разминка для мозга.",
    "Солёный попкорн и сладкий чай — классика учёных вечеров.",
    "Черновик решения проблемы чаще появляется во время отдыха, а не за столом.",
    "Всё новое в науке когда-то было чьим-то конспектом.",
    "Облако на 100% состоит из капель воды, а не из дыма или ваты.",
    "Молния бьёт примерно на 30 000°C — в пять раз горячее Солнца.",
    "Дождь падает со скоростью около 9 метров в секунду.",
    "Летом Земля вращается быстрее, чем зимой (эффект сохраняется!).",
    "У нас и у бананов совпадает примерно 60% генов — не напрягайся.",
    "Если очень долго сидеть над конспектом, помидор станет другом.",
  ];

  var q = function (sel) { return document.querySelector(sel); };

  function fact() {
    var el = q("#fact-text");
    if (!el) return;
    el.style.opacity = "0";
    el.style.transition = "opacity .2s";
    setTimeout(function () {
      el.textContent = FACTS[Math.floor(Math.random() * FACTS.length)];
      el.style.opacity = "1";
    }, 200);
  }

  function dice() {
    var die = q("#die");
    if (!die) return;
    die.classList.remove("rolling");
    void die.offsetWidth;
    die.classList.add("rolling");
    var faces = ["⚀", "⚁", "⚂", "⚃", "⚄", "⚅"];
    var i = 0;
    var t = setInterval(function () {
      die.textContent = faces[Math.floor(Math.random() * 6)];
      if (++i >= 4) {
        clearInterval(t);
        die.textContent = faces[Math.floor(Math.random() * 6)];
        die.classList.remove("rolling");
      }
    }, 120);
  }

  function coin() {
    var c = q("#coin"), res = q("#coin-res");
    if (!c) return;
    c.classList.remove("heads", "tails");
    void c.offsetWidth;
    var heads = Math.random() < 0.5;
    setTimeout(function () {
      c.classList.add(heads ? "heads" : "tails");
      var s = (res.textContent.match(/\d+/g) || ["0", "0"]).map(Number);
      if (heads) s[0]++; else s[1]++;
      res.textContent = "Счёт: орёл " + s[0] + " · решка " + s[1];
    }, 80);
  }

  var pomo = {
    mins: 25, total: 25 * 60, left: 25 * 60, running: false, tick: null,
    el: null, ring: null, btn: null,
    fmt: function () {
      var m = Math.floor(this.left / 60), s = this.left % 60;
      return (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
    },
    paint: function () {
      this.el.textContent = this.fmt();
      var p = this.total ? ((this.total - this.left) / this.total) * 100 : 0;
      this.ring.style.background =
        "conic-gradient(#8b5cf6 " + p + "%, rgba(255,255,255,.08) 0%)";
      if (this.total) document.title = "🍅 " + this.fmt() + " · Conspectus";
      else document.title = "Conspectus";
    },
    start: function () {
      var self = this;
      if (this.running) return;
      this.running = true;
      this.btn.textContent = "Пауза";
      this.tick = setInterval(function () {
        if (self.left > 1) {
          self.left--;
          self.paint();
        } else {
          self.left = 0;
          self.paint();
          self.stop();
          try {
            var ac = new (window.AudioContext || window.webkitAudioContext)();
            var o = ac.createOscillator(), g = ac.createGain();
            o.connect(g); g.connect(ac.destination);
            o.frequency.value = 880; g.gain.value = 0.2;
            o.start(); o.stop(ac.currentTime + 0.6);
          } catch (e) {}
        }
      }, 1000);
    },
    stop: function () {
      this.running = false;
      if (this.tick) clearInterval(this.tick);
      this.btn.textContent = "Старт";
    },
    set: function (m) {
      var was = this.running;
      this.stop();
      this.mins = m; this.total = m * 60; this.left = m * 60;
      this.paint();
      if (was) this.start();
    },
  };

  function wire() {
    var fb = q("#fact-btn");
    if (fb) fb.addEventListener("click", fact);
    if (q("#fact-text")) fact();
    var db = q("#dice-btn");
    if (db) db.addEventListener("click", dice);
    var cb = q("#coin-btn");
    if (cb) cb.addEventListener("click", coin);
    var ring = q("#pomo-ring"), pt = q("#pomo-time"), pb = q("#pomo-btn");
    if (ring && pt && pb) {
      pomo.el = pt; pomo.ring = ring; pomo.btn = pb;
      var presets = document.querySelectorAll("#pomo-presets .btn");
      presets.forEach(function (b) {
        b.addEventListener("click", function () {
          presets.forEach(function (x) { x.classList.remove("on"); });
          b.classList.add("on");
          pomo.set(parseInt(b.dataset.min, 10));
        });
      });
      pb.addEventListener("click", function () {
        if (pomo.running) pomo.stop();
        else pomo.start();
      });
      pomo.paint();
    }
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", wire);
  else wire();
})();