/* Conspectus · 2048 */
(function () {
  "use strict";
  var G = window.G;
  var grid = [];
  var score = 0;
  var moved = false;

  function blank() { grid = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]]; }

  function addTile() {
    var cells = [];
    for (var r = 0; r < 4; r++) for (var c = 0; c < 4; c++) if (!grid[r][c]) cells.push([r, c]);
    if (!cells.length) return false;
    var p = cells[Math.floor(Math.random() * cells.length)];
    grid[p[0]][p[1]] = Math.random() < 0.9 ? 2 : 4;
    return true;
  }

  function render() {
    var root = G.$("#tiles");
    root.innerHTML = "";
    for (var r = 0; r < 4; r++) {
      for (var c = 0; c < 4; c++) {
        var t = document.createElement("div");
        t.className = "tile";
        t.dataset.v = grid[r][c];
        t.textContent = grid[r][c] || "";
        root.appendChild(t);
      }
    }
    document.querySelector("#st-Счёт").textContent = score;
    if (score > G.best("2048")) G.best("2048", score);
    document.querySelector("#st-Рекорд").textContent = G.best("2048");
  }

  function slide(rows) {
    moved = false;
    return rows.map(function (row) {
      var vals = row.filter(function (v) { return v; });
      var out = [0, 0, 0, 0];
      for (var i = 0; i < vals.length; i++) {
        if (i + 1 < vals.length && vals[i] === vals[i + 1]) {
          out[out.indexOf(0)] = vals[i] * 2;
          score += vals[i] * 2;
          i++;
        } else {
          out[out.indexOf(0)] = vals[i];
        }
      }
      if (out.join(",") !== row.join(",")) moved = true;
      return out;
    });
  }

  function move(dir) {
    var rows;
    if (dir === 0) rows = grid;                                   // влево
    else if (dir === 1) rows = grid.map(function (r) { return r.slice().reverse(); }); // вправо
    else if (dir === 2) {                                          // вверх
      rows = [[], [], [], []];
      for (var c = 0; c < 4; c++) rows[c] = [grid[0][c], grid[1][c], grid[2][c], grid[3][c]];
    } else {                                                       // вниз
      rows = [[], [], [], []];
      for (var c2 = 0; c2 < 4; c2++) rows[c2] = [grid[3][c2], grid[2][c2], grid[1][c2], grid[0][c2]];
    }
    var done = slide(rows);
    if (dir === 1) done = done.map(function (r) { return r.reverse(); });
    if (dir === 2) {
      for (var cc = 0; cc < 4; cc++) for (var r = 0; r < 4; r++) grid[r][cc] = done[cc][r];
    } else if (dir === 3) {
      for (var c3 = 0; c3 < 4; c3++) for (var r2 = 0; r2 < 4; r2++) grid[r2][c3] = done[c3][3 - r2];
    } else {
      grid = done;
    }
    if (moved) {
      addTile();
      render();
      check();
    }
  }

  function canMove() {
    for (var r = 0; r < 4; r++) {
      for (var c = 0; c < 4; c++) {
        if (!grid[r][c]) return true;
        if (c < 3 && grid[r][c] === grid[r][c + 1]) return true;
        if (r < 3 && grid[r][c] === grid[r + 1][c]) return true;
      }
    }
    return false;
  }

  function check() {
    var area = G.$("#game-area");
    var overlays = area.querySelector(".overlay");
    var won = false;
    for (var r = 0; r < 4; r++) if (grid[r].includes(2048)) won = true;
    if (won && !overlays) {
      G.overlay(area, "Ты собрал 2048!", "Рекорд: " + score, "Играть дальше",
        function () { G.hideOverlay(area); });
    }
    if (!canMove() && !overlays) {
      G.overlay(area, "Нет ходов", "Счёт: " + score, "Заново",
        function () { G.hideOverlay(area); resetGame(); });
    }
  }

  function resetGame() {
    blank(); score = 0;
    addTile(); addTile();
    render();
  }

  function wire() {
    var map = { ArrowLeft: 0, ArrowRight: 1, ArrowUp: 2, ArrowDown: 3, a: 0, d: 1, w: 2, s: 3, A: 0, D: 1, W: 2, S: 3 };
    document.addEventListener("keydown", function (e) {
      if (map[e.key] !== undefined) { e.preventDefault(); move(map[e.key]); }
    });
    var area = G.$("#game-area");
    var sx = null, sy = null;
    area.addEventListener("touchstart", function (e) {
      var t = e.changedTouches[0];
      sx = t.clientX; sy = t.clientY;
      e.preventDefault();
    }, { passive: false });
    area.addEventListener("touchmove", function (e) { e.preventDefault(); }, { passive: false });
    area.addEventListener("touchend", function (e) {
      if (sx === null) return;
      var t = e.changedTouches[0];
      var dx = t.clientX - sx, dy = t.clientY - sy;
      if (Math.max(Math.abs(dx), Math.abs(dy)) < 20) return;
      if (Math.abs(dx) > Math.abs(dy)) move(dx > 0 ? 1 : 0);
      else move(dy > 0 ? 3 : 2);
      sx = sy = null;
    }, { passive: false });
  }

  function boot() {
    var root = G.$("#g-root");
    G.sub("Соединяй одинаковые плитки. Стрелки, клавиши WASD или свайпы.");
    root.innerHTML =
      G.bar(G.stat("Счёт", 0) + G.stat("Рекорд", G.best("2048")) +
        '<button class="btn xm ghost" id="reset-btn">Новая игра</button>') +
      '<div class="gshell"><div class="game-area" id="game-area"><div class="board" id="tiles"></div></div></div>' +
      G.hint(G.k("← ") + G.k("→ ") + G.k("↑ ") + G.k("↓ ") + "или свайпы");
    G.$("#reset-btn").addEventListener("click", resetGame);
    wire();
    resetGame();
  }

  boot();
})();