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

  /* ---------- QQ 音乐搜索（JSONP，找王晰的发行版/Live 版 songmid） ---------- */
  function qqSearch(keyword) {
    return new Promise(function (resolve, reject) {
      var cbName = '__qqs_cb_' + Date.now() + '_' + Math.floor(Math.random() * 1e4);
      var url = 'https://c.y.qq.com/soso/fcgi-bin/client_search_cp?p=1&n=8&format=jsonp&callback=' + cbName +
                '&w=' + encodeURIComponent(keyword);
      var timer = setTimeout(function () { cleanup(); reject(new Error('QQ搜索超时')); }, 12000);
      function cleanup() {
        clearTimeout(timer);
        var s = document.getElementById(cbName);
        if (s) s.remove();
        delete global[cbName];
      }
      global[cbName] = function (resp) {
        cleanup();
        try {
          var list = (resp.data && resp.data.song && resp.data.song.list) || [];
          resolve(list.map(function (s) {
            return {
              mid: s.songmid,
              name: s.songname,
              singer: (s.singer || []).map(function (x) { return x.name; }).join('、')
            };
          }));
        } catch (e) { reject(e); }
      };
      var s = document.createElement('script');
      s.id = cbName;
      s.src = url;
      s.onerror = function () { cleanup(); reject(new Error('QQ搜索失败')); };
      document.head.appendChild(s);
    });
  }
  /* 严格过滤：演唱者必须含「王晰」（发行版优先，其次 Live 版） */
  function pickQq(hits, title) {
    var nt = norm(title);
    var byWang = hits.filter(function (h) { return h.singer.indexOf('王晰') >= 0; });
    if (!byWang.length) return null;   /* 没有王晰版本，坚决不播别人的 */
    var stripped = byWang.map(function (h) {
      return { h: h, plain: norm(h.name).replace(/\(.*?\)/g, '').replace(/\[.*?\]/g, '') };
    });
    var exact = stripped.filter(function (x) { return x.plain === nt; })[0];
    if (exact) return exact.h;
    /* 仅允许「歌名包含搜索词」（搜"晚风"可命中"晚风暖暖"）；不允许反向退化 */
    var partial = stripped.filter(function (x) { return x.plain.indexOf(nt) >= 0 && x.plain !== nt; })[0];
    if (partial) return partial.h;
    /* 发行版无 → 王晰的 Live/现场版（同样要求歌名包含搜索词） */
    return byWang.filter(function (h) {
      return /live|现场|演唱会|巡演/i.test(h.name) && norm(h.name).indexOf(nt) >= 0;
    })[0] || null;
  }

  /* ---------- 网易云音乐（JSONP 搜索 + 试听直链） ---------- */
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
          }).slice(0, 8));
        } catch (e) { reject(e); }
      };
      var s = document.createElement('script');
      s.id = cbName;
      s.src = url;
      s.onerror = function () { cleanup(); reject(new Error('网易云搜索失败')); };
      document.head.appendChild(s);
    });
  }
  /* 严格过滤：演唱者必须含「王晰」（发行版优先，其次 Live 版） */
  function pickWyy(hits, title) {
    var nt = norm(title);
    var byWang = hits.filter(function (h) { return h.artist.indexOf('王晰') >= 0; });
    if (!byWang.length) return null;   /* 没有王晰版本，坚决不播别人的 */
    var stripped = byWang.map(function (h) {
      return { h: h, plain: norm(h.name).replace(/\(.*?\)/g, '').replace(/\[.*?\]/g, '') };
    });
    var exact = stripped.filter(function (x) { return x.plain === nt; })[0];
    if (exact) return exact.h;
    /* 仅允许「歌名包含搜索词」；不允许反向退化（"晚风暖暖"不会命中"晚风"） */
    var partial = stripped.filter(function (x) { return x.plain.indexOf(nt) >= 0 && x.plain !== nt; })[0];
    if (partial) return partial.h;
    /* 发行版无 → 王晰的 Live/现场版（同样要求歌名包含搜索词） */
    return byWang.filter(function (h) {
      return /live|现场|演唱会|巡演/i.test(h.name) && norm(h.name).indexOf(nt) >= 0;
    })[0] || null;
  }
  function wyyPlayUrl(songId) {
    return 'https://music.163.com/song/media/outer/url?id=' + songId + '.mp3';
  }

  /* ---------- 多平台回退链（每步严格「王晰演唱」） ----------
   * ① QQ vkey（当前歌曲 mid，发行版）
   * ② QQ 搜索：发行版（王晰）→ Live 版（王晰）
   * ③ 网易云：发行版（王晰）→ Live 版（王晰）
   * ④ 全部失败 → 提示
   */
  function resolvePlayable(songmid, title) {
    if (!title && !songmid) return Promise.reject(new Error('无歌曲信息'));
    var nt = title || '';
    function tryQQvkey(mid) {
      return fetchVkey(mid).then(function (url) {
        if (url) return url;
        throw new Error('QQ无直链');
      });
    }
    function tryQQsearch(kw) {
      return qqSearch(kw).then(function (hits) {
        var best = pickQq(hits, nt);
        if (!best || !best.mid) throw new Error('QQ无王晰版本');
        return tryQQvkey(best.mid);
      });
    }
    function tryWyy(kw) {
      return wyySearch(kw).then(function (hits) {
        var best = pickWyy(hits, nt);
        if (!best) throw new Error('网易云无王晰版本');
        return wyyPlayUrl(best.id);
      });
    }
    /* ① QQ 当前歌曲 mid（发行版） */
    var p = songmid ? tryQQvkey(songmid) : Promise.reject(new Error('无QQ ID'));
    /* ② QQ 搜索发行版 → ③ QQ 搜索 Live 版 */
    p = p.catch(function () {
      return tryQQsearch(nt + ' 王晰').catch(function () {
        return tryQQsearch(nt + ' 王晰 live');
      });
    });
    /* ④ 网易云发行版 → ⑤ 网易云 Live 版 */
    p = p.catch(function () {
      return tryWyy(nt + ' 王晰').catch(function () {
        return tryWyy(nt + ' 王晰 live');
      });
    });
    return p;
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
