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

  /* ---------- 本地电台代理（解锁 VIP 全曲，与小酒馆一致） ---------- */
  var PROXY = 'http://127.0.0.1:8787';
  var proxyState = 0; /* 0=未探测 1=可用 2=不可用 */
  function proxyProbe() {
    if (proxyState) return Promise.resolve(proxyState === 1);
    var ctrl = new AbortController();
    var timer = setTimeout(function () { ctrl.abort(); }, 1200);
    return fetch(PROXY + '/health', { mode: 'cors', signal: ctrl.signal })
      .then(function (r) { proxyState = r.ok ? 1 : 2; })
      .catch(function () { proxyState = 2; })
      .then(function () { clearTimeout(timer); return proxyState === 1; });
  }
  function proxyVkey(songmid) {
    return fetch(PROXY + '/vkey?mid=' + encodeURIComponent(songmid), { mode: 'cors' })
      .then(function (r) { return r.json(); })
      .then(function (j) { return (j.urls && j.urls[0]) || null; });
  }

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
    /* 代理可用（本机电台代理）→ 走代理解锁 VIP；否则 JSONP 免费试听 */
    return proxyProbe().then(function (ok) {
      if (ok) {
        return proxyVkey(songmid).then(function (url) {
          if (url) return url;
          var e = new Error('该曲为 VIP/未提供试听'); e.noPurl = true; throw e;
        });
      }
      return jsonpVkey(songmid).then(function (url) {
        if (!url) { var e = new Error('该曲为 VIP/未提供试听'); e.noPurl = true; throw e; }
        return url;
      });
    });
  }

  /* ---------- 网易云音乐（第二平台，JSONP 搜索 + 试听直链） ---------- */
  function wyySearch(keyword) {
    return new Promise(function (resolve, reject) {
      var cbName = '__wyy_cb_' + Date.now() + '_' + Math.floor(Math.random() * 1e4);
      var url = 'https://music.163.com/api/search/get/web?type=1&callback=' + cbName +
                '&s=' + encodeURIComponent(keyword);
      var timer = setTimeout(function () { cleanup(); reject(new Error('网易云搜索超时')); }, 12000);
      function cleanup() {
        clearTimeout(timer);
        var s = document.getElementById(cbName);
        if (s) s.remove();
        delete global[cbName];
      }
      global[cbName] = function (resp) {
        cleanup();
        try {
          var songs = (resp.result && resp.result.songs) || [];
          resolve(songs.map(function (s) {
            return {
              id: s.id,
              name: s.name,
              artist: (s.artists || []).map(function (a) { return a.name; }).join('、')
            };
          }).slice(0, 5));
        } catch (e) { reject(e); }
      };
      var s = document.createElement('script');
      s.id = cbName;
      s.src = url;
      s.onerror = function () { cleanup(); reject(new Error('网易云搜索失败')); };
      document.head.appendChild(s);
    });
  }
  /* 从网易云结果中挑选：优先发行版（歌名匹配+王晰），其次 live 版（王晰） */
  function pickWyy(hits, title) {
    var nt = norm(title);
    var byWang = hits.filter(function (h) { return h.artist.indexOf('王晰') >= 0; });
    /* 发行版优先：先去括号（(Live)/(live版) 等）后与歌名完全相等 */
    var stripped = byWang.map(function (h) {
      return { h: h, plain: norm(h.name).replace(/\(.*?\)/g, '').replace(/\[.*?\]/g, '') };
    });
    var exact = stripped.filter(function (x) { return x.plain === nt; })[0];
    if (exact) return exact.h;
    var partial = stripped.filter(function (x) { return x.plain.indexOf(nt) >= 0 || nt.indexOf(x.plain) >= 0; })[0];
    if (partial) return partial.h;
    /* 发行版没有 → 找王晰的 live/现场/演唱会版 */
    var live = byWang.filter(function (h) {
      return /live|现场|演唱会|巡演|live版|Live/i.test(h.name);
    })[0];
    return live || byWang[0] || null;
  }
  function wyyPlayUrl(songId) {
    /* 302 重定向到真实 MP3，audio 可直接播 */
    return 'https://music.163.com/song/media/outer/url?id=' + songId + '.mp3';
  }
  /* 多平台聚合：QQ -> 网易云发行版 -> 网易云 live 版 -> 提示 */
  function resolvePlayable(songmid, title) {
    if (!title && !songmid) return Promise.reject(new Error('无歌曲信息'));
    function tryWyy(keyword) {
      return wyySearch(keyword).then(function (hits) {
        var best = pickWyy(hits, title);
        if (best) return wyyPlayUrl(best.id);
        throw new Error('网易云无匹配');
      });
    }
    var fromQQ = songmid ? fetchVkey(songmid) : Promise.reject(new Error('无 QQ ID'));
    return fromQQ.catch(function () {
      /* QQ 不可用 → 网易云发行版（歌名 王晰） */
      return tryWyy((title || '') + ' 王晰').catch(function () {
        /* 发行版没有 → 网易云 live 版（歌名 王晰 live） */
        return tryWyy((title || '') + ' 王晰 live');
      });
    });
  }

  /* ---------- 播放控制 ---------- */
  function play(mid, title) {
    var songmid = norm(mid);
    if (!songmid && !title) return Promise.resolve(false);
    var a = getAudio();
    if (currentMid === songmid && !a.paused && songmid) { a.pause(); setState('pause'); return Promise.resolve(true); }
    if (currentMid === songmid && a.src && a.paused && songmid) { a.play(); setState('play'); return Promise.resolve(true); }
    currentMid = songmid;
    currentTitle = title || '试听';
    setState('load');
    /* 多平台：QQ(vkey) -> 网易云(搜索+直链) */
    return resolvePlayable(songmid, title).then(function (url) {
      a.src = url;
      var p = a.play();
      if (p && p.catch) p.catch(function () {
        setState('fail');
        if (typeof statusFn === 'function') statusFn('fail', '音频无法播放（可能为 VIP 或需登录）');
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
    isPlaying: function () { return !!(audio && !audio.paused); },
    get currentMid() { return currentMid; }
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = PlayerEmbed;
  global.PlayerEmbed = PlayerEmbed;
})(typeof window !== 'undefined' ? window : this);
