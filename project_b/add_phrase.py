"""往词句库加内容（本地 CLI）。

用法：
  python -X utf8 project_b\\add_phrase.py --type lyrics --text "句子" --source "歌词《某某》"
  python -X utf8 project_b\\add_phrase.py --type talk --text "句子" --source "上海20251121" --unverified
  python -X utf8 project_b\\add_phrase.py --list
  python -X utf8 project_b\\add_phrase.py --from-json new.json     # 批量 [{"type":..,"text":..,"source":..}]

可选：--rights free|仅内部|娱乐向   --mood 任意   --rebuild（顺带重建骰子与页面）
不加 --rebuild 时只入库；加 --rebuild 会跑 rebuild_dice_sets + build_phrases_page + build_nav。
"""
import argparse, json, subprocess, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "data" / "phrase_bank.json"
TYPES = {"talk": "free", "lyrics": "仅内部", "mystic": "娱乐向", "interview": "free", "song": "free"}

def load():
    return json.loads(BANK.read_text(encoding="utf-8"))

def save(bank):
    bank["count"] = len(bank["items"])
    bank["by_type"] = dict(Counter(it["type"] for it in bank["items"]))
    BANK.write_text(json.dumps(bank, ensure_ascii=False, indent=1), encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", choices=list(TYPES))
    ap.add_argument("--text")
    ap.add_argument("--source", default="")
    ap.add_argument("--rights")
    ap.add_argument("--mood", default="")
    ap.add_argument("--unverified", action="store_true", help="标记 verified=false（转写/OCR 未校对）")
    ap.add_argument("--from-json")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    a = ap.parse_args()

    bank = load()
    if a.list:
        print("当前 %d 条：%s" % (bank["count"], bank["by_type"]))
        for it in bank["items"][-10:]:
            print("  [%s] %s｜%s" % (it["type"], it["text"][:40], it.get("source", "")))
        return 0

    new = []
    if a.from_json:
        new = json.loads(Path(a.from_json).read_text(encoding="utf-8"))
    else:
        if not (a.type and a.text):
            print("需要 --type 与 --text（或用 --from-json / --list）")
            return 2
        new = [{"type": a.type, "text": a.text, "source": a.source,
                "rights": a.rights or TYPES[a.type], "mood": a.mood,
                "verified": not a.unverified}]

    exist = {it["text"] for it in bank["items"]}
    added, skipped = 0, []
    for r in new:
        t = (r.get("text") or "").strip()
        if not t:
            continue
        if t in exist:
            skipped.append(t)
            continue
        typ = r.get("type")
        if typ not in TYPES:
            print("跳过未知类型:", typ, t[:20]); continue
        bank["items"].append({
            "text": t, "type": typ,
            "source": r.get("source") or "手工新增",
            "curated": bool(r.get("curated", False)),
            "rights": r.get("rights") or TYPES[typ],
            "mood": r.get("mood") or typ,
            "verified": bool(r.get("verified", True)),
        })
        exist.add(t)
        added += 1
    save(bank)
    print("入库 %d 条｜跳过重复 %d 条｜现共 %d 条 %s" % (added, len(skipped), bank["count"], bank["by_type"]))

    if a.rebuild and added:
        for s in ("rebuild_dice_sets.py", "build_phrases_page.py", "build_nav.py"):
            p = ROOT / "project_b" / s
            if p.exists():
                rc = subprocess.call([sys.executable, "-X", "utf8", str(p)])
                print("  %s -> rc=%d" % (s, rc))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
