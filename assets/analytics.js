(function () {
  var cfg = window.__ANALYTICS__ || {};
  if (!cfg.site) return; // 未配置站点代码：不加载、不采集
  var s = document.createElement('script');
  s.async = true;
  s.src = '/assets/goatcounter-count.js';
  s.setAttribute('data-goatcounter', 'https://' + cfg.site + '.goatcounter.com/count');
  document.head.appendChild(s);
  document.addEventListener('click', function (e) {
    var a = e.target.closest ? e.target.closest('a') : null;
    if (!a || !a.href || a.hostname === location.hostname) return;
    if (window.goatcounter && window.goatcounter.count) {
      window.goatcounter.count({ path: 'outbound/' + a.hostname, title: (a.textContent || '').slice(0, 80), event: true });
    }
  }, true);
})();
