import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')

# 1) 官方账号自动入库（微博）
p = ROOT / 'project_b' / 'scan_intake.py'
s = p.read_text(encoding='utf-8')
s = s.replace("NOISE = ('直拍', '花絮', '返图', '转发', '后台', '排练', '混剪')",
              "NOISE = ('直拍', '花絮', '返图', '转发', '后台', '排练', '混剪')\n"
              "# 官方账号：命中官宣词即自动入库，不用人工确认\n"
              "OFFICIAL_UIDS = {1292815744: '王晰本人', 7215995153: '王晰工作室'}")
s = s.replace('                out.append({"date": day, "text": txt, "id": mb.get(\'id\')})',
              '                out.append({"date": day, "text": txt, "id": mb.get(\'id\'),\n'
              '                            "uid": (mb.get("user") or {}).get("id")})')
s = s.replace('''        nid = f"c{len(inbox['items'])+1:03d}"
        inbox['items'].append({''',
'''        nid = f"c{len(inbox['items'])+1:03d}"
        official = p.get('uid') in OFFICIAL_UIDS
        if official:
            tl = json.loads(TIMELINE.read_text(encoding='utf-8'))
            tl.append({"date": p['date'], "type": "media",
                       "title": f"官宣：{title[:36]}",
                       "source": f"{OFFICIAL_UIDS[p['uid']]}微博 {p.get('id')}",
                       "stage": "官方"})
            tl.sort(key=lambda e: e.get('date', ''))
            TIMELINE.write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding='utf-8')
        inbox['items'].append({''')
s = s.replace('            "status": "pending",', '            "status": "accepted" if official else "pending",')
s = s.replace('        added += 1\n', '        added += 1\n')
p.write_text(s, encoding='utf-8')
print('已接入官方账号自动入库')

# 2) 清理候选箱
q = ROOT / 'data' / 'intake_inbox.json'
d = json.loads(q.read_text(encoding='utf-8'))
for x in d['items']:
    if x['id'] == 'c001':
        x['date'] = '2026-10-27'
        x['note'] = '《火光》发行日 2026-10-27（用户提供官方信息）'
    elif x['id'] == 'c002':
        x['status'] = 'rejected'
        x['date'] = ''
        x['note'] = '撤回：2026-11-01 系我推测的占位日期，无来源'
    elif x['id'] in ('c005', 'c006'):
        x['status'] = 'rejected'
        x['note'] = (x.get('note') or '') + ' ｜粉丝对新歌的宣传，非新活动'
    elif x['id'] == 'c004':
        x['status'] = 'rejected'
        x['note'] = (x.get('note') or '') + ' ｜《火光》已入库；汽水音乐属平台，非新活动'
q.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
print('候选箱已清理')

# 3) 平台清单：加入汽水音乐
mp = ROOT / 'data' / 'music_platforms.json'
mp.write_text(json.dumps({
    "schema": "music_platforms/v1",
    "platforms": [
        {"id": "qqmusic", "name": "QQ音乐", "collector": "project_b/watch_releases.py", "auto": True},
        {"id": "netease", "name": "网易云音乐", "collector": "project_b/watch_netease.py", "auto": True},
        {"id": "soda", "name": "汽水音乐", "collector": None,
         "auto": False,
         "note": "待接入：汽水音乐无公开搜索 API，需用其 App/H5 接口或人工核对；发现新歌请走候选箱"},
    ],
    "updated": "2026-10-28",
}, ensure_ascii=False, indent=1), encoding='utf-8')
print('已建 data/music_platforms.json（含汽水音乐，标待接入）')
