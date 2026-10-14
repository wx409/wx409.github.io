# -*- coding: utf-8 -*-
"""P1-3 时间演变图：早期 vs 近期（短句率、第一人称率、句长中位、跨源三层对照）

数据源：`data/text_profile.json#by_year` / `#by_year_bin` / `#cross_source`（全部由 P0-1 现算派生）。
产出：`assets/insight/语言演变_分期.png`、`assets/insight/语言演变_逐年.png`、`assets/insight/跨源三层.png`
＋ 指纹文件 `data/share/insight_charts.json`（图上数字 + PNG sha256，供双重校验）。
用法：python -X utf8 project_b\\build_insight_charts.py
"""
from __future__ import annotations
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SITE = Path(r"D:\wx409.github.io")
D = SITE / "data"
OUTDIR = SITE / "assets" / "insight"
OUT_FP = D / "share" / "insight_charts.json"
TP = json.loads((D / "text_profile.json").read_text(encoding="utf-8"))

by_year = TP.get("by_year") or {}
bins = TP.get("by_year_bin") or {}
cross = TP.get("cross_source") or {}

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False
OUTDIR.mkdir(parents=True, exist_ok=True)
charts = []


def save(fig, name):
    p = OUTDIR / name
    fig.tight_layout()
    fig.savefig(p, dpi=150)
    plt.close(fig)
    charts.append(p)
    return p


# 图 1：分期对照（短句率 / 第一人称率）
names = list(bins.keys())
short = [(bins[n] or {}).get("short_sent_pct") or 0 for n in names]
first = [(bins[n] or {}).get("first_person_pct") or 0 for n in names]
ns = [(bins[n] or {}).get("n_docs") or 0 for n in names]
fig, ax = plt.subplots(figsize=(7.6, 3.4))
x = range(len(names))
ax.bar([i - 0.18 for i in x], short, width=0.36, color="#4a6fa5", label="短句率（≤15 字）")
ax.bar([i + 0.18 for i in x], first, width=0.36, color="#c08a3e", label="第一人称句占比")
for i, (a, b, n) in enumerate(zip(short, first, ns)):
    ax.text(i - 0.18, a + 1, f"{a}%", ha="center", fontsize=8)
    ax.text(i + 0.18, b + 1, f"{b}%", ha="center", fontsize=8)
ax.set_xticks(list(x))
ax.set_xticklabels([f"{n}\n(n={m})" for n, m in zip(names, ns)], fontsize=8.5)
ax.set_ylim(0, 100)
ax.set_ylabel("占比 %")
ax.set_title("图1｜分期语言特征（数据源 data/text_profile.json）")
ax.legend(fontsize=8)
save(fig, "语言演变_分期.png")

# 图 2：逐年（短句率 + 句长中位）
ys = sorted([k for k, v in by_year.items() if (v or {}).get("short_sent_pct") is not None])
s2 = [by_year[y]["short_sent_pct"] for y in ys]
l2 = [by_year[y].get("sent_len_median") or 0 for y in ys]
n2 = [by_year[y].get("n_docs") or 0 for y in ys]
fig, ax = plt.subplots(figsize=(9.2, 3.6))
ax.plot(ys, s2, "o-", color="#4a6fa5", label="短句率 %")
for i, y in enumerate(ys):
    ax.annotate(f"n={n2[i]}", (y, s2[i]), textcoords="offset points", xytext=(0, 6),
                fontsize=6.5, ha="center", color="#666")
ax.set_ylim(0, 100)
ax.set_ylabel("短句率 %")
ax2 = ax.twinx()
ax2.plot(ys, l2, "s--", color="#c08a3e", label="句长中位（字）")
ax2.set_ylabel("句长中位（字）")
h1, lb1 = ax.get_legend_handles_labels()
h2, lb2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, lb1 + lb2, fontsize=8, loc="lower left")
ax.set_title("图2｜逐年演变（每点标注该年样本量 n）")
plt.setp(ax.get_xticklabels(), rotation=45, ha="right", fontsize=8)
save(fig, "语言演变_逐年.png")

# 图 3：跨源三层
ck = [k for k, v in cross.items() if (v or {}).get("short_sent_pct") is not None]
cs = [cross[k]["short_sent_pct"] for k in ck]
cf = [cross[k].get("first_person_pct") or 0 for k in ck]
cn = [cross[k].get("n_sent") or 0 for k in ck]
fig, ax = plt.subplots(figsize=(7.6, 3.2))
x = range(len(ck))
ax.bar([i - 0.18 for i in x], cs, width=0.36, color="#5a7d5a", label="短句率")
ax.bar([i + 0.18 for i in x], cf, width=0.36, color="#8a5a7d", label="第一人称句占比")
for i, (a, b, n) in enumerate(zip(cs, cf, cn)):
    ax.text(i - 0.18, a + 1, f"{a}%", ha="center", fontsize=8)
    ax.text(i + 0.18, b + 1, f"{b}%", ha="center", fontsize=8)
ax.set_xticks(list(x))
ax.set_xticklabels([k.replace("（", "\n（") + f"\n{n} 句" for k, n in zip(ck, cn)], fontsize=8)
ax.set_ylim(0, 100)
ax.set_ylabel("占比 %")
ax.set_title("图3｜跨源三层对照（口语 / 事务 / 曲目）")
ax.legend(fontsize=8)
save(fig, "跨源三层.png")

fp = {"schema": 1, "generated_at": date.today().isoformat(),
      "source": "data/text_profile.json（由 project_b/build_language_profile.py 现算）",
      "charts": [{"file": f"assets/insight/{p.name}", "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                  "numbers": {
                      "分期": {n: {"short_sent_pct": (bins[n] or {}).get("short_sent_pct"),
                                   "first_person_pct": (bins[n] or {}).get("first_person_pct"),
                                   "n_docs": (bins[n] or {}).get("n_docs")} for n in names},
                      "跨源": {k: {"short_sent_pct": cross[k].get("short_sent_pct"),
                                   "first_person_pct": cross[k].get("first_person_pct"),
                                   "n_sent": cross[k].get("n_sent")} for k in ck},
                      "逐年点数": len(ys),
                  }} for p in charts]}
OUT_FP.parent.mkdir(parents=True, exist_ok=True)
OUT_FP.write_text(json.dumps(fp, ensure_ascii=False, indent=1), encoding="utf-8")

print(f"[ok] 图 {len(charts)} 张 → assets/insight/")
for c in charts:
    print("   ", c.name, c.stat().st_size, "bytes")
print(f"[ok] {OUT_FP.name}")
print("分期:", {n: (bins[n] or {}).get("short_sent_pct") for n in names})
print("跨源:", {k: cross[k].get("short_sent_pct") for k in ck})
