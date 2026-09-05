/* Conspectus · Змейка */
(function () {
  "use strict";
  var G = window.G;
  var N = 21;
  var CELL = 20;
  var state = { snake: [], dir: 1, food: null, score: 0, dead: false, timer: null };

  function randCell() {
    while (true) {
      var c = Math.floor(Math.random() * N * N);
      if (!state.snake.includes(c)) return c;
    }
  }

  function draw(canvas) {
    var ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, N * CELL, N * CELL);
    ctx.fillStyle = "rgba(255,255,255,.045)";
    for (var i = 0; i < N * N; i++) {
      var x = (i % N) * CELL, y = Math.floor(i / N) * CELL;
      ctx.fillRect(x, y, CELL, CELL);
    }
    ctx.fillStyle = "#3ddc97";
    ctx.shadowColor = "#3ddc97"; ctx.shadowBlur = 12;
    var fx = (state.food % N) * CELL, fy = Math.floor(state.food / N) * CELL;
    ctx.fillRect(fx + 4, fy + 4, CELL - 8, CELL - 8);
    ctx.shadowBlur = 0;
    state.snake.forEach(function (c, idx) {
      var x = (c % N) * CELL, y = Math.floor(c / N) * CELL;
      var t = idx / state.snake.length;
      ctx.fillStyle = "rgb(" + Math.round(139 + t * 74) + "," + Math.round(92 + t * 10) + "," + Math.round(246 - t * 40) + ")";
      ctx.fillRect(x + 1, y + 1, CELL - 2, CELL - 2);
    });
  }

  function step(canvas) {
    var head = state.snake[0];
    var col = head % N, row = Math.floor(head / N);
    if (state.dir === 1) col++; else if (state.dir === 3) col--;
    else if (state.dir === 2) row++; else row--;
    if (col < 0 || col >= N || row < 0 || row >= N) return over(canvas);
    var next = row * N + col;
    if (state.snake.includes(next)) return over(canvas);
    state.snake.unshift(next);
    if (next === state.food) {
      state.score += 10;
      document.querySelector("#st-Очки").textContent = state.score;
      if (state.score > G.best("snake")) G.best("snake", state.score);
      document.querySelector("#st-Рекорд").textContent = G.best("snake");
      state.food = randCell();
      var speed = Math.max(70, 130 - state.score);
      if (state.timer) { clearInterval(state.timer); state.timer = setInterval(function () { step(canvas); }, speed); }
    } else {
      state.snake.pop();
    }
    draw(canvas);
  }

  function over(canvas) {
    var wasRunning = !!state.timer;
    if (state.timer) { clearInterval(state.timer); state.timer = null; }
    if (!wasRunning || state.dead) return;
    state.dead = true;
    G.best("snake", state.score);
    document.querySelector("#st-Рекорд").textContent = G.best("snake");
    var area = canvas.parentElement;
    G.overlay(area,
      "Игра окончена",
      "Набрано очков: " + state.score,
      "Ещё раз",
      function () { G.hideOverlay(area); start(); });
  }

  function change(d) {
    if (d % 2 === state.dir % 2) return;
    state.dir = d;
  }

  function start() {
    state.snake = [Math.floor(N / 2) * N + Math.floor(N / 2)];
    state.dir = 1; state.score = 0; state.dead = false;
    state.food = randCell();
    var canvas = G.$("#snake");
    draw(canvas);
    document.querySelector("#st-Очки").textContent = "0";
    document.querySelector("#st-Рекорд").textContent = G.best("snake");
    if (state.timer) clearInterval(state.timer);
    state.timer = setInterval(function () { step(canvas); }, 130);
  }

  function wireKeyboard() {
    document.addEventListener("keydown", function (e) {
      var map = { ArrowRight: 1, ArrowDown: 2, ArrowLeft: 3, ArrowUp: 4, d: 1, s: 2, a: 3, w: 4, D: 1, S: 2, A: 3, W: 4 };
      if (map[e.key]) { e.preventDefault(); change(map[e.key]); }
      if (e.key === "r" || e.key === "R") rest();
    });
  }

  function wireTouch(canvas) {
    var sx = null, sy = null;
    canvas.addEventListener("touchstart", function (e) {
      var t = e.changedTouches[0];
      sx = t.clientX; sy = t.clientY;
      e.preventDefault();
    }, { passive: false });
    canvas.addEventListener("touchmove", function (e) { e.preventDefault(); }, { passive: false });
    canvas.addEventListener("touchend", function (e) {
      if (sx === null) return;
      var t = e.changedTouches[0];
      var dx = t.clientX - sx, dy = t.clientY - sy;
      if (Math.max(Math.abs(dx), Math.abs(dy)) < 18) return;
      if (Math.abs(dx) > Math.abs(dy)) change(dx > 0 ? 1 : 3);
      else change(dy > 0 ? 2 : 4);
      sx = sy = null;
    }, { passive: false });
  }

  function rest() {
    if (state.timer) clearInterval(state.timer);
    var area = G.$("#snake").parentElement;
    G.hideOverlay(area);
    start();
  }

  function boot() {
    var root = G.$("#g-root");
    G.sub("Ешь зелёные кубики. Стрелки/клавиши WASD или свайп на телефоне.");
    root.innerHTML =
      G.bar(G.stat("Очки", 0) + G.stat("Рекорд", G.best("snake"))) +
      '<div class="game-area snake-canvas-wrap"><canvas id="snake" class="snake" width="' +
      N * CELL + '" height="' + N * CELL + '">' +
      "</canvas></div>" +
      G.hint(G.k("↑ ↓ ← →") + "или" + G.k("WASD") + "· свайпы ·" + G.k("R") + "— заново");
    var canvas = G.$("#snake");
    wireKeyboard();
    wireTouch(canvas);
    start();
  }

  boot();
})();