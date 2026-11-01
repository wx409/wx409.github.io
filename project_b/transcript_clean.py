"""转写共用件：本地模型发现 + 文本清洗（繁转简、错名纠正、去口水）

被 transcribe.py 使用；其它脚本也可 import 复用，避免三处各写一份纠正表。
"""
import glob
import os
import re

MODELS = {
    "small": "models--Systran--faster-whisper-small",
    "turbo": "models--mobiuslabsgmbh--faster-whisper-large-v3-turbo",
}

# 错名纠正表（按出现频率与已发现错误累积；命中即替换）
FIX = [
    (r"东方印象家|东方艺想家|东方艺享嘉|东方向往家|东方影响家", "东方艺享家"),
    (r"王熙|王晰晰|王熹|王西(?![瓜])", "王晰"),
    (r"(?<![王])熹(?=的|在|哥|这)", "晰"),
    (r"晰哥儿|希哥", "晰哥"),
    (r"沈想与长歌|沉想与长歌|陈响与长歌", "沉响与长歌"),
    (r"聲入人心|声入人新", "声入人心"),
    (r"嘠达梅林", "嘎达梅林"),
    (r"秦毅(?=主持)", "秦屹"),
    (r"胖叔叔(?=独家)", "胖蜀黍"),
    (r"刘水纪", "流水纪"),
    (r"音乐流水季", "音乐流水纪"),
    (r"胖蜀黍独家|胖叔叔独家", "胖蜀黍独家"),
]

# 纯口水/无信息片段（整段丢弃）
DROP = re.compile(r"^(嗯+|啊+|哦+|呃+|对+|是+|好+|哈+|谢+|拜拜|那个|然后|就是)$")

# 整行丢弃：视频水印、台标、字幕组签名
NOISE_LINE = re.compile(
    r"优优.{0,6}独播剧场|YoYo Television|Subscribe|字幕由|字幕组|"
    r"关注.{0,4}公众号|扫码|下载.{0,4}APP|本视频由.{0,10}制作", re.I)


def model_dir(name="auto"):
    """返回本地模型目录；auto 时优先 turbo，其次 small。"""
    order = ["turbo", "small"] if name == "auto" else [name]
    base = os.path.expanduser("~/.cache/huggingface/hub")
    for key in order:
        repo = MODELS.get(key)
        if not repo:
            continue
        for snap in glob.glob(os.path.join(base, repo, "snapshots", "*")):
            if os.path.exists(os.path.join(snap, "model.bin")):
                return key, snap
    return "", ""


def list_models():
    out = []
    for key in MODELS:
        k, d = model_dir(key)
        out.append((key, bool(k), d))
    return out


def clean_text(text, to_simplified=True):
    """繁转简 + 错名纠正 + 去首尾空白"""
    if to_simplified:
        try:
            import opencc
            text = opencc.OpenCC("t2s").convert(text)
        except Exception:
            pass
    for pat, rep in FIX:
        text = re.sub(pat, rep, text)
    return text.strip()


def is_noise(line):
    body = re.sub(r"^\[\d{2}:\d{2}\]\s*", "", line).strip()
    if not body:
        return True
    if NOISE_LINE.search(body):
        return True
    return bool(DROP.match(body))
