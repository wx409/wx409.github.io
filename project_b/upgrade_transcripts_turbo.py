"""把此前用 small 转的 5 个补跑 turbo，并清理重复的小模型版本

用法：python -X utf8 project_b/upgrade_transcripts_turbo.py
"""
import glob, os, re, shutil, time
from opencc import OpenCC
from faster_whisper import WhisperModel

BASE = r"E:\wx\私有\王晰全文库\采访目录"
VID = os.path.join(BASE, "视频"); TXT = os.path.join(BASE, "全文")
ARCH = os.path.join(BASE, "全文_旧small")
os.makedirs(ARCH, exist_ok=True)

md = glob.glob(os.path.expanduser(
    "~/.cache/huggingface/hub/models--mobiuslabsgmbh--faster-whisper-large-v3-turbo/snapshots/*"))[0]
cc = OpenCC("t2s")
model = WhisperModel(md, device="cpu", compute_type="int8")
print("turbo 就绪")

FIX = [(r"王熙|王晰晰|王西", "王晰"), (r"希哥|晰哥儿", "晰哥"),
       (r"東方影響家|东方影响家", "东方艺享家"), (r"沈想与长歌|沉想与长歌", "沉响与长歌"),
       (r"聲入人心|声入人新", "声入人心")]

# 需要补跑的：视频文件名（去掉 .mp4）
targets = ["东方艺享家_视频播客_秦屹x王晰", "民族歌曲讲座_范唱与问答",
           "沉响与长歌_报道_身兼制作人"]
for name in targets:
    vp = os.path.join(VID, name + ".mp4")
    if not os.path.exists(vp):
        print("缺视频", name); continue
    t0 = time.time()
    segs, _ = model.transcribe(vp, language="zh", vad_filter=True, beam_size=5)
    lines = ["[%02d:%02d] %s" % (int(x.start) // 60, int(x.start) % 60, cc.convert(x.text.strip()))
             for x in segs]
    body = "\n".join(lines)
    for pat, rep in FIX:
        body = re.sub(pat, rep, body)
    out = os.path.join(TXT, name + "_转写_turbo.txt")
    open(out, "w", encoding="utf-8").write(
        "名称：%s\n模型：faster-whisper large-v3-turbo（本地，未校对）\n\n%s\n" % (name, body))
    # 旧 small 版归档
    for old in glob.glob(os.path.join(TXT, name + "_转写*.txt")):
        if "turbo" in old:
            continue
        shutil.move(old, os.path.join(ARCH, os.path.basename(old)))
    print("%-30s %d 段 %d 字 %.0fs" % (name[:30], len(lines), len(body), time.time() - t0))

# 清理「同一 mid 的 small 版」：已有 turbo 版的 mid，把 small 版归档
for small in glob.glob(os.path.join(TXT, "*_转写_*.txt")):
    base = os.path.basename(small)
    if "turbo" in open(small, encoding="utf-8", errors="ignore").read(200):
        continue
    m = re.match(r"(\d{15,20})_转写_", base)
    if not m:
        continue
    if glob.glob(os.path.join(TXT, m.group(1) + "_转写_*turbo*.txt")) or \
       any(m.group(1) in open(p, encoding="utf-8", errors="ignore").read(200)
           for p in glob.glob(os.path.join(TXT, "*turbo*.txt"))):
        shutil.move(small, os.path.join(ARCH, base))
        print("归档 small 版", base[:44])
print("旧 small 版归档到", ARCH)
