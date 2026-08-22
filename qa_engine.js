/**
 * 王晰 AI 问答浮动助手（qa_engine.js v2 · 全站通用）
 * 纯静态、零依赖：fetch data/qa_bank.json，右下角浮动按钮 → 弹出问答面板，任何页面可用。
 * 设计：离线预生成问答 + 前端语义检索（零后端、零 key、零成本），随提问增量扩充。
 * 用法：页面里加 <script src="/qa_engine.js"></script> 即可（自动注入浮动助手 UI）。
 */
(function () {
  var INDEX_URL = 'qa_engine.js'.indexOf('/') >= 0
    ? 'data/qa_bank.json'
    : 'data/qa_bank.json';
  // 兼容：无论脚本在哪个层级被引用，都用站点根的 data/qa_bank.json
  INDEX_URL = (document.querySelector('base') && document.querySelector('base').href)
    ? new URL('data/qa_bank.json', document.querySelector('base').href).href
    : 'data/qa_bank.json';
  // 若页面已在子目录（如 /live/、/tavern/），用绝对路径更稳
  if (window.location.pathname.split('/').length > 2) {
    INDEX_URL = 'https://wx409.github.io/data/qa_bank.json';
  }

  var bank = null;
  var bankState = 'pending';
  var widgetInjected = false;

  // 同义词折叠：把常见同义表达归一，提升语义匹配
  var SYNONYMS = [
    ['下降', '下滑', '跌落', '下跌', '掉', '跌'],
    ['上涨', '上升', '涨', '升'],
    ['最多', '最常', '经常', '频繁', '次数最多'],
    ['顶点', '峰值', '最高', '最火', '最红', '最好'],
    ['演唱', '唱', '唱过', '演绎', '表演'],
    ['歌曲', '歌', '曲目', '作品', '曲子'],
    ['巡回', '巡演', '演唱会', '个唱'],
    ['制作人', '监制', 'producer'],
    ['词作者', '作词', '写词', '词人'],
    ['曲作者', '作曲', '写曲', '编曲'],
  ];
  function norm(s) {
    var t = String(s || '').toLowerCase().replace(/[，。！？、；：""''《》【】（）()\s\-—·]/g, '');
    SYNONYMS.forEach(function (grp) {
      for (var i = 1; i < grp.length; i++) {
        t = t.split(grp[i]).join(grp[0]);
      }
    });
    return t;
  }
  function bigrams(s) {
    var b = {};
    for (var i = 0; i < s.length - 1; i++) {
      b[s.slice(i, i + 2)] = true;
    }
    return b;
  }

  function scoreItem(item, q) {
    var nq = norm(q);
    var qb = bigrams(nq);
    var score = 0, hit = false;
    // 问题/别名：字级 bigram 重合度
    (item.aliases || []).concat([item.question]).forEach(function (a) {
      var na = norm(a);
      if (na && (nq.indexOf(na) >= 0 || na.indexOf(nq) >= 0)) { score += 50; hit = true; }
      else if (na && nq.length >= 2) {
        var overlap = 0, total = 0;
        var ab = bigrams(na);
        for (var b in qb) { if (ab[b]) overlap++; total++; }
        if (total > 0 && overlap / total >= 0.4) { score += 20 * (overlap / total); hit = true; }
      }
    });
    // 关键词命中（归一后）
    var counted = {};
    (item.keywords || []).forEach(function (k) {
      var nk = norm(k);
      if (nk && nk.length >= 2 && !counted[nk] && nq.indexOf(nk) >= 0) { score += 15; hit = true; counted[nk] = true; }
    });
    if (!hit && item.category && nq.indexOf(norm(item.category)) >= 0) { score += 8; hit = true; }
    return hit ? score : 0;
  }
  function esc(s) {
    return String(s || '').replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function loadBank(cb) {
    if (bankState === 'ready') { cb && cb(); return; }
    if (bankState === 'loading') return;
    bankState = 'loading';
    fetch(INDEX_URL, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { bank = j; bankState = 'ready'; cb && cb(); })
      .catch(function () { bankState = 'failed'; cb && cb(); });
  }

  function answer(q) {
    if (!bank || !bank.items) return [];
    return bank.items.map(function (it) { return { item: it, score: scoreItem(it, q) }; })
      .filter(function (x) { return x.score > 0; })
      .sort(function (a, b) { return b.score - a.score; });
  }

  // ===== 歌曲档案参数化查询：识别歌名 → 实时从 song_index_lite.json 查 =====
  var songIndex = null;
  var songState = 'pending';
  function loadSongIndex(cb) {
    if (songState === 'ready') { cb && cb(); return; }
    if (songState === 'loading') return;
    songState = 'loading';
    var siUrl = INDEX_URL.replace('qa_bank.json', 'song_index_lite.json');
    fetch(siUrl, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { songIndex = j.songs || {}; songState = 'ready'; cb && cb(); })
      .catch(function () { songState = 'failed'; cb && cb(); });
  }

  // 从问题里识别歌名（最长歌名优先，避免短名误匹配）
  function findSong(q) {
    if (!songIndex) return null;
    var nq = norm(q);
    var best = null, bestLen = 0;
    for (var key in songIndex) {
      var e = songIndex[key];
      var nn = norm(e.name);
      if (nn.length < 2) continue;
      if (nq.indexOf(nn) >= 0 && nn.length > bestLen) {
        best = e; bestLen = nn.length;
      }
    }
    return best;
  }

  function songCard(e) {
    var lines = [];
    lines.push('<div class="qaw-card">');
    lines.push('<div class="qaw-q">《' + esc(e.name) + '》</div>');
    var cr = e.credits || {};
    var roleMap = { lyricist: '作词', composer: '作曲', producer: '制作人', arranger: '编曲', backing: '和声', mixing: '混音', guitar: '吉他', strings: '弦乐' };
    var crLines = [];
    for (var k in roleMap) { if (cr[k]) crLines.push(roleMap[k] + '：' + esc(cr[k])); }
    if (crLines.length) lines.push('<div class="qaw-a">' + crLines.join('<br>') + '</div>');
    else lines.push('<div class="qaw-a">（翻唱/资料歌，无词曲制作信息）</div>');
    var meta = [];
    if (e.release && e.release !== '-') meta.push('发行 ' + esc(e.release));
    if (e.attr) meta.push(esc(e.attr));
    if (e.show_count) meta.push('演唱 ' + e.show_count + ' 次');
    if (e.cities && e.cities.length) {
      meta.push('演出城市：' + e.cities.slice(0, 12).join('、') + (e.cities.length > 12 ? ' 等' + e.cities.length + '城' : ''));
    }
    if (meta.length) lines.push('<div class="qaw-src">' + esc(meta.join(' · ')) + '</div>');
    lines.push('</div>');
    return lines.join('');
  }

  // ===== 巡演歌单参数化查询：识别巡次/城市 → 实时查 setlists.json =====
  var setlistsData = null;
  var setlistsState = 'pending';
  function loadSetlists(cb) {
    if (setlistsState === 'ready') { cb && cb(); return; }
    if (setlistsState === 'loading') return;
    setlistsState = 'loading';
    var slUrl = INDEX_URL.replace('qa_bank.json', 'setlists.json');
    fetch(slUrl, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { setlistsData = j.setlists || {}; setlistsState = 'ready'; cb && cb(); })
      .catch(function () { setlistsState = 'failed'; cb && cb(); });
  }

  // 识别巡次（一巡/二巡/.../六巡）或城市名
  function findTourScope(q) {
    if (!setlistsData) return null;
    var nq = norm(q);
    // 巡次
    var tourNum = nq.match(/([一二三四五六])巡/);
    if (tourNum) {
      return { type: 'tour', key: tourNum[1] + '巡' };
    }
    // 城市：从所有场的 city 里找
    var cityList = {};
    for (var dt in setlistsData) {
      var c = setlistsData[dt].city;
      if (c) cityList[norm(c)] = c;
    }
    for (var nk in cityList) {
      if (nk && nk.length >= 2 && nq.indexOf(nk) >= 0) {
        return { type: 'city', key: cityList[nk] };
      }
    }
    return null;
  }

  function setlistCardItems(entries) {
    // entries: [{date, city, venue, tour, songs}]
    var html = '';
    entries.forEach(function (e) {
      var songs = (e.songs || []).map(function (s) { return s.title; }).join('、');
      html += '<div class="qaw-card">'
        + '<div class="qaw-q">' + esc(e.date) + ' · ' + esc(e.city) + (e.venue ? ' · ' + esc(e.venue) : '') + '（' + esc(e.tour) + '）</div>'
        + '<div class="qaw-a">' + esc(songs) + '</div>'
        + '</div>';
    });
    return html;
  }

  function renderSetlist(scope) {
    if (!setlistsData) return '';
    var entries = [];
    if (scope.type === 'tour') {
      for (var dt in setlistsData) {
        if (setlistsData[dt].tour === scope.key) {
          entries.push(setlistsData[dt]);
        }
      }
    } else if (scope.type === 'city') {
      for (var dt2 in setlistsData) {
        if (setlistsData[dt2].city === scope.key) {
          entries.push(setlistsData[dt2]);
        }
      }
    }
    entries.sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    if (!entries.length) return '';
    var title = scope.type === 'tour' ? '「' + scope.key + '」共 ' + entries.length + ' 场' : '「' + scope.key + '」共 ' + entries.length + ' 场演出';
    return '<div class="qaw-q">' + esc(title) + ' 的歌单：</div>' + setlistCardItems(entries.slice(0, 6))
      + (entries.length > 6 ? '<div class="qaw-src">（仅显示前 6 场，共 ' + entries.length + ' 场）</div>' : '');
  }

  function render(list) {
    var result = document.getElementById('qaWidgetResult');
    var all = document.getElementById('qaWidgetAll');
    if (!result) return;
    if (!list.length) {
      result.innerHTML = '<div class="qaw-empty">暂未找到相关问题。这个问答库会随提问持续扩充——你可以先问下方已收录的问题。</div>';
    } else {
      var top = list[0].item;
      var html = '<div class="qaw-card">'
        + '<div class="qaw-q">' + esc(top.question) + '</div>'
        + '<div class="qaw-a">' + esc(top.answer).replace(/\n/g, '<br>') + '</div>'
        + '<div class="qaw-src">📚 ' + esc((top.sources || []).join('；'))
        + (top.verified ? ' · ✅' + esc(top.verified) : '')
        + (top.confidence ? ' · 置信度 ' + esc(top.confidence) : '') + '</div>'
        + '</div>';
      if (list.length > 1) {
        html += '<div class="qaw-rel">相关：' + list.slice(1, 3).map(function (r) {
          return '<button type="button" class="qaw-relbtn" data-qid="' + r.item.id + '">' + esc(r.item.question) + '</button>';
        }).join('') + '</div>';
      }
      result.innerHTML = html;
    }
    if (all && bank && bank.items) {
      all.innerHTML = '<div class="qaw-allt">更多问题：</div>' + bank.items.map(function (it) {
        return '<button type="button" class="qaw-relbtn" data-qid="' + it.id + '">' + esc(it.question) + '</button>';
      }).join('');
    }
    bind();
  }

  function bind() {
    Array.prototype.forEach.call(document.querySelectorAll('.qaw-relbtn[data-qid]'), function (b) {
      b.onclick = function () {
        var id = b.getAttribute('data-qid');
        var item = (bank.items || []).filter(function (x) { return x.id === id; })[0];
        if (item) render([{ item: item, score: 100 }]);
      };
    });
  }

  function runQuestion() {
    var input = document.getElementById('qaWidgetInput');
    var result = document.getElementById('qaWidgetResult');
    if (!input || !result) return;
    var q = String(input.value || '').trim();
    if (!q) { result.innerHTML = '<div class="qaw-empty">请输入问题：如「在路上的词曲作者」「为什么要下降」「北京唱了什么歌」「一巡」等。</div>'; return; }
    // 优先级：歌名档案 → 巡次/城市歌单 → 预设问答
    loadSongIndex(function () {
      var song = songState === 'ready' ? findSong(q) : null;
      if (song) {
        result.innerHTML = songCard(song);
        return;
      }
      loadSetlists(function () {
        var scope = setlistsState === 'ready' ? findTourScope(q) : null;
        if (scope) {
          var slHtml = renderSetlist(scope);
          if (slHtml) { result.innerHTML = slHtml; return; }
        }
        loadBank(function () {
          if (bankState === 'failed') { result.innerHTML = '<div class="qaw-empty">问答库加载失败，请刷新。</div>'; return; }
          render(answer(q));
        });
      });
    });
  }

  function injectWidget() {
    if (widgetInjected) return;
    widgetInjected = true;

    var css = '.qaw-fab{position:fixed;right:20px;bottom:20px;z-index:9999;width:52px;height:52px;border-radius:50%;background:#c41e3a;color:#fff;border:none;font-size:22px;cursor:pointer;box-shadow:0 4px 16px rgba(196,30,58,.35);display:flex;align-items:center;justify-content:center;transition:transform .15s}'
      + '.qaw-fab:hover{transform:scale(1.08)}'
      + '.qaw-panel{position:fixed;right:20px;bottom:80px;z-index:9999;width:360px;max-width:calc(100vw - 40px);max-height:70vh;background:#fff;border:1px solid #e8d3d7;border-radius:14px;box-shadow:0 8px 30px rgba(0,0,0,.18);display:none;flex-direction:column;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif}'
      + '.qaw-panel.open{display:flex}'
      + '.qaw-head{background:linear-gradient(135deg,#c41e3a,#a31832);color:#fff;padding:12px 14px;font-size:15px;font-weight:700;display:flex;align-items:center;gap:6px}'
      + '.qaw-close{margin-left:auto;background:none;border:none;color:#fff;font-size:18px;cursor:pointer;line-height:1}'
      + '.qaw-body{padding:12px 14px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:10px}'
      + '.qaw-search{display:flex;gap:6px}'
      + '.qaw-search input{flex:1;min-width:0;padding:9px 12px;font-size:14px;border:1px solid #e0c0c6;border-radius:8px;outline:none}'
      + '.qaw-search input:focus{border-color:#c41e3a}'
      + '.qaw-search button{background:#c41e3a;border:none;border-radius:8px;color:#fff;font-weight:600;padding:0 14px;font-size:13px;cursor:pointer;white-space:nowrap}'
      + '.qaw-result{font-size:13px;color:#333}'
      + '.qaw-card{background:#fafafa;border:1px solid #f0e0e3;border-radius:10px;padding:12px 13px}'
      + '.qaw-q{font-weight:700;margin-bottom:6px}'
      + '.qaw-a{line-height:1.8}'
      + '.qaw-src{font-size:11px;color:#999;margin-top:8px;padding-top:6px;border-top:1px dashed #eee}'
      + '.qaw-rel{display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin-top:6px;font-size:12px;color:#888}'
      + '.qaw-relbtn{background:#fff;border:1px solid #e0c0c6;border-radius:14px;padding:3px 10px;font-size:11px;color:#a31832;cursor:pointer}'
      + '.qaw-relbtn:hover{border-color:#c41e3a;background:#fdf0f2}'
      + '.qaw-empty{color:#888;font-size:12px;padding:8px;text-align:center}'
      + '.qaw-allt{font-size:11px;color:#999;margin-bottom:4px}';
    var st = document.createElement('style');
    st.textContent = css;
    document.head.appendChild(st);

    var fab = document.createElement('button');
    fab.className = 'qaw-fab';
    fab.id = 'qaWidgetFab';
    fab.setAttribute('aria-label', 'AI 问答助手');
    fab.textContent = '💬';

    var panel = document.createElement('div');
    panel.className = 'qaw-panel';
    panel.id = 'qaWidgetPanel';
    panel.innerHTML = ''
      + '<div class="qaw-head">🤖 AI 问答助手 <button class="qaw-close" id="qaWidgetClose" aria-label="关闭">×</button></div>'
      + '<div class="qaw-body">'
      + '  <div class="qaw-search"><input type="search" id="qaWidgetInput" placeholder="问：为什么巡演当天指数下降？" autocomplete="off"><button id="qaWidgetBtn">提问</button></div>'
      + '  <div class="qaw-result" id="qaWidgetResult"><div class="qaw-empty">基于 38 场逐日指数 + 867 条微博事件，回答「为什么」类深层问题。</div></div>'
      + '  <div class="qaw-all" id="qaWidgetAll"></div>'
      + '</div>';

    document.body.appendChild(fab);
    document.body.appendChild(panel);

    fab.onclick = function () { panel.classList.toggle('open'); loadBank(function(){ render([]); }); };
    document.getElementById('qaWidgetClose').onclick = function () { panel.classList.remove('open'); };
    document.getElementById('qaWidgetBtn').onclick = runQuestion;
    document.getElementById('qaWidgetInput').onkeydown = function (e) { if (e.key === 'Enter') runQuestion(); };

    loadBank(function () {
      var all = document.getElementById('qaWidgetAll');
      if (all && bank && bank.items) {
        all.innerHTML = '<div class="qaw-allt">已收录问题：</div>' + bank.items.map(function (it) {
          return '<button type="button" class="qaw-relbtn" data-qid="' + it.id + '">' + esc(it.question) + '</button>';
        }).join('');
        bind();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectWidget);
  } else {
    injectWidget();
  }

  window.QAEngine = { answer: answer };
})();
