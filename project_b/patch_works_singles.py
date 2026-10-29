import sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
p = Path(r'D:\wx409.github.io\project_b\build_compact.py')
s = p.read_text(encoding='utf-8')
if '_singles_block' in s:
    print('已存在'); raise SystemExit

helper = '''
def _singles_block():
    """正式单曲 / OST 实测区块（只报音级；数据来自 data/research/singles_analysis.json）。"""
    try:
        d = jload("data/research/singles_analysis.json", {})
        rows = []
        for s in d.get("songs", []):
            low = s.get("low_stable") or {}
            if not low.get("note"):
                continue
            rows.append((s.get("title"), low["note"], s.get("span_octaves") or 0,
                         s.get("stability_cents_median") or 0))
    except Exception:
        return ""
    if not rows:
        return ""
    order = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6,
             "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}

    def key(r):
        n = r[1][:-1]
        try:
            return order[n] + 12 * int(r[1][-1])
        except Exception:
            return 99
    rows.sort(key=key)
    trs = "".join(
        f'<tr><td>{i+1}</td><td>{esc(t)}</td><td class="n">{esc(n)}</td>'
        f'<td class="n">{num(sp, 2)}</td><td class="n">{num(st, 1)}</td></tr>'
        for i, (t, n, sp, st) in enumerate(rows[:10]))
    return f"""
<h2>二之二、正式单曲 / OST 实测（{len(rows)} 首已测）</h2>
<p>单曲与 OST 的主导权常在制作人与剧方，更能说明<strong>他的声音被怎样使用</strong>。
下表只报<strong>音级</strong>——单曲多为 320k 有损，频率精度低于无损素材，故不报 Hz。</p>
<table><tr><th>#</th><th>曲目</th><th>最低音</th><th>跨度（八度）</th><th>稳定性（音分）</th></tr>{trs}</table>
<p class="sub">按最低音排序，展示前 10 首；已测 {len(rows)} 首。数据源：
<a href="/data/research/singles_analysis.json">singles_analysis.json</a>（逐曲全量）。</p>
"""

'''

anchor = 'def build_works():'
assert s.count(anchor) == 1
s = s.replace(anchor, helper + anchor)

old = '''    return page("works.html",'''
new = '''    blocks += _singles_block()
    return page("works.html",'''
assert s.count(old) == 1
s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
print('已把单曲区块接入 build_compact.build_works')
