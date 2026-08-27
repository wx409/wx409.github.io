/* 王晰知识库 · 语义检索引擎（纯前端零模型，零后端）
 * 策略：①别名扩展 ②char-bigram TF 向量余弦（纯JS稀疏，运行时无模型） ③整词命中加权
 *       ④预计算语义近邻（bge-small-zh，graph.json）延伸"相关知识"
 * 数据：data/kb/semantic/{docs.json, vectors.bin, graph.json, manifest.json}
 * 用法：const kb = KBSearch; await kb.init(); kb.search('王晰哪年拿的青歌赛冠军');
 */
var KBSearch = (function () {
  var docs = [], graph = {}, manifest = null, docBg = [], ready = false;
  var ALIASES = {
    '低音炮': ' 低音 王晰', 'low c': ' 低音', 'lowc': ' 低音', '低音男声': ' 低音',
    '晰哥': ' 王晰', '王晰elvis': ' 王晰', '男低音': ' 低音 男声', 'elvis': ' 王晰',
    '六巡': ' 回 巡演', '回巡': ' 回 巡回音乐会', '个巡': ' 巡回音乐会',
    '青歌赛': ' 青年歌手电视大奖赛', '东演': ' 中国东方演艺集团', '乐华': ' 乐华娱乐',
    '海政': ' 海政文工团', '声入人心': ' 湖南卫视 声入人心'
  };
  function norm(s) {
    return (s || '').toLowerCase().replace(/[\s，。、；：""''《》【】()（）!?！？·—…~]/g, '');
  }
  function bigrams(s) {
    var t = norm(s), out = {};
    for (var i = 0; i < t.length - 1; i++) {
      var k = t[i] + t[i + 1];
      out[k] = (out[k] || 0) + 1;
    }
    return out;
  }
  function expand(q) {
    var s = ' ' + q + ' ';
    for (var k in ALIASES) {
      if (q.toLowerCase().indexOf(k) >= 0) s += ALIASES[k];
    }
    return s;
  }
  function init(base) {
    base = base || 'data/kb/semantic/';
    return Promise.all([
      fetch(base + 'docs.json').then(function (r) { return r.json(); }),
      fetch(base + 'graph.json').then(function (r) { return r.json(); }),
      fetch(base + 'manifest.json').then(function (r) { return r.json(); })
    ]).then(function (res) {
      docs = res[0]; graph = res[1]; manifest = res[2];
      docBg = docs.map(function (d) { return bigrams(d.text); });
      ready = true;
      return manifest;
    });
  }
  function search(query, top) {
    top = top || 12;
    if (!ready || !query) return [];
    var qb = bigrams(expand(query));
    var qchars = new Set(norm(query));
    var scored = [];
    for (var i = 0; i < docs.length; i++) {
      var db = docBg[i];
      var num = 0, denA = 0, denB = 0;
      for (var k in qb) { var a = qb[k], b = db[k] || 0; num += a * b; denA += a * a; }
      for (var k2 in db) { denB += db[k2] * db[k2]; }
      var cos = num / Math.sqrt(denA * denB || 1);
      var text = norm(docs[i].text), hit = 0;
      qchars.forEach(function (ch) { if (text.indexOf(ch) >= 0) hit++; });
      var lex = hit / (qchars.size || 1);
      scored.push({ score: cos * 0.7 + lex * 0.3, i: i });
    }
    scored.sort(function (a, b) { return b.score - a.score; });
    var out = [], seen = {};
    for (var j = 0; j < Math.min(scored.length, top); j++) {
      var d = docs[scored[j].i];
      seen[d.id] = 1;
      out.push({ id: d.id, type: d.type, text: d.text, score: +scored[j].score.toFixed(3) });
    }
    // 语义近邻延伸（bge 预计算，展示"相关知识"）
    for (var m = 0; m < out.length && out.length < top + 12; m++) {
      var nb = graph[out[m].id] || [];
      for (var n = 0; n < nb.length && out.length < top + 12; n++) {
        var nid = nb[n];
        if (seen[nid]) continue;
        seen[nid] = 1;
        var nd = docs.find(function (x) { return x.id === nid; });
        if (nd) out.push({ id: nd.id, type: nd.type, text: nd.text, score: null, neighbor_of: out[m].id });
      }
    }
    return out;
  }
  function stats() { return manifest ? { docs: manifest.doc_count, types: manifest.types, model: manifest.model } : null; }
  return { init: init, search: search, stats: stats, ready: function () { return ready; } };
})();
