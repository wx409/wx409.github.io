# -*- coding: utf-8 -*-
"""声学档案的 Schema.org 结构化数据工厂（单一事实源，禁止在页面里手写 JSON-LD）

为什么单独抽出来：
  · voice.html 与 stage.html 是同一套研究方法（demucs 分离 + 逐帧 F0）的两个语料，
    结构化数据必须共享同一套「项目身份 / 版本谱系 / 口径说明」措辞，否则两页会漂移；
  · 版本谱系（isBasedOn v1）是学术引用友好标记：将来申请 DOI / Zenodo 时，
    这套字段可直接迁移，不必重写。

约定：
  · 数字一律由调用方从 manifest/JSON 派生后传入，本模块不写死任何数值；
  · 只输出可核验的客观陈述，不做「华语最低 / 唯一 / 排名」类断言。
"""
from __future__ import annotations

SITE = "https://wx409.github.io"
AUTHOR = {"@type": "Person", "name": "wx409", "url": SITE}
SUBJECT = {"@type": "Person", "name": "王晰", "url": SITE}
LICENSE = "https://creativecommons.org/licenses/by-nc/4.0/"


def research_project(*, name: str, url: str, description: str, date_modified: str,
                     dataset_url: str, based_on: list[dict], parts: list[dict],
                     keywords: list[str], method: str,
                     scope_note: str = "") -> dict:
    """研究项目对象（@type: ResearchProject）。

    based_on: 版本谱系（v1 → v2 的口径演进），每项形如
              {"@type": "Dataset", "name": "...", "datePublished": "YYYY-MM-DD",
               "description": "..."}
    parts:    本项目产出的数据集（Dataset 引用）
    """
    obj = {
        "@context": "https://schema.org",
        "@type": "ResearchProject",
        "name": name,
        "url": url,
        "description": description,
        "dateModified": date_modified,
        "creator": AUTHOR,
        "about": SUBJECT,
        "measurementTechnique": method,
        "keywords": keywords,
        "license": LICENSE,
        "hasPart": parts,
        "subjectOf": {"@type": "Dataset", "url": dataset_url},
    }
    if based_on:
        obj["isBasedOn"] = based_on
    if scope_note:
        obj["disambiguatingDescription"] = scope_note
    return obj


def faq_page(pairs: list[tuple[str, str]], *, url: str = "") -> dict:
    """FAQPage（问答对直接可被生成式引擎摘引，答案须自带口径与数字来源）。"""
    obj = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in pairs
        ],
    }
    if url:
        obj["url"] = url
    return obj


def dataset_ref(name: str, url: str, description: str = "") -> dict:
    d = {"@type": "Dataset", "name": name, "url": url}
    if description:
        d["description"] = description
    return d
