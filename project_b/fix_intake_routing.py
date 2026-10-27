import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
p = Path(r'D:\wx409.github.io\project_b\scan_intake.py')
s = p.read_text(encoding='utf-8')

# 用"按内容类型分流"替换"官方即入库"
old = '''        nid = f"c{len(inbox['items'])+1:03d}"
        official = p.get('uid') in OFFICIAL_UIDS
        if official:
            tl = json.loads(TIMELINE.read_text(encoding='utf-8'))
            tl.append({"date": p['date'], "type": "media",
                       "title": f"官宣：{title[:36]}",
                       "source": f"{OFFICIAL_UIDS[p['uid']]}微博 {p.get('id')}",
                       "stage": "官方"})
            tl.sort(key=lambda e: e.get('date', ''))
            TIMELINE.write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding='utf-8')'''
new = '''        nid = f"c{len(inbox['items'])+1:03d}"
        official = p.get('uid') in OFFICIAL_UIDS
        kind = classify_content(txt)
        if kind == 'material':
            continue
        # 只有"新歌发行"这类可结构化落点，才允许官方源自动写时间轴；
        # 演出/剧目需要场馆、场次、卡司等字段，走现有管道（add_show），仍进候选箱。
        if official and kind == 'release':
            tl = json.loads(TIMELINE.read_text(encoding='utf-8'))
            tl.append({"date": p['date'], "type": "album",
                       "title": f"新歌发行：{title[:36]}",
                       "source": f"{OFFICIAL_UIDS[p['uid']]}微博 {p.get('id')}",
                       "stage": "发行"})
            tl.sort(key=lambda e: e.get('date', ''))
            TIMELINE.write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding='utf-8')'''
assert s.count(old) == 1
s = s.replace(old, new)

# 状态：官方 release 自动 accepted；其余 pending
s = s.replace('            "status": "accepted" if official else "pending",',
              '            "status": "accepted" if (official and kind == "release") else "pending",')

# 新增分类函数
anchor = 'def main() -> None:'
helper = '''RELEASE_KEYS = ('新歌', '单曲', '发行', '上线')
SHOW_KEYS = ('巡演', '音乐会', '开票', '首演', '剧场', '演出')
MATERIAL_KEYS = ('直拍', '花絮', '返图', '后台', '排练')


def classify_content(text: str) -> str:
    """内容性质分流：release / show / material / other。"""
    if any(k in text for k in MATERIAL_KEYS):
        return 'material'
    if any(k in text for k in RELEASE_KEYS):
        return 'release'
    if any(k in text for k in SHOW_KEYS):
        return 'show'
    return 'other'


'''
assert s.count(anchor) == 1
s = s.replace(anchor, helper + anchor)
p.write_text(s, encoding='utf-8')
print('已改为按内容类型分流')
