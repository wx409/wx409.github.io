#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""从「王晰个人巡回音乐会」微博抽取场次（日期/城市/场馆），去重后列出待补场次。

城市用 data/cities.json 白名单匹配，场馆截断到括号/省略号前，避免脏字段。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
ARCH = Path(r'E:\wx\私有工具\weibo_archive_tour\posts')
OUT = ROOT / 'data' / 'tour_events_extracted.json'

DATE_RE = re.compile(r'演出时间[：:]\s*(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})')
DATE_RE2 = re.compile(r'(\d{4})[.\-/年](\d{1,2})[.\-/月](\d{1,2})日?')
VENUE_RE = re.compile(r'演出地点[：:]\s*([^\n📌]{2,40})')

raw_cities = json.loads((ROOT / 'data' / 'cities.json').read_text(encoding='utf-8'))
_c = raw_cities.get('cities') if isinstance(raw_cities, dict) else raw_cities
if isinstance(_c, dict):
    cities = [str(k) for k in _c.keys()]
elif isinstance(_c, list):
    cities = [str(x.get('name') if isinstance(x, dict) else x) for x in _c]
else:
    cities = []


def find_city(text: str) -> str:
    for c in sorted(cities, key=len, reverse=True):
        if c and c in text:
            return c
    m = re.search(r'——\s*([\u4e00-\u9fa5]{2,4})(站|首场)', text)
    return m.group(1) if m else ''


def clean_venue(v: str) -> str:
    v = re.split(r'[（(]|…|开票|售票|票价|温馨提示', v)[0]
    return v.replace('@', '').replace('丨', '·').strip(' ：:·')[:28]


def main() -> None:
    am = json.loads((ROOT / 'data' / 'activity_master.json').read_text(encoding='utf-8'))
    known = {(r.get('date'), str(r.get('city') or '')[:2]) for r in am.get('rows', []) if isinstance(r, dict)}
    known_dates = {d for d, _ in known}
    events, seen = [], set()
    for f in sorted(ARCH.glob('*/*/*.json')):
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
        except Exception:
            continue
        t = d['text']
        m = DATE_RE.search(t) or DATE_RE2.search(t)
        if not m:
            continue
        y, mo, dd = (int(x) for x in m.groups())
        if not (2000 <= y <= 2030):
            continue
        date = f"{y:04d}-{mo:02d}-{dd:02d}"
        city = find_city(t)
        vm = VENUE_RE.search(t)
        venue = clean_venue(vm.group(1)) if vm else ''
        key = (date, city)
        if key in seen:
            continue
        seen.add(key)
        events.append({"date": date, "city": city, "venue": venue,
                       "in_activity_master": date in known_dates,
                       "source_id": d['id'], "text": t[:120]})
    events.sort(key=lambda x: x['date'])
    OUT.write_text(json.dumps({"schema": "tour_events_extracted/v2", "count": len(events),
                               "events": events}, ensure_ascii=False, indent=1), encoding='utf-8')
    new = [e for e in events if not e['in_activity_master']]
    clean = [e for e in new if e['city'] and e['venue']]
    print(f'抽取 {len(events)}｜活动表已有 {len(events)-len(new)}｜缺 {len(new)}｜字段完整 {len(clean)}')
    for e in clean:
        print(f"  {e['date']} {e['city']:4s} {e['venue']}")


if __name__ == '__main__':
    main()
