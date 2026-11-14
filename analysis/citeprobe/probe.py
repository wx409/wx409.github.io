# -*- coding: utf-8 -*-
"""AI/搜索可见性探测：固定问题集 × 每月一轮，记录你的站点有没有被搜到、排第几。

只依赖标准库（urllib / re / json），用系统 Python 即可跑。
数据落 analysis/citeprobe/history/，每次运行追加一行到 history.jsonl。
有「新命中 / 名次进前三 / 收录数明显变化」时，调用 project_b/notify.py 推送。

注意：这里测的是「搜索引擎可见性」，是「AI 是否引用」的**代理指标**。
真正的 LLM 引用探测需要 DeepSeek API key（Anthropic 兼容 + web_search 工具），
拿到 key 后把 MODE 换成 'llm' 即可，接口已在文件末尾留好位置。
"""
import json
import random
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

SITE = Path(r"D:\wx409.github.io")
HERE = Path(__file__).resolve().parent
HIST = HERE / "history"
HIST.mkdir(exist_ok=True)
STATE = HERE / "state.json"
LATEST = HERE / "LATEST.md"
NOTIFY = SITE / "project_b" / "notify.py"

DOMAIN = "wx409.github.io"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0 Safari/537.36")

# 20 个「真人会问 AI / 会去搜」的问题。改这里就能扩题，不用改代码。
QUERIES = [
    "王晰 音域 最低音 多少",
    "王晰 低音 B1 现场",
    "王晰 男低音 音域 跨度",
    "王晰 唱功 怎么样 客观分析",
    "王晰 演唱会 现场 音准 稳定",
    "王晰 有哪些 代表作 专辑",
    "王晰 巡演 城市 场次",
    "王晰 深夜小酒馆 播客",
    "王晰 音乐指数 数据 变化",
    "王晰 抖音 收藏 音乐",
    "王晰 颤音 技术 特点",
    "王晰 低音 下探 歌曲 排行",
    "王晰 与 赵鹏 对比 低音",
    "王晰 一巡 巡演 歌单",
    "王晰 声乐 分析 长音",
    "王晰 气息 HNR 嗓音 数据",
    "王晰 华语 男低音 代表",
    "王晰 现场 稳定 音域 实测",
    "王晰 数据 档案 网站",
    "王晰 演出 带动 收听 数据",
]

RESULT_RE = re.compile(r'<h2[^>]*>\s*<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', re.S)
TAG_RE = re.compile(r"<[^>]+>")


def bing(query, timeout=25):
    url = "https://cn.bing.com/search?q=" + urllib.parse.quote(query) + "&setlang=zh-CN&count=20"
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "ignore")


def parse(html, limit=10):
    out = []
    for url, title in RESULT_RE.findall(html):
        t = TAG_RE.sub("", title).strip()
        if "bing.com" in url or "microsoft.com" in url:
            continue
        out.append({"url": url, "title": t})
        if len(out) >= limit:
            break
    return out


def probe_query(q):
    try:
        results = parse(bing(q))
    except Exception as e:
        return {"query": q, "error": f"{type(e).__name__}: {e}"[:120], "hit": False, "rank": None}
    rank = None
    for i, r in enumerate(results, 1):
        if DOMAIN in r["url"]:
            rank = i
            break
    return {
        "query": q, "hit": rank is not None, "rank": rank,
        "top": [{"url": r["url"], "title": r["title"][:60]} for r in results[:3]],
        "n_results": len(results),
    }


def index_probe():
    """site: 查询，估算收录页数（Bing 的结果块数 + 域名出现次数）。"""
    try:
        html = bing(f"site:{DOMAIN}")
        blocks = len(re.findall(r'class="b_algo"', html))
        return {"blocks": blocks, "mentions": html.count(DOMAIN)}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"[:120]}


# ── 反爬护栏 ──────────────────────────────────────────────────────────────
# 2026-11-14 实测：本机 IP 访问 cn.bing.com / www.bing.com 的搜索页与 RSS，
# 无论查询是什么都返回同一批「王/汉字/王者荣耀」结果 —— 属于被降级/占位页。
# 这种情况绝不能记成「0/20 未命中」，否则会得出完全错误的结论。
def degraded(rows):
    seen = set()
    for r in rows:
        doms = tuple(sorted({urllib.parse.urlparse(t["url"]).netloc for t in r.get("top", [])[:3]}))
        if doms:
            seen.add(doms)
    return len(rows) >= 5 and len(seen) <= 1

def notify(title, content):
    try:
        subprocess.run([sys.executable, "-X", "utf8", str(NOTIFY), title, content],
                       cwd=str(SITE), timeout=60, capture_output=True)
        return True
    except Exception:
        return False


def main():
    started = datetime.now().strftime("%Y-%m-%d %H:%M")
    rows = []
    for i, q in enumerate(QUERIES, 1):
        rows.append(probe_query(q))
        print(f"[{i:>2}/{len(QUERIES)}] {'HIT#'+str(rows[-1]['rank']) if rows[-1].get('hit') else 'miss'}  {q}")
        time.sleep(1.2 + random.random())
    idx = index_probe()

    if degraded(rows):
        print("\n[中止] 搜索引擎返回的是降级/占位页（不同查询命中的域名完全相同），")
        print("       本轮结果不可信，未写入历史。改用 DSH 的 web_search 跑一轮，")
        print("       或给一个 Bing Webmaster / DeepSeek API key（见 README.md）。")
        return 2

    prev = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else None
    hits = [r for r in rows if r.get("hit")]
    payload = {
        "at": started,
        "mode": "bing-html",
        "queries": len(QUERIES),
        "hits": len(hits),
        "best_rank": min([r["rank"] for r in hits]) if hits else None,
        "index": idx,
        "rows": rows,
    }

    stamp = datetime.now().strftime("%Y-%m-%d")
    (HIST / f"{stamp}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with open(HERE / "history.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"at": started, "hits": len(hits),
                            "rank": payload["best_rank"], "index": idx}, ensure_ascii=False) + "\n")

    # 报告
    lines = [f"# AI/搜索可见性 · {started}", "",
             f"- 问题数 **{len(QUERIES)}**，命中 **{len(hits)}**，最好名次 "
             f"**{payload['best_rank'] or '—'}**",
             f"- `site:{DOMAIN}` 结果块 **{idx.get('blocks','—')}**（收录代理指标）", ""]
    if hits:
        lines += ["## 命中的问题", "", "| 问题 | 名次 | 命中的页面 |", "|---|---|---|"]
        for r in hits:
            page = next((t["url"] for t in r["top"] if DOMAIN in t["url"]), "")
            lines.append(f"| {r['query']} | {r['rank']} | {page} |")
        lines.append("")
    lines += ["## 全部问题", "", "| 问题 | 命中 | 名次 | 前 3 竞争页面 |", "|---|---|---|---|"]
    for r in rows:
        comp = "、".join(urllib.parse.urlparse(t["url"]).netloc for t in r.get("top", [])[:3])
        lines.append(f"| {r['query']} | {'✅' if r.get('hit') else '—'} | {r.get('rank') or '—'} | {comp} |")
    LATEST.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # 变化检测：只报「值得看」的
    changes = []
    if prev:
        prev_hit = {r["query"] for r in prev.get("rows", []) if r.get("hit")}
        now_hit = {r["query"] for r in hits}
        new = now_hit - prev_hit
        lost = prev_hit - now_hit
        if new:
            changes.append("新命中：" + "、".join(sorted(new)))
        if lost:
            changes.append("跌出：" + "、".join(sorted(lost)))
        if prev.get("best_rank") and payload["best_rank"] and payload["best_rank"] < prev["best_rank"]:
            changes.append(f"最好名次 {prev['best_rank']} → {payload['best_rank']}")
        pi, ci = prev.get("index", {}).get("blocks"), idx.get("blocks")
        if isinstance(pi, int) and isinstance(ci, int) and abs(ci - pi) >= 5:
            changes.append(f"收录块 {pi} → {ci}")
    else:
        changes.append("首次建立基线")

    if changes:
        notify("AI 可见性：" + "；".join(changes)[:40],
               "\n".join(changes) + f"\n\n命中 {len(hits)}/{len(QUERIES)}，最好名次 {payload['best_rank'] or '—'}。"
               f"\n详情：analysis/citeprobe/LATEST.md")

    STATE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n命中 {len(hits)}/{len(QUERIES)} | 最好名次 {payload['best_rank']} | site: 块 {idx.get('blocks')}")
    print("变化：" + ("；".join(changes) if changes else "无"))
    print(f"报告：{LATEST}")


if __name__ == "__main__":
    sys.exit(main())
