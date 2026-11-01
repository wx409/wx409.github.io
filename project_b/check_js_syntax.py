"""用 node 真正解析页面内联脚本，验证语法（比数括号可靠）"""
import io
import os
import re
import subprocess
import tempfile

P = r"D:\wx409.github.io\tavern\index.html"
s = io.open(P, encoding="utf-8", errors="ignore").read()

ok = True
for idx, mm in enumerate(re.finditer(r"<script([^>]*)>(.*?)</script>", s, re.S), 1):
    attrs, body = mm.group(1), mm.group(2).strip()
    if "application/ld+json" in attrs or "json" in attrs:
        continue
    if not body:
        continue
    if "divCard" in body:
        name = "起卦脚本"
    elif "diceFace" in body:
        name = "今日签脚本"
    else:
        name = "脚本#%d" % idx
    f = os.path.join(tempfile.gettempdir(), "check_%d.js" % idx)
    io.open(f, "w", encoding="utf-8").write(body)
    r = subprocess.run(["node", "--check", f], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    status = "OK" if r.returncode == 0 else "语法错误"
    print("%-10s %s" % (name, status))
    if r.returncode != 0:
        ok = False
        print((r.stderr or "")[:600])
print("汇总:", "全部通过" if ok else "存在错误")
