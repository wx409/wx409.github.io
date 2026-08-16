/* ============================================================================
 * 全站搜索引擎（site_search_engine.js）
 * ----------------------------------------------------------------------------
 * 纯静态、零依赖：fetch data/site_search_index.json，自实现多词 AND 匹配 + 加权打分。
 * 数据源唯一：data/site_search_index.json（488 条：歌曲/城市/演出/小酒馆/指南/页面）
 * 匹配规则：
 *   - 空格分词，多词 AND（全部命中才算）
 *   - 打分：title 命中 +40 / keywords 命中 +25 / text 命中 +8
 *   - 完全匹配 +30 / 前缀匹配 +15（title 或 keywords）
 *   - 命中词高亮（<mark>）
 * ========================================================================== */
(function () {
  'use strict';

  var INDEX_URL = 'data/site_search_index.json';
  var MAX_RESULTS = 30;
  var indexData = null;     // 索引缓存
  var indexState = 'pending'; // pending | ready | failed
  var waiters = [];

  /* ---------------- 工具 ---------------- */
  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function norm(s) {
    return String(s == null ? '' : s)
      .replace(/[《》「」『』]/g, '')
      .replace(/\s+/g, '')
      .toLowerCase()
      .normalize('NFD').replace(/[\u0300-\u036f]/g, '');
  }
  function highlight(text, terms) {
    var t = esc(text);
    terms.forEach(function (term) {
      if (!term) return;
      var re = new RegExp('(' + term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + ')', 'gi');
      t = t.replace(re, '<mark>$1</mark>');
    });
    return t;
  }
  function snippet(text, terms, maxLen) {
    maxLen = maxLen || 120;
    var t = String(text == null ? '' : text);
    if (t.length <= maxLen) return t;
    // 尝试从第一个命中词附近截取
    var idx = -1;
    terms.forEach(function (term) {
      var i = t.toLowerCase().indexOf(term);
      if (i >= 0 && (idx < 0 || i < idx)) idx = i;
    });
    var start = Math.max(0, (idx > 0 ? idx - 20 : 0));
    var prefix = start > 0 ? '…' : '';
    return prefix + t.substr(start, maxLen) + '…';
  }

  /* ---------------- 索引加载 ---------------- */
  function loadIndex() {
    if (indexState !== 'pending') return;
    indexState = 'loading';
    fetch(INDEX_URL)
      .then(function (r) {
        if (!r.ok) throw new Error('index ' + r.status);
        return r.json();
      })
      .then(function (j) {
        indexData = Array.isArray(j) ? j : [];
        indexState = 'ready';
        fireWaiters();
      })
      .catch(function () {
        indexState = 'failed';
        fireWaiters();
      });
  }
  function whenReady(fn) {
    if (indexState === 'ready') { fn(); return; }
    if (indexState === 'failed') return;
    waiters.push(fn);
    loadIndex();
  }
  function fireWaiters() {
    var q = waiters;
    waiters = [];
    q.forEach(function (fn) { try { fn(); } catch (e) {} });
  }

  /* ---------------- 打分匹配 ---------------- */
  var TYPE_LABEL = {
    song: '歌曲', city: '城市', concert: '演出',
    episode: '小酒馆', guide: '指南', page: '页面'
  };
  var TYPE_ICON = {
    song: '🎵', city: '🏙️', concert: '🎤',
    episode: '🍷', guide: '🧭', page: '📄'
  };

  function matchEntry(entry, terms) {
    var title = norm(entry.title || '');
    var text = norm(entry.text || '');
    var kws = (entry.keywords || []).map(norm);
    var score = 0;
    var allHit = true;
    terms.forEach(function (term) {
      var hitTitle = title.indexOf(term) >= 0;
      var hitKw = kws.some(function (k) { return k.indexOf(term) >= 0; });
      var hitText = text.indexOf(term) >= 0;
      if (!hitTitle && !hitKw && !hitText) { allHit = false; return; }
      if (hitTitle) {
        score += 40;
        if (title === term) score += 30;
        else if (title.indexOf(term) === 0) score += 15;
      }
      if (hitKw) {
        score += 25;
        if (kws.some(function (k) { return k === term; })) score += 15;
      }
      if (hitText) score += 8;
    });
    if (!allHit) return null;
    return { entry: entry, score: score };
  }

  function search(q) {
    var raw = String(q || '').trim();
    if (!raw) return [];
    var terms = raw.split(/\s+/).map(norm).filter(Boolean);
    if (!terms.length) return [];
    var hits = [];
    indexData.forEach(function (entry) {
      var m = matchEntry(entry, terms);
      if (m) hits.push(m);
    });
    hits.sort(function (a, b) { return b.score - a.score; });
    return hits.slice(0, MAX_RESULTS);
  }

  /* ---------------- 渲染 ---------------- */
  function buildResultHtml(hit) {
    var e = hit.entry;
    var type = e.type || 'page';
    var label = TYPE_LABEL[type] || '页面';
    var icon = TYPE_ICON[type] || '📄';
    var terms = String(document.getElementById('searchInput').value || '')
      .split(/\s+/).map(norm).filter(Boolean);
    var kws = (e.keywords || []).slice(0, 5);
    var kwHtml = kws.length
      ? '<div class="sr-kws">' + kws.map(function (k) {
          return '<span class="sr-kw">' + highlight(k, terms) + '</span>';
        }).join('') + '</div>'
      : '';
    return '<a class="sr-card" href="' + esc(e.url) + '" target="_blank" rel="noopener">' +
      '<div class="sr-top">' +
      '<span class="sr-badge sr-badge-' + esc(type) + '">' + icon + ' ' + esc(label) + '</span>' +
      '<span class="sr-title">' + highlight(e.title || '', terms) + '</span>' +
      '</div>' +
      '<div class="sr-text">' + highlight(snippet(e.text || '', terms), terms) + '</div>' +
      kwHtml +
      '</a>';
  }

  function render(hits, q) {
    var out = document.getElementById('searchResults');
    if (!out) return;
    var countEl = document.getElementById('resultCount');
    if (!hits.length) {
      out.innerHTML = '<div class="sr-empty">没有找到与「' + esc(q) + '」相关的内容，换个关键词试试～</div>';
      if (countEl) countEl.textContent = '0';
      return;
    }
    if (countEl) countEl.textContent = String(hits.length);
    out.innerHTML = hits.map(buildResultHtml).join('');
  }

  function runSearch(q) {
    var status = document.getElementById('searchStatus');
    if (indexState === 'failed') {
      if (status) status.textContent = '索引加载失败，请刷新重试。';
      return;
    }
    if (indexState !== 'ready') {
      if (status) status.textContent = '索引加载中…';
    }
    whenReady(function () {
      if (status) status.textContent = '';
      render(search(q), q);
    });
  }

  /* ---------------- 初始化 ---------------- */
  function init() {
    var input = document.getElementById('searchInput');
    var btn = document.getElementById('searchBtn');
    if (!input) return;
    loadIndex();
    function go() { runSearch(input.value); }
    input.addEventListener('keydown', function (e) { if (e.key === 'Enter') go(); });
    if (btn) btn.addEventListener('click', go);
    // URL ?q= 参数自动执行
    var m = /[?&]q=([^&]+)/.exec(window.location.search || '');
    if (m) {
      var q = decodeURIComponent(m[1].replace(/\+/g, ' '));
      if (q) {
        input.value = q;
        go();
        input.focus();
      }
    } else {
      input.focus();
    }
    // 建议 chip
    document.querySelectorAll('.chip').forEach(function (c) {
      c.addEventListener('click', function () {
        var v = c.getAttribute('data-q') || '';
        input.value = v;
        go();
      });
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  // 调试导出
  if (typeof window !== 'undefined') {
    window.SiteSearch = {
      search: function (q) {
        if (indexState !== 'ready' && indexData === null) loadIndex();
        return indexData ? search(q) : [];
      },
      indexSize: function () { return indexData ? indexData.length : 0; }
    };
  }
})();
