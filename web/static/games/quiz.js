/* Conspectus · Квиз по конспектам */
(function () {
  "use strict";
  var G = window.G;
  var streak = 0;
  var session = 0;
  var answered = 0;
  var best = G.best("quizbest");
  var locked = false;
  var LETTERS = ["А", "Б", "В", "Г"];

  function paint() {
    var el = document.querySelector("#st-Серия");
    if (el) el.textContent = streak;
    var sess = document.querySelector("#st-Ответы");
    if (sess) sess.textContent = session + " / " + answered;
    var b = document.querySelector("#st-Рекорд");
    if (b) b.textContent = best;
  }

  async function load() {
    var feed = G.$("#q-feedback");
    if (feed) feed.textContent = "Ищу вопрос по твоим конспектам…";
    var hint = G.$("#q-load");
    if (hint) hint.style.display = "block";
    try {
      var res = await fetch("/api/fun/quiz");
      var data = await res.json();
      if (hint) hint.style.display = "none";
      if (!data.ok) {
        renderEmpty(data.error);
        return;
      }
      if (!data.question || !data.question.options || data.question.options.length < 2) {
        renderEmpty("Пока не хватает вариантов ответа — добавь больше предметов или конспектов.");
        return;
      }
      renderQuestion(data.question);
    } catch (e) {
      if (hint) hint.style.display = "none";
      renderEmpty("Не получилось загрузить вопрос. Попробуй ещё раз.");
    }
  }

  function renderEmpty(msg) {
    G.hideOverlay(G.$("#quiz-area"));
    var root = G.$("#q-body");
    if (!root) return;
    root.innerHTML =
      '<div class="quiz-q"><div class="q-sub">· квиз ·</div><div class="q-title">' + msg + "</div>" +
      '<p class="quiz-streak">Загляни в конспекты или добавь новые.</p></div>' +
      '<button class="btn" id="q-again">Ещё раз</button>';
    var btn = G.$("#q-again");
    if (btn) btn.addEventListener("click", load);
  }

  function renderQuestion(q) {
    locked = false;
    G.hideOverlay(G.$("#quiz-area"));
    var root = G.$("#q-body");
    var opts = q.options.map(function (o, i) {
      return '<button class="quiz-opt" data-id="' + o.id + '"><span class="qi">' +
        LETTERS[i] + "</span>" + esc(o.name) + "</button>";
    }).join("");
    root.innerHTML =
      '<div class="quiz-q">' +
      '<div class="q-sub">Вопрос по твоему конспекту</div>' +
      '<div class="q-title">' + esc(q.title) + "</div>" +
      '<div class="q-snippet">' + esc(q.snippet) + "</div>" +
      "</div>" +
      '<div class="quiz-opts" id="q-opts">' + opts + "</div>" +
      '<div class="quiz-feedback" id="q-feedback"></div>' +
      '<div class="quiz-streak" id="q-streak"></div>' +
      '<button class="btn xm ghost" id="q-next" style="margin-top:6px">Следующий вопрос</button>';
    G.$("#q-next").style.display = "none";
    var feed = G.$("#q-feedback");
    feed.textContent = "Какой это предмет?";
    document.querySelector("#q-opts").addEventListener("click", function (e) {
      var btn = e.target.closest(".quiz-opt");
      if (btn && !locked) pick(btn, q);
    });
    G.$("#q-next").addEventListener("click", load);
  }

  function pick(btn, q) {
    locked = true;
    answered++;
    var id = parseInt(btn.dataset.id, 10);
    var correct = id === q.answer_id;
    if (correct) {
      streak++; session++;
      if (streak > best) { best = streak; G.best("quizbest", streak); }
    } else {
      streak = 0;
    }
    document.querySelectorAll("#q-opts .quiz-opt").forEach(function (b) {
      b.disabled = true;
      var bid = parseInt(b.dataset.id, 10);
      if (bid === q.answer_id) b.classList.add("right");
      else if (b === btn) b.classList.add("wrong");
    });
    var feed = G.$("#q-feedback");
    feed.textContent = correct
      ? "Верно! Это «" + q.answer_name + "»."
      : "Это «" + q.answer_name + "». Запиши на память!";
    var st = G.$("#q-streak");
    st.textContent = "Серия верных: " + streak + " · рекорд: " + best;
    G.$("#q-next").style.display = "inline-flex";
    paint();
  }

  function esc(s) {
    var d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function boot() {
    var root = G.$("#g-root");
    G.sub("Угадывай, из какого ты предмета видишь конспект. Вопросы берутся из твоих записей.");
    root.innerHTML =
      G.bar(G.stat("Ответы", "0 / 0") + G.stat("Серия", 0) + G.stat("Рекорд", best)) +
      '<div class="quiz-card"><div id="q-load" style="text-align:center;color:var(--muted)"></div><div id="q-body"></div></div>';
    load();
  }

  boot();
})();