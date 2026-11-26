(function () {
  var box = document.getElementById('todayStrip');
  if (!box) return;
  fetch('/data/today.json?t=' + Date.now()).then(function (r) { return r.json(); }).then(function (d) {
    if (!d || !d.date) { box.style.display = 'none'; return; }
    box.innerHTML = '<a href="/today.html" style="display:flex;gap:10px;align-items:center;justify-content:space-between;text-decoration:none;color:#6b5320">' +
      '<span><b>📅 今日新入库</b> · ' + d.date + ' · ' + (d.headline || '') + '</span><span>去看 →</span></a>';
  }).catch(function () { box.style.display = 'none'; });
})();
