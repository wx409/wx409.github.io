#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""新歌自动入库：一条链把新歌写进「采集清单 / 发行事件表 / 时间轴」。

来源：watch_releases.py 的产出（data/pending_releases.json）或 albums.json 中尚无收录的曲目。
行为：幂等、先备份、文件被占用时进队列下次重试。
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')
XLSX_TRACK = Path(r'E:\wx\收听人数（2026.7.24）.xlsx')
XLSX_SONG = Path(r'E:\wx\index_records\王晰歌曲信息汇总.xlsx')
QUEUE = ROOT / 'data' / 'intake_queue.json'
LOG = ROOT / 'data' / 'song_intake_log.json'


def link_for(mid: str) -> str:
    return (f'https://y.qq.com/m/client/music_index/index.html?ADTAG=cbshare&channelId=10036163'
            f'&mid={mid}&openinqqmusic=1&type={mid}')


def load_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except Exception:
        return default


def candidates() -> list[dict]:
    """待入库新歌：pending_releases.json + albums.json 中未进清单的曲目。"""
    out = []
    pend = load_json(ROOT / 'data' / 'pending_releases.json', {})
    for x in (pend.get('releases') or pend.get('new') or pend.get('items') or []):
        if isinstance(x, dict) and x.get('mid'):
            out.append({"name": x.get('name') or x.get('title'), "mid": x['mid'].replace('L:', ''),
                        "date": x.get('release') or x.get('date') or ''})
    alb = load_json(ROOT / 'data' / 'albums.json', {})
    for a in alb.get('albums', []):
        if str(a.get('kind', '')).lower() != 'single':
            continue  # 专辑曲目不该进单曲/OST 清单
        for s in (a.get('songs') or []):
            mid = (s.get('mid') or '').replace('L:', '')
            if mid and s.get('title'):
                out.append({"name": s['title'], "mid": mid,
                            "date": a.get('release_date') or a.get('release') or ''})
    seen, uniq = set(), []
    for x in out:
        if x['mid'] in seen:
            continue
        seen.add(x['mid'])
        uniq.append(x)
    return uniq


def flush_queue() -> None:
    q = load_json(QUEUE, {"items": []})
    if not q.get('items'):
        return
    remain = []
    for it in q['items']:
        ok = apply_one(it, dry=False)
        if not ok:
            remain.append(it)
    q['items'] = remain
    QUEUE.write_text(json.dumps(q, ensure_ascii=False, indent=1), encoding='utf-8')


def apply_one(it: dict, dry: bool = False) -> bool:
    import openpyxl
    name, mid, date = it['name'], it['mid'], it.get('date') or ''
    link = link_for(mid)
    ok = True

    # ① 采集清单
    try:
        wb = openpyxl.load_workbook(XLSX_TRACK)
        ws = wb.active
        names = [str(ws.cell(row=r, column=2).value or '') for r in range(2, ws.max_row + 1)]
        if name not in names:
            if dry:
                print('[dry] 采集清单 +', name)
            else:
                bak = XLSX_TRACK.with_name(XLSX_TRACK.stem + f'.bak_{datetime.now():%Y%m%d_%H%M}' + XLSX_TRACK.suffix)
                shutil.copy2(XLSX_TRACK, bak)
                r = ws.max_row + 1
                ws.cell(row=r, column=1).value = ws.max_row - 1
                ws.cell(row=r, column=2).value = name
                ws.cell(row=r, column=3).value = '王晰'
                ws.cell(row=r, column=4).value = link
                ws.cell(row=r, column=5).value = link
                ws.cell(row=r, column=7).value = name
                wb.save(XLSX_TRACK)
                print('采集清单 +', name)
    except PermissionError:
        print('采集清单被占用，进队列:', name); ok = False
    except Exception as e:
        print('采集清单写入失败', name, repr(e)[:60]); ok = False

    # ② 发行事件表
    try:
        wb = openpyxl.load_workbook(XLSX_SONG)
        ws = wb['OST&单曲']
        names = [str(ws.cell(row=r, column=3).value or '') for r in range(2, ws.max_row + 1)]
        if name not in names:
            if dry:
                print('[dry] 发行表 +', name)
            else:
                bak = XLSX_SONG.with_name(XLSX_SONG.stem + f'.bak_{datetime.now():%Y%m%d_%H%M}' + XLSX_SONG.suffix)
                shutil.copy2(XLSX_SONG, bak)
                r = ws.max_row + 1
                ws.cell(row=r, column=1).value = '=ROW()-1'
                ws.cell(row=r, column=3).value = name
                ws.cell(row=r, column=4).value = date or datetime.now().strftime('%Y-%m-%d')
                ws.cell(row=r, column=5).value = '单曲（自动入库）'
                wb.save(XLSX_SONG)
                print('发行表 +', name)
    except PermissionError:
        print('发行表被占用，进队列:', name); ok = False
    except Exception as e:
        print('发行表写入失败', name, repr(e)[:60]); ok = False

    # ③ 时间轴
    if not dry:
        tl = load_json(ROOT / 'data' / 'timeline.json', [])
        if not any(name in e.get('title', '') for e in tl):
            tl.append({"date": date or datetime.now().strftime('%Y-%m-%d'), "type": "album",
                       "title": f"新歌《{name}》发行", "source": "自动入库（watch_releases）", "stage": "发行"})
            tl.sort(key=lambda e: e.get('date', ''))
            (ROOT / 'data' / 'timeline.json').write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding='utf-8')
            print('时间轴 +', name)
    return ok


def main() -> None:
    dry = '--dry' in sys.argv
    flush_queue()
    done, queued = [], []
    for it in candidates():
        try:
            ok = apply_one(it, dry=dry)
        except Exception as e:
            print('失败', it['name'], repr(e)[:80]); ok = False
        (done if ok else queued).append(it)
    log = load_json(LOG, {"history": []})
    log['history'].append({"at": datetime.now().isoformat(timespec='seconds'),
                           "done": [x['name'] for x in done], "queued": [x['name'] for x in queued]})
    log['history'] = log['history'][-200:]
    LOG.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'完成 {len(done)}｜入队 {len(queued)}')


if __name__ == '__main__':
    main()
