# -*- coding: utf-8 -*-
"""本地数据仓库：把站点 JSON / 指数长表 CSV 灌进 DuckDB 单文件，供「自然语言 → SQL」查询。

用法:
  python -X utf8 project_b\\build_warehouse.py                # 默认输出 E:\\wx\\warehouse\\wangxi.duckdb
  python -X utf8 project_b\\build_warehouse.py --out <path>
产物: warehouse.duckdb + docs\\DATA-WAREHOUSE.md（表清单/行数/示例 SQL，供后续会话直接查）

规则：list[dict] → 一张表；dict 里的每个 list[dict] → 一张子表（键名即表名）；
嵌套值序列化成 JSON 字符串列；同名表后写覆盖（幂等，可重复跑）。
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DASH = ROOT / "dashboard" / "dashboard_data.json"
LONG_CSV = Path(r"E:\wx\wx_textmine_out\music_index_long.csv")
DOC = ROOT / "temp" / "DATA-WAREHOUSE.md"  # 不进公开仓库（含本机绝对路径）
DEFAULT_OUT = Path(r"E:\wx\warehouse\wangxi.duckdb")


def tname(s: str) -> str:
    return re.sub(r"\W+", "_", s).strip("_").lower()


def norm(rows: list) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    for c in df.columns:
        if df[c].map(lambda v: isinstance(v, (dict, list))).any():
            df[c] = df[c].map(lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v)
    return df


def add(con, name: str, rows: list) -> int | None:
    if not rows:
        return None
    df = norm(rows)
    con.register("_tmp", df)
    con.execute(f'CREATE OR REPLACE TABLE "{tname(name)}" AS SELECT * FROM _tmp')
    con.unregister("_tmp")
    return len(df)


def json_tables(obj, prefix: str = ""):
    """从任意 JSON 结构里抽出 (表名, list[dict])。"""
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        yield prefix, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                yield f"{prefix}_{k}" if prefix else k, v
            elif isinstance(v, dict) and not prefix:  # 只下钻一层
                for k2, v2 in v.items():
                    if isinstance(v2, list) and v2 and isinstance(v2[0], dict):
                        yield k2, v2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    a = ap.parse_args()
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(out))
    made: list[tuple[str, int]] = []

    for f in sorted(DATA.rglob("*.json")):
        rel = f.relative_to(DATA).with_suffix("").as_posix()
        try:
            obj = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  ! {rel}: {e}")
            continue
        for sub, rows in json_tables(obj, tname(rel.replace("/", "_"))):
            n = add(con, sub, rows)
            if n is not None:
                made.append((tname(sub), n))

    if DASH.exists():
        obj = json.loads(DASH.read_text(encoding="utf-8"))
        for k, v in obj.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                n = add(con, f"dash_{k}", v)
                if n:
                    made.append((tname(f"dash_{k}"), n))
            elif not isinstance(v, (list, dict)):
                con.execute("CREATE OR REPLACE TABLE dash_meta AS SELECT * FROM (SELECT ? AS k, ? AS v)", [k, v])
        made = [m for m in made if m[0] != "dash_meta"]

    if LONG_CSV.exists():
        con.execute(f'CREATE OR REPLACE TABLE index_long AS SELECT * FROM read_csv_auto(\'{LONG_CSV.as_posix()}\')')
        made.append(("index_long", con.execute("SELECT count(*) FROM index_long").fetchone()[0]))

    # 去重（同名后写覆盖）
    seen, tables = set(), []
    for n, c in made:
        if n not in seen:
            seen.add(n)
            tables.append((n, con.execute(f'SELECT count(*) FROM "{n}"').fetchone()[0]))
    tables.sort()

    rows_md = "\n".join(f"| `{n}` | {c:,} |" for n, c in tables)
    DOC.write_text(f"""# 数据仓库（DuckDB 单文件）

> 生成：`python -X utf8 project_b\\build_warehouse.py`｜库文件：`{out}`
> 用途：把站点数据变成可以**直接问 SQL** 的表，DSH 里一条 python/duckdb 即可查。

```python
import duckdb
con = duckdb.connect(r"{out}", read_only=True)
con.sql("SELECT ...").df()
```

| 表 | 行数 |
|---|---:|
{rows_md}

## 示例

```sql
-- 指数年度中位（主口径=追踪曲目池日均）
SELECT year(d) y, median(index) FROM (SELECT CAST(date AS DATE) d, index FROM index_long) GROUP BY 1 ORDER BY 1;
-- 某首歌的现场实测明细
SELECT * FROM archive_stage_tour WHERE song='多听有益';
-- 口径字典
SELECT * FROM calibers;
```
""", encoding="utf-8")
    con.close()
    print(f"表 {len(tables)} 张 → {out}")
    for n, c in tables[:200]:
        print(f"  {n:<34}{c:>8,}")
    print("→", DOC)
    assert tables, "仓库为空：没有识别到任何表"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
