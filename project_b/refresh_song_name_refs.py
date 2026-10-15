# -*- coding: utf-8 -*-
"""裁决 5：《唱起草原的歌》曲名归一 → 刷新站内产物（只改曲名/键/ID，不动证据引用与文件名）。

范围：`data/` 下公开 JSON（含 share 卡片/词条）与站内 HTML 中的**曲名引用**；
**不触碰** `原始材料\*`（历史素材，证据引用留原样）与任何文件名。
"""
import json
from pathlib import Path

SITE = Path(r"D:\wx409.github.io")
OLD, NEW = "唱起草原歌", "唱起草原的歌"
changed: list[str] = []


def fix_obj(o):
    n = 0
    if isinstance(o, dict):
        for k, v in list(o.items()):
            if isinstance(v, str) and OLD in v:
                o[k] = v.replace(OLD, NEW)
                n += 1
            else:
                n += fix_obj(v)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            if isinstance(v, str) and OLD in v:
                o[i] = v.replace(OLD, NEW)
                n += 1
            else:
                n += fix_obj(v)
    return n


for p in sorted(SITE.glob("data/**/*.json")):
    if any(x in str(p) for x in ("\\kb\\semantic\\", "voice_corpus", "voice_sentences")):
        continue                      # 语义索引/语料为历史产物，重建时自然派生
    try:
        raw = p.read_text(encoding="utf-8")
    except Exception:
        continue
    if OLD not in raw:
        continue
    try:
        obj = json.loads(raw)
    except Exception:
        continue
    k = fix_obj(obj)
    if k:
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
        changed.append(f"{p.relative_to(SITE)}（{k} 处）")

for p in sorted(SITE.glob("*.html")):
    raw = p.read_text(encoding="utf-8")
    if OLD not in raw:
        continue
    p.write_text(raw.replace(OLD, NEW), encoding="utf-8")
    changed.append(f"{p.name}（HTML）")

print("[已刷新]", len(changed), "个产物")
for c in changed:
    print("   -", c)
