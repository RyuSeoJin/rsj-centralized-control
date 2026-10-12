# -*- coding: utf-8 -*-
# v1.5 · 2026-10-12: 흐름도 — 다른 기능으로 이동(to: F-…), 도형의 화면 쪽 링크(screen), 조건의 판정 기준(check ·
#                    check_text) 검사 · 링크 채우기 추가
# v1.4 · 2026-10-12: flow 입력을 워크플로우 탐색기 어휘(term·action·input·output·decision·process·ref · 구역 u·s ·
#                    code 섹션)로 바꿈 — 옛 형식은 이전 안내와 함께 오류, 흐름도는 섹션마다 한 장
# v1.3 · 2026-10-12: 흐름 ID·분기 라벨·출구 누락 검사 추가
# v1.2 · 2026-10-12: 화면 카탈로그와 이동 대상 검사 — 처리 노드를 화면으로 그리는 입력 차단
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
from patterns import TOP, BOTTOM, NUM_GAP, CARD_BODY, CARD_PAD, SECTION_GAP  # noqa: E402

HEAD_BODY = 0.36               # ▼ 소제목 위끝에서 그 아래 본문 위끝까지

T = TOGGLE_STEP                # ▼ 소제목 아래 내용의 들여쓰기

# 기능 흐름도 입력 — 어휘의 정본은 core/modules/workflow-explorer/rules/explorer.md §1 · §2입니다
FLOW_TYPES = ("term", "action", "input", "output", "decision", "process", "ref")
FLOW_SCREEN_TYPES = ("input", "output")        # 화면과 ID를 나눠 쓸 수 있는 도형(입력 · 출력)
FLOW_KINDS = ("normal", "yes", "no")
FLOW_LANES = [{"key": "u", "label": "유저 구역"}, {"key": "s", "label": "시스템 구역"}]
FLOW_SECTION_MAX = globals().get("FLOW_MAX", 15)   # 한 장(섹션)에 권하는 도형 수 — 렌더러 값이 있으면 따릅니다
# 옛 형식(v1.3까지)에서 새 형식으로 — 오류 메시지의 이전 안내에 씁니다
FLOW_OLD_TYPES = {"start": "term", "end": "term", "screen": "output 또는 input", "io": "output 또는 input"}
FLOW_OLD_LANES = {"사용자": "u", "앱": "s", "서버": "s"}
FLOW_MIGRATION = ("옛 flow 형식입니다 — start·end → term, screen·io → output(노출) 또는 input(입력), "
                  "process → action(또는 공통 처리는 process), 레인 사용자 → u · 앱·서버 → s, "
                  "노드 label → text, 연결 kind exception → no(조건의 아니오) 또는 normal")
FLOW_FEATURE_RE = re.compile(r"^F-[A-Z]+-\d+$")    # 연결의 to가 이 꼴이면 다른 기능으로 넘어가는 이동입니다


def check_text(check):
    """조건(decision)의 판정 기준을 보일 글로 — 문자열은 그대로, 탐색기 객체는 「path」 또는 「path = equals」."""
    if isinstance(check, dict):
        path = str(check.get("path") or "").strip()
        if "equals" in check:
            eq = check["equals"]
            eq = json.dumps(eq, ensure_ascii=False) if not isinstance(eq, str) else eq
            return "%s = %s" % (path, eq)
        return path
    return "" if check is None else str(check)


# ── 프로젝트 전체 문서 ─────────────────────────────────────────────────

def _moscow(f):
    """moscow 값을 must · should · could · wont 중 하나로 — 대소문자 · 아포스트로피를 무시합니다."""
    return str(f.get("moscow") or "").lower().replace("'", "").replace("’", "")


def in_scope(f):
    """이번 범위 안 기능인가 — scope가 out이거나 MoSCoW가 Won't면 범위 밖입니다."""
    return f.get("scope") != "out" and _moscow(f) != "wont"


def screens_of(f):
    """기능의 screen은 문자열 하나 또는 목록 — 늘 목록으로 돌려줍니다."""
    sc = f.get("screen")
    if not sc:
        return []
    return [str(x) for x in sc] if isinstance(sc, (list, tuple)) else [str(sc)]


def _rank(f):
    """기능 목록 「우선」 칸 — MoSCoW가 있으면 그 우리말, 없으면 priority. 범위 밖은 「범위 밖」."""
    if not in_scope(f):
        return "범위 밖"
    lead = {k: ko for k, _, ko in MOSCOW}.get(_moscow(f))
    return lead or f.get("priority")


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
    s = d.slide("이 문서를 읽는 법", "문서 정보")
    d.mark("guide")
    reading_guide(s, kind="overview", change_base=m.get("change_base"))

    # 01 개요서
    d.divider(1, "프로젝트 개요서", "이후 모든 문서의 기준점입니다. 팀이 같은 방향을 보는지 여기서 맞춥니다.")
    s = d.slide("기획 배경과 해결할 문제", "01 프로젝트 개요서")
    d.note("기획 배경", o.get("background"))
    probs = lst(o.get("problems"))
    d.note("해결할 문제", probs)
    cw = (SW - 2 * MX - 0.4) / 2
    # 좌우 두 카드는 같은 높이 — 높이는 더 긴 쪽 내용에 맞춥니다(빈 카드가 남지 않게)
    # 카드마다 제목이 하나뿐이라 ▼ 없이 card_title, 본문도 제목과 같은 x에서 시작합니다
    need = max(est_text_height(v(o.get("background")), cw - 0.45, 14, 8),
               sum(est_text_height(p, cw - 0.9, 14, 0) + NUM_GAP for p in probs[:5] or [UNKNOWN]) - NUM_GAP)
    ch = min(BOTTOM - 1.5, CARD_BODY + need + CARD_PAD)
    y0 = group_top(ch)
    for i, t in enumerate(("기획 배경", "해결할 문제")):
        x = MX + i * (cw + 0.4)
        box(s, x, y0, cw, ch, fill=TINT, round_=True, name="card")
        card_title(s, x + 0.3, y0 + 0.2, cw - 0.6, t, size=16)
    text(s, MX + 0.3, y0 + CARD_BODY, cw - 0.45, ch - 0.9, v(o.get("background")), size=14, spacing=8)
    x2 = MX + cw + 0.4 + 0.3
    numbered_list(s, x2, y0 + CARD_BODY, cw - 0.45, probs[:5] or [UNKNOWN], size=14)

    personas = o.get("personas") or [{}]
    s = d.slide("타겟 사용자 — 페르소나", "01 프로젝트 개요서")
    cw = (SW - 2 * MX - 0.4 * (len(personas[:2]) - 1)) / len(personas[:2])

    def persona_body(p, x, draw):
        """인용 · 원하는 것 · 불편한 것을 위에서부터 이어 놓고, 끝난 y를 돌려줍니다.

        묶음 사이는 고정 위치가 아니라 앞 묶음이 끝난 자리 + SECTION_GAP입니다 — 목록이 짧아도 벌어지지 않습니다.
        """
        bw = cw - 0.6 - T
        y = 2.72
        if p.get("quote"):
            q = "“%s”" % p["quote"]
            qh = est_text_height(q, cw - 0.6, 13)
            if draw:
                text(s, x + 0.3, y, cw - 0.6, qh + 0.05, q, size=13, bold=True, color=SUB)
            y += qh + SECTION_GAP
        for k, (label, key) in enumerate((("원하는 것", "needs"), ("불편한 것", "pains"))):
            items = bullets((p.get(key) or [])[:3]) or UNKNOWN
            bh = est_text_height(items, bw, 13)
            if draw:
                subhead(s, x + 0.3, y, cw - 0.6, label, size=13)
                text(s, x + 0.3 + T, y + HEAD_BODY, bw, bh + 0.05, items, size=13)
            y += HEAD_BODY + bh + (SECTION_GAP if k == 0 else 0)
        return y

    end = max(persona_body(p, 0, False) for p in personas[:2])
    for i, p in enumerate(personas[:2]):
        x = MX + i * (cw + 0.4)
        box(s, x, 1.5, cw, min(BOTTOM - 1.5, end - 1.5 + CARD_PAD), fill=TINT, round_=True, name="persona-card")
        circle(s, x + 0.3, 1.75, 0.7, INK, (v(p.get("name"))[:1]), size=20)
        text(s, x + 1.2, 1.78, cw - 1.5, 0.4, v(p.get("name")), size=18, bold=True)
        text(s, x + 1.2, 2.18, cw - 1.5, 0.35, v(p.get("profile")), size=12, color=SUB)
        d.note("페르소나 %d 프로필" % (i + 1), p.get("profile"))
        persona_body(p, x, True)

    s = d.slide("핵심 가치 제안", "01 프로젝트 개요서")
    d.note("핵심 가치 제안", o.get("value"))
    text(s, MX, 1.7, SW - 2 * MX, 1.6, "“%s”" % v(o.get("value")), size=28, bold=True, color=INK, anchor="m")
    scope = o.get("scope", {})
    for i, (t, key) in enumerate((("이번 범위", "in"), ("범위 밖", "out"))):
        cw = (SW - 2 * MX - 0.4) / 2
        x = MX + i * (cw + 0.4)
        need = max(est_text_height(bullets(scope.get(k) or []) or UNKNOWN, cw - 0.6, 13) for k in ("in", "out"))
        box(s, x, 3.7, cw, min(BOTTOM - 3.7, CARD_BODY + need + CARD_PAD), fill=TINT, round_=True, name="scope-card")
        card_title(s, x + 0.3, 3.9, cw - 0.6, t, size=15)
        text(s, x + 0.3, 3.7 + CARD_BODY, cw - 0.6, need + 0.1, bullets(scope.get(key) or []) or UNKNOWN, size=13)

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
              [[g.get("term"), g.get("definition"), g.get("example") or "—"] for g in chunk], size=11)

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
        for sid in screens_of(f):
            owner.setdefault(sid, []).append(str(f.get("id")) + ("" if in_scope(f) else "(범위 밖)"))
    for i, chunk in enumerate(paged(screens, 12) if screens else []):
        s = d.slide("화면 목록" + (" (%d)" % (i + 1) if i else ""), "02 정보 구조도 (IA)")
        d.mark("screens")
        table(s, MX, TOP, SW - 2 * MX, (1.1, 2.0, 2.8, 1.0, 0.9, 2.2, 0.9),
              ["화면 ID", "화면명", "경로", "형태", "로그인", "기능", "변경"],
              [[n.get("id"), n.get("name"), path, NODE_KINDS.get(n.get("kind", "page"), n.get("kind")),
                {True: "필요", False: "불필요"}.get(n.get("login"), "?"),
                ", ".join(owner.get(n.get("id"), [])) or "—",
                STATUS.get(str(n.get("change", "")).upper(), ("—",))[0]] for n, path in chunk],
              size=10)
    flows = ia.get("flows") or []
    if flows:
        names = {n["id"]: n.get("name", n["id"]) for n in walk(tree)}
        # 흐름마다 기본 경로와 예외 갈래(비로그인 · 마감 등)를 함께 그립니다 — 장 나눔은 높이로 정합니다
        for i, chunk in enumerate(flow_pages(flows)):
            s = d.slide("주요 흐름" + (" (%d)" % (i + 1) if i else ""), "02 정보 구조도 (IA)")
            main_flows(s, chunk, names)
    policies = data.get("policies") or []
    for i, chunk in enumerate(paged(policies, 9) if policies else []):
        s = d.slide("공통 정책" + (" (%d)" % (i + 1) if i else ""), "02 정보 구조도 (IA)")
        d.mark("policies")
        table(s, MX, TOP, SW - 2 * MX, (1.1, 1.8, 5.5, 1.8), ["정책 ID", "항목", "규칙", "적용 화면"],
              [[p.get("id"), p.get("name"), p.get("rule"), v(p.get("screens"))] for p in chunk],
              size=11)

    # 03 기능 정의서
    d.divider(3, "기능 정의서", "큰 기능을 세부 동작 단위로 쪼갭니다. 견적 · 일정과 DB 설계의 근거입니다.")
    # 범위 안 기능을 앞에, 범위 밖 기능은 뒤에 모읍니다(같은 쪽 안에서는 입력 순서 그대로)
    inside = [f for f in feats if in_scope(f)]
    outside = [f for f in feats if not in_scope(f)]
    listed = inside + outside
    d.note("기능 목록", feats)
    for f in inside:                                 # 범위 밖 기능은 요약 · 정책을 미결로 묻지 않습니다
        d.note("%s 세부 동작 요약" % v(f.get("id")), f.get("summary"))
        d.note("%s 정책" % v(f.get("id")), f.get("policy"))
    for i, chunk in enumerate(paged(listed, 9)):
        s = d.slide("기능 목록" + (" (%d)" % (i + 1) if i else ""), "03 기능 정의서")
        table(s, MX, TOP, SW - 2 * MX, (1.3, 1.9, 0.9, 3.4, 2.6, 1.6, 1.0),
              ["기능 ID", "기능명", "화면", "세부 동작 요약", "정책", "외부 연동", "우선"],
              [[f.get("id"), f.get("name"), "\n".join(screens_of(f)) or None, f.get("summary"), f.get("policy"),
                f.get("integration") or "없음", _rank(f)] for f in chunk]
              or [[UNKNOWN] * 7], size=10)
    # MoSCoW로 범위를 먼저 정하고, 그 안의 기능만 영향 × 노력으로 순서를 봅니다
    if any(f.get("moscow") for f in feats):
        s = d.slide("우선순위 — MoSCoW", "03 기능 정의서")
        d.mark("priority")
        moscow_board(s, feats)
    if any(f.get("impact") and f.get("effort") for f in inside):
        s = d.slide("우선순위 — 영향 × 노력", "03 기능 정의서")
        d.mark("priority")
        rest = priority_matrix(s, inside)
        # 옆 설명은 제목이 하나뿐이라 ▼ 없이 card_title, 본문도 같은 x에서 시작합니다
        card_title(s, 8.9, TOP + 0.1, 3.8, "읽는 법", size=13)
        text(s, 8.9, TOP + 0.5, 3.8, 2.6,
             bullets(["MoSCoW로 정한 범위 안 기능을 어떤 순서로 할지 봅니다",
                      "영향이 크고 노력이 적은 「빠른 성과」부터 합니다",
                      "반드시인데 「큰 승부」면 일정을 나눠 먼저 시작합니다"]), size=11, spacing=6)
        if rest:
            text(s, 8.9, TOP + 3.2, 3.8, 1.6, "판단 전: " + ", ".join(v(f.get("id")) for f in rest), size=10,
                 color=SUB)
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
    rows = [[f.get("id"), f.get("name"), f.get("doc") or "%s-기능별 기획서" % f.get("id")] for f in inside[:10]]
    table(s, MX, 2.0, SW - 2 * MX, (1.5, 2.5, 5), ["기능 ID", "기능명", "기능별 문서"],
          rows or [[UNKNOWN] * 3], size=11)
    if outside:
        y = min(BOTTOM - 0.35, 2.0 + 0.4 * (max(1, len(rows)) + 1) + 0.15)
        text(s, MX, y, SW - 2 * MX, 0.35, "범위 밖 기능(%s)은 기능별 문서를 만들지 않습니다"
             % ", ".join(v(f.get("id")) for f in outside), size=11, color=SUB)

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
    draw_toc(toc_slide, toc, link=lambda run, page: d.link(run, toc_slide, page))
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
    """기능별 기획서 — 처음 보는 사람이 앞에서부터 읽어 내려갈 수 있는 순서입니다.

    표지 · 이력 · 목차 · 읽는 법 → 01 기능 개요(무엇이고 어디 있나 · 어떤 화면) → 02 흐름(무슨 일이
    어떤 순서로) → 03 기능 정의(어떤 규칙으로) → 04 화면 상세(화면마다 배치 · 동작 · 상태 · 예외) → 미결.
    규칙 정본은 ../rules/planning-slides.md §1입니다.
    """
    m = data.get("project", {})
    f = data.get("feature", {})
    d = Deck("기능별 기획서 %s" % v(f.get("id")), m)
    screens = data.get("screens", [])
    loc = f.get("location") or {}

    base = m.get("base") or "프로젝트 전체 기획서 v%s" % v(m.get("version"))
    d.cover(v(f.get("id")), v(f.get("name")), "기능별 기획서 · 기준 문서 — %s" % base)
    d.history(data.get("history", []))
    toc_slide = d.slide("목차", "문서 정보")       # 쪽 번호는 끝에서 채웁니다
    s = d.slide("이 문서를 읽는 법", "문서 정보")
    d.mark("guide")
    reading_guide(s)

    # 01 기능 개요 — 무엇이고, 앱의 어디에 있고, 어떤 화면이 얽혀 있나
    d.divider(1, "기능 개요", "왜 만들고, 무엇이고, 앱의 어디에 있는지, 어떤 화면이 얽혀 있는지 봅니다.")
    if data.get("compare"):                          # 왜 만드는가 — 개요의 맨 앞
        c = data["compare"]
        s = d.slide(v(c.get("title") or "현행 · 개선 비교"), "01 기능 개요")
        compare(s, c.get("left") or {}, c.get("right") or {})
    s = d.slide("기능 개요 — %s" % v(f.get("name")), "01 기능 개요")
    d.note("기능 요약", f.get("summary"))
    d.note("앱 안의 위치", loc.get("path"))
    box(s, MX, TOP, SW - 2 * MX, 0.8, fill=TINT, round_=True, name="summary-card")
    text(s, MX + 0.25, TOP + 0.05, SW - 2 * MX - 0.5, 0.7, v(f.get("summary")), size=15, anchor="m")
    cw = (SW - 2 * MX - 0.4) / 2
    y = TOP + 1.1
    subhead(s, MX, y, cw, "사용자 스토리", size=14)
    text(s, MX + T, y + HEAD_BODY, cw - T, 1.2, "“%s”" % v(f.get("story")), size=13, bold=True, color=SUB)
    subhead(s, MX, y + 1.5, cw, "앱 안의 위치", size=14)
    where = [("메뉴 경로 — " + v(loc.get("path")), {"bullet": 0}),
             ("앞 기능 — " + v(loc.get("before") or "없음"), {"bullet": 0}),
             ("다음 기능 — " + v(loc.get("after") or "없음"), {"bullet": 0})]
    text(s, MX + T, y + 1.5 + HEAD_BODY, cw - T, 1.4, where, size=13)
    terms = f.get("terms") or []
    x2 = MX + cw + 0.4
    subhead(s, x2, y, cw, "이 문서에 나오는 용어", size=14)
    table(s, x2 + T, y + HEAD_BODY, cw - T, (1.2, 3.4), ["용어", "뜻"],
          [[t.get("term"), t.get("definition")] for t in terms[:6]] or [["없음", "—"]], size=11)

    s = d.slide("이 기능의 화면", "01 기능 개요")
    d.mark("screens")
    text(s, MX, TOP - 0.05, SW - 2 * MX, 0.35, "보고 싶은 화면의 쪽 번호를 누르면 그 장으로 이동합니다.",
         size=12, color=SUB)
    kinds = (("wf", "와이어프레임"), ("sb", "화면설계서"), ("ex", "예외 처리"))
    screen_rows = [[sc.get("id"), sc.get("name"), sc.get("role")] + ["p. ?"] * 3 for sc in screens]
    # 다른 기능의 화면 — 이 문서에는 상세가 없지만, 이동 대상으로 나오므로 이름을 함께 보입니다
    own = {sc.get("id") for sc in screens}
    linked = {l.get("id"): l for l in (data.get("linked_screens") or [])}
    for to in sorted({n.get("to") for sc in screens for n in (sc.get("next") or []) if n.get("to") not in own}):
        ln = linked.get(to, {})
        d.note("연결 화면 %s 이름" % to, ln.get("name"))
        screen_rows.append([to, ln.get("name"), "다른 기능의 화면%s" % (" — " + ln["feature"] if ln.get("feature") else ""),
                            "—", "—", "—"])
    for sc in screens:
        d.note("%s %s 역할" % (v(sc.get("id")), v(sc.get("name"))), sc.get("role"))
    screen_table = table(s, MX, TOP + 0.4, SW - 2 * MX, (1.0, 1.8, 4.6, 1.3, 1.2, 1.1),
                         ["화면 ID", "화면명", "역할"] + [k[1] for k in kinds],
                         screen_rows or [["—", "화면 없음", "—", "—", "—", "—"]], size=11)

    # 02 흐름 — 무슨 일이 어떤 순서로 일어나나
    d.divider(2, "흐름", "사용자가 무엇을 하면 시스템이 어떤 순서로 처리하고, 어느 화면으로 이어지는지 봅니다.")
    flow = data.get("flow")
    flow_refs = []                                   # (흐름도 장, 렌더러가 돌려준 ref)
    if flow and flow.get("nodes"):
        # 섹션(코드 앞부분 · A1-02의 A1)마다 한 장 — 섹션이 하나면 제목에 섹션을 붙이지 않습니다
        secs = flow_sections(flow)
        for sec in secs:
            many = len(secs) > 1
            s = d.slide("기능 흐름도" + (" — %s %s" % (sec["key"], v(sec.get("title"))) if many else ""), "02 흐름")
            for nid in sec.get("ids") or []:
                d.mark("flow:%s" % nid)                  # 섹션 밖 「→ 코드」 연결자의 링크 대상
            fit = workflow_chart(s, flow, section=sec["key"] if many else None, feature_id=f.get("id"))
            # 화면 쪽 표시(p. N) · 다른 기능 이동(→ F-…) — 쪽이 정해진 뒤 끝에서 채웁니다
            flow_refs += [(s, ref) for ref in (fit or {}).get("refs") or []]
            if (fit or {}).get("overflow"):
                print("경고  기능 흐름도%s: 한 장에 다 들어가지 않습니다 (%s열 × %s행) — 섹션을 나눕니다"
                      % (" " + str(sec["key"]) if many else "", fit.get("cols"), fit.get("rows")))
    # 화면 흐름은 늘 만듭니다 — 화면이 하나여도 어디서 들어와 어디로 나가는지(예외 포함)를 보입니다
    s = d.slide("화면 흐름", "02 흐름")
    screen_flow(s, screens, data.get("linked_screens"))

    # 03 기능 정의 — 어떤 규칙으로 동작하나
    d.divider(3, "기능 정의", "흐름을 이루는 입력 · 처리 순서와, 지켜야 할 조건 · 정책을 봅니다.")
    s = d.slide("입력값 · 처리 순서", "03 기능 정의")
    subhead(s, MX, TOP, 6, "입력값", size=14)
    table(s, MX + T, TOP + HEAD_BODY, 6.0 - T, (1.4, 1, 2.6), ["항목", "형식", "규칙"],
          [[i.get("name"), i.get("type"), i.get("rule")] for i in (f.get("inputs") or [])[:7]] or [[UNKNOWN] * 3],
          size=10)
    subhead(s, 7.0, TOP, 5.7, "처리 순서", size=14)
    steps = lst(f.get("process"))
    d.note("처리 순서", steps)
    numbered_list(s, 7.0 + T, TOP + HEAD_BODY + 0.05, 5.75 - T, steps[:8] or [UNKNOWN], size=12)

    s = d.slide("조건 · 정책 · 외부 연동", "03 기능 정의")
    cols = (("조건", f.get("conditions")), ("정책", f.get("policies")), ("외부 연동", f.get("integrations")))
    cw = (SW - 2 * MX - 0.8) / 3
    need = max(est_text_height(bullets(it or []) or UNKNOWN, cw - 0.35, 13, 8) for _, it in cols)
    ch = min(BOTTOM - 1.5, CARD_BODY + need + CARD_PAD)
    y0 = group_top(ch)
    for i, (t, items) in enumerate(cols):
        x = MX + i * (cw + 0.4)
        raw, items = items or [], lst(items)
        if t != "외부 연동":
            d.note(t, items)
        box(s, x, y0, cw, ch, fill=TINT, round_=True, name="rule-card")
        card_title(s, x + 0.25, y0 + 0.2, cw - 0.5, t, size=16)     # 카드마다 제목 하나 — ▼ 없음
        text(s, x + 0.25, y0 + CARD_BODY, cw - 0.35, ch - 0.8, bullets(raw)
             or ("없음" if t == "외부 연동" else UNKNOWN), size=13, spacing=8)

    acc = f.get("acceptance") or []
    if acc:
        s = d.slide("수용 기준", "03 기능 정의")
        text(s, MX, TOP - 0.05, SW - 2 * MX, 0.35, "이 상황에서 이렇게 하면 이렇게 되어야 완성입니다.", size=12,
             color=SUB)
        table(s, MX, TOP + 0.4, SW - 2 * MX, (0.6, 3, 3, 3), ["No", "상황 (Given)", "행동 (When)", "결과 (Then)"],
              [[i, a.get("given"), a.get("when"), a.get("then")] for i, a in enumerate(acc[:8], 1)], size=10)

    # 04 화면 상세 — 화면마다 한 묶음
    d.divider(4, "화면 상세", "화면마다 배치(와이어프레임) · 요소별 동작(화면설계서) · 상태 · 예외를 한 묶음으로 봅니다.")
    for sc in screens:
        regions = sc.get("regions") or []
        sid = v(sc.get("id"))
        title = "%s %s" % (sid, v(sc.get("name")))
        sec = "04 화면 상세 · %s" % sid
        d.note("%s 경로" % title, sc.get("path"))
        # 와이어프레임 — 역할 · 배치 · 이동
        s = d.slide("와이어프레임 — " + title, sec)
        d.mark("wf:" + str(sc.get("id")))
        _header(s, sc, m)
        phone(s, MX + 0.4, SB_Y, SB_PHONE_H, regions)
        subhead(s, 4.1, SB_Y, 8.6, "이 화면의 역할", size=14)
        rh = est_text_height(v(sc.get("role")), SW - MX - 4.1 - T, 13, 0)
        text(s, 4.1 + T, SB_Y + HEAD_BODY, SW - MX - 4.1 - T, rh + 0.05, v(sc.get("role")), size=13)
        # 역할 아래에 영역 구성 · 이동 흐름을 좌우로 — 위아래로 쌓으면 영역이 많을 때 바닥글까지 내려갑니다
        y = SB_Y + HEAD_BODY + rh + SECTION_GAP
        hw = (SW - MX - 4.1 - 0.3) / 2
        x2 = 4.1 + hw + 0.3
        subhead(s, 4.1, y, hw, "영역 구성", size=14)
        table(s, 4.1 + T, y + HEAD_BODY, hw - T, (0.45, 0.9, 2.4), ["No", "유형", "영역"],
              [[r.get("no", i), r.get("type"), r.get("label")] for i, r in enumerate(regions[:10], 1)]
              or [[UNKNOWN] * 3], size=10, row_h=0.32)
        nx = sc.get("next") or []
        subhead(s, x2, y, hw, "이동 흐름", size=14)
        table(s, x2 + T, y + HEAD_BODY, hw - T, (0.55, 1.6, 1.0), ["요소", "조건", "이동할 화면"],
              [[n.get("element"), n.get("when"), n.get("to")] for n in nx[:10]] or [["없음", "", ""]],
              size=10, row_h=0.32)
        # 화면설계서 — 번호 표식과 Description
        elems = sc.get("elements") or []
        d.note("%s 요소 동작" % title, elems)
        dx, dw = 4.1, SW - MX - 4.1
        pages = paginate_desc(elems, dw - T, BOTTOM - SB_Y - 0.5)
        for i, chunk in enumerate(pages):
            s = d.slide("화면설계서 — " + title + (" (%d)" % (i + 1) if len(pages) > 1 else ""), sec)
            d.mark("sb:" + str(sc.get("id")))
            _header(s, sc, m)
            phone(s, MX + 0.4, SB_Y, SB_PHONE_H, regions)
            description_list(s, dx, SB_Y, dw, chunk or [{"no": "?", "name": UNKNOWN, "behavior": UNKNOWN}])
        if sc.get("states"):
            s = d.slide("화면 상태 — " + title, sec)
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
        s = d.slide("예외 처리 — " + title, sec)
        d.mark("ex:" + str(sc.get("id")))
        _header(s, sc, m)
        table(s, MX, SB_Y, SW - 2 * MX, (1.2, 1.3, 2.5, 6.0), ["예외 ID", "상황", "사용자 메시지", "처리"],
              rows[:9], size=11)

    d.questions(data.get("open_questions"))

    # 목차 — 큰 묶음과 쪽 번호만. 화면 찾기는 「이 기능의 화면」 표가 맡습니다
    sections = [("01", "기능 개요", "무엇이고 어디 있나 · 이 기능의 화면", d.marks.get("div1")),
                ("02", "흐름", "무슨 일이 어떤 순서로 일어나나", d.marks.get("div2")),
                ("03", "기능 정의", "입력 · 처리 순서 · 조건 · 정책", d.marks.get("div3")),
                ("04", "화면 상세", "화면마다 배치 · 동작 · 상태 · 예외", d.marks.get("div4"))]
    if "questions" in d.marks:
        sections.append(("—", "미결 사항", "확정 전에 정할 것", d.marks["questions"]))
    draw_toc(toc_slide, sections, link=lambda run, page: d.link(run, toc_slide, page))
    # 「이 기능의 화면」 표의 쪽 칸 — 쪽이 정해진 뒤 채우고 링크를 겁니다
    screen_slide = d.page_slide(d.marks["screens"])
    for r, sc in enumerate(screens, 1):
        for c, (k, _) in enumerate(kinds, 3):
            page = d.marks.get("%s:%s" % (k, sc.get("id")))
            cell = screen_table.table.cell(r, c)
            run = cell.text_frame.paragraphs[0].runs[0]
            run.text = "p. %s" % (page or "—")
            d.link(run, screen_slide, page)
    # 흐름도의 화면 쪽 표시 — 이 기능의 화면은 와이어프레임 장, 다른 기능의 화면 · 다른 기능 이동은 「이 기능의 화면」 장
    for flow_slide, ref in flow_refs:
        run = ref.get("run")
        if run is None:
            continue
        if ref.get("screen") is not None:
            page = d.marks.get("wf:%s" % ref["screen"]) or d.marks.get("screens")
            run.text = "p. %s" % (page or "—")
        elif ref.get("node") is not None:            # 섹션 밖 「→ 코드」 — 그 도형이 그려진 흐름도 장
            page = d.marks.get("flow:%s" % ref["node"])
        else:                                        # feature — 「→ F-…」 글은 렌더러가 쓴 그대로 둡니다
            page = d.marks.get("screens")
        d.link(run, flow_slide, page)
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
        tree = (data.get("ia") or {}).get("tree") or []
        nodes = [n.get("id") for n in walk(tree)]
        for f in data.get("features", []):
            for sid in screens_of(f):
                if sid not in nodes:
                    warn.append("%s: 화면 %s가 IA에 없습니다" % (f.get("id"), sid))
            if f.get("scope") == "out" and _moscow(f) in ("must", "should"):
                err.append("%s: 범위 밖(scope: out)인데 moscow가 %s입니다 — 둘 중 하나를 고칩니다"
                           % (f.get("id"), f.get("moscow")))
        # IA 잎 화면마다 범위 안 기능이 하나는 있어야 합니다 — 빠진 기능을 찾습니다
        covered = {sid for f in data.get("features", []) if in_scope(f) for sid in screens_of(f)}
        for n, _ in _paths(tree):
            if n.get("kind") != "external" and n.get("id") not in covered:
                warn.append("%s: 연결된 기능이 없습니다 — 기능 목록의 screen에 적습니다" % n.get("id"))
        for fl in (data.get("ia") or {}).get("flows") or []:
            path = fl.get("path") or []
            for sid in path:
                if sid not in nodes:
                    warn.append("흐름 %s: %s가 IA에 없습니다" % (fl.get("name"), sid))
            for ex in fl.get("exceptions") or []:
                if ex.get("from") not in path:
                    err.append("흐름 %s: 예외 갈래의 from %s가 흐름 경로에 없습니다" % (fl.get("name"), ex.get("from")))
                to = str(ex.get("to") or "")
                if re.match(r"^S\d", to) and to not in nodes:
                    warn.append("흐름 %s: 예외 갈래의 to %s가 IA에 없습니다" % (fl.get("name"), to))
        if any(n.get("change") for n in walk(tree)) and not (data.get("project") or {}).get("change_base"):
            warn.append("변경 배지가 있지만 project.change_base가 비어 있습니다 — 무엇에 비해 바뀌었는지 적습니다")
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
        # 변경 배지는 비교할 이전 버전이 있을 때만 뜻이 있습니다
        if len(data.get("history") or []) < 2:
            marked = [sc.get("id") for sc in data.get("screens", []) if sc.get("change")]
            marked += ["%s-%s" % (sc.get("id"), e.get("no")) for sc in data.get("screens", [])
                       for e in sc.get("elements") or [] if e.get("change")]
            if marked:
                warn.append("변경 배지(%s)가 있지만 문서 이력이 한 줄뿐입니다 — 무엇에 비해 바뀌었는지 이력에 적습니다"
                            % ", ".join(marked))
        if len((data.get("feature") or {}).get("terms") or []) > 6:
            warn.append("용어는 6개까지 보입니다 — 7번째부터는 빠집니다. 합치거나 전체 문서의 용어 정의로 옮깁니다")
        # 등록 여부와 의미를 따로 검사합니다. 코드 접두로 화면 종류를 추측하지 않습니다.
        catalog = list(data.get("screens") or []) + list(data.get("linked_screens") or [])
        screen_ids = set()
        for sc in catalog:
            sid = sc.get("id")
            if not isinstance(sid, str) or not sid.strip():
                err.append("화면 ID는 비어 있지 않은 문자열이어야 합니다")
                continue
            if sid in screen_ids:
                err.append("화면 카탈로그 ID 중복: %s" % sid)
            screen_ids.add(sid)
        for sc in data.get("linked_screens") or []:
            if not sc.get("name"):
                warn.append("연결 화면 %s의 이름이 없습니다" % sc.get("id"))
        fl = data.get("flow") or {}
        non_screens = {n.get("id") for n in fl.get("nodes") or [] if n.get("type") not in FLOW_SCREEN_TYPES}
        for sid in screen_ids & non_screens:
            err.append("화면 %s: 처리·조건 등 화면이 아닌 흐름 노드와 ID가 겹칩니다 — 화면과 ID를 나눠 쓰는 도형은 "
                       "input · output뿐입니다" % sid)
        validate_flow(fl, err, warn, screen_ids=screen_ids, feature_id=(data.get("feature") or {}).get("id"))
        for sc in data.get("screens", []):
            for n in sc.get("next") or []:
                to = n.get("to")
                if not isinstance(to, str) or not to.strip():
                    err.append("%s: 이동할 화면 ID가 없습니다 — 미정 이동은 open_questions에 적습니다" % sc.get("id"))
                elif to not in screen_ids:
                    err.append("%s: 이동 대상 %s는 등록된 화면이 아닙니다 — 처리·조건은 flow에 적습니다"
                               % (sc.get("id"), to))
                if n.get("kind") not in (None, "exception"):
                    err.append("%s: 이동의 kind는 exception만 씁니다 (%r)" % (sc.get("id"), n.get("kind")))
    return err, warn


def flow_section_key(n):
    """도형의 섹션 — 코드(없으면 id)가 A1-02처럼 앞부분을 가지면 그 앞부분(A1), 아니면 None(흐름 전체)."""
    code = str(n.get("code") or n.get("id") or "")
    return code.rsplit("-", 1)[0] if "-" in code else None


def validate_flow(fl, err, warn, screen_ids=None, feature_id=None):
    """기능 흐름도(flow) 검사 — 워크플로우 탐색기 §2와 같은 기준입니다. 결과는 err · warn에 더합니다.

    screen_ids: 등록된 화면 ID(screens + linked_screens) — 도형의 screen이 여기 있어야 합니다(None이면 건너뜀).
    feature_id: 이 기능의 ID — 연결의 to가 자기 기능 ID면 경고합니다.
    """
    nodes = fl.get("nodes") or []
    edges = fl.get("edges") or []
    if not nodes and not edges:
        return
    before = len(err)
    # 옛 형식이면 하나하나 따지지 않고 이전 안내 하나만 냅니다 — 같은 원인의 오류가 수십 줄 쌓이지 않게
    old = sorted({"type %s" % n.get("type") for n in nodes if n.get("type") in FLOW_OLD_TYPES}
                 | {"lane %s" % n.get("lane") for n in nodes if n.get("lane") in FLOW_OLD_LANES}
                 | {"노드 label" for n in nodes if "label" in n and "text" not in n}
                 | {"kind exception" for e in edges if e.get("kind") == "exception"})
    if old:
        err.append("흐름도: %s (발견: %s)" % (FLOW_MIGRATION, ", ".join(old)))
        return
    lanes = fl.get("lanes") or FLOW_LANES
    lane_keys = [ln.get("key") for ln in lanes]
    user = "u" if "u" in lane_keys else (lane_keys[0] if lane_keys else None)
    node_ids = [n.get("id") for n in nodes]
    ids = {i for i in node_ids if isinstance(i, str) and i.strip()}
    if len(ids) != len(node_ids):
        err.append("흐름도: 노드 ID는 비어 있지 않은 문자열이며 중복될 수 없습니다")
    for n in nodes:
        nid, t = n.get("id"), n.get("type")
        if t not in FLOW_TYPES:
            err.append("흐름도 %s: 알 수 없는 도형 %r (%s)" % (nid, t, " · ".join(FLOW_TYPES)))
        if n.get("lane") not in lane_keys:
            err.append("흐름도 %s: 알 수 없는 구역 %r (%s)" % (nid, n.get("lane"), " · ".join(map(str, lane_keys))))
        if t == "ref" and n.get("target") not in ids:
            err.append("흐름도 %s: 반복 지점의 target %r가 없는 도형입니다" % (nid, n.get("target")))
        if not str(n.get("text") or "").strip():
            warn.append("흐름도 %s: 문구(text)가 비어 있습니다" % nid)
        # 화면 쪽 링크 — 이동 대상(next.to)과 같은 기준으로 등록된 화면만 받습니다
        if "screen" in n and screen_ids is not None:
            sc = n.get("screen")
            if not isinstance(sc, str) or sc not in screen_ids:
                err.append("흐름도 %s: screen %r는 등록된 화면이 아닙니다 — screens 또는 linked_screens에 적습니다"
                           % (nid, sc))
        # 판정 기준 — 조건(decision)에만 씁니다. 객체면 탐색기 형식 {"path", "equals"(선택)}
        if "check" in n:
            ck = n.get("check")
            if t != "decision":
                warn.append("흐름도 %s: 판정 기준(check)은 조건(decision)에만 씁니다 — 이 도형은 %s입니다" % (nid, t))
            if isinstance(ck, dict):
                if not isinstance(ck.get("path"), str) or not ck["path"].strip():
                    err.append("흐름도 %s: check 객체에는 비어 있지 않은 문자열 path가 있어야 합니다" % nid)
            elif not isinstance(ck, str):
                err.append("흐름도 %s: check는 문자열 또는 {\"path\", \"equals\"} 객체입니다 (%r)" % (nid, ck))
    for e in edges:
        to = e.get("to")
        cross = isinstance(to, str) and FLOW_FEATURE_RE.match(to) and to not in ids
        if e.get("from") not in ids or (to not in ids and not cross):
            err.append("흐름도 연결 %s → %s: 없는 노드" % (e.get("from"), to))
        elif cross and to == feature_id:
            warn.append("흐름도 연결 %s → %s: 이 기능 자신의 ID입니다 — 이 기능 안의 도형으로 잇습니다"
                        % (e.get("from"), to))
        if e.get("kind", "normal") not in FLOW_KINDS:
            err.append("흐름도 연결 %s → %s: 알 수 없는 연결 종류 %r (%s)"
                       % (e.get("from"), e.get("to"), e.get("kind"), " · ".join(FLOW_KINDS)))
    if len(err) > before:                  # 구조가 깨졌으면 출구 · 구역 경고는 뜻이 없습니다
        return
    for n in nodes:
        nid, t = n.get("id"), n.get("type")
        outgoing = [e for e in edges if e.get("from") == nid]
        if t == "decision":
            kinds = {e.get("kind") for e in outgoing}
            if len(outgoing) < 2 or not {"yes", "no"} <= kinds:
                warn.append("흐름도 %s: 조건 출구가 부족합니다 — 예(kind yes)와 아니오(kind no) 연결을 모두 둡니다" % nid)
        elif t not in ("term", "ref") and not outgoing:
            warn.append("흐름도 %s: 출구가 없습니다 — 종료(term)·복귀(ref)·미정 여부를 검토합니다" % nid)
        # 유저가 입력·선택하는 도형은 유저 구역, 판단·처리·노출은 시스템 구역입니다(explorer §1)
        if t == "input" and n.get("lane") != user:
            warn.append("흐름도 %s: 입력(input)은 유저 구역에 둡니다" % nid)
        elif t in ("decision", "output", "process") and n.get("lane") == user:
            warn.append("흐름도 %s: 판단·노출·공통 처리(%s)는 시스템 구역에 둡니다" % (nid, t))
    for e in edges:
        if e.get("kind") in ("yes", "no"):
            src = next(n for n in nodes if n.get("id") == e.get("from"))
            if src.get("type") != "decision":
                warn.append("흐름도 연결 %s → %s: 예·아니오(kind %s)는 조건(decision)에서만 나갑니다"
                            % (e.get("from"), e.get("to"), e.get("kind")))
    names = fl.get("sections") or {}
    count = {}
    for n in nodes:
        k = flow_section_key(n)
        count[k] = count.get(k, 0) + 1
    for k, c in sorted(count.items(), key=lambda kv: str(kv[0])):
        where = "섹션 %s" % k if k else "흐름도"
        if c > FLOW_SECTION_MAX:
            warn.append("%s: 도형은 한 장에 %d개 이하를 권합니다 — 섹션(코드 앞부분)을 나눕니다 (지금 %d)"
                        % (where, FLOW_SECTION_MAX, c))
        if k and names and k not in names:
            warn.append("섹션 %s: flow.sections에 이름이 없습니다" % k)


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
    feats = (data or {}).get("features", [])
    listed = {f.get("id") for f in feats}
    planned = {f.get("id") for f in feats if in_scope(f)}      # 범위 밖 기능은 기능별 문서를 만들지 않습니다
    made = set()
    for p in sorted(glob.glob(os.path.join(folder, "features", "*.json"))):
        r, fd = run("feature", p, os.path.join(outdir, "features", os.path.basename(p)[:-5] + ".pptx"))
        rc |= r
        if fd:
            made.add((fd.get("feature") or {}).get("id"))
    for i in sorted(made - listed):
        print("오류  기능별 문서 %s가 전체 문서의 기능 목록에 없습니다" % i)
        rc = 1
    for i in sorted(planned - made):
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
