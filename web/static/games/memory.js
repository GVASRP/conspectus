/* Conspectus · Память */
(function () {
  "use strict";
  var G = window.G;
  var EMOJI = ["🧠", "🚀", "⚡", "🌊", "🍀", "🎲", "🔥", "⭐"];
  var cards = [];
  var openIdx = [];
  var matched = 0;
  var moves = 0;
  var startT = null;
  var timer = null;

  function pad(n) { return n < 10 ? "0" + n : "" + n; }

  function fmtMs(ms) {
    var s = Math.floor(ms / 1000);
    return pad(Math.floor(s / 60)) + ":" + pad(s % 60);
  }

  function tick() {
    var el = document.querySelector("#st-Время");
    if (el && startT) el.textContent = fmtMs(Date.now() - startT);
  }

  function renderGrid() {
    var root = G.$("#mem-grid");
    root.innerHTML = "";
    cards.forEach(function (card, i) {
      var d = document.createElement("div");
      d.className = "mem-card";
      if (card.open) d.classList.add("open");
      if (card.done) d.classList.add("matched");
      d.dataset.i = i;
      d.innerHTML = '<div class="mem-in"><div class="mem-f">✦</div><div class="mem-b">' + card.v + "</div></div>";
      root.appendChild(d);
    });
  }

  function flip(i) {
    var card = cards[i];
    if (card.open || card.done) return;
    card.open = true;
    openIdx.push(i);
    renderGrid();
    if (!startT) { startT = Date.now(); timer = setInterval(tick, 500); }
    if (openIdx.length === 2) {
      moves++;
      var a = openIdx[0], b = openIdx[1];
      document.querySelector("#st-Ходы").textContent = moves;
      if (cards[a].v === cards[b].v) {
        cards[a].done = cards[b].done = true;
        matched += 2;
        openIdx = [];
        if (matched === cards.length) win();
      } else {
        setTimeout(function () {
          cards[a].open = cards[b].open = false;
          openIdx = [];
          renderGrid();
        }, 700);
      }
    } else if (openIdx.length > 2) {
      var extra = openIdx.shift();
      cards[extra].open = false;
    }
  }

  function win() {
    clearInterval(timer);
    var old = G.best("memory");
    if (old === 0 || moves < old) G.best("memory", moves);
    document.querySelector("#st-Рекорд").textContent = G.best("memory");
    var area = G.$("#mem-area");
    G.overlay(area,
      "Все пары найдены!",
      "За " + fmtMs(Date.now() - startT) + " · " + moves + " ходов",
      "Сыграть ещё",
      function () { G.hideOverlay(area); newGame(true); });
  }

  function newGame(keepBest) {
    var pairs = EMOJI.slice().map(function (v) { return { v: v }; })
      .concat(EMOJI.slice().map(function (v) { return { v: v }; }));
    for (var i = pairs.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var tmp = pairs[i]; pairs[i] = pairs[j]; pairs[j] = tmp;
    }
    cards = pairs.map(function (p) { return { v: p.v, open: false, done: false }; });
    openIdx = []; matched = 0; moves = 0;
    startT = null;
    if (timer) clearInterval(timer);
    document.querySelector("#st-Ходы").textContent = "0";
    document.querySelector("#st-Время").textContent = "00:00";
    if (!keepBest) document.querySelector("#st-Рекорд").textContent = G.best("memory");
    renderGrid();
  }

  function boot() {
    var root = G.$("#g-root");
    G.sub("Открывай карточки и находи одинаковые пары. Чем меньше ходов — тем лучше.");
    root.innerHTML =
      G.bar(G.stat("Ходы", 0) + G.stat("Время", "00:00") + G.stat("Рекорд", G.best("memory")) +
        '<button class="btn xm ghost" id="new-btn">Сначала</button>') +
      '<div class="game-area" id="mem-area" style="display:grid;place-items:center"><div class="mem-grid" id="mem-grid"></div></div>' +
      G.hint("Тап по карточке раскрывает её");
    G.$("#mem-grid").addEventListener("click", function (e) {
      var card = e.target.closest(".mem-card");
      if (card) flip(parseInt(card.dataset.i, 10));
    });
    G.$("#new-btn").addEventListener("click", function () { newGame(false); });
    newGame(false);
  }

  boot();
})();