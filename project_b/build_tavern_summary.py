# -*- coding: utf-8 -*-
"""
小酒馆"有价值摘要"提取（DeepSeek API）
=======================================
从本地全文库的 106 期逐字稿中，用 LLM 提取有留存价值的摘要：
  - 主题与主旨
  - 王晰的个人喜好（喜欢的歌 / 书 / 文章 / 电影 / 生活爱好等）
  - 金句（1-3 条王晰原话，有风格或观点价值）
  - 本期涉及的关键词
  - 本期歌单（songmid 关联，来自 transcripts）

用于生成"摘要版"小酒馆 EP 页（替代站内逐字稿全文，合规 + 保留价值）。

用法：
  python project_b/build_tavern_summary.py --limit 2     # 只处理前2期（测试）
  python project_b/build_tavern_summary.py --all          # 全部106期

安全：DEEPSEEK_API_KEY 从环境变量读取，绝不硬编码/入库。
"""
from __future__ import annotations
import json, os, re, time, sys
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
TAVERN_LIB = Path(r"E:\wx\私有\王晰全文库\小酒馆逐字稿")
OUT = ROOT / "tavern" / "tavern_summaries.json"   # 站内只放摘要（合规）
CACHE_DIR = TAVERN_LIB / "summaries"               # 本地缓存完整处理态

API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-v4-flash"

PROMPT = """你是档案馆摘要员。下面是歌手王晰《深夜小酒馆》节目第{n}期「{theme}」的逐字稿。
请提取有档案留存价值的摘要，输出 JSON（只输出JSON，不要其他文字）：
{{
  "theme": "本期主题",
  "summary": "80-150字的主旨概述，讲这期聊了什么、王晰讲的故事/观点",
  "likes": ["王晰在节目中表达的喜好：喜欢的歌/书/电影/生活爱好，逐条列出，没有则空数组"],
  "songs": ["本期提到/喜欢的歌曲名"],
  "quotes": ["1-3条王晰原话金句（保留口语风格，每条≤40字）"],
  "keywords": ["4-8个关键词，便于检索"]
}}
只依据逐字稿提取，不要臆造。逐字稿如下：
---
{text}
"""


def get_api_key():
    """优先环境变量 DEEPSEEK_API_KEY，其次 gitignored 私有配置 temp/deepseek_key.json"""
    k = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if k:
        return k
    try:
        cfg = Path(r"D:\wx409.github.io\temp\deepseek_key.json")
        if cfg.exists():
            return json.loads(cfg.read_text(encoding='utf-8')).get("api_key", "").strip()
    except Exception:
        pass
    return ""


def call_deepseek(text, theme, n):
    key = get_api_key()
    if not key:
        raise RuntimeError("未设置 DEEPSEEK_API_KEY")
    import urllib.request
    prompt = PROMPT.format(n=n, theme=theme or '', text=text[:6000])
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是严谨的档案内容摘要师，只输出合法JSON。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }).encode('utf-8')
    req = urllib.request.Request(API_URL, data=body, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    content = data["choices"][0]["message"]["content"]
    # DeepSeek 可能返回 markdown 包裹的 json
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
    return json.loads(content)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=2)
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    if not get_api_key():
        print("[X] 请设置 DEEPSEEK_API_KEY 环境变量")
        return

    t = json.loads((TAVERN_LIB / "tavern_transcripts.json").read_text(encoding='utf-8'))
    eps = t.get('episodes', {})
    keys = list(eps.keys())
    if not a.all:
        keys = keys[:a.limit]

    # 载入已有摘要（增量续传）
    existing = {}
    if OUT.exists():
        try:
            existing = json.loads(OUT.read_text(encoding='utf-8')).get('episodes', {})
        except Exception:
            existing = {}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    for i, key in enumerate(keys, 1):
        if key in existing and existing[key].get('summary'):
            print(f"[{i}/{len(keys)}] {key} 已有摘要，跳过")
            continue
        v = eps[key]
        text = v.get('text', '')
        theme = v.get('theme', '')
        n = v.get('episode_num', '')
        print(f"[{i}/{len(keys)}] 处理 {key}（{len(text)}字）…")
        try:
            smry = call_deepseek(text, theme, n)
            existing[key] = {
                "episode": key, "category": v.get('category'),
                "theme": theme, "songmid": v.get('songmid'),
                "summary": smry.get("summary", ""),
                "likes": smry.get("likes", []),
                "songs": smry.get("songs", []),
                "quotes": smry.get("quotes", []),
                "keywords": smry.get("keywords", []),
            }
            print(f"  ✓ theme={theme} | likes={len(smry.get('likes',[]))} | quotes={len(smry.get('quotes',[]))}")
        except Exception as e:
            print(f"  ✗ {key} 失败: {str(e)[:80]}")
            existing[key] = {"episode": key, "category": v.get('category'),
                             "theme": theme, "songmid": v.get('songmid'),
                             "summary": "", "likes": [], "songs": [],
                             "quotes": [], "keywords": [], "error": str(e)[:100]}
        time.sleep(1.0)  # 限速

    result = {
        "_meta": {"note": "小酒馆逐字稿的有价值摘要（LLM提取，合规：不含逐字稿全文，仅主题/喜好/金句/歌单/关键词）",
                  "generated_at": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M")},
        "episodes": existing,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
    done = sum(1 for v in existing.values() if v.get('summary'))
    print(f"\n[完成] 已提取 {done}/{len(existing)} 期摘要 → {OUT}")


if __name__ == '__main__':
    main()
