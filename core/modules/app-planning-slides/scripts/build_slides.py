# -*- coding: utf-8 -*-
"""앱 기획 슬라이드 생성 — 입력(JSON)에서 Google Slides로 옮길 .pptx를 만듭니다

두 가지 문서를 만듭니다. 형식과 채우는 법의 정본은 rules/planning-slides.md입니다.

  overview   프로젝트 전체 문서 — 개요서 · 정보 구조도(IA) · 기능 정의서 목록
  feature    기능별 문서 — 기능 정의 상세 · 와이어프레임 · 화면설계서 · 예외 처리

Google Slides로 변환해도 고칠 수 있게 만듭니다
--------------------------------------------
  글꼴은 Noto Sans KR 하나, 차트 · SmartArt · 그라데이션 · 그림자는 쓰지 않습니다. 슬라이드
  레이아웃(마스터)에 기대지 않고 텍스트 상자 · 표 · 도형 · 선을 직접 놓습니다. 변환 뒤 그림으로
  굳는 요소가 없어야 Google Slides에서 그대로 고칠 수 있기 때문입니다. lint()가 이것을 확인합니다.

모르는 값은 추측하지 않습니다
---------------------------
  비어 있는 칸은 `?`로 찍고, 입력의 open_questions와 함께 「미결 사항」 슬라이드에 모읍니다.

사용법
------
    python build_slides.py overview 입력.json -o 출력.pptx
    python build_slides.py feature  입력.json -o 출력.pptx
    python build_slides.py all {기획 폴더}           overview + features/*.json 전부, ID 대조 포함
    python build_slides.py lint 출력.pptx
    python build_slides.py gallery {출력 폴더}       모든 패턴이 들어간 견본 덱 두 개
"""
import argparse
import glob
import io
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slidekit import *  # noqa: E402,F401,F403
from slidekit import SW, SH, MX, ALLOWED_FONTS, REGION_TYPES, STANDARD_EXCEPTIONS, UNKNOWN, STATUS, TOGGLE_STEP  # noqa: E402,F401
from patterns import *  # noqa: E402,F401,F403
from patterns import TOP, BOTTOM  # noqa: E402

T = TOGGLE_STEP                # ▼ 소제목 아래 내용의 들여쓰기


# ── 프로젝트 전체 문서 ─────────────────────────────────────────────────

def _paths(tree):
    """IA 잎 화면마다 (노드, 경로 문자열) — 화면 목록과 화면설계서 경로 칸에 씁니다."""
    out = []

    def go(ns, trail):
        for n in ns:
            here = trail + [v(n.get("name"))]
            ch = n.get("children") or []
            if ch:
                go(ch, here)
            else:
                out.append((n, " > ".join(here[1:-1] or here[:1])))
    go(tree, [])
    return out


def build_overview(data, out):
    m = data.get("project", {})
    d = Deck("프로젝트 전체 기획서", m)
    o = data.get("overview", {})
    ia = data.get("ia", {})
    feats = data.get("features", [])

    d.cover("PROJECT PLANNING", v(m.get("name")), "프로젝트 전체 기획서 — 개요서 · 정보 구조도 · 기능 정의서")
    d.history(data.get("history", []))
    # 목차는 자리만 잡고, 쪽 번호가 정해지는 끝에서 채웁니다
    toc_slide = d.slide("목차", "문서 정보")

    # 01 개요서
    d.divider(1, "프로젝트 개요서", "이후 모든 문서의 기준점입니다. 팀이 같은 방향을 보는지 여기서 맞춥니다.")
    s = d.slide("기획 배경과 해결할 문제", "01 프로젝트 개요서")
    d.note("기획 배경", o.get("background"))
    box(s, MX, 1.5, 5.9, 5.1, fill=TINT, round_=True, name="card-bg")
    subhead(s, MX + 0.3, 1.7, 5.3, "기획 배경", size=16)
    text(s, MX + 0.3 + T, 2.2, 5.3 - T, 4.2, v(o.get("background")), size=14, spacing=8)
    subhead(s, 7.0, 1.7, 5.7, "해결할 문제", size=16)
    probs = lst(o.get("problems"))
    d.note("해결할 문제", probs)
    for i, p in enumerate(probs[:5] or [UNKNOWN]):
        numbered_item(s, 7.0 + T, 2.3 + i * 0.85, 5.75 - T, i + 1, p, size=14, d=0.38, h=0.8)

    personas = o.get("personas") or [{}]
    s = d.slide("타겟 사용자 — 페르소나", "01 프로젝트 개요서")
    cw = (SW - 2 * MX - 0.4 * (len(personas[:2]) - 1)) / len(personas[:2])
    for i, p in enumerate(personas[:2]):
        x = MX + i * (cw + 0.4)
        box(s, x, 1.5, cw, 5.1, fill=TINT, round_=True, name="persona-card")
        circle(s, x + 0.3, 1.75, 0.7, INK, (v(p.get("name"))[:1]), size=20)
        text(s, x + 1.2, 1.78, cw - 1.5, 0.4, v(p.get("name")), size=18, bold=True)
        text(s, x + 1.2, 2.18, cw - 1.5, 0.35, v(p.get("profile")), size=12, color=SUB)
        d.note("페르소나 %d 프로필" % (i + 1), p.get("profile"))
        oy = 0.0
        if p.get("quote"):
            text(s, x + 0.3, 2.75, cw - 0.6, 0.45, "“%s”" % p["quote"], size=13, bold=True, color=SUB)
            oy = 0.45
        subhead(s, x + 0.3, 2.85 + oy, cw - 0.6, "원하는 것", size=13)
        text(s, x + 0.3 + T, 3.2 + oy, cw - 0.6 - T, 1.2, bullets((p.get("needs") or [])[:3])
             or UNKNOWN, size=13)
        subhead(s, x + 0.3, 4.55 + oy, cw - 0.6, "불편한 것", size=13)
        text(s, x + 0.3 + T, 4.9 + oy, cw - 0.6 - T, 1.2, bullets((p.get("pains") or [])[:3])
             or UNKNOWN, size=13)

    s = d.slide("핵심 가치 제안", "01 프로젝트 개요서")
    d.note("핵심 가치 제안", o.get("value"))
    text(s, MX, 1.7, SW - 2 * MX, 1.6, "“%s”" % v(o.get("value")), size=28, bold=True, color=INK, anchor="m")
    scope = o.get("scope", {})
    for i, (t, key) in enumerate((("이번 범위", "in"), ("범위 밖", "out"))):
        x = MX + i * 6.15
        box(s, x, 3.7, 5.9, 2.9, fill=TINT, round_=True, name="scope-card")
        subhead(s, x + 0.3, 3.85, 5.3, t, size=15)
        text(s, x + 0.3 + T, 4.3, 5.3 - T, 2.2, bullets(scope.get(key) or []) or UNKNOWN, size=13)

    kpis = o.get("kpis") or []
    d.note("핵심 지표(KPI)", kpis)
    s = d.slide("핵심 지표 (KPI)", "01 프로젝트 개요서")
    top = kpis[:3]
    if top:
        cw = (SW - 2 * MX - 0.4 * (len(top) - 1)) / len(top)
        for i, k in enumerate(top):
            x = MX + i * (cw + 0.4)
            box(s, x, 1.5, cw, 1.9, fill=TINT, round_=True, name="kpi-card")
            text(s, x + 0.25, 1.6, cw - 0.5, 0.9, v(k.get("target")), size=30, bold=True, color=ACCENT)
            text(s, x + 0.25, 2.5, cw - 0.5, 0.8, v(k.get("name")), size=14, bold=True)
    table(s, MX, 3.75, SW - 2 * MX, (2.2, 1.5, 4), ["지표", "목표", "측정 방법"],
          [[k.get("name"), k.get("target"), k.get("measure")] for k in kpis[:6]] or [[UNKNOWN] * 3])

    journey = o.get("journey")
    if journey:
        s = d.slide("사용자 여정", "01 프로젝트 개요서")
        d.mark("journey")
        journey_map(s, journey)
    glossary = data.get("glossary") or []
    for i, chunk in enumerate(paged(glossary, 10) if glossary else []):
        s = d.slide("용어 정의" + (" (%d)" % (i + 1) if i else ""), "01 프로젝트 개요서")
        d.mark("glossary")
        table(s, MX, TOP, SW - 2 * MX, (1.6, 5, 3), ["용어", "정의", "예시"],
              [[g.get("term"), g.get("definition"), g.get("example") or "—"] for g in chunk], size=11, row_h=0.42)

    # 02 IA
    d.divider(2, "정보 구조도 (IA)", "화면을 그리기 전에 메뉴 · 화면 계층을 펼쳐 빠진 화면과 끊긴 경로를 찾습니다.")
    tree = ia.get("tree") or []
    d.note("정보 구조도 트리", tree)
    for root, chunk in ia_pages(tree):
        s = d.slide("정보 구조도" + ("" if root is None else " — " + v(root.get("name"))), "02 정보 구조도 (IA)")
        draw_tree(s, chunk)
    screens = _paths(tree)
    owner = {}
    for f in feats:
        owner.setdefault(f.get("screen"), []).append(str(f.get("id")))
    for i, chunk in enumerate(paged(screens, 12) if screens else []):
        s = d.slide("화면 목록" + (" (%d)" % (i + 1) if i else ""), "02 정보 구조도 (IA)")
        d.mark("screens")
        table(s, MX, TOP, SW - 2 * MX, (1.1, 2.0, 2.8, 1.0, 0.9, 2.2, 0.9),
              ["화면 ID", "화면명", "경로", "형태", "로그인", "기능", "변경"],
              [[n.get("id"), n.get("name"), path, NODE_KINDS.get(n.get("kind", "page"), n.get("kind")),
                {True: "필요", False: "불필요"}.get(n.get("login"), "?"),
                ", ".join(owner.get(n.get("id"), [])) or "—",
                STATUS.get(str(n.get("change", "")).upper(), ("—",))[0]] for n, path in chunk],
              size=10, row_h=0.36)
    flows = ia.get("flows") or []
    if flows:
        names = {n["id"]: n.get("name", n["id"]) for n in walk(tree)}
        for i, chunk in enumerate(paged(flows, 4)):
            s = d.slide("주요 흐름" + (" (%d)" % (i + 1) if i else ""), "02 정보 구조도 (IA)")
            for j, f in enumerate(chunk):
                y = 1.55 + j * 1.3
                text(s, MX, y, 3, 0.35, v(f.get("name")), size=14, bold=True, color=ACCENT)
                path = f.get("path") or []
                n = max(1, min(len(path), 7))
                cw = min(1.55, (SW - 2 * MX - 0.35 * (n - 1)) / n)
                for k, sid in enumerate(path[:7]):
                    x = MX + k * (cw + 0.35)
                    box(s, x, y + 0.42, cw, 0.6, fill=WHITE, line=INK, round_=True,
                        label="%s\n%s" % (sid, names.get(sid, "")), size=10, name="flow-step")
                    if k:
                        line(s, x - 0.33, y + 0.72, x - 0.02, y + 0.72, color=INK, arrow=True)
    policies = data.get("policies") or []
    for i, chunk in enumerate(paged(policies, 9) if policies else []):
        s = d.slide("공통 정책" + (" (%d)" % (i + 1) if i else ""), "02 정보 구조도 (IA)")
        d.mark("policies")
        table(s, MX, TOP, SW - 2 * MX, (1.1, 1.8, 5.5, 1.8), ["정책 ID", "항목", "규칙", "적용 화면"],
              [[p.get("id"), p.get("name"), p.get("rule"), v(p.get("screens"))] for p in chunk],
              size=11, row_h=0.5)

    # 03 기능 정의서
    d.divider(3, "기능 정의서", "큰 기능을 세부 동작 단위로 쪼갭니다. 견적 · 일정과 DB 설계의 근거입니다.")
    d.note("기능 목록", feats)
    for f in feats:
        d.note("%s 세부 동작 요약" % v(f.get("id")), f.get("summary"))
        d.note("%s 정책 (없으면 「없음」)" % v(f.get("id")), f.get("policy"))
    for i, chunk in enumerate(paged(feats, 8)):
        s = d.slide("기능 목록" + (" (%d)" % (i + 1) if i else ""), "03 기능 정의서")
        table(s, MX, TOP, SW - 2 * MX, (1.3, 1.9, 0.9, 3.6, 2.6, 1.6, 0.8),
              ["기능 ID", "기능명", "화면", "세부 동작 요약", "정책", "외부 연동", "우선"],
              [[f.get("id"), f.get("name"), f.get("screen"), f.get("summary"), f.get("policy"),
                f.get("integration") or "없음", f.get("priority") or f.get("moscow")] for f in chunk]
              or [[UNKNOWN] * 7], size=10, row_h=0.6)
    if any(f.get("impact") and f.get("effort") for f in feats):
        s = d.slide("우선순위 — 영향 × 노력", "03 기능 정의서")
        d.mark("priority")
        rest = priority_matrix(s, feats)
        subhead(s, 8.9, TOP + 0.1, 3.8, "읽는 법", size=13)
        text(s, 8.9 + T, TOP + 0.5, 3.8 - T, 2.6,
             bullets(["영향이 크고 노력이 적은 「빠른 성과」부터 합니다", "「큰 승부」는 일정 계획을 세워 나눠 합니다",
                      "「보류」는 범위에서 빼거나 다시 정의합니다"]), size=11, spacing=6)
        if rest:
            text(s, 8.9, TOP + 3.2, 3.8, 1.6, "판단 전: " + ", ".join(v(f.get("id")) for f in rest), size=10,
                 color=SUB)
    if any(f.get("moscow") for f in feats):
        s = d.slide("우선순위 — MoSCoW", "03 기능 정의서")
        d.mark("priority")
        moscow_board(s, feats)
    if data.get("roadmap"):
        s = d.slide("로드맵", "03 기능 정의서")
        d.mark("roadmap")
        roadmap(s, data["roadmap"])

    # 04 색인
    s = d.slide("기능별 문서 색인", "04 기능별 문서")
    d.mark("index")
    text(s, MX, 1.4, SW - 2 * MX, 0.5,
         "와이어프레임 · 화면설계서 · 예외 처리는 기능 ID마다 따로 만든 기능별 문서에 있습니다.",
         size=14, color=SUB)
    table(s, MX, 2.0, SW - 2 * MX, (1.5, 2.5, 5), ["기능 ID", "기능명", "기능별 문서"],
          [[f.get("id"), f.get("name"), f.get("doc") or "%s-기능별 기획서" % f.get("id")]
           for f in feats[:10]] or [[UNKNOWN] * 3], size=11)

    d.questions(data.get("open_questions"))
    extra1 = " · 여정" if "journey" in d.marks else ""
    extra2 = " · 화면 목록" if "screens" in d.marks else ""
    extra3 = " · 우선순위" if "priority" in d.marks else ""
    extra3 += " · 로드맵" if "roadmap" in d.marks else ""
    toc = [("01", "프로젝트 개요서", "배경 · 페르소나 · 가치 · KPI" + extra1, d.marks.get("div1")),
           ("02", "정보 구조도 (IA)", "메뉴 · 화면 계층" + extra2 + " · 주요 흐름", d.marks.get("div2")),
           ("03", "기능 정의서", "기능 ID별 동작 · 정책" + extra3, d.marks.get("div3")),
           ("04", "기능별 문서 색인", "와이어프레임 · 화면설계서는 기능별 문서에 있습니다", d.marks.get("index"))]
    if "questions" in d.marks:
        toc.append(("—", "미결 사항", "확정 전에 정할 것", d.marks["questions"]))
    draw_toc(toc_slide, toc)
    d.save(out)
    return d


# ── 기능별 문서 ───────────────────────────────────────────────────────

SB_Y = 1.85                    # 화면 정보 띠 아래 본문이 시작하는 높이
SB_PHONE_H = 4.85


def _header(s, sc, m):
    storyboard_header(s, [("화면 ID", sc.get("id"), 1.0), ("화면명", sc.get("name"), 1.6),
                          ("경로", sc.get("path"), 2.6), ("버전", sc.get("version") or m.get("version"), 0.6)],
                      change=sc.get("change"))


def build_feature(data, out):
    m = data.get("project", {})
    f = data.get("feature", {})
    d = Deck("기능별 기획서 %s" % v(f.get("id")), m)
    screens = data.get("screens", [])

    d.cover(v(f.get("id")), v(f.get("name")), "기능별 기획서 — 기능 정의 · 와이어프레임 · 화면설계서 · 예외 처리")
    d.history(data.get("history", []))
    # 목차는 자리만 잡습니다 — 화면이 많으면 화면 쪽표가 여러 장으로 이어집니다
    toc_slides = [d.slide("목차" + (" (%d)" % (i + 1) if i else ""), "문서 정보")
                  for i in range(len(paged(screens, 10)))]

    s = d.slide("기능 정의 — %s" % v(f.get("name")), "01 기능 정의")
    d.mark("def")
    d.note("기능 요약", f.get("summary"))
    box(s, MX, 1.45, SW - 2 * MX, 0.8, fill=TINT, round_=True, name="summary-card")
    text(s, MX + 0.25, 1.5, SW - 2 * MX - 0.5, 0.7, v(f.get("summary")), size=15, anchor="m")
    subhead(s, MX, 2.5, 6, "입력값", size=14)
    table(s, MX + T, 2.9, 6.0 - T, (1.4, 1, 2.6), ["항목", "형식", "규칙"],
          [[i.get("name"), i.get("type"), i.get("rule")] for i in (f.get("inputs") or [])[:7]] or [[UNKNOWN] * 3],
          size=10, row_h=0.42)
    subhead(s, 7.0, 2.5, 5.7, "처리 순서", size=14)
    steps = lst(f.get("process"))
    d.note("처리 순서", steps)
    for i, st in enumerate(steps[:6] or [UNKNOWN]):
        numbered_item(s, 7.0 + T, 3.0 + i * 0.6, 5.75 - T, i + 1, st, size=12, d=0.32, h=0.56)

    if f.get("story") or f.get("acceptance"):
        s = d.slide("사용자 스토리 · 수용 기준", "01 기능 정의")
        box(s, MX, TOP, SW - 2 * MX, 1.1, fill=TINT, round_=True, name="story-card")
        text(s, MX + 0.3, TOP + 0.1, SW - 2 * MX - 0.6, 0.9, "“%s”" % v(f.get("story")), size=17, bold=True,
             anchor="m")
        acc = f.get("acceptance") or []
        d.note("수용 기준", acc)
        table(s, MX, TOP + 1.4, SW - 2 * MX, (0.6, 3, 3, 3), ["No", "상황 (Given)", "행동 (When)", "결과 (Then)"],
              [[i, a.get("given"), a.get("when"), a.get("then")] for i, a in enumerate(acc[:7], 1)]
              or [[UNKNOWN] * 4], size=10, row_h=0.46)

    s = d.slide("조건 · 정책 · 외부 연동", "01 기능 정의")
    cols = (("조건", f.get("conditions")), ("정책", f.get("policies")), ("외부 연동", f.get("integrations")))
    cw = (SW - 2 * MX - 0.8) / 3
    for i, (t, items) in enumerate(cols):
        x = MX + i * (cw + 0.4)
        raw, items = items or [], lst(items)
        if t != "외부 연동":
            d.note(t, items)
        box(s, x, 1.5, cw, 5.1, fill=TINT, round_=True, name="rule-card")
        subhead(s, x + 0.25, 1.7, cw - 0.5, t, size=16)
        text(s, x + 0.25 + T, 2.2, cw - 0.5 - T, 4.2, bullets(raw)
             or ("없음" if t == "외부 연동" else UNKNOWN), size=13, spacing=8)

    flow = data.get("flow")
    if flow and flow.get("nodes"):
        s = d.slide("기능 흐름도", "01 기능 정의")
        d.mark("flow")
        flowchart(s, flow["nodes"], flow.get("edges") or [])
    if data.get("compare"):
        c = data["compare"]
        s = d.slide(v(c.get("title") or "현행 · 개선 비교"), "01 기능 정의")
        compare(s, c.get("left") or {}, c.get("right") or {})

    d.divider(2, "와이어프레임", "무엇이 어디에 있는가만 정합니다. 색과 이미지는 넣지 않습니다.")
    if len(screens) > 1:
        s = d.slide("화면 흐름", "02 와이어프레임")
        n = min(len(screens), 5)
        gap = 0.9
        ph = min(4.6, ((SW - 2 * MX - gap * (n - 1)) / n) * 2)
        pw = ph * 0.5
        x0 = (SW - (pw * n + gap * (n - 1))) / 2
        ids = [sc.get("id") for sc in screens]
        for i, sc in enumerate(screens[:5]):
            x = x0 + i * (pw + gap)
            phone(s, x, 1.85, ph, sc.get("regions") or [], markers=False,
                  title="%s %s" % (v(sc.get("id")), v(sc.get("name"))))
            if i:
                line(s, x - gap + 0.15, 1.85 + ph / 2, x - 0.15, 1.85 + ph / 2, color=INK, width=1.25,
                     arrow=True)
        other = [n.get("to") for sc in screens for n in (sc.get("next") or []) if n.get("to") not in ids]
        if other:
            text(s, MX, SH - 0.85, SW - 2 * MX, 0.3, "다른 기능으로 나가는 화면: " + ", ".join(sorted(set(other))),
                 size=11, color=SUB)
    for sc in screens:
        regions = sc.get("regions") or []
        title = "%s %s" % (v(sc.get("id")), v(sc.get("name")))
        d.note("%s 경로" % title, sc.get("path"))
        # 와이어프레임 — 배치와 이동
        s = d.slide("와이어프레임 — " + title, "02 와이어프레임")
        d.mark("wf:" + str(sc.get("id")))
        _header(s, sc, m)
        phone(s, MX + 0.4, SB_Y, SB_PHONE_H, regions)
        subhead(s, 4.1, SB_Y, 8.6, "영역 구성", size=14)
        table(s, 4.1 + T, SB_Y + 0.4, SW - MX - 4.1 - T, (0.5, 1.1, 3.2), ["No", "유형", "영역"],
              [[r.get("no", i), r.get("type"), r.get("label")] for i, r in enumerate(regions[:8], 1)]
              or [[UNKNOWN] * 3], size=10, row_h=0.3)
        nx = sc.get("next") or []
        y = SB_Y + 0.4 + 0.3 * (min(len(regions), 8) + 1) + 0.3
        subhead(s, 4.1, y, 8.6, "이동 흐름", size=14)
        table(s, 4.1 + T, y + 0.4, SW - MX - 4.1 - T, (0.8, 2.5, 1.5), ["요소", "조건", "이동할 화면"],
              [[n.get("element"), n.get("when"), n.get("to")] for n in nx[:5]] or [["없음", "", ""]],
              size=10, row_h=0.3)
        # 화면설계서 — 번호 표식과 Description
        elems = sc.get("elements") or []
        d.note("%s 요소 동작" % title, elems)
        dx, dw = 4.1, SW - MX - 4.1
        pages = paginate_desc(elems, dw - T, BOTTOM - SB_Y - 0.5)
        for i, chunk in enumerate(pages):
            s = d.slide("화면설계서 — " + title + (" (%d)" % (i + 1) if len(pages) > 1 else ""), "03 화면설계서")
            d.mark("sb:" + str(sc.get("id")))
            _header(s, sc, m)
            phone(s, MX + 0.4, SB_Y, SB_PHONE_H, regions)
            description_list(s, dx, SB_Y, dw, chunk or [{"no": "?", "name": UNKNOWN, "behavior": UNKNOWN}])
        if sc.get("states"):
            s = d.slide("화면 상태 — " + title, "03 화면설계서")
            _header(s, sc, m)
            ui_states(s, sc["states"], header=v(sc.get("name")))
        # 예외 처리 — 표준 네 경우는 항상 찍습니다
        given = {e.get("case"): e for e in (sc.get("exceptions") or [])}
        cases = list(STANDARD_EXCEPTIONS) + [c for c in given if c not in STANDARD_EXCEPTIONS]
        rows = []
        for k, c in enumerate(cases, 1):
            e = given.get(c, {})
            d.note("%s 예외 — %s" % (title, c), e.get("handling"))
            rows.append([e.get("id") or "E-%s-%02d" % (sc.get("id"), k), c, e.get("message") or "—",
                         e.get("handling")])
        s = d.slide("예외 처리 — " + title, "04 예외 처리")
        d.mark("ex:" + str(sc.get("id")))
        _header(s, sc, m)
        table(s, MX, SB_Y, SW - 2 * MX, (1.3, 1.5, 3, 5), ["예외 ID", "상황", "사용자 메시지", "처리"],
              rows[:9], size=11, row_h=0.48)

    d.questions(data.get("open_questions"))

    def first(prefix):
        pages = [p for k, p in d.marks.items() if k.startswith(prefix)]
        return min(pages) if pages else None
    sections = [("01", "기능 정의", "요약 · 입력값 · 처리 순서 · 정책" + (" · 흐름도" if "flow" in d.marks else ""),
                 d.marks.get("def")),
                ("02", "와이어프레임", "화면 흐름과 화면별 영역 · 이동", d.marks.get("div2")),
                ("03", "화면설계서", "번호별 Description — 첫 화면부터", first("sb:")),
                ("04", "예외 처리", "기본 예외 네 가지와 추가 예외", first("ex:"))]
    if "questions" in d.marks:
        sections.append(("—", "미결 사항", "확정 전에 정할 것", d.marks["questions"]))
    for i, (ts, chunk) in enumerate(zip(toc_slides, paged(screens, 10))):
        if i == 0:
            draw_toc(ts, sections, w=5.9, top=1.45, step=min(1.0, 5.3 / len(sections)))
        subhead(ts, 7.0, 1.45, 5.7, "화면별 쪽", size=14)
        table(ts, 7.0 + T, 1.85, SW - MX - 7.0 - T, (2.6, 1.1, 1.1, 1.1), ["화면", "와이어프레임", "화면설계서", "예외 처리"],
              [["%s %s" % (v(sc.get("id")), v(sc.get("name")))]
               + ["p. %s" % d.marks.get("%s:%s" % (k, sc.get("id")), "—") for k in ("wf", "sb", "ex")]
               for sc in chunk] or [["화면 없음", "—", "—", "—"]], size=11, row_h=0.42)
    d.save(out)
    return d


# ── 검사 ─────────────────────────────────────────────────────────────

def validate(kind, data):
    """(오류, 경고). 오류가 있으면 만들지 않습니다. 빈 값은 오류가 아니라 `?`입니다."""
    err, warn = [], []
    want = "app-planning/%s@1" % kind
    if data.get("schema") != want:
        err.append("schema가 %r이어야 합니다 (지금 %r)" % (want, data.get("schema")))
    if not (data.get("project") or {}).get("name"):
        err.append("project.name이 없습니다")
    if kind == "overview":
        ids = [f.get("id") for f in data.get("features", [])]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        if dup:
            err.append("기능 ID 중복: %s" % ", ".join(map(str, dup)))
        if any(not i for i in ids):
            err.append("기능 ID가 빈 기능이 있습니다")
        nodes = [n.get("id") for n in walk((data.get("ia") or {}).get("tree") or [])]
        for f in data.get("features", []):
            if f.get("screen") and f["screen"] not in nodes:
                warn.append("%s: 화면 %s가 IA에 없습니다" % (f.get("id"), f["screen"]))
        for fl in (data.get("ia") or {}).get("flows") or []:
            for sid in fl.get("path") or []:
                if sid not in nodes:
                    warn.append("흐름 %s: %s가 IA에 없습니다" % (fl.get("name"), sid))
        ps = (data.get("overview") or {}).get("personas") or []
        if len(ps) > 2:
            warn.append("페르소나는 1~2명을 권합니다 — 앞의 둘만 그립니다")
        val = (data.get("overview") or {}).get("value") or ""
        if len(re.findall(r"[.!?。]\s", val + " ")) > 1:
            warn.append("핵심 가치 제안은 한 문장으로 씁니다")
        for n in walk((data.get("ia") or {}).get("tree") or []):
            if n.get("kind") and n["kind"] not in NODE_KINDS:
                err.append("%s: 알 수 없는 노드 형태 %r (%s)" % (n.get("id"), n["kind"], " · ".join(NODE_KINDS)))
            if n.get("change") and str(n["change"]).upper() not in ("NEW", "UPDATE", "DELETE"):
                err.append("%s: 변경 표시는 NEW · UPDATE · DELETE입니다 (%r)" % (n.get("id"), n["change"]))
        for f in data.get("features", []):
            for k in ("impact", "effort"):
                if f.get(k) and str(f[k]).lower() not in ("high", "low"):
                    err.append("%s: %s는 high · low입니다 (%r)" % (f.get("id"), k, f[k]))
            if f.get("moscow") and str(f["moscow"]).lower().replace("'", "") not in [m[0] for m in MOSCOW]:
                err.append("%s: moscow는 must · should · could · wont입니다 (%r)" % (f.get("id"), f["moscow"]))
        st = ((data.get("overview") or {}).get("journey") or {}).get("stages") or []
        if len(st) > JOURNEY_MAX:
            warn.append("여정 단계는 %d개까지 그립니다 (지금 %d)" % (JOURNEY_MAX, len(st)))
        rm = data.get("roadmap") or {}
        if len(rm.get("tracks") or []) > ROADMAP_MAX_TRACKS:
            warn.append("로드맵 트랙은 %d개까지 그립니다" % ROADMAP_MAX_TRACKS)
        last = len(rm.get("periods") or []) - 1
        for tr in rm.get("tracks") or []:
            for it in tr.get("items") or []:
                if float(it.get("end", it.get("start", 0))) > last + 0.99:
                    warn.append("로드맵 %s: 기간 칸 밖으로 나갑니다" % it.get("label"))
    else:
        if not (data.get("feature") or {}).get("id"):
            err.append("feature.id가 없습니다")
        sids = [s.get("id") for s in data.get("screens", [])]
        if len(set(sids)) != len(sids):
            err.append("화면 ID 중복")
        for s in data.get("screens", []):
            for r in s.get("regions") or []:
                if r.get("type") not in REGION_TYPES:
                    err.append("%s: 알 수 없는 영역 유형 %r (%s)" % (s.get("id"), r.get("type"),
                                                            " · ".join(REGION_TYPES)))
                for k in ("x", "y", "w", "h"):
                    if r.get(k) is not None and not 0 <= r[k] <= 100:
                        err.append("%s: 영역 %s의 %s는 0~100 백분율입니다" % (s.get("id"), r.get("label"), k))
            if s.get("change") and str(s["change"]).upper() not in ("NEW", "UPDATE", "DELETE"):
                err.append("%s: 변경 표시는 NEW · UPDATE · DELETE입니다" % s.get("id"))
            for k in s.get("states") or {}:
                if k not in [n for n, _ in STATE_NAMES]:
                    err.append("%s: 화면 상태는 empty · loading · error입니다 (%r)" % (s.get("id"), k))
            nos = {str(r.get("no", i)) for i, r in enumerate(s.get("regions") or [], 1)}
            for e in s.get("elements") or []:
                if str(e.get("no")) not in nos:
                    warn.append("%s: 요소 %s에 맞는 영역 번호가 없습니다" % (s.get("id"), e.get("no")))
    if kind == "feature":
        fl = data.get("flow") or {}
        ids = {n.get("id") for n in fl.get("nodes") or []}
        if len(ids) > FLOW_MAX:
            warn.append("흐름도 노드는 %d개 이하를 권합니다 — 나눠 그립니다 (지금 %d)" % (FLOW_MAX, len(ids)))
        for n in fl.get("nodes") or []:
            if n.get("type", "process") not in FLOW_SHAPES:
                err.append("흐름도 %s: 알 수 없는 기호 %r (%s)" % (n.get("id"), n.get("type"), " · ".join(FLOW_SHAPES)))
        for e in fl.get("edges") or []:
            if e.get("from") not in ids or e.get("to") not in ids:
                err.append("흐름도 연결 %s → %s: 없는 노드" % (e.get("from"), e.get("to")))
        lanes = {n.get("lane") for n in fl.get("nodes") or [] if n.get("lane")}
        if lanes and any(not n.get("lane") for n in fl.get("nodes") or []):
            err.append("흐름도: 레인을 쓰면 모든 노드에 lane을 적습니다")
        if len(lanes) > 5:
            warn.append("레인은 5개 이하를 권합니다")
    return err, warn


def lint(path):
    """Google Slides로 옮겨도 고칠 수 있는가 — 그림으로 굳는 요소와 허용하지 않은 글꼴을 찾습니다."""
    bad = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if not name.endswith(".xml"):
                continue
            x = z.read(name).decode("utf-8", "replace")
            if name.startswith("ppt/charts/") or "drawingml/2006/chart" in x and name.startswith("ppt/slides/"):
                bad.append("%s — 차트 (변환 뒤 그림이 됩니다)" % name)
            if name.startswith("ppt/diagrams/") or "drawingml/2006/diagram" in x:
                bad.append("%s — SmartArt" % name)
            if not name.startswith("ppt/slides/slide"):
                continue
            for tag in ("a:gradFill", "a:outerShdw", "a:innerShdw", "a:blipFill"):
                if "<%s" % tag in x:
                    bad.append("%s — %s" % (name, tag))
            for face in set(re.findall(r'typeface="([^"]+)"', x)):
                if face not in ALLOWED_FONTS and not face.startswith("+"):
                    bad.append("%s — 허용하지 않은 글꼴 %s" % (name, face))
    return bad


# ── 실행 ─────────────────────────────────────────────────────────────

def load(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def run(kind, src, out):
    data = load(src)
    err, warn = validate(kind, data)
    for w in warn:
        print("경고  " + w)
    if err:
        for e in err:
            print("오류  " + e)
        return 1, None
    deck = (build_overview if kind == "overview" else build_feature)(data, out)
    bad = lint(out)
    for b in bad:
        print("변환 위험  " + b)
    print("만듦  %s  (%d장 · 미결 %d)" % (out, deck.page, len(deck.open)))
    return (1 if bad else 0), data


def run_all(folder, outdir):
    """overview와 features/*.json을 모두 만들고, 기능 ID가 양쪽에서 맞는지 대조합니다."""
    ov = sorted(glob.glob(os.path.join(folder, "*-overview.json")))
    if len(ov) != 1:
        print("오류  %s에 *-overview.json이 하나 있어야 합니다 (%d개)" % (folder, len(ov)))
        return 1
    outdir = outdir or os.path.join(folder, "slides")
    stem = os.path.basename(ov[0])[:-len(".json")]
    rc, data = run("overview", ov[0], os.path.join(outdir, stem + ".pptx"))
    listed = {f.get("id") for f in (data or {}).get("features", [])}
    made = set()
    for p in sorted(glob.glob(os.path.join(folder, "features", "*.json"))):
        r, fd = run("feature", p, os.path.join(outdir, "features", os.path.basename(p)[:-5] + ".pptx"))
        rc |= r
        if fd:
            made.add((fd.get("feature") or {}).get("id"))
    for i in sorted(made - listed):
        print("오류  기능별 문서 %s가 전체 문서의 기능 목록에 없습니다" % i)
        rc = 1
    for i in sorted(listed - made):
        print("알림  %s의 기능별 문서가 아직 없습니다" % i)
    return rc


def gallery(outdir):
    """견본 덱 — 예시 입력 둘로 모든 패턴이 들어간 두 문서를 만듭니다. 패턴을 고르기 전에 이것을 봅니다."""
    tpl = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "design-template")
    rc = 0
    for kind in ("overview", "feature"):
        rc |= run(kind, os.path.join(tpl, "%s.example.json" % kind),
                  os.path.join(outdir, "견본-%s.pptx" % kind))[0]
    return rc


def main():
    ap = argparse.ArgumentParser(description="앱 기획 슬라이드(.pptx) 생성")
    ap.add_argument("kind", choices=("overview", "feature", "all", "lint", "gallery"))
    ap.add_argument("src", nargs="?", help="입력 JSON · 기획 폴더 · .pptx (gallery는 출력 폴더)")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    if a.kind == "lint":
        bad = lint(a.src)
        for b in bad:
            print("변환 위험  " + b)
        print("변환 점검 — %s" % ("통과" if not bad else "%d건" % len(bad)))
        return 1 if bad else 0
    if a.kind == "gallery":
        return gallery(a.src or a.out or ".")
    if not a.src:
        ap.error("입력이 필요합니다")
    if a.kind == "all":
        return run_all(a.src, a.out)
    out = a.out or os.path.splitext(a.src)[0] + ".pptx"
    return run(a.kind, a.src, out)[0]


if __name__ == "__main__":
    sys.exit(main())
