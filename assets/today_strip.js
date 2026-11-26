(function () {
  var box = document.getElementById('todayStrip');
  if (!box) return;
  fetch('/data/today.json?t=' + Date.now()).then(function (r) { return r.json(); }).then(function (d) {
    if (!d || !d.date) { box.style.display = 'none'; return; }
    var latest = d.latest_date || d.date;
    var text = (d.fresh === false ? '⚠ 今日更新未完成 · 先看 ' + latest : '📅 今日新入库 · ' + d.date) + ' · ' + (d.headline || '');
    box.innerHTML = '<a href="/today.html" style="display:flex;gap:10px;align-items:center;justify-content:space-between;text-decoration:none;color:#6b5320">' +
      '<span><b>' + text + '</b></span><span>去看 →</span></a>';
  }).catch(function () { box.style.display = 'none'; });
})();
