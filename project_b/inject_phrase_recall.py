"""把「词句链式召回」区块注入 qa.html（幂等）"""
import io

P = r"D:\wx409.github.io\qa.html"
s = io.open(P, encoding="utf-8", errors="ignore").read()

if 'id="psInput"' in s:
    print("已存在，跳过")
    raise SystemExit(0)

BLOCK = '''
<section id="phraseRecall" style="margin:36px auto;max-width:820px;padding:0 16px">
  <h2 style="border-left:4px solid #c41e3a;padding-left:10px">查他说过的话</h2>
  <p id="psHint" style="color:#8a8a8a;font-size:13px;margin:6px 0 12px">
    输入任意词（如 低音、月亮、坚持），从词句库里按相关度召回，每条带出处。
  </p>
  <input id="psInput" type="text" placeholder="例如：低音 大海 / 月亮 / 坚持"
         style="width:100%;box-sizing:border-box;font:inherit;padding:12px 14px;border:1px solid #d8cfc0;border-radius:10px">
  <ul id="psRes" style="list-style:none;padding:0;margin:14px 0"></ul>
</section>
<script src="/assets/phrase-search.js"></script>
'''

marker = "<!-- FOOTER_NAV_START -->"
if marker in s:
    s = s.replace(marker, BLOCK + "\n" + marker, 1)
else:
    s = s.replace("</body>", BLOCK + "\n</body>", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("已注入词句召回区块，页面长度", len(s))
