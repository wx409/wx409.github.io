# -*- coding: utf-8 -*-
"""改名：分享作战室 → 素材与引用（全站文案统一、去掉「作战/素材包/粉丝」）。

范围：生成器（build_share_page / build_compact / build_nav / build_copy_usage_page /
deploy_all 注释）、页面（share.html / index.html / community.html）。
标题、JSON-LD name、H1、按钮文案、底部索引项、meta description 全部统一。
"""
from pathlib import Path

SITE = Path(r"D:\wx409.github.io")
OLD_NEW = [
    ("🎁 给粉丝的素材包 → 分享作战室", "素材与引用 →"),
    ("给粉丝的素材包 → 分享作战室", "素材与引用 →"),
    ("给粉丝的素材包", "素材与引用"),
    ("分享作战室", "素材与引用"),
    ("🧰 素材与引用", "素材与引用"),
    ("分享作战室", "素材与引用"),
]
FILES = [SITE / "project_b" / "build_share_page.py", SITE / "project_b" / "build_compact.py",
         SITE / "project_b" / "build_nav.py", SITE / "project_b" / "build_copy_usage_page.py",
         SITE / "project_b" / "deploy_all.py"]
PAGES = [SITE / "share.html", SITE / "index.html", SITE / "community.html"]

changed = []
for p in FILES + PAGES:
    if not p.exists():
        continue
    t = p.read_text(encoding="utf-8")
    o = t
    for a, b in OLD_NEW:
        t = t.replace(a, b)
    # 去掉残留 emoji 与「素材包」字眼
    t = t.replace("🎁", "").replace("素材包", "素材").replace("粉丝的素材", "素材")
    if t != o:
        p.write_text(t, encoding="utf-8")
        changed.append(p.name)

print("[已改名]", changed)
