# -*- coding: utf-8 -*-
"""生成站内「使用说明（四件套）」页，并把「①d 一键成稿」区与顶部链接接进 share.html。

- 页面：`使用说明-四件套.html`（从 `data/share/copy_pipeline.json` 的 usage 段与固定纪律渲染，
  数字/规则均派生；不写死统计）
- share.html：在 ①d 区已由 build_share_page.py 插入片段；本脚本负责补**顶部一行链接**（幂等）
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
OUT = SITE / "使用说明-四件套.html"


def main() -> int:
    cp = json.loads((D / "share" / "copy_pipeline.json").read_text(encoding="utf-8"))
    st = cp.get("style") or {}
    c = (st.get("constraints") or {})
    items = cp.get("items") or []
    H = ["<!DOCTYPE html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\">",
         "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">",
         "<title>使用说明 · 四件套（小红书/微博/抖音/传记体）</title>",
         "<link rel=\"canonical\" href=\"https://wx409.github.io/使用说明-四件套.html\">",
         "<style>body{font:15px/1.7 -apple-system,Segoe UI,Microsoft YaHei,sans-serif;max-width:860px;"
         "margin:24px auto;padding:0 16px;color:#222}h1{font-size:1.5em}h2{margin-top:1.6em;font-size:1.15em}"
         "pre{white-space:pre-wrap;background:#fafafa;border:1px solid #eee;padding:10px;border-radius:6px}"
         ".meta{color:#666;font-size:.9em}code{background:#f2f2f2;padding:1px 4px;border-radius:3px}"
         "</style></head><body>",
         "<!-- NAV_START --><!-- NAV_END -->",
         "<h1>使用说明 · 四件套</h1>",
         f"<p class=\"meta\">生成 {datetime.now():%Y-%m-%d}｜数据源 <code>data/share/copy_pipeline.json</code>"
         f"｜人味标尺来自真语料 {st.get('n_posts')} 条笔记 / {st.get('n_comments')} 条评论"
         f"｜<b>只预览，不自动发布</b></p>",
         "<h2>① 从哪里打开</h2><ul>",
         "<li>站内：<a href=\"share.html\">share.html</a> →「①d 一键成稿」区（本页从同一区链出）</li>",
         "<li>本地：<code>data/share/rendered/copy_pipeline.html</code>"
         "（数据 <code>data/share/copy_pipeline.json</code>）</li>",
         "<li>人味标尺：<code>data/share/copy_style.json</code>（由 <code>project_b/copy_style_audit.py</code> 统计）</li></ul>",
         "<h2>② 三步</h2><ol>",
         "<li><b>勾选</b>：<code>data/hooks_pick.json</code> 把目标钩子 <code>picked</code> 设 true"
         "（或跑 <code>hook_miner.py --render-picked</code>）</li>",
         "<li><b>预览</b>：<code>python -X utf8 project_b/build_copy_pipeline.py</code> → 打开上面两个入口</li>",
         "<li><b>复制</b>：先改掉所有 <code>〔你来补：…〕</code>，再整段复制发布（<b>不要不改就发</b>）</li></ol>",
         "<h2>③ 改完后自检 5 条</h2><ol>",
         "<li>去掉 AI 句式（不仅…而且／值得一提的是／综上所述／让我们／在…的过程中）</li>",
         "<li>加一个只有你知道的细节（哪一场、坐哪边、身边谁在哭）</li>",
         "<li>标签换成你所在城市与场次（3–5 个，放末尾）</li>",
         "<li>确认数字与出处（一条最多一个数字，出处写在后面）</li>",
         "<li>删掉任何「总结句」与空洞祝愿</li></ol>",
         "<h2>④ 不建议直接发的情况</h2><ul>",
         "<li>涉及私域／他人信息（家事、联系方式、未公开行程）→ <b>一律不发</b></li>",
         "<li>未证实的细节（听说的、没有出处的数字）→ 先标「待核」再决定</li>",
         "<li>涉及逝者／悼念语境 → 不发</li>",
         "<li>平台机制类说法 → 必须标「经验性认知（非官方）」</li></ul>",
         "<h2>⑤ 风格硬约束（本页与生成器同源）</h2>",
         f"<p class=\"meta\">每行 ≤ <b>{c.get('line_max_chars')}</b> 字｜正文行数 <b>{c.get('lines_range')}</b>｜"
         f"emoji ≤ <b>{c.get('emoji_max')}</b>｜标签 <b>{c.get('tags_range')}</b> 个放末尾｜"
         f"留白 <b>{c.get('fill_in_slots')}</b> 处｜一条最多一个数字</p>",
         "<p class=\"meta\">禁句式：" + "、".join((cp.get("anti_ai") or {}).get("banned_patterns") or []) + "</p>",
         "<p class=\"meta\">夸词黑名单共 " + str(len((cp.get("anti_ai") or {}).get("banned_words") or [])) + " 条（列举见 <code>project_b/build_copy_pipeline.py#BANNED</code>）：生成时自动过滤并记账，页面不转载。</p>",
         f"<h2>⑥ 当前待用钩子（{len(items)} 条）</h2><ul>"]
    for it in items:
        H.append(f"<li>{it['hook']}　<span class=\"meta\">{it['usage']['预计发布时机']}</span></li>")
    H += ["</ul>", "<p class=\"meta\">音视频不入 git、不上页面；不接外部自动发布接口。</p>",
          "<p><a href=\"share.html\">← 回 share.html</a></p></body></html>"]
    OUT.write_text("\n".join(H), encoding="utf-8")
    print("[OK]", OUT, OUT.stat().st_size, "B")

    # share.html 顶部链接（幂等）
    sp = SITE / "share.html"
    if sp.exists():
        t = sp.read_text(encoding="utf-8")
        if "使用说明-四件套.html" not in t:
            anchor = "<h1>素材与引用</h1>"
            if anchor in t:
                t = t.replace(anchor, anchor + "\n<p class=\"meta\">📖 先看 <a href=\"使用说明-四件套.html\">"
                                             "使用说明（四件套）</a>：怎么勾选、怎么改、怎么自检。</p>", 1)
                sp.write_text(t, encoding="utf-8")
                print("[OK] share.html 顶部已加使用说明链接")
        else:
            print("[=] share.html 已有链接")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
