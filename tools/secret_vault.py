#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DPAPI 文件加密保险库
====================
把明文密钥文件用 Windows DPAPI 加密成 .dpapi 文件，绑定当前 Windows
用户。只有本机当前用户能解密；拷到别处、别的用户、别的机器都无法还原。

适用：secrets.bat（GitHub PAT / DeepSeek key）、notify_config.json
（Server酱 SendKey）、radio_cookie.json（QQ音乐 Cookie）等本机密钥。

依赖：pip install pywin32

用法：
    python tools/secret_vault.py protect <file>       # 加密 -> file.dpapi，删除明文
    python tools/secret_vault.py reveal  <file>       # 解密 file.dpapi -> stdout（手动查看）
    python tools/secret_vault.py status               # 列出所有 .dpapi 文件状态
    python tools/secret_vault.py run <bat> <cmd...>   # 解密 .bat 注入环境变量后运行命令

示例：
    python tools/secret_vault.py protect secrets.bat
    python tools/secret_vault.py reveal  secrets.bat
    python tools/secret_vault.py run    secrets.bat python deploy.py
"""
import os
import sys
import glob

try:
    import win32crypt
except ImportError:
    print("[X] 需要 pywin32：pip install pywin32")
    sys.exit(1)


def protect(path: str) -> str:
    """加密文件 -> path.dpapi，删除原明文"""
    if not os.path.exists(path):
        print(f"[X] 文件不存在: {path}")
        return ""
    if path.endswith(".dpapi"):
        print(f"[!] 已经是加密文件: {path}")
        return ""
    with open(path, "rb") as f:
        data = f.read()
    if not data:
        print(f"[!] 文件为空: {path}")
        return ""
    blob = win32crypt.CryptProtectData(
        data, os.path.basename(path), None, None, None, 0
    )
    out = path + ".dpapi"
    with open(out, "wb") as f:
        f.write(blob)
    os.remove(path)
    print(f"[OK] 已加密: {path}")
    print(f"     -> {out}")
    print(f"     明文已删除（不可恢复，请确认 .dpapi 能解密后再清理备份）")
    return out


def reveal(path: str) -> bytes:
    """解密 .dpapi 文件，返回明文 bytes"""
    if not path.endswith(".dpapi"):
        path = path + ".dpapi"
    if not os.path.exists(path):
        # 也尝试同名 .dpapi
        alt = path + ".dpapi"
        if os.path.exists(alt):
            path = alt
        else:
            print(f"[X] 加密文件不存在: {path}")
            sys.exit(1)
    with open(path, "rb") as f:
        blob = f.read()
    _desc, data = win32crypt.CryptUnprotectData(blob, None, None, None, 0)
    return data


def _decode_text(data: bytes) -> str:
    """自动检测 .bat / 文本文件编码"""
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def cmd_reveal(path: str):
    data = reveal(path)
    try:
        sys.stdout.buffer.write(data)
        sys.stdout.buffer.write(b"\n")
    except Exception:
        print(_decode_text(data))


def cmd_run(bat_path: str, args: list):
    """解密 .bat，解析 set KEY=VALUE 注入环境变量，运行 args 命令"""
    data = reveal(bat_path)
    text = _decode_text(data)
    injected = 0
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith("set ") and "=" in line[4:]:
            body = line[4:]
            k, v = body.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"')
            if k and v:
                os.environ[k] = v
                injected += 1
                print(f"  [env] {k} = {'*' * min(len(v), 8)} ({len(v)} 字符已注入)")
    print(f"[OK] 注入了 {injected} 个环境变量")
    if not args:
        print("[!] 未指定要运行的命令")
        return
    import subprocess
    print(f"[RUN] {' '.join(args)}")
    rc = subprocess.call(args)
    sys.exit(rc)


def cmd_status():
    """列出常见位置的 .dpapi 文件状态"""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    found = []
    # 主站递归
    for dp in glob.glob(os.path.join(root, "**", "*.dpapi"), recursive=True):
        found.append(dp)
    # E 盘私有工具
    for extra in [r"E:\wx\私有工具", r"E:\wx\私有工具\radio_proxy"]:
        if os.path.isdir(extra):
            for dp in glob.glob(os.path.join(extra, "*.dpapi")):
                if dp not in found:
                    found.append(dp)
    if not found:
        print("（暂无 .dpapi 加密文件）")
        return
    print("已加密的密钥文件：")
    for dp in found:
        try:
            data = reveal(dp)
            print(f"  [OK] {dp}  (解密成功, 明文 {len(data)} 字节)")
        except Exception as e:
            print(f"  [ERR] {dp}  (解密失败: {e})")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "protect":
        if len(sys.argv) < 3:
            print("用法: protect <file>"); sys.exit(1)
        protect(sys.argv[2])
    elif cmd == "reveal":
        if len(sys.argv) < 3:
            print("用法: reveal <file>"); sys.exit(1)
        cmd_reveal(sys.argv[2])
    elif cmd == "run":
        if len(sys.argv) < 4:
            print("用法: run <bat> <cmd...>"); sys.exit(1)
        cmd_run(sys.argv[2], sys.argv[3:])
    elif cmd == "status":
        cmd_status()
    else:
        print(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
