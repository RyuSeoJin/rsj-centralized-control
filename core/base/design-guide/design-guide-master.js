/* ============================================================
   design-guide-master.js — 셸 동작 정본 (v2.1 · 2026-08-05)
   ------------------------------------------------------------
   테마 토글 · 사이드바 서랍 · 표 도구(검색·필터·정렬)를 담습니다.
   CSS와 같은 방식으로 다룹니다 — 규칙서는 <script src>로 참조하고,
   산출물은 생성 시점 사본을 <script>에 inline합니다(네트워크 요청 0건).

   <head>에서 동기로 불러야 합니다. 테마는 첫 페인트 전에 적용되고,
   DOM을 만지는 나머지는 DOMContentLoaded 뒤에 붙습니다.

   마크업 약속
   · 테마 토글 버튼      <button data-theme-toggle>
   · 사이드바 서랍       .side / .backdrop / .side-toggle
   · 표 도구            <div class="tbl-tools" data-table="표id">
                          <input class="tbl-search">
                          <button class="fbtn" data-col="3" data-val="Fail">
                          <button class="fbtn" data-attr="issue" data-val="1">
                          <span class="tbl-count"></span>
                        </div>
                        data-col은 그 열의 글자를, data-attr은 행의 data-* 값을
                        봅니다. 화면에 안 적힌 기준으로 거를 때 뒤엣것을 씁니다
   · 정렬               <th class="sortable">   (숫자 열은 class="num sortable")
   · 탭                 <div class="tabs" data-tabs="묶음이름">
                          <button class="tab-btn" data-panel="패널id">라벨</button>
                        </div>
                        <div class="tab-panel" id="패널id"> … </div>
                        스크립트가 꺼져 있어도 **첫 패널은 보입니다** — 감추는 쪽을
                        JS가 붙이므로 자바스크립트 없이도 문서가 죽지 않습니다
   ============================================================ */
(function () {
  var KEY = 'qavn-theme';
  var root = document.documentElement;

  function applyTheme(t) { root.setAttribute('data-theme', t); }

  /* 기본값은 라이트 고정입니다. OS 설정을 따라가면 처음 여는 사람마다 다른 화면을
     보게 되고, 문서에 첨부한 화면과도 어긋납니다. 다크는 고른 사람에게만 남습니다. */
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  applyTheme(saved === 'dark' ? 'dark' : 'light');

  function ready(fn) {
    if (document.readyState !== 'loading') { fn(); }
    else { document.addEventListener('DOMContentLoaded', fn); }
  }

  function each(sel, fn, ctx) {
    var list = (ctx || document).querySelectorAll(sel);
    for (var i = 0; i < list.length; i++) { fn(list[i], i); }
  }

  /* ---------- 테마 토글 ---------- */
  function initTheme() {
    var btn = document.querySelector('[data-theme-toggle]');
    if (!btn) { return; }
    function label() {
      var dark = root.getAttribute('data-theme') === 'dark';
      btn.textContent = dark ? '라이트' : '다크';
      btn.setAttribute('aria-label', dark ? '라이트 테마로 전환' : '다크 테마로 전환');
    }
    label();
    btn.addEventListener('click', function () {
      var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      try { localStorage.setItem(KEY, next); } catch (e) {}
      label();
    });
  }

  /* ---------- 사이드바 서랍 (좁은 화면) ---------- */
  function initDrawer() {
    var side = document.querySelector('.side');
    var back = document.querySelector('.backdrop');
    var tog = document.querySelector('.side-toggle');
    if (!side) { return; }
    function close() {
      side.classList.remove('open');
      if (back) { back.classList.remove('on'); }
    }
    if (tog) {
      tog.addEventListener('click', function () {
        side.classList.toggle('open');
        if (back) { back.classList.toggle('on'); }
      });
    }
    if (back) { back.addEventListener('click', close); }
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') { close(); }
    });
    each('.side a', function (a) {
      a.addEventListener('click', function () {
        if (window.innerWidth <= 980) { close(); }
      });
    });
  }

  /* ---------- 사이드바 목차 — 지금 읽는 절 표시 ---------- */
  function initScrollSpy() {
    var subs = [];
    each('.nav-sub[href^="#"]', function (a) {
      var el = document.getElementById(a.getAttribute('href').slice(1));
      if (el) { subs.push({ a: a, el: el }); }
    });
    if (!subs.length) { return; }
    function mark() {
      var y = window.scrollY + 90, cur = subs[0];
      for (var i = 0; i < subs.length; i++) {
        if (subs[i].el.offsetTop <= y) { cur = subs[i]; }
      }
      for (var j = 0; j < subs.length; j++) {
        subs[j].a.classList.toggle('on', subs[j] === cur);
      }
    }
    mark();
    window.addEventListener('scroll', mark, { passive: true });
  }

  /* ---------- 표 도구 — 검색·필터·정렬 ---------- */
  function cellText(row, i) {
    var td = row.cells[i];
    return td ? (td.textContent || '').trim() : '';
  }

  function numOf(s) {
    var m = String(s).replace(/,/g, '').match(/-?\d+(\.\d+)?/);
    return m ? parseFloat(m[0]) : null;
  }

  function initTable(tools) {
    var table = document.getElementById(tools.getAttribute('data-table'));
    if (!table) { return; }
    var body = table.tBodies[0];
    if (!body) { return; }
    var rows = [].slice.call(body.rows);
    var search = tools.querySelector('.tbl-search');
    var count = tools.querySelector('.tbl-count');
    var buttons = [].slice.call(tools.querySelectorAll('.fbtn[data-col],.fbtn[data-attr]'));
    var active = null;

    function refresh() {
      var q = search ? search.value.trim().toLowerCase() : '';
      var shown = 0;
      for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        var okText = !q || (row.textContent || '').toLowerCase().indexOf(q) >= 0;
        var okFilter = true;
        if (active) {
          var want = active.getAttribute('data-val');
          var attr = active.getAttribute('data-attr');
          okFilter = attr
            ? row.getAttribute('data-' + attr) === want
            : cellText(row, parseInt(active.getAttribute('data-col'), 10)).indexOf(want) >= 0;
        }
        var show = okText && okFilter;
        row.classList.toggle('row-hide', !show);
        if (show) { shown++; }
      }
      if (count) {
        count.textContent = shown === rows.length
          ? rows.length + '건'
          : shown + ' / ' + rows.length + '건';
      }
    }

    if (search) { search.addEventListener('input', refresh); }
    buttons.forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (active === btn) { active = null; } else { active = btn; }
        buttons.forEach(function (b) { b.classList.toggle('on', b === active); });
        refresh();
      });
    });

    each('th.sortable', function (th, idx) {
      var col = th.cellIndex;
      th.addEventListener('click', function () {
        var asc = !th.classList.contains('sort-asc');
        each('th.sortable', function (o) {
          o.classList.remove('sort-asc', 'sort-desc');
        }, table);
        th.classList.add(asc ? 'sort-asc' : 'sort-desc');
        var sorted = rows.slice().sort(function (a, b) {
          var x = cellText(a, col), y = cellText(b, col);
          var nx = numOf(x), ny = numOf(y);
          var r = (nx !== null && ny !== null) ? nx - ny : x.localeCompare(y, 'ko');
          return asc ? r : -r;
        });
        for (var i = 0; i < sorted.length; i++) { body.appendChild(sorted[i]); }
      });
    }, table);

    refresh();
  }

  /* 탭 — 칩 하나가 패널 하나를 켠다. 감추는 일을 JS가 맡으므로 스크립트가
     꺼져 있으면 패널이 전부 보인다(문서가 죽지 않는다). */
  function initTabs(box) {
    var btns = [].slice.call(box.querySelectorAll('.tab-btn'));
    if (!btns.length) { return; }
    var panels = btns.map(function (b) {
      return document.getElementById(b.getAttribute('data-panel'));
    });
    function show(i) {
      btns.forEach(function (b, j) {
        var on = i === j;
        b.classList.toggle('on', on);
        b.setAttribute('aria-selected', on ? 'true' : 'false');
        if (panels[j]) { panels[j].hidden = !on; }
      });
    }
    btns.forEach(function (b, i) {
      b.setAttribute('role', 'tab');
      b.addEventListener('click', function () { show(i); });
    });
    box.setAttribute('role', 'tablist');
    // 처음 칠 자리는 .on이 붙은 칩, 없으면 첫째
    var start = 0;
    for (var k = 0; k < btns.length; k++) {
      if (btns[k].classList.contains('on')) { start = k; break; }
    }
    show(start);
  }

  ready(function () {
    initTheme();
    initDrawer();
    initScrollSpy();
    each('.tbl-tools[data-table]', initTable);
    each('.tabs[data-tabs]', initTabs);
  });
})();
