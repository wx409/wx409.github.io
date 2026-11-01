"""从 操作中心.bat 解析出「全流程图」→ docs/操作中心全图.md

产出内容：
  - 分组（A~W）与组内编号、说明
  - 每个编号对应的跳转标签与执行的脚本
  - 常用场景速查（自然语言 → 编号）
"""
import io
import re

BAT = r"D:\wx409.github.io\操作中心.bat"
OUT = r"D:\wx409.github.io\docs\操作中心全图.md"

lines = io.open(BAT, encoding="gbk", errors="ignore").read().splitlines()

# 1) 菜单：分组 + 编号 + 说明
group = "（未分组）"
menu = []
for l in lines:
    s = l.strip()
    m = re.match(r"^echo\s*\[([A-Z])\s*·\s*(.+?)\]$", s)
    if m:
        group = "%s · %s" % (m.group(1), m.group(2))
        menu.append(("__group__", group, ""))
        continue
    m = re.match(r"^echo\s+(\d+)\.\s*(.+)$", s)
    if m:
        menu.append((group, m.group(1), m.group(2).strip()))

# 2) 分派：编号 → 标签
disp = {}
for l in lines:
    s = l.strip()
    m = re.match(r'^if "%op%"=="(\d+)" goto (\w+)$', s)
    if m:
        disp[m.group(1)] = m.group(2)

# 3) 标签块：标签 → 执行的脚本（取块内前 6 行）
blocks = {}
cur = None
for l in lines:
    s = l.strip()
    if s.startswith(":"):
        cur = s[1:]
        blocks[cur] = []
        continue
    if cur and len(blocks[cur]) < 12:
        blocks[cur].append(s)

def script_of(tag):
    for s in blocks.get(tag, []):
        m = re.search(r"project_b\\([\w\u4e00-\u9fa5]+\.py)", s)
        if m:
            return m.group(1)
        m = re.search(r"([\w\u4e00-\u9fa5]+\.(py|bat))", s)
        if m:
            return m.group(1)
    return ""

rows = []
seen_num = {}
for g, num, desc in menu:
    if g == "__group__":
        rows.append(("GROUP", num, ""))
        continue
    tag = disp.get(num, "")
    sc = script_of(tag) if tag else ""
    flag = "（编号重复）" if num in seen_num else ""
    seen_num[num] = 1
    rows.append(("ITEM", num, "%s｜%s｜%s%s" % (desc, tag or "无分派", sc, flag)))

with io.open(OUT, "w", encoding="utf-8") as f:
    f.write("# 操作中心全图（自动生成，%d 项）\n\n" % sum(1 for r in rows if r[0] == "ITEM"))
    f.write("> 由 `操作中心.bat` 解析生成。改完 bat 后重跑 `python -X utf8 project_b\\dump_ops_map.py`。\n\n")
    f.write("| 编号 | 说明 | 标签 | 脚本 |\n|---|---|---|---|\n")
    for kind, a, b in rows:
        if kind == "GROUP":
            f.write("\n**%s**\n\n| 编号 | 说明 | 标签 | 脚本 |\n|---|---|---|---|\n" % a)
            continue
        parts = b.split("｜")
        f.write("| %s | %s | %s | %s |\n" % (a, parts[0], parts[1] if len(parts) > 1 else "",
                                              parts[2] if len(parts) > 2 else ""))

print("已生成", OUT, "｜条目", sum(1 for r in rows if r[0] == "ITEM"))
dup = [n for n, c in __import__("collections").Counter(
    a for k, a, _ in rows if k == "ITEM").items() if c > 1]
print("重复编号:", sorted(set(dup)))
