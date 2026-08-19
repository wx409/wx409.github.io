# -*- coding: utf-8 -*-
"""粗聚类：按日期+场次/歌名主题去重，估算独立事件数（省 LLM token 的关键）"""
import json, re
from pathlib import Path

idx = json.loads(Path(r"E:\wx\私有工具\weibo_archive_studio\index.json").read_text(encoding='utf-8'))
posts = idx.get('posts', [])

# 提取"场次/歌名"关键词：从 #话题# 和 正文里的《歌名》
def extract_key(text, tags):
    # 取第一个非 #王晰# 的话题作为类别标记
    meaningful = [t for t in tags if t not in ('王晰',)]
    if meaningful:
        return meaningful[0][:12]
    # 取《歌名》
    songs = re.findall(r'《([^》]{2,12})》', text)
    if songs:
        return '歌:' + songs[0]
    return ''

events = {}  # (date, key) -> count
for p in posts:
    date = p['date'][:10]
    text = p.get('text', '')
    tags = re.findall(r'#([^#]+)#', text)
    key = extract_key(text, tags)
    if not key:
        key = text[:10]
    events.setdefault((date, key), 0)
    events[(date, key)] += 1

print(f"粗聚类后独立事件数: {len(events)}（原始 {len(posts)} 条）")
print(f"压缩比: 去重后约为原条数的 {len(events)*100//max(len(posts),1)}%")

# 按类别统计（复用之前规则）
TOUR = ['巡演','巡回','音乐会','演唱会','听海而歌']
def cat_of(k):
    return '巡演' if any(x in k for x in TOUR) else '其它'

cats = {}
for (d,k),c in events.items():
    c0 = cat_of(k)
    cats.setdefault(c0, []).append((d,k,c))
for c0, arr in sorted(cats.items(), key=lambda x:-len(x[1])):
    print(f"  {c0}: {len(arr)} 个独立事件")
