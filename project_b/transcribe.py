"""王晰素材本地转写总入口（统一流程）

用法：
  # 1) 单条微博链接（自动下视频→转写）
  python -X utf8 project_b/transcribe.py --weibo https://m.weibo.cn/detail/5128496726674389

  # 2) 本地视频/音频文件
  python -X utf8 project_b/transcribe.py --file "E:\\wx\\xxx.mp4"

  # 3) 目录批量（跳过已转写的）
  python -X utf8 project_b/transcribe.py --dir "E:\\wx\\私有\\王晰全文库\\采访目录\\视频"

  # 4) 把「采访杂志根表」里所有有视频未转写的补完
  python -X utf8 project_b/transcribe.py --pending

  通用参数：--model auto|turbo|small   --lang zh   --force（已存在也重跑）
           --min-chars 100（低于此视为无语音，不写文件）  --list-models
输出：采访目录\\全文\\<名字>_转写_<model>.txt
索引：采访目录\\转写索引.json（累积）
"""
import argparse
import glob
import json
import os
import re
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transcript_clean import clean_text, is_noise, list_models, model_dir  # noqa: E402

BASE = r"E:\wx\私有\王晰全文库\采访目录"
TXT = os.path.join(BASE, "全文")
VID = os.path.join(BASE, "视频")
INDEX = os.path.join(BASE, "转写索引.json")
CK = r"E:\wx\index_records\wb.txt"
H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
     "Referer": "https://m.weibo.cn/", "X-Requested-With": "XMLHttpRequest"}


def slug(s, n=44):
    return re.sub(r"[\\/:*?\"<>|\s]+", "_", s or "")[:n]


def cookie():
    try:
        ck = open(CK, encoding="utf-8", errors="ignore").read().strip()
        return ck.split(":", 1)[1].strip() if ck.lower().startswith("cookie:") else ck
    except Exception:
        return ""


def load_index():
    if os.path.exists(INDEX):
        return json.load(open(INDEX, encoding="utf-8"))
    return {"count": 0, "items": []}


def save_index(rec):
    idx = load_index()
    for i, it in enumerate(idx["items"]):
        if it.get("out") == rec.get("out"):
            idx["items"][i] = rec
            break
    else:
        idx["items"].append(rec)
    idx["count"] = len(idx["items"])
    idx["updated"] = time.strftime("%Y-%m-%d %H:%M")
    json.dump(idx, open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def weibo_video(url):
    """返回 (标题, 视频直链, mid)；非视频返回 None"""
    m = re.search(r"(?:detail/|weibo\.com/\d+/)(\d{6,})", url)
    if not m:
        return None
    mid = m.group(1)
    h = dict(H, Cookie=cookie())
    j = json.loads(urllib.request.urlopen(
        urllib.request.Request("https://m.weibo.cn/statuses/show?id=%s" % mid, headers=h), timeout=30
    ).read().decode("utf-8", "ignore"))
    d = j.get("data") or {}
    title = re.sub(r"<[^>]+>", "", d.get("text") or "")[:48].replace("\n", " ")
    pi = d.get("page_info") or {}
    mi = pi.get("media_info") or {}
    v = mi.get("stream_url") or mi.get("mp4_720p_mp4") or mi.get("mp4_hd_url") or ""
    return (title or mid, v, mid) if v else None


def download(url, path):
    h = dict(H, Cookie=cookie())
    data = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=300).read()
    if len(data) < 100000:
        return 0
    open(path, "wb").write(data)
    return len(data)


def transcribe_one(model, path, title, model_name, lang="zh", min_chars=100, force=False):
    out = os.path.join(TXT, "%s_转写_%s.txt" % (slug(title), model_name))
    if os.path.exists(out) and not force:
        return ("skip", out, 0)
    t0 = time.time()
    segs, _ = model.transcribe(path, language=lang, vad_filter=True, beam_size=5)
    lines = []
    for s in segs:
        line = "[%02d:%02d] %s" % (int(s.start) // 60, int(s.start) % 60, clean_text(s.text))
        if is_noise(line):
            continue
        lines.append(line)
    body = "\n".join(lines)
    if len(body) < min_chars:
        return ("no-speech", "", len(body))
    open(out, "w", encoding="utf-8").write(
        "名称：%s\n模型：faster-whisper %s（本地，未人工校对）\n时长：%d 段\n\n%s\n"
        % (title, model_name, len(lines), body))
    return ("ok", out, len(body), round(time.time() - t0))


ROOT_TABLE = os.path.join(BASE, "采访杂志根表.json")


def register_to_root(src, title, out_name, chars, model_name, date_hint=""):
    """把转写结果并回采访杂志根表（按链接去重），并重生成 md。"""
    if not os.path.exists(ROOT_TABLE):
        return False
    table = json.load(open(ROOT_TABLE, encoding="utf-8"))
    key = (src or "").split("?")[0]
    hit = None
    for it in table["items"]:
        if key and (it.get("链接") or "").split("?")[0] == key:
            hit = it
            break
        if not key and (it.get("名称") or "")[:20] == (title or "")[:20]:
            hit = it
            break
    if hit is None:
        hit = {"名称": (title or "")[:80], "类型": "采访", "时间": date_hint,
               "链接": src, "全文路径": "", "字数": 0,
               "渠道": "转写入口（手工/链接）", "状态": "", "备注": ""}
        table["items"].append(hit)
    hit["全文路径"] = out_name
    hit["字数"] = chars
    hit["状态"] = "已存（本地转写·%s）" % model_name
    hit["备注"] = (hit.get("备注") or "转写入口登记").strip("｜")
    table["count"] = len(table["items"])
    table["updated"] = time.strftime("%Y-%m-%d")
    json.dump(table, open(ROOT_TABLE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # md 由 json 派生
    try:
        import subprocess
        subprocess.call([sys.executable, "-X", "utf8",
                         os.path.join(os.path.dirname(os.path.abspath(__file__)), "slim_root_table.py")])
    except Exception:
        pass
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weibo")
    ap.add_argument("--file")
    ap.add_argument("--dir")
    ap.add_argument("--pending", action="store_true", help="补完根表/审计里未转写的视频")
    ap.add_argument("--model", default="auto")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--min-chars", type=int, default=100)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--no-register", action="store_true", help="不写入采访杂志根表")
    a = ap.parse_args()

    if a.list_models:
        for k, ok, d in list_models():
            print("%-6s %s %s" % (k, "可用" if ok else "缺失", d))
        return 0

    name, md = model_dir(a.model)
    if not md:
        print("模型不可用：", a.model)
        return 2
    print("模型：%s（%s）" % (name, md))
    from faster_whisper import WhisperModel
    model = WhisperModel(md, device="cpu", compute_type="int8")

    jobs = []  # (path, title, src)
    if a.weibo:
        r = weibo_video(a.weibo)
        if not r:
            print("该链接没有视频")
            return 1
        title, vurl, mid = r
        p = os.path.join(VID, "%s_%s.mp4" % (mid, slug(title)))
        if not (os.path.exists(p) and os.path.getsize(p) > 100000):
            n = download(vurl, p)
            print("  已下 %.1f MB" % (n / 1048576))
        jobs.append((p, title, a.weibo))
    if a.file:
        jobs.append((a.file, slug(os.path.basename(a.file), 40), a.file))
    if a.dir:
        for f in sorted(glob.glob(os.path.join(a.dir, "*"))):
            if f.lower().endswith((".mp4", ".m4a", ".wav", ".mp3")):
                jobs.append((f, slug(os.path.basename(f), 40), f))
    if a.pending:
        ap_ = os.path.join(BASE, "视频审计.json")
        if os.path.exists(ap_):
            for r in json.load(open(ap_, encoding="utf-8")):
                if r["video"] and not r["transcript"]:
                    for f in glob.glob(os.path.join(VID, "*%s*" % r["mid"])):
                        jobs.append((f, r["title"], "https://m.weibo.cn/detail/%s" % r["mid"]))
                        break

    if not jobs:
        print("没有可处理的输入")
        return 1

    ok = skip = nospeech = 0
    for path, title, src in jobs:
        try:
            res = transcribe_one(model, path, title, name, a.lang, a.min_chars, a.force)
        except Exception as e:
            print("  失败 %-30s %s" % (title[:30], type(e).__name__))
            continue
        if res[0] == "ok":
            ok += 1
            print("  ✅ %-30s %d 字 %.0fs" % (title[:30], res[2], res[3]))
            save_index({"title": title, "src": src, "model": name, "out": os.path.basename(res[1]),
                        "chars": res[2], "at": time.strftime("%Y-%m-%d %H:%M")})
            if not a.no_register:
                register_to_root(src, title, os.path.basename(res[1]), res[2], name)
        elif res[0] == "skip":
            skip += 1
        else:
            nospeech += 1
            print("  ⏭  %-30s 无有效语音（%d 字）" % (title[:30], res[2]))

    print("完成：转写 %d｜跳过已存在 %d｜无语音 %d｜共 %d" % (ok, skip, nospeech, len(jobs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
