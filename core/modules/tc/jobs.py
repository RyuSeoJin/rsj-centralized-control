# -*- coding: utf-8 -*-
"""tc 모듈의 산출물 — regen.py가 켠 프로젝트에서 이 파일을 훑어 돌립니다

  기능 골격 HTML    spec/{슬러그}-feature-tree.md가 있을 때만
  TC 시트 xlsx      test-case/{슬러그}-tc-input-v1.0.json이 있을 때만

  **정본이 없으면 건너뜁니다.** 빈 정본으로 0노드 문서를 찍지 않습니다.
"""
import os

SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts")


def project_jobs(ctx):
    out, p, slug, pre = [], ctx["folder"], ctx["slug"], ctx["prefix"]
    t_md = os.path.join(p, "spec", "%s-feature-tree.md" % slug)
    if os.path.exists(t_md):
        o = os.path.join(p, "docs", "%s-feature-tree.html" % pre)
        out.append(("기능 골격 — " + slug, [t_md], o,
                    [ctx["python"], os.path.join(SCRIPTS, "gen_feature_tree_html.py"), t_md, "-o", o]))
    tc_in = os.path.join(p, "test-case", "%s-tc-input-v1.0.json" % slug)
    if os.path.exists(tc_in):
        o = os.path.join(p, "test-case", "%s-tc-v1.0.xlsx" % slug)
        out.append(("TC 시트 — " + slug, [tc_in], o,
                    [ctx["python"], os.path.join(SCRIPTS, "build_tc_template_xlsx.py"), tc_in, "-o", o]))
    return out
