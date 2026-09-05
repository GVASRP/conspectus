/* Conspectus · UI microlayers */
(function () {
  'use strict';

  /* --- часы в навбаре --- */
  var clock = document.querySelector('.clock');
  var dateEl = document.querySelector('.date-chunk');
  function tick() {
    var d = new Date();
    var p = function (n) { return (n < 10 ? '0' : '') + n; };
    if (clock) clock.textContent = p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
    if (dateEl) {
      var days = ['вс', 'пн', 'вт', 'ср', 'чт', 'пт', 'сб'];
      dateEl.textContent = d.getDate() + '.' + p(d.getMonth() + 1) + ' · ' + days[d.getDay()];
    }
  }
  tick();
  setInterval(tick, 1000);

  /* --- появление при скролле --- */
  var revealEls = document.querySelectorAll('.reveal');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); }
      });
    }, { threshold: 0.12 });
    revealEls.forEach(function (el) { io.observe(el); });
  } else {
    revealEls.forEach(function (el) { el.classList.add('in'); });
  }

  /* --- анимированные счётчики --- */
  document.querySelectorAll('.num[data-count]').forEach(function (el) {
    var target = parseInt(el.dataset.count, 10) || 0;
    var dur = 900, start = null;
    function step(ts) {
      if (!start) start = ts;
      var p = Math.min((ts - start) / dur, 1);
      var eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased);
      if (p < 1) requestAnimationFrame(step);
      else el.textContent = target;
    }
    if ('IntersectionObserver' in window && io) {
      var io2 = new IntersectionObserver(function (en) {
        if (en[0].isIntersecting) { requestAnimationFrame(step); io2.disconnect(); }
      }, { threshold: 0.4 });
      io2.observe(el);
    } else requestAnimationFrame(step);
  });

  /* --- курсор-glow (только мышь/desktop) --- */
  var glowEl = document.createElement('div');
  glowEl.className = 'glow-cursor';
  document.body.appendChild(glowEl);
  var glowOn = false, fine = window.matchMedia('(pointer:fine)').matches;
  if (fine) {
    var rx = 0, ry = 0, tx = 0, ty = 0, raf = null;
    window.addEventListener('mousemove', function (e) {
      tx = e.clientX; ty = e.clientY; glowOn = true;
      if (!raf) {
        raf = requestAnimationFrame(function loop() {
          rx += (tx - rx) * 0.14; ry += (ty - ry) * 0.14;
          glowEl.style.transform = 'translate3d(' + (rx - 260) + 'px,' + (ry - 260) + 'px,0)';
          glowEl.style.opacity = 1;
          raf = requestAnimationFrame(loop);
        });
      }
    });
    document.addEventListener('mouseleave', function () { glowEl.style.opacity = 0; });
  } else {
    glowEl.style.display = 'none';
  }

  /* --- централизованный поиск: input[data-search] фильтрует .s-item --- */
  document.querySelectorAll('[data-search]').forEach(function (inp) {
    inp.addEventListener('input', function () {
      var v = inp.value.toLowerCase().trim();
      var items = document.querySelectorAll(inp.dataset.search + ' .s-item');
      items.forEach(function (el) {
        el.style.display = (!v || (el.dataset.s || '').includes(v)) ? '' : 'none';
      });
    });
  });

  /* --- прогресс чтения --- */
  var pbar = document.querySelector('.pbar');
  if (pbar) {
    var doc = document.documentElement;
    function pbmove() {
      var h = doc.scrollHeight - window.innerHeight;
      pbar.style.width = (h > 0 ? (window.scrollY / h) * 100 : 0) + '%';
    }
    window.addEventListener('scroll', pbmove, { passive: true });
    pbmove();
  }

  /* --- копирование: [data-copy] копирует текст поля-мишени --- */
  document.querySelectorAll('[data-copy]').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var src = document.querySelector(btn.dataset.copy);
      if (!src) return;
      var text = src.innerText || src.value || '';
      var done = function () {
        var old = btn.textContent;
        btn.textContent = 'Скопировано ✓';
        setTimeout(function () { btn.textContent = old; }, 1500);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done).catch(function () { fallbackCopy(text); done(); });
      } else { fallbackCopy(text); done(); }
      function fallbackCopy(t) {
        var ta = document.createElement('textarea');
        ta.value = t; ta.style.position = 'fixed'; ta.style.opacity = '0';
        document.body.appendChild(ta); ta.select();
        try { document.execCommand('copy'); } catch (e) {}
        document.body.removeChild(ta);
      }
    });
  });

  /* --- TOTP-поля: только цифры --- */
  document.querySelectorAll('input[inputmode="numeric"]').forEach(function (inp) {
    inp.addEventListener('input', function () { inp.value = inp.value.replace(/\D/g, '').slice(0, 6); });
  });

  /* --- счётчик символов для textarea.content --- */
  var ta = document.querySelector('textarea[name="content"]');
  var taCount = document.querySelector('.ta-count');
  if (ta && taCount) {
    var upd = function () {
      var n = ta.value.length;
      taCount.textContent = n > 0 ? n.toLocaleString('ru-RU') + ' символов' : '';
    };
    ta.addEventListener('input', upd); upd();
  }
})();