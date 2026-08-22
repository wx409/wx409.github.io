# -*- coding: utf-8 -*-
"""从观众反馈提取「现场歌单候选」：用歌名库匹配反馈文本中的歌名，按提及次数排序。
帮助人工确认演出实际歌单（自动提取不可靠，仅做候选清单，零 LLM 省 token）。
用法：
  python project_b/build_repo_setlist_candidates.py --date 2026-08-23 --city 广州
输出：E:\wx\私有工具\show_feedback\<日期>_<城市>\setlist_candidates.txt + 控制台
数据源：all_feedback.json（微博/B站/Bing）+ xhs_archive 中含城市的笔记正文
"""
import argparse, io, json, re, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(r'D:\wx409.github.io')
FB_ROOT = Path(r'E:\wx\私有工具\show_feedback')
XHS_ARCHIVE = Path(r'E:\wx\私有工具\xhs_archive')

def load_song_names():
    """歌名清单（长歌名优先匹配，避免短名误配）"""
    si = json.loads((ROOT / 'data' / 'song_index_lite.json').read_text(encoding='utf-8'))
    songs = si.get('songs', {})
    names = set()
    for k, v in songs.items():
        nm = v.get('name') or k
        names.add(nm)
        # 变体：去掉 (Live)/（Live）后缀、全角括号版本
        nm2 = re.sub(r'[\(（]\s*(Live|live)\s*[\)）]', '', nm).strip()
        if nm2 != nm and len(nm2) >= 2:
            names.add(nm2)
    return sorted(names, key=len, reverse=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--date', required=True)
    ap.add_argument('--city', required=True)
    args = ap.parse_args()

    out_dir = FB_ROOT / ('%s_%s' % (args.date.replace('-', ''), args.city))
    names = load_song_names()
    print('歌名库: %d 个（含变体）' % len(names))

    texts = []  # (text, platform)
    fb_path = out_dir / 'all_feedback.json'
    if fb_path.exists():
        fb = json.loads(fb_path.read_text(encoding='utf-8'))
        for p in fb.get('weibo') or []:
            if not p.get('official'):
                texts.append((p.get('text', ''), '微博'))
        for v in fb.get('bili') or []:
            texts.append((v.get('title', ''), 'B站'))
            for c in v.get('comments') or []:
                texts.append((c.get('text', ''), 'B站评论'))
        for h in fb.get('bing') or []:
            texts.append((h.get('snippet', ''), '网页'))
    # 小红书正文
    if XHS_ARCHIVE.exists():
        d0 = args.date.replace('-', '')
        for kd in XHS_ARCHIVE.iterdir():
            if not kd.is_dir(): continue
            m = re.match(r'^(\d{8})_', kd.name)
            if not m or m.group(1) < d0: continue
            if args.city not in kd.name: continue
            ct = kd / 'content.txt'
            if ct.exists():
                texts.append((ct.read_text(encoding='utf-8', errors='ignore'), '小红书'))
    print('反馈文本: %d 条' % len(texts))

    cand = {}  # 歌名 -> {count, sources:set}
    for text, plat in texts:
        if not text or len(text) < 3:
            continue
        matched = set()
        for nm in names:
            # 短歌名（≤2字）仅在《》内匹配，避免"我/你/爱"等泛匹配噪音
            if len(nm) <= 2 and ('《' + nm + '》') not in text:
                continue
            if nm in text:
                matched.add(nm)
        for nm in matched:
            e = cand.setdefault(nm, {'count': 0, 'sources': set()})
            e['count'] += 1
            e['sources'].add(plat)

    if not cand:
        print('未匹配到歌名（反馈不足或数据未收集），稍后再试。')
        return
    ranked = sorted(cand.items(), key=lambda kv: (-kv[1]['count'], -len(kv[1]['sources'])))
    lines = ['【现场歌单候选 %s %s站】按反馈提及次数排序（候选清单，供人工确认实际歌单）' % (args.date, args.city)]
    for i, (nm, e) in enumerate(ranked, 1):
        lines.append('%2d. %-20s 提及 %d 次（%s）' % (i, nm, e['count'], '/'.join(sorted(e['sources']))))
    (out_dir / 'setlist_candidates.txt').write_text('\n'.join(lines), encoding='utf-8')
    print('\n'.join(lines[:40]))
    print('已存: %s\\setlist_candidates.txt' % out_dir)

if __name__ == '__main__':
    main()
