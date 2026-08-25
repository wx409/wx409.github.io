# -*- coding: utf-8 -*-
"""B站视频下载 + 摘要工具（省 token：纯规则 + bilibili 公开 API，零 LLM）

读：E:\\wx\\六巡\\20260823广州站\\bilibili链接.txt   （每行一个 B站链接或 BV 号）
写：E:\\wx\\六巡\\20260823广州站\\bilibili视频\\{BV}_{标题}.mp4
    E:\\wx\\六巡\\20260823广州站\\bilibili视频\\bilibili_summary.json / .md （摘要，方便查找）

下载顺序：
  1. yt-dlp（推荐，pip install yt-dlp 一次即可，支持最高清晰度）
  2. bilibili 官方 API（wbi 签名 + playurl，匿名可取 480p 起，无第三方依赖）
  3. 均失败 → 记录「需手动下载」清单（摘要照常生成）

用法：
  python project_b/download_bilibili.py [链接txt路径] [--no-download] [--force]
"""
import argparse, io, json, os, re, sys, time, hashlib, urllib.parse, urllib.request
from datetime import datetime
from pathlib import Path

DEFAULT_TXT = Path(r"E:\wx\六巡\20260823广州站\bilibili链接.txt")
DEFAULT_OUT = Path(r"E:\wx\六巡\20260823广州站\bilibili视频")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
REFERER = "https://www.bilibili.com/"
MIXIN_KEY_ENC_TAB = [46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
                     33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40, 61,
                     26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11, 36,
                     20, 34, 44, 52]


def http_get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {
        "User-Agent": UA, "Referer": REFERER, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def http_get_json(url, headers=None, timeout=20):
    return json.loads(http_get(url, headers, timeout).decode("utf-8", errors="replace"))


def extract_bvid(line):
    m = re.search(r"BV[0-9A-Za-z]{10}", line)
    return m.group(0) if m else None


def fmt_dur(sec):
    sec = int(sec or 0)
    return f"{sec // 60}:{sec % 60:02d}"


def fetch_view(bvid):
    """view API 摘要：标题/UP主/时长/简介/发布时间（匿名可访问，部分情况需降级）"""
    url = f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}"
    j = http_get_json(url)
    if j.get("code") != 0:
        return None
    d = j["data"]
    return {
        "bvid": bvid,
        "title": d.get("title", ""),
        "owner": d.get("owner", {}).get("name", ""),
        "duration": d.get("duration", 0),
        "desc": (d.get("desc") or "")[:120],
        "pubdate": datetime.fromtimestamp(d.get("pubdate", 0)).strftime("%Y-%m-%d") if d.get("pubdate") else "",
    }


# ---------- WBI 签名（bilibili playurl 需要） ----------
def get_mixin_key(orig):
    return "".join(orig[i] for i in MIXIN_KEY_ENC_TAB)[:32]


def enc_wbi(params, img_key, sub_key):
    mixin_key = get_mixin_key(img_key + sub_key)
    params["wts"] = round(time.time())
    params = dict(sorted(params.items()))
    params = {k: "".join(c for c in str(v) if c not in "!'()*") for k, v in params.items()}
    query = urllib.parse.urlencode(params)
    return query + "&wbi_sign=" + hashlib.md5((query + mixin_key).encode()).hexdigest()


def get_wbi_keys():
    j = http_get_json("https://api.bilibili.com/x/web-interface/nav")
    wbi = j.get("data", {}).get("wbi_img", {})
    img = wbi.get("img_url", "")
    sub = wbi.get("sub_url", "")
    return img.rsplit("/", 1)[-1].split(".")[0], sub.rsplit("/", 1)[-1].split(".")[0]


def playurl_durl(bvid):
    """老式 durl 接口：单文件同时含音视频（fnval 不传），匿名可取 480p，最兼容。"""
    view = fetch_view(bvid)
    if not view:
        return None
    j = http_get_json("https://api.bilibili.com/x/web-interface/view?bvid=" + bvid)
    if j.get("code") != 0 or not j["data"].get("pages"):
        return None
    cid = j["data"]["pages"][0]["cid"]
    img_key, sub_key = get_wbi_keys()
    query = enc_wbi({"bvid": bvid, "cid": cid, "qn": 64}, img_key, sub_key)
    j = http_get_json("https://api.bilibili.com/x/player/playurl?" + query)
    d = j.get("data") or {}
    dur = d.get("durl")
    if dur:
        return dur[0].get("url")
    return None


def playurl_480p(bvid):
    """dash 格式降级（durl 不可用时）：返回视频流/音频流 URL（需 ffmpeg 合并）。"""
    img_key, sub_key = get_wbi_keys()
    j = http_get_json("https://api.bilibili.com/x/web-interface/view?bvid=" + bvid)
    if j.get("code") != 0 or not j["data"].get("pages"):
        return None, None
    cid = j["data"]["pages"][0]["cid"]
    query = enc_wbi({"bvid": bvid, "cid": cid, "qn": 64, "fnval": 16, "fourk": 0},
                    img_key, sub_key)
    j = http_get_json("https://api.bilibili.com/x/player/playurl?" + query)
    d = j.get("data") or {}
    dash = d.get("dash") or {}
    v = (dash.get("video") or [{}])[0].get("baseUrl")
    a = (dash.get("audio") or [{}])[0].get("baseUrl")
    return v, a


def download_stream(url, dest, headers=None):
    req = urllib.request.Request(url, headers=headers or {"User-Agent": UA, "Referer": REFERER})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
        total = int(resp.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
    return got, total


def try_ytdlp(bvid, dest):
    try:
        import yt_dlp
    except Exception:
        return False, "未安装 yt-dlp"
    try:
        opts = {"outtmpl": str(dest).rsplit(".", 1)[0] + ".%(ext)s",
                "format": "bv*+ba/b", "merge_output_format": "mp4",
                "quiet": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([f"https://www.bilibili.com/video/{bvid}"])
        return True, ""
    except Exception as e:
        return False, str(e)[:120]


def get_session_cookie():
    """访问 bilibili.com 首页收集匿名会话 cookie（buvid3/buvid4），绕过 412 风控。"""
    import http.cookiejar
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.open(urllib.request.Request("https://www.bilibili.com/",
                                       headers={"User-Agent": UA}), timeout=15)
    return "; ".join(f"{c.name}={c.value}" for c in cj)


BILI_COOKIE_FILE = Path(r"E:\wx\私有工具\bilibili_cookie.json")


def load_bili_cookie():
    """B站登录 Cookie：优先读用户更新的 bilibili_cookies.txt（纯文本，E:\\wx\\index_records）；
    兜底 E:\\wx\\私有工具\\bilibili_cookie.json {"cookie": "SESSDATA=..."}。
    空间全量抓取需要登录态；普通 BV 链接下载不需要。"""
    try:
        t = Path(r"E:\wx\index_records\bilibili_cookies.txt").read_text(encoding="utf-8").strip()
        if t:
            return t
    except Exception:
        pass
    try:
        return json.loads(BILI_COOKIE_FILE.read_text(encoding="utf-8")).get("cookie", "")
    except Exception:
        return os.environ.get("BILI_COOKIE", "")


def fetch_space_bvids(mid):
    """拉取 B站用户空间全部视频的 BV 列表。
    实测：x/space/arc/search（旧接口）带登录 Cookie 可用；wbi 版接口返回 -403（风控），故用旧接口。"""
    cookie = get_session_cookie()
    extra = load_bili_cookie()
    if extra:
        cookie = cookie + "; " + extra
    headers = {"User-Agent": UA, "Referer": f"https://space.bilibili.com/{mid}",
               "Cookie": cookie}
    bvids, pn = [], 1
    while pn <= 20:
        j = None
        for _attempt in range(4):  # -799 限流：冷却 60s 重试
            try:
                j = http_get_json(
                    f"https://api.bilibili.com/x/space/arc/search?mid={mid}&ps=50&pn={pn}",
                    headers=headers)
            except Exception as e:
                raise RuntimeError(
                    f"B站空间接口被风控（{e}）。请配置 B站登录 Cookie："
                    f"E:\\wx\\index_records\\bilibili_cookies.txt（浏览器登录 bilibili.com 后 F12 复制完整 Cookie）")
            if j.get("code") == -799:
                print(f"  限流(-799)，冷却 60s 后重试…")
                time.sleep(60)
                continue
            break
        if j is None or j.get("code") != 0:
            raise RuntimeError(
                f"B站空间接口失败 code={j.get('code') if j else '?'} {j.get('message') if j else ''}；"
                f"需 B站登录 Cookie（E:\\wx\\index_records\\bilibili_cookies.txt）且避免高频请求")
        d = j.get("data") or {}
        vlist = (d.get("list") or {}).get("vlist") or []
        if not vlist:
            break
        for v in vlist:
            b = v.get("bvid")
            if b:
                bvids.append(b)
        if not d.get("has_more"):
            break
        pn += 1
        time.sleep(1.0)
    return bvids


def main():
    if sys.stdout and getattr(sys.stdout, "buffer", None):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser(description="B站视频下载+摘要")
    ap.add_argument("txt", nargs="?", default=str(DEFAULT_TXT))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--no-download", action="store_true", help="只生成摘要不下载")
    ap.add_argument("--force", action="store_true", help="强制重新下载")
    ap.add_argument("--space", default="", help="B站用户空间 MID，拉取该空间全部视频（如王晰 3493257487059302）")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if args.space:
        print(f"拉取空间 MID={args.space} 全部视频…")
        try:
            bvids = fetch_space_bvids(args.space)
        except Exception as e:
            print(f"!! {e}")
            print("提示：空间全量抓取需 B站登录 Cookie；替代方案——把空间视频链接逐条复制进 bilibili链接.txt 后重跑（普通 BV 下载不受风控影响）。")
            return
        print(f"空间视频 {len(bvids)} 个")
    else:
        txt = Path(args.txt)
        if not txt.exists():
            print(f"!! 链接文件不存在: {txt}"); return
        bvids = []
        for ln in txt.read_text(encoding="utf-8").splitlines():
            b = extract_bvid(ln)
            if b:
                bvids.append(b)
        print(f"读取到 {len(bvids)} 个 BV 号")
    if not bvids:
        return

    summary = []
    for i, bvid in enumerate(bvids, 1):
        print(f"\n[{i}/{len(bvids)}] {bvid}")
        try:
            info = fetch_view(bvid)
        except Exception as e:
            info = None
            print(f"  !! view API 失败: {e}")
        rec = {"no": i, "bvid": bvid, "title": "", "owner": "", "duration": 0,
               "desc": "", "pubdate": "", "status": "摘要获取失败", "file": ""}
        if info:
            rec.update(info)
            safe = re.sub(r'[\\/:*?"<>|\s]+', "_", rec["title"])[:60] or bvid
            rec["file"] = f"{bvid}_{safe}.mp4"
            rec["status"] = "待下载"
            print(f"  标题: {rec['title']} | UP主: {rec['owner']} | 时长: {fmt_dur(rec['duration'])}")

        dest = out / rec["file"]
        if args.no_download:
            pass
        elif not args.force and dest.exists() and dest.stat().st_size > 1024:
            rec["status"] = "已存在"
            print(f"  已存在: {dest.name}")
        else:
            ok, err = try_ytdlp(bvid, dest)
            if ok:
                rec["status"] = "已下载"
                print(f"  yt-dlp 下载完成 -> {dest.name}")
            elif "未安装" in err:
                # 降级1：durl 单文件（含音视频）
                try:
                    vurl = playurl_durl(bvid)
                    if vurl:
                        got, total = download_stream(vurl, dest)
                        rec["status"] = f"已下载(durl {got // 1048576}MB)"
                        print(f"  durl 下载完成 -> {dest.name}")
                    else:
                        # 降级2：dash 视频+音频分离
                        v2, a2 = playurl_480p(bvid)
                        if v2 and a2:
                            vf = str(dest)
                            af = str(dest).rsplit(".", 1)[0] + "_音频.m4s"
                            download_stream(v2, vf)
                            download_stream(a2, af)
                            rec["status"] = "已下载(视频+音频分离，需ffmpeg合并)"
                            print(f"  已下载视频+音频（{Path(vf).name} + 音频.m4s），合并需 ffmpeg")
                        else:
                            rec["status"] = "需手动下载（API 无流）"
                            print(f"  !! {rec['status']}")
                except Exception as e2:
                    rec["status"] = "需手动下载"
                    print(f"  !! API 下载失败: {e2}")
            else:
                rec["status"] = "需手动下载"
                print(f"  !! 下载失败: {err}")
        summary.append(rec)

    # 摘要输出
    (out / "bilibili_summary.json").write_text(
        json.dumps({"generated": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "items": summary}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = ["# B站视频清单（王晰「回」广州站 2026-08-23）", "",
          f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')} | 共 {len(summary)} 条 | 纯本地规则+公开 API，零 LLM", "",
          "| 序号 | BV | 标题 | UP主 | 时长 | 发布 | 状态 |", "|---|---|---|---|---|---|---|"]
    for r in summary:
        md.append(f"| {r['no']} | {r['bvid']} | {r['title']} | {r['owner']} | "
                  f"{fmt_dur(r['duration'])} | {r['pubdate']} | {r['status']} |")
    (out / "bilibili_summary.md").write_text("\n".join(md), encoding="utf-8")
    print(f"\n[OK] 摘要 -> {out / 'bilibili_summary.md'}")


if __name__ == "__main__":
    main()
