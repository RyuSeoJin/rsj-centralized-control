# -*- coding: utf-8 -*-
"""qa-site 모듈의 산출물 — regen.py가 켠 모듈의 이 파일을 훑어 돌립니다

  워크스페이스   루트 index.html (진입 층 — 중앙 규칙 구조 · 프로젝트 생성 방식)
  프로젝트       {접두}-dictionary.html (정본 dictionary md가 있을 때만)
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CSS = os.path.join(HERE, "design-guide", "design-guide-master.css")
SCRIPTS = os.path.join(HERE, "scripts")


def _rule_sources(core):
    out = []
    for kind in ("base", "modules"):
        for cur, _d, names in os.walk(os.path.join(core, kind)):
            if "__pycache__" in cur:
                continue
            out += [os.path.join(cur, n) for n in names if n.endswith((".md", ".py"))]
    return out


def workspace_jobs(ctx):
    idx = os.path.join(ctx["root"], "index.html")
    return [("워크스페이스 문서", _rule_sources(ctx["core"]), idx,
             [ctx["python"], os.path.join(SCRIPTS, "gen_intro_html.py"), "--repo-root", ctx["root"],
              "--slug", "none", "--css", CSS, "-o", idx])]


def project_jobs(ctx):
    d_md = ctx["managed"]("dictionary")
    if not os.path.exists(d_md):
        return []
    o = os.path.join(ctx["folder"], "docs", "%s-dictionary.html" % ctx["prefix"])
    return [("용어집 — " + ctx["slug"], [d_md], o,
             [ctx["python"], os.path.join(SCRIPTS, "gen_dictionary_html.py"),
              d_md, "--css", CSS, "-o", o])]
