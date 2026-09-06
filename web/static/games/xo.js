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
})();