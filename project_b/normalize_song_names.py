# -*- coding: utf-8 -*-
"""曲名自动统一工具（基础数据层）：把各种写法改写成规范名。

安全边界（很重要）
------------------
**只改"曲名字段"**（song / title / name / song_title / songs[…] 等），
**绝不改引用正文**（weibo 的 text/content、证据 evidence、转写稿 等）——
那些是原始素材，改了就是篡改来源。

用法：
  python -X utf8 project_b\\normalize_song_names.py            # 试算（默认）
  python -X utf8 project_b\\normalize_song_names.py --apply     # 执行（自动备份到 temp/_songname_bak/）
  python -X utf8 project_b\\normalize_song_names.py --apply --also-absolute   # 同时处理 E: 派生文件
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SITE / "project_b"))
from song_names import canon, norm, strict_norm  # noqa: E402

BAK = SITE / "temp" / "_songname_bak"

# 允许改写的字段名（小写比较）；"text/content/evidence/quote" 等一律不碰
NAME_KEYS = {"song", "title", "name", "song_title", "songtitle", "songname", "曲名",
             "canonical_title", "canonical_name", "track", "track_title"}
LIST_KEYS = {"songs", "song_titles", "titles", "tracks", "songlist", "song_list"}


def walk(obj, path=""):
    """遍历所有字符串值与列表内字符串（配合 _known_keys() 判定，只改整串命中的）。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                yield obj, k, v, f"{path}.{k}"
            else:
                yield from walk(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            if isinstance(x, str):
                yield obj, i, x, f"{path}[{i}]"
            else:
                yield from walk(x, f"{path}[{i}]")


def targets(also_absolute: bool):
    files = []
    for pat in ("data/**/*.json", "dashboard/**/*.json", "*.json",
                "tavern/**/*.json", "live/**/*.json", "repo/**/*.json"):
        files += [p for p in SITE.glob(pat) if p.is_file()]
    if also_absolute:
        files += [Path(r"E:\wx\wx_textmine_out\master_timeline.json")]
    return sorted({p for p in files
                   if ".bak" not in p.name and p.name not in ("song_aliases.json",)
                   and "_songname" not in str(p)})


def rename_keys(obj, changes, path=""):
    """把字典键按 canon() 重命名；冲突时保留已存在的目标键（不覆盖），并记录。

    只重命名「确实在别名/覆盖表里」的键（canon 已收紧，不会误伤无关名称）。
    """
    if isinstance(obj, dict):
        for k in list(obj.keys()):
            if isinstance(k, str):
                nk = canon(k)
                if nk != k and (strict_norm(k) in _known_keys()):
                    if nk in obj and nk != k:
                        changes.append((k, nk, f"{path}.{k}", "冲突保留已有"))
                    else:
                        obj[nk] = obj.pop(k)
                        changes.append((k, nk, f"{path}.{k}", "键重命名"))
            rename_keys(obj[k] if isinstance(obj.get(k), dict) else obj.get(k), changes, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            rename_keys(x, changes, f"{path}[{i}]")


def _known_keys():
    """{strict_norm(写法)}：别名表/覆盖表里登记过的所有写法。"""
    from song_names import _aliases, _canon_overrides
    ks = set(_canon_overrides().keys())
    ks |= set(_aliases().keys())
    return ks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--also-absolute", action="store_true")
    a = ap.parse_args()
    if a.apply:
        BAK.mkdir(parents=True, exist_ok=True)

    tot_files, tot_fields = 0, 0
    detail = []
    for fp in targets(a.also_absolute):
        try:
            txt = fp.read_text(encoding="utf-8")
            data = json.loads(txt)
        except Exception:
            continue
        changed = []
        known = _known_keys()
        for holder, key, old, path in list(walk(data)):
            if strict_norm(old) not in known:      # 只处理整串命中已知变体的
                continue
            new = canon(old)
            if new != old:
                holder[key] = new
                changed.append((old, new, path))
        key_changes = []
        rename_keys(data, key_changes)
        if key_changes:
            changed += [(k, v, f"{pp}(键)") for k, v, pp, _ in key_changes[:50]]
        if not changed:
            continue
        tot_files += 1
        tot_fields += len(changed)
        detail.append((fp, changed))
        if a.apply:
            rel = fp.relative_to(SITE) if str(fp).startswith(str(SITE)) else Path(fp.name)
            dst = BAK / (str(rel).replace("\\", "__") + f".bak_{datetime.now():%Y%m%d_%H%M}")
            shutil.copy2(fp, dst)
            fp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    print(f"{'[已执行]' if a.apply else '[试算]'} 涉及文件 {tot_files}｜改写曲名字段 {tot_fields}")
    for fp, ch in detail[:25]:
        kinds = {}
        for old, new, _ in ch:
            kinds.setdefault(f"{old} → {new}", 0)
            kinds[f"{old} → {new}"] += 1
        print(f"  {fp.relative_to(SITE) if str(fp).startswith(str(SITE)) else fp}")
        for k, v in sorted(kinds.items(), key=lambda kv: -kv[1])[:4]:
            print(f"      {k} × {v}")
    if not a.apply:
        print("\n（未写入；确认后加 --apply）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
