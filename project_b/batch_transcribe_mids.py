"""批量：按 mids 下载微博视频 → 本地转写 → 繁转简+错名纠正

用法：python -X utf8 project_b/batch_transcribe_mids.py 5128496726674389 5128145411770407
"""
import glob, json, os, re, sys, time, urllib.request

BASE = r"E:\wx\私有\王晰全文库\采访目录"
TXT = os.path.join(BASE, "全文"); VID = os.path.join(BASE, "视频")
os.makedirs(TXT, exist_ok=True); os.makedirs(VID, exist_ok=True)

CK = open(r"E:\wx\index_records\wb.txt", encoding="utf-8", errors="ignore").read().strip()
H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
     "Referer": "https://m.weibo.cn/", "Cookie": CK, "X-Requested-With": "XMLHttpRequest"}
MODEL_DIR = glob.glob(os.path.expanduser(
    "~/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/*"))[0]

FIX = [(r"王熙|王晰晰|王西", "王晰"), (r"希哥|晰哥儿", "晰哥"),
       (r"東方影響家|东方影响家", "东方艺享家"), (r"沈想与长歌|沉想与长歌", "沉响与长歌"),
       (r"聲入人心|声入人新", "声入人心")]

def slug(s):
    return re.sub(r"[\\/:*?\"<>|\s]+", "_", s)[:44]

mids = sys.argv[1:]
if not mids:
    print("用法：batch_transcribe_mids.py <mid> [mid...]")
    raise SystemExit(2)

from opencc import OpenCC
cc = OpenCC("t2s")
from faster_whisper import WhisperModel
model = WhisperModel(MODEL_DIR, device="cpu", compute_type="int8")
print("模型就绪")

for mid in mids:
    try:
        r = json.loads(urllib.request.urlopen(
            urllib.request.Request("https://m.weibo.cn/statuses/show?id=%s" % mid, headers=H), timeout=25
        ).read().decode("utf-8", "ignore"))
    except Exception as e:
        print(mid, "拉取失败", type(e).__name__); continue
    d = r.get("data") or {}
    title = re.sub(r"<[^>]+>", "", d.get("text") or "")[:50].replace("\n", " ")
    pi = d.get("page_info") or {}
    vurl = ""
    if pi.get("media_info"):
        mi = pi["media_info"]
        vurl = mi.get("stream_url") or mi.get("mp4_720p_mp4") or mi.get("mp4_hd_url") or ""
    if not vurl:
        print(mid, "无视频，跳过"); continue

    s = slug(title) or mid
    vp = os.path.join(VID, "%s_%s.mp4" % (mid, s))
    if not (os.path.exists(vp) and os.path.getsize(vp) > 100000):
        try:
            data = urllib.request.urlopen(urllib.request.Request(vurl, headers=H), timeout=300).read()
            if len(data) > 100000:
                open(vp, "wb").write(data)
        except Exception as e:
            print(mid, "下载失败", type(e).__name__); continue
    size_mb = round(os.path.getsize(vp) / 1048576, 1)

    t0 = time.time()
    segs, info = model.transcribe(vp, language="zh", vad_filter=True, beam_size=5)
    lines = ["[%02d:%02d] %s" % (int(x.start) // 60, int(x.start) % 60, cc.convert(x.text.strip()))
             for x in segs]
    body = "\n".join(lines)
    for pat, rep in FIX:
        body = re.sub(pat, rep, body)
    out = os.path.join(TXT, "%s_转写_%s.txt" % (mid, s))
    open(out, "w", encoding="utf-8").write(
        "名称：%s\n链接：https://m.weibo.cn/detail/%s\n模型：faster-whisper small（本地，未校对）\n"
        "视频：%s（%.1f MB）\n\n%s\n" % (title, mid, os.path.basename(vp), size_mb, body))
    print("%s | %s｜%d 段｜%d 字｜%.0fs" % (mid, title[:28], len(lines), len(body), time.time() - t0))
