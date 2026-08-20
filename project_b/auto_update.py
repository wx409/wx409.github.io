# -*- coding: utf-8 -*-
"""auto_update.py —— 王晰数字档案全链路编排器（无感更新）

流程（每步失败不阻塞后续，日志落 logs/）：
  1. watch（可选 --watch）：新歌/小酒馆 diff（只读，输出清单）
  2. 增量抓取：新 mid 的歌词+班底（fetch_credits_lyrics 增量模式）
  3. 构建：deploy_all.py（12 步，幂等）
  4. diff 检查：无变化则跳过发布
  5. 发布：git commit → push（本机凭据）→ IndexNow
  6. 日志：logs/auto_update_YYYYMMDD.log

用法：
  python project_b/auto_update.py --machine laptop|desktop --watch --no-push
  （--no-push 用于调试；默认全链路）
"""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"


def log(msg):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    line = "[%s] %s" % (ts, msg)
    print(line)
    LOGS.mkdir(exist_ok=True)
    with open(LOGS / ("auto_update_%s.log" % datetime.date.today().strftime("%Y%m%d")),
              "a", encoding="utf-8") as f:
        f.write(line + "\n")


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot():
    """关键数据文件快照（用于 diff 判断）"""
    files = ["data/dashboard_data.json", "data/songs_meta.json", "data/albums.json",
             "data/tavern_audio.json", "data/live_repos.json", "data/cities.json",
             "data/timeline.json", "data/site_search_index.json"]
    return {f: sha256_file(ROOT / f) for f in files if (ROOT / f).exists()}


def run(cmd, cwd=None):
    r = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True,
                       encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        log("!! %s 失败: %s" % (cmd[0], (r.stderr or r.stdout)[-300:]))
    return r.returncode == 0


def notify(title, msg):
    try:
        sys.path.insert(0, str(ROOT / "project_b"))
        import notify as nf
        nf.send(title or "📡 王晰数字档案", msg)
    except Exception as e:
        log("notify 失败: %s" % e)


def notify_digest():
    """汇总三个 watch 的新增结果，整合成 2 条推送：
    1 条「歌曲类」（QQ + 网易云新歌），1 条「消息类」（Bing 全渠道聚合）。
    无新增则不推该条；都无新增则跳过。"""
    releases = json.loads((ROOT / "data" / "pending_releases.json").read_text(encoding="utf-8")) \
        if (ROOT / "data" / "pending_releases.json").exists() else {}
    netease = json.loads((ROOT / "data" / "pending_netease.json").read_text(encoding="utf-8")) \
        if (ROOT / "data" / "pending_netease.json").exists() else {}
    web = json.loads((ROOT / "data" / "pending_web.json").read_text(encoding="utf-8")) \
        if (ROOT / "data" / "pending_web.json").exists() else {}

    # 歌曲类：QQ 正式作品 + 网易云新增
    qq = releases.get("releases", []) or []
    ne = netease.get("fresh", []) or []
    if qq or ne:
        lines = []
        for f in qq[:10]:
            lines.append("- %s（QQ，%s）" % (f.get("name"), f.get("album") or "单曲"))
        for f in ne[:10]:
            lines.append("- %s（网易云，%s）" % (f.get("name"), f.get("album") or "单曲"))
        n = len(qq) + len(ne)
        notify("🎵 王晰新歌 %d 首待确认" % n,
               "QQ + 网易云新增：\n" + "\n".join(lines)
               + ("\n…等共 %d 首" % n if n > 10 else "")
               + "\n\n已入库候选清单，歌词/班底将自动补充。")

    # 消息类：Bing 全渠道聚合新增
    wnew = web.get("new", []) or []
    if wnew:
        lines = "\n".join("- %s\n  %s" % (r.get("title"), r.get("url")) for r in wnew[:10])
        notify("📣 王晰动态聚合 %d 条新增（需确认）" % len(wnew),
               "全渠道(Bing索引)本日新增：\n" + lines
               + ("\n…等共 %d 条" % len(wnew) if len(wnew) > 10 else "")
               + "\n\n详情见 data/pending_web.json；确认后入库。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", choices=["laptop", "desktop"], default="laptop",
                    help="双机错峰：laptop 工作日 / desktop 周末")
    ap.add_argument("--watch", action="store_true", help="先跑 watch_releases/watch_tavern（只读）")
    ap.add_argument("--no-push", action="store_true", help="只构建不推送（调试）")
    args = ap.parse_args()

    # 双机错峰（复用 run_scheduler 模式）
    weekday = datetime.datetime.now().weekday()
    if args.machine == "laptop" and weekday >= 5:
        log("laptop 周末跳过（desktop 值班）")
        return
    if args.machine == "desktop" and weekday < 5:
        log("desktop 工作日跳过（laptop 值班）")
        return

    log("=== 开始自动更新（%s）===" % args.machine)
    before = snapshot()

    # 1. watch（新歌自动入库；小酒馆节目已结束，不再监测/推送）
    if args.watch:
        log("-- watch_releases (--apply 自动入库QQ新歌) --")
        run([sys.executable, str(ROOT / "project_b" / "watch_releases.py"), "--apply", "--no-notify"])
        log("-- watch_netease (--apply 自动入库网易云新歌) --")
        run([sys.executable, str(ROOT / "project_b" / "watch_netease.py"), "--apply", "--no-notify"])
        log("-- watch_web (Bing site: 聚合，只读) --")
        run([sys.executable, str(ROOT / "project_b" / "watch_web.py"), "--no-notify"])
        log("-- 汇总推送（歌曲类 + 消息类）--")
        notify_digest()

    # 2. 构建（deploy_all 自带敏感文件扫描；内部已含 commit）
    log("-- deploy_all --")
    ok = run([sys.executable, str(ROOT / "project_b" / "deploy_all.py")])
    if not ok:
        log("deploy_all 失败，终止发布")
        notify("⚠️ 自动更新失败：deploy_all 出错", "详情见 logs/ 目录")
        return

    # 3. 检查是否有未推送的 commit（deploy_all 内部已 commit，
    #    工作区恒为空，不能用 git status 判断，改用 rev-list 对比远端）
    if args.no_push:
        log("调试模式 --no-push，跳过发布")
        return
    r = subprocess.run(["git", "rev-list", "--count", "origin/main..HEAD"], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8")
    try:
        ahead = int((r.stdout or "").strip() or "0")
    except ValueError:
        ahead = 0
    if ahead == 0:
        log("无未推送提交，跳过 push/IndexNow")
        return
    log("检测到 %d 个未推送提交，执行 push" % ahead)

    # 4. 发布
    log("-- git push --")
    if not run(["git", "push", "origin", "main"]):
        log("push 失败（网络/凭据？），请手动 push")
        notify("⚠️ 自动更新失败：git push 未成功", "请手动执行 cd D:\\wx409.github.io && git push origin main")
        return
    log("-- IndexNow 通知 --")
    run([sys.executable, str(ROOT / "project_b" / "deploy_all.py"), "--notify-only"])
    # IndexNow 通知搜索引擎保留；但不再向 Server酱(微信)推送"更新完成"，
    # 以免占用 Server酱 免费推送名额（每日仅 5 条）。
    log("=== 完成 ===")


if __name__ == "__main__":
    main()
