/* ============================================================================
 * 数据知识库搜索引擎（DataSpeak）
 * ----------------------------------------------------------------------------
 * 纯前端实时计算：读取大屏页面已加载的 dashboardData（无需新接口/预生成索引），
 * 让数据「开口说话」。能力：
 *   ① 查歌检索   —— 歌名/别名模糊匹配，展开完整档案卡（指标+迷你趋势图）
 *   ② 数据问答   —— 「涨幅最大的歌」「周末听什么」等意图实时从数据算出答案
 *   ③ 洞察引用   —— 预计算结论句匹配（巡演/发行/周末溢价/老歌复活/异动…）
 *   ④ 自然问句   —— 中文模板解析 + 关键词词典
 *   ⑤ 图表联动   —— 每条结果可跳转高亮下方对应图表区块
 *   ⑥ 可扩展     —— 歌曲档案动态字段（未来新增「来源:电台」等元数据自动透传显示）
 * 依赖：无（可选 echarts，用于档案卡迷你趋势图；缺失时降级为文本）
 * ========================================================================== */
(function () {
  'use strict';

  var D = null;            // dashboardData（页面内联脚本注入，后续脚本可读）
  var songs = [];          // 合并后的歌曲档案
  var nameIndex = [];      // 歌名/别名索引
  var insights = [];       // 预计算洞察句
  var pendingSpark = [];   // 等待 echarts 就绪后绘制的迷你图队列

  // ---- 跨站关系数据（entity_index.json + cities.json，异步加载）----
  var entitySongs = null;  // entity_index.json 的 songs（歌曲 → live/tavern 关系）
  var citiesData = null;   // cities.json（城市 → shows）
  var extrasState = 'pending'; // pending | ready | failed
  var extrasWaiters = [];  // 加载完成后待执行的回调

  /* ---------------- 跨站数据加载（人-歌-城三位一体） ---------------- */
  function loadExtras() {
    if (extrasState !== 'pending') return;
    extrasState = 'loading';
    var remain = 2;
    function done() { if (--remain <= 0) { extrasState = 'ready'; fireWaiters(); } }
    function fail() { extrasState = 'failed'; fireWaiters(); }
    fetch('../entity_index.json').then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { entitySongs = (j && j.songs) || null; done(); })
      .catch(fail);
    fetch('../data/cities.json').then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { citiesData = (j && j.cities) || null; done(); })
      .catch(fail);
  }
  function whenExtras(fn) {
    if (extrasState === 'ready') { fn(); return; }
    if (extrasState === 'failed') return;
    extrasWaiters.push(fn);
    loadExtras();
  }
  function fireWaiters() {
    var q = extrasWaiters;
    extrasWaiters = [];
    q.forEach(function (fn) { try { fn(); } catch (e) {} });
  }

  /* ---------------- 工具 ---------------- */
  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function fmt(n) {
    if (n === null || n === undefined || n === '' || isNaN(n)) return '—';
    return Math.round(Number(n)).toLocaleString('en-US');
  }
  function pct(x) {
    if (x === null || x === undefined || isNaN(x)) return '—';
    var v = Math.round(Number(x) * 10) / 10;
    return (v >= 0 ? '+' : '') + v + '%';
  }
  function downSample(pts, maxN) {
    if (!pts || !pts.length) return [];
    if (pts.length <= maxN) return pts;
    var out = [], step = pts.length / maxN;
    for (var i = 0; i < maxN; i++) out.push(pts[Math.floor(i * step)]);
    out.push(pts[pts.length - 1]);
    return out;
  }

  /* ---------------- ① 构建歌曲档案（优先 song_index，兼容旧 detail_songs+rank_groups） ---------------- */
  function buildSongs() {
    var src = (D.song_index && D.song_index.length) ? D.song_index : null;
    if (src) {
      songs = src.map(function (s) {
        var rec = {
          uid: s.uid || '', name: s.name || '', attr: s.attr || '', release: s.release || '-',
          latest: s.latest, mean30: s.mean30, peak: s.peak,
          lifecycle: s.lifecycle || '', score: s.score, streak: s.streak,
          best_rank: s.best_rank, active_days: s.active_days, profile: s.profile || [],
          points: downSample(s.points || [], 120),
          _src: s
        };
        return rec;
      });
    } else {
      var byName = {};
      (D.detail_songs || []).forEach(function (s) {
        var rec = {
          uid: s.uid || '', name: s.name || '', attr: s.attr || '', release: s.release || '-',
          latest: s.latest, mean30: s.mean30, peak: s.peak,
          points: downSample(s.points, 120),
          lifecycle: '', score: '', streak: '', _src: s
        };
        byName[rec.name] = rec;
        songs.push(rec);
      });
      Object.keys(D.rank_groups || {}).forEach(function (cat) {
        (D.rank_groups[cat] || []).forEach(function (r) {
          var rec = byName[r[1]];
          if (rec) {
            rec.score = r[2]; rec.lifecycle = r[5]; rec.streak = r[4];
            if (r[6] && r[6] !== '-' && (!rec.release || rec.release === '-')) rec.release = r[6];
            if (!rec.attr) rec.attr = r[7] || cat;
          } else {
            rec = {
              uid: r[0] || '', name: r[1] || '', attr: r[7] || cat, release: r[6] || '-',
              latest: '', mean30: r[3], peak: '', points: [],
              lifecycle: r[5] || '', score: r[2], streak: r[4], _src: null
            };
            byName[rec.name] = rec;
            songs.push(rec);
          }
        });
      });
    }
    // 别名索引（历史 uid→名 映射）
    Object.keys(D.hist_uid_names || {}).forEach(function (k) {
      var n = D.hist_uid_names[k];
      if (n && nameIndex.indexOf(n) < 0) nameIndex.push(n);
    });
    songs.forEach(function (s) { if (s.name) nameIndex.push(s.name); });
  }

  function findSong(q) {
    if (q.length < 2) return null;
    var exact = null;
    for (var i = 0; i < songs.length; i++) {
      if (songs[i].name === q) return songs[i];
      if (!exact && songs[i].name.indexOf(q) >= 0) exact = songs[i];
    }
    if (exact) return exact;
    for (var j = 0; j < nameIndex.length; j++) {
      if (nameIndex[j].indexOf(q) >= 0) {
        for (var k = 0; k < songs.length; k++) {
          if (songs[k].name === nameIndex[j]) return songs[k];
        }
      }
    }
    return null;
  }

  /* ---------------- ③ 预计算洞察句（全部由真实数据生成，无编造） ---------------- */
  function buildInsights() {
    var cs = D.chart_summaries || {};
    function add(text, anchor, keys) {
      if (text) insights.push({ text: text, anchor: anchor || '', keys: keys || [] });
    }
    add(cs.sankey, 'sankeyChart', ['生命周期', '沉淀', '流转', '生态']);
    add(cs.weekend_premium, 'albumPremiumChart', ['周末', '溢价', '专辑', '通勤']);
    add(cs.timeline, 'timelineChart', ['时间轴', '竞争', '格局', '月度']);
    add(cs.waterfall, 'waterfallChart', ['排名', '战争', '瀑布', '跃迁']);
    var tf = (D.tour_fx || []).slice().sort(function (a, b) { return (b.uplift || 0) - (a.uplift || 0); });
    if (tf.length) add('在可量化的 ' + tf.length + ' 个巡演节点中，带动最强的是 ' + tf[0].label + '（+' + tf[0].uplift + '%）。', 'tourFxChart', ['巡演', '演唱', '现场', '带动']);
    var rf = (D.release_fx || []).slice().sort(function (a, b) { return (b.avg || 0) - (a.avg || 0); });
    if (rf.length) add('新歌发行14日平均指数最高：' + rf[0].label + '（平均 ' + fmt(rf[0].avg) + '，峰值 ' + fmt(rf[0].peak) + '）。', 'tourFxChart', ['发行', '新歌', '上线', '新曲']);
    var ap = D.weekend_premium || {};
    if (ap.album !== undefined && ap.ost !== undefined) add('专辑类周末溢价 ' + ap.album + ' vs OST/单曲 ' + ap.ost + '——专辑更具周末沉浸式聆听特质。', 'albumPremiumChart', ['周末', '专辑', '听']);
    var ss = D.second_spring || {};
    if (ss.names && ss.names.length) add('近30日出现「第二春」的老歌：' + ss.names.slice(0, 3).join('、') + '（偏离度最高 +' + (ss.values && ss.values[0] || 0) + '%）。', 'sankeyChart', ['复活', '回春', '老歌', '第二春']);
    var da = D.daily_anomalies || [];
    if (da.length) add('今日监测到 ' + da.length + ' 条异动：' + da.map(function (x) { return x.song || x.name || x.label || ''; }).filter(Boolean).join('、') + '。', 'summary', ['异常', '异动', '今日']);
    var tr = D.trend_raw || [], lb = D.time_labels || [];
    if (tr.length >= 2 && tr[0]) add('全曲目月度平均指数：' + lb[0] + ' ' + fmt(tr[0]) + ' → ' + lb[lb.length - 1] + ' ' + fmt(tr[tr.length - 1]) + '。', 'trendChart', ['趋势', '走势', '平均', '指数']);
  }

  function matchInsights(q) {
    var s = String(q || '').replace(/\s+/g, '');
    if (!s) return [];
    var scored = insights.map(function (it) {
      var score = 0;
      for (var i = 0; i < it.keys.length; i++) if (s.indexOf(it.keys[i]) >= 0) score++;
      return { it: it, score: score };
    }).filter(function (x) { return x.score > 0; })
      .sort(function (a, b) { return b.score - a.score; })
      .slice(0, 2);
    return scored.map(function (x) { return x.it; });
  }

  /* ---------------- ② 意图解析（自然问句模板 + 关键词词典） ---------------- */
  function parseIntent(q) {
    var s = String(q || '').replace(/\s+/g, '');
    if (!s) return { type: 'empty' };
    var hit = findSong(s);
    if (hit) return { type: 'song', song: hit.name };
    // 多歌曲对比检测：在原始输入上按空格/逗号/和/与/vs 分词，
    // 命中 ≥2 首歌 → 对比意图（「A 和 B」「A vs B」「A 对比 B」等组合查询）
    var raw = String(q || '');
    var matchedSongs = [];
    raw.split(/[\s,，、/;；+&|]+|和|与|\bvs\b/i).forEach(function (t) {
      t = t.trim();
      if (t.length < 2) return;
      var h = findSong(t);
      if (h && matchedSongs.indexOf(h.name) < 0) matchedSongs.push(h.name);
    });
    if (matchedSongs.length >= 2) return { type: 'compare_songs', songs: matchedSongs };
    var intents = [
      { type: 'top_trend', re: /涨幅|飙升|涨得|上涨最多|涨最多|上升最多|最猛|涨最/ },
      { type: 'top_index', re: /指数最高|最热|最火|最受欢迎|收听最多|最厉害|第一名|最强|平均最高|热度最高|排行/ },
      { type: 'weekend', re: /周末|双休|通勤|休息日|工作日|什么时候听/ },
      { type: 'tour', re: /巡演|演唱会|现场|带动|北京|广州|重庆|成都|深圳|西安|上海|南京|武汉|杭州|巡唱/ },
      { type: 'release', re: /发行|新歌|新曲|新单|上线|发布|新专辑/ },
      { type: 'anomaly', re: /异常|异动|警报|突然|爆/ },
      { type: 'lifecycle', re: /沉淀|经典|上升期|稳定期|生命周期|复活|回春|第二春|老歌|长尾/ },
      { type: 'compare', re: /对比|差距|差别|哪个.*(高|低|多|少)|比.*(高|低|多|少)|\bvs\b/ },
      { type: 'recent', re: /最近|近7|近30|近90|今日|今天|昨日|昨天|新鲜/ }
    ];
    for (var i = 0; i < intents.length; i++) {
      if (intents[i].re.test(s)) return { type: intents[i].type };
    }
    return { type: 'browse' };
  }

  /* ---------------- 各意图的实时计算 ---------------- */
  function jumpBlock(anchor, label) {
    return { type: 'jump', anchor: anchor, label: label };
  }
  function songBlocks(name) {
    var r = null;
    for (var i = 0; i < songs.length; i++) if (songs[i].name === name) { r = songs[i]; break; }
    if (!r) return [{ type: 'answer', text: '未在数据集中找到《' + esc(name) + '》，试试「browse」或搜索歌名片段。' }];
    return [
      { type: 'list', title: '《' + esc(r.name) + '》档案', items: [r] },
      jumpBlock('trendChart', '全景趋势')
    ];
  }
  function topTrendBlocks() {
    var tops = (D.top_songs || []).slice().sort(function (a, b) { return (b.trend || 0) - (a.trend || 0); }).slice(0, 5);
    if (!tops.length) return [{ type: 'answer', text: '暂无近期异常活跃数据。' }];
    return [
      { type: 'answer', text: '按环比涨幅排序，近期最活跃的歌曲：' },
      { type: 'rows', items: tops.map(function (t) {
        return '<div class="sr-row"><span class="sr-rank">' + (tops.indexOf(t) + 1) + '</span>' +
          '<span class="sr-song">' + esc(t.name) + '</span>' +
          '<span class="sr-val up">' + pct(t.trend) + '</span>' +
          '<span class="sr-tag">' + esc(t.tag || '') + '</span></div>';
      }) },
      jumpBlock('summary', '核心结论')
    ];
  }
  function topIndexBlocks(q) {
    var byPeak = /峰值|最高峰/.test(q);
    var arr = songs.filter(function (s) { return byPeak ? (s.peak || 0) > 0 : (s.mean30 || 0) > 0; })
      .sort(function (a, b) { return (byPeak ? (b.peak || 0) : (b.mean30 || 0)) - (byPeak ? (a.peak || 0) : (a.mean30 || 0)); })
      .slice(0, 8);
    if (!arr.length) return [{ type: 'answer', text: '暂无指数数据。' }];
    return [
      { type: 'answer', text: '按' + (byPeak ? '历史峰值' : '近30日均值') + '排序，榜单前列作品：' },
      { type: 'list', title: 'Top ' + arr.length, items: arr },
      jumpBlock('trendChart', '全景趋势')
    ];
  }
  function weekendBlocks() {
    var ap = D.weekend_premium || {};
    var ww = D.weekend_workday || [];
    var lines = [];
    if (ap.attr_premium && ap.attr_premium.length) {
      var parts = ap.attr_premium.map(function (x) { return x.attr + ' ' + x.ratio; }).join('，');
      lines.push('周末/工作日溢价（按类别）：' + parts + '。');
    }
    if (ww.length >= 2) {
      var diff = ww[1] ? ((ww[0] - ww[1]) / ww[1] * 100) : 0;
      lines.push('全站周末平均指数 ' + fmt(ww[0]) + ' vs 工作日 ' + fmt(ww[1]) + '（' + (diff >= 0 ? '高' : '低') + Math.abs(Math.round(diff * 10) / 10) + '%）。');
    }
    var rec = (ap.album_songs || []).slice(0, 6);
    var ost = (ap.ost_songs || []).slice(0, 6);
    var blocks = [
      { type: 'answer', text: lines.length ? lines.join(' ') : '暂无周末数据。' }
    ];
    if (rec.length) blocks.push({ type: 'list', title: '周末更适合沉浸聆听的专辑类（Top6）', items: rec.map(nameToRec).filter(Boolean) });
    if (ost.length) blocks.push({ type: 'list', title: 'OST/单曲类（Top6）', items: ost.map(nameToRec).filter(Boolean) });
    blocks.push(jumpBlock('albumPremiumChart', '时间偏好洞察图'));
    return blocks;
  }
  function tourBlocks() {
    var tf = (D.tour_fx || []).slice().sort(function (a, b) { return (b.uplift || 0) - (a.uplift || 0); }).slice(0, 5);
    var ev = (D.tour_events || []).slice(-5).reverse();
    if (!tf.length && !ev.length) return [{ type: 'answer', text: '暂无巡演数据。' }];
    var blocks = [];
    if (tf.length) {
      blocks.push({ type: 'answer', text: '巡演后7日全站日均指数较基线涨幅 Top' + tf.length + '：' });
      blocks.push({ type: 'rows', items: tf.map(function (t) {
        return '<div class="sr-row"><span class="sr-rank">' + (tf.indexOf(t) + 1) + '</span>' +
          '<span class="sr-song">' + esc(t.label) + '</span>' +
          '<span class="sr-val up">+' + t.uplift + '%</span></div>';
      }) });
    }
    if (ev.length) blocks.push({ type: 'answer', text: '最近巡演节点：' + ev.map(function (e) { return esc(e[1]); }).join('；') + '。' });
    blocks.push(jumpBlock('tourFxChart', '巡演与发行事件图'));
    return blocks;
  }
  function releaseBlocks() {
    var rf = (D.release_fx || []).slice().sort(function (a, b) { return (b.avg || 0) - (a.avg || 0); }).slice(0, 5);
    var ev = (D.release_events || []).slice(-5).reverse();
    if (!rf.length && !ev.length) return [{ type: 'answer', text: '暂无发行数据。' }];
    var blocks = [];
    if (rf.length) {
      blocks.push({ type: 'answer', text: '新歌发行14日表现 Top' + rf.length + '（平均指数 / 峰值）：' });
      blocks.push({ type: 'rows', items: rf.map(function (t) {
        return '<div class="sr-row"><span class="sr-rank">' + (rf.indexOf(t) + 1) + '</span>' +
          '<span class="sr-song">' + esc(t.label) + '</span>' +
          '<span class="sr-val">' + fmt(t.avg) + ' / ' + fmt(t.peak) + '</span></div>';
      }) });
    }
    if (ev.length) blocks.push({ type: 'answer', text: '最近发行事件：' + ev.map(function (e) { return esc(e[1]); }).join('；') + '。' });
    blocks.push(jumpBlock('tourFxChart', '巡演与发行事件图'));
    return blocks;
  }
  function anomalyBlocks() {
    var da = D.daily_anomalies || [];
    var tops = (D.top_songs || []).filter(function (t) { return /飙升|暴涨|上涨/.test(t.tag || ''); }).slice(0, 5);
    if (!da.length && !tops.length) return [{ type: 'answer', text: '当前监测平稳，暂无显著异动。' }];
    var blocks = [];
    if (da.length) blocks.push({ type: 'answer', text: '今日异动 ' + da.length + ' 条：' + da.map(function (x) { return esc(x.song || x.name || x.label || ''); }).join('、') + '。' });
    if (tops.length) {
      blocks.push({ type: 'answer', text: '近30日标记为异常活跃的歌曲：' });
      blocks.push({ type: 'rows', items: tops.map(function (t) {
        return '<div class="sr-row"><span class="sr-song">' + esc(t.name) + '</span>' +
          '<span class="sr-val up">' + pct(t.trend) + '</span>' +
          '<span class="sr-tag">' + esc(t.tag || '') + '</span></div>';
      }) });
    }
    blocks.push(jumpBlock('summary', '核心结论'));
    return blocks;
  }
  function lifecycleBlocks(q) {
    var which = /沉淀|经典/.test(q) ? '经典沉淀期' : (/上升/.test(q) ? '上升期' : (/稳定/.test(q) ? '稳定期' : ''));
    var arr = songs.filter(function (s) { return which ? s.lifecycle === which : s.lifecycle; })
      .sort(function (a, b) { return (b.score || 0) - (a.score || 0); }).slice(0, 8);
    var lm = D.lifecycle_migration || {};
    var links = lm.links || [];
    var blocks = [];
    if (!which) {
      var dist = {};
      songs.forEach(function (s) { if (s.lifecycle) dist[s.lifecycle] = (dist[s.lifecycle] || 0) + 1; });
      blocks.push({ type: 'answer', text: '当前生命周期分布：' + Object.keys(dist).map(function (k) { return k + ' ' + dist[k] + ' 首'; }).join('，') + '。' });
    } else if (arr.length) {
      blocks.push({ type: 'answer', text: '「' + which + '」作品（按综合得分）：' });
      blocks.push({ type: 'list', title: which + ' Top' + arr.length, items: arr });
    }
    if (links.length) {
      var s = links.filter(function (l) { return /经典/.test(l.target || ''); }).map(function (l) { return l.value; });
      blocks.push({ type: 'answer', text: '近60日生命周期流转：' + links.length + ' 组流动关系，' + (s.length ? s[s.length - 1] : 0) + ' 首沉淀为经典。' });
    }
    blocks.push(jumpBlock('sankeyChart', '生命周期流转图'));
    return blocks;
  }
  function compareSongsBlocks(names) {
    // 多歌曲对比：并排档案卡 + 核心指标差异小结（全部实时从 song_index 计算）
    var recs = names.map(function (n) {
      for (var i = 0; i < songs.length; i++) if (songs[i].name === n) return songs[i];
      return null;
    }).filter(Boolean);
    if (recs.length < 2) return [{ type: 'answer', text: '无法对比这两首歌曲。' }];
    var a = recs[0], b = recs[1];
    var diffs = [];
    function addDiff(label, x, y) {
      if (x == null || y == null || x === '' || y === '' || isNaN(x) || isNaN(y)) return;
      if (Number(x) === Number(y)) return;
      var base = Math.min(Math.abs(Number(x)), Math.abs(Number(y)));
      if (base <= 0) return;
      var pct = Math.round(Math.abs(Number(x) - Number(y)) / base * 100);
      var hi = Number(x) > Number(y) ? a : b;
      var lo = Number(x) > Number(y) ? b : a;
      diffs.push(label + '：《' + hi.name + '》高于《' + lo.name + '》' + pct + '%（' + fmt(x) + ' vs ' + fmt(y) + '）');
    }
    addDiff('近30日均值', a.mean30, b.mean30);
    addDiff('历史峰值', a.peak, b.peak);
    addDiff('最新指数', a.latest, b.latest);
    addDiff('综合得分', a.score, b.score);
    addDiff('最长连涨', a.streak, b.streak);
    var summary = diffs.length ? diffs.slice(0, 4).join('；') + '。' : '各项核心指标接近。';
    return [
      { type: 'answer', text: '《' + a.name + '》 vs 《' + b.name + '》：' + summary },
      { type: 'list', title: '档案并排对比', items: recs },
      jumpBlock('trendChart', '全景趋势')
    ];
  }
  function compareBlocks() {
    var ap = D.weekend_premium || {};
    var ww = D.weekend_workday || [];
    var lines = [];
    if (ap.album !== undefined && ap.ost !== undefined) lines.push('专辑类周末溢价 ' + ap.album + '，OST/单曲 ' + ap.ost + '，前者高 ' + Math.round((ap.album - ap.ost) * 100) / 100 + '。');
    if (ww.length >= 2) lines.push('周末 vs 工作日平均指数：' + fmt(ww[0]) + ' vs ' + fmt(ww[1]) + '。');
    if (!lines.length) return [{ type: 'answer', text: '暂无可对比的数据。' }];
    return [
      { type: 'answer', text: lines.join(' ') },
      jumpBlock('albumPremiumChart', '时间偏好洞察图')
    ];
  }
  function recentBlocks() {
    var r7 = D.recent_7days || [];
    var lines = [];
    if (r7.length) {
      var vals = r7.map(function (x) { return typeof x === 'object' && x !== null ? x.value : x; }).filter(function (v) { return v !== null && v !== undefined; });
      if (vals.length) lines.push('最近7日全站平均指数：' + vals.map(fmt).join('、') + '。');
    }
    if (D.daily_new_records !== undefined) lines.push('较昨日新增追踪歌曲 ' + D.daily_new_records + ' 首。');
    if (D.batch_count) lines.push('数据覆盖 ' + D.batch_count + ' 个监测批次（' + (D.date_range || '') + '）。');
    return [
      { type: 'answer', text: lines.length ? lines.join(' ') : '暂无近期数据。' },
      jumpBlock('microTrendChart', '最近7日微趋势')
    ];
  }
  function browseBlocks() {
    var arr = songs.filter(function (s) { return (s.mean30 || 0) > 0; })
      .sort(function (a, b) { return (b.mean30 || 0) - (a.mean30 || 0); }).slice(0, 6);
    var blocks = [
      { type: 'answer', text: '没有匹配到具体问题或歌名。这里是最新「近30日均值」热门作品，也可以试试下面这些问法：' }
    ];
    if (arr.length) blocks.push({ type: 'list', title: '热门作品 Top' + arr.length, items: arr });
    blocks.push({ type: 'plain', text: '💡 试试问：「涨幅最大的歌」 · 「周末听什么」 · 「巡演影响」 · 「最近异常」 · 「经典沉淀期」 · 「某首歌名」' });
    return blocks;
  }
  function nameToRec(n) {
    for (var i = 0; i < songs.length; i++) if (songs[i].name === n) return songs[i];
    return null;
  }

  /* ---------------- ⑤ 图表联动 ---------------- */
  function jumpTo(anchor) {
    var el = document.getElementById(anchor);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    el.classList.remove('sr-flash');
    void el.offsetWidth;
    el.classList.add('sr-flash');
    setTimeout(function () { el.classList.remove('sr-flash'); }, 1800);
  }

  /* ---------------- 跨站关系渲染（人-歌-城三位一体） ----------------
   * 三类分组：
   *   【歌曲档案】现有 dashboard 结果（render 内）
   *   【现场记录】entity_index 的 live 关系（城市/场馆/日期，live_url 为 null 时纯文本）
   *   【酒馆提及】entity_index 的 tavern 关系（EP 页锚点链接）
   * 城市名命中时：演出历史（cities.json shows）+ 该城相关歌曲的酒馆提及
   */
  function normStr(s) {
    return String(s == null ? '' : s).replace(/[《》「」]/g, '').replace(/\s+/g, '').toLowerCase();
  }

  function findEntityByName(q) {
    if (!entitySongs) return null;
    var nq = normStr(q);
    if (!nq) return null;
    var keys = Object.keys(entitySongs);
    for (var i = 0; i < keys.length; i++) {
      if (normStr(keys[i]) === nq) return { name: keys[i], data: entitySongs[keys[i]] };
    }
    for (var j = 0; j < keys.length; j++) {
      if (nq.length >= 2 && normStr(keys[j]).indexOf(nq) >= 0) {
        return { name: keys[j], data: entitySongs[keys[j]] };
      }
    }
    return null;
  }

  function findCity(q) {
    if (!citiesData) return null;
    var nq = normStr(q);
    if (!nq) return null;
    var names = Object.keys(citiesData);
    for (var i = 0; i < names.length; i++) {
      if (normStr(names[i]) === nq) return names[i];
      if (normStr(names[i]).indexOf(nq) >= 0) return names[i];
    }
    return null;
  }

  // 城市演出历史 + 该城歌曲的酒馆提及（来自 cities.json + entity_index，全部动态）
  function cityBlocks(cityName) {
    var node = citiesData[cityName];
    var blocks = [];
    var shows = (node && node.shows) || [];
    if (!shows.length) return [];
    var rows = shows.map(function (s) {
      var venue = s.venue || '场馆待补';
      var venueHtml = s.live_url ? '<a href="../' + s.live_url + '" target="_blank" rel="noopener">' + esc(venue) + '</a>' : esc(venue);
      return '<div class="sr-row"><span class="sr-rank">' + esc(s.date) + '</span>' +
        '<span class="sr-song">' + esc(s.tour) + '「' + esc(s.theme) + '」' + '</span>' +
        '<span class="sr-val">' + venueHtml + '</span>' +
        (s.has_data ? '<span class="sr-tag">有数据</span>' : '') +
        (s.cancelled ? '<span class="sr-tag">未举办</span>' : '') + '</div>';
    });
    blocks.push({ type: 'head', title: '【城市演出】' + cityName + ' · ' + shows.length + ' 场' });
    blocks.push({ type: 'rows', items: rows });

    // 该城唱过的歌 → 酒馆提及（entity_index 反查）
    if (entitySongs) {
      var cityMentions = [];
      Object.keys(entitySongs).forEach(function (songName) {
        var en = entitySongs[songName];
        var playedHere = (en.live || []).some(function (lv) { return lv.city === cityName; });
        if (!playedHere) return;
        var taverns = (en.tavern || []).filter(function (t) { return t !== '歌词'; });
        if (!taverns.length) return;
        cityMentions.push({ song: songName, eps: taverns });
      });
      if (cityMentions.length) {
        var mRows = cityMentions.slice(0, 6).map(function (m) {
          var epLinks = m.eps.slice(0, 3).map(function (ep) {
            return '<a href="../tavern/ep/' + encodeURIComponent(ep) + '.html" target="_blank" rel="noopener">' + esc(ep) + '</a>';
          }).join('、');
          return '<div class="sr-row"><span class="sr-song">《' + esc(m.song) + '》</span>' +
            '<span class="sr-val">' + epLinks + '</span></div>';
        });
        blocks.push({ type: 'head', title: '【酒馆提及】' + cityName + ' 相关歌曲的深夜小酒馆期次' });
        blocks.push({ type: 'rows', items: mRows });
      }
    }
    return blocks;
  }

  // 歌曲的跨站关系（现场记录 + 酒馆提及）
  function songRelationBlocks(songName) {
    if (!entitySongs) return [];
    var en = entitySongs[songName];
    if (!en) return [];
    var blocks = [];
    var live = en.live || [];
    var tavern = (en.tavern || []).filter(function (t) { return t !== '歌词'; });
    if (live.length) {
      var liveRows = live.slice(0, 8).map(function (lv) {
        var date = esc(lv.date || '');
        var city = esc(lv.city || '');
        var venue = esc(lv.venue || '场馆待补');
        var tour = esc(lv.tour || '');
        var link = lv.url ? '<a href="../' + esc(lv.url) + '" target="_blank" rel="noopener">' + venue + ' ↗</a>' : venue;
        return '<div class="sr-row"><span class="sr-rank">' + date + '</span>' +
          '<span class="sr-song">' + city + ' · ' + link + '</span>' +
          '<span class="sr-tag">' + tour + '</span></div>';
      });
      blocks.push({ type: 'head', title: '【现场记录】《' + esc(songName) + '》' + live.length + ' 场巡演' });
      blocks.push({ type: 'rows', items: liveRows });
    }
    if (tavern.length) {
      var tRows = tavern.slice(0, 6).map(function (ep) {
        var epName = esc(String(ep).replace(/_/g, ' '));
        return '<div class="sr-row"><span class="sr-song">小酒馆 ' + epName + '</span>' +
          '<span class="sr-val"><a href="../tavern/ep/' + encodeURIComponent(ep) + '.html" target="_blank" rel="noopener">查看逐字稿 ↗</a></span></div>';
      });
      blocks.push({ type: 'head', title: '【酒馆提及】《' + esc(songName) + '》· 深夜小酒馆 ' + tavern.length + ' 期' });
      blocks.push({ type: 'rows', items: tRows });
    }
    return blocks;
  }

  /* ---------------- 渲染 ---------------- */
  var KNOWN = { uid: 1, name: 1, attr: 1, release: 1, latest: 1, mean30: 1, peak: 1, points: 1, lifecycle: 1, score: 1, streak: 1, best_rank: 1, active_days: 1, profile: 1, _src: 1 };
  function extraFields(r) {
    // 动态字段透传：未来 Python 侧新增元数据（如「来源:电台」）会自动展示
    var o = r._src || r;
    var parts = [];
    Object.keys(o).forEach(function (k) {
      if (KNOWN[k] || o[k] === '' || o[k] === null || o[k] === undefined) return;
      var v = o[k];
      if (typeof v === 'object') v = JSON.stringify(v);
      parts.push('<span class="sc-extra-item"><b>' + esc(k) + '</b> ' + esc(v) + '</span>');
    });
    return parts.join('');
  }
  function profileHTML(r) {
    // 「数据档案」区：Python 侧生成的 profile 键值对（中文标签，已格式化），直接展示
    var p = (r.profile || []).map(function (x) {
      return '<span class="sc-extra-item"><b>' + esc(x.k) + '</b> ' + esc(x.v) + '</span>';
    }).join('');
    return p;
  }
  function songCardHTML(r) {
    return '<div class="song-card" data-uid="' + esc(r.uid) + '" data-name="' + esc(r.name) + '">' +
      '<div class="sc-top"><span class="sc-name">' + esc(r.name) + '</span>' +
      (r.attr ? '<span class="sc-attr">' + esc(r.attr) + '</span>' : '') +
      (r.lifecycle ? '<span class="sc-life">' + esc(r.lifecycle) + '</span>' : '') + '</div>' +
      '<div class="sc-metrics">' +
      '<div class="sc-m"><span>最新</span><b>' + fmt(r.latest) + '</b></div>' +
      '<div class="sc-m"><span>近30日均值</span><b>' + fmt(r.mean30) + '</b></div>' +
      '<div class="sc-m"><span>历史峰值</span><b>' + fmt(r.peak) + '</b></div>' +
      '<div class="sc-m"><span>综合得分</span><b>' + fmt(r.score) + '</b></div>' +
      '</div>' +
      '<div class="sc-extra">' +
      (r.streak ? '<span class="sc-extra-item"><b>最长连涨</b> ' + esc(r.streak) + ' 次</span>' : '') +
      (r.release && r.release !== '-' ? '<span class="sc-extra-item"><b>发行</b> ' + esc(r.release) + '</span>' : '') +
      profileHTML(r) +
      extraFields(r) +
      '</div>' +
      '<div class="sc-chart" style="height:56px"></div>' +
      '<div class="sc-foot">' +
      '<button type="button" class="sc-open" data-anchor="trendChart">趋势图表 ↗</button>' +
      '</div></div>';
  }

  function render(blocks) {
    var out = document.getElementById('searchResults');
    if (!out) return;
    out.innerHTML = '';
    if (!blocks || !blocks.length) {
      out.innerHTML = '<div class="sr-empty">没有找到相关内容，试试上面的推荐问题。</div>';
      return;
    }
    blocks.forEach(function (b) {
      var el = document.createElement('div');
      el.className = 'sr-block';
      if (b.type === 'answer') el.innerHTML = '<div class="sr-answer">' + b.text + '</div>';
      else if (b.type === 'head') el.innerHTML = '<div class="sr-head">' + b.title + '</div>';
      else if (b.type === 'plain') el.innerHTML = '<div class="sr-answer sr-hint">' + b.text + '</div>';
      else if (b.type === 'list') {
        el.innerHTML = '<div class="sr-head">' + b.title + '</div><div class="sr-grid">' +
          b.items.map(songCardHTML).join('') + '</div>';
      } else if (b.type === 'rows') {
        el.innerHTML = '<div class="sr-rows">' + b.items.join('') + '</div>';
      } else if (b.type === 'insights') {
        el.innerHTML = '<div class="sr-head">💡 相关洞察（实时从数据计算）</div>' +
          b.items.map(function (it) {
            return '<div class="sr-insight">' + it.text + (it.anchor ? ' <button type="button" class="sr-insight-jump" data-anchor="' + it.anchor + '">查看↗</button>' : '') + '</div>';
          }).join('');
      } else if (b.type === 'jump') {
        el.innerHTML = '<button type="button" class="sr-jump" data-anchor="' + b.anchor + '">跳到相关图表：' + esc(b.label) + ' ↗</button>';
      }
      out.appendChild(el);
    });
    out.querySelectorAll('[data-anchor]').forEach(function (btn) {
      btn.addEventListener('click', function () { jumpTo(btn.getAttribute('data-anchor')); });
    });
    // 迷你趋势图
    out.querySelectorAll('.song-card').forEach(function (card) {
      var uid = card.getAttribute('data-uid');
      var rec = null;
      for (var i = 0; i < songs.length; i++) if (songs[i].uid === uid) { rec = songs[i]; break; }
      if (rec && rec.points && rec.points.length >= 2) drawSpark(card.querySelector('.sc-chart'), rec.points);
      else if (rec && (rec.mean30 || rec.latest)) {
        card.querySelector('.sc-chart').innerHTML = '<div class="sc-chart-text">近30日均值 ' + fmt(rec.mean30) + ' · 最新 ' + fmt(rec.latest) + '</div>';
      }
    });
  }

  /* ---------------- 迷你趋势图（echarts 就绪后绘制，缺失降级文本） ---------------- */
  function drawSpark(container, pts) {
    var draw = function () {
      if (!container || !container.isConnected) return;
      var labels = pts.map(function (p) { return p[0]; });
      var values = pts.map(function (p) { return p[1]; });
      container.innerHTML = '';
      var chart = window.echarts.init(container);
      chart.setOption({
        animation: false,
        grid: { left: 2, right: 2, top: 6, bottom: 2 },
        xAxis: { type: 'category', show: false, data: labels },
        yAxis: { type: 'value', show: false, scale: true },
        series: [{
          type: 'line', data: values, showSymbol: false, smooth: true,
          lineStyle: { color: '#00d2ff', width: 1.4 },
          areaStyle: { color: 'rgba(0,210,255,0.10)' },
          emphasis: { disabled: true }
        }]
      });
    };
    if (window.echarts) draw();
    else pendingSpark.push(draw);
  }
  function flushPendingSpark() {
    var q = pendingSpark;
    pendingSpark = [];
    q.forEach(function (fn) { fn(); });
  }

  /* ---------------- 搜索入口 ---------------- */
  function runSearch(q) {
    if (!D) {
      render([{ type: 'answer', text: '数据未就绪，请刷新页面。' }]);
      return;
    }
    var intent = parseIntent(q);
    var blocks = answerBlocks(q, intent);
    render(blocks);
    // 跨站关系（人-歌-城）：就绪后立即追加渲染
    whenExtras(function () {
      var extra = [];
      var cityName = findCity(q);
      if (cityName) {
        extra = extra.concat(cityBlocks(cityName));
      } else if (intent.type === 'song' || intent.type === 'compare_songs') {
        var names = intent.type === 'compare_songs' ? intent.songs : [intent.song];
        names.forEach(function (nm) {
          var hit = findEntityByName(nm);
          if (hit) extra = extra.concat(songRelationBlocks(hit.name));
        });
      } else {
        var hit2 = findEntityByName(q);
        if (hit2) extra = extra.concat(songRelationBlocks(hit2.name));
      }
      if (extra.length) {
        var all = answerBlocks(q, parseIntent(q)).concat(extra);
        render(all);
      }
    });
  }
  function answerBlocks(q, intent) {
    var blocks = [];
    switch (intent.type) {
      case 'song': blocks = songBlocks(intent.song); break;
      case 'top_trend': blocks = topTrendBlocks(); break;
      case 'top_index': blocks = topIndexBlocks(q); break;
      case 'weekend': blocks = weekendBlocks(); break;
      case 'tour': blocks = tourBlocks(); break;
      case 'release': blocks = releaseBlocks(); break;
      case 'anomaly': blocks = anomalyBlocks(); break;
      case 'lifecycle': blocks = lifecycleBlocks(q); break;
      case 'compare_songs': blocks = compareSongsBlocks(intent.songs); break;
      case 'compare': blocks = compareBlocks(); break;
      case 'recent': blocks = recentBlocks(); break;
      default: blocks = browseBlocks();
    }
    var matched = matchInsights(q);
    if (matched.length && intent.type !== 'song') blocks.push({ type: 'insights', items: matched });
    return blocks;
  }

  /* 获取 dashboardData：兼容 window 属性与全局词法 const 声明（const/let 不挂 window） */
  function getData() {
    if (typeof window !== 'undefined' && window.dashboardData) return window.dashboardData;
    if (typeof dashboardData !== 'undefined') return dashboardData;
    return null;
  }

  function init() {
    D = getData();
    if (!D) {
      var box = document.getElementById('searchResults');
      if (box) box.innerHTML = '<div class="sr-empty">数据未就绪</div>';
      return;
    }
    buildSongs();
    buildInsights();
    loadExtras(); // 预加载跨站关系（entity_index + cities）

    var input = document.getElementById('searchInput');
    var btn = document.getElementById('searchBtn');
    if (input) {
      input.addEventListener('keydown', function (e) { if (e.key === 'Enter') runSearch(input.value); });
    }
    if (btn) btn.addEventListener('click', function () { runSearch(input ? input.value : ''); });
    document.querySelectorAll('.chip').forEach(function (c) {
      c.addEventListener('click', function () {
        var q = c.getAttribute('data-q') || '';
        if (input) input.value = q;
        runSearch(q);
      });
    });
    // 主站跳转：?q= 参数自动执行
    var m = /[?&]q=([^&]+)/.exec(window.location.search || '');
    if (m) {
      var q = decodeURIComponent(m[1].replace(/\+/g, ' '));
      if (q) {
        if (input) input.value = q;
        runSearch(q);
        input.focus();
      }
    }
    // echarts 就绪后补绘
    document.addEventListener('echarts-ready', flushPendingSpark);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();

  // 调试/测试导出：window.DataSpeak.search(q) 可直接调用
  if (typeof window !== 'undefined') {
    window.DataSpeak = {
      search: function (q) {
        if (!D) D = getData() || {};
        buildSongs();
        buildInsights();
        return answerBlocks(String(q || ''), parseIntent(String(q || '')));
      },
      songCount: function () { return songs.length; },
      indexReady: function () { return !!(D && D.song_index && D.song_index.length); }
    };
  }
})();
