# -*- coding: utf-8 -*-
"""完整档案索引页 + 本地链接登记（2026-09-13 重写）

产出两件东西：

1. `archive-index.html`（站点）——**纯分类链接索引**，不内嵌任何页面正文副本。
   机器人策略：`noindex, nofollow`（私密索引页，不进 sitemap、不提交 IndexNow、不进主导航）。
   旧版是「瘦身前首页整页快照」（151KB，含整页正文与统计表），维护两份内容本身就是隐患；
   现改为 <15KB 的纯链接页——正文只此一份、在原页。

2. `docs/链接登记.md`（本地）——**全部链接留在本地**，每个 URL 附用途与收录状态，
   以后知道链接也能直接查看。

用法：
  python -X utf8 project_b/build_archive_index.py            # 生成/更新
  python -X utf8 project_b/build_archive_index.py --check     # 只检查
"""
from __future__ import annotations

import argparse
import html
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "project_b"))
from build_nav import render_nav, render_footer  # noqa: E402  导航单一事实源

SITE = "https://wx409.github.io"
OUT = os.path.join(ROOT, "archive-index.html")
REGISTRY = os.path.join(ROOT, "docs", "链接登记.md")
ROBOTS = '<meta name="robots" content="noindex, nofollow">'
TITLE = "完整档案索引（仅自己可见）| 王晰 GEO 数字档案站"
DESC = ("完整档案索引（仅本人查看）：全部页面的分类链接，"
        "不加入主导航、不提交 IndexNow、不写入 sitemap。")

# (分类, [(路径, 一句说明)])
GROUPS = [
    ("对外主入口（精简版 7 页 · 有主导航位）", [
        ("index.html", "王晰是谁 + 全站检索入口 + 可引用统计表"),
        ("works.html", "他发布了什么作品（72 首逐曲稳定音/跨度/稳定性/颤音）"),
        ("live.html", "他在哪里唱过什么、唱得怎么样（场次/城市/三层现场实测）"),
        ("vocal.html", "他的声音数据是什么（最低稳定音、方法学、动态范围、同管线对照）"),
        ("history.html", "按时间顺序发生了什么（生涯时间轴 + 语录档案）"),
        ("research.html", "外部研究 + 数据证据（文献、权威点评、口径登记表）"),
        ("community.html", "访客参与入口（投稿、勘误、观感索引、问答库入口）"),
    ]),
    ("内容档案（仍对外可见、仍被索引与推送）", [
        ("live-reviews.html", "现场实录：逐场观感与反馈（体量最大）"),
        ("discography.html", "作品百科：专辑/曲目/署名与试听线索"),
        ("songs.html", "歌曲库：全量曲目与元数据"),
        ("live/setlists.html", "全部歌单：逐场歌单明细"),
        ("live/", "演出详情目录：各城市场次独立页"),
        ("city-guides.html", "城市攻略：22 城观演指南"),
        ("map/", "巡演地图：22 城 64 场交互地图"),
        ("culture/index.html", "文化足迹：对外交流/文旅/官方项目"),
        ("timeline.html", "生涯时间轴"),
        ("data-timeline.html", "数据时间线"),
        ("story.html", "数据故事"),
        ("story-hui-guangzhou-2026.html", "六巡广州站单场数据复盘专题"),
        ("notifications.html", "自动通知"),
        ("gallery.html", "视觉记录：逐站图片记录"),
        ("jazz.html", "爵士专题"),
        ("tavern/", "深夜小酒馆：现场逐字稿"),
        ("submit.html", "投稿入口"),
    ]),
    ("声学实测（声乐实验区）", [
        ("voice.html", "音域实测：72 曲录音室全量 + 跨素材精测"),
        ("stage.html", "现场实测：王晰主导巡演 + 他人主导舞台双层"),
        ("skill.html", "唱功实测：七维实测 + 每日唱功卡片 + 同管线横向对照"),
        ("dashboard/index.html", "数据大屏：指数趋势/当月榜单/档案层"),
    ]),
    ("可引用资产", [
        ("qa.html", "问答库：315 条问答对（真实 HTML + FAQPage，GEO 可引用）"),
        ("academic.html", "学术研究：46 条可核验文献 + 权威点评著录"),
        ("data/calibers.md", "口径登记表：全站数字字典（引用任何数字前必查）"),
        ("data/kb/kb_digest.md", "知识库摘要"),
        ("llms.txt", "面向 AI 的摘要文件"),
        ("feed.xml", "RSS 订阅"),
    ]),
    ("实验区与工具（noindex，刻意不收录）", [
        ("debate/index.html", "争议案例索引：口径分歧的结构化陈列"),
        ("debate/xiangzhe-taiyang-lowest.html", "案例 1：《向着太阳》最低音之争"),
        ("search.html", "全站检索（含知识库语义召回，支持 ?q= 直达）"),
        ("kb-semantic.html", "知识库语义检索旧入口（noindex，保书签兼容）"),
        ("about.html", "关于本站"),
    ]),
]

# 本地登记表补充：站点级文件
REG_EXTRA = [
    ("archive-index.html", "完整档案索引（本页，私密）", "不推送"),
    ("sitemap.xml", "站点地图（对外页全量）", "推送"),
    ("robots.txt", "爬虫规则", "—"),
    ("404.html", "404 页", "不收录"),
]


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def page_html():
    parts = ['<!DOCTYPE html>', '<html lang="zh-CN">', '<head>', '<meta charset="UTF-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
             f'<title>{esc(TITLE)}</title>', ROBOTS,
             f'<meta name="description" content="{esc(DESC)}">',
             '<style>',
             ':root{--red:#c41e3a;--gold:#b8912e;--ink:#222;--sub:#6b6b6b;--line:#e6e2da;--bg:#fffdf8}',
             'body{margin:0;background:var(--bg);color:var(--ink);line-height:1.8;font-size:15px;'
             "font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif}",
             '.wrap{max-width:900px;margin:0 auto;padding:18px 20px 8px}',
             'h1{font-size:21px;margin:8px 0 4px}',
             'h2{font-size:15px;margin:18px 0 6px;padding-left:8px;border-left:3px solid var(--gold)}',
             'ul{margin:4px 0;padding-left:20px}li{margin:3px 0}',
             'a{color:var(--red);text-decoration:none}a:hover{text-decoration:underline}',
             '.sub{color:var(--sub);font-size:13px}',
             'code{background:#f5f0e6;padding:1px 5px;border-radius:3px;font-size:13px}',
             'footer.site-index{max-width:900px;margin:28px auto;padding:16px 18px;'
             'border-top:1px solid var(--line);font-size:13px;color:#666;line-height:2}',
             '</style>', '</head>', '<body>', render_nav(), '<div class="wrap">',
             '<h1>完整档案索引（仅自己可见）</h1>',
             '<p class="sub">本页是<b>私密索引页</b>：不加入主导航、不提交 IndexNow、不写入 sitemap。<br>'
             '全部页面的正文都在各自原页，本页<b>不复制任何正文</b>——只有链接与一句说明。<br>'
             '页面本身仍对外可达（不做访问限制），但 noindex：搜索引擎不会收录本索引页。</p>']
    for gname, items in GROUPS:
        parts.append(f'<h2>{esc(gname)}</h2>')
        parts.append('<ul>')
        for path, desc in items:
            parts.append(f'<li><a href="/{esc(path)}">{esc(path)}</a> — {esc(desc)}</li>')
        parts.append('</ul>')
    parts.append('<p class="sub">维护：本页由 <code>project_b/build_archive_index.py</code> 生成；'
                 '本地链接登记见 <code>docs/链接登记.md</code>（含收录状态与用途）。</p>')
    parts += ['</div>', render_footer(), '</body>', '</html>', '']
    return "\n".join(parts)


def registry_md():
    out = ['# 链接登记（本地）', '',
           '> 全部链接留在本地，以后知道链接也能直接查看。',
           '> 由 `project_b/build_archive_index.py` 生成，与 `archive-index.html` 同源。', '',
           '站点根：`' + SITE + '/`', '',
           '| 分类 | 路径 | 完整 URL | 用途 | 收录 / 推送 |', '|---|---|---|---|---|']
    for gname, items in GROUPS:
        if '主入口' in gname:
            push = 'index,follow · 在 sitemap · 推送 IndexNow（有主导航位）'
        elif '实验区' in gname:
            push = '不推送（noindex / 私密）'
        else:
            push = 'index,follow · 在 sitemap · 推送 IndexNow'
        for path, desc in items:
            out.append(f'| {gname} | `{path}` | {SITE}/{path} | {desc} | {push} |')
    for path, desc, push in REG_EXTRA:
        url = f'{SITE}/{path}'
        out.append(f'| 站点级 | `{path}` | {url} | {desc} | {push} |')
    out += ['', '## 刻意不收录的两类', '',
            '- `archive-index.html`（本索引页）：私密页，noindex,nofollow，不进 sitemap、不推送。',
            '- `debate/`（实验区）与 `kb-semantic.html`：noindex，成熟后再迁入可索引区。', '',
            '## 说明', '',
            '- 「不展示」≠「不收录」：完整档案页不占主导航位，但**仍被索引、仍在 sitemap、仍推送 IndexNow**，',
            '  并在每页底部全站索引里有直连入口（人点得到、爬虫也走得到）。',
            '- 站点级文件 `data/calibers.md`、`data/kb/kb_digest.md`、`llms.txt` 同时进 sitemap 与推送。', '']
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description="完整档案索引页 + 本地链接登记")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    targets = [(OUT, page_html()), (REGISTRY, registry_md())]
    drift = []
    for path, content in targets:
        old = io.open(path, encoding="utf-8").read() if os.path.exists(path) else ""
        if old == content:
            print("  %-30s 已一致 ✅ (%d 字节)" % (os.path.relpath(path, ROOT), len(content.encode("utf-8"))))
            continue
        drift.append(os.path.relpath(path, ROOT))
        if args.check:
            print("  %-30s 需更新" % os.path.relpath(path, ROOT))
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            io.open(path, "w", encoding="utf-8").write(content)
            print("  %-30s 已生成 (%d 字节)" % (os.path.relpath(path, ROOT), len(content.encode("utf-8"))))
    if args.check and drift:
        print("\n[FAIL] %d 个文件漂移：%s" % (len(drift), ", ".join(drift)))
        return 1
    print("\n[OK] 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
