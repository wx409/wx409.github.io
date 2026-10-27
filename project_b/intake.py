#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""活动/新歌 入库候选箱：先收，再问，后入库。

用法：
  python -X utf8 project_b/intake.py list
  python -X utf8 project_b/intake.py add --kind show --title "音乐舞蹈诗剧《长城长》" --date 2026-11-01 --city 石家庄 --source "大麦"
  python -X utf8 project_b/intake.py accept <id>     # show 只打印待执行命令；song 直接写时间轴
  python -X utf8 project_b/intake.py reject <id>

纪律：任何候选默认 pending，必须人工确认后才入库。
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
INBOX = ROOT / 'data' / 'intake_inbox.json'


def load():
    if INBOX.exists():
        return json.loads(INBOX.read_text(encoding='utf-8'))
    return {"schema": "intake_inbox/v1", "items": []}


def save(d):
    INBOX.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')


def cmd_list(a):
    d = load()
    items = d['items']
    pend = [x for x in items if x['status'] == 'pending']
    print(f"候选 {len(items)} 条｜待确认 {len(pend)}")
    for x in items:
        print(f"  [{x['status']}] {x['id']} {x['kind']} {x['title']} {x.get('date','')} {x.get('city','')}")


def cmd_add(a):
    d = load()
    nid = f"c{len(d['items'])+1:03d}"
    d['items'].append({"id": nid, "kind": a.kind, "title": a.title, "date": a.date or "",
                       "city": a.city or "", "source": a.source or "", "note": a.note or "",
                       "status": "pending", "detected_at": date.today().isoformat()})
    save(d)
    print('已加入候选：', nid)


def cmd_accept(a):
    d = load()
    it = next((x for x in d['items'] if x['id'] == a.id), None)
    if not it:
        print('没有这个候选'); return
    if it['kind'] == 'song':
        tl = json.loads((ROOT / 'data/timeline.json').read_text(encoding='utf-8'))
        if any(it['title'] in e.get('title', '') for e in tl):
            print('时间轴已存在'); return
        tl.append({"date": it['date'], "type": "album", "title": it['title'],
                   "source": it['source'], "stage": "发行"})
        tl.sort(key=lambda e: e.get('date', ''))
        (ROOT / 'data/timeline.json').write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding='utf-8')
        it['status'] = 'accepted'
        save(d)
        print('已写入时间轴')
    else:
        print('请在确认信息后执行：')
        print(f'python -X utf8 project_b\\add_show.py --date {it["date"]} --name "{it["title"]}" '
              f'--city {it.get("city","")} --stage 东演 --match {it["title"][:4]} '
              f'--source "{it["source"]}" --held-date {it["date"]}')
        print('（执行成功后把该候选标为 accepted：intake.py done ' + it['id'] + '）')


def cmd_done(a):
    d = load()
    for x in d['items']:
        if x['id'] == a.id:
            x['status'] = 'accepted'
    save(d)
    print('已标记 accepted')


def cmd_reject(a):
    d = load()
    for x in d['items']:
        if x['id'] == a.id:
            x['status'] = 'rejected'
    save(d)
    print('已标记 rejected')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd')
    sub.add_parser('list')
    ad = sub.add_parser('add')
    ad.add_argument('--kind', default='show', choices=['show', 'song', 'activity'])
    ad.add_argument('--title', required=True)
    ad.add_argument('--date', default='')
    ad.add_argument('--city', default='')
    ad.add_argument('--source', default='')
    ad.add_argument('--note', default='')
    for name in ('accept', 'done', 'reject'):
        p = sub.add_parser(name)
        p.add_argument('id')
    args = ap.parse_args()
    {'list': cmd_list, 'add': cmd_add, 'accept': cmd_accept,
     'done': cmd_done, 'reject': cmd_reject}[args.cmd](args)
