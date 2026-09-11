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

# 强制 stdout/stderr 走 UTF-8：计划任务环境默认 GBK 控制台，遇到 ▶ 等符号会
# 抛 UnicodeEncodeError 导致整条链路中止（2026-08-17 8:49 曾因此崩溃）。
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# (脚本路径, 说明, 是否关键) —— 关键脚本失败则中止
STEPS = [
    (r"E:\wx\私有工具\generate_cities_json.py", "地图 cities.json + map/index.html", True),
    (ROOT / "generate_tour_index.py", "巡演目录 live/index.html", True),
    (ROOT / "update_index_table.py", "首页表格（效应注入）", True),
    (ROOT / "project_b" / "build_home.py", "首页动态槽（最新场次摘要卡）", False),
    (ROOT / "project_b" / "inject_vocal_summary.py", "首页音域摘要块（从实测 JSON 派生，禁手写）", True),
    (ROOT / "project_b" / "inject_index_facts.py", "首页事实块（轮次/城市/覆盖天数/Last updated 派生）", True),
    (ROOT / "project_b" / "build_entity_index.py", "跨站关系 entity_index.json", True),
    (ROOT / "project_b" / "build_kb_graph.py", "知识库三层 data/kb/*.json", True),
    (ROOT / "tools" / "build_kb_vectors.py", "知识库语义索引 data/kb/semantic/*（需sentence-transformers，缺依赖仅警告）", False),
    (ROOT / "tools" / "build_qa_page.py", "问答库静态页 qa.html（GEO 可引用）", True),
    (ROOT / "project_b" / "build_setlists.py", "歌单 data/setlists.json（全站 64 场 = 巡演 59 + 签唱会 5）", True),
    (ROOT / "project_b" / "build_songs_meta.py", "歌曲元数据 data/songs_meta.json", True),
    (ROOT / "project_b" / "build_songs_page.py", "歌曲库页 songs.html", True),
    (ROOT / "project_b" / "build_setlists_page.py", "歌单索引页 live/setlists.html", True),
    (ROOT / "project_b" / "generate_city_guides.py", "22 城攻略 data/city_guides.json", True),
    (ROOT / "project_b" / "build_story.py", "数据故事 story.html", True),
    (ROOT / "project_b" / "build_academic.py", "学术研究页 academic.html（读 data/literature.json）", False),
    (ROOT / "project_b" / "verify_album_dates.py", "专辑发行日期 QQ 音乐核验（回写 release_date 精确日期）", False),
    (ROOT / "project_b" / "auto_new_song_vocal.py", "新歌入声学记录（发现→待测→下载→实测，无新歌秒退）", False),
    (ROOT / "project_b" / "refresh_vocal_pages.py", "音域三页数据同步（输入有变化才跑生产脚本，幂等）", False),
    (ROOT / "project_b" / "build_skill_card.py", "每日唱功卡片 data/skill_cards.json + 本地传记素材归档", False),
    (ROOT / "project_b" / "build_stage_page.py", "现场音域双层页 stage.html（王晰主导巡演现场 + 他人主导舞台）", False),
    (r"E:\wx\论文素材_王晰作传\基线口径\generate_voice_page.py", "声部·音域页 voice.html（读 data/archive_vocal.json）", False),
    (ROOT / "project_b" / "build_skill_page.py", "唱功实测页 skill.html（七维实测 + 今日唱功卡片）", False),
    (ROOT / "project_b" / "track_event_lifecycle.py", "活动生命周期追踪（官宣/开票/开演的指数前后窗口）", False),
    (ROOT / "project_b" / "elevator_definition.py", "电梯定义句（首页/问答库/llms/Person 单一事实源）", True),
    (ROOT / "project_b" / "build_calibers.py", "口径登记表 data/calibers.json+md（数字字典，禁混用）", True),
    (r"E:\wx\论文素材_王晰作传\基线口径\generate_llms.py", "llms.txt（计数从各 manifest 自动派生，禁手写）", True),
    (ROOT / "tavern" / "_build_episodes.py", "小酒馆逐字稿页", True),
    (ROOT / "tavern" / "_build_songs_compact.py", "小酒馆歌曲索引", False),
    (ROOT / "project_b" / "build_music_index.py", "音乐数据周报", False),
    (ROOT / "project_b" / "build_feed.py", "Atom Feed feed.xml", False),
    (ROOT / "project_b" / "build_nav.py", "导航单一事实源（顶部导航+底部全站索引，幂等）", True),
    (ROOT / "project_b" / "update_sitemap_lastmod.py", "sitemap.xml lastmod 按 git 自动回填（禁手写日期）", True),
    (ROOT / "project_b" / "audit_nav.py", "导航与内链审计（孤儿页=0 把关）", False),
    (ROOT / "project_b" / "audit_jsonld.py", "结构化数据审计（JSON-LD 语法/必备类型/纪律用词）", False),
    (ROOT / "project_b" / "audit_bat.py", "批处理体检（GBK/BEL/双回车/goto 目标）", False),
    (ROOT / "project_b" / "audit_ops_coverage.py", "操作中心覆盖审计（人工功能都有菜单入口）", False),
    (ROOT / "project_b" / "build_pipeline_views.py", "任务视图刷新（install_tasks.ps1 / 任务登记表 / skill 任务表）", False),
    (ROOT / "project_b" / "audit_pipeline.py", "任务一致性审计（登记表 vs 部署 vs 菜单 vs 计划任务，漂移告警）", False),
    (ROOT / "project_b" / "check_index_integrity.py", "指数数据源完整性守卫（防回退到缺陷版构建）", True),
    (ROOT / "project_b" / "audit_caliber.py", "口径审计（单一事实源一致性自检，末尾把关）", False),
    (ROOT / "project_b" / "audit_live.py", "线上核验（图片200+sha256对指纹+关键数字+黑名单；未推送/工作区脏自动 SKIP）",
     False, ["--skip-if-unpushed", "--skip-if-dirty"]),
]

COMMIT_MSG = "自动部署: 数据更新 ({ts})"

# IndexNow：部署后通知 Bing/Yandex 即时抓取（key 为公开验证文件，协议要求公开）
INDEXNOW_KEY_FILE = ROOT / "e3f1a2b4c5d6e7f8a9b0c1d2e3f4a5b6.txt"
INDEXNOW_URLS = [
    # 枢纽页：其中 sitemap.xml 会让引擎顺藤摸瓜覆盖全部详情页
    "https://wx409.github.io/",
    "https://wx409.github.io/sitemap.xml",
    "https://wx409.github.io/feed.xml",
    "https://wx409.github.io/entity_index.json",
    "https://wx409.github.io/search.html",
    # 常更新内容入口页（巡演讯息/反馈/新歌/新专辑）
    "https://wx409.github.io/live-reviews.html",
    "https://wx409.github.io/live/",
    "https://wx409.github.io/discography.html",
    "https://wx409.github.io/songs.html",
    "https://wx409.github.io/timeline.html",
    "https://wx409.github.io/data-timeline.html",
    "https://wx409.github.io/kb-semantic.html",
    "https://wx409.github.io/qa.html",
    "https://wx409.github.io/data/kb/kb_digest.md",
    "https://wx409.github.io/city-guides.html",
    # 声学实测页（voice/stage：数据类页，改动后单独推送）
    "https://wx409.github.io/voice.html",
    "https://wx409.github.io/stage.html",
    # 其他固定入口页
    "https://wx409.github.io/story.html",
    "https://wx409.github.io/about.html",
    "https://wx409.github.io/academic.html",
    "https://wx409.github.io/gallery.html",
    "https://wx409.github.io/jazz.html",
    "https://wx409.github.io/submit.html",
    "https://wx409.github.io/tavern/",
    "https://wx409.github.io/map/",
    "https://wx409.github.io/dashboard/",
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


def run(script, desc: str, critical: bool, extra: list[str] | None = None) -> bool:
    script = Path(script)
    print(f"\n{'=' * 60}\n▶ {desc}\n   {script}\n{'=' * 60}")
    r = subprocess.run([PY, "-X", "utf8", str(script), *(extra or [])], cwd=ROOT, capture_output=True, text=True,
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
    parser.add_argument("--notify-only", action="store_true",
                        help="只发送 IndexNow 通知（供 auto_update.py 发布后调用）")
    args = parser.parse_args()

    if args.notify_only:
        print("--- IndexNow 通知（notify-only）---")
        ok = notify_indexnow()
        print("通知完成 ✅" if ok else "通知失败（不影响站点）")
        return

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

    # 2. 顺序执行生成脚本（第 4 项为可选附加参数）
    for step in STEPS:
        script, desc, critical = step[0], step[1], step[2]
        extra = list(step[3]) if len(step) > 3 else []
        if not run(script, desc, critical, extra):
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
    print("  python -X utf8 project_b\\audit_live.py --wait 180   # 推送后等 Pages 构建窗口再核验")
    print("=" * 60)


if __name__ == "__main__":
    main()
