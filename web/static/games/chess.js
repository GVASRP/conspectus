/* Conspectus · шахматы — онлайн-комната (рендер FEN) и соло против бота */
(function () {
  "use strict";
  var G = window.G;
  var GLYPHS = { P: "♟", N: "♞", B: "♝", R: "♜", Q: "♛", K: "♚" };
  var START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1";

  var state = { ori: "w", my: "w", myTurn: false, legal: [], selected: null, over: false };
  var onMoveCb = null, rootEl = null, boardEl = null;

  function sqName(row, col) {
    var ori = state.ori;
    var fi = (ori === "w") ? col : 7 - col;
    var ri = (ori === "w") ? row : 7 - row;
    return String.fromCharCode(97 + fi) + (8 - ri);
  }

  function sqColor(sq) {
    var fi = sq.charCodeAt(0) - 97, rn = parseInt(sq[1], 10);
    return (fi + rn - 1) % 2 === 1;
  }

  function kingSquare(fen, color) {
    var board = fen.split(" ")[0].replace(/\d/g, function (d) { return ".".repeat(+d); }).replace(/\//g, "");
    var ch = color === "w" ? "K" : "k";
    var i = board.indexOf(ch);
    if (i < 0) return null;
    return String.fromCharCode(97 + (i % 8)) + (8 - Math.floor(i / 8));
  }

  function mount(root, mySlot) {
    rootEl = root;
    state.ori = (mySlot === "host") ? "w" : "b";
    state.my = state.ori;
    rootEl.innerHTML =
      '<div class="chess-wrap"><div class="chess-board"></div></div>';
    boardEl = rootEl.querySelector(".chess-board");
    var rows = "";
    for (var r = 0; r < 8; r++) {
      for (var c = 0; c < 8; c++) {
        var sq = sqName(r, c);
        rows += '<div class="sq ' + (sqColor(sq) ? "light" : "dark") + '" data-sq="' + sq + '"></div>';
      }
    }
    boardEl.innerHTML = rows;
    boardEl.addEventListener("click", onBoardClick);
  }

  function onBoardClick(ev) {
    var sqEl = ev.target.closest(".sq");
    if (!sqEl || !state.myTurn || state.over) return;
    var sq = sqEl.dataset.sq, pc = sqEl.dataset.pc;
    var targets = legalTargets(state.selected);
    if (state.selected && targets.indexOf(sq) >= 0) {
      var uciBase = state.selected + sq;
      var promos = state.legal.filter(function (u) { return u.slice(0, 4) === uciBase && u.length === 4; });
      if (promos.length === 1) sendMove(promos[0]);
      else if (promos.length > 1) showPromo(uciBase + "?", promos);
      else sendMove(uciBase);
      return;
    }
    if (pc && isMine(pc)) {
      state.selected = sq;
      paint();
    } else {
      state.selected = null;
      paint();
    }
  }

  function isMine(pc) {
    return (state.my === "w" && pc === pc.toUpperCase()) || (state.my === "b" && pc === pc.toLowerCase());
  }

  function legalTargets(fs) {
    if (!fs) return [];
    return state.legal.filter(function (u) { return u.slice(0, 2) === fs; }).map(function (u) { return u.slice(2, 4); });
  }

  function sendMove(uci) {
    var fromSq = uci.slice(0, 2), toSq = uci.slice(2, 4);
    var fromEl = boardEl.querySelector('.sq[data-sq="' + fromSq + '"]');
    var enemy = !!(fromEl && fromEl.dataset.pc && fromEl.dataset.pc !== fromEl.dataset.pc.toUpperCase());
    try { G.sound.states[enemy ? "capture" : "move"](); } catch (e) {}
    state.selected = null;
    if (onMoveCb) onMoveCb(uci);
  }

  function showPromo(base, promos) {
    var box = document.createElement("div");
    box.className = "promo-box";
    box.innerHTML = '<div class="promo-title">Ферзь или кто повыше?</div><div class="promo-row"></div>';
    var row = box.querySelector(".promo-row");
    promos.forEach(function (u) {
      var b = document.createElement("button");
      b.className = "btn sm ghost";
      b.textContent = GLYPHS[u[3].toUpperCase()];
      b.addEventListener("click", function () { box.remove(); sendMove(u); });
      row.appendChild(b);
    });
    rootEl.querySelector(".chess-wrap").appendChild(box);
  }

  function piecesForRow(rowStr, ori) {
    var out = [];
    for (var i = 0; i < rowStr.length; i++) {
      var ch = rowStr[i];
      if (/\d/.test(ch)) {
        for (var k = 0; k < +ch; k++) out.push(null);
      } else out.push(ch);
    }
    if (ori === "b") out.reverse();
    return out;
  }

  function paint() {
    if (!boardEl) return;
    var parts = state.fen.split(" ");
    var ranks = parts[0].split("/"); // r8..r1
    var pieces = [];
    for (var i = 0; i < 8; i++) pieces.push(piecesForRow(ranks[i], state.ori));
    var targets = legalTargets(state.selected);
    var lastSqs = state.last ? [state.last.slice(0, 2), state.last.slice(2, 4)] : [];
    var chk = (state.inCheck && state.myTurn !== null) ? kingSquare(state.fen, state.turn === "w" ? "w" : "b") : null;

    var cells = boardEl.children;
    for (var r = 0; r < 8; r++) {
      for (var c = 0; c < 8; c++) {
        var sq = sqName(r, c);
        var idx = r * 8 + c;
        var cell = cells[idx];
        var pc = pieces[r][c] || "";
        cell.textContent = pc ? GLYPHS[pc.toUpperCase()] : "";
        cell.className = "sq " + (sqColor(sq) ? "light" : "dark") +
          (pc === pc.toUpperCase() ? " pw" : pc ? " pb" : "");
        cell.dataset.pc = pc;
        if (state.selected === sq) cell.classList.add("sel");
        if (lastSqs.indexOf(sq) >= 0) cell.classList.add("last");
        if (sq === chk) cell.classList.add("chk");
        if (targets.indexOf(sq) >= 0) {
          cell.classList.add(pc ? "cap" : "mv");
        }
      }
    }
  }

  function setState(data) {
    state.fen = data.fen || state.fen;
    state.myTurn = !!data.my_turn;
    state.legal = data.legal || [];
    state.last = data.last || null;
    state.inCheck = !!data.in_check;
    state.over = !!data.over;
    if (state.selected && (!data.my_turn || !state.legal.length)) {
      if (data.my_turn && state.selected && state.legal.some(function (u) { return u.slice(0, 2) === state.selected; })) {
        // ок, оставляем выделение
      } else state.selected = null;
    }
    paint();
  }

  G.chess = {
    mount: mount,
    setState: setState,
    onMove: function (cb) { onMoveCb = cb; },
  };

  /* ---------- соло против бота на /fun/play/chess ---------- */
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
    if (!root || root.dataset.game !== "chess") return;
    var myColor = "w";
    var fen = START_FEN;
    var busy = false;

    root.innerHTML =
      G.bar('<span class="hint-row" style="margin:0">Вы — белые. Сходите первым.</span>' +
        '<button class="btn xm ghost" id="ch-restart">Заново</button>') +
      '<div class="game-area" style="display:grid;place-items:center" id="chess-solo-wrap"></div>';
    G.sub("Шахматы с ботом. Ваш ход — белые.");
    mount(root.querySelector("#chess-solo-wrap"), "host");

    function restart() {
      fen = START_FEN;
      G.hideOverlay(root);
      setState({ fen: fen, my_turn: false, legal: [], over: false });
      serverTurn("");
    }

    function showResult(r) {
      var title, sub;
      if (r.reason === "Мат") {
        var meWon = r.winner === "me";
        title = meWon ? "Шах и мат! Вы выиграли" : "Вам мат";
        sub = meWon ? "Бот капитулировал." : "Бот оказался сильнее. Реванш?";
      } else {
        title = "Ничья";
        sub = r.reason || "Никто не победил.";
      }
      G.overlay(root, title, sub, "Ещё раз", restart);
    }

    function serverTurn(ucv) {
      if (busy || state.over) return;
      busy = true;
      postBot("/api/bot/chess/move", { fen: fen, uci: ucv || "", color: myColor }, function (r) {
        busy = false;
        if (!r.ok) { try { G.sound.states.wrong(); } catch (e) {} return; }
        fen = r.fen;
        setState(r);
        if (r.over) showResult(r);
      });
    }

    onMoveCb = function (uci) {
      // sendMove уже сыграл звук; отправляем ход боту
      serverTurn(uci);
    };
    root.querySelector("#ch-restart").addEventListener("click", restart);
    serverTurn("");
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bootSolo);
  else bootSolo();
})();