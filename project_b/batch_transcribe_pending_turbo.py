"""批量转写全部「有视频但未转写」的微博链接：先下视频，等 turbo 模型就绪后统一转写

用法：python -X utf8 project_b/batch_transcribe_pending_turbo.py [--model turbo|small]
"""
import glob, json, os, re, sys, time, urllib.request

BASE = r"E:\wx\私有\王晰全文库\采访目录"
TXT = os.path.join(BASE, "全文"); VID = os.path.join(BASE, "视频")
os.makedirs(TXT, exist_ok=True); os.makedirs(VID, exist_ok=True)

CK = open(r"E:\wx\index_records\wb.txt", encoding="utf-8", errors="ignore").read().strip()
H = {"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148",
     "Referer": "https://m.weibo.cn/", "Cookie": CK, "X-Requested-With": "XMLHttpRequest"}

WANT = "turbo" if "--model" not in sys.argv or sys.argv[sys.argv.index("--model") + 1] == "turbo" else "small"
def model_dir():
    if WANT == "turbo":
        pats = [os.path.expanduser("~/.cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/snapshots/*")]
    else:
        pats = [os.path.expanduser("~/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/*")]
    for pat in pats:
        for d in glob.glob(pat):
            if os.path.exists(os.path.join(d, "model.bin")):
                return d
    return ""

# 待转写清单
audit = json.load(open(os.path.join(BASE, "视频审计.json"), encoding="utf-8"))
todo = [r for r in audit if r["video"] and not r["transcript"]]
json.dump({"started": time.strftime("%Y-%m-%d %H:%M"), "model": WANT, "requested": len(todo), "state": "running"},
          open(os.path.join(BASE, "转写状态.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("待转写", len(todo))

def slug(s):
    return re.sub(r"[\\/:*?\"<>|\s]+", "_", s)[:44]

# 1) 先下视频
vids = []
for r in todo:
    mid, title = r["mid"], r["title"]
    s = slug(title) or mid
    vp = os.path.join(VID, "%s_%s.mp4" % (mid, s))
    if not (os.path.exists(vp) and os.path.getsize(vp) > 100000):
        try:
            j = json.loads(urllib.request.urlopen(
                urllib.request.Request("https://m.weibo.cn/statuses/show?id=%s" % mid, headers=H), timeout=25
            ).read().decode("utf-8", "ignore"))
            pi = (j.get("data") or {}).get("page_info") or {}
            mi = pi.get("media_info") or {}
            u = mi.get("stream_url") or mi.get("mp4_720p_mp4") or mi.get("mp4_hd_url") or ""
            if u:
                data = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=300).read()
                if len(data) > 100000:
                    open(vp, "wb").write(data)
        except Exception as e:
            print("  下载失败", mid, type(e).__name__)
    if os.path.exists(vp):
        vids.append((mid, title, vp))
print("视频就绪", len(vids), "个")

# 2) 等模型
md = model_dir()
if not md:
    print("模型未就绪，等待下载完成…")
    for _ in range(720):
        time.sleep(30)
        md = model_dir()
        if md:
            break
if not md:
    print("模型仍未就绪，退出（下次再跑）")
    raise SystemExit(3)
print("模型：", md)

from opencc import OpenCC
from faster_whisper import WhisperModel
cc = OpenCC("t2s")
model = WhisperModel(md, device="cpu", compute_type="int8")

FIX = [(r"王熙|王晰晰|王西", "王晰"), (r"希哥|晰哥儿", "晰哥"),
       (r"東方影響家|东方影响家", "东方艺享家"), (r"沈想与长歌|沉想与长歌", "沉响与长歌"),
       (r"聲入人心|声入人新", "声入人心")]

done_list, skip_list = [], []
for mid, title, vp in vids:
    t0 = time.time()
    try:
        segs, _ = model.transcribe(vp, language="zh", vad_filter=True, beam_size=5)
        lines = ["[%02d:%02d] %s" % (int(x.start) // 60, int(x.start) % 60, cc.convert(x.text.strip()))
                 for x in segs]
    except Exception as e:
        print("  转写失败", mid, type(e).__name__); continue
    body = "\n".join(lines)
    for pat, rep in FIX:
        body = re.sub(pat, rep, body)
    if len(body) < 100:
        skip_list.append(mid)
        print("  %s 无有效语音，跳过（%d 字）" % (mid, len(body)))
        continue
    out = os.path.join(TXT, "%s_转写_%s.txt" % (mid, slug(title)))
    open(out, "w", encoding="utf-8").write(
        "名称：%s\n链接：https://m.weibo.cn/detail/%s\n模型：faster-whisper %s（本地，未校对）\n\n%s\n"
        % (title, mid, WANT, body))
    done_list.append(mid)
    print("  %s | %-26s %d 段 %d 字 %.0fs" % (mid, title[:26], len(lines), len(body), time.time() - t0))
# 完成：写状态文件 + 站内通知
done_info = {"finished": time.strftime("%Y-%m-%d %H:%M"), "model": WANT,
             "requested": len(todo), "transcribed": len(done_list),
             "skipped": len(skip_list)}
json.dump(done_info, open(os.path.join(BASE, "转写状态.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
try:
    import sys as _s
    _s.path.insert(0, r"D:\wx409.github.io\project_b")
    import notify as _n
    _n.record("视频转写完成（%s）" % WANT,
              "本次 %d 条：转写 %d 条、跳过 %d 条（无有效语音）｜明细见 采访目录\全文\*_转写_*.txt"
              % (len(todo), len(done_list), len(skip_list)))
    print("已写站内通知")
except Exception as e:
    print("通知写入失败", type(e).__name__)
print("全部完成")
