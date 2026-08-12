/* ============================================================
 * 深夜小酒馆 · 音乐播放模块 (TavernPlayer)
 * 纯前端：JSONP 调 QQ音乐 vkey 接口 → 音频直链 → <audio> 播放
 * 背景频谱光效：Web Audio AnalyserNode → Canvas（随音乐真实跳动）
 * 桌面端：网页内直接播放；移动端：跳转 QQ音乐 App 后返回页面
 * 版权边界：仅试听级直链播放，不下载、不托管音频文件
 * ============================================================ */
(function (global) {
  'use strict';

  var VERSION = '1.0.0';

  /* ---------- 移动端检测 ---------- */
  function isMobile() {
    return /Android|iPhone|iPad|iPod|Windows Phone/i.test(navigator.userAgent || '');
  }

  /* ---------- 工具 ---------- */
  function $(id) { return document.getElementById(id); }

  /* ---------- JSONP 批量请求 vkey（script 标签携带登录 Cookie，返回每首的直链或 null） ---------- */
  function fetchVkeys(songmids, filenames) {
    return new Promise(function (resolve, reject) {
      var cbName = '__tv_cb_' + Date.now() + '_' + Math.floor(Math.random() * 1e4);
      var param = {
        guid: '10000' + Math.floor(Math.random() * 1e10),
        songmid: songmids,
        songtype: songmids.map(function () { return 0; }),
        uin: '0',
        loginflag: 1,
        platform: '20'
      };
      if (filenames && filenames.length) param.filename = filenames;
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
          var out = songmids.map(function (mid, i) {
            var it = info[i] || {};
            return it.purl ? 'https://isure.stream.qqmusic.qq.com/' + it.purl : null;
          });
          resolve(out);
        } catch (e) { reject(e); }
      };
      var s = document.createElement('script');
      s.id = cbName;
      s.src = url;
      s.onerror = function () { cleanup(); reject(new Error('网络请求失败')); };
      document.head.appendChild(s);
    });
  }

  /* 单曲包装：返回直链或 reject */
  function fetchVkey(songmid, filename) {
    return fetchVkeys([songmid], filename ? [filename] : null).then(function (arr) {
      if (!arr[0]) { var e = new Error('该资源暂未提供试听地址'); e.noPurl = true; throw e; }
      return arr[0];
    });
  }

  /* ---------- 播放器 ---------- */
  var audio = new Audio();
  audio.crossOrigin = 'anonymous';
  audio.volume = 0.8;
  audio.preload = 'none';

  var analyser = null, freqData = null;
  var canvas = null, ctx = null, drawing = false;
  var currentTitle = '';
  var currentMid = '';
  var currentKind = '';   /* song | episode */
  var statusFn = null;    /* 状态回调 (text, isErr) */
  var ui = {};            /* {titleEl, stateEl, playBtn, prevBtn} */

  function setStatus(text, isErr) {
    if (typeof statusFn === 'function') statusFn(text, isErr);
  }

  /* ---------- 频谱光效 ---------- */
  function initCanvas(canvasEl) {
    canvas = canvasEl;
    if (!canvas) return;
    ctx = canvas.getContext('2d');
    function resize() {
      canvas.width = window.innerWidth * (global.devicePixelRatio || 1);
      canvas.height = window.innerHeight * (global.devicePixelRatio || 1);
      canvas.style.width = window.innerWidth + 'px';
      canvas.style.height = window.innerHeight + 'px';
    }
    resize();
    window.addEventListener('resize', resize);
    if (!drawing) { drawing = true; drawLoop(); }
  }

  function drawLoop() {
    requestAnimationFrame(drawLoop);
    if (!ctx || !canvas) return;
    var w = canvas.width, h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    var level = 0;
    var data = freqData;
    if (analyser && data) {
      analyser.getByteFrequencyData(data);
      var sum = 0;
      for (var i = 0; i < data.length; i++) sum += data[i];
      level = sum / (data.length * 255);          /* 0~1 平均能量 */
    }

    /* 呼吸底光：随能量渐变 */
    var glow = 0.05 + level * 0.22;
    var g = ctx.createRadialGradient(w / 2, h * 0.62, 0, w / 2, h * 0.62, Math.max(w, h) * 0.7);
    g.addColorStop(0, 'rgba(0,210,255,' + glow.toFixed(3) + ')');
    g.addColorStop(0.55, 'rgba(58,123,213,' + (glow * 0.5).toFixed(3) + ')');
    g.addColorStop(1, 'rgba(8,12,36,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);

    /* 底部频谱光柱 */
    if (analyser && data) {
      var bars = 56;
      var bw = w / bars;
      var baseY = h;
      for (var b = 0; b < bars; b++) {
        var idx = Math.floor(b * data.length / bars);
        var v = data[idx] / 255;
        var bh = v * h * 0.5;
        var hue = 190 + b * 1.1;
        if (b > bars * 0.55) hue = 42 + (b - bars * 0.55) * 1.8; /* 高频偏金 */
        ctx.fillStyle = 'hsla(' + hue + ',92%,60%,' + (0.12 + v * 0.4).toFixed(3) + ')';
        ctx.shadowColor = 'hsla(' + hue + ',92%,60%,0.5)';
        ctx.shadowBlur = 14 * v;
        ctx.fillRect(b * bw + 3, baseY - bh, bw - 6, bh);
        ctx.shadowBlur = 0;
      }
    } else {
      /* 无音频时：极淡的呼吸波动，保持氛围 */
      var t = Date.now() / 1000;
      var amp = 0.04 + 0.03 * Math.sin(t * 1.3);
      ctx.fillStyle = 'rgba(0,210,255,' + amp.toFixed(3) + ')';
      ctx.fillRect(0, h - 3, w, 3);
    }
  }

  /* ---------- 播放控制 ---------- */
  function attachAudio() {
    if (analyser) return;
    var ac = new (window.AudioContext || window.webkitAudioContext)();
    var src = ac.createMediaElementSource(audio);
    analyser = ac.createAnalyser();
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.82;
    freqData = new Uint8Array(analyser.frequencyBinCount);
    src.connect(analyser);
    analyser.connect(ac.destination);
    /* 恢复音频上下文（iOS 需要用户手势解锁） */
    if (ac.state === 'suspended') ac.resume();
  }

  function playUrl(url, title, kind) {
    attachAudio();
    audio.src = url;
    audio.load();
    currentTitle = title || '';
    currentKind = kind || '';
    audio.onended = function () { updateUI(); };
    updateUI();
    /* 返回 play() 结果：被自动播放策略拦截时在此暴露（NotAllowedError） */
    var p = audio.play();
    return p || Promise.resolve();
  }

  function stop() {
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
    currentTitle = '';
    currentKind = '';
    updateUI();
  }

  function toggle() {
    if (audio.paused) {
      if (!audio.src) { setStatus('还没有可播放的内容', true); return; }
      attachAudio();
      var p = audio.play();
      if (p && p.catch) p.catch(function () {});
    } else {
      audio.pause();
    }
    updateUI();
  }

  function updateUI() {
    if (!ui.titleEl || !ui.stateEl) return;
    ui.titleEl.textContent = currentTitle || '暂无播放内容';
    ui.stateEl.textContent = audio.paused ? '已暂停' : '播放中';
  }

  /* ---------- 对外 API ---------- */
  var TavernPlayer = {
    VERSION: VERSION,

    /* 初始化：传 canvas 元素和 UI 元素 */
    init: function (opts) {
      opts = opts || {};
      initCanvas(opts.canvas || null);
      if (opts.statusFn) statusFn = opts.statusFn;
      ui = {
        titleEl: opts.titleEl || null,
        stateEl: opts.stateEl || null,
        playBtn: opts.playBtn || null,
        prevBtn: opts.prevBtn || null,
        nextBtn: opts.nextBtn || null
      };
      if (ui.playBtn) ui.playBtn.addEventListener('click', toggle);
      if (ui.prevBtn) ui.prevBtn.addEventListener('click', function () { if (ui.onPrev) ui.onPrev(); });
      if (ui.nextBtn) ui.nextBtn.addEventListener('click', function () { if (ui.onNext) ui.onNext(); });
      updateUI();
      return this;
    },

    isMobile: isMobile,

    /* 播放歌曲（uid 或 songmid）：
     *   mid: '00001wwR2VTfPE' 或 'L:00001wwR2VTfPE'
     * 返回 Promise<boolean>：true=已在页面播放，false=移动端已跳转 App */
    playSong: function (mid, title) {
      var songmid = String(mid || '').trim().replace(/^L:/, '');
      if (!songmid) return Promise.resolve(false);
      if (isMobile()) { this.jumpApp(songmid); return Promise.resolve(false); }
      setStatus('正在获取播放地址…');
      var self = this;
      return fetchVkey(songmid).then(function (url) {
        var p = playUrl(url, title || '正在播放', 'song');
        setStatus('正在播放 · ' + (title || ''));
        return p.then(function () { return true; }).catch(function (e) {
          self._blockedHint();
          return false;
        });
      }).catch(function (e) {
        setStatus(e.message + '（点击「🎵 播这首歌」前请先在 y.qq.com 登录）', true);
        return false;
      });
    },

    /* 播放小酒馆期次（data_type 5，通常需浏览器已登录 y.qq.com） */
    playEpisode: function (songmid, title) {
      if (!songmid) return Promise.resolve(false);
      if (isMobile()) { this.jumpApp(songmid); return Promise.resolve(false); }
      setStatus('正在获取本期音频（需 QQ音乐 登录态）…');
      var self = this;
      return fetchVkey(songmid).then(function (url) {
        var p = playUrl(url, title || '深夜小酒馆', 'episode');
        setStatus('正在播放 · ' + (title || '小酒馆本期'));
        return p.then(function () { return true; }).catch(function (e) {
          self._blockedHint();
          return false;
        });
      }).catch(function (e) {
        setStatus(e.message + '｜本期为节目音频，需登录 QQ音乐 后重试', true);
        return false;
      });
    },

    /* 候选列表按顺序播第一首能播的：
     *   songs: [{mid, title}, ...]（已按优先级排序）
     * 返回：true=已播放 | false=全部不可播 | {blocked:true}=内容可用但被自动播放策略拦截 */
    playFirstAvailable: function (songs) {
      var self = this;
      if (!songs || !songs.length) return Promise.resolve(false);
      var mids = songs.map(function (s) { return String(s.mid || '').replace(/^L:/, ''); });
      if (isMobile()) { this.jumpApp(mids[0]); return Promise.resolve(false); }
      setStatus('正在为你挑一首今晚最值得听的歌…');
      return fetchVkeys(mids).then(function (urls) {
        for (var i = 0; i < urls.length; i++) {
          if (!urls[i]) continue;
          setStatus('正在播放 · ' + (songs[i].title || ''));
          var p = playUrl(urls[i], songs[i].title, 'song');
          return p.then(function () { return true; }).catch(function () {
            setStatus('浏览器拦了自动播放，点一下页面任意处就能听到', true);
            return { blocked: true };
          });
        }
        setStatus('这轮候选歌曲暂时都无法播放，试试「🎲 免费试听」', true);
        return false;
      }).catch(function (e) {
        setStatus(e.message + '，稍后再试', true);
        return false;
      });
    },

    /* 自动播放被拦时的统一提示 */
    _blockedHint: function () {
      setStatus('浏览器拦了自动播放，点一下页面任意处就能听到', true);
    },

    /* 移动端跳转 QQ音乐 App（新标签打开，原页面保留，播完可切回） */
    jumpApp: function (mid) {
      var songmid = String(mid || '').trim().replace(/^L:/, '');
      var web = 'https://y.qq.com/n/ryqq/songDetail/' + songmid;
      var win = global.open(web, '_blank');
      if (!win) global.location.href = web;   /* 被拦截时降级为当前页跳转 */
    },

    stop: stop,
    toggle: toggle,
    getAudio: function () { return audio; },
    isPlaying: function () { return !audio.paused && !!audio.src; }
  };

  global.TavernPlayer = TavernPlayer;
})(window);
