#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""线上核验（audit_live.py）——把「审计通过 ≠ 部署成功」这个盲区堵掉。

设计输入（全部来自一次真实误报：外部核验报告"两张图 404 + 线上仍是旧图"，
实测为假——图片在仓库、线上 200、sha256 与指纹一致，误报原因是**推送/Pages 边缓存窗口**）：

  1. 资产核验用 **sha256 对指纹**，不做"渲染比对"（图内文字无法可靠机读）；
  2. 所有 URL 加 **cache-buster**，绕过 CDN/Pages 边缓存；
  3. 失败**退避重试 2–3 次**再判 FAIL；
  4. **网络不可达显式 SKIP**（exit 0 + 醒目提示），绝不把抓取异常判成断链；
  5. 黑名单**语境化匹配**（`2.34` 是逐曲跨度的合法值，裸匹配会误报）；
  6. 推送后建议 `--wait` 或延迟数分钟运行，给 Pages 构建/缓存失效留窗口。

检查项：
  A. voice.html 引用的全部站内图片 HTTP 200
  B. 线上长图 sha256 == assets/voice/acoustic_id_card.fingerprint.json 的 png_sha256
  C. llms.txt 关键数字与本地派生值一致（最低 B1 61.5Hz / 稳定性 7 音分 / 跨度 2.30 / 覆盖 1282 天）
  D. sitemap.xml 条数与本地一致 + 抽样 lastmod 不倒挂（不早于该页 git 最后提交日）
  E. 陈旧数字黑名单语境化扫描（2.25 八度 / 跨度中位 2.34 / 音准偏差 5 音分 / 890 天 / NoneHz / 旧 B1 句式）

用法：
  python -X utf8 project_b/audit_live.py                  # 全量核验
  python -X utf8 project_b/audit_live.py --wait 180       # 先等 3 分钟（Pages 构建窗口）
  python -X utf8 project_b/audit_live.py --skip-if-unpushed   # deploy_all 用：本地未推送则 SKIP
  python -X utf8 project_b/audit_live.py --retries 3 --timeout 20
退出码：0=通过或 SKIP；1=存在真实不一致。
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://wx409.github.io"
UA = {"User-Agent": "Mozilla/5.0 (compatible; wx409-audit-live/1.0)"}

problems: list[str] = []
skips: list[str] = []
notes: list[str] = []


# ---------------------------------------------------------------- HTTP 层
class Net:
    """带 cache-buster + 退避重试的抓取器；区分「网络不可达」与「真失败」。"""

    def __init__(self, retries: int, timeout: int) -> None:
        self.retries = max(1, retries)
        self.timeout = timeout
        self.network_down = False
        self.fetched = 0

    def get(self, path: str, *, bust: bool = True) -> tuple[int | None, bytes]:
        url = path if path.startswith("http") else f"{BASE}/{path.lstrip('/')}"
        if bust:
            url += ("&" if "?" in url else "?") + f"_cb={int(time.time() * 1000)}"
        last_err = ""
        for i in range(self.retries):
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    data = r.read()
                    self.fetched += 1
                    return r.status, data
            except urllib.error.HTTPError as e:
                # 4xx/5xx 是「服务端真实回应」，重试仍 4xx 才算失败
                last_err = f"HTTP {e.code}"
                code = e.code
                if 400 <= e.code < 500:
                    return code, b""
            except Exception as e:                     # DNS / 超时 / 连接被拒
                last_err = f"{type(e).__name__}: {e}"
            if i < self.retries - 1:
                time.sleep(1.5 * (i + 1))              # 退避
        if "HTTP" not in last_err:
            self.network_down = True                   # 全程网络层异常 → 疑似断网
        return None, last_err.encode()


def local(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def git_last_commit_date(rel: str) -> str:
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel],
                           cwd=str(ROOT), capture_output=True, timeout=30)
        return r.stdout.decode("utf-8", "replace").strip()
    except Exception:
        return ""


def check(label: str, expect, actual) -> None:
    good = expect == actual
    print(f"[{'OK  ' if good else 'FAIL'}] {label}: 期望 {expect} / 实际 {actual}")
    if not good:
        problems.append(f"{label}: 期望 {expect} / 实际 {actual}")


# ---------------------------------------------------------------- 检查项
def check_images(net: Net) -> None:
    st, data = net.get("voice.html")
    if st != 200:
        problems.append(f"voice.html 抓取失败（{data[:60]!r}）")
        return
    text = data.decode("utf-8", "replace")
    refs = set(re.findall(r'<img[^>]+src="([^"]+)"', text))
    for m in re.finditer(r'<meta[^>]+(?:property|name)="og:image"[^>]*>', text):
        mm = re.search(r'content="([^"]+)"', m.group(0))
        if mm:
            refs.add(mm.group(1))
    for u in sorted(refs):
        if u.startswith("http") and "wx409.github.io" not in u:
            continue
        rel = u.split("wx409.github.io/", 1)[1] if u.startswith("http") else u.lstrip("/")
        rel = rel.split("?")[0]
        st2, d2 = net.get(rel)
        check(f"线上图片 {rel}", 200, st2 if st2 is not None else f"抓取失败({d2[:40]!r})")


def check_fingerprint(net: Net) -> None:
    fp = local("assets/voice/acoustic_id_card.fingerprint.json")
    st, data = net.get("assets/voice/acoustic_id_card.png")
    if st != 200:
        problems.append(f"线上长图抓取失败（{st}）")
        return
    sha = hashlib.sha256(data).hexdigest()
    check("线上长图 sha256 == 指纹登记", fp["png_sha256"], sha)
    check("线上长图字节数", len(open(ROOT / "assets/voice/acoustic_id_card.png", "rb").read()), len(data))


def check_llms(net: Net) -> None:
    alb = local("data/archive_vocal_albums.json")["summary"]
    cal = {c["id"]: c["value"] for c in local("data/calibers.json")["calibers"]}
    st, data = net.get("llms.txt")
    if st != 200:
        problems.append(f"llms.txt 抓取失败（{st}）")
        return
    text = data.decode("utf-8", "replace")
    want = {
        f"最低稳定音 {alb['lowest']['note']} {alb['lowest']['hz']}Hz": alb["lowest"]["hz"],
        f"音符内稳定性中位 {alb['stability_cents_median']:.0f} 音分": alb["stability_cents_median"],
        f"跨度中位 {alb['span_median_octaves']:.2f} 个八度": alb["span_median_octaves"],
        f"指数数据覆盖 {cal['index_days']} 天": cal["index_days"],
    }
    for label in want:
        check(f"llms.txt 含「{label}」", True, label in text)


def check_sitemap(net: Net) -> None:
    st, data = net.get("sitemap.xml")
    if st != 200:
        problems.append(f"sitemap.xml 抓取失败（{st}）")
        return
    live = data.decode("utf-8", "replace")
    local_txt = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    check("sitemap 条数（线上 == 本地）", local_txt.count("<url>"), live.count("<url>"))
    # 抽样 lastmod 不倒挂：线上 lastmod 不得早于该页 git 最后提交日
    entries = re.findall(r"<loc>([^<]+)</loc>\s*<lastmod>([^<]+)</lastmod>", live)
    sample = [e for e in entries if e[0].endswith(".html")][:5]
    for loc, lm in sample:
        rel = loc.split("wx409.github.io/", 1)[-1]
        g = git_last_commit_date(rel)
        if g and lm < g:
            problems.append(f"sitemap lastmod 倒挂：{rel} 线上 {lm} < git {g}")
            print(f"[FAIL] sitemap lastmod 倒挂: {rel} 线上 {lm} < git {g}")
        else:
            print(f"[OK  ] sitemap lastmod {rel}: {lm}（git {g or '—'}）")


def check_blacklist(net: Net) -> None:
    """语境化黑名单：裸数字会误伤逐曲合法值，必须带上下文。"""
    rules = [
        (r"跨度中位[^。<]{0,14}2\.25", "跨度中位 2.25（旧中位数口径）"),
        (r"2\.25\s*个八度", "2.25 个八度（旧中位数口径）"),
        (r"跨度中位[^。<]{0,14}2\.34", "跨度中位 2.34（取上中位偏差）"),
        (r"音准偏差中位\s*5\s*音分", "音准偏差中位 5 音分（已作废措辞）"),
        (r"890\s*天", "890 天（指数覆盖天数陈旧）"),
        (r"—（NoneHz）", "NoneHz 渲染缺陷"),
        (r"1 首歌曲（《多听有益》）最低稳定音达 B1", "旧 B1 句式（未分统计范围）"),
        (r"B1–F#2|B1-F#2", "旧低音主区写法 B1–F#2"),
        # 过程稿措辞（2026-09-09 决策：旧口径叙述一律不上线）
        (r"旧口径", "旧口径叙述"),
        (r"v1 口径|v1 曾|v1 报告", "方法版本号叙述"),
        (r"口径升级|口径变更", "口径变更叙述"),
        (r"结论修正", "结论修正叙述"),
        (r"瞬时最低", "瞬时最低列/叙述"),
        (r"已作废", "已作废叙述"),
    ]
    pages = ["voice.html", "stage.html", "index.html", "llms.txt"]
    for page in pages:
        st, data = net.get(page)
        if st != 200:
            problems.append(f"{page} 抓取失败（{st}）")
            continue
        text = data.decode("utf-8", "replace")
        hit = [desc for pat, desc in rules if re.search(pat, text)]
        if hit:
            problems.append(f"{page} 命中陈旧数字：{'、'.join(hit)}")
            print(f"[FAIL] {page} 命中陈旧数字：{'、'.join(hit)}")
        else:
            print(f"[OK  ] {page} 陈旧数字黑名单零残留（语境化匹配）")


# ---------------------------------------------------------------- 主流程
def head_matches_remote() -> bool | None:
    try:
        r = subprocess.run(["git", "ls-remote", "origin", "main"], cwd=str(ROOT),
                           capture_output=True, timeout=40)
        remote = r.stdout.decode().split()[0] if r.stdout.strip() else ""
        local_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(ROOT),
                                    capture_output=True, timeout=20).stdout.decode().strip()
        return bool(remote) and remote == local_head
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="线上核验")
    ap.add_argument("--retries", type=int, default=3, help="抓取失败重试次数（默认 3）")
    ap.add_argument("--timeout", type=int, default=20, help="单次请求超时秒（默认 20）")
    ap.add_argument("--wait", type=int, default=0, help="开始前等待秒数（给 Pages 构建窗口）")
    ap.add_argument("--skip-if-unpushed", action="store_true",
                    help="本地 HEAD 与远端不一致时直接 SKIP（供 deploy_all 末尾调用）")
    ap.add_argument("--skip-if-dirty", action="store_true",
                    help="工作区有未提交改动时直接 SKIP（流水线运行中必然如此，避免误报）")
    args = ap.parse_args()

    if args.skip_if_dirty:
        try:
            r = subprocess.run(["git", "status", "--porcelain"], cwd=str(ROOT),
                               capture_output=True, timeout=30)
            if r.stdout.strip():
                print("[SKIP] 工作区存在未提交改动（流水线运行中属正常）——线上核验跳过；"
                      "push 后跑菜单「89 线上核验」或 python -X utf8 project_b/audit_live.py --wait 180")
                return 0
        except Exception:
            pass

    if args.skip_if_unpushed:
        same = head_matches_remote()
        if same is False:
            print("[SKIP] 本地 HEAD 与远端 main 不一致（改动尚未推送）——线上核验跳过；"
                  "push 后请跑菜单「89 线上核验」或 python -X utf8 project_b/audit_live.py")
            return 0
        if same is None:
            print("[warn] 无法读取远端 HEAD（网络不可达），继续尝试线上核验")

    if args.wait:
        print(f"[wait] 等待 {args.wait}s，给 Pages 构建/缓存失效留窗口…")
        time.sleep(args.wait)

    print("=" * 68)
    print("线上核验 audit_live.py（cache-buster + 退避重试 + 语境化黑名单）")
    print("=" * 68)
    net = Net(args.retries, args.timeout)

    for fn in (check_images, check_fingerprint, check_llms, check_sitemap, check_blacklist):
        print(f"\n--- {fn.__name__} ---")
        try:
            fn(net)
        except Exception as e:
            problems.append(f"{fn.__name__} 异常: {type(e).__name__}: {e}")
            print(f"[FAIL] {fn.__name__} 异常: {e}")

    print("\n" + "-" * 68)
    print(f"抓取 {net.fetched} 次｜问题 {len(problems)} 项")

    # 网络不可达 → SKIP（不误判为断链）
    if net.network_down and net.fetched == 0:
        print("[SKIP] 网络不可达（DNS/超时/连接被拒）——本次线上核验跳过，"
              "不代表部署失败；联网后重跑本脚本。")
        return 0
    if net.network_down:
        print("[warn] 部分请求网络层异常，已计入问题清单，请核对是否为本机网络波动。")

    if problems:
        print("\n结论：线上核验发现不一致 —— 必须修，禁止当作部署成功。")
        for x in problems:
            print("  -", x)
        return 1
    print("\n结论：线上核验通过 ✅（图片 200 + sha256 对指纹 + 关键数字一致 + 黑名单零残留）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
