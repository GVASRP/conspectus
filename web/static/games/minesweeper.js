/* Conspectus · Сапёр (9×9, 10 мин) */
(function () {
  "use strict";
  var G = window.G;
  var R = 9, C = 9, MINES = 10;
  var cells = [], revealed = 0, first = true, over = false, flags = 0;
  var time = 0, timer = null, started = false;

  function neighborCount(r, c) {
    var n = 0;
    for (var dr = -1; dr <= 1; dr++)
      for (var dc = -1; dc <= 1; dc++) {
        var rr = r + dr, cc = c + dc;
        if (rr >= 0 && rr < R && cc >= 0 && cc < C && cells[rr][cc].mine) n++;
      }
    return n;
  }

  function placeMines(safeR, safeC) {
    var idx = [];
    for (var r = 0; r < R; r++)
      for (var c = 0; c < C; c++)
        if (Math.abs(r - safeR) > 1 || Math.abs(c - safeC) > 1) idx.push(r * C + c);
    for (var i = idx.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = idx[i]; idx[i] = idx[j]; idx[j] = t;
    }
    for (var k = 0; k < MINES; k++) {
      var p = idx[k];
      cells[Math.floor(p / C)][p % C].mine = true;
    }
  }

  function build() {
    cells = [];
    for (var r = 0; r < R; r++) {
      cells.push([]);
      for (var c = 0; c < C; c++) cells[r].push({ mine: false, open: false, flag: false, n: 0 });
    }
    revealed = 0; flags = 0; over = false; first = true; started = false;
    if (timer) { clearInterval(timer); timer = null; }
    time = 0;
    document.getElementById("st-Время").textContent = "0с";
    document.getElementById("st-Мины").textContent = MINES;
    document.getElementById("st-Рекорд").textContent = G.best("mines") + "с";
    paint();
  }

  function open(r, c) {
    var cell = cells[r][c];
    if (over || cell.open || cell.flag) return;
    if (first) { first = false; placeMines(r, c); started = true; timer = setInterval(tick, 1000); }
    if (cell.mine) {
      cell.open = true;
      over = true;
      if (timer) clearInterval(timer);
      try { G.sound.states.gameover(); } catch (e) {}
      cells.forEach(function (row) { row.forEach(function (x) { if (x.mine) { x.flag = false; x.open = true; } }); });
      paint();
      G.overlay($root, "Бу-у-ум 💥", "Наступил на мину. Попробуй ещё раз!", "Заново", function () { G.hideOverlay($root); build(); });
      return;
    }
    cell.open = true;
    revealed++;
    if (cells[r][c].n === 0) flood(r, c);
    if (revealed === R * C - MINES) win();
    paint();
  }

  function flood(r, c) {
    for (var dr = -1; dr <= 1; dr++)
      for (var dc = -1; dc <= 1; dc++) {
        var rr = r + dr, cc = c + dc;
        if (rr < 0 || rr >= R || cc < 0 || cc >= C) continue;
        var x = cells[rr][cc];
        if (x.open || x.flag || x.mine) continue;
        x.open = true;
        revealed++;
        if (x.n === 0) flood(rr, cc);
      }
  }

  function flag(r, c) {
    var cell = cells[r][c];
    if (over || cell.open) return;
    cell.flag = !cell.flag;
    flags += cell.flag ? 1 : -1;
    document.getElementById("st-Мины").textContent = Math.max(0, MINES - flags);
    try { G.sound.states.click(); } catch (e) {}
    paint();
  }

  function win() {
    over = true;
    if (timer) clearInterval(timer);
    var best = G.best("mines");
    var newBest = !best || time < best;
    if (newBest) G.best("mines", time);
    document.getElementById("st-Рекорд").textContent = G.best("mines") + "с";
    try { G.sound.states.win(); } catch (e) {}
    G.overlay($root, "Поле чистое! 🎉", "Время: " + time + "с" + (newBest ? " — новый рекорд!" : ""), "Ещё раз", function () { G.hideOverlay($root); build(); });
  }

  function tick() { time++; document.getElementById("st-Время").textContent = time + "с"; }

  function paint() {
    var board = document.getElementById("m-board");
    board.innerHTML = "";
    for (var r = 0; r < R; r++) {
      for (var c = 0; c < C; c++) {
        var cell = cells[r][c];
        var btn = document.createElement("button");
        btn.className = "m-cell";
        var label = "";
        if (cell.open) {
          btn.classList.add("open");
          if (cell.mine) btn.classList.add("boom");
          else if (cell.n) { label = cell.n; btn.classList.add("n" + cell.n); }
        } else if (cell.flag) {
          label = "🚩"; btn.classList.add("flag");
        }
        btn.textContent = label;
        btn.addEventListener("click", function (rr, cc) { return function () { open(rr, cc); }; }(r, c));
        btn.addEventListener("contextmenu", function (rr, cc) { return function (e) { e.preventDefault(); flag(rr, cc); }; }(r, c));
        board.appendChild(btn);
      }
    }
  }

  var $root;
  function boot() {
    $root = G.$("#g-root");
    G.sub("Классика: чикни клетку, не наступи на мину. Правый клик — флаг.");
    $root.innerHTML =
      G.bar(G.stat("Время", "0с") + G.stat("Мины", MINES) + G.stat("Рекорд", G.best("mines") + "с") +
        '<button class="btn xm ghost" id="m-reset">Заново</button>') +
      '<div class="game-area"><div class="mgrid a" id="m-board"></div></div>' +
      G.hint("ЛКМ — открыть · ПКМ — флаг 🚩");
    G.$("#m-reset").addEventListener("click", build);
    build();
  }

  boot();
})();