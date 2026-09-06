/* Conspectus · крестики-нолики (онлайн-комната) */
(function () {
  "use strict";
  var G = window.G;
  var onMoveCb = null;
  var els = [];

  function mount(root, mySlot) {
    root.innerHTML =
      '<div class="xo-wrap"><div class="xo-board">' +
      new Array(9).fill(0).map(function (_, i) {
        return '<button class="xo-cell" data-idx="' + i + '"></button>';
      }).join("") +
      '</div></div>';
    var board = root.querySelector(".xo-board");
    els = [];
    for (var i = 0; i < 9; i++) {
      var b = board.children[i];
      b.addEventListener("click", function () {
        if (state.over || !state.myTurn) return;
        var idx = parseInt(this.dataset.idx, 10);
        if (state.board[idx] !== ".") return;
        try { G.sound.states.move(); } catch (e) {}
        if (onMoveCb) onMoveCb(idx);
      });
      if (!b.dataset.idx) b.dataset.idx = String(i);
      els.push(b);
    }
  }

  var state = { board: ".........", myTurn: false, over: false };
  var mySym = "X";

  function setState(data) {
    state.board = data.board || state.board || ".........";
    state.myTurn = !!data.my_turn;
    state.over = !!data.over;
    mySym = data.my_sym || mySym;
    for (var i = 0; i < 9; i++) {
      var el = els[i];
      if (!el) continue;
      var v = state.board[i];
      el.textContent = v === "." ? "" : (v === "X" ? "✕" : "◯");
      el.className = "xo-cell" + (v !== "." ? " placed" : "") + (state.over ? " locked" : "");
      if (mySym === v && v !== ".") el.classList.add("mine");
    }
  }

  G.xo = {
    mount: function (root, mySlot) { mySlot = mySlot || "guest"; mount(root, mySlot); },
    setState: setState,
    onMove: function (cb) { onMoveCb = cb; },
  };

  /* ---------- соло против бота на /fun/play/xo ---------- */
  function postBot(path, data, done) {
    var fd = new FormData();
    Object.keys(data).forEach(function (k) { fd.append(k, data[k]); });
    fetch(path, { method: "POST", body: fd })
      .then(function (r) { return r.json(); })
      .then(done)
      .catch(function () { done({ ok: false, error: "Сеть недоступна." }); });
  }

  function bootSolo() {
    var root = document.getElementById("g-root");
    if (!root || root.dataset.game !== "xo") return;
    var G = window.G;
    var mySym = "X";
    var lastBoard = ".........";
    var busy = false;

    root.innerHTML =
      G.bar('<span class="hint-row" style="margin:0">Вы — ✕, ходите первым.</span>' +
        '<button class="btn xm ghost" id="xo-restart">Заново</button>') +
      '<div class="game-area" style="display:grid;place-items:center" id="xo-solo-wrap"></div>';
    G.sub("Крестики-нолики с ботом. Ваши — ✕.");
    mount(root.querySelector("#xo-solo-wrap"), "host");

    function restart() {
      lastBoard = ".........";
      busy = false;
      G.hideOverlay(root);
      setState({ board: lastBoard, my_turn: true, my_sym: "X", over: false, winner: null, draw: false });
    }

    function showResult(r) {
      var title, sub;
      if (r.draw) { title = "Ничья"; sub = "Никто не смог победить."; }
      else if (r.winner === "me") { title = "Победа!"; sub = "Бот пасует перед вами."; }
      else { title = "Бот выиграл"; sub = "Он зевает редко — попробуй ещё."; }
      G.overlay(root, title, sub, "Ещё раз", restart);
    }

    function serverTurn(cell) {
      if (busy || state.over) return;
      busy = true;
      postBot("/api/bot/xo/move", { board: lastBoard, cell: String(cell), my_sym: mySym }, function (r) {
        busy = false;
        if (!r.ok) { try { G.sound.states.wrong(); } catch (e) {} return; }
        lastBoard = r.board;
        setState(r);
        if (r.over) showResult(r);
      });
    }

    onMoveCb = function (cell) { serverTurn(cell); };
    root.querySelector("#xo-restart").addEventListener("click", restart);
    setState({ board: lastBoard, my_turn: true, my_sym: "X", over: false });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bootSolo);
  else bootSolo();
})();