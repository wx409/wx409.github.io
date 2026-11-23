(function () {
  var box = document.getElementById('upcomingList');
  if (!box) return;
  fetch('/data/upcoming.json?t=' + Date.now()).then(function (r) { return r.json(); }).then(function (d) {
    var items = (d && d.items) || [];
    if (!items.length) { box.textContent = '暂无已官宣的未发生场次。'; return; }
    box.innerHTML = items.map(function (x) {
      var dt = (x.date || '').replace(/-/g, '.');
      var city = x.city || '城市待补';
      var title = x.title || '';
      var link = x.link || '/live.html';
      return '<div style="padding:5px 0;border-bottom:1px dashed #eee">' +
        '<b style="color:#a8323d">' + dt + '</b> · ' + city +
        ' · <a href="' + link + '" style="color:#1f2328;text-decoration:none">' + title + '</a>' +
        (x.kind ? ' <span style="color:#999;font-size:12px">' + x.kind + '</span>' : '') +
        '</div>';
    }).join('');
  }).catch(function () { box.textContent = '场次信息加载失败，请到现场页查看。'; });
})();
