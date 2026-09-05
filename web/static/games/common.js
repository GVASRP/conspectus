/* Conspectus · общие помощники для мини-игр */
(function () {
  "use strict";
  window.G = {
    $: function (sel) { return document.querySelector(sel); },
    sub: function (t) { var s = document.querySelector("#gsub"); if (s) s.textContent = t; },
    best: function (key, val) {
      if (val === undefined) {
        var raw = localStorage.getItem("csp_" + key);
        return raw ? parseInt(raw, 10) : 0;
      }
      localStorage.setItem("csp_" + key, String(val));
      return val;
    },
    stat: function (label, value) {
      return '<span class="gstat"><span>' + label + '</span><b id="st-' + label + '">' + value + "</b></span>";
    },
    bar: function (html) {
      return '<div class="gbar">' + html + "</div>";
    },
    hint: function (html) {
      return '<div class="hint-row">' + html + "</div>";
    },
    k: function (txt) { return '<span class="k">' + txt + "</span>"; },
    overlay: function (root, title, sub, btnText, onBtn) {
      var o = document.createElement("div");
      o.className = "overlay";
      o.style.display = "grid";
      o.innerHTML =
        '<h2>' + title + "</h2>" +
        "<p>" + sub + "</p>" +
        '<button class="btn xm" id="ov-btn">' + btnText + "</button>";
      o.addEventListener("click", function (e) {
        if (e.target.id === "ov-btn" && onBtn) onBtn();
      });
      root.appendChild(o);
    },
    hideOverlay: function (root) {
      var o = root.querySelector(".overlay");
      if (o) o.remove();
    },
  };
})();