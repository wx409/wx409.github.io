# -*- coding: utf-8 -*-
"""confirm_event.py —— 演出场次确认入库（人工确认后的唯一录入动作）

用法示例：
  python project_b/confirm_event.py --date 2026-09-20 --city 成都 --venue 成都城市音乐厅 --tour 六巡 --theme 回 --note 待定
  python project_b/confirm_event.py --date 2026-09-20 --city 成都 --venue 成都城市音乐厅 --tour 六巡 --cancelled

作用：
  1. 写入 data/cities.json（新增城市自动建条目）
  2. 重跑 live-reviews 生成器（该场自动出现为 pending 卡片，带 data-status）
  3. 提示后续：歌单/详细实录需长表或另行补充
注意：
  - 只写 cities.json（档案骨架）；歌单仍以长表为准
  - 取消场加 --cancelled 标记
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CITIES = ROOT / "data" / "cities.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", required=True, help="日期 YYYY-MM-DD")
    ap.add_argument("--city", required=True, help="城市")
    ap.add_argument("--venue", required=True, help="场馆")
    ap.add_argument("--tour", required=True, help="巡次，如 六巡")
    ap.add_argument("--theme", default="", help="主题，如 回")
    ap.add_argument("--scene", default="", help="场次名，如 成都（首场）；默认城市名")
    ap.add_argument("--note", default="", help="备注")
    ap.add_argument("--cancelled", action="store_true", help="标记为未举办/取消")
    ap.add_argument("--no-rebuild", action="store_true", help="只写数据不重建页面")
    args = ap.parse_args()

    cities = json.loads(CITIES.read_text(encoding="utf-8"))
    cc = cities.setdefault("cities", {}).setdefault(args.city, {"coord": None, "shows": []})
    if "shows" not in cc:
        cc["shows"] = []

    # 查重：同日期+同场馆不重复写入
    for s in cc["shows"]:
        if s.get("date") == args.date and s.get("venue") == args.venue:
            print("[!] 已存在同日期同场馆场次，跳过（%s %s）" % (args.date, args.venue))
            return

    show = {
        "date": args.date,
        "scene": args.scene or args.city,
        "note": args.note,
        "tour": args.tour,
        "tour_num": None,
        "theme": args.theme,
        "venue": args.venue,
        "live_url": None,
        "cancelled": args.cancelled,
    }
    cc["shows"].append(show)
    cities["show_count"] = sum(len(v.get("shows", [])) for v in cities["cities"].values())
    cities["city_count"] = len(cities["cities"])
    CITIES.write_text(json.dumps(cities, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[OK] 已写入 cities.json：%s %s %s（%s）" % (args.date, args.city, args.venue, args.tour))
    if args.cancelled:
        print("     （标记为未举办/取消）")

    if not args.no_rebuild:
        r = subprocess.run([sys.executable, str(ROOT / "project_b" / "build_live_reviews.py")])
        print("[OK] live-reviews.html 已重建，该场自动出现（pending 卡片）" if r.returncode == 0 else "[!] 重建失败")
        print("     歌单/详细实录需另行补充（长表或 live/ 页面）")


if __name__ == "__main__":
    main()
