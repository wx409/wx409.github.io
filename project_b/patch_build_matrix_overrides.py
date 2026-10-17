# -*- coding: utf-8 -*-
"""给 00_build_matrix.py 增加「按日档列覆盖」支持（当日中间批/单文件两日值的场景）。

背景（2026-10-17 核查）：
  · `2026.10.16.xlsx` 同时含两列：`昨日音乐指数`＝10-15 的值、`音乐指数`＝10-16 的值（各 11/13 行非空）。
  · 旧逻辑只读「昨日音乐指数」并统一映射到 D−1 → 只进 10-15，10-16 永远缺。
  · 用户确认该文件内容准确 → 允许把 `音乐指数` 列**额外**按 D 导入（不走 D−1）。

实现：新增可选配置 `E:\\wx\\index_records\\day_overrides.json`：
  { "2026.10.16.xlsx": { "column": "音乐指数", "as_date": "2026-10-16" } }
处理该文件时，除了原有「昨日音乐指数→D−1」，**额外**把指定列按指定日期写入。
只对显式登记的文件生效，**不改变历史口径**。
"""
from pathlib import Path

P = Path(r"E:\wx\wx_textmine\00_build_matrix.py")
t = P.read_text(encoding="utf-8")
if "day_overrides" in t:
    print("[=] 已支持 day_overrides")
    raise SystemExit(0)

# 1) 配置读取
t = t.replace('OUT_DEFAULT = r"E:\\wx\\wx_textmine_out\\music_index_long.csv"',
              'OUT_DEFAULT = r"E:\\wx\\wx_textmine_out\\music_index_long.csv"\n'
              'OVERRIDES = Path(r"E:\\wx\\index_records\\day_overrides.json") if "Path" in dir() else None', 1)

# 2) 在 main 里加载配置
t = t.replace("def main():", '''def _load_overrides():
    """可选：按文件名指定「额外列 + 目标日期」，用于单文件含两日值（如 10-16 档的 音乐指数 列）。"""
    import json as _json
    from pathlib import Path as _P
    p = _P(r"E:\\wx\\index_records\\day_overrides.json")
    if not p.exists():
        return {}
    try:
        return _json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main():''', 1)

# 3) 处理完正常逻辑后，追加覆盖列
anchor = '''            per_store[prio]["rows"] += 1'''
add = '''            # ★ 2026-10-17：按 day_overrides 额外导入指定列（如 10-16 档的「音乐指数」列 = 当日值）
            _ov = ov.get(base)
            if _ov:
                _col = next((c for c in df.columns if str(c) == _ov.get("column")), None)
                _day = _ov.get("as_date")
                if _col is not None and _day:
                    for _, row in df.iterrows():
                        nm = clean_name(row.get(name_c))
                        if not nm or nm in ("歌曲名称", "nan", "None") or len(nm) < 2:
                            continue
                        art = clean_name(row.get(artist_c)) if artist_c is not None else ""
                        if art and "王晰" not in art:
                            continue
                        v = to_num(row.get(_col))
                        if v is None:
                            continue
                        data.setdefault(nm, {})[_day] = v
                        per_store[prio]["rows"] += 1
'''
if anchor in t:
    t = t.replace(anchor, add + anchor, 1)

# 4) ov 变量初始化
t = t.replace('    data = {}      # song -> {date: value}', '    data = {}      # song -> {date: value}\n    ov = _load_overrides()', 1)

P.write_text(t, encoding="utf-8")
print("[OK] 00_build_matrix.py 已支持 day_overrides")
