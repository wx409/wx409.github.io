# -*- coding: utf-8 -*-
"""把「口径标注 + 重算页链接」写进生成器模板与当前产物（幂等）。

为什么改生成器：dashboard/index.html 由 project_b 生成器每次重写并自动部署，
手工改仓库里的 index.html 会被下一次自动部署覆盖（2026-11-07 23:59 已发生一次）。
"""
import sys
from pathlib import Path

GEN = Path(r"D:\wx409.github.io\project_b\QQ音乐大屏生成器_GEO优化版_源码.py")
SRC_INDEX = Path(r"E:\wx\index_records\dashboard\index.html")

OLD_TITLE = '巡演带动效应（事件后7日 vs 基线，追踪曲目池日均指数涨幅%）'
NEW_TITLE = '巡演带动效应（曲目池口径：事件后 7 日 vs 21~7 日基线｜非「同场对照」，不可与重算结论混用）'
OLD_ES = '📉 事件研究曲线 · 演出后逐日效应（CAR 式，daily_series）'
NEW_ES = '📉 事件研究曲线 · 演出后逐日效应（仅 T+，缺前窗；规范版见「重算」页）'
INSIGHT = ('<p class="chart-insight">同场对照重算：演出当天至第 2 天 +7.0~7.9%（95% CI 0.8–14.7），'
           '第 7 天回到 0 附近（n=38–45 场）· <a href="analysis-v2.html" style="color:#5bc2e7">方法与口径敏感性</a></p>')


def patch(path: Path, is_generator: bool):
    text = path.read_text(encoding="utf-8")
    changed = []
    if OLD_TITLE in text:
        text = text.replace(OLD_TITLE, NEW_TITLE)
        changed.append("title")
    if OLD_ES in text:
        text = text.replace(OLD_ES, NEW_ES)
        changed.append("event-study-title")
    if "analysis-v2.html" not in text:
        # 在 tourFx 图表容器之后插入一行结论（模板里该行以 </div></div> 收尾）
        anchor = ('<div class="chart-container" id="tourFxChart" style="height:300px"></div></div>')
        if anchor in text:
            text = text.replace(anchor, anchor[:-6] + INSIGHT + "</div>")
            changed.append("insight")
    if changed:
        backup = path.with_suffix(path.suffix + ".bak_before_label")
        if not backup.exists():
            backup.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        path.write_text(text, encoding="utf-8")
    print(f"{path.name}: {', '.join(changed) if changed else '已是最新，跳过'}")
    return changed


def main():
    changed = patch(GEN, True)
    if changed:
        src = GEN.read_text(encoding="utf-8")
        try:
            compile(src, str(GEN), "exec")
            print("生成器语法 OK")
        except SyntaxError as e:
            print("生成器语法错误，回滚：", e)
            GEN.with_suffix(GEN.suffix + ".bak_before_label").replace(GEN)
            sys.exit(1)
    if SRC_INDEX.exists():
        patch(SRC_INDEX, False)


if __name__ == "__main__":
    main()
