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


def _record(category, title, content, source="", url=""):
    """只写本地通知表，供 notifications.html 做细粒度聚合展示。"""
    try:
        sys.path.insert(0, str(ROOT / "project_b"))
        import notify as nf
        nf.record(title, content, category=category, source=source, url=url)
    except Exception as e:
        log("本地通知记录失败: %s" % e)


def notify_digest():
    """把 watch 结果按来源/条目写入本地通知表，供网页端聚合展示。

    不再受 Server酱条数限制，因此可以记录到更细的粒度：
    - QQ 新歌
    - 网易云新歌
    - Bing/全网动态
    """
    releases = json.loads((ROOT / "data" / "pending_releases.json").read_text(encoding="utf-8")) \
        if (ROOT / "data" / "pending_releases.json").exists() else {}
    netease = json.loads((ROOT / "data" / "pending_netease.json").read_text(encoding="utf-8")) \
        if (ROOT / "data" / "pending_netease.json").exists() else {}
    web = json.loads((ROOT / "data" / "pending_web.json").read_text(encoding="utf-8")) \
        if (ROOT / "data" / "pending_web.json").exists() else {}

    # QQ 新歌
    qq = releases.get("releases", []) or []
    for f in qq[:50]:
        name = f.get("name") or ""
        album = f.get("album") or "单曲"
        url = f.get("url") or ""
        _record("QQ新歌", "🎵 QQ新歌 · %s" % name,
                "专辑/单曲：%s\n已写入候选清单，后续自动补歌词/班底。" % album,
                source="QQ音乐", url=url)

    # 网易云新歌
    ne = netease.get("fresh", []) or []
    for f in ne[:50]:
        name = f.get("name") or ""
        album = f.get("album") or "单曲"
        url = f.get("url") or ""
        _record("网易云新歌", "🎵 网易云新歌 · %s" % name,
                "专辑/单曲：%s\n已写入候选清单，后续自动补歌词/班底。" % album,
                source="网易云", url=url)

    # Bing/全网动态
    wnew = web.get("new", []) or []
    for r in wnew[:100]:
        title = r.get("title") or "全网动态"
        url = r.get("url") or ""
        snippet = (r.get("snippet") or r.get("summary") or "")[:200]
        _record("全网动态", "📣 %s" % title,
                snippet + ("\n链接：%s" % url if url else ""),
                source="Bing聚合", url=url)

    total = len(qq) + len(ne) + len(wnew)
    if total:
        _record("汇总", "自动更新聚合完成",
                "本轮新增：QQ %d 首 / 网易云 %d 首 / 全网动态 %d 条" % (len(qq), len(ne), len(wnew)),
                source="auto_update")
    else:
        log("本轮无新增，不写本地通知明细。")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--machine", choices=["laptop", "desktop"], default="laptop",
                    help="机器标签（仅日志用）；不再做双机错峰，笔记本每天都执行")
    ap.add_argument("--watch", action="store_true", help="先跑 watch_releases/watch_tavern（只读）")
    ap.add_argument("--no-push", action="store_true", help="只构建不推送（调试）")
    args = ap.parse_args()

    # 说明：已取消双机错峰（此前 laptop 周末/desktop 工作日互相跳过）。
    # 现在统一由笔记本每天自动更新 + push + IndexNow，无需换班。
    log("=== 开始自动更新（%s，每天执行）===" % args.machine)
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
