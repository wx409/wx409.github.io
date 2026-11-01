"""电台代理守护：没运行就拉起来（后台、不弹窗），并报告 Cookie 状态

用法：
  python -X utf8 project_b\\radio_proxy_guard.py          # 检查，必要时启动
  python -X utf8 project_b\\radio_proxy_guard.py --status # 只看状态
"""
import json
import os
import subprocess
import sys
import time
import urllib.request

PORT = 8787
BASE = r"E:\wx\私有工具\radio_proxy"
SCRIPT = os.path.join(BASE, "radio_proxy.py")


def health(timeout=4):
    try:
        r = json.loads(urllib.request.urlopen("http://127.0.0.1:%d/health" % PORT, timeout=timeout)
                       .read().decode("utf-8", "ignore"))
        return r
    except Exception:
        return None


def start():
    pyw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    exe = pyw if os.path.exists(pyw) else sys.executable
    flags = 0
    if os.name == "nt":
        flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([exe, SCRIPT], cwd=BASE, creationflags=flags,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)




def probe_vkey(mid=None):
    """取一首歌试 vkey；purl 为空说明 Cookie 失效或无该曲版权。"""
    import json as _j
    if not mid:
        try:
            d = _j.load(open(r"D:\wx409.github.io\data\tavern_audio.json", encoding="utf-8"))
            eps = d if isinstance(d, list) else (d.get("episodes") or d.get("items") or [])
            mid = eps[0].get("mid") if eps else None
        except Exception:
            mid = None
    if not mid:
        return None
    try:
        r = _j.loads(urllib.request.urlopen(
            "http://127.0.0.1:%d/vkey?mid=%s" % (PORT, mid), timeout=20).read().decode("utf-8", "ignore"))
        urls = r.get("urls") or []
        return bool(urls and urls[0])
    except Exception:
        return None

def main():
    st = health()
    if "--status" in sys.argv:
        if st:
            print("电台代理：运行中 ｜ Cookie：%s" % ("已设置 ✅" if st.get("cookie") else "未设置 ❌"))
        else:
            print("电台代理：未运行 ❌（执行不带参数的命令可拉起）")
        return 0

    if st and st.get("cookie"):
        okv = probe_vkey()
        if okv:
            print("电台代理：运行中，Cookie 有效 ✅（试取音频成功）")
            return 0
        if okv is False:
            print("电台代理：运行中，Cookie 已设置，但**取不到音频直链** —— Cookie 很可能已过期 ❌")
            print("  修复：浏览器登录 https://y.qq.com → F12 → Console 执行：")
            print('  fetch("http://127.0.0.1:%d/setcookie?cookie=" + encodeURIComponent(document.cookie))' % PORT)
            return 3
        print("电台代理：运行中，Cookie 已设置（未能探测音频，可能网络问题）")
        return 0
    if st and not st.get("cookie"):
        print("电台代理：运行中，但 Cookie 未设置 —— 需要在 y.qq.com 登录后执行一次 /setcookie")
        return 2

    print("电台代理未运行，正在后台启动…")
    start()
    for _ in range(10):
        time.sleep(1.5)
        st = health()
        if st:
            print("已启动 ｜ Cookie：%s" % ("已设置 ✅" if st.get("cookie") else "未设置 ❌"))
            return 0 if st.get("cookie") else 2
    print("启动失败：请手动运行 启动电台代理.bat 看报错")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
