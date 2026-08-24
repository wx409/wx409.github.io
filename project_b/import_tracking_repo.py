# -*- coding: utf-8 -*-
"""一次性：把 演出实时追踪报告 里的观众 repo 接入网站（live_repos.json → live-reviews.html）
读 temp\演出追踪_20260823\实时反馈_手动收集.md，解析「微博」观众条目，
追加到 data/live_repos.json 的 2026-08-23，再重建 live-reviews.html。

规则：
- 跳过官方号（王晰本人 uid 1292815744 → 已在站内纯文字呈现，不入 repo 链接）
- title 格式：@作者：正文前 40 字（可读 + 可复核）
- level=single（单源观众），platform=微博
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(r"D:\wx409.github.io")
REPORT = ROOT / "temp" / "演出追踪_20260823" / "实时反馈_手动收集.md"
REPOS_JSON = ROOT / "data" / "live_repos.json"
SHOW_DATE = "2026-08-23"

# 官方号 uid（王晰本人 1292815744 / 工作室 7215995153）不入观众 repo
OFFICIAL_UIDS = {"1292815744", "7215995153"}

PAT = re.compile(r"^- \[(?P<user>[^\]]+)\]\(https://weibo\.com/(?P<uid>\d+)/(?P<mid>\d+)\) · (?P<time>[^：]+)：(?P<text>.*)$")


def strip_weibo_link(t):
    """去正文里的 #话题# 与链接尾巴，截短"""
    t = re.sub(r"#\S+#", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:40] + ("…" if len(t) > 40 else "")


def main():
    if not REPORT.exists():
        print("报告不存在:", REPORT)
        return
    lines = REPORT.read_text(encoding="utf-8").splitlines()
    seen = set()
    new_items = []
    for ln in lines:
        m = PAT.match(ln.strip())
        if not m:
            continue
        uid = m.group("uid")
        if uid in OFFICIAL_UIDS:
            continue
        mid = m.group("mid")
        if mid in seen:
            continue
        seen.add(mid)
        user = m.group("user")
        text = strip_weibo_link(m.group("text"))
        title = f"@%s：%s" % (user, text) if text else f"@%s 的现场repo" % user
        new_items.append({
            "title": title,
            "platform": "微博",
            "url": f"https://weibo.com/{uid}/{mid}",
            "level": "single",
        })

    if not new_items:
        print("报告中无观众 repo（全部官方或已存在？）")
        return

    # 读现有 repos，去重后合并
    data = json.loads(REPOS_JSON.read_text(encoding="utf-8"))
    existing = data["repos"].get(SHOW_DATE, [])
    exist_urls = {r.get("url") for r in existing}
    added = [it for it in new_items if it["url"] not in exist_urls]
    if not added:
        print("所有条目已存在，无需追加")
        return
    data["repos"][SHOW_DATE] = existing + added
    data["_meta"]["checked"] = "2026-08-24"
    REPOS_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"追加 {len(added)} 条观众 repo -> {SHOW_DATE}")

    # 重建 live-reviews.html
    import subprocess
    r = subprocess.run([sys.executable, "-X", "utf8",
                        str(ROOT / "project_b" / "build_live_reviews.py")], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    print(r.stdout.strip() or r.stderr.strip())
    print("完成。下一步: git add/commit/push + IndexNow")


if __name__ == "__main__":
    main()
