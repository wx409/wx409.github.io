/* ============================================================
 * 深夜小酒馆 · 互动引擎 (TavernKeeper)
 * 纯静态、零后端。受王晰「日木斤深夜小酒馆」节目启发，粉丝创作。
 * 素材：歌词片段 / 采访语录 / 金句 / 小酒馆文案（本地 JSON）
 * 歌曲与数据洞察：从 dashboard_data.json 动态读取（失败时降级到 songs_compact.json）
 * ============================================================ */
(function (global) {
  'use strict';

  var VERSION = '1.0.0';

  /* ---------- 情绪配置：一杯酒 ---------- */
  var MOODS = {
    insomnia: { label: '深夜失眠', drink: '安眠月光', color: '#ffb74d', glass: '🎑',
      greeting: '夜深了，把白天所有的忙乱都放在门外，我陪你喝一杯安神的。',
      goodnight: '晚安，祝你的夜里有光、有酒、有梦。' },
    longing: { label: '思念一个人', drink: '晚风相思', color: '#4dd0e1', glass: '🌙',
      greeting: '想一个人，是很贵的，今晚这杯我请。',
      goodnight: '愿梦里相见，醒来无恙。晚安。' },
    healing: { label: '需要被治愈', drink: '热汤暖心', color: '#ffd700', glass: '☕',
      greeting: '欢迎回来，先把心放在吧台上歇一歇，剩下的交给我。',
      goodnight: '心是暖的，夜就是暖的。晚安。' },
    motivate: { label: '想被鼓励', drink: '勇气气泡', color: '#00ff9d', glass: '🍸',
      greeting: '别急，喝下这杯，明天又是乘风破浪的一天。',
      goodnight: '去梦里积蓄力气，醒来继续发光。晚安。' },
    letgo: { label: '释怀告别', drink: '放下茶', color: '#64b5f6', glass: '🍵',
      greeting: '有些事，就像喝茶，只有两个动作：拿起、放下。',
      goodnight: '放下的人，都值得一杯好觉。晚安。' },
    romance: { label: '浪漫心动', drink: '微醺玫瑰', color: '#f48fb1', glass: '🍷',
      greeting: '今晚风很轻，酒很温柔，适合想一些甜甜的事。',
      goodnight: '梦里有玫瑰和月光。晚安。' },
    lonely: { label: '独自一人', drink: '独酌月影', color: '#b39ddb', glass: '🏮',
      greeting: '一个人坐吧台也挺好，月亮今晚就归你一个人。',
      goodnight: '孤独不可怕，有人在远处陪你失眠。晚安。' }
  };

  /* ---------- 晚安模板（按情绪） ---------- */
  var GOODNIGHTS = {
    insomnia: ['晚安，祝你的夜里有光、有酒、有梦。', '睡不着的夜，也值得被好好对待。晚安。'],
    longing: ['愿梦里相见，醒来无恙。晚安。', '把思念交给月亮，你只管入睡。晚安。'],
    healing: ['心是暖的，夜就是暖的。晚安。', '被治愈是需要时间的，今晚先把觉睡好。晚安。'],
    motivate: ['去梦里积蓄力气，醒来继续发光。晚安。', '明天的你会感谢今天好好睡觉的自己。晚安。'],
    letgo: ['放下的人，都值得一杯好觉。晚安。', '晚安，明天会是个新的开始。'],
    romance: ['梦里有玫瑰和月光。晚安。', '把心动藏进梦里，明天再去见面。晚安。'],
    lonely: ['孤独不可怕，有人在远处陪你失眠。晚安。', '今晚的酒馆一直亮着灯，随时欢迎你再来。晚安。']
  };

  /* ---------- 默认文案（素材缺失时降级） ---------- */
  var FALLBACK = {
    lyric: '夜色温柔，把心放轻，明天会好的。',
    interview: '唱得动听，不如活得真诚。',
    golden: '向下扎根，向上开花。',
    tavern: '欢迎光临深夜小酒馆，今晚想喝点什么？'
  };

  /* ---------- 情绪关键词映射：英文情绪键 → 素材中的中文情绪标签 ---------- */
  var MOOD_TAG_MAP = {
    insomnia: ['失眠', '深夜', '孤独', '平静'],
    longing: ['思念', '感伤', '回忆', '爱情', '深夜'],
    healing: ['治愈', '温暖', '平静', '希望', '释怀', '温柔'],
    motivate: ['励志', '勇气', '坚持', '希望', '自信', '出发', '梦想', '热爱', '热血'],
    letgo: ['释怀', '告别', '离别', '感伤', '平静', '回忆', '祝福'],
    romance: ['浪漫', '爱情', '温暖', '心动', '温柔', '自由'],
    lonely: ['孤独', '深夜', '温柔', '感伤', '平静']
  };

  /* ---------- 随机工具 ---------- */
  function pick(arr) {
    if (!arr || !arr.length) return null;
    return arr[Math.floor(Math.random() * arr.length)];
  }
  function shuffle(arr) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  function matchMood(item, moodKey) {
    if (!item || !item.moods || !item.moods.length) return false;
    var tags = MOOD_TAG_MAP[moodKey] || [];
    if (!tags.length) return false;
    return item.moods.some(function (m) { return tags.indexOf(m) >= 0; });
  }
  function fetchJSON(url, timeout) {
    timeout = timeout || 8000;
    return new Promise(function (resolve, reject) {
      var ctrl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
      var timer = setTimeout(function () { if (ctrl) ctrl.abort(); }, timeout);
      var opt = { method: 'GET' };
      if (ctrl) opt.signal = ctrl.signal;
      fetch(url, opt).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }).then(function (d) { clearTimeout(timer); resolve(d); })
        .catch(function (e) { clearTimeout(timer); reject(e); });
    });
  }

  /* ============================================================
   * TavernKeeper
   * ============================================================ */
  function TavernKeeper(options) {
    options = options || {};
    this.base = options.base || './';
    this._assets = null;        // {lyrics, interview, golden, tavern}
    this._songPool = null;      // {list: [{name,...}], data: dashboard原始对象或compact}
    this._songCacheKey = '__tavern_songs_v1__';
    this._assetsPromise = null;
    this._songsPromise = null;
    this._transcripts = null;   // 完整逐字稿 {EP01_P1: {text, theme, ...}, ...}
    this._transcriptsPromise = null;
  }

  TavernKeeper.VERSION = VERSION;
  TavernKeeper.MOODS = MOODS;

  TavernKeeper.prototype.loadAssets = function () {
    var self = this;
    if (this._assetsPromise) return this._assetsPromise;
    var files = {
      lyrics: 'lyrics_fragments.json',
      interview: 'interview_quotes.json',
      golden: 'golden_quotes.json',
      tavern: 'tavern_quotes.json'
    };
    this._assetsPromise = Promise.all(Object.keys(files).map(function (key) {
      return fetchJSON(self.base + files[key]).then(function (d) { return { key: key, data: d }; })
        .catch(function () { return { key: key, data: null }; });
    })).then(function (results) {
      var out = { lyrics: {}, interview: {}, golden: {}, tavern: {} };
      results.forEach(function (r) { out[r.key] = r.data || out[r.key]; });
      self._assets = out;
      return out;
    });
    return this._assetsPromise;
  };

  /* 懒加载歌曲池：优先 dashboard_data.json（动态数据源），失败降级 songs_compact.json */
  TavernKeeper.prototype.loadSongs = function () {
    var self = this;
    if (this._songsPromise) return this._songsPromise;

    /* 1. 尝试本地缓存（sessionStorage，量大时自动放弃） */
    try {
      var cached = sessionStorage.getItem(this._songCacheKey);
      if (cached) {
        var obj = JSON.parse(cached);
        this._songPool = obj;
        this._songsPromise = Promise.resolve(obj);
        return this._songsPromise;
      }
    } catch (e) { /* 忽略配额问题 */ }

    var fromDashboard = fetchJSON('../dashboard/dashboard_data.json', 12000)
      .then(function (data) {
        var list = (data.song_index || []).map(function (s) {
          return { uid: s.uid, name: s.name, attr: s.attr, release: s.release,
                   latest: s.latest, mean30: s.mean30, peak: s.peak, lifecycle: s.lifecycle };
        });
        return { source: 'dashboard_data.json', version: data.timestamp || '', list: list };
      });
    var fromCompact = fetchJSON(this.base + 'songs_compact.json', 8000)
      .then(function (data) { return { source: 'songs_compact.json', version: data.generated_at || '', list: data.songs || [] }; });

    this._songsPromise = fromDashboard
      .catch(function () { return fromCompact; })
      .then(function (pool) {
        self._songPool = pool;
        /* 缓存：2MB 级别的数据尝试存入，失败无妨 */
        try {
          if (pool.list.length > 0) sessionStorage.setItem(self._songCacheKey, JSON.stringify(pool));
        } catch (e) { /* 配额不足则跳过缓存 */ }
        return pool;
      });
    return this._songsPromise;
  };

  /* 模糊搜索歌曲 */
  TavernKeeper.prototype.searchSongs = function (q, limit) {
    limit = limit || 12;
    if (!this._songPool) return [];
    var s = String(q || '').trim();
    if (!s) return this._songPool.list.slice(0, limit);
    var lower = s.toLowerCase();
    return this._songPool.list.filter(function (song) {
      return song.name && song.name.toLowerCase().indexOf(lower) >= 0;
    }).slice(0, limit);
  };

  TavernKeeper.prototype.findSong = function (name) {
    if (!this._songPool || !name) return null;
    var s = String(name).trim();
    var exact = this._songPool.list.filter(function (x) { return x.name === s; });
    if (exact.length) return exact[0];
    var fuzzy = this._songPool.list.filter(function (x) { return x.name && x.name.indexOf(s) >= 0; });
    return fuzzy.length ? fuzzy[0] : null;
  };

  /* 数据洞察 */
  TavernKeeper.prototype.insight = function (song, pool) {
    if (!song) return null;
    pool = pool || (this._songPool ? this._songPool.list : null);
    var rank = null;
    if (pool && pool.length) {
      var sorted = pool.slice().sort(function (a, b) {
        return (Number(b.mean30) || 0) - (Number(a.mean30) || 0);
      });
      var idx = sorted.indexOf(song);
      if (idx >= 0) rank = idx + 1;
    }
    return {
      name: song.name,
      attr: song.attr || '',
      release: song.release || '',
      latest: song.latest,
      mean30: song.mean30,
      peak: song.peak,
      rank: rank,
      poolSize: pool ? pool.length : null,
      dataSource: this._songPool ? this._songPool.source : '',
      dataVersion: this._songPool ? this._songPool.version : ''
    };
  };

  /* ---------- 素材检索 ---------- */
  function collectLyrics(assets, songName, mood) {
    var frags = [];
    if (songName && assets.lyrics[songName]) {
      frags = frags.concat(assets.lyrics[songName].fragments || []);
    }
    /* 补充：用情绪匹配其它歌曲片段 */
    Object.keys(assets.lyrics).forEach(function (name) {
      if (name === songName) return;
      (assets.lyrics[name].fragments || []).forEach(function (f) {
        if (matchMood(f, mood)) frags.push(f);
      });
    });
    if (!frags.length) return null;
    var hit = pick(frags);
    return { text: hit.text, source: hit.source || songName || '' };
  }
  function collectByMood(obj, mood) {
    var pool = [];
    Object.keys(obj || {}).forEach(function (topic) {
      var items = obj[topic];
      if (!Array.isArray(items)) return; /* 跳过 _meta 等元数据字段 */
      items.forEach(function (item) {
        if (matchMood(item, mood)) pool.push({ topic: topic, item: item });
      });
    });
    return pool;
  }
  function collectTavern(tav, mood) {
    var pool = (tav.episodes || []).filter(function (e) { return matchMood(e, mood); });
    if (!pool.length) pool = tav.episodes || [];
    var hit = pick(pool);
    if (!hit) return null;
    return { text: hit.text, episode: hit.episode || '', note: hit.note || '', has_transcript: hit.has_transcript !== false };
  }

  /* ---------- 调酒 ---------- */
  TavernKeeper.prototype.makeDrink = function (moodKey, songName, opts) {
    opts = opts || {};
    var assets = this._assets || { lyrics: {}, interview: {}, golden: {}, tavern: {} };
    var mood = MOODS[moodKey] || MOODS.healing;
    var song = this.findSong(songName);

    /* 歌词 */
    var lyric = collectLyrics(assets, song ? song.name : null, moodKey);
    if (!lyric) lyric = { text: FALLBACK.lyric, source: '' };

    /* 采访 */
    var ivPool = collectByMood(assets.interview, moodKey);
    var iv = ivPool.length ? pick(ivPool) : null;

    /* 金句 */
    var gdPool = collectByMood(assets.golden, moodKey);
    var gd = gdPool.length ? pick(gdPool) : null;

    /* 小酒馆文案 */
    var tav = collectTavern(assets.tavern, moodKey);

    /* 数据洞察 */
    var insight = this.insight(song, opts.pool || undefined);

    /* 酒名 */
    var drinkName = mood.drink;
    if (song && song.name) {
      drinkName = mood.drink + ' · ' + song.name;
    } else if (songName && songName.trim()) {
      drinkName = mood.drink + ' · 「' + songName.trim() + '」';
    }

    return {
      mood: moodKey,
      moodLabel: mood.label,
      drinkName: drinkName,
      drinkGlass: mood.glass,
      color: mood.color,
      greeting: opts.greeting || mood.greeting,
      tavern: tav || { text: FALLBACK.tavern, episode: '', note: '' },
      lyric: lyric,
      interview: iv ? { topic: iv.topic, text: iv.item.text, context: iv.item.context } : null,
      golden: gd ? { topic: gd.topic, text: gd.item.text } : null,
      insight: insight,
      goodnight: pick(GOODNIGHTS[moodKey] || GOODNIGHTS.healing),
      songFound: !!song,
      generatedAt: opts.generatedAt || new Date().toISOString()
    };
  };

  /* 随机来一杯 */
  TavernKeeper.prototype.randomDrink = function () {
    var keys = Object.keys(MOODS);
    return this.makeDrink(pick(keys), '');
  };

  /* 懒加载完整逐字稿 */
  TavernKeeper.prototype.loadTranscripts = function () {
    var self = this;
    if (this._transcriptsPromise) return this._transcriptsPromise;
    this._transcriptsPromise = fetchJSON(this.base + 'tavern_transcripts.json', 15000)
      .then(function (data) {
        self._transcripts = data.episodes || {};
        return self._transcripts;
      })
      .catch(function () {
        self._transcripts = {};
        return self._transcripts;
      });
    return this._transcriptsPromise;
  };

  /* 按 episode 标识获取完整逐字稿 */
  TavernKeeper.prototype.getTranscript = function (episodeId) {
    if (!this._transcripts) return null;
    return this._transcripts[episodeId] || null;
  };

  /* 查找某期节目的 transcript key（支持 EP03 → EP03_P1 / EP03_P2） */
  TavernKeeper.prototype.findTranscriptKey = function (episode, part) {
    if (!this._transcripts) return null;
    if (part) {
      var key = episode + '_P' + part;
      if (this._transcripts[key]) return key;
    }
    // 尝试 P1 / P2
    var k1 = episode + '_P1';
    if (this._transcripts[k1]) return k1;
    var k2 = episode + '_P2';
    if (this._transcripts[k2]) return k2;
    return null;
  };

  global.TavernKeeper = TavernKeeper;
})(window);
