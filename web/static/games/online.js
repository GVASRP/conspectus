/* Conspectus · онлайн-комнаты: поллинг, статус, диспетчер по типу игры */
(function () {
  "use strict";
  var G = window.G;
  var INTERVAL = 1500;

  var root, code = null, gameType = null, mySlot = null;
  var pollTimer = null, inFlight = false, mounted = false;
  var tRace = null, raceMounted = false;

  var prev = { over: null, myTurn: null, check: null, status: null };

  var statusEl, titleEl, subEl, rhCode, leaveBtn, codeBox;

  function post(path, data, done) {
    var fd = new FormData();
    if (data) Object.keys(data).forEach(function (k) { fd.append(k, data[k]); });
    fetch(path, { method: "POST", body: fd })
      .then(function (r) { return r.json(); })
      .then(done)
      .catch(function () { if (done) done({ ok: false, error: "Сеть недоступна." }); });
  }

  function setHeader(gameName, sub) {
    if (titleEl) titleEl.textContent = gameName || "Комната";
    if (subEl) subEl.textContent = sub || "";
    if (rhCode) rhCode.textContent = code || "";
  }

  function gotoLobby() {
    window.location.href = "/fun/online";
  }

  function closedRoom(msg) {
    statusEl.innerHTML = '<span class="msg-bad">' + (msg || "Комната закрыта.") + "</span>";
    setTimeout(gotoLobby, 2200);
  }

  function createRoom(game) {
    post("/api/games/create", { game_type: game }, function (d) {
      if (!d.ok) { closedRoom(d.error || "Не удалось создать комнату."); return; }
      code = d.code;
      try { history.replaceState(null, "", "/fun/online/game?code=" + code); } catch (e) {}
      showInvite();
      setHeader(d.game_name || "Комната", "Ждём второго игрока…");
    });
  }

  var inviteWired = false;
  function showInvite() {
    if (!codeBox) return;
    var inv = document.getElementById("invite-code");
    if (inv) inv.textContent = code;
    codeBox.style.display = "";
    var btn = document.getElementById("copy-code");
    if (btn && !inviteWired) {
      inviteWired = true;
      btn.addEventListener("click", function () {
        if (navigator.clipboard) {
          navigator.clipboard.writeText(code).then(function () {
            btn.textContent = "Скопирован ✓";
            setTimeout(function () { btn.textContent = "Скопировать код"; }, 1500);
          });
        }
      });
    }
  }

  function startPolling() {
    poll();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(poll, INTERVAL);
    document.addEventListener("visibilitychange", function () {
      if (document.hidden) { if (pollTimer) { clearInterval(pollTimer); pollTimer = null; } }
      else if (!pollTimer) { poll(); pollTimer = setInterval(poll, INTERVAL); }
    });
  }

  function poll() {
    if (!code || inFlight) return;
    inFlight = true;
    fetch("/api/games/" + code)
      .then(function (r) { return r.json(); })
      .then(handlePoll)
      .catch(function () { try { G.sound.states.wrong(); } catch (e) {} })
      .then(function () { inFlight = false; });
  }

  function handlePoll(d) {
    if (!d.ok) { closedRoom(d.error); return; }
    if (code !== d.room_code) return;
    gameType = gameType || d.game_type;
    mySlot = d.my_slot;
    setHeader(d.game_name, statusSub(d));

    transitions(d);

    if (!mounted) {
      mountModule(d);
      mounted = true;
      if (d.status === "active" && d.state_wait) { /* nothing */ }
    }
    if (mySlot === "host" && d.status === "waiting") showInvite();
    updateModule(d);
    updateStatusBar(d);
  }

  function statusSub(d) {
    var parts = [];
    parts.push("вы: " + (mySlot === "host" ? d.host.username : (d.guest ? "гость(" + d.guest.username + ")" : "?")));
    if (d.status === "waiting") parts.push("жду соперника");
    else if (d.status === "finished") parts.push("партия окончена");
    else if (d.game_type === "chess") parts.push(d.my_turn ? "ваш ход" : "ход соперника");
    else if (d.game_type === "xo") parts.push(d.my_turn ? "ваш ход (" + d.my_sym + ")" : "ход соперника");
    else if (d.started) parts.push("вы — " + progressStr(d));
    return parts.join(" · ");
  }

  function progressStr(d) {
    var l = d.lines, t = d.target;
    var mine = l[mySlot], opp = l[mySlot === "host" ? "guest" : "host"];
    return mine + "/" + t + " линий (у соперника " + (opp || 0) + ")";
  }

  function transitions(d) {
    var nowOver = !!d.over;
    var nowMyTurn = !!d.my_turn;
    if (prev.over === null) { prev.over = nowOver; prev.myTurn = nowMyTurn; prev.check = !!d.in_check; prev.status = d.status; return; }
    if (!prev.over && nowOver && d.status === "finished") {
      var won = d.winner === mySlot;
      var draw = d.game_type !== "chess" && d.draw;
      if (d.game_type === "chess") { won = (d.winner_name === (mySlot === "host" ? d.host.username : (d.guest && d.guest.username))); }
      try {
        if (draw) G.sound.states.flip();
        else G.sound.states[won ? "win" : "gameover"]();
      } catch (e) {}
      showResult(d);
    }
    if (prev.over) { prev.over = nowOver; return; }
    if (d.game_type === "chess" && d.in_check && !prev.check && d.my_turn) {
      try { G.sound.states.capture(); } catch (e) {}
    }
    if (d.status === "active" && prev.status === "waiting" && d.guest) {
      try { G.sound.states.match(); } catch (e) {}
    }
    prev.over = nowOver; prev.myTurn = nowMyTurn; prev.check = !!d.in_check; prev.status = d.status;
  }

  /* ---------- модули ---------- */
  function mountModule(d) {
    if (d.game_type === "chess") {
      G.chess.mount(root, mySlot);
      G.chess.onMove(function (uci) {
        post("/api/games/" + code + "/move", { uci: uci }, function (r) {
          if (!r.ok) { try { G.sound.states.wrong(); } catch (e) {} }
        });
      });
    } else if (d.game_type === "xo") {
      G.xo.mount(root, mySlot);
      G.xo.onMove(function (cell) {
        post("/api/games/" + code + "/move", { cell: String(cell) }, function (r) {
          if (!r.ok) { try { G.sound.states.wrong(); } catch (e) {} }
        });
      });
    } else if (d.game_type === "tetris") {
      buildTetrisArena();
    }
  }

  function buildTetrisArena() {
    var html = G.bar(G.stat("Мои линии", 0) + G.stat("Соперник", 0) + G.stat("Цель", 20) +
      '<button class="btn xm ghost" id="t-ctl"></button>');
    html += '<div class="game-area" style="display:grid;place-items:center"><canvas class="tetris" width="260" height="520"></canvas></div>';
    html += G.hint(G.k("←") + G.k("→") + "·" + G.k("↑") + "поворот ·" + G.k("↓") + "вниз ·" + G.k("Пробел") + "сброс");
    root.innerHTML = html;
    var reg = function (s) { return root.querySelector(s); };
    var ctl = reg("#t-ctl");
    if (ctl) ctl.addEventListener("click", function () {
      if (tStarted) post("/api/games/" + code + "/event", { event: "giveup" });
      else if (mySlot === "host") post("/api/games/" + code + "/event", { event: "start" });
    });
    var map = { ArrowLeft: 1, ArrowRight: 2, ArrowDown: 3, ArrowUp: 4, Space: 5, a: 1, d: 2, s: 3, w: 4, A: 1, D: 2, S: 3, W: 4 };
    document.addEventListener("keydown", function (e) { if (tRace) tRace.onKey(e, map); });
  }

  function ensureTetrisRace(d) {
    if (tRace || !d.seed) return;
    var canvas = root.querySelector("canvas.tetris");
    if (!canvas) return;
    var lastSent = -1;
    tRace = G.tetris.create(canvas, {
      seed: d.seed,
      onLines: function (n) {
        document.getElementById("st-Мои линии").textContent = n;
        if (n > lastSent) { lastSent = n; post("/api/games/" + code + "/event", { event: "lines", value: String(n) }); }
      },
      onTopOut: function () { post("/api/games/" + code + "/event", { event: "topout" }); },
    });
    tRace.start();
  }

  function tetrisState(d) {
    if (d.status === "active" && d.started) ensureTetrisRace(d);
    else if (d.over) { if (tRace) { tRace.destroy(); tRace = null; } }
    updateTetrisControl(d);
    if (d.lines) updateTetrisProgress(d);
  }

  var tStarted = false;
  function updateTetrisControl(d) {
    tStarted = !!d.started;
    var ctl = root && root.querySelector("#t-ctl");
    if (!ctl) return;
    if (d.over) { ctl.disabled = true; ctl.textContent = "Игра окончена"; }
    else if (d.started) { ctl.disabled = false; ctl.textContent = "Сдаться"; }
    else if (mySlot === "host") { ctl.disabled = d.status !== "active"; ctl.textContent = "Старт"; }
    else { ctl.disabled = true; ctl.textContent = "Ждём старта…"; }
  }

  function updateTetrisProgress(d) {
    var mine = document.getElementById("st-Мои линии");
    var opp = document.getElementById("st-Соперник");
    var tgt = document.getElementById("st-Цель");
    if (mine) mine.textContent = (d.lines[mySlot] || 0) + (d.top[mySlot] ? " (выбыл)" : "");
    if (opp) opp.textContent = (d.lines[mySlot === "host" ? "guest" : "host"] || 0) + (d.top[mySlot === "host" ? "guest" : "host"] ? " (выбыл)" : "");
    if (tgt) tgt.textContent = d.target || 20;
  }

  /* ---------- статус-бар и результат ---------- */
  function updateStatusBar(d) {
    if (!statusEl) return;
    var chips = '<span class="chip">' + d.game_name + "</span>" +
      '<span class="chip chip-' + (d.status === "waiting" ? "warn" : d.status === "finished" ? "done" : "ok") + '">' +
      (d.status === "waiting" ? "ждём соперника" : d.status === "finished" ? "партия окончена" : "идёт игра") + "</span>";
    var opp = d.guest ? (d.guest.username === d.host.username ? d.host.username : d.guest.username) : null;
    chips += '<span class="chip">код: ' + code + "</span>";
    if (opp) chips += '<span class="chip">против: ' + opp + "</span>";
    statusEl.innerHTML = chips;
  }

  function showResult(d) {
    if (document.querySelector(".overlay")) return;
    var won = mySlot && d.winner === mySlot;
    var draw = d.game_type !== "chess" && d.draw;
    var title, sub;
    if (d.game_type === "chess") {
      var iWon = (d.winner_name === (mySlot === "host" ? d.host.username : (d.guest ? d.guest.username : null)));
      if (d.reason === "Ничья") { title = "Ничья"; }
      else { title = iWon ? "Мая! Вы выиграли" : "Вам мат"; }
      sub = "Партия завершена. " + (d.reason || "");
    } else if (draw) {
      title = "Ничья"; sub = "Никто не смог победить!";
    } else {
      title = won ? "Победа!" : "Поражение";
      sub = won ? "Так держать!" : "Бывает — реванш?";
    }
    var o = document.createElement("div");
    o.className = "overlay";
    o.style.display = "grid";
    o.innerHTML = "<h2>" + title + "</h2><p>" + sub + "</p>" +
      '<div class="btn-row"><button class="btn xm" id="ov-rematch">Реванш</button>' +
      '<button class="btn xm ghost" id="ov-exit">Выйти</button></div>';
    statusEl.appendChild(o);
    o.querySelector("#ov-rematch").addEventListener("click", function () {
      post("/api/games/" + code + "/rematch", {}, function (r) {
        if (!r.ok) { try { G.sound.states.wrong(); } catch (e) {} return; }
        mounted = false; raceMounted = false; tRace = null;
        root.innerHTML = ""; o.remove();
        prev.over = false; prev.status = "waiting";
        poll();
      });
    });
    o.querySelector("#ov-exit").addEventListener("click", function () {
      post("/api/games/" + code + "/leave", {}, gotoLobby);
    });
  }

  function updateModule(d) {
    if (d.game_type === "chess") G.chess.setState(d);
    else if (d.game_type === "xo") G.xo.setState(d);
    else if (d.game_type === "tetris") tetrisState(d);
  }

  /* ---------- вход ---------- */
  function init(el, roomCode, roomGame) {
    root = el;
    statusEl = document.getElementById("room-status");
    titleEl = document.getElementById("rh-title");
    subEl = document.getElementById("rh-sub");
    rhCode = document.getElementById("rh-code");
    leaveBtn = document.getElementById("rh-leave");
    codeBox = document.getElementById("code-box");
    if (leaveBtn) leaveBtn.addEventListener("click", function () {
      if (!code) { gotoLobby(); return; }
      post("/api/games/" + code + "/leave", {}, gotoLobby);
    });
    if (roomCode) { code = roomCode; startPolling(); }
    else if (roomGame) { createRoom(roomGame); startPolling(); }
    else { closedRoom("Нет параметров комнаты."); }
  }

  G.online = { init: init };
})();