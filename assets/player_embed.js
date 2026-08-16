/* ============================================================================
 * 通用试听组件（player_embed.js）—— 全站页面内直听
 * ----------------------------------------------------------------------------
 * 纯前端：JSONP 调 QQ音乐 vkey 接口 → 免费试听直链 → <audio> 页面内播放
 * 版权边界：仅试听级直链播放，不下载、不托管音频文件
 * 用法：
 *   <script src="assets/player_embed.js"></script>
 *   PlayerEmbed.attach(buttonEl, { mid: 'xxx', title: '歌名', onState: fn })
 *   PlayerEmbed.play(mid, title)   // 直接播
 * ========================================================================== */
(function (global) {
  'use strict';

  var audio = null;        /* 单例 audio */
  var currentMid = '';
  var currentTitle = '';
  var statusFn = null;

  function getAudio() {
    if (!audio) {
      audio = new Audio();
      audio.crossOrigin = 'anonymous';
      audio.volume = 0.8;
      audio.preload = 'none';
      audio.addEventListener('ended', function () { setState('play'); });
    }
    return audio;
  }

  function setState(kind) {
    /* 更新所有按钮状态（基于 audio 真实状态） */
    var playing = !!(audio && !audio.paused);
    var btns = document.querySelectorAll('.pe-btn');
    btns.forEach(function (b) {
      var mid = b.getAttribute('data-mid');
      if (mid === currentMid) {
        b.textContent = playing ? '⏸ 暂停' : '▶ 试听';
        b.classList.toggle('pe-playing', playing);
      } else {
        b.textContent = '▶ 试听';
        b.classList.remove('pe-playing');
      }
    });
    if (typeof statusFn === 'function') statusFn(kind, currentTitle);
  }

  function norm(mid) {
    return String(mid || '').trim().replace(/^L:/, '');
  }

  /* ---------- JSONP vkey ---------- */
  function jsonpVkey(songmid) {
    return new Promise(function (resolve, reject) {
      var cbName = '__pe_cb_' + Date.now() + '_' + Math.floor(Math.random() * 1e4);
      var param = {
        guid: '10000' + Math.floor(Math.random() * 1e10),
        songmid: [songmid],
        songtype: [0],
        uin: '0',
        loginflag: 1,
        platform: '20'
      };
      var data = JSON.stringify({ req_0: { module: 'vkey.GetVkeyServer', method: 'CgiGetVkey', param: param } });
      var url = 'https://u.y.qq.com/cgi-bin/musicu.fcg?callback=' + cbName +
                '&data=' + encodeURIComponent(data) + '&format=json';
      var timer = setTimeout(function () { cleanup(); reject(new Error('获取播放地址超时')); }, 15000);
      function cleanup() {
        clearTimeout(timer);
        var s = document.getElementById(cbName);
        if (s) s.remove();
        delete global[cbName];
      }
      global[cbName] = function (resp) {
        cleanup();
        try {
          var info = (resp.req_0 && resp.req_0.data && resp.req_0.data.midurlinfo) || [];
          var it = info[0] || {};
          resolve(it.purl ? 'https://isure.stream.qqmusic.qq.com/' + it.purl : null);
        } catch (e) { reject(e); }
      };
      var s = document.createElement('script');
      s.id = cbName;
      s.src = url;
      s.onerror = function () { cleanup(); reject(new Error('网络请求失败')); };
      document.head.appendChild(s);
    });
  }

  function fetchVkey(songmid) {
    return jsonpVkey(songmid).then(function (url) {
      if (!url) { var e = new Error('该曲为 VIP/未提供试听'); e.noPurl = true; throw e; }
      return url;
    });
  }

  /* ---------- 播放控制 ---------- */
  function play(mid, title) {
    var songmid = norm(mid);
    if (!songmid) return Promise.resolve(false);
    var a = getAudio();
    if (currentMid === songmid && !a.paused) { a.pause(); setState('pause'); return Promise.resolve(true); }
    if (currentMid === songmid && a.src && a.paused) { a.play(); setState('play'); return Promise.resolve(true); }
    currentMid = songmid;
    currentTitle = title || '试听';
    setState('load');
    return fetchVkey(songmid).then(function (url) {
      a.src = url;
      var p = a.play();
      if (p && p.catch) p.catch(function () {
        /* 自动播放被拦 / 音频加载失败：给明确反馈 */
        setState('fail');
        if (typeof statusFn === 'function') statusFn('fail', '音频无法播放（可能为 VIP 或需登录 QQ音乐）');
      });
      setState('play');
      return true;
    }).catch(function (e) {
      setState('fail');
      if (typeof statusFn === 'function') statusFn('fail', (e && e.message) || '播放失败');
      return false;
    });
  }

  /* ---------- 按钮绑定 ---------- */
  function attach(btn, opts) {
    opts = opts || {};
    btn.classList.add('pe-btn');
    btn.setAttribute('data-mid', norm(opts.mid || ''));
    btn.textContent = '▶ 试听';
    btn.addEventListener('click', function () {
      play(opts.mid, opts.title);
    });
    return btn;
  }

  /* ---------- 对外 API ---------- */
  var PlayerEmbed = {
    VERSION: '1.0.0',
    play: play,
    attach: attach,
    stop: function () { if (audio) { audio.pause(); audio.removeAttribute('src'); } currentMid = ''; },
    setStatusFn: function (fn) { statusFn = fn; },
    isPlaying: function () { return !!(audio && !audio.paused); }
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = PlayerEmbed;
  global.PlayerEmbed = PlayerEmbed;
})(typeof window !== 'undefined' ? window : this);
