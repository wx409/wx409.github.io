#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一键部署流水线：长表/数据更新后，按序执行全部生成脚本并提交 git。

流程（与交接文档一致）：
  1. generate_cities_json.py    -> data/cities.json + map/index.html（地图）
  2. generate_tour_index.py     -> live/index.html（巡演目录，读长表）
  3. update_index_table.py      -> 首页表格（读 dashboard 效应）
  4. build_entity_index.py      -> entity_index.json（跨站关系图谱）
  5. build_city_guides.py       -> data/city_guides.json（22 城攻略，保留 web_tips）
  6. build_story.py             -> story.html（数据故事页）
  7. tavern/_build_episodes.py  -> tavern/ep/*.html（小酒馆逐字稿页）
  8. tavern/_build_songs_compact.py -> tavern/songs_compact.json
  9. build_music_index.py       -> data/music-index.*（音乐数据周报）
  10. git add/commit            -> 自动提交（推送需手动，沙箱限制）

用法：
  python project_b/deploy_all.py            # 完整部署（推荐）
  python project_b/deploy_all.py --no-git   # 只生成不提交（预览/调试）
  python project_b/deploy_all.py --commit "自定义提交信息"

完整说明文档：docs/deploy_all流水线使用说明.md
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# (脚本路径, 说明, 是否关键) —— 关键脚本失败则中止
STEPS = [
    (r"E:\wx\私有工具\generate_cities_json.py", "地图 cities.json + map/index.html", True),
    (ROOT / "generate_tour_index.py", "巡演目录 live/index.html", True),
    (ROOT / "update_index_table.py", "首页表格（效应注入）", True),
    (ROOT / "project_b" / "build_entity_index.py", "跨站关系 entity_index.json", True),
    (ROOT / "project_b" / "generate_city_guides.py", "22 城攻略 data/city_guides.json", True),
    (ROOT / "project_b" / "build_story.py", "数据故事 story.html", True),
    (ROOT / "tavern" / "_build_episodes.py", "小酒馆逐字稿页", True),
    (ROOT / "tavern" / "_build_songs_compact.py", "小酒馆歌曲索引", False),
    (ROOT / "project_b" / "build_music_index.py", "音乐数据周报", False),
    (ROOT / "project_b" / "build_feed.py", "Atom Feed feed.xml", False),
]

COMMIT_MSG = "自动部署: 数据更新 ({ts})"

# IndexNow：部署后通知 Bing/Yandex 即时抓取（key 为公开验证文件，协议要求公开）
INDEXNOW_KEY_FILE = ROOT / "e3f1a2b4c5d6e7f8a9b0c1d2e3f4a5b6.txt"
INDEXNOW_URLS = [
    "https://wx409.github.io/",
    "https://wx409.github.io/story.html",
    "https://wx409.github.io/sitemap.xml",
    "https://wx409.github.io/feed.xml",
    "https://wx409.github.io/entity_index.json",
    "https://wx409.github.io/tavern/",
    "https://wx409.github.io/map/",
    "https://wx409.github.io/dashboard/",
    "https://wx409.github.io/city-guides.html",
    "https://wx409.github.io/live-reviews.html",
    "https://wx409.github.io/culture/",
]


def notify_indexnow() -> bool:
    """通过 IndexNow 通知搜索引擎即时抓取（成功返回 True，失败警告不阻塞）。"""
    if not INDEXNOW_KEY_FILE.exists():
        print("[IndexNow] key 文件缺失，跳过")
        return False
    key = INDEXNOW_KEY_FILE.read_text(encoding="utf-8").strip()
    import urllib.request
    ok = 0
    for u in INDEXNOW_URLS:
        try:
            url = f"https://api.indexnow.org/indexnow?url={u}&key={key}"
            with urllib.request.urlopen(url, timeout=20) as resp:
                if resp.status == 200:
                    ok += 1
                else:
                    print(f"[IndexNow] {u} -> HTTP {resp.status}")
        except Exception as e:
            print(f"[IndexNow] {u} -> 失败: {str(e)[:80]}")
    print(f"[IndexNow] 已通知 {ok}/{len(INDEXNOW_URLS)} 个 URL")
    return ok > 0


def run(script, desc: str, critical: bool) -> bool:
    script = Path(script)
    print(f"\n{'=' * 60}\n▶ {desc}\n   {script}\n{'=' * 60}")
    r = subprocess.run([PY, "-X", "utf8", str(script)], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    # 输出可能含非 GBK 字符，写到日志
    log = ROOT / "temp" / "deploy_run.log"
    log.write_text(f"=== {script.name} ===\nstdout:\n{r.stdout}\nstderr:\n{r.stderr}\n", encoding="utf-8")
    if r.returncode != 0:
        print(f"[FAIL] {desc} 退出码 {r.returncode}，详见 {log}")
        if critical:
            return False
        print("[warn] 非关键步骤，继续…")
    else:
        print(f"[OK] {desc}")
    return True


def git(args: list[str]) -> bool:
    r = subprocess.run(["git"] + args, cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(f"[git] {' '.join(args)} 失败: {r.stderr.strip()[:300]}")
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="一键部署流水线")
    parser.add_argument("--commit", default=None, help="自定义 git commit 信息")
    parser.add_argument("--no-git", action="store_true", help="只跑生成，不提交")
    args = parser.parse_args()

    print(f"王晰 GEO 站 · 一键部署流水线\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 1. git 状态安全检查（敏感文件预警）
    r = subprocess.run(["git", "status", "--short"], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    status = r.stdout
    sensitive = [ln for ln in status.splitlines()
                 if any(k in ln.lower() for k in ("radio_proxy", "radio_cookie", "secrets", ".env", ".mp3", ".flac"))]
    if sensitive:
        print("\n[!] 警告：检测到敏感文件在工作区！")
        for s in sensitive:
            print("    ", s)
        print("[!] 中止部署，请先处理。")
        sys.exit(1)

    # 2. 顺序执行生成脚本
    for script, desc, critical in STEPS:
        if not run(script, desc, critical):
            print("\n[X] 流水线中止于关键步骤")
            sys.exit(2)

    # 3. git 提交
    if args.no_git:
        print("\n[--no-git] 跳过提交。")
        return
    msg = args.commit or COMMIT_MSG.format(ts=datetime.now().strftime("%m-%d %H:%M"))
    git(["add", "-A"])
    r = subprocess.run(["git", "commit", "-m", msg], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode == 0:
        print(f"\n[OK] 已提交: {msg}")
    else:
        print("\n[i] 无新变更或提交失败（未修改则属正常）")
        print("    ", r.stderr.strip()[:200])

    # 4. IndexNow 通知（部署后即时抓取，需本机能联网；失败不阻塞）
    print("\n--- IndexNow 通知 ---")
    notify_indexnow()

    # 5. 提醒手动 push（沙箱无法 ssh）
    print("\n" + "=" * 60)
    print("流水线完成 ✅")
    print("下一步（手动，沙箱限制 ssh）:")
    print("  cd D:\\wx409.github.io")
    print("  git push origin main")
    print("=" * 60)


if __name__ == "__main__":
    main()
