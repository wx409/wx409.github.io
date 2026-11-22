#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xhs_comments_slow.py —— 低速逐篇抓小红书评论（每篇间隔 120 秒，避开 300013 风控）"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
TOOL = Path(r"E:\wx\私有工具\xhs_proxy\xhs_comments.py")
LINKS = Path(r"E:\wx\私有工具\xhs_comments_links.txt")
OUTROOT = Path(r"E:\wx\私有工具\xhs_comments_slow")
TMP = Path(r"E:\wx\私有工具\xhs_comments_slow_tmp.txt")
PUB = ROOT / "data" / "xhs_comments.json"
SLEEP_OK, SLEEP_FAIL = 120, 240


def main():
    links = [x.strip() for x in LINKS.read_text(encoding="utf-8").splitlines() if x.strip()]
    OUTROOT.mkdir(parents=True, exist_ok=True)
    results = []
    for i, url in enumerate(links, 1):
        out = OUTROOT / ("n%02d" % i)
        jf = out / "comments.json"
        if jf.exists():
            try:
                d = json.loads(jf.read_text(encoding="utf-8"))
                if d.get("n_ok"):
                    results.append(d)
                    print(i, "cached", d.get("n_out_total"), flush=True)
                    continue
            except Exception:
                pass
        TMP.write_text(url + "\n", encoding="utf-8")
        print(i, "fetch", url[:80], flush=True)
        r = subprocess.run([sys.executable, "-X", "utf8", str(TOOL), "--file", str(TMP),
                            "--out", str(out), "--inner", "0", "--max-out", "100"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        ok = False
        if jf.exists():
            try:
                d = json.loads(jf.read_text(encoding="utf-8"))
                if d.get("n_ok"):
                    results.append(d)
                    ok = True
                    print(i, "ok", d.get("n_out_total"), flush=True)
            except Exception:
                pass
        if not ok:
            print(i, "fail", (r.stdout or "")[-160:].replace("\n", " "), flush=True)
        time.sleep(SLEEP_OK if ok else SLEEP_FAIL)

    vids = []
    for d in results:
        for n in d.get("notes") or []:
            cs = n.get("comments") or []
            def likes(c):
                try:
                    return int(str(c.get("like_count") or 0).replace("万", "0000"))
                except Exception:
                    return 0
            top = [c.get("content", "")[:60] for c in sorted(cs, key=lambda x: -likes(x))[:5]]
            vids.append({"id": n.get("note_id"), "title": n.get("title_from_list") or "", "count": len(cs), "top": top})
    PUB.write_text(json.dumps({"generated_at": time.strftime("%Y-%m-%d %H:%M"), "videos": vids}, ensure_ascii=False, indent=1), encoding="utf-8")
    print("合计", len(vids), "篇 /", sum(v["count"] for v in vids), "条 →", PUB)


if __name__ == "__main__":
    main()
