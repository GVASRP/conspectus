/* Conspectus · Пятнашки (4×4) */
(function () {
  "use strict";
  var G = window.G;
  var N = 4, total = N * N;
  var tiles = [], empty = total - 1, moves = 0, over = false;

  function solved() {
    return tiles.every(function (v, i) { return v === i + 1; });
  }

  function neighbors() {
    var r = Math.floor(empty / N), c = empty % N, out = [];
    if (r > 0) out.push(empty - N);
    if (r < N - 1) out.push(empty + N);
    if (c > 0) out.push(empty - 1);
    if (c < N + 1) out.push(empty + 1);
    return out;
  }

  function slide(idx) {
    if (over) return;
    var ns = neighbors();
    if (ns.indexOf(idx) < 0) return;
    tiles[empty] = tiles[idx];
    tiles[idx] = 0;
    empty = idx;
    moves++;
    document.getElementById("st-Ходы").textContent = moves;
    try { G.sound.states.move(); } catch (e) {}
    paint();
    if (solved()) win();
  }

  function shuffleTiles() {
    tiles = [];
    for (var i = 0; i < total; i++) tiles.push(i === total - 1 ? 0 : i + 1);
    empty = total - 1;
    for (var n = 0; n < 400; n++) {
      var ns = neighbors();
      var idx = ns[Math.floor(Math.random() * ns.length)];
      tiles[empty] = tiles[idx];
      tiles[idx] = 0;
      empty = idx;
    }
    moves = 0;
    over = false;
    document.getElementById("st-Ходы").textContent = "0";
  }

  function win() {
    over = true;
    var best = G.best("fifteen");
    var newBest = !best || moves < best;
    if (newBest) G.best("fifteen", moves);
    document.getElementById("st-Рекорд").textContent = G.best("fifteen");
    try { G.sound.states.win(); } catch (e) {}
    G.overlay($root, "Собрано! 🎉", "Ходов: " + moves + (newBest ? " — новый рекорд!" : ""), "Перемешать", function () { G.hideOverlay($root); shuffleTiles(); });
  }

  function paint() {
    var grid = G.$("#f-grid");
    grid.innerHTML = "";
    for (var i = 0; i < total; i++) {
      var btn = document.createElement("button");
      btn.className = "f-cell";
      if (tiles[i] === 0) { btn.classList.add("empty"); btn.textContent = ""; }
      else { btn.textContent = tiles[i]; if (over) btn.classList.add("win"); }
      btn.addEventListener("click", (function (idx) { return function () { slide(idx); }; })(i));
      grid.appendChild(btn);
    }
  }

  var $root;
  function boot() {
    $root = G.$("#g-root");
    G.sub("Порядок 1…15, пустую клетку двигай соседними.");
    $root.innerHTML =
      G.bar(G.stat("Ходы", 0) + G.stat("Рекорд", G.best("fifteen")) +
        '<button class="btn xm ghost" id="f-reset">Перемешать</button>') +
      '<div class="game-area"><div class="f-grid" id="f-grid"></div></div>' +
      G.hint("Клик по плитке рядом с пустой клеткой двигает её");
    G.$("#f-reset").addEventListener("click", function () { shuffleTiles(); paint(); });
    shuffleTiles();
    paint();
  }

  boot();
})();