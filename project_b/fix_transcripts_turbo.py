"""turbo 转写后处理：扩充错名纠正 + 统一标注（可重复运行）"""
import glob, os, re

TXT = r"E:\wx\私有\王晰全文库\采访目录\全文"

FIX = [
    (r"东方印象家|东方艺想家|东方艺享嘉|东方向往家", "东方艺享家"),
    (r"王熙|王晰晰|王西(?![瓜])", "王晰"),
    (r"晰哥儿|希哥", "晰哥"),
    (r"沈想与长歌|沉想与长歌|陈响与长歌", "沉响与长歌"),
    (r"聲入人心|声入人新|声入人心(?!·)", "声入人心"),
    (r"嘠达梅林", "嘎达梅林"),
    (r"乌苏里船歌|乌苏里船歌", "乌苏里船歌"),
    (r"秦屹|秦毅(?=主持)", "秦屹"),
    (r"胖蜀黍|胖叔叔(?=独家)", "胖蜀黍"),
    (r"流水纪|刘水纪", "流水纪"),
]

n = 0
for f in sorted(glob.glob(os.path.join(TXT, "*_turbo.txt"))):
    s = open(f, encoding="utf-8", errors="ignore").read()
    orig = s
    for pat, rep in FIX:
        s = re.sub(pat, rep, s)
    if s != orig:
        open(f, "w", encoding="utf-8").write(s)
        n += 1
print("修正文件", n, "个")
for f in sorted(glob.glob(os.path.join(TXT, "*_turbo.txt")))[:3]:
    head = open(f, encoding="utf-8", errors="ignore").read().splitlines()
    print(" ", os.path.basename(f)[:40], "→", head[4][:60] if len(head) > 4 else "")
