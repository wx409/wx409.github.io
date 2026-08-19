# -*- coding: utf-8 -*-
"""规则筛选工作室微博 → 分类统计（纯正则，零 AI token）"""
import json, re
from pathlib import Path
from collections import Counter

idx = json.loads(Path(r"E:\wx\私有工具\weibo_archive_studio\index.json").read_text(encoding='utf-8'))
posts = idx.get('posts', [])

# 类别关键词
TOUR_KW = ['巡演', '巡回', '个人巡回', '音乐会', '演唱会', '听海而歌', '个巡', '回响', '「回」']
PERF_KW = ['音乐节', '盛典', '晚会', '发布会', '音乐剧', '综艺', '舞台', '演出', '大赛', '盛典']
RELEASE_KW = ['新歌', '专辑', '单曲', '上线', '发行', '首发', 'OST', '主题曲', '片尾曲', '插曲', '预告', '献唱']
# 无价值（转发/祝福/日常）
DROP_KW = ['//@', '转发微博', '生日快乐', '新年快乐', '祝福', '爱国', '致敬', '纪念', '悼念',
           '勿忘', '平安', '周末愉快', '早安', '晚安', '国庆', '中秋', '清明', '端午', '节日']

def classify(text):
    t = text or ''
    # 无价值优先
    if any(k in t for k in DROP_KW):
        return '无价值'
    # 主题标签优先判断
    tags = re.findall(r'#([^#]+)#', t)
    tag_str = ''.join(tags)
    if any(k in tag_str for k in ['巡演', '巡回', '音乐会', '演唱会', '听海而歌']):
        return '巡演'
    if any(k in tag_str for k in PERF_KW):
        return '演出'
    if any(k in tag_str for k in ['新歌', '专辑', '单曲', '上线', '发行', 'OST', '主题曲']):
        return '新歌'
    # 正文关键词
    if any(k in t for k in TOUR_KW):
        return '巡演'
    if any(k in t for k in RELEASE_KW):
        return '新歌'
    if any(k in t for k in PERF_KW):
        return '演出'
    if any(k in t for k in DROP_KW):
        return '无价值'
    return '待定'

result = {}
for p in posts:
    cat = classify(p.get('text', ''))
    result.setdefault(cat, []).append(p)

print(f"总微博: {len(posts)}")
for cat, items in sorted(result.items(), key=lambda x: -len(x[1])):
    print(f"  {cat}: {len(items)} 条")

# 按年份统计有价值类
print("\n=== 有价值类按年份 ===")
for cat in ('巡演', '演出', '新歌'):
    c = Counter(p['date'][:4] for p in result.get(cat, []))
    print(f"  {cat}: " + ', '.join(f"{y}:{n}" for y, n in sorted(c.items())))

print("\n=== '待定' 抽样（看是否有漏分） ===")
for p in result.get('待定', [])[:10]:
    print(f"  [{p['date']}] {p['text'][:50]}")
