/* Conspectus · звук: лёгкий WebAudio-синтез + тоггл */
(function () {
  "use strict";
  var ctx;
  function getCtx() { if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)(); return ctx; }

  var ENABLED = localStorage.getItem("csp_sound") !== "0";

  function beep(freq, dur, vol, type, delay) {
    if (!ENABLED) return;
    try {
      var ac = getCtx(), now = ac.currentTime + (delay || 0);
      var osc = ac.createOscillator(), gain = ac.createGain();
      osc.connect(gain); gain.connect(ac.destination);
      osc.type = type || "sine"; osc.frequency.value = freq;
      gain.gain.setValueAtTime(vol || 0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + dur);
      osc.start(now); osc.stop(now + dur + 0.01);
    } catch (e) {}
  }

  function chord(freqs, dur, vol, type, stagger) {
    freqs.forEach(function (f, i) { beep(f, dur, vol, type, (stagger || 0.06) * i); });
  }

  var NS = {
    move:   function () { beep(440, 0.08, 0.10, "sine"); },
    capture:function () { chord([440, 660], 0.10, 0.11, "sine", 0.04); },
    flip:    function () { beep(520, 0.06, 0.09); },
    match:   function () { chord([523, 659, 784], 0.18, 0.14, "sine", 0.05); },
    clear:   function () { chord([523, 659, 784], 0.14, 0.13, "triangle", 0.04); },
    correct: function () { chord([523, 659, 784], 0.20, 0.16, "sine", 0.05); },
    wrong:   function () { chord([233, 220], 0.15, 0.12, "sawtooth", 0.03); },
    win:     function () { chord([523, 659, 784, 1047], 0.24, 0.16, "sine", 0.07); },
    gameover:function () { chord([294, 220, 165], 0.22, 0.13, "triangle", 0.08); },
    click:   function () { beep(600, 0.04, 0.08); },
    drop:    function () { chord([262, 330], 0.06, 0.10, "triangle"); },
  };

  G.sound = {
    states: NS,
    on: function () { return ENABLED; },
    toggle: function () {
      ENABLED = !ENABLED;
      localStorage.setItem("csp_sound", ENABLED ? "1" : "0");
      this.updateBtn();
    },
    updateBtn: function () {
      var btns = document.querySelectorAll(".sound-toggle");
      btns.forEach(function (b) { b.textContent = ENABLED ? "♪" : "♪̸"; b.title = ENABLED ? "Выключить звук" : "Включить звук"; b.classList.toggle("off", !ENABLED); });
    },
  };

  function injectToggle() {
    var bars = document.querySelectorAll(".gbar");
    bars.forEach(function (bar) {
      if (bar.querySelector(".sound-toggle")) return;
      var btn = document.createElement("button");
      btn.className = "btn xs ghost sound-toggle";
      btn.title = ENABLED ? "Выключить звук" : "Включить звук";
      btn.textContent = ENABLED ? "♪" : "♪̸";
      btn.classList.toggle("off", !ENABLED);
      btn.addEventListener("click", function () { G.sound.toggle(); });
      bar.appendChild(btn);
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", injectToggle);
  else injectToggle();
})();