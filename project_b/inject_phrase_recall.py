"""把「词句链式召回」区块注入 qa.html（v2：分「他说过的话 / 歌词」+ 类型筛选）"""
import io
import re

P = r"D:\wx409.github.io\qa.html"
s = io.open(P, encoding="utf-8", errors="ignore").read()

# 移除旧区块（若存在）
s = re.sub(r'<section id="phraseRecall".*?</section>\s*(<script src="/assets/phrase-search\.js"></script>)?\s*', "", s, flags=re.S)

BLOCK = '''
<section id="phraseRecall" style="margin:36px auto;max-width:820px;padding:0 16px">
  <h2 style="border-left:4px solid #c41e3a;padding-left:10px">他说过的话 / 歌词句子</h2>
  <p id="psHint" style="color:#8a8a8a;font-size:13px;margin:6px 0 12px">
    输入关键词，先给采访与现场原话，歌词单列在下面，每条都带出处。
  </p>
  <input id="psInput" type="text" placeholder="例如：低音 / 大海 / 坚持 / 月亮"
         style="width:100%;box-sizing:border-box;font:inherit;padding:12px 14px;border:1px solid #d8cfc0;border-radius:10px">
  <div id="psChips" style="display:flex;gap:8px;flex-wrap:wrap;margin:12px 0 4px"></div>
  <ul id="psRes" style="list-style:none;padding:0;margin:12px 0"></ul>
</section>
<script src="/assets/phrase-search.js"></script>
'''

marker = "<!-- FOOTER_NAV_START -->"
if marker in s:
    s = s.replace(marker, BLOCK + "\n" + marker, 1)
else:
    s = s.replace("</body>", BLOCK + "\n</body>", 1)

io.open(P, "w", encoding="utf-8").write(s)
print("已注入 v2 召回区块，页面长度", len(s))
