# -*- coding: utf-8 -*-
"""大屏活动节点联动：演出日已过的巡演场次状态更新（长表单一事实源）。
- 长表：E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx
- 规则：日期 < 今天 且 场次含「未举办/官宣未举办」→ 改为「已举办」场次名 + 备注追加完成说明
- 写前备份到 长表同目录 backup/
用法：python project_b/update_show_status.py [--rebuild]
"""
import datetime, io, shutil, subprocess, sys
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

LONG = Path(r'E:\wx\index_records\历次巡演歌单\王晰巡演歌单长表_单一事实源.xlsx')
GEN = Path(r'E:\wx\QQ音乐大屏生成器_GEO优化版_源码.py')

def main():
    import openpyxl
    today = datetime.date.today()
    if not LONG.exists():
        print('!! 长表不存在: %s' % LONG); return

    backup_dir = LONG.parent / 'backup'
    backup_dir.mkdir(exist_ok=True)
    bak = backup_dir / ('长表备份_%s.xlsx' % today.strftime('%Y%m%d_%H%M%S'))
    shutil.copy2(LONG, bak)

    wb = openpyxl.load_workbook(LONG)
    ws = wb.active
    changed = 0
    for row in ws.iter_rows(min_row=2):
        date_cell = row[1]  # 日期列
        scene_cell = row[2]  # 场次列
        note_cell = row[5]  # 备注列
        scene = str(scene_cell.value or '')
        if '未举办' not in scene and '官宣' not in scene:
            continue
        if isinstance(date_cell.value, datetime.datetime):
            d = date_cell.value.date()
        elif isinstance(date_cell.value, datetime.date):
            d = date_cell.value
        elif isinstance(date_cell.value, str):
            # 部分行日期是文本（如 '2026-08-23'），需解析
            try:
                d = datetime.datetime.strptime(date_cell.value.strip()[:10], '%Y-%m-%d').date()
            except Exception:
                continue
        else:
            continue
        if d >= today:
            continue  # 还没到演出日，不动
        # 更新：去「（官宣未举办）」标记
        new_scene = scene.replace('（官宣未举办）', '').replace('（官宣待举办）', '').replace('官宣未举办', '').strip()
        scene_cell.value = new_scene
        note = str(note_cell.value or '')
        add = '已于%s完成；观众反馈见 live 页。' % d.strftime('%Y-%m-%d')
        if '已于' not in note:
            note_cell.value = (note + ' ' + add).strip()
        changed += 1
        print('更新场次: %s | %s -> %s' % (d, scene, new_scene))

    if changed:
        wb.save(LONG)
        print('长表已保存（备份: %s），更新 %d 行' % (bak.name, changed))
        if '--rebuild' in sys.argv:
            print('=== 触发大屏 rebuild（活动节点/辐射自动刷新 + push）===')
            r = subprocess.run([sys.executable, str(GEN), '--rebuild'])
            print('rebuild 退出码: %d' % r.returncode)
    else:
        print('无需更新（无已过演出日的「未举办」场次）')

if __name__ == '__main__':
    main()
