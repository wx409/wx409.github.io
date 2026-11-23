#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pick_moments.py —— 每周精选：一条命令标注 5 条，自动重建 moments

用法：
  python project_b/pick_moments.py --list          # 看编号
  python project_b/pick_moments.py q01 s03 m02 q07 s01
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
DATA = ROOT / "data" / "moments.json"
PICKS = ROOT / "data" / "moments_picks.json"


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    ids = []
    if "--list" in sys.argv:
        for kind, key, label in (("q", "quotes", "金句"), ("s", "screams", "现场"), ("m", "memes", "路人梗")):
            for x in d.get(key) or []:
                print(x.get("id"), "｜", (x.get("quote") or x.get("title") or "")[:60])
        return
    want = [x.strip() for x in sys.argv[1:] if x.strip()]
    if not want:
        print("用法：python project_b/pick_moments.py --list 或 q01 s03 m02 ...")
        return
    valid = {x.get("id") for k in ("quotes", "screams", "memes") for x in (d.get(k) or [])}
    bad = [x for x in want if x not in valid]
    if bad:
        print("无效编号：", "、".join(bad), "（先 --list）")
        return
    week = date.today().isocalendar()
    PICKS.write_text(json.dumps({"week": "%d-W%02d" % (week[0], week[1]), "picks": want}, ensure_ascii=False, indent=1), encoding="utf-8")
    subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "project_b" / "build_moments.py")], cwd=str(ROOT))
    subprocess.run(["git", "-C", str(ROOT), "add", "moments.html", "data/moments.json", "data/moments_picks.json"])
    r = subprocess.run(["git", "-C", str(ROOT), "commit", "-m", "content: 本周精选（%s）" % "、".join(want)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode == 0:
        subprocess.run(["git", "-C", str(ROOT), "push", "origin", "main"])
    print("本周精选：", "、".join(want))


if __name__ == "__main__":
    main()
