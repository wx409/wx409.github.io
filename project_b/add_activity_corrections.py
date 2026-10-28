import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
ROOT = Path(r'D:\wx409.github.io')

# 1) 更正表
corr = {"schema": "activity_corrections/v1",
        "note": "对活动总表的日期-城市错配做人工更正；不改原始核对表，保留可追溯",
        "items": [
            {"date": "2023-05-01", "from_city": "昆明", "to_city": "郑州",
             "to_title": "三巡郑州站彩排花絮",
             "reason": "用户确认：2023-05-01 是郑州站（长表亦记郑州 2023-05-01）"},
            {"date": "2022-09-17", "from_city": "郑州", "to_city": "武汉",
             "to_title": "王晰图景巡演武汉站",
             "reason": "用户确认：2022-09-17 是武汉站（长表亦记武汉 2022-09-17）"},
        ]}
(ROOT / 'data' / 'activity_corrections.json').write_text(
    json.dumps(corr, ensure_ascii=False, indent=1), encoding='utf-8')
print('更正表已建')

# 2) 构建器应用更正
p = ROOT / 'project_b' / 'build_activity_master.py'
s = p.read_text(encoding='utf-8')
old = '''    for r in rows:
        r["kind"] = classify(f"{r['title']} {r['note']}")'''
new = '''    # 应用人工更正（日期-城市错配）
    try:
        corr = json.loads((Path(__file__).resolve().parent.parent / "data" / "activity_corrections.json")
                          .read_text(encoding="utf-8"))
        for item in corr.get("items", []):
            for r in rows:
                if r["date"] == item["date"] and r.get("city") == item["from_city"]:
                    r["city"] = item["to_city"]
                    if item.get("to_title"):
                        r["title"] = item["to_title"]
                    r["note"] = (r.get("note") or "") + f"｜更正：{item['reason']}"
    except Exception as e:
        print("更正表读取失败:", e)

    for r in rows:
        r["kind"] = classify(f"{r['title']} {r['note']}")'''
assert s.count(old) == 1
s = s.replace(old, new)
if 'import json' not in s.split('\n')[0:10][0]:
    pass
p.write_text(s, encoding='utf-8')
print('构建器已接入更正')
