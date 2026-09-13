# -*- coding: utf-8 -*-
"""私密入口 archive-index.html 生成器（瘦身 2.0 · 第四阶段）

archive-index.html = 瘦身前完整首页（`index.html@<快照引用>`）的**完整快照**
   + 头部一份「完整档案索引」目录（17 个旧页入口，保证旧页不退化为孤儿页）
   + `noindex, nofollow`（不进任何导航、不进 sitemap、不提交 IndexNow、不进 llms.txt）。

为什么从 git 快照取而不是复制当前 index.html：
  瘦身 2.0 之后 index.html 已是精简版，完整首页只存在于备份快照里。
  快照引用默认 `v1.0-full-20260913`（瘦身执行前打的标签），可用 --src 覆盖。

用法：
  python -X utf8 project_b/build_archive_index.py            # 生成/更新
  python -X utf8 project_b/build_archive_index.py --check     # 只检查
  python -X utf8 project_b/build_archive_index.py --src HEAD  # 换快照来源
"""
from __future__ import annotations

import argparse
import io
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "archive-index.html")
DEFAULT_SRC = "v1.0-full-20260913"

START = "<!-- ARCHIVE-INDEX:START（由 project_b/build_archive_index.py 生成，勿手改）-->"
END = "<!-- ARCHIVE-INDEX:END -->"
ROBOTS = '<meta name="robots" content="noindex, nofollow">'
TITLE = "完整档案索引（仅自己可见）| 王晰 GEO 数字档案站"
DESC = ("完整档案索引（仅本人查看）：旧页完整快照目录，不加入导航、不提交 IndexNow、"
        "不写入 sitemap。旧页内容一律保留完整快照，不删内容。")

GROUPS = [
    ("作品与歌曲", [
        ("discography.html", "作品百科：专辑/曲目/署名与试听线索（完整版）"),
        ("songs.html", "歌曲库：全量曲目与元数据（完整版）"),
    ]),
    ("现场与演出", [
        ("live-reviews.html", "现场实录：逐场观感与反馈（体量最大，完整版）"),
        ("live/setlists.html", "全部歌单：逐场歌单明细（完整版）"),
        ("stage.html", "🎤 现场实测（声乐实验区）：巡演/综艺双层现场音域实测"),
        ("map/index.html", "巡演地图：22 城 64 场交互地图（完整版）"),
        ("city-guides.html", "城市攻略：22 城观演指南（完整版）"),
        ("story-hui-guangzhou-2026.html", "六巡广州站单场数据复盘专题（完整版）"),
    ]),
    ("声学实测（声乐实验区）", [
        ("voice.html", "🎼 音域实测（声乐实验区）：72 曲录音室全量 + 跨素材精测"),
        ("skill.html", "🎙️ 唱功实测（声乐实验区）：七维实测 + 每日唱功卡片"),
        ("debate/index.html", "⚖️ 争议案例（实验区）：口径分歧的结构化陈列"),
    ]),
    ("生涯与文化", [
        ("timeline.html", "生涯时间轴（完整版）"),
        ("data-timeline.html", "数据时间线（完整版）"),
        ("culture/index.html", "文化足迹：对外交流/文旅/官方项目（完整版）"),
        ("academic.html", "学术研究：可核验文献（完整版）"),
        ("jazz.html", "爵士专题（完整版）"),
    ]),
    ("数据与工具", [
        ("dashboard/index.html", "数据大屏：指数趋势/当月榜单/档案层（完整版）"),
        ("tavern/index.html", "深夜小酒馆：现场逐字稿（完整版）"),
        ("gallery.html", "视觉记录：逐站图片记录（完整版）"),
        ("submit.html", "投稿入口（完整版）"),
        ("search.html", "全站检索（完整版，含知识库语义召回）"),
        ("notifications.html", "自动通知（完整版）"),
    ]),
]


def get_src(ref):
    r = subprocess.run(["git", "show", ref + ":index.html"], cwd=ROOT, capture_output=True)
    if r.returncode != 0:
        raise SystemExit("无法从 git 取出 %s:index.html —— %s" %
                         (ref, r.stderr.decode("utf-8", "replace")[:200]))
    return r.stdout.decode("utf-8")


def build_directory():
    parts = [START,
             '<div style="max-width:1000px;margin:0 auto;padding:18px 20px;">',
             '<h1 style="font-size:22px;margin:6px 0 4px;">完整档案索引（仅自己可见）</h1>',
             '<p style="font-size:13.5px;color:#666;line-height:1.8;margin:6px 0">'
             '本页是<strong>私密入口</strong>：不加入任何导航、不提交 IndexNow、不写入 sitemap，'
             '仅供作者本人查看。<br>旧页内容一律保留<strong>完整快照</strong>，不删内容；'
             '精简版 7 页为对外主入口。日常通过书签访问本页。</p>']
    for gname, items in GROUPS:
        lis = "".join(f'<li style="margin:3px 0"><a href="/{p}">{p}</a> — {d}</li>' for p, d in items)
        parts.append(f'<h2 style="font-size:16px;margin:16px 0 6px;padding-left:8px;'
                     f'border-left:3px solid #b8912e;">{gname}</h2>')
        parts.append('<ul style="margin:4px 0;padding-left:22px;font-size:14px;line-height:1.9">'
                     + lis + "</ul>")
    parts.append('<p style="font-size:13px;color:#888;margin-top:16px">'
                 '对外主入口（精简版 7 页）：<a href="/index.html">首页</a> · '
                 '<a href="/works.html">作品</a> · <a href="/live.html">现场</a> · '
                 '<a href="/vocal.html">声音数据</a> · <a href="/history.html">生涯</a> · '
                 '<a href="/research.html">研究</a> · <a href="/community.html">参与</a></p>')
    parts.append("</div>")
    parts.append(END)
    return "\n".join(parts)


def transform(src):
    txt = re.sub(r'<meta[^>]+name=["\']robots["\'][^>]*>\s*', "", src, flags=re.I)
    m = re.search(r"<head[^>]*>", txt, re.I)
    if not m:
        raise SystemExit("源页面没有 <head>")
    txt = txt[:m.end()] + "\n" + ROBOTS + txt[m.end():]
    txt = re.sub(r"<title>.*?</title>", "<title>" + TITLE + "</title>", txt, count=1,
                 flags=re.S | re.I)
    if re.search(r'<meta[^>]+name=["\']description["\'][^>]*>', txt, re.I):
        txt = re.sub(r'<meta[^>]+name=["\']description["\'][^>]*>',
                     '<meta name="description" content="' + DESC + '">', txt, count=1, flags=re.I)
    block = build_directory()
    if START in txt and END in txt:
        txt = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _m: block, txt,
                     count=1, flags=re.S)
    else:
        anchor = "<!-- NAV_END -->"
        if anchor in txt:
            i = txt.index(anchor) + len(anchor)
            txt = txt[:i] + "\n" + block + txt[i:]
        else:
            b = re.search(r"<body[^>]*>", txt, re.I)
            txt = txt[:b.end()] + "\n" + block + txt[b.end():]
    return txt


def main():
    ap = argparse.ArgumentParser(description="私密入口 archive-index.html 生成器")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--src", default=DEFAULT_SRC, help="git 快照引用（默认 %s）" % DEFAULT_SRC)
    args = ap.parse_args()

    out = transform(get_src(args.src))
    old = io.open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
    if old == out:
        print("[OK] archive-index.html 已一致（%d 字节，源 index.html@%s）" % (len(out), args.src))
        return 0
    if args.check:
        print("[FAIL] archive-index.html 需重建（当前 %d → 目标 %d 字节）" % (len(old), len(out)))
        return 1
    io.open(OUT, "w", encoding="utf-8").write(out)
    print("[OK] 已生成 archive-index.html（%d 字节，源 index.html@%s）" % (len(out), args.src))
    return 0


if __name__ == "__main__":
    sys.exit(main())
