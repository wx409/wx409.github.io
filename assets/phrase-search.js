/* 词句链式召回 v2：默认先给「他说过的话」（采访/现场），歌词另列
   用法：<div id="psInput"> + <div id="psChips"> + <div id="psRes"> + <script src="/assets/phrase-search.js">
*/
(function () {
  var idx = null, df = null, N = 0, curType = "";
  var TY = { interview: "采访", talk: "现场", lyrics: "歌词", mystic: "卦象", song: "歌名" };
  var BOOST = { interview: 2.2, talk: 2.0, mystic: 1.1, song: 1.0, lyrics: 0.75 };

  function grams(s) {
    s = (s || "").replace(/[^\u4e00-\u9fff A-Za-z0-9]/g, "");
    if (s.length < 2) return s ? [s] : [];
    var out = [];
    for (var i = 0; i < s.length - 1; i++) out.push(s.substr(i, 2));
    return out;
  }
  function build(items) {
    df = Object.create(null); N = items.length;
    items.forEach(function (it) {
      var gs = grams(it.t + " " + it.s), seen = Object.create(null);
      gs.forEach(function (g) { if (seen[g]) return; seen[g] = 1; df[g] = (df[g] || 0) + 1; });
    });
  }
  function search(q, top) {
    var qg = grams(q); if (!qg.length) return [];
    var res = [];
    for (var i = 0; i < idx.items.length; i++) {
      var it = idx.items[i];
      if (curType && it.y !== curType) continue;
      var tg = grams(it.t + " " + it.s), seen = Object.create(null), w = 0, hit = 0;
      tg.forEach(function (g) {
        if (seen[g]) return; seen[g] = 1;
        if (qg.indexOf(g) >= 0) { hit = 1; w += Math.log(1 + N / (1 + (df[g] || 0))); }
      });
      if (!hit) continue;
      res.push({ sc: (w / Math.sqrt(tg.length + 1)) * (BOOST[it.y] || 1), it: it });
    }
    res.sort(function (a, b) { return b.sc - a.sc; });
    return res.slice(0, top);
  }
  function esc(s) { return (s || "").replace(/[<>&]/g, function (c) { return ({ "<": "&lt;", ">": "&gt;", "&": "&amp;" })[c]; }); }

  function li(it) {
    return "<li style='margin:9px 0'><div style='font-size:15px;color:#222'>" + esc(it.t) + "</div>" +
      "<div style='color:#8a8a8a;font-size:12px'>" + (TY[it.y] || it.y) + " · " + esc(it.s) + "</div></li>";
  }

  function render(q) {
    var box = document.getElementById("psRes");
    if (!idx) { box.innerHTML = "<p style='color:#888'>词句库加载中…</p>"; return; }
    if (!q) { box.innerHTML = ""; return; }
    var rows = search(q, 40);
    if (!rows.length) { box.innerHTML = "<p style='color:#888'>没找到相关句子</p>"; return; }

    var words = rows.filter(function (r) { return r.it.y !== "lyrics"; }).slice(0, 8);
    var lyrics = rows.filter(function (r) { return r.it.y === "lyrics"; }).slice(0, 6);

    var html = "";
    if (words.length) {
      html += "<li style='list-style:none;margin:12px 0 4px;font-weight:600;color:#c41e3a'>他说过的话</li>" +
        words.map(function (r) { return li(r.it); }).join("");
    }
    if (lyrics.length) {
      html += "<li style='list-style:none;margin:16px 0 4px;font-weight:600;color:#7a6a5a'>歌词里的句子</li>" +
        lyrics.map(function (r) { return li(r.it); }).join("");
    }
    if (!words.length && lyrics.length) {
      html = "<li style='list-style:none;margin:8px 0;color:#8a8a8a'>没有找到他说过的话，以下是歌词：</li>" + html;
    }
    box.innerHTML = html;
  }

  function chips() {
    var box = document.getElementById("psChips");
    if (!box) return;
    var opts = [["", "全部"], ["interview", "采访"], ["talk", "现场"], ["lyrics", "歌词"], ["mystic", "卦象"]];
    box.innerHTML = opts.map(function (o) {
      return "<button data-t='" + o[0] + "' style='font:inherit;font-size:13px;padding:5px 12px;border-radius:999px;cursor:pointer;" +
        (o[0] === curType ? "background:#c41e3a;color:#fff;border:1px solid #c41e3a" : "background:#fbf8f3;border:1px solid #d8cfc0") +
        "'>" + o[1] + "</button>";
    }).join("");
    box.querySelectorAll("button").forEach(function (b) {
      b.onclick = function () {
        curType = b.dataset.t;
        chips();
        render(document.getElementById("psInput").value.trim());
      };
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var input = document.getElementById("psInput");
    if (!input) return;
    fetch("/data/phrase_index.json?v=2026110121").then(function (r) { return r.json(); }).then(function (j) {
      idx = j; build(j.items); chips();
      var hint = document.getElementById("psHint");
      if (hint) hint.textContent = "索引 " + j.n + " 条；默认先给「他说过的话」，歌词单独列在下面。";
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
