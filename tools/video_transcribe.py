# -*- coding: utf-8 -*-
"""本地音视频转文字闭环工具：ffmpeg 抽音 → faster-whisper 转写 → 时间戳分段 → 金句校验回写

用途（王晰 GEO 档案站·音视频转写对接 3.1 环节的本地自动化实现）：
  抓取到的视频（B站/本地直拍等）→ 直接在本机提取文字，无需云端 API。
  产物：
    temp/transcripts/<bvid或文件名>.segments.json   （meta + segments[{start,end,text}]，带时间戳）
    temp/transcripts/<同>.txt                         （纯文本，可进 transcript_pipeline --ingest-txt）
  金句校验（--verify-show）：
    将 data/tour/<date>-<city>.json 中 quotes[] 的 text 与分段文本做归一化模糊匹配，
    命中后 verified=true 并补 start/end 时间戳；同步更新 data/quotes.json（金句墙数据源）。

用法：
  python tools/video_transcribe.py --video <视频路径|bvid> [--model small|base|medium] [--threads 4]
  python tools/video_transcribe.py --video BV1aNhP65E4A --verify-show 2026-08-23 广州
  python tools/video_transcribe.py --bili-json E:\\wx\\私有工具\\show_feedback\\20260823_广州\\bili_feedback.json --video-dir E:\\wx\\私有工具\\bilibili_wangxi --dry-run

模型：faster-whisper（PyPI），默认 small（中文质量好）；模型缓存走 hf-mirror.com 镜像。
红线：仅本地转写公开来源视频；版权判断仍由 transcript_pipeline --precheck 把关，本工具不发布任何内容。
"""
import argparse, io, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

ROOT = Path(r"D:\wx409.github.io")
OUT_DIR = ROOT / "temp" / "transcripts"
VIDEO_DIRS = [Path(r"E:\wx\私有工具\bilibili_wangxi"), Path(r"E:\wx\六巡\20260823广州站\bilibili视频")]
MODEL_DIR = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "huggingface" / "hub"
CITY_PINYIN = {"重庆": "chongqing", "北京": "beijing", "上海": "shanghai", "广州": "guangzhou",
               "深圳": "shenzhen", "南京": "nanjing", "杭州": "hangzhou", "武汉": "wuhan",
               "长沙": "changsha", "成都": "chengdu", "南昌": "nanchang", "三亚": "sanya",
               "郑州": "zhengzhou", "昆明": "kunming", "南宁": "nanning", "延边": "yanbian",
               "澳门": "macao", "苏州": "suzhou", "乌鲁木齐": "wulumuqi", "伊宁": "yining",
               "舟山": "zhoushan", "庐山": "lushan", "莫斯科": "moscow", "河南": "henan"}

# 镜像下载：必须在 import faster_whisper / huggingface_hub 之前设置
# HF_HUB_DISABLE_XET=1：禁用新 Xet/CAS 存储后端（国内不可达），强制经典 LFS 走镜像
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")


def log(*a):
    print("[%s]" % time.strftime("%H:%M:%S"), *a, flush=True)


def find_video(bvid):
    """按 bvid 在本地视频目录找文件（文件名含 BV 号）"""
    for d in VIDEO_DIRS + [Path(r"E:\wx\私有工具\bilibili_wangxi")]:
        if not d.exists():
            continue
        for f in d.iterdir():
            if f.is_file() and f.suffix.lower() in (".mp4", ".mkv", ".flv", ".webm", ".mov", ".m4a", ".mp3", ".wav"):
                if bvid in f.name:
                    return f
    return None


def extract_audio(video, wav, ffmpeg_exe):
    """ffmpeg 抽 16k 单声道 wav（本地，无网络）"""
    r = subprocess.run([ffmpeg_exe, "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
                        "-f", "wav", str(wav)], capture_output=True, text=True, encoding="utf-8", errors="ignore")
    if r.returncode != 0:
        raise RuntimeError("ffmpeg 失败: " + (r.stderr or r.stdout or "")[-300:])
    return wav


def transcribe(wav, model_name, threads):
    from faster_whisper import WhisperModel  # 延迟导入：先设 HF_ENDPOINT
    model = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=threads)
    segs, info = model.transcribe(str(wav), language="zh", beam_size=1, vad_filter=True)
    out = []
    for s in segs:
        t = (s.text or "").strip()
        if t:
            out.append({"start": round(float(s.start), 1), "end": round(float(s.end), 1), "text": t})
    return out, (info.language or "zh")


def norm(s):
    """归一化：去空白与标点，仅留中日韩字符（含数字/字母），用于模糊匹配"""
    return re.sub(r"[^\u4e00-\u9fff\u3040-\u30ffA-Za-z0-9]", "", s or "")


def fmt_ts(sec):
    sec = int(sec or 0)
    return "%02d:%02d" % (sec // 60, sec % 60)


def verify_quotes(segments, show_json_path, quotes_data_path=None, seg_pointer=""):
    """金句 ↔ 分段模糊匹配（窗口相似度）：命中则 verified=true + start/end 时间戳。
    返回 (matched, unmatched, updated_quotes)"""
    from difflib import SequenceMatcher
    joined = []
    for s in segments:
        joined.append({"start": s["start"], "end": s["end"], "n": norm(s["text"])})
    full_n = "".join(x["n"] for x in joined)

    def best_window(qn):
        """滑动窗口找与金句相似度最高的位置（窗口为金句长度，步进 len/20）"""
        win = len(qn)
        if win < 4 or len(full_n) < win:
            return 0.0, -1
        step = max(1, win // 20)
        best_r, best_p = 0.0, -1
        for pos in range(0, len(full_n) - win + 1, step):
            r = SequenceMatcher(None, qn, full_n[pos:pos + win]).ratio()
            if r > best_r:
                best_r, best_p = r, pos
                if r > 0.85:
                    break
        return best_r, best_p

    show = json.loads(show_json_path.read_text(encoding="utf-8"))
    quotes = show.get("quotes") or []
    updated, matched, unmatched = [], [], []
    for q in quotes:
        # 已人工核实的条目不覆盖文本，仅尝试补时间戳
        already = q.get("verified") is True and q.get("ts")
        qn = norm(q.get("text", ""))
        if len(qn) < 6:
            unmatched.append((q.get("source_transcript_id"), q.get("text", "")[:20], "过短"))
            continue
        ratio, pos = best_window(qn)
        # 阈值：长句（润色稿容忍更多误听）0.52；短句从严 0.68
        thr = 0.52 if len(qn) >= 20 else 0.68
        if ratio < thr:
            unmatched.append((q.get("source_transcript_id"), q.get("text", "")[:20],
                              "未命中(相似%.2f)" % ratio))
            if not already:
                continue
            updated.append(q)
            matched.append((q.get("source_transcript_id"), q.get("ts", "?"),
                            q.get("text", "")[:24] + " (人工核实，机器稿未命中)"))
            continue
        # 定位命中位置所在分段（累计长度法）
        acc, seg_hit = 0, joined[0]
        for x in joined:
            if acc + len(x["n"]) > pos:
                seg_hit = x
                break
            acc += len(x["n"])
        q["verified"] = True
        q["start"] = seg_hit["start"]
        q["end"] = seg_hit["end"]
        q["ts"] = "%s-%s" % (fmt_ts(seg_hit["start"]), fmt_ts(seg_hit["end"]))
        updated.append(q)
        matched.append((q.get("source_transcript_id"), fmt_ts(seg_hit["start"]),
                        q.get("text", "")[:24] + " (相似%.2f)" % ratio))
    show["quotes"] = quotes
    # 全文转写仅本地存档（temp/，gitignore）；公开数据层只落摘要+指针（版权红线：饭拍仅公开摘要+引语）
    n_seg = len(segments)
    show["transcripts"] = [{
        "source_url": show.get("meta", {}).get("source_url", ""),
        "source_type": show.get("meta", {}).get("source_type", "fan_recording"),
        "engine": "faster-whisper", "model": "small", "local": True,
        "transcribed_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "segment_count": n_seg,
        "duration_sec": round(segments[-1]["end"], 1) if n_seg else 0,
        "pointer": "temp/transcripts/" + seg_pointer,
        "note": "全文转写仅本地存档（版权红线：饭拍仅公开摘要+关键引语，标注BV号可复核）",
    }]
    show.setdefault("meta", {})["updated_at"] = time.strftime("%Y-%m-%d %H:%M")
    show_json_path.write_text(json.dumps(show, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[存档] 全文转写 %d 段已归档 -> %s (transcripts[0].segments)" % (len(segments), show_json_path.name))
    print("[校验] %s 共 %d 条金句：命中 %d / 未命中 %d" % (show_json_path.name, len(quotes), len(matched), len(unmatched)))
    for m in matched:
        print("  ✓ %s @%s | %s" % m)
    for u in unmatched:
        print("  ✗ %s | %s | %s" % u)
    # 同步金句墙数据源 data/quotes.json：先按 id+前缀覆盖，未覆盖的条目用窗口匹配直接补时间戳
    if quotes_data_path and quotes_data_path.exists():
        qd = json.loads(quotes_data_path.read_text(encoding="utf-8"))
        qlist = qd.get("quotes") or []
        for i, old in enumerate(qlist):
            old_id = old.get("source_transcript_id")
            for q in updated:
                if old_id == q.get("source_transcript_id") and \
                        norm(old.get("text", ""))[:12] == norm(q.get("text", ""))[:12]:
                    qlist[i]["verified"] = True
                    qlist[i]["start"] = q.get("start")
                    qlist[i]["end"] = q.get("end")
                    qlist[i]["ts"] = q.get("ts")
                    break
            else:
                # 公开版文案与 tour 版不同：直接对 quotes.json 文本做窗口匹配补时间戳
                if old.get("ts"):
                    continue
                qn = norm(old.get("text", ""))
                if len(qn) < 6:
                    continue
                ratio, pos = best_window(qn)
                thr = 0.52 if len(qn) >= 20 else 0.68
                if ratio < thr:
                    continue
                acc, seg_hit = 0, joined[0]
                for x in joined:
                    if acc + len(x["n"]) > pos:
                        seg_hit = x
                        break
                    acc += len(x["n"])
                qlist[i]["start"] = seg_hit["start"]
                qlist[i]["end"] = seg_hit["end"]
                qlist[i]["ts"] = "%s-%s" % (fmt_ts(seg_hit["start"]), fmt_ts(seg_hit["end"]))
                print("  ⊕ quotes.json %s 独立匹配 @%s (相似%.2f)" % (old_id, qlist[i]["ts"], ratio))
        qd["quotes"] = qlist
        quotes_data_path.write_text(json.dumps(qd, ensure_ascii=False, indent=1), encoding="utf-8")
        print("[校验] data/quotes.json 已同步 verified/时间戳")
    return updated, unmatched


def main():
    if sys.stdout and getattr(sys.stdout, "buffer", None):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="本地音视频转文字闭环（ffmpeg + faster-whisper）")
    ap.add_argument("--video", help="视频/音频路径，或 BV 号（自动在本地视频目录查找）")
    ap.add_argument("--bili-json", help="B站反馈 JSON（bili_feedback.json），批量模式：按 bvid 找本地文件")
    ap.add_argument("--video-dir", default="", help="批量模式视频目录（默认 E:\\wx\\私有工具\\bilibili_wangxi）")
    ap.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium"])
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--dry-run", action="store_true", help="批量模式只列出可转写视频，不执行")
    ap.add_argument("--verify-show", nargs=2, metavar=("DATE", "CITY"),
                    help="转写后校验金句并回写，如 --verify-show 2026-08-23 广州")
    args = ap.parse_args()

    from imageio_ffmpeg import get_ffmpeg_exe
    ffmpeg = get_ffmpeg_exe()
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.bili_json:
        items = json.loads(Path(args.bili_json).read_text(encoding="utf-8"))
        vdirs = [Path(args.video_dir)] if args.video_dir else VIDEO_DIRS
        tasks = []
        for v in items:
            bvid = v.get("bvid", "")
            for d in vdirs:
                if not d.exists():
                    continue
                for f in d.iterdir():
                    if f.is_file() and bvid in f.name:
                        tasks.append((bvid, f, v.get("title", "")))
                        break
                if any(t[0] == bvid for t in tasks):
                    break
        print("[批量] %d 个视频中，本地有 %d 个可转写" % (len(items), len(tasks)))
        for bvid, f, title in tasks:
            print("  %s | %s | %s" % (bvid, f.name, title[:30]))
        if args.dry_run or not tasks:
            return
        for bvid, f, _t in tasks:
            segs, lang = transcribe_workflow(bvid, f, args.model, args.threads, ffmpeg)
            print("")
        return

    if not args.video:
        ap.print_help()
        return

    video = Path(args.video)
    bvid = ""
    if not video.exists():
        bvid = args.video
        found = find_video(bvid)
        if not found:
            print("!! 未找到本地视频: %s（批量模式请用 --bili-json）" % args.video)
            return
        video = found
    if not bvid:
        m = re.search(r"(BV[0-9A-Za-z]+)", video.name)
        bvid = m.group(1) if m else video.stem
    segs, lang, seg_file = transcribe_workflow(bvid, video, args.model, args.threads, ffmpeg)

    if args.verify_show:
        date, city = args.verify_show
        pinyin = CITY_PINYIN.get(city, city)
        show_json = ROOT / "data" / "tour" / ("%s-%s.json" % (date, pinyin))
        if not show_json.exists():
            print("!! show json 不存在: %s" % show_json)
        else:
            verify_quotes(segs, show_json, ROOT / "data" / "quotes.json", seg_file.name)


def transcribe_workflow(bvid, video, model_name, threads, ffmpeg):
    """单视频转写主流程：抽音 → 转写 → 落盘 segments.json + txt"""
    # 文件名已含 BV 号时不重复拼接
    stem = video.stem[:20] if (bvid and video.stem.startswith(bvid)) else ("%s_%s" % (bvid, video.stem[:20]) if bvid else video.stem)
    seg_json = OUT_DIR / (stem + ".segments.json")
    seg_txt = OUT_DIR / (stem + ".txt")
    if seg_json.exists():
        log("%s 已有转写产物，跳过（删除 %s 可重跑）" % (bvid or video.name, seg_json.name))
        return json.loads(seg_json.read_text(encoding="utf-8"))["segments"], "zh", seg_json
    t0 = time.time()
    log("① 抽音: %s (%s)" % (video.name, "%.0fMB" % (video.stat().st_size / 1048576)))
    wav = Path(tempfile.mkdtemp(prefix="wx_asr_")) / "audio.wav"
    extract_audio(video, wav, ffmpeg)
    log("② 转写（模型=%s, CPU×%d, int8）: %s" % (model_name, threads, wav.name))
    segs, lang = transcribe(wav, model_name, threads)
    try:
        wav.unlink()
    except Exception:
        pass
    meta = {"bvid": bvid, "file": video.name, "engine": "faster-whisper", "model": model_name,
            "lang": lang, "segments": len(segs), "duration": round(segs[-1]["end"], 1) if segs else 0,
            "transcribed_at": time.strftime("%Y-%m-%d %H:%M:%S"), "local": True}
    seg_json.write_text(json.dumps({"meta": meta, "segments": segs}, ensure_ascii=False, indent=1), encoding="utf-8")
    seg_txt.write_text("\n".join("%.1f\t%.1f\t%s" % (s["start"], s["end"], s["text"]) for s in segs), encoding="utf-8")
    log("③ 完成: %d 段 / %.0f 分钟 -> %s" % (len(segs), (segs[-1]["end"] or 0) / 60, seg_json.name))
    log("   用时 %.0f 秒" % (time.time() - t0))
    return segs, lang, seg_json


if __name__ == "__main__":
    main()
