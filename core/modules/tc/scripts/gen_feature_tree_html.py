# -*- coding: utf-8 -*-
"""feature-tree.md (정본) -> feature-tree.html (파생, 자기완결 단일 파일)

파이프라인에서의 위치
--------------------
  spec/{프로젝트}-feature-tree.md   (정본)
    │  parse_feature_tree.parse()   (md 형식 v2)
    ▼
  이 스크립트 — 템플릿 01-feature-tree 구조로 HTML 생성
    · 생성 시점의 design-guide-master.css 전문을 <style>에 inline (자기완결)
    · 신규 CSS 클래스를 만들지 않는다 — 마스터 토큰 재사용:
        유형: chip-det/ban/prob/rub · P: chip-high/mid/low
        범위: 구현=chip-ok · 보류=chip-part · 제외=chip-no · 출처: 기본 chip
    · TC 관계도 섹션은 두지 않는다(2026-08-05) — 케이스 사이의 선행 관계는 TC 시트의
      열과 추적 매트릭스가 이미 담는다. 여기 또 두면 같은 관계의 세 번째 사본이 되고,
      기능 골격은 「기능이 무엇인가」에 집중한다

사용법:
    python gen_feature_tree_html.py spec/…-feature-tree.md -o spec/…-feature-tree.html
"""
import argparse
import datetime
import html
import io
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
# 모듈 도구는 base의 공용 부품(shell.py·norm.py)을 씁니다. 모듈은 base 위에서만 돕니다 —
# 반대 방향(base가 모듈을 부르는 것)은 두지 않습니다
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "base", "scripts"))
import shell  # noqa: E402
from parse_feature_tree import parse  # noqa: E402

TYPE_CHIP = {"결정적": "chip-det", "금칙": "chip-ban",
             "확률적": "chip-prob", "루브릭": "chip-rub"}
PRI_CHIP = {"High": "chip-high", "Medium": "chip-mid", "Low": "chip-low"}
SCOPE_CHIP = {"구현": "chip-ok", "보류": "chip-part", "제외": "chip-no"}


def esc(s):
    return html.escape(s, quote=False)


def chips(node):
    out = []
    if node["type"]:
        out.append(f'<span class="chip {TYPE_CHIP[node["type"]]}">{node["type"]}</span>')
    if node["priority"]:
        out.append(f'<span class="chip {PRI_CHIP[node["priority"]]}">{node["priority"]}</span>')
    if node["source"]:
        out.append(f'<span class="chip">{node["source"]}</span>')
    if node["scope"]:
        out.append(f'<span class="chip {SCOPE_CHIP[node["scope"]]}">{node["scope"]}</span>')
    # 상태 선언 — 그 기능 단위를 확인해야 하는 상태 목록. 마스터 토큰 재사용(신규 클래스 금지)
    if node.get("states"):
        out.append(f'<span class="chip">상태: {esc(node["states"])}</span>')
    return " ".join(out)


def render_tree(nodes):
    """flat 노드 목록(depth 포함)을 중첩 <ul class="tree">로 변환한다."""
    parts = ['<ul class="tree">']
    prev_depth = 0
    for n in nodes:
        d = n["depth"]
        if d > prev_depth:
            parts.append("<ul>" * (d - prev_depth))
        elif d < prev_depth:
            parts.append("</li>" + "</ul></li>" * (prev_depth - d))
        elif prev_depth:
            parts.append("</li>")
        seg = [f'<li><span class="depth-tag">D{d}</span>'
               f'<span class="node">{esc(n["name"])}</span>']
        c = chips(n)
        if c:
            seg.append(" " + c)
        if n["pre"]:
            seg.append(f' <span class="note">PRE: {esc(" / ".join(n["pre"]))}</span>')
        if n["note"]:
            seg.append(f' <span class="note">{esc(n["note"])}</span>')
        parts.append("".join(seg))
        prev_depth = d
    parts.append("</li>" + "</ul></li>" * (prev_depth - 1) + "</ul>")
    return "\n".join(parts)


def main():
    # 한글 출력이 콘솔 기본 인코딩으로 나가면, 다른 도구가 받아 읽을 때 깨집니다.
    # 오류는 stderr로 나가므로 둘 다 맞춥니다
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("-o", "--output", required=True)
    args = ap.parse_args()
    # 없는 파일이면 스택을 쏟지 않고 한 줄로 알립니다 — 대개 경로를 잘못 친 경우입니다
    if not os.path.exists(args.input):
        sys.exit("그런 파일이 없습니다: %s" % args.input)

    with io.open(args.input, encoding="utf-8") as f:
        data = parse(f.read())
    if not data["nodes"]:
        sys.exit("트리 노드를 찾지 못함")

    # scripts → tc → modules → core. 이름이 repo면 저장소 루트로 읽혀 다음 이동에서 조용히 틀린다
    core = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    css_path = os.path.join(core, "base", "design-guide", "design-guide-master.css")
    with io.open(css_path, encoding="utf-8") as f:
        css = f.read()
    js_path = os.path.join(core, "base", "design-guide", "design-guide-master.js")
    js = io.open(js_path, encoding="utf-8").read() if os.path.exists(js_path) else ""
    css_ver = "v1.0"
    for line in css.splitlines():
        if line.strip().startswith("v") and "(" in line:
            css_ver = line.strip().split()[0]
            break

    nodes = data["nodes"]
    leaves = [n for n in nodes if n["type"]]
    n_impl = sum(1 for n in leaves if n["scope"] == "구현")
    n_hold = sum(1 for n in nodes if n["scope"] == "보류")
    n_excl = sum(1 for n in nodes if n["scope"] == "제외")
    max_d = max(n["depth"] for n in nodes)
    det_pct = round(100 * sum(1 for n in leaves if n["type"] == "결정적") / len(leaves))
    today = datetime.date.today().isoformat()
    proj, ver = data["project"], data["version"]

    # 사이드바에서 열리는 문서이므로 셸을 입힌다 — 메뉴로 들어와 메뉴가 사라지면 돌아갈 길이 없다
    proj_dir = os.path.dirname(os.path.dirname(os.path.abspath(args.input)))
    rel = os.path.relpath(proj_dir, os.path.dirname(os.path.abspath(args.output)))
    rel = rel.replace(os.sep, "/")
    rel = "" if rel == "." else rel + "/"
    body_open = shell.open_body(
        proj, "tree", rel, "기능 골격",
        "골격 v%s" % ver, out_path=args.output)
    body_close = shell.close_body()

    unknown_rows = "\n".join(
        f'    <tr><td>{esc(u["path"])}</td><td>{esc(u["value"])}</td>'
        f'<td>{esc(u["how"])}</td></tr>'
        for u in data["unknowns"])

    # 목록이 비면 빈 표 대신 상태를 적는다 — 빈 표는 "아직 안 적었다"로도 읽힌다
    if data["unknowns"]:
        unknown_block = f"""<div class="callout warn">아래 항목은 design/에서 확정되기 전까지 기대값이 성립하지 않습니다. 그래서 이 목록이 곧 명세 작성의 작업 목록입니다.</div>
<div class="tbl-scroll">
<table>
  <thead><tr><th>노드 경로</th><th>미확인 값</th><th>확정처</th></tr></thead>
  <tbody>
{unknown_rows}
  </tbody>
</table>
</div>"""
    else:
        unknown_block = ('<div class="callout">현재 미확인 항목이 없습니다 — 전 항목이 '
                         'design/에서 확정되었습니다. 값의 정본은 design/이며, 트리 노드는 '
                         '값을 담지 않고 위임합니다.</div>')

    doc = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{proj} 기능 골격 v{ver}</title>
<!-- ============================================================
  파생 문서 — 직접 수정 금지.
  정본: spec/{proj}-feature-tree.md (md 형식 v2)
  재생성: python core/modules/tc/scripts/gen_feature_tree_html.py
  기준: 템플릿 01-feature-tree v1.0 · design-guide-master {css_ver} 스냅샷
  ============================================================ -->
<style>
{css}
</style>
<script>
{js}
</script>
</head>
{body_open}

<header class="doc-header">
  <h1>{proj} 기능 골격 v{ver}</h1>
  <p class="doc-lead">{proj}의 기획 골격 정본을 시각화한 파생 문서입니다.
  범위 태그가 구현(이번 검증 대상)·보류(트리에만)·제외(사유만)를 가릅니다.</p>
  <div class="meta-row">
    <span class="badge">골격 버전 <b>v{ver}</b></span>
    <span class="badge">정본 <b>{proj}-feature-tree.md</b></span>
    <span class="badge">기준일 <b>{today}</b></span>
  </div>
  <nav class="toc">
    <a href="#stats">개요</a><a href="#tree">기능 트리</a><a href="#unknown">미확인 목록</a>
  </nav>
</header>

<h2 id="stats">개요</h2>
<div class="stats">
  <div class="stat"><div class="num">{n_impl}</div><div class="lbl">구현 노드 (검증 대상)</div></div>
  <div class="stat"><div class="num">{n_hold} / {n_excl}</div><div class="lbl">보류 / 제외</div></div>
  <div class="stat"><div class="num"><em>{len(data["unknowns"])}</em></div><div class="lbl">미확인(?) 항목</div></div>
  <div class="stat"><div class="num">{det_pct}%</div><div class="lbl">결정적 비율</div></div>
</div>

<h2 id="tree">기능 트리</h2>
<p>명칭이 아니라 역할로 묶었고, 상태(로그인·인증)는 Depth가 아니라 Pre-Condition으로 흡수했습니다.
칩은 순서대로 검증유형 · 우선순위 · 출처(REF=레퍼런스 채택 / ADD=직접 보강) · 범위이며,
상태 칩이 붙은 기능 단위는 선언된 상태 각각에서 최소 한 케이스가 요구됩니다(규칙: rules/depth-and-tn.md §상태 축).
값이 미정인 항목은 트리에 박지 않고 미확인 목록에 모았습니다 — 확정처는 전부 spec/design/입니다.</p>
{render_tree(nodes)}

<h2 id="unknown">미확인 목록</h2>
{unknown_block}

<footer class="doc-footer">
  {proj} 기능 골격 v{ver} · 템플릿 01-feature-tree v1.0 · design-guide-master {css_ver} 스냅샷 · 파생 문서(직접 수정 금지)
</footer>

{body_close}
"""
    shell.save(args.output, doc)
    print(f"{len(nodes)} nodes -> {args.output}")


if __name__ == "__main__":
    main()
