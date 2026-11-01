/* 词句链式召回（前端版）：字符 bigram + 词频倒排，无依赖
   用法：<div id="psBox"></div> + <script src="/assets/phrase-search.js"></script>
   数据：/data/phrase_index.json  → {n, items:[{t,s,y,q}]}
*/
(function () {
  var idx = null, df = null, N = 0;

  function grams(s) {
    s = (s || "").replace(/[^\u4e00-\u9fff A-Za-z0-9]/g, "").replace(/\s+/g, "");
    if (s.length < 2) return s ? [s] : [];
    var out = [];
    for (var i = 0; i < s.length - 1; i++) out.push(s.substr(i, 2));
    return out;
  }

  function build(items) {
    df = Object.create(null);
    N = items.length;
    items.forEach(function (it) {
      var gs = grams(it.t + " " + it.s);
      var seen = Object.create(null);
      gs.forEach(function (g) {
        if (seen[g]) return;
        seen[g] = 1;
        df[g] = (df[g] || 0) + 1;
      });
    });
  }

  function search(q, top) {
    var qg = grams(q);
    if (!qg.length) return [];
    var res = [];
    for (var i = 0; i < idx.items.length; i++) {
      var it = idx.items[i];
      var tg = grams(it.t + " " + it.s);
      var seen = Object.create(null), inter = [];
      tg.forEach(function (g) { if (seen[g]) return; seen[g] = 1; if (qg.indexOf(g) >= 0) inter.push(g); });
      if (!inter.length) continue;
      var w = 0;
      inter.forEach(function (g) { w += Math.log(1 + N / (1 + (df[g] || 0))); });
      res.push({ sc: w / Math.sqrt(tg.length + 1), it: it });
    }
    res.sort(function (a, b) { return b.sc - a.sc; });
    return res.slice(0, top || 10);
  }

  function esc(s) { return (s || "").replace(/[<>&]/g, function (c) { return ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" })[c]; }); }

  function render(q) {
    var box = document.getElementById("psRes");
    if (!idx) { box.innerHTML = "<p style='color:#888'>词句库加载中…</p>"; return; }
    if (!q) { box.innerHTML = ""; return; }
    var rows = search(q, 12);
    if (!rows.length) { box.innerHTML = "<p style='color:#888'>没找到相关句子</p>"; return; }
    var TY = { interview: "采访", lyrics: "歌词", talk: "现场", mystic: "卦象", song: "歌名" };
    box.innerHTML = rows.map(function (r) {
      return "<li style='margin:10px 0'><div style='font-size:15px'>" + esc(r.it.t) + "</div>" +
        "<div style='color:#8a8a8a;font-size:12px'>" + (TY[r.it.y] || r.it.y) + " · " + esc(r.it.s) + "</div></li>";
    }).join("");
  }

  document.addEventListener("DOMContentLoaded", function () {
    var input = document.getElementById("psInput");
    if (!input) return;
    fetch("/data/phrase_index.json").then(function (r) { return r.json(); }).then(function (j) {
      idx = j; build(j.items);
      var hint = document.getElementById("psHint");
      if (hint) hint.textContent = "索引 " + j.n + " 条（高质量层），输入任意词即可召回";
      render(input.value.trim());
    }).catch(function () {
      document.getElementById("psRes").innerHTML = "<p style='color:#c41e3a'>索引加载失败</p>";
    });
    var t = null;
    input.addEventListener("input", function () {
      clearTimeout(t);
      var v = input.value.trim();
      t = setTimeout(function () { render(v); }, 160);
    });
  });
})();
