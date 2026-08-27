# -*- coding: utf-8 -*-
"""演出状态自动联动（三处同步，随时可重算）：
  ① 长表单一事实源：演出日已过的「未举办/官宣未举办」→ 改为「已举办」（写前备份）
  ② 大屏 rebuild：长表变更后触发 QQ音乐大屏生成器 --rebuild
  ③ live 页：按各页 live-date meta 与今天重算 状态（已结束/售票中）→ 更新表格行/meta/og描述
用法：
  python project_b/update_show_status.py                # 三处联动（长表+大屏+live页）
  python project_b/update_show_status.py --no-rebuild   # 只改长表+live页，不触发大屏
  python project_b/update_show_status.py --page-only    # 只联动 live 页
"""
import argparse, datetime, io, re, shutil, subprocess, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = Path(r'D:\wx409.github.io')
LIVE = ROOT / 'live'
LONG = Path(r'E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx')
GEN = Path(r'E:\wx\QQ音乐大屏生成器_GEO优化版_源码.py')


def update_long_table():
    """① 长表：日期 < 今天 且含「未举办/官宣」→ 已举办（备份后写）"""
    import openpyxl
    today = datetime.date.today()
    if not LONG.exists():
        print('!! 长表不存在: %s' % LONG); return 0
    backup_dir = LONG.parent / 'backup'
    backup_dir.mkdir(exist_ok=True)
    bak = backup_dir / ('长表备份_%s.xlsx' % today.strftime('%Y%m%d_%H%M%S'))
    shutil.copy2(LONG, bak)
    wb = openpyxl.load_workbook(LONG)
    ws = wb.active
    changed = 0
    for row in ws.iter_rows(min_row=2):
        scene = str(row[2].value or '')
        if '未举办' not in scene and '官宣' not in scene:
            continue
        v = row[1].value
        if isinstance(v, datetime.datetime):
            d = v.date()
        elif isinstance(v, datetime.date):
            d = v
        elif isinstance(v, str):
            try:
                d = datetime.datetime.strptime(v.strip()[:10], '%Y-%m-%d').date()
            except Exception:
                continue
        else:
            continue
        if d >= today:
            continue
        new_scene = scene.replace('（官宣未举办）', '').replace('（官宣待举办）', '').replace('官宣未举办', '').strip()
        row[2].value = new_scene
        note = str(row[5].value or '')
        add = '已于%s完成；观众反馈见 live 页。' % d.strftime('%Y-%m-%d')
        if '已于' not in note:
            row[5].value = (note + ' ' + add).strip()
        changed += 1
        print('长表更新: %s | %s -> %s' % (d, scene, new_scene))
    if changed:
        wb.save(LONG)
        print('长表已保存（备份 %s），更新 %d 行' % (bak.name, changed))
    else:
        print('长表无需更新')
    return changed


def calc_status(show_date: datetime.date) -> str:
    return '已结束' if show_date < datetime.date.today() else '售票中'


def patch_live_pages():
    """③ live 页状态联动：按 live-date 重算状态，更新表格行/meta/og描述"""
    total = 0
    for page in sorted(LIVE.glob('*.html')):
        if 'setlists' in page.name:
            continue
        html = page.read_text(encoding='utf-8')
        m = re.search(r'<meta name="live-date" content="(\d{4}-\d{2}-\d{2})">', html)
        if not m:
            continue
        show_date = datetime.date.fromisoformat(m.group(1))
        st = calc_status(show_date)
        n = 0
        html, c = re.subn(r'(<tr><td>状态</td><td class="highlight">)[^<]*(</td></tr>)',
                          lambda x: x.group(1) + st + x.group(2), html)
        n += c
        html, c = re.subn(r'(<meta name="live-status" content=")[^"]*(">)',
                          lambda x: x.group(1) + st + x.group(2), html)
        n += c
        # og:description 状态词：只替换 售票中/未开票（已结束 不重复替换，幂等）
        html, c = re.subn(r'(og:description" content="[^"]*?)(售票中|未开票)([^"]*")',
                          lambda x: x.group(1) + st + x.group(3), html)
        n += c
        if st == '已结束':
            # JSON-LD 语义联动（GEO 友好）：EventScheduled→EventEnded，InStock→SoldOut
            html, c = re.subn(r'eventStatus":\s*"[^"]*EventScheduled"', '"eventStatus": "https://schema.org/EventEnded"', html)
            n += c
            html, c = re.subn(r'"availability":\s*"https://schema.org/InStock"', '"availability": "https://schema.org/SoldOut"', html)
            n += c
        if n:
            page.write_text(html, encoding='utf-8')
            total += n
            print('live页 %s: 状态→%s（%d 处）' % (page.name, st, n))
    print('live 页共更新 %d 处' % total)
    return total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--no-rebuild', action='store_true', help='不触发大屏 rebuild')
    ap.add_argument('--page-only', action='store_true', help='只联动 live 页')
    ap.add_argument('--no-push', action='store_true')
    a = ap.parse_args()

    if not a.page_only:
        update_long_table()
        if not a.no_rebuild:
            print('=== 大屏 rebuild ===')
            r = subprocess.run([sys.executable, str(GEN), '--rebuild'])
            print('rebuild 退出码: %d' % r.returncode)
    patch_live_pages()

    if not a.no_push:
        subprocess.run(['git', '-C', str(ROOT), 'add', 'live/'])
        r = subprocess.run(['git', '-C', str(ROOT), 'commit', '-m', '演出状态自动联动：长表/大屏/live页状态同步'])
        r2 = subprocess.run(['git', '-C', str(ROOT), 'push', 'origin', 'main'])
        print('已 commit + push（退出码 %d/%d）' % (r.returncode, r2.returncode))
    else:
        print('--no-push 模式，未提交。')


if __name__ == '__main__':
    main()
