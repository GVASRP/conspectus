/* Conspectus · Тетрис: фабрика (соло + онлайн-гонка с общим силом) */
(function () {
  "use strict";
  var G = window.G;
  var COLS = 10, ROWS = 20, CELL = 26;
  var SHAPES = {
    I: [[1, 1, 1, 1]], O: [[1, 1], [1, 1]],
    T: [[0, 1, 0], [1, 1, 1]], S: [[0, 1, 1], [1, 1, 0]], Z: [[1, 1, 0], [0, 1, 1]],
    J: [[1, 0, 0], [1, 1, 1]], L: [[0, 0, 1], [1, 1, 1]],
  };
  var COLORS = { I: "#22d3ee", O: "#fbbf24", T: "#a855f7", S: "#3ddc97", Z: "#fb5c7a", J: "#3b82f6", L: "#fb923c" };

  function makeRng(seed) {
    var s = (seed >>> 0) || Math.floor(Math.random() * 2 ** 31);
    return function () {
      s = (s + 0x6D2B79F5) | 0;
      var t = s;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t = (t + Math.imul(t ^ (t >>> 7), t | 61)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function create(canvas, opts) {
    opts = opts || {};
    var rnd = opts.seed != null ? makeRng(opts.seed) : Math.random;
    var grid, bag, cur, dropTimer, score, lines, over, speed;

    function newGrid() {
      grid = [];
      for (var r = 0; r < ROWS; r++) grid.push(new Array(COLS).fill(0));
    }

    function shuffle(a) {
      for (var i = a.length - 1; i > 0; i--) {
        var j = Math.floor(rnd() * (i + 1));
        var t = a[i]; a[i] = a[j]; a[j] = t;
      }
      return a;
    }

    function bag7() {
      return shuffle(Object.keys(SHAPES)).map(function (t) {
        return { type: t, shape: SHAPES[t].map(function (r) { return r.slice(); }) };
      });
    }

    function nextCur() {
      if (!bag || !bag.length) bag = bag7();
      var piece = bag.shift();
      var shape = piece.shape, w = shape[0].length;
      cur = { type: piece.type, shape: shape, x: Math.floor((COLS - w) / 2), y: 0 };
      if (collides(cur.x, cur.y)) {
        over = true;
        try { G.sound.states.gameover(); } catch (e) {}
        if (opts.onTopOut) opts.onTopOut();
      }
    }

    function collides(x, y, shape) {
      shape = shape || cur.shape;
      for (var r = 0; r < shape.length; r++) {
        for (var c = 0; c < shape[r].length; c++) {
          if (!shape[r][c]) continue;
          var nx = x + c, ny = y + r;
          if (nx < 0 || nx >= COLS || ny >= ROWS) return true;
          if (ny >= 0 && grid[ny][nx]) return true;
        }
      }
      return false;
    }

    function lock() {
      for (var r = 0; r < cur.shape.length; r++) {
        for (var c = 0; c < cur.shape[r].length; c++) {
          if (cur.shape[r][c] && cur.y + r >= 0) grid[cur.y + r][cur.x + c] = cur.type;
        }
      }
      var full = [];
      for (var rr = 0; rr < ROWS; rr++) if (grid[rr].every(function (v) { return v; })) full.push(rr);
      if (full.length) {
        try { G.sound.states.clear(); } catch (e) {}
        score += [0, 100, 300, 500, 800][Math.min(full.length, 4)];
        lines += full.length;
        for (var i = 0; i < full.length; i++) grid.splice(full[i], 1)[0];
        while (grid.length < ROWS) grid.unshift(new Array(COLS).fill(0));
        if (opts.onLines) opts.onLines(lines);
      } else {
        try { G.sound.states.move(); } catch (e) {}
      }
      paint();
      nextCur();
      if (!over) {
        clearInterval(dropTimer);
        speed = Math.max(120, 700 - lines * 18);
        dropTimer = setInterval(drop, speed);
      }
      paint();
    }

    function drop() {
      if (over) return;
      if (!collides(cur.x, cur.y + 1)) { cur.y++; paint(); }
      else lock();
    }

    function hardDrop() {
      while (!collides(cur.x, cur.y + 1)) cur.y++;
      lock();
    }

    function slide(dx) {
      if (over) return;
      if (!collides(cur.x + dx, cur.y)) { cur.x += dx; paint(); }
    }

    function rotate() {
      if (over) return;
      var sh = cur.shape;
      var rot = sh[0].map(function (_, i) { return sh.map(function (row) { return row[i]; }).reverse(); });
      var kicks = [0, -1, 1, -2, 2];
      for (var k = 0; k < kicks.length; k++) {
        if (!collides(cur.x + kicks[k], cur.y, rot)) { cur.shape = rot; cur.x += kicks[k]; paint(); return; }
      }
    }

    function fillCell(ctx, x, y, color, ghost) {
      if (y < 0) return;
      var px = x * CELL, py = y * CELL;
      ctx.fillStyle = ghost ? shade(color, 0.35) : color;
      ctx.fillRect(px + 1, py + 1, CELL - 2, CELL - 2);
      if (!ghost) {
        ctx.fillStyle = "rgba(255,255,255,.18)";
        ctx.fillRect(px + 1, py + 1, CELL - 2, 3);
      }
    }

    function shade(hex, k) {
      var n = parseInt(hex.slice(1), 16);
      var r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
      r = Math.round(r + (255 - r) * k); g = Math.round(g + (255 - g) * k); b = Math.round(b + (255 - b) * k);
      return "rgb(" + r + "," + g + "," + b + ")";
    }

    function paint() {
      var ctx = canvas.getContext("2d");
      ctx.fillStyle = "#0a0f20";
      ctx.fillRect(0, 0, COLS * CELL, ROWS * CELL);
      ctx.strokeStyle = "rgba(255,255,255,.04)";
      for (var r = 0; r <= ROWS; r++) { ctx.beginPath(); ctx.moveTo(0, r * CELL); ctx.lineTo(COLS * CELL, r * CELL); ctx.stroke(); }
      for (var c = 0; c <= COLS; c++) { ctx.beginPath(); ctx.moveTo(c * CELL, 0); ctx.lineTo(c * CELL, ROWS * CELL); ctx.stroke(); }
      for (var rr = 0; rr < ROWS; rr++) {
        for (var cc = 0; cc < COLS; cc++) if (grid[rr][cc]) fillCell(ctx, cc, rr, COLORS[grid[rr][cc]], false);
      }
      if (cur && !over) {
        for (var pr = 0; pr < cur.shape.length; pr++) {
          for (var pc = 0; pc < cur.shape[pr].length; pc++) {
            if (cur.shape[pr][pc]) fillCell(ctx, cur.x + pc, cur.y + pr, COLORS[cur.type], true);
          }
        }
      }
      if (opts.onPaint) opts.onPaint(score, lines);
    }

    function onKey(e, map) {
      if (map[e.key] !== undefined) {
        e.preventDefault();
        if (map[e.key] === 1) slide(-1);
        else if (map[e.key] === 2) slide(1);
        else if (map[e.key] === 3) drop();
        else if (map[e.key] === 4) rotate();
        else hardDrop();
      }
    }

    function start() {
      newGrid();
      bag = []; score = 0; lines = 0; over = false;
      if (dropTimer) clearInterval(dropTimer);
      nextCur();
      speed = 700;
      dropTimer = setInterval(drop, speed);
      paint();
    }

    return {
      start: start, onKey: onKey, destroy: function () { if (dropTimer) clearInterval(dropTimer); },
      get: function () { return { score: score, lines: lines, over: over }; },
    };
  }

  /* ---------- соло-автозапуск на /fun/play/tetris ---------- */
  function bootSolo() {
    var root = document.getElementById("g-root");
    if (!root || root.dataset.room) return;
    if (root.dataset.game !== "tetris") return;
    var G = window.G;
    G.sub("Собирай линии. Стрелки = движение и поворот, пробел = сброс.");
    root.innerHTML =
      G.bar(G.stat("Очки", 0) + G.stat("Линии", 0) + G.stat("Рекорд", G.best("tetris")) +
        '<button class="btn xm ghost" id="t-reset">Заново</button>') +
      '<div class="game-area" style="display:grid;place-items:center"><canvas class="tetris" width="' +
      COLS * CELL + '" height="' + ROWS * CELL + '"></canvas></div>' +
      G.hint(G.k("←") + G.k("→") + "·" + G.k("↑") + "поворот ·" + G.k("↓") + "вниз ·" + G.k("Пробел") + "сброс");
    var reg = function (sel) { return root.querySelector(sel); };
    var canvas = reg("canvas");
    var t = create(canvas, {
      onPaint: function (score, lines) {
        var b = G.best("tetris");
        if (lines >= b) { G.best("tetris", lines); b = lines; }
        document.getElementById("st-Очки").textContent = score;
        document.getElementById("st-Линии").textContent = lines;
        document.getElementById("st-Рекорд").textContent = b;
      },
      onTopOut: function () {},
    });
    reg("#t-reset").addEventListener("click", function () { t.destroy(); t.start(); });
    var map = { ArrowLeft: 1, ArrowRight: 2, ArrowDown: 3, ArrowUp: 4, Space: 5, a: 1, d: 2, s: 3, w: 4, A: 1, D: 2, S: 3, W: 4 };
    document.addEventListener("keydown", function (e) { t.onKey(e, map); });
    t.start();
  }

  G.tetris = { create: create };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bootSolo);
  else bootSolo();
})();