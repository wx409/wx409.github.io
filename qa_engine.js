/**
 * 王晰 AI 问答引擎（qa_engine.js）
 * 纯静态、零依赖：fetch data/qa_bank.json，用「关键词 + 别名 + 语义类别」匹配预生成的归因问答。
 * 设计：离线预生成问答库 + 前端语义检索（零后端、零 key 暴露、零成本），可按提问增量扩充。
 */
(function () {
  var INDEX_URL = 'data/qa_bank.json';
  var bank = null;          // { items: [...] }
  var bankState = 'pending'; // pending | ready | failed

  function norm(s) {
    return String(s || '').toLowerCase().replace(/[，。！？、；：""''《》【】（）()\s\-—·]/g, '');
  }

  function loadBank() {
    if (bankState !== 'pending') return;
    bankState = 'loading';
    fetch(INDEX_URL, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) {
        bank = j;
        bankState = 'ready';
      })
      .catch(function () { bankState = 'failed'; });
  }

  // 打分：问题里命中 item 的 keywords/aliases/question 越多、越靠前，分越高
  function scoreItem(item, q) {
    var nq = norm(q);
    var score = 0;
    var hit = false;
    // question / aliases 命中（高权重）
    (item.aliases || []).concat([item.question]).forEach(function (a) {
      var na = norm(a);
      if (na && nq.indexOf(na) >= 0) { score += 50; hit = true; }
      else if (na && na.length > 0 && nq.length > 0 && (na.indexOf(nq) >= 0)) { score += 30; hit = true; }
    });
    // keywords 命中（每命中一个 +15，去重）
    var counted = {};
    (item.keywords || []).forEach(function (k) {
      var nk = norm(k);
      if (nk && !counted[nk] && nk.length > 0 && nq.indexOf(nk) >= 0) {
        score += 15; hit = true; counted[nk] = true;
      }
    });
    // 无任何词命中但命中 category 语义（弱）
    if (!hit && item.category && norm(item.category).length > 0 && nq.indexOf(norm(item.category)) >= 0) {
      score += 8; hit = true;
    }
    return hit ? score : 0;
  }

  function answer(q) {
    if (!bank || !bank.items) return [];
    var scored = [];
    bank.items.forEach(function (item) {
      var s = scoreItem(item, q);
      if (s > 0) scored.push({ item: item, score: s });
    });
    scored.sort(function (a, b) { return b.score - a.score; });
    return scored;
  }

  function renderAnswer(list, q) {
    var box = document.getElementById('qaResult');
    if (!box) return;
    if (!list.length) {
      box.innerHTML = '<div class="qa-empty">暂未找到相关问题。此问答库会随提问持续扩充——你可以先看看下方「已收录的问题」。</div>';
      renderAllQuestions();
      return;
    }
    var top = list[0].item;
    var a = top.answer.replace(/\n/g, '<br>');
    var src = (top.sources || []).join('；');
    var html = '<div class="qa-card">'
      + '<div class="qa-q">Q：' + escapeHtml(top.question) + '</div>'
      + '<div class="qa-a">' + a + '</div>'
      + '<div class="qa-src">📚 佐证：' + escapeHtml(src)
      + (top.verified ? ' · ✅ ' + escapeHtml(top.verified) : '')
      + (top.confidence ? ' · 置信度：' + escapeHtml(top.confidence) : '') + '</div>'
      + '</div>';
    // 若有次优结果，列 1-2 个相关
    if (list.length > 1) {
      html += '<div class="qa-related">相关：';
      list.slice(1, 3).forEach(function (r) {
        html += '<button type="button" class="qa-rel-btn" data-qid="' + r.item.id + '">' + escapeHtml(r.item.question) + '</button>';
      });
      html += '</div>';
    }
    box.innerHTML = html;
    bindRelated();
  }

  function renderAllQuestions() {
    var box = document.getElementById('qaAllList');
    if (!box || !bank || !bank.items) return;
    box.innerHTML = bank.items.map(function (it) {
      return '<button type="button" class="qa-rel-btn" data-qid="' + it.id + '">' + escapeHtml(it.question) + '</button>';
    }).join('');
    bindRelated();
  }

  function bindRelated() {
    Array.prototype.forEach.call(document.querySelectorAll('.qa-rel-btn[data-qid]'), function (b) {
      b.onclick = function () {
        var id = b.getAttribute('data-qid');
        var item = (bank.items || []).filter(function (x) { return x.id === id; })[0];
        if (item) renderAnswer([{ item: item, score: 100 }], item.question);
      };
    });
  }

  function escapeHtml(s) {
    return String(s || '').replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function init() {
    loadBank();
    var input = document.getElementById('qaInput');
    var btn = document.getElementById('qaBtn');
    if (!input || !btn) return;
    function run() {
      var q = String(input.value || '').trim();
      if (!q) { document.getElementById('qaResult').innerHTML = '<div class="qa-empty">请输入你的问题，例如「为什么巡演当天指数下降」。</div>'; return; }
      if (bankState === 'failed') { document.getElementById('qaResult').innerHTML = '<div class="qa-empty">问答库加载失败，请刷新重试。</div>'; return; }
      if (bankState !== 'ready') { loadBank(); return; }
      renderAnswer(answer(q), q);
    }
    btn.onclick = run;
    input.onkeydown = function (e) { if (e.key === 'Enter') run(); };
    renderAllQuestions();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  window.QAEngine = { answer: answer, render: renderAnswer };
})();
