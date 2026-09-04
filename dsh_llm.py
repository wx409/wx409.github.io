# -*- coding: utf-8 -*-
"""DSH 本地模型调用助手（省 token 版）。

用法:
    from dsh_llm import ask
    print(ask("dsh-office", "把这段材料总结成3点：..."))
    print(ask("dsh-code", "写一个Python函数：...", max_tokens=1024))
    print(ask("dsh-deep", "复杂问题：..."))
"""
from openai import OpenAI

_client = OpenAI(base_url="http://127.0.0.1:11434/v1", api_key="ollama")


def ask(model: str, prompt: str, max_tokens: int = 512, temperature: float | None = None) -> str:
    """调用 DSH 本地模型。dsh-* 模型已内置系统提示，不要再发 system，省 token。"""
    kwargs = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": max_tokens}
    if temperature is not None:
        kwargs["temperature"] = temperature
    r = _client.chat.completions.create(**kwargs)
    return r.choices[0].message.content


if __name__ == "__main__":
    import sys
    model = sys.argv[1] if len(sys.argv) > 1 else "dsh-office"
    text = sys.argv[2] if len(sys.argv) > 2 else "你好"
    print(ask(model, text))
