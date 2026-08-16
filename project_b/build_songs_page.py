#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成歌曲库页 songs.html —— 433 首歌曲元数据（歌词/专辑/演唱/试听）。

数据源：data/songs_meta.json（build_songs_meta.py 产出）
前端动态渲染 + 搜索过滤；歌曲可页面内试听（PlayerEmbed）。
用法：python project_b/build_songs_page.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "songs_meta.json"
OUT = ROOT / "songs.html"
SITE = "https://wx409.github.io"


def build_page(meta: dict) -> str:
    songs = meta["songs"]
    n_all = len(songs)
    n_lyrics = sum(1 for v in songs.values() if v.get("lyrics"))
    n_album = sum(1 for v in songs.values() if v.get("album"))
    n_shows = sum(1 for v in songs.values() if v.get("show_count"))
    n_play = sum(1 for v in songs.values() if v.get("mid"))
    n_lyr = n_lyrics
    # 可播清单（QQ 接口实测）
    playable_path = ROOT / "data" / "playable_songs.json"
    n_playable = 0
    playable_list = []
    if playable_path.exists():
        try:
            pj = json.loads(playable_path.read_text(encoding="utf-8"))
            playable_list = sorted(pj.get("playable", {}).values(), key=lambda x: x["name"])
            n_playable = len(playable_list)
        except Exception:
            pass

    # 小酒馆音频清单
    n_tavern = 0
    tavern_path = ROOT / "data" / "tavern_audio.json"
    if tavern_path.exists():
        try:
            tj = json.loads(tavern_path.read_text(encoding="utf-8"))
            n_tavern = tj.get("count", 0) or len(tj.get("items", []))
        except Exception:
            pass

    ld = {
        "@context": "https://schema.org",
        "@type": "MusicGroup",
        "name": "王晰 歌曲库",
        "description": f"王晰作品歌曲库：{len(songs)} 首歌曲元数据，含歌词片段、专辑、发行与巡演演唱记录。",
        "url": f"{SITE}/songs.html",
        "member": {"@type": "Person", "name": "王晰"},
    }

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>王晰歌曲库 | {len(songs)}首 · 歌词/专辑/演唱记录</title>
<meta name="description" content="王晰歌曲库：{len(songs)} 首歌曲元数据（{n_lyrics} 首含歌词片段、{n_album} 首有专辑关联、{n_shows} 首有巡演演唱记录），支持搜索与页面内试听。">
<link rel="canonical" href="{SITE}/songs.html">
<meta property="og:title" content="王晰歌曲库 | {len(songs)}首">
<meta property="og:description" content="歌词 / 专辑 / 巡演演唱记录 / 页面内试听。">
<meta property="og:url" content="{SITE}/songs.html">
<meta property="og:type" content="website">
<script type="application/ld+json">
{json.dumps(ld, ensure_ascii=False, indent=2)}
</script>
<style>
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif;line-height:1.8;max-width:960px;margin:0 auto;padding:20px;color:#333;}}
h1{{color:#1a1a1a;border-bottom:3px solid #c41e3a;padding-bottom:10px;}}
.nav{{background:#f8f9fa;padding:15px;border-radius:8px;margin-bottom:20px;}}
.nav a{{color:#c41e3a;margin-right:16px;text-decoration:none;font-weight:500;}}
.search-box{{display:flex;gap:10px;margin:16px 0;}}
.search-box input{{flex:1;padding:10px 14px;font-size:14px;border:1px solid #ccc;border-radius:8px;outline:none;}}
.search-box input:focus{{border-color:#c41e3a;}}
.song-list{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;}}
.song-card{{background:#fafafa;border:1px solid #eee;border-radius:10px;padding:12px 14px;}}
.song-head{{display:flex;align-items:center;justify-content:space-between;gap:8px;}}
.song-name{{font-size:15px;font-weight:700;color:#1a1a1a;}}
.song-meta{{font-size:12px;color:#888;margin-top:4px;}}
.tag{{display:inline-block;font-size:11px;padding:1px 8px;border-radius:10px;margin-left:6px;}}
.tag.album{{background:#fdecea;color:#c41e3a;}}
.tag.lyric{{background:#e8f0fe;color:#1a56c4;}}
.tag.live{{background:#e6f7ee;color:#0a7a5a;}}
.tag.tavern{{background:#f3e8ff;color:#7c3aed;}}
.song-lyrics{{font-size:13px;color:#555;margin-top:8px;border-left:2px solid #ddd;padding-left:10px;}}
.song-credits{{font-size:12px;color:#888;margin-top:6px;}}
.lyr-toggle{{background:none;border:none;color:#c41e3a;font-size:12px;cursor:pointer;padding:0;margin-left:4px;text-decoration:underline;}}
.lyr-full{{display:block;line-height:1.9;margin-top:4px;}}
.pe-btn{{background:#c41e3a;color:#fff;border:none;border-radius:14px;padding:3px 14px;font-size:12px;cursor:pointer;}}
.pe-btn:hover{{filter:brightness(1.1);}}
.pe-btn.pe-playing{{background:#0a7a5a;}}
.no-play{{font-size:11px;color:#bbb;}}
#playerStatus{{display:none;margin:8px 0;padding:8px 12px;background:#f0f4ff;border-left:3px solid #3a7bd5;border-radius:6px;font-size:13px;}}
.empty{{color:#888;text-align:center;padding:30px;}}
.filter-bar{{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 14px;}}
.chip{{background:#f8f9fa;border:1px solid #ddd;border-radius:16px;padding:4px 14px;font-size:13px;cursor:pointer;color:#555;}}
.chip:hover{{border-color:#c41e3a;color:#c41e3a;}}
.chip.on{{background:#c41e3a;color:#fff;border-color:#c41e3a;}}
.playable-top{{background:#e6f7ee;border:1px solid #b7e0cc;border-radius:8px;padding:8px 14px;margin:8px 0;font-size:13px;color:#0a7a5a;}}
/* 左右布局：左侧可播歌单侧栏 */
.layout{{display:flex;gap:20px;align-items:flex-start;}}
.sidebar{{flex:0 0 240px;position:sticky;top:20px;max-height:calc(100vh - 40px);overflow:auto;background:#f8faf8;border:1px solid #dce8e0;border-radius:10px;padding:12px;}}
.sidebar h3{{margin:0 0 8px;font-size:14px;color:#0a7a5a;}}
.sidebar .side-item{{display:block;width:100%;text-align:left;background:none;border:none;border-bottom:1px dashed #e5ece6;padding:6px 4px;font-size:13px;color:#333;cursor:pointer;}}
.sidebar .side-item:hover{{color:#c41e3a;}}
.sidebar .side-item.playing{{color:#0a7a5a;font-weight:700;}}
.main{{flex:1;min-width:0;}}
.side-note{{font-size:11px;color:#8aa;margin-top:8px;}}
@media (max-width:760px){{.layout{{flex-direction:column;}}.sidebar{{flex:none;position:static;max-height:200px;width:100%;}}}}
.footnote{{color:#888;font-size:12px;margin-top:30px;border-top:1px solid #eee;padding-top:12px;}}
</style>
</head>
<body>
<div class="nav">
<a href="index.html">首页</a>
<a href="discography.html">作品百科</a>
<a href="songs.html">歌曲库</a>
<a href="live/setlists.html">全部歌单</a>
<a href="live-reviews.html">现场实录</a>
<a href="tavern/">深夜小酒馆</a>
<a href="search.html">🔍 全站搜索</a>
</div>
<h1>🎵 王晰歌曲库</h1>
<p style="color:#666;font-size:14px;">共 <strong>{len(songs)}</strong> 首：{n_lyrics} 首含歌词片段 · {n_album} 首有专辑关联 · {n_shows} 首有巡演演唱记录。数据来源 <code>data/songs_meta.json</code>。</p>
<div class="layout">
<div class="sidebar">
<h3>🎧 曲库试听（{n_all}）</h3>
<div id="sideList"></div>
<p class="side-note">点击即播：自动探测 QQ音乐 → 网易云音乐，哪个能听用哪个；再点暂停。</p>
</div>
<div class="main">
<div class="search-box" role="search">
<input type="search" id="songSearch" placeholder="搜索歌曲 / 专辑 / 歌词…" autocomplete="off" aria-label="搜索歌曲库">
</div>
<div class="filter-bar">
<button type="button" class="chip chip-all" id="chipAll">全部（{n_all}）</button>
<button type="button" class="chip" id="chipPlayable">🎧 可试听（{n_play}）</button>
<button type="button" class="chip" id="chipLyric">📝 有歌词（{n_lyr}）</button>
<button type="button" class="chip" id="chipTavern">🍷 日木斤深夜小酒馆（{n_tavern}）</button>
</div>
<div id="playerStatus"></div>
<div class="song-list" id="songList"></div>
</div>
</div>
<p class="footnote">🎧 试听为多平台聚合：先试 QQ音乐（vkey 直链），失败自动切网易云音乐（搜索+直链）——哪个能听用哪个，不写死。VIP 锁曲需本地代理或登录。试听均为公开直链（不下载不托管）。生成时间 {meta["generated_at"]}。</p>
<script src="assets/player_embed.js?v=3"></script>
<script>
(function () {{
  'use strict';
  var songs = null;
  var statusEl = document.getElementById('playerStatus');
  var filter = 'all';
  var PLAYABLE = {json.dumps(playable_list, ensure_ascii=False)};
  function esc(s) {{ return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }}
  function norm(s) {{ return String(s == null ? '' : s).replace(/[《》「」]/g,'').replace(/\\s+/g,'').toLowerCase(); }}
  if (window.PlayerEmbed && window.PlayerEmbed.setStatusFn) {{
    window.PlayerEmbed.setStatusFn(function (kind, title) {{
      if (!statusEl) return;
      if (kind === 'fail') {{ statusEl.style.display=''; statusEl.textContent = '⚠️ 试听失败：' + (title || '该曲可能为 VIP 或需登录 QQ音乐'); }}
      else if (kind === 'load') {{ statusEl.style.display=''; statusEl.textContent = '⏳ ' + (title || '正在查找可播版本…'); }}
      else if (kind === 'play' && title) {{ statusEl.style.display=''; statusEl.textContent = '🎵 正在试听：' + title; }}
      else if (kind === 'pause') {{ statusEl.style.display=''; statusEl.textContent = '⏸ 已暂停'; }}
    }});
  }}
  function cardHtml(s) {{
    var tags = '';
    if (s.tavern) tags += '<span class="tag tavern">🍷 日木斤深夜小酒馆</span>';
    if (s.album) tags += '<span class="tag album">专辑《' + esc(s.album) + '》</span>';
    if (s.lyrics && s.lyrics.length) tags += '<span class="tag lyric">歌词</span>';
    if (s.show_count) tags += '<span class="tag live">巡演 ' + s.show_count + ' 场</span>';
    var lyrics = '';
    if (s.lyrics && s.lyrics.length) {{
      var allLines = s.lyrics.map(function (f) {{ return esc(f.text); }}).join('<br>');
      if (s.lyrics.length === 1) {{
        lyrics = '<div class="song-lyrics">' + allLines + '</div>';
      }} else {{
        lyrics = '<div class="song-lyrics"><span class="lyr-preview">' + esc(s.lyrics[0].text) + '…</span>' +
          '<button type="button" class="lyr-toggle">展开完整歌词</button>' +
          '<span class="lyr-full" style="display:none">' + allLines + '</span></div>';
      }}
    }}
    var credits = '';
    if (s.credits) {{
      var cp = [];
      if (s.credits.lyricist) cp.push('词：' + s.credits.lyricist);
      if (s.credits.composer) cp.push('曲：' + s.credits.composer);
      if (s.credits.arranger) cp.push('编曲：' + s.credits.arranger);
      if (s.credits.producer) cp.push('制作人：' + s.credits.producer);
      if (s.credits.original) cp.push('原唱：' + s.credits.original);
      if (cp.length) credits = '<div class="song-credits">' + cp.map(esc).join(' · ') + '</div>';
    }}
    var meta = [s.attr, s.release !== '-' ? s.release : ''].filter(Boolean).join(' · ');
    /* 多平台试听：有 mid 用 mid（QQ→网易云），无 mid 用歌名（网易云） */
    var play = '<button type="button" class="pe-btn" data-mid="' + esc(s.mid || '') + '" data-title="' + esc(s.name) + '">▶ 试听</button>';
    return '<div class="song-card">' +
      '<div class="song-head"><span class="song-name">《' + esc(s.name) + '》</span>' + play + '</div>' +
      (meta ? '<div class="song-meta">' + esc(meta) + tags + '</div>' : '<div class="song-meta">' + tags + '</div>') +
      credits + lyrics + '</div>';
  }}
  function applyFilter(list) {{
    if (filter === 'playable') return list.filter(function (s) {{ return !!s.mid; }});
    if (filter === 'lyric') return list.filter(function (s) {{ return s.lyrics && s.lyrics.length; }});
    if (filter === 'tavern') return list.filter(function (s) {{ return s.tavern; }});
    return list;
  }}
  function render() {{
    var box = document.getElementById('songList');
    var q = norm(document.getElementById('songSearch').value);
    var list = songs || [];
    if (q) {{
      list = list.filter(function (s) {{
        return norm(s.name).indexOf(q) >= 0 ||
          (s.album || '').indexOf(q) >= 0 ||
          (s.attr || '').indexOf(q) >= 0 ||
          (s.lyrics || []).some(function (f) {{ return norm(f.text).indexOf(q) >= 0; }});
      }});
    }}
    list = applyFilter(list);
    /* 可试听置顶 */
    list = list.slice().sort(function (a, b) {{ return (b.mid ? 1 : 0) - (a.mid ? 1 : 0); }});
    if (!list.length) {{ box.innerHTML = '<div class="empty">没有匹配的歌曲</div>'; return; }}
    box.innerHTML = list.map(cardHtml).join('');
    if (window.PlayerEmbed && window.PlayerEmbed.attach) {{
      box.querySelectorAll('.pe-btn').forEach(function (b) {{
        window.PlayerEmbed.attach(b, {{ mid: b.getAttribute('data-mid'), title: b.getAttribute('data-title') }});
      }});
    }}
  }}
  function setFilter(f) {{
    filter = f;
    ['chipAll','chipPlayable','chipLyric','chipTavern'].forEach(function (id) {{
      var el = document.getElementById(id);
      if (el) el.classList.toggle('on', id === ('chip' + f.charAt(0).toUpperCase() + f.slice(1)));
    }});
    render();
  }}
  /* 左侧试听栏：全部歌曲，点击时动态探测 QQ→网易云 */
  function renderSide() {{
    var box = document.getElementById('sideList');
    if (!box || !songs) return;
    box.innerHTML = songs.map(function (s) {{
      return '<button type="button" class="side-item" data-mid="' + esc(s.mid || '') + '" data-title="' + esc(s.name) + '">▶ ' + esc(s.name) + '</button>';
    }}).join('');
    if (window.PlayerEmbed && window.PlayerEmbed.attach) {{
      box.querySelectorAll('.side-item').forEach(function (b) {{
        window.PlayerEmbed.attach(b, {{ mid: b.getAttribute('data-mid'), title: b.getAttribute('data-title') }});
      }});
    }}
  }}
  /* 播放高亮：当前播放的侧栏项/卡片标绿 */
  function highlightPlaying() {{
    var playingMid = window.PlayerEmbed && window.PlayerEmbed.currentMid ? window.PlayerEmbed.currentMid.replace(/^L:/, '') : '';
    document.querySelectorAll('.side-item').forEach(function (b) {{
      var mid = (b.getAttribute('data-mid') || '').replace(/^L:/, '');
      b.classList.toggle('playing', !!playingMid && mid === playingMid);
      b.textContent = (mid === playingMid ? '⏸ ' : '▶ ') + b.textContent.replace(/^[▶⏸] /, '');
    }});
  }}
  setInterval(highlightPlaying, 800);
  /* 展开/收起完整歌词（事件委托） */
  document.getElementById('songList').addEventListener('click', function (e) {{
    var btn = e.target && e.target.closest ? e.target.closest('.lyr-toggle') : null;
    if (!btn) return;
    var card = btn.closest('.song-card');
    if (!card) return;
    var full = card.querySelector('.lyr-full');
    var preview = card.querySelector('.lyr-preview');
    if (full && full.style.display === 'none') {{
      full.style.display = 'block';
      if (preview) preview.style.display = 'none';
      btn.textContent = '▲ 收起歌词';
    }} else if (full) {{
      full.style.display = 'none';
      if (preview) preview.style.display = '';
      btn.textContent = '展开完整歌词';
    }}
  }});
  document.getElementById('chipAll').addEventListener('click', function () {{ setFilter('all'); }});
  document.getElementById('chipPlayable').addEventListener('click', function () {{ setFilter('playable'); }});
  document.getElementById('chipLyric').addEventListener('click', function () {{ setFilter('lyric'); }});
  document.getElementById('chipTavern').addEventListener('click', function () {{ setFilter('tavern'); }});
  /* 加载歌曲库 + 小酒馆音频清单，按歌名合并 mid */
  Promise.all([
    fetch('data/songs_meta.json', {{ cache: 'no-store' }}).then(function (r) {{ return r.json(); }}),
    fetch('data/tavern_audio.json', {{ cache: 'no-store' }}).then(function (r) {{ return r.json(); }}).catch(function () {{ return null; }})
  ]).then(function (res) {{
    var j = res[0];
    var t = res[1];
    songs = Object.values(j.songs || {{}});
    var byName = {{}};
    songs.forEach(function (s) {{ if (s.name) byName[norm(s.name)] = s; }});
    var tavern = [];
    if (t && t.items) {{
      t.items.forEach(function (it) {{
        var key = norm(it.name);
        var exist = byName[key];
        if (exist) {{
          if (!exist.mid && it.mid) exist.mid = it.mid;
          exist.tavern = true;
          exist.tavernEpisode = it.episode;
          if (!exist.album && it.album) exist.album = it.album;
        }} else {{
          tavern.push({{ name: it.name, mid: it.mid, album: it.album || '日木斤深夜小酒馆',
            attr: '小酒馆音频', release: '-', tavern: true, tavernEpisode: it.episode,
            lyrics: [], show_count: 0 }});
        }}
      }});
    }}
    songs = songs.concat(tavern);
    render();
    renderSide();
  }})
  .catch(function () {{ document.getElementById('songList').innerHTML = '<div class="empty">数据加载失败</div>'; }});
  document.getElementById('songSearch').addEventListener('input', render);
}})();
</script>
</body>
</html>
"""


def main() -> None:
    meta = json.loads(DATA.read_text(encoding="utf-8"))
    OUT.write_text(build_page(meta), encoding="utf-8")
    print(f"[OK] 已生成 -> {OUT}")
    print(f"  歌曲: {meta['song_count']}")


if __name__ == "__main__":
    main()
