/**
 * 王晰 AI 问答浮动助手（qa_engine.js v2 · 全站通用）
 * 纯静态、零依赖：fetch data/qa_bank.json，右下角浮动按钮 → 弹出问答面板，任何页面可用。
 * 设计：离线预生成问答 + 前端语义检索（零后端、零 key、零成本），随提问增量扩充。
 * 用法：页面里加 <script src="/qa_engine.js"></script> 即可（自动注入浮动助手 UI）。
 */
(function () {
  var INDEX_URL = 'qa_engine.js'.indexOf('/') >= 0
    ? 'data/qa_bank.json'
    : 'data/qa_bank.json';
  // 兼容：无论脚本在哪个层级被引用，都用站点根的 data/qa_bank.json
  INDEX_URL = (document.querySelector('base') && document.querySelector('base').href)
    ? new URL('data/qa_bank.json', document.querySelector('base').href).href
    : 'data/qa_bank.json';
  // 若页面已在子目录（如 /live/、/tavern/），用绝对路径更稳
  if (window.location.pathname.split('/').length > 2) {
    INDEX_URL = 'https://wx409.github.io/data/qa_bank.json';
  }

  var bank = null;
  var bankState = 'pending';
  var widgetInjected = false;

  // ===== 实时数据层（dashboard_lite.json，随大屏 rebuild 自动更新）=====
  var dash = null;
  var dashState = 'pending';
  var DASH_URL = (document.querySelector('base') && document.querySelector('base').href)
    ? new URL('dashboard/dashboard_lite.json', document.querySelector('base').href).href
    : 'dashboard/dashboard_lite.json';
  if (window.location.pathname.split('/').length > 2) {
    DASH_URL = 'https://wx409.github.io/dashboard/dashboard_lite.json';
  }
  function loadDashboard(cb) {
    if (dashState === 'ready') { cb && cb(); return; }
    if (dashState === 'loading') return;
    dashState = 'loading';
    fetch(DASH_URL, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { dash = j; dashState = 'ready'; cb && cb(); })
      .catch(function () { dashState = 'failed'; cb && cb(); });
  }
  function dashFoot(extra) {
    // 数据口径脚注：时间戳 + 完整度（动态，不写死）
    var ts = dash && dash.last_update ? dash.last_update : (dash && dash.timestamp ? dash.timestamp : '—');
    var cr = dash && dash.complete_rate != null ? ' · 数据完整度 ' + dash.complete_rate + '%' : '';
    return '<div class="qaw-src">📊 ' + esc(ts) + ' 数据快照' + cr + (extra || '') + '</div>';
  }
  function dashCard(title, body) {
    return '<div class="qaw-card"><div class="qaw-q">' + title + '</div><div class="qaw-a">' + body + '</div>' + dashFoot() + '</div>';
  }
  // 实时数据回答器：返回 HTML 或 null（"为什么"类归因问题留给预生成问答库）
  function dashboardAnswer(q) {
    if (!dash) return null;
    var nq = norm(q);
    if (/为什么|为何|原因|因为|怎么会|凭什么/.test(nq)) return null;

    // 1) 异常监测
    if (/(异常|突增|骤降|飙升|异动|波动|反常|猛涨|大跌)/.test(nq) && (dash.daily_anomalies || []).length) {
      var items = dash.daily_anomalies.map(function (a) {
        return '<div>· ' + esc(a.song) + '（' + esc(a.type) + '，' + esc(a.desc) + '）</div>';
      }).join('');
      var lat = dash.latest_anomaly;
      var head = lat ? '最新：' + esc(lat.song) + '（' + esc(lat.desc) + '）' : '';
      return dashCard('🔍 近期指数异常（' + (dash.daily_anomalies.length) + ' 条）', (head ? '<div style="margin-bottom:4px">' + head + '</div>' : '') + items);
    }

    // 2) 完整度 / 数据概况
    if (/(完整度|覆盖率|数据完整|采集|数据规模|总记录|一共.*条|多少条|多少首|追踪)/.test(nq)) {
      var rows = [
        ['数据周期', dash.date_range],
        ['累计记录', (dash.total || 0).toLocaleString() + ' 条'],
        ['数据完整度', (dash.complete_rate != null ? dash.complete_rate : 0) + '%'],
        ['追踪歌曲', dash.total_songs + ' 首（活跃 ' + dash.active_songs + ' 首，' + (dash.active_rate != null ? dash.active_rate : 0) + '%）'],
        ['监测批次', dash.batch_count + ' 批']
      ].map(function (r) { return '<div>· ' + esc(r[0]) + '：' + esc(r[1]) + '</div>'; }).join('');
      return dashCard('📊 数据概况', rows);
    }

    // 3) 演出效应（带动/辐射）
    if (/(效应|带动|辐射|哪场|演出效果|演出.*最|巡演.*涨|哪场演出)/.test(nq) && (dash.tour_song_effects || []).length) {
      var fx = dash.tour_song_effects.slice().sort(function (a, b) {
        return (b.total_uplift == null ? -999 : b.total_uplift) - (a.total_uplift == null ? -999 : a.total_uplift);
      }).slice(0, 5);
      var fxHtml = fx.map(function (f) {
        var top = (f.top_songs || []).slice(0, 3).map(function (s) { return '《' + s.name + '》+' + s.uplift + '%'; }).join('、');
        return '<div>· ' + esc(f.scene) + '（' + esc(f.city || '') + '，' + esc(f.content_type || '') + '）全站效应 <b>' + (f.total_uplift != null ? f.total_uplift + '%' : '—') + '</b> · ' + esc(f.pattern || '') + (top ? '<br/><span style="color:#888">　带动：' + top + '</span>' : '') + '</div>';
      }).join('');
      return dashCard('🎤 演出效应 Top' + fx.length + '（全站指数相对基线变化）', fxHtml);
    }

    // 4) 周末 / 工作日
    if (/(周末|工作日|通勤)/.test(nq) && dash.weekend_workday && dash.weekend_workday.length === 2) {
      var wk = dash.weekend_workday[0], wd = dash.weekend_workday[1];
      var ratio = wd > 0 ? (wk / wd) : null;
      var kind = ratio == null ? '' : (ratio > 1.05 ? '偏「周末型」' : (ratio < 0.95 ? '偏「通勤/工作日型」' : '周末与工作日接近'));
      return dashCard('🗓️ 周末 vs 工作日收听', '周末均值 <b>' + wk + '</b> · 工作日均值 <b>' + wd + '</b>' + (ratio != null ? '（比值 ' + ratio.toFixed(2) + '，' + kind + '）' : ''));
    }

    // 5) 今日收听份额 / 最近7天（先于榜单，避免"份额"意图被抢）
    if (/(今日|份额|占比|收听榜|最近7天|近7天|七天)/.test(nq) && (dash.daily_listen_trend || []).length) {
      var dl = dash.daily_listen_trend.slice(0, 5).map(function (x) {
        var d = x.trend_pct != null ? ('（' + (x.trend_pct > 0 ? '+' : '') + x.trend_pct + '%）') : '';
        return '<div>· 《' + esc(x.song) + '》 份额 ' + esc(x.share_pct) + '%' + d + '</div>';
      }).join('');
      var r7 = '';
      if ((dash.recent_7days || []).length) {
        r7 = '<div style="margin-top:6px;color:#888">近7日均值：' + dash.recent_7days.map(function (r) { return esc(String(r.date).slice(5)) + ' ' + esc(r.avg_index); }).join(' · ') + '</div>';
      }
      return dashCard('📻 今日收听份额 Top' + dash.daily_listen_trend.length, dl + r7);
    }

    // 6) 榜单（最火/最高/排名）
    if (/(最火|最热|最高|top|榜首|排名|排行|榜单|哪首.*最)/.test(nq) && (dash.top_songs || []).length) {
      var tops = dash.top_songs.slice(0, 8).map(function (s, i) {
        return '<div>· ' + (i + 1) + '. 《' + esc(s.name) + '》 指数 ' + esc(s.trend) + (s.tag ? '（' + esc(s.tag) + '）' : '') + '</div>';
      }).join('');
      return dashCard('🔥 热度榜单（当前 Top' + dash.top_songs.length + '）', tops);
    }

    // 7) 月度叙事 / 走势
    if (/(月|走势|趋势|叙事|大盘|整体)/.test(nq) && (dash.timeline_narrative || []).length && (dash.time_labels || []).length) {
      var labels = dash.time_labels, trend = dash.trend_raw || [];
      var last = labels.slice(-4).map(function (m, i) {
        var idx = labels.length - 4 + i;
        var v = trend[idx];
        var prev = idx > 0 ? trend[idx - 1] : null;
        var d = (prev != null && prev > 0) ? ((v - prev) / prev * 100) : null;
        return '<div>· ' + esc(m) + '：指数 <b>' + (v != null ? v : '—') + '</b>' + (d != null ? '（' + (d >= 0 ? '+' : '') + d.toFixed(1) + '%）' : '') + '</div>';
      }).join('');
      return dashCard('📈 近期走势（最近 4 个月）', last);
    }

    // 8) 近期事件（演出/发行/晚会）
    if (/(演出|发行|晚会|综艺|最近|最新|近期|有什么活动)/.test(nq)) {
      function evBlock(name, arr, cls, max) {
        arr = arr || [];
        if (!arr.length) return '';
        var last3 = arr.slice(-max || 3).map(function (e) {
          return '<div><span class="badge ' + cls + '">' + name + '</span>' + esc(Array.isArray(e) ? (e[1] || e[0]) : e) + '</div>';
        }).join('');
        return last3;
      }
      var b = evBlock('巡演', dash.tour_events, 'b-tour', 3)
        + evBlock('发行', dash.release_events, 'b-release', 3)
        + evBlock('晚会', dash.performance_events, 'b-perf', 3);
      if (!b) return null;
      return dashCard('📅 最近已登记事件', b);
    }

    return null;
  }

  // 同义词折叠：把常见同义表达归一，提升语义匹配
  var SYNONYMS = [
    ['下降', '下滑', '跌落', '下跌', '掉', '跌'],
    ['上涨', '上升', '涨', '升'],
    ['最多', '最常', '经常', '频繁', '次数最多'],
    ['顶点', '峰值', '最高', '最火', '最红', '最好'],
    ['演唱', '唱', '唱过', '演绎', '表演'],
    ['歌曲', '歌', '曲目', '作品', '曲子'],
    ['巡回', '巡演', '演唱会', '个唱'],
    ['制作人', '监制', 'producer'],
    ['词作者', '作词', '写词', '词人'],
    ['曲作者', '作曲', '写曲', '编曲'],
  ];
  function norm(s) {
    var t = String(s || '').toLowerCase().replace(/[，。！？、；：""''《》【】（）()\s\-—·]/g, '');
    SYNONYMS.forEach(function (grp) {
      for (var i = 1; i < grp.length; i++) {
        t = t.split(grp[i]).join(grp[0]);
      }
    });
    return t;
  }
  function bigrams(s) {
    var b = {};
    for (var i = 0; i < s.length - 1; i++) {
      b[s.slice(i, i + 2)] = true;
    }
    return b;
  }

  function scoreItem(item, q) {
    var nq = norm(q);
    var qb = bigrams(nq);
    var score = 0, hit = false;
    // 问题/别名：字级 bigram 重合度
    (item.aliases || []).concat([item.question]).forEach(function (a) {
      var na = norm(a);
      if (na && (nq.indexOf(na) >= 0 || na.indexOf(nq) >= 0)) { score += 50; hit = true; }
      else if (na && nq.length >= 2) {
        var overlap = 0, total = 0;
        var ab = bigrams(na);
        for (var b in qb) { if (ab[b]) overlap++; total++; }
        if (total > 0 && overlap / total >= 0.4) { score += 20 * (overlap / total); hit = true; }
      }
    });
    // 关键词命中（归一后）
    var counted = {};
    (item.keywords || []).forEach(function (k) {
      var nk = norm(k);
      if (nk && nk.length >= 2 && !counted[nk] && nq.indexOf(nk) >= 0) { score += 15; hit = true; counted[nk] = true; }
    });
    if (!hit && item.category && nq.indexOf(norm(item.category)) >= 0) { score += 8; hit = true; }
    return hit ? score : 0;
  }
  function esc(s) {
    return String(s || '').replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function loadBank(cb) {
    if (bankState === 'ready') { cb && cb(); return; }
    if (bankState === 'loading') return;
    bankState = 'loading';
    fetch(INDEX_URL, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { bank = j; bankState = 'ready'; cb && cb(); })
      .catch(function () { bankState = 'failed'; cb && cb(); });
  }

  function answer(q) {
    if (!bank || !bank.items) return [];
    return bank.items.map(function (it) { return { item: it, score: scoreItem(it, q) }; })
      .filter(function (x) { return x.score > 0; })
      .sort(function (a, b) { return b.score - a.score; });
  }

  // ===== 歌曲档案参数化查询：识别歌名 → 实时从 song_index_lite.json 查 =====
  var songIndex = null;
  var songState = 'pending';
  function loadSongIndex(cb) {
    if (songState === 'ready') { cb && cb(); return; }
    if (songState === 'loading') return;
    songState = 'loading';
    var siUrl = INDEX_URL.replace('qa_bank.json', 'song_index_lite.json');
    fetch(siUrl, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { songIndex = j.songs || {}; songMeta = { generated_at: j.generated_at || '' }; songState = 'ready'; cb && cb(); })
      .catch(function () { songState = 'failed'; cb && cb(); });
  }

  // 从问题里识别歌名（最长歌名优先，避免短名误匹配）
  function findSong(q) {
    if (!songIndex) return null;
    var nq = norm(q);
    var best = null, bestLen = 0;
    for (var key in songIndex) {
      var e = songIndex[key];
      var nn = norm(e.name);
      if (nn.length < 2) continue;
      if (nq.indexOf(nn) >= 0 && nn.length > bestLen) {
        best = e; bestLen = nn.length;
      }
    }
    return best;
  }

  // ===== 人名反查：作词人/作曲人/制作人/编曲人 → 作品列表 =====
  var PERSON_ROLES = { lyricist: '作词', composer: '作曲', producer: '制作人', arranger: '编曲', backing: '和声', guitar: '吉他', strings: '弦乐', mixing: '混音', recording: '录音', mastering: '母带', bass: '贝斯', drum: '鼓', supervisor: '监制' };
  var creditsFull = null;
  var cfState = 'pending';
  function loadCreditsFull() {
    if (cfState === 'ready' || cfState === 'loading') return;
    cfState = 'loading';
    var cfUrl = INDEX_URL.replace('qa_bank.json', 'credits_full.json');
    fetch(cfUrl, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { creditsFull = j; cfState = 'ready'; })
      .catch(function () { cfState = 'failed'; });
  }
  var persons = null;
  var personsWithCf = false;
  function buildPersons() {
    if (!songIndex) return;
    var cfReady = (cfState === 'ready');
    if (persons && personsWithCf === cfReady) return; // 缓存命中
    persons = {};
    var seen = {};
    function add(songName, roleKey, val) {
      var rn = PERSON_ROLES[roleKey] || roleKey;
      String(val).split(/[&、,/;；/]/).forEach(function (nm) {
        nm = nm.trim();
        if (nm.length < 2) return;
        var variants = [nm];
        // 去掉 @工作室 后缀再注册一个变体（如 黄竣琮@TYZ → 黄竣琮），保证人名可直接搜
        var at = nm.indexOf('@');
        if (at > 0) variants.push(nm.slice(0, at).trim());
        variants.forEach(function (v) {
          if (v.length < 2) return;
          var kk = v + '|' + songName + '|' + rn;
          if (seen[kk]) return;
          seen[kk] = 1;
          if (!persons[v]) persons[v] = [];
          persons[v].push({ song: songName, role: rn });
        });
      });
    }
    for (var key in songIndex) {
      var e = songIndex[key];
      var cr = e.credits || {};
      for (var role in cr) add(e.name || key, role, cr[role]);
    }
    if (cfReady && creditsFull && creditsFull.songs) {
      for (var sk in creditsFull.songs) {
        var info = creditsFull.songs[sk];
        var cr2 = info.credits || {};
        for (var role2 in cr2) add(sk, role2, cr2[role2]);
      }
    }
    personsWithCf = cfReady;
  }
  // 人名反查：宽松触发——单独人名、人名+任意作品/角色词都能搜到；
  // 仅当问题指向"榜单/演出"等明确意图时跳过（防截胡）
  var PERSON_BLOCK = /最火|最热|最高|排名|排行|榜单|演唱会|巡演|巡回|开唱|唱过|歌单|现场|票房|粉丝|数据|效应|周末/;
  var PERSON_HINT = /写|词|曲|作|编|制|监|和声|混音|弦乐|吉他|贝斯|鼓|录音|母带|作品|参与|的歌|有哪些|谁/;
  function findPerson(q) {
    buildPersons();
    if (!persons) return null;
    var nq = norm(q);
    if (PERSON_BLOCK.test(nq)) return null;
    var best = null, bestLen = 0;
    for (var p in persons) {
      var np = norm(p);
      if (np.length < 2 || np.length <= bestLen) continue;
      if (nq.indexOf(np) >= 0) { best = p; bestLen = np.length; }
    }
    if (!best) {
      // 部分匹配：问题作为子串反查人名（如「炫豆」→「刘炫豆」）；匹配过多人名则放弃避免泛匹配
      var subs = [];
      for (var p2 in persons) {
        var np2 = norm(p2);
        if (np2.length > 2 && np2.length >= nq.length && np2.indexOf(nq) >= 0) subs.push(p2);
      }
      if (subs.length && subs.length <= 3) {
        subs.sort(function (a, b) { return persons[b].length - persons[a].length; }); // 参与作品多的优先
        best = subs[0];
        bestLen = nq.length;
      }
    }
    if (!best) return null;
    // 宽松触发：问题基本就是人名本身（≤ 人名长度+3）或含作品/角色相关词
    if (nq.length <= bestLen + 3 || PERSON_HINT.test(nq)) {
      return { name: best, entries: persons[best] };
    }
    return null;
  }
  // 角色统计：问「谁编曲最多」「编曲人有哪些」→ 返回该角色参与作品 Top 榜
  function roleBoard(q) {
    if (!songIndex) return null;
    var nq = norm(q);
    if (!/(谁|哪些|最多|有哪些|最常)/.test(nq)) return null;
    var roleHit = null;
    for (var rn in PERSON_ROLES) {
      if (nq.indexOf(PERSON_ROLES[rn]) >= 0) { roleHit = PERSON_ROLES[rn]; break; }
    }
    if (!roleHit) return null;
    buildPersons();
    var stats = {};
    for (var p in persons) {
      // 按去 @后缀 的主名合并统计（黄竣琮@TYZ 与 黄竣琮 算同一人）
      var main = p.split('@')[0];
      persons[p].forEach(function (e) {
        if (e.role === roleHit) stats[main] = (stats[main] || 0) + 1;
      });
    }
    var top = Object.keys(stats).sort(function (a, b) { return stats[b] - stats[a]; }).slice(0, 8);
    if (!top.length) return null;
    var lines = top.map(function (p, i) {
      return '<div>· ' + (i + 1) + '. ' + esc(p) + '（' + stats[p] + ' 首' + roleHit + '）</div>';
    }).join('');
    return '<div class="qaw-card"><div class="qaw-q">🎼 ' + esc(roleHit) + ' Top 榜</div><div class="qaw-a">' + lines + '</div>' +
      '<div class="qaw-src">📚 数据：data/song_index_lite.json + credits_full.json（动态统计）</div></div>';
  }
  function personCard(p) {
    var all = p.entries.map(function (e) {
      return '<div>· 《' + esc(e.song) + '》' + esc(e.role) + '</div>';
    }).join('');
    var head = '<div class="qaw-q">📝 ' + esc(p.name) + ' 参与的作品（' + p.entries.length + ' 首）</div>';
    if (p.entries.length <= 8) {
      return '<div class="qaw-card">' + head + '<div class="qaw-a">' + all + '</div></div>';
    }
    // 超过 8 首：前 8 直接显示，其余折叠（点击展开）
    var first = p.entries.slice(0, 8).map(function (e) {
      return '<div>· 《' + esc(e.song) + '》' + esc(e.role) + '</div>';
    }).join('');
    var rest = p.entries.slice(8).map(function (e) {
      return '<div>· 《' + esc(e.song) + '》' + esc(e.role) + '</div>';
    }).join('');
    return '<div class="qaw-card">' + head + '<div class="qaw-a">' + first +
      '<details><summary style="cursor:pointer;color:#a31832;font-size:12px;margin-top:6px">展开其余 ' + (p.entries.length - 8) + ' 首（点击）</summary>' +
      '<div style="margin-top:6px">' + rest + '</div></details></div></div>';
  }

  function songCard(e) {
    var lines = [];
    lines.push('<div class="qaw-card">');
    lines.push('<div class="qaw-q">《' + esc(e.name) + '》</div>');
    var cr = e.credits || {};
    var roleMap = { lyricist: '作词', composer: '作曲', producer: '制作人', arranger: '编曲', backing: '和声', mixing: '混音', guitar: '吉他', strings: '弦乐' };
    var crLines = [];
    for (var k in roleMap) { if (cr[k]) crLines.push(roleMap[k] + '：' + esc(cr[k])); }
    if (crLines.length) lines.push('<div class="qaw-a">' + crLines.join('<br>') + '</div>');
    else lines.push('<div class="qaw-a">（翻唱/资料歌，无词曲制作信息）</div>');
    var meta = [];
    if (e.release && e.release !== '-') meta.push('发行 ' + esc(e.release));
    if (e.attr) meta.push(esc(e.attr));
    if (e.show_count) meta.push('演唱 ' + e.show_count + ' 次');
    if (e.cities && e.cities.length) {
      meta.push('演出城市：' + e.cities.slice(0, 12).join('、') + (e.cities.length > 12 ? ' 等' + e.cities.length + '城' : ''));
    }
    if (meta.length) lines.push('<div class="qaw-src">' + esc(meta.join(' · ')) + '</div>');
    lines.push('</div>');
    return lines.join('');
  }

  // ===== 作品属性分布（实时统计，排除小酒馆音频/趋势脏标签；原创/翻唱诚实披露）=====
  var songMeta = null;
  function attrAnswer(q) {
    if (!songIndex) return null;
    var nq = norm(q);
    if (!/(原创|翻唱|\bost\b|属性分布|作品类型|什么类型|专辑多|单曲多|作品.*分布)/.test(nq)) return null;
    var cnt = {};
    var tavern = 0;
    for (var key in songIndex) {
      var a = String(songIndex[key].attr || '').trim();
      if (a === '小酒馆音频') { tavern++; continue; }
      if (a === '飙升' || a === '上涨' || a === '下降') a = ''; // 趋势标签混入的脏值，剔除
      if (!a) a = '未标注（多为翻唱/现场曲）';
      cnt[a] = (cnt[a] || 0) + 1;
    }
    var total = 0;
    var keys = Object.keys(cnt).sort(function (x, y) { return cnt[y] - cnt[x]; });
    keys.forEach(function (k) { total += cnt[k]; });
    var lines = keys.map(function (a) { return '<div>· ' + esc(a) + '：' + cnt[a] + ' 首</div>'; }).join('');
    var ts = songMeta && songMeta.generated_at ? songMeta.generated_at : '';
    return '<div class="qaw-card"><div class="qaw-q">🎵 王晰作品属性分布（' + total + ' 首音乐作品，实时统计）</div><div class="qaw-a">' + lines +
      (tavern ? '<div style="margin-top:6px;color:#888">· 另有小酒馆电台音频 ' + tavern + ' 期（非音乐作品，不计入）</div>' : '') +
      '<div style="margin-top:6px;color:#a05a2c">诚实说明：档案未标注「原创/翻唱」字段，无法直接统计两者比例；单曲的词曲作者可查「《歌名》的词曲作者」。</div></div>' +
      '<div class="qaw-src">📚 数据：data/song_index_lite.json' + (ts ? ' · ' + esc(ts) : '') + '</div></div>';
  }

  // ===== 巡演歌单参数化查询：识别巡次/城市 → 实时查 setlists.json =====
  var setlistsData = null;
  var setlistsState = 'pending';  function loadSetlists(cb) {
    if (setlistsState === 'ready') { cb && cb(); return; }
    if (setlistsState === 'loading') return;
    setlistsState = 'loading';
    var slUrl = INDEX_URL.replace('qa_bank.json', 'setlists.json');
    fetch(slUrl, { cache: 'no-store' })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) { setlistsData = j.setlists || {}; setlistsState = 'ready'; cb && cb(); })
      .catch(function () { setlistsState = 'failed'; cb && cb(); });
  }

  // 识别巡次（一巡/二巡/.../六巡）或城市名，可组合（如"二巡广州"）
  function findTourScope(q) {
    if (!setlistsData) return null;
    var nq = norm(q);
    var scope = null;
    // 巡次
    var tourNum = nq.match(/([一二三四五六])巡/);
    if (tourNum) {
      scope = { type: 'tour', key: tourNum[1] + '巡' };
    }
    // 城市：从所有场的 city 里找（与巡次可并存，过滤更精确）
    var cityList = {};
    for (var dt in setlistsData) {
      var c = setlistsData[dt].city;
      if (c) cityList[norm(c)] = c;
    }
    var cityHit = null;
    for (var nk in cityList) {
      if (nk && nk.length >= 2 && nq.indexOf(nk) >= 0) {
        cityHit = cityList[nk];
        break;
      }
    }
    if (scope && cityHit) scope.city = cityHit;
    else if (!scope && cityHit) scope = { type: 'city', key: cityHit };
    return scope;
  }

  function setlistCardItems(entries) {
    // entries: [{date, city, venue, tour, songs}]
    var html = '';
    entries.forEach(function (e) {
      var songs = (e.songs || []).map(function (s) { return s.title; }).join('、');
      html += '<div class="qaw-card">'
        + '<div class="qaw-q">' + esc(e.date) + ' · ' + esc(e.city) + (e.venue ? ' · ' + esc(e.venue) : '') + '（' + esc(e.tour) + '）</div>'
        + '<div class="qaw-a">' + esc(songs) + '</div>'
        + '</div>';
    });
    return html;
  }

  function renderSetlist(scope) {
    if (!setlistsData) return '';
    var entries = [];
    if (scope.type === 'tour') {
      for (var dt in setlistsData) {
        if (setlistsData[dt].tour === scope.key) {
          if (!scope.city || setlistsData[dt].city === scope.city) {
            entries.push(setlistsData[dt]);
          }
        }
      }
    } else if (scope.type === 'city') {
      for (var dt2 in setlistsData) {
        if (setlistsData[dt2].city === scope.key) {
          entries.push(setlistsData[dt2]);
        }
      }
    }
    entries.sort(function (a, b) { return a.date < b.date ? -1 : 1; });
    if (!entries.length) return '';
    var title = scope.type === 'tour'
      ? '「' + scope.key + '」' + (scope.city ? '·' + esc(scope.city) : '') + ' 共 ' + entries.length + ' 场'
      : '「' + scope.key + '」共 ' + entries.length + ' 场演出';
    return '<div class="qaw-q">' + esc(title) + ' 的歌单：</div>' + setlistCardItems(entries.slice(0, 6))
      + (entries.length > 6 ? '<div class="qaw-src">（仅显示前 6 场，共 ' + entries.length + ' 场）</div>' : '');
  }

  function render(list) {
    var result = document.getElementById('qaWidgetResult');
    var all = document.getElementById('qaWidgetAll');
    if (!result) return;
    if (!list.length) {
      result.innerHTML = '<div class="qaw-empty">暂未找到相关问题。这个问答库会随提问持续扩充——你可以先问下方已收录的问题。</div>';
    } else {
      var top = list[0].item;
      var html = '<div class="qaw-card">'
        + '<div class="qaw-q">' + esc(top.question) + '</div>'
        + '<div class="qaw-a">' + esc(top.answer).replace(/\n/g, '<br>') + '</div>'
        + '<div class="qaw-src">📚 ' + esc((top.sources || []).join('；'))
        + (top.verified ? ' · ✅' + esc(top.verified) : '')
        + (top.confidence ? ' · 置信度 ' + esc(top.confidence) : '') + '</div>'
        + '</div>';
      if (list.length > 1) {
        html += '<div class="qaw-rel">相关：' + list.slice(1, 3).map(function (r) {
          return '<button type="button" class="qaw-relbtn" data-qid="' + r.item.id + '">' + esc(r.item.question) + '</button>';
        }).join('') + '</div>';
      }
      result.innerHTML = html;
    }
    if (all && bank && bank.items) {
      all.innerHTML = '<div class="qaw-allt">更多问题：</div>' + bank.items.map(function (it) {
        return '<button type="button" class="qaw-relbtn" data-qid="' + it.id + '">' + esc(it.question) + '</button>';
      }).join('');
    }
    bind();
  }

  function bind() {
    Array.prototype.forEach.call(document.querySelectorAll('.qaw-relbtn[data-qid]'), function (b) {
      b.onclick = function () {
        var id = b.getAttribute('data-qid');
        var item = (bank.items || []).filter(function (x) { return x.id === id; })[0];
        if (item) render([{ item: item, score: 100 }]);
      };
    });
  }

  function runQuestion() {
    var input = document.getElementById('qaWidgetInput');
    var result = document.getElementById('qaWidgetResult');
    if (!input || !result) return;
    var q = String(input.value || '').trim();
    if (!q) { result.innerHTML = '<div class="qaw-empty">请输入问题：如「在路上的词曲作者」「为什么要下降」「北京唱了什么歌」「一巡」等。</div>'; return; }
    // 优先级：歌名档案 → 人名反查 → 实时数据 → 巡次/城市歌单 → 预设问答
    loadSongIndex(function () {
      loadCreditsFull(); // 后台预载完整班底，让人名反查更全（不阻塞）
      var song = songState === 'ready' ? findSong(q) : null;
      if (song) {
        result.innerHTML = songCard(song);
        return;
      }
      var person = songState === 'ready' ? findPerson(q) : null;
      if (person) {
        result.innerHTML = personCard(person);
        return;
      }
      var roleB = songState === 'ready' ? roleBoard(q) : null;
      if (roleB) {
        result.innerHTML = roleB;
        return;
      }
      var attrH = songState === 'ready' ? attrAnswer(q) : null;
      if (attrH) {
        result.innerHTML = attrH;
        return;
      }
      loadDashboard(function () {
        var dh = dashState === 'ready' ? dashboardAnswer(q) : null;
        if (dh) {
          result.innerHTML = dh;
          return;
        }
        loadSetlists(function () {
          var scope = setlistsState === 'ready' ? findTourScope(q) : null;
          if (scope) {
            var slHtml = renderSetlist(scope);
            if (slHtml) { result.innerHTML = slHtml; return; }
          }
          loadBank(function () {
            if (bankState === 'failed') { result.innerHTML = '<div class="qaw-empty">问答库加载失败，请刷新。</div>'; return; }
            render(answer(q));
          });
        });
      });
    });
  }

  function injectWidget() {
    if (widgetInjected) return;
    widgetInjected = true;

    var css = '.qaw-fab{position:fixed;right:20px;bottom:20px;z-index:9999;width:52px;height:52px;border-radius:50%;background:#c41e3a;color:#fff;border:none;font-size:22px;cursor:pointer;box-shadow:0 4px 16px rgba(196,30,58,.35);display:flex;align-items:center;justify-content:center;transition:transform .15s}'
      + '.qaw-fab:hover{transform:scale(1.08)}'
      + '.qaw-panel{position:fixed;right:20px;bottom:80px;z-index:9999;width:360px;max-width:calc(100vw - 40px);max-height:70vh;background:#fff;border:1px solid #e8d3d7;border-radius:14px;box-shadow:0 8px 30px rgba(0,0,0,.18);display:none;flex-direction:column;overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif}'
      + '.qaw-panel.open{display:flex}'
      + '.qaw-head{background:linear-gradient(135deg,#c41e3a,#a31832);color:#fff;padding:12px 14px;font-size:15px;font-weight:700;display:flex;align-items:center;gap:6px}'
      + '.qaw-close{margin-left:auto;background:none;border:none;color:#fff;font-size:18px;cursor:pointer;line-height:1}'
      + '.qaw-body{padding:12px 14px;overflow-y:auto;flex:1;display:flex;flex-direction:column;gap:10px}'
      + '.qaw-search{display:flex;gap:6px}'
      + '.qaw-search input{flex:1;min-width:0;padding:9px 12px;font-size:14px;border:1px solid #e0c0c6;border-radius:8px;outline:none}'
      + '.qaw-search input:focus{border-color:#c41e3a}'
      + '.qaw-search button{background:#c41e3a;border:none;border-radius:8px;color:#fff;font-weight:600;padding:0 14px;font-size:13px;cursor:pointer;white-space:nowrap}'
      + '.qaw-result{font-size:13px;color:#333}'
      + '.qaw-card{background:#fafafa;border:1px solid #f0e0e3;border-radius:10px;padding:12px 13px}'
      + '.qaw-q{font-weight:700;margin-bottom:6px}'
      + '.qaw-a{line-height:1.8}'
      + '.qaw-src{font-size:11px;color:#999;margin-top:8px;padding-top:6px;border-top:1px dashed #eee}'
      + '.qaw-rel{display:flex;flex-wrap:wrap;gap:5px;align-items:center;margin-top:6px;font-size:12px;color:#888}'
      + '.qaw-relbtn{background:#fff;border:1px solid #e0c0c6;border-radius:14px;padding:3px 10px;font-size:11px;color:#a31832;cursor:pointer}'
      + '.qaw-relbtn:hover{border-color:#c41e3a;background:#fdf0f2}'
      + '.qaw-empty{color:#888;font-size:12px;padding:8px;text-align:center}'
      + '.qaw-allt{font-size:11px;color:#999;margin-bottom:4px}';
    var st = document.createElement('style');
    st.textContent = css;
    document.head.appendChild(st);

    var fab = document.createElement('button');
    fab.className = 'qaw-fab';
    fab.id = 'qaWidgetFab';
    fab.setAttribute('aria-label', 'AI 问答助手');
    fab.textContent = '💬';

    var panel = document.createElement('div');
    panel.className = 'qaw-panel';
    panel.id = 'qaWidgetPanel';
    panel.innerHTML = ''
      + '<div class="qaw-head">🤖 AI 问答助手 <button class="qaw-close" id="qaWidgetClose" aria-label="关闭">×</button></div>'
      + '<div class="qaw-body">'
      + '  <div class="qaw-search"><input type="search" id="qaWidgetInput" placeholder="问：为什么巡演当天指数下降？" autocomplete="off"><button id="qaWidgetBtn">提问</button></div>'
      + '  <div class="qaw-result" id="qaWidgetResult"><div class="qaw-empty">直接输入人名可查作品（如「林夕」「谭伊哲」），或问：歌名档案、巡演歌单（「三巡」「二巡广州」）、实时榜单/异常、"为什么"类问题。</div></div>'
      + '  <div class="qaw-all" id="qaWidgetAll"></div>'
      + '</div>';

    document.body.appendChild(fab);
    document.body.appendChild(panel);

    fab.onclick = function () { panel.classList.toggle('open'); loadBank(function(){ render([]); }); };
    document.getElementById('qaWidgetClose').onclick = function () { panel.classList.remove('open'); };
    document.getElementById('qaWidgetBtn').onclick = runQuestion;
    document.getElementById('qaWidgetInput').onkeydown = function (e) { if (e.key === 'Enter') runQuestion(); };

    loadBank(function () {
      var all = document.getElementById('qaWidgetAll');
      if (all && bank && bank.items) {
        all.innerHTML = '<div class="qaw-allt">已收录问题：</div>' + bank.items.map(function (it) {
          return '<button type="button" class="qaw-relbtn" data-qid="' + it.id + '">' + esc(it.question) + '</button>';
        }).join('');
        bind();
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectWidget);
  } else {
    injectWidget();
  }

  window.QAEngine = { answer: answer };
})();
