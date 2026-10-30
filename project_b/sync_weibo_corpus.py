"""weibo_archive* → wx_textmine_corpus 同步（幂等）
- 读 weibo_archive / weibo_archive_studio 的 index.json
- 每条未同步过的帖子写一个 txt：YYYY-MM-DD_HHMM_<账号>_<序号>.txt
- 幂等：已同步的 post id 记在 _synced_ids.json，跳过
- 不删除、不覆盖已有文件
"""
import json, os, re, sys, html
from datetime import datetime

CORPUS = r"E:\wx\wx_textmine_corpus"
SIDE = os.path.join(CORPUS, "_synced_ids.json")

SOURCES = [
    (r"E:\wx\私有工具\weibo_archive\index.json", "本人微博"),
    (r"E:\wx\私有工具\weibo_archive_studio\index.json", "工作室微博"),
]

def load_side():
    if os.path.exists(SIDE):
        try:
            return json.load(open(SIDE, encoding="utf-8"))
        except Exception:
            return {}
    return {}

def strip_html(s):
    s = s or ""
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    return html.unescape(s).strip()

def ts_of(p):
    for k in ("date", "created_at"):
        v = p.get(k)
        if not v:
            continue
        if k == "date" and re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            return v + " 0000"
        try:
            d = datetime.strptime(v.replace("+0800", "").strip(), "%a %b %d %H:%M:%S %Y")
            return d.strftime("%Y-%m-%d %H%M")
        except Exception:
            pass
    return "1970-01-01 0000"

def main():
    side = load_side()
    total_new = 0
    for idx_path, label in SOURCES:
        if not os.path.exists(idx_path):
            print("[skip] no index:", idx_path); continue
        d = json.load(open(idx_path, encoding="utf-8"))
        posts = d.get("posts") or d.get("data") or []
        outdir = os.path.join(CORPUS, label)
        os.makedirs(outdir, exist_ok=True)
        n_new = 0
        for p in posts:
            pid = str(p.get("id") or "")
            key = "%s:%s" % (label, pid)
            if not pid or key in side:
                continue
            ts = ts_of(p)
            base = ts.replace("-", "-").replace(" ", "_")
            fname = "%s_%s_001.txt" % (base, label.split("微")[0] or label)
            path = os.path.join(outdir, fname)
            i = 2
            while os.path.exists(path):
                fname = "%s_%s_%03d.txt" % (base, label.split("微")[0] or label, i)
                path = os.path.join(outdir, fname)
                i += 1
            body = strip_html(p.get("text") or p.get("text_html") or "")
            if not body:
                side[key] = "empty"
                continue
            with open(path, "w", encoding="utf-8") as f:
                f.write(body + "\n")
            side[key] = os.path.basename(path)
            n_new += 1
        print("%s: 新增 %d 条（共 %d）" % (label, n_new, len(posts)))
        total_new += n_new
    json.dump(side, open(SIDE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("本次新增合计", total_new)

if __name__ == "__main__":
    main()
