import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
p = Path(r'D:\wx409.github.io\songs.html')
s = p.read_text(encoding='utf-8')

old = '<p style="color:#666;font-size:14px;">共 <strong>683</strong> 首：42 首含歌词片段 · 268 首有专辑关联 · 305 首有巡演演唱记录。数据来源 <code>data/songs_meta.js'
assert old in s
# 整段替换为占位（保留后半说明）
i = s.find(old)
j = s.find('</p>', i)
seg = s[i:j+4]
s = s[:i] + '<p id="songsStats" style="color:#666;font-size:14px;">正在统计…</p>' + s[j+4:]

s = s.replace('<h3>🎧 曲库试听（683）</h3>', '<h3 id="sideCount">🎧 曲库试听</h3>')

old2 = '    songs = Object.values(j.songs || {});'
new2 = '''    songs = Object.values(j.songs || {});
    (function () {
      var total = songs.length;
      var lyr = songs.filter(function (s) { return s.lyrics && s.lyrics.length; }).length;
      var alb = songs.filter(function (s) { return s.album; }).length;
      var live = songs.filter(function (s) { return (s.show_count || 0) > 0; }).length;
      var el = document.getElementById('songsStats');
      if (el) el.innerHTML = '共 <strong>' + total + '</strong> 首：' + lyr + ' 首有歌词 · '
        + alb + ' 首有专辑关联 · ' + live + ' 首有巡演演唱记录。数据来源 <code>data/songs_meta.json</code>（页面实时统计）';
      var sc = document.getElementById('sideCount');
      if (sc) sc.textContent = '🎧 曲库试听（' + total + '）';
    })();'''
assert s.count(old2) == 1
s = s.replace(old2, new2)
p.write_text(s, encoding='utf-8')
print('songs.html 统计改为实时派生')
