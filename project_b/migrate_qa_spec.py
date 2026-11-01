"""从现有 qa.html 抽出问答 → data/qa_spec.json（一次性迁移用）"""
import io
import json
import re

SRC = r"D:\wx409.github.io\qa.html"
OUT = r"D:\wx409.github.io\data\qa_spec.json"

DROP = [
    "为什么王晰个人巡回演唱会当天，音乐指数会下降？",
    "王晰开过个人演唱会吗？那些「演唱会」是什么性质的？",
]

s = io.open(SRC, encoding="utf-8", errors="ignore").read()

pairs = []
for m in re.finditer(r"<h2[^>]*>(.*?)</h2>\s*(.*?)(?=<h2|<!-- FOOTER_NAV_START -->|</body>)", s, re.S):
    q = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    a_html = m.group(2).strip()
    text = re.sub(r"<br\s*/?>", "\n", a_html)
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if q and text:
        pairs.append({"q": q, "a": text})

kept = [p for p in pairs if p["q"] not in DROP]
print("抽出", len(pairs), "→ 保留", len(kept), "（删", len(pairs) - len(kept), "）")

json.dump({"note": "问答规格：dynamic 字段非空表示答案由 build_qa_page.py 用数据现算",
           "items": [{"q": p["q"], "a": p["a"], "dynamic": ""} for p in kept]},
          open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("→", OUT)
for p in kept:
    print("  -", p["q"][:50])
