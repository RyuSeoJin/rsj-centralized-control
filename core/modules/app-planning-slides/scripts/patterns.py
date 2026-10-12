# -*- coding: utf-8 -*-
"""슬라이드 패턴 — 여러 장에서 되풀이되는 구성 단위

패턴마다 쓰임 · 최대 개수 · 배치가 정해져 있습니다. 정본은 ../rules/slide-patterns.md이며,
패턴을 더하거나 고치면 그 문서와 견본 덱(build_slides.py gallery)을 함께 맞춥니다.

모든 패턴은 본문 영역(y 1.45 ~ SH-0.6, x MX ~ SW-MX) 안에 그리고, 범례는 오른쪽 아래 같은 자리에
둡니다. 최대 개수를 넘는 입력은 패턴이 자르지 않고, 덱 조립 쪽이 장을 나눕니다.
"""
from slidekit import *  # noqa: F401,F403
from slidekit import SW, SH, MX, UNKNOWN, TOGGLE_STEP  # noqa: F401

TOP = 1.45                    # 본문이 시작하는 높이 — 제목 아래
BOTTOM = SH - 0.6             # 본문이 끝나는 높이 — 푸터 위


#: 한 카드 안에서 ▼ 소제목 묶음과 다음 ▼ 소제목 사이 틈 — 앞 묶음이 끝난 자리에서 이만큼만 띄웁니다
SECTION_GAP = 0.22
#: 카드 높이 = 본문 시작 위치(소제목 아래) + 내용 높이 + 아래 여백 — 카드마다 같은 공식이라 여백이 같습니다
CARD_BODY = 0.64
CARD_PAD = 0.3


def group_top(height, top=1.5):
    """내용 높이에 맞춘 카드 묶음의 위쪽 y — 남는 높이의 35%를 위에 둡니다.

    카드를 내용에 맞춰 줄이면 위에 붙여 둘 때 아래가 크게 빕니다. 정가운데보다 조금 위에 두어야
    제목과 이어져 읽힙니다.
    """
    return top + max(0.0, BOTTOM - top - height) * 0.35


# ── 번호 목록 ─────────────────────────────────────────────────────────

#: 번호 목록의 항목 사이 틈(in) — 글머리 목록과 비슷한 리듬으로, 고정 간격이 아니라 글 높이 + 이 틈입니다
NUM_GAP = 0.16


def numbered_list(slide, x, y, w, items, size=14, fill=INK):
    """번호 원 + 글 목록. 원은 본문 한 줄 높이 정도이고, 원 뒤는 글머리처럼 짧은 간격입니다.

    · 첫 항목의 글은 y에서 시작합니다 — 옆 카드의 본문과 같은 높이에 맞출 수 있습니다.
    · 글의 첫 줄 세로 중심을 원의 중심에 맞춥니다(slide-patterns.md §4).
    · 항목 간격은 글 높이 + NUM_GAP이라, 여러 줄 항목은 그만큼 내려가고 틈은 늘 같습니다.
    마지막 항목 아래 끝 y를 돌려줍니다.
    """
    lh = line_height(size)
    d = round(size * 1.43 / 72.0, 3)                       # 원 지름 — 본문 한 줄 높이 정도
    gap = size * MARK_GAP / 72.0 + 0.04
    tw = w - d - gap
    for no, body in enumerate(items, 1):
        mid = glyph_mid(y, size)                           # 첫 줄 글자의 눈에 보이는 중심
        circle(slide, x, mid - d / 2.0, d, fill, str(no), size=max(8, int(size * 0.72)))
        th = est_text_height(body, tw, size, 0)
        text(slide, x + d + gap, y, tw, th + 0.05, body, size=size)
        y += max(th, d) + NUM_GAP
    return y - NUM_GAP


# ── 목차 ──────────────────────────────────────────────────────────────

def draw_toc(slide, entries, x=MX, w=SW - 2 * MX, top=1.5, step=None, link=None):
    """번호 · 제목 · 설명과 오른쪽 끝의 쪽 번호. 제목과 쪽 번호 사이를 옅은 선으로 잇습니다.

    link(run, page)를 주면 쪽 번호 글자에 그 장으로 가는 링크를 겁니다.
    """
    step = step or min(1.05, (SH - top - 0.7) / max(1, len(entries)))
    for i, (no, t, lead, page) in enumerate(entries):
        y = top + i * step
        text(slide, x, y, 1.0, 0.7, no, size=28, bold=True, color=ACCENT)
        # ① 큰 번호와 제목은 글자 중심을 맞춥니다
        mid = glyph_mid(y, 28)
        ty = first_line_top(mid, 18)
        text(slide, x + 1.1, ty, w - 2.4, line_height(18) + 0.06, t, size=18, bold=True)
        ly = ty + line_height(18) + 0.04
        text(slide, x + 1.1, ly, w - 2.4, 0.36, lead, size=12, color=SUB)
        line(slide, x + 1.1, y + step - 0.12, x + w, y + step - 0.12, color=LINE, width=0.75)
        # ② 쪽 번호는 제목과 설명 두 줄 묶음의 세로 가운데에 둡니다
        block = (mid + glyph_mid(ly, 12)) / 2.0
        pb = text(slide, x + w - 1.2, first_line_top(block, 16), 1.2, line_height(16) + 0.06,
                  "p. %s" % (page or "—"), size=16, bold=True, color=INK, align="r")
        if link and page:
            link(pb.text_frame.paragraphs[0].runs[0], page)


# ── 정보 구조도 ───────────────────────────────────────────────────────

#: 노드 형태 — 모양으로 구분하고 범례에 글자로 적습니다
NODE_KINDS = {"page": "페이지", "popup": "팝업", "tab": "탭", "external": "외부 링크"}
TAB_FILL = "E6EDF3"
IA_MAX_LEAVES = 14


def walk(nodes):
    for n in nodes:
        yield n
        for c in walk(n.get("children") or []):
            yield c


def leaves(n):
    ch = n.get("children") or []
    return sum(leaves(c) for c in ch) if ch else 1


def ia_pages(tree):
    """잎이 많으면 최상위 메뉴마다 한 장으로 나눕니다. 한 장에 다 들어가면 그대로 둡니다."""
    if sum(leaves(n) for n in tree) <= IA_MAX_LEAVES:
        return [(None, tree)]
    if len(tree) == 1:
        root = tree[0]
        return [(c, [dict(root, children=[c])]) for c in root.get("children") or []] or [(None, tree)]
    return [(n, [n]) for n in tree]


def _node(slide, x, y, w, h, n, k, has_children, fs):
    kind = n.get("kind", "page")
    label = "%s  %s" % (n.get("id", ""), n.get("name", UNKNOWN))
    if kind == "external":
        label += "  ↗"
    root = k == 0
    fill = INK if root else (TINT if has_children else (TAB_FILL if kind == "tab" else WHITE))
    shp = box(slide, x, y, w, h, fill=fill,
        line=None if root else (INK if has_children else GRID),
        shape="round",
        dash=kind in ("popup", "external"), label=label.strip(), size=fs,
        color=WHITE if root else INK, bold=has_children, align="l", name="ia-node")
    if n.get("change"):
        badge(slide, x + w - 0.5, y - 0.1, n["change"], size=7)
    return shp


def ia_legend(slide, tree):
    kinds = {n.get("kind", "page") for n in walk(tree)}
    changes = []
    for n in walk(tree):
        c = str(n.get("change", "")).upper()
        if c and c not in changes:
            changes.append(c)
    items = []
    for k in ("page", "tab", "popup", "external"):
        if k in kinds and (k != "page" or len(kinds) > 1):
            items.append((lambda s, x, y, k=k: box(s, x, y, 0.28, 0.18, fill=TAB_FILL if k == "tab" else WHITE,
                                                   line=INK, shape="round",
                                                   dash=k in ("popup", "external"),
                                                   label="↗" if k == "external" else None, size=7),
                          NODE_KINDS[k]))
    for c in changes:
        items.append((lambda s, x, y, c=c: box(s, x, y, 0.28, 0.18, fill=STATUS.get(c, ("", MUTED))[1],
                                               shape="capsule"), STATUS.get(c, (c,))[0]))
    if items:
        legend(slide, items)


def draw_tree(slide, tree):
    """깊이마다 열을 하나씩 두고, 잎을 위에서부터 쌓는 가로 트리입니다. 범례는 오른쪽 아래입니다."""
    depth = [0]

    def dmax(ns, k):
        for n in ns:
            depth[0] = max(depth[0], k)
            dmax(n.get("children") or [], k + 1)
    dmax(tree, 0)
    cols = depth[0] + 1
    total = max(1, sum(leaves(n) for n in tree))
    top, avail = TOP, BOTTOM - TOP - 0.45          # 범례 자리를 비워 둡니다
    slot = avail / total
    nh = max(0.26, min(0.5, slot * 0.78))
    fs = 10 if nh >= 0.34 else 8
    gap = 0.45
    cw = min(2.9, (SW - 2 * MX - gap * (cols - 1)) / cols)
    # 트리 전체를 가로 가운데에 둡니다 — 왼쪽에 몰리면 오른쪽 위가 크게 빕니다
    x_off = (SW - 2 * MX - (cols * cw + gap * (cols - 1))) / 2.0
    cursor = [top]

    def place(n, k):
        ch = n.get("children") or []
        x = MX + x_off + k * (cw + gap)
        if ch:
            kids = [place(c, k + 1) for c in ch]
            y = (kids[0][0] + kids[-1][0]) / 2.0
        else:
            y = cursor[0] + (slot - nh) / 2.0
            cursor[0] += slot
        shp = _node(slide, x, y, cw, nh, n, k, bool(ch), fs)
        # 부모 오른쪽 → 자식 왼쪽을 Z자 연결선 하나로 잇고 양 끝을 노드에 붙입니다(노드를 옮기면 따라옵니다)
        for cy, cshp in (kids if ch else []):
            elbow(slide, x + cw, y + nh / 2, x + cw + gap, cy + nh / 2, first="h", mid=x + cw + gap / 2.0,
                  color=MUTED, start=(shp, 3), end=(cshp, 1))
        return y, shp
    for n in tree:
        place(n, 0)
    ia_legend(slide, tree)


# ── 화면설계서 ────────────────────────────────────────────────────────

def storyboard_header(slide, fields, change=None, y=1.3):
    """화면 정보 띠 — 이름 칸(옅은 회색)과 값 칸(흰색)을 번갈아 둡니다. 변경 배지는 오른쪽 끝입니다.

    fields: [(이름, 값, 폭 비율)]. 장마다 같은 자리 · 같은 칸이라 화면을 넘겨도 눈이 같은 곳을 봅니다.
    """
    x, h = MX, 0.36
    right = SW - MX                                   # 배지가 있어도 띠 길이는 같습니다
    tot = sum(f[2] for f in fields)
    unit = (right - x - 0.75 * len(fields)) / tot
    for name, val, ratio in fields:
        box(slide, x, y, 0.75, h, fill=TABLE["head_fill"], line=GRID, label=name, size=9, bold=True, color=INK)
        w = unit * ratio
        box(slide, x + 0.75, y, w, h, fill=WHITE, line=GRID, label=v(val), size=10, align="l")
        x += 0.75 + w
    if change:
        # 배지는 마지막 값 칸 안 오른쪽 — 띠 밖에 떠 있으면 띠 길이가 장마다 달라 보입니다
        name, color = STATUS.get(str(change).upper(), (str(change), MUTED))
        bw = 0.16 + 0.11 * len(name)
        badge(slide, right - bw - 0.08, y + (h - 0.22) / 2, change, size=8)


DESC_GAP = 0.14


def _desc_height(item, w):
    body = v(item.get("behavior"))
    h = 0.34 + est_lines(body, w - 0.45, 11) * 0.24
    h += sum(est_lines(s, w - 0.75, 10) * 0.23 for s in item.get("sub") or [])
    return h


def paginate_desc(items, w, h):
    """Description을 높이에 맞춰 장으로 나눕니다. 한 장에 넣지 못하는 항목은 다음 장으로 넘깁니다."""
    pages, cur, used = [], [], 0.0
    for it in items:
        need = _desc_height(it, w) + DESC_GAP
        if cur and used + need > h:
            pages.append(cur)
            cur, used = [], 0.0
        cur.append(it)
        used += need
    pages = pages + [cur] if cur else pages or [[]]
    if len(pages) < 2:
        return pages
    # 마지막 장에 한두 개만 남으면 장마다 높이를 고르게 다시 나눕니다 — 한 장은 꽉 차고 다음 장은 비는 것을 막습니다
    heights = [_desc_height(it, w) + DESC_GAP for it in items]
    target = sum(heights) / len(pages)
    out, cur, used = [], [], 0.0
    for it, hh in zip(items, heights):
        if cur and used + hh > target * 1.08 and len(out) < len(pages) - 1:
            out.append(cur)
            cur, used = [], 0.0
        cur.append(it)
        used += hh
    out.append(cur)
    return out if all(sum(_desc_height(i, w) + DESC_GAP for i in pg) <= h for pg in out) else pages


def description_list(slide, x, y, w, items, title="Description"):
    """와이어프레임의 번호 표식과 1:1로 대응하는 설명 목록입니다. 하위 항목은 1-1) 형식으로 씁니다."""
    card_title(slide, x, y, w, title, size=12)           # 제목 하나뿐 — ▼ 없이, 본문도 같은 선에서
    line(slide, x, y + 0.34, x + w, y + 0.34, color=GRID, width=0.75)
    cy = y + 0.48
    for it in items:
        no = str(it.get("no", "?"))
        circle(slide, x, cy + 0.02, 0.26, ACCENT, no, size=9)
        name = v(it.get("name"))
        if it.get("change"):
            badge(slide, x + w - 0.62, cy + 0.04, it["change"], size=7)
        text(slide, x + 0.4, first_line_top(cy + 0.15, 12), w - 1.1, 0.28, name, size=12, bold=True)
        body = v(it.get("behavior"))
        bh = est_lines(body, w - 0.45, 11) * 0.24
        text(slide, x + 0.4, cy + 0.32, w - 0.45, bh + 0.05, body, size=11, color=INK, spacing=2)
        sy = cy + 0.34 + bh
        for j, sub in enumerate(it.get("sub") or [], 1):
            sh = est_lines(sub, w - 0.75, 10) * 0.23
            text(slide, x + 0.4, sy, w - 0.45, sh + 0.04, "%s-%d) %s" % (no, j, sub), size=10, color=SUB,
                 spacing=1)
            sy += sh
        cy += _desc_height(it, w) + DESC_GAP


# ── 기능 흐름도 — 워크플로우 탐색기 규칙 ──────────────────────────────
#
# 규칙 정본은 core/modules/workflow-explorer/rules/explorer.md §1 · §3 「흐름도」입니다. 탐색기는 좌표를 받지 않고
# 흐름의 의미(도형 · 구역 · 연결)만 받아 배치를 계산합니다 — 같은 데이터면 탐색기와 슬라이드가 같은 그림이 되도록
# 배치 원칙(열 · 행 · 구역 뒤집기 · 먼 복귀 연결자 · 통로)을 그대로 옮기고, 한 장에 맞게 크기만 줄입니다.
# 입력: flow = {"lanes", "sections", "nodes": [{id, code, type, lane, text, target, screen, check}],
#              "edges": [{from, to, kind, label}]} — to는 다른 기능 ID(F-XXX-NN)일 수도 있습니다.

import json as _json
import re as _re
from itertools import permutations as _perms

from slidekit import _char_em, _font, path_connector, LETTER_SPACING  # noqa: F401

#: 도형 종류 — 탐색기 shape()와 같은 기호입니다(슬라이드 도형 이름)
FLOW_SHAPES = {"term": "capsule", "action": "round", "input": "para", "output": "para",
               "decision": "diamond", "process": "predefined", "ref": "oval"}
FLOW_NAMES = {"term": "시작 · 종료", "action": "행동 · 처리", "input": "입력 · 출력", "output": "입력 · 출력",
              "decision": "조건 판단", "process": "공통 처리", "ref": "반복 지점"}
FLOW_MAX = 15

#: 연결 색 — 예 파랑 · 아니오 빨강 · 일반 진한 회색(--wfx-yes · --wfx-no · --wfx-line)
WF_YES, WF_NO, WF_LINE = "2563EB", "DC2626", "1E1E1E"
WF_COLORS = {"yes": WF_YES, "no": WF_NO, "normal": WF_LINE}
#: 구역 색 — (글자 · 띠, 바탕 8%, 테두리) · 유저 초록(--wfx-user) · 시스템 파랑(--wfx-system)
WF_LANE_USER = ("16A34A", "EEF8F1", "A7DCBA")
WF_LANE_SYSTEM = ("2563EB", "EEF3FD", "ADC4F7")
#: 이동 연결자 — 주황(--wfx-jump) 점선 테두리 · 옅은 주황 바탕 · 진한 주황 글자
WF_JUMP, WF_JUMP_FILL, WF_JUMP_TEXT = "D97706", "FBEFE1", "A26217"
WF_EDGE = "3D4851"             # 도형 테두리(--ink-2)
WF_DECISION_FILL = "F2F6FE"    # 조건 도형 바탕 — 시스템 색 6%
WF_WIDTH = 1.25                # 연결선 두께(pt)

WF_LANE_COL = 1.05             # 왼쪽 구역 이름 칸
WF_W_MAX, WF_W_MIN = 1.75, 1.05
WF_TRACK = 0.13                # 나란한 선 사이(탐색기 12px 이상)
WF_TAIL = 0.22                 # 도형으로 들어가는 마지막 구간(MIN_TAIL)
WF_NARROW = 0.32               # 곧은 선만 지나는 열 사이(GAP_MIN)
WF_RG = 0.42                   # 행 사이 통로
WF_PAD = 0.16                  # 구역 위 · 아래 여백
WF_LINK_W, WF_LINK_H = 0.82, 0.4   # 이동 연결자(76×40)
WF_SLANT = 0.1                 # 평행사변형 기울기
WF_LABEL = 8                   # 선 라벨 글자 크기
WF_LABEL_H = 0.2
WF_MAX_COLS = 8
FAR_BACK = 2                   # 두 열 이상 앞으로 돌아가면 선 대신 「↩ 코드」 연결자
_SEC_RE = _re.compile(r"^([A-Za-z]+\d+)-\d+$")
_FEATURE_RE = _re.compile(r"^F-[A-Z]+-\d+$")


def _wf_sec(code):
    m = _SEC_RE.match(str(code))
    return m.group(1) if m else ""


def _wf_norm(flow):
    """입력을 다듬습니다 — code 기본값 id, 모르는 종류는 행동, 모르는 구역은 마지막 구역(시스템)."""
    lanes = [dict(l) for l in (flow.get("lanes") or [])] or [{"key": "u", "label": "유저 구역"},
                                                               {"key": "s", "label": "시스템 구역"}]
    keys = [str(l.get("key")) for l in lanes]
    nodes, order = {}, []
    for raw in flow.get("nodes") or []:
        if raw.get("id") is None or str(raw["id"]) in nodes:
            continue
        n = dict(raw)
        n["id"] = str(n["id"])
        n["code"] = str(n.get("code") or n["id"])
        n["type"] = n.get("type") if n.get("type") in FLOW_SHAPES else "action"
        n["lane"] = str(n.get("lane")) if str(n.get("lane")) in keys else keys[-1]
        n["text"] = str(n.get("text") or n.get("label") or "")
        nodes[n["id"]] = n
        order.append(n["id"])
    edges = []
    for k, e in enumerate(flow.get("edges") or []):
        a, b = str(e.get("from")), str(e.get("to"))
        if a not in nodes:
            continue
        feat = b not in nodes and bool(_FEATURE_RE.match(b))
        if b not in nodes and not feat:
            continue
        kind = e.get("kind") if e.get("kind") in WF_COLORS else "normal"
        edges.append({"i": k, "from": a, "to": b, "kind": kind, "label": str(e.get("label") or ""),
                      "feature": feat})
    start = str(flow.get("start")) if str(flow.get("start")) in nodes else (order[0] if order else None)
    return {"lanes": lanes, "keys": keys, "nodes": nodes, "order": order, "edges": edges,
            "names": flow.get("sections") or {}, "start": start, "title": flow.get("title") or ""}


def flow_sections(flow):
    """섹션(코드 앞부분 · A1-02의 A1) 목록을 읽는 순서로 — 시작 섹션, 섹션을 건너는 연결로 처음 닿는 순서, 나머지.

    돌려주는 값: [{"key", "title", "ids", "entry"}]. 코드에 앞부분이 없으면 섹션 하나("")입니다.
    """
    F = _wf_norm(flow)
    secs = {}
    for i in F["order"]:
        secs.setdefault(_wf_sec(F["nodes"][i]["code"]), []).append(i)
    if not secs:
        return []
    order, seen = [], set()

    def grow(k0):
        q = [k0]
        seen.add(k0)
        while q:
            k = q.pop(0)
            order.append(k)
            for i in secs[k]:
                for e in F["edges"]:
                    if e["from"] != i or e["feature"]:
                        continue
                    k2 = _wf_sec(F["nodes"][e["to"]]["code"])
                    if k2 not in seen:
                        seen.add(k2)
                        q.append(k2)
    grow(_wf_sec(F["nodes"][F["start"]]["code"]))
    for k in secs:
        if k not in seen:
            grow(k)
    out = []
    for k in order:
        ids = secs[k]
        # 들어오는 도형 — 시작 도형, 아니면 다른 섹션에서 처음 들어오는 도형, 아니면 첫 도형
        entry = F["start"] if F["start"] in ids else next(
            (e["to"] for e in F["edges"] if not e["feature"] and e["to"] in ids and e["from"] not in ids), ids[0])
        out.append({"key": k, "title": F["names"].get(k) or (k or F["title"]), "ids": list(ids), "entry": entry})
    return out


def check_text(check):
    """조건 도형의 판정 기준 → 「판정: …」 글. 문자열은 그대로, {"path", "equals"}는 「path = 값」입니다."""
    if check is None or check == "":
        return ""
    if isinstance(check, dict):
        s = str(check.get("path") or "")
        if "equals" in check:
            q = check["equals"]
            s += " = " + (q if isinstance(q, str) else _json.dumps(q, ensure_ascii=False))
    else:
        s = str(check)
    return "판정: " + s if s.strip() else ""


def _wf_text_w(s, size):
    """한 줄 글 폭(in) 어림."""
    return sum(_char_em(c) + LETTER_SPACING for c in str(s)) * size / 72.0


def _wf_label_w(s):
    return _wf_text_w(s, WF_LABEL) + 0.14


def _wf_pad(t, w, h):
    """도형 안 글 (좌우 여백, 글이 실제로 쓰는 폭). 프리셋 도형은 글 영역이 이미 안쪽으로 들어가 있어
    (마름모 가운데 절반 · 평행사변형 기울기 절반 · 공통 처리 세로선 안쪽 · 알약 둥근 끝 안쪽) 여백은 그 위에 더하는 몫입니다.
    평행사변형은 기울어진 변에 닿지 않게 기울기만큼 + 여유를 둡니다(탐색기 SLANT + 9)."""
    if t == "decision":
        return 0.0, w * 0.5 - 0.04
    if t in ("input", "output"):
        m = WF_SLANT / 2.0 + 0.06
        return m, w - 2 * (WF_SLANT + 0.06) - 0.04
    if t == "process":
        return 0.03, w * 0.75 - 0.1
    if t == "term":
        return 0.04, w - 2 * (0.15 * h + 0.04) - 0.04
    return 0.07, w - 0.18


def _wf_fz(size, sc):
    """판을 줄였을 때의 글자 크기 — 0.5pt 단위, 7pt 아래로는 줄이지 않습니다."""
    return size if sc >= 1.0 else max(7.0, round(size * sc * 2) / 2.0)


def _wf_link_text(n):
    # ↩ 뒤에 글자 표시 선택자(U+FE0E)를 붙입니다 — 없으면 PowerPoint가 색 그림 글자(이모지)로 바꿔 찍습니다
    return "%s %s" % (n["sym"] + ("\ufe0e" if n["sym"] == "↩" else ""), n["code"])


class _Track(object):
    """통로 위의 선 한 줄 — 같은 통로 안 순서는 교차가 가장 적게 나중에 정합니다."""
    __slots__ = ("group", "c", "pos")

    def __init__(self, group, c):
        self.group, self.c, self.pos = group, c, 0.0


def _wf_layout(F, ids, entry, x0, y0, w, h, band_over=None):
    band_over = band_over or {}
    nodes, keys = F["nodes"], F["keys"]
    nl = len(keys)
    inV = set(ids)
    outs = {i: [e for e in F["edges"] if e["from"] == i] for i in ids}
    internal = {i: [e for e in outs[i] if e["to"] in inV] for i in ids}
    inc = {i: [] for i in ids}
    for i in ids:
        for e in internal[i]:
            inc[e["to"]].append(e)

    # ① 열 — 들어오는 도형을 맨 앞 열에 두고, 되돌아가는 연결을 뺀 가장 긴 경로로 왼쪽→오른쪽 (layoutView)
    roots = [entry] + [i for i in ids if i != entry and not [e for e in inc[i] if e["from"] != i]]
    state, back, post = {}, set(), []

    def dfs(i):
        state[i] = 1
        for e in internal[i]:
            t = e["to"]
            if state.get(t) == 1 or t == entry:
                back.add(e["i"])
            elif not state.get(t):
                dfs(t)
        state[i] = 2
        post.append(i)
    for r in roots + ids:
        if not state.get(r):
            dfs(r)
    rank = {}
    for i in reversed(post):
        rank.setdefault(i, 0)
        for e in internal[i]:
            if e["i"] not in back:
                rank[e["to"]] = max(rank.get(e["to"], 0), rank[i] + 1)
    ncol = max(rank.values()) + 1

    # ② 행 — 주 경로는 앞 도형의 행을 이어 곧게, 갈래는 빈 행으로. 구역이 바뀌면 앞 도형의 행 순서를 뒤집습니다
    li = {i: keys.index(nodes[i]["lane"]) for i in ids}
    slot, used, maxslot = {}, set(), [0] * nl
    byrank = {}
    for i in ids:
        byrank.setdefault(rank[i], []).append(i)

    def key(i):
        best, start = None, 0
        for e in inc[i]:
            p = e["from"]
            if e["i"] in back or p not in slot:
                continue
            same = li[p] == li[i]
            k = (slot[p] if same else -slot[p], rank[p], internal[p].index(e))
            if best is None or k[0] < best[0] or (k[0] == best[0] and (k[1] > best[1] or
                                                                     (k[1] == best[1] and k[2] < best[2]))):
                best, start = k, (slot[p] if same else 0)
        return (best or (0, 0, ids.index(i))), start
    for r in range(ncol):
        col = [(i, key(i)) for i in byrank.get(r, [])]
        col.sort(key=lambda c: (c[1][0][0], -c[1][0][1], c[1][0][2]))
        for i, (_, s) in col:
            while (li[i], s, r) in used:
                s += 1
            used.add((li[i], s, r))
            slot[i] = s
            maxslot[li[i]] = max(maxslot[li[i]], s + 1)
    nrows = [max(1, m) for m in maxslot]
    R = sum(nrows)

    def mirrored(l):
        return nl > 1 and l < nl - 1

    def vrow_of(l, s):
        off = sum(nrows[:l])
        return off + (nrows[l] - 1 - s if mirrored(l) else s)
    vr = {i: vrow_of(li[i], slot[i]) for i in ids}
    occ = {(vr[i], rank[i]): i for i in ids}
    lane_rows = [(sum(nrows[:l]), sum(nrows[:l + 1]) - 1) for l in range(nl)]

    def row_clear(v, r1, r2):
        return all((v, r) not in occ for r in range(r1, r2 + 1))

    def col_clear(r, v1, v2):
        return all((v, r) not in occ for v in range(min(v1, v2), max(v1, v2) + 1))

    def outer_band(l):
        return 0 if mirrored(l) else R
    boundary = set(lane_rows[l][0] for l in range(1, nl))

    def band_cands(c, vertex=None):
        """가로 통로 후보 — 같은 구역끼리 잇는 선은 그 구역 안 통로만(자기 구역 지키기), 꼭짓점에서 내려가면 그 방향만."""
        a, b = c["a"], c["b"]
        if li[a] == li[b]:
            f, l = lane_rows[li[a]]
            ks = [k for k in range(f, l + 2) if not (k == l + 1 and k in boundary and mirrored(li[a]))]
        else:
            ks = list(range(R + 1))
        if vertex == "d":
            ks = [k for k in ks if k > vr[a] and all((v, rank[a]) not in occ for v in range(vr[a] + 1, k))]
        elif vertex == "u":
            ks = [k for k in ks if k <= vr[a] and all((v, rank[a]) not in occ for v in range(k, vr[a]))]
        return ks

    def pick(c, default, vertex=None):
        c["bands"] = band_cands(c, vertex)
        k = band_over.get(c["e"]["i"], default)
        return k if k in c["bands"] or not c["bands"] else default

    # ③ 연결 — 앞으로 · 가까운 복귀(통로) · 이동 연결자(먼 복귀 「↩」 · 섹션 밖 「→」 · 다른 기능 「→ F-…」)
    C, links = [], {}
    for i in ids:
        for e in outs[i]:
            t = e["to"]
            c = {"e": e, "a": i, "kind": e["kind"], "label": e["label"]}
            sym = None
            if e["feature"]:
                sym, code = "→", t
            elif t not in inV:
                sym, code = "→", nodes[t]["code"]
            elif e["i"] in back and (t == i or rank[i] - rank[t] >= FAR_BACK):
                sym, code = "↩", nodes[t]["code"]
            elif e["i"] in back:
                c.update(cls="back", b=t)
            else:
                c.update(cls="fwd", b=t)
            if sym:
                lid = "link:%d" % e["i"]
                links[lid] = {"id": lid, "type": "link", "sym": sym, "code": code, "lane": nodes[i]["lane"],
                              "feature": t if e["feature"] else None, "h": WF_LINK_H,
                              # 섹션 밖 「→ 코드」는 그 도형이 그려진 장으로 링크합니다(빌드가 쪽을 채움)
                              "node": t if (sym == "→" and not e["feature"] and t not in inV) else None}
                links[lid]["w"] = max(WF_LINK_W, _wf_text_w(_wf_link_text(links[lid]), 9) + 0.26)
                c.update(cls="link", b=lid)
            C.append(c)
    N = dict((i, dict(nodes[i])) for i in ids)
    N.update(links)

    # ④ 나가는 자리 — 조건은 오른쪽 · 아래 · 위 꼭짓점(같은 행 가장 가까운 도착이 오른쪽), 그 밖은 오른쪽 면
    bysrc = {}
    for c in C:
        bysrc.setdefault(c["a"], []).append(c)
    for a, cs in bysrc.items():
        dec = N[a]["type"] == "decision"
        outer = "u" if mirrored(li[a]) else "d"
        lk = [c for c in cs if c["cls"] == "link"]
        if dec:
            free = {"r": True, "d": True, "u": True}
            fw = [c for c in cs if c["cls"] == "fwd"]
            same = [c for c in fw if vr[c["b"]] == vr[a]]
            if same:
                c0 = min(same, key=lambda c: rank[c["b"]])
                c0["exit"], free["r"] = "r", False
            for c in fw:
                if "exit" in c:
                    continue
                dv = vr[c["b"]] - vr[a]
                want = "u" if dv < 0 else ("d" if dv > 0 else outer)
                for s in (want, "r", "d" if want == "u" else "u"):
                    if free[s]:
                        c["exit"], free[s] = s, False
                        break
                else:
                    c["exit"] = "r"
            for c in [c for c in cs if c["cls"] == "back"]:
                clear = col_clear(rank[a], vr[a] + (1 if outer == "d" else -1),
                                  R - 1 if outer == "d" else 0) if (0 <= vr[a] + (1 if outer == "d" else -1) < R) \
                    else True
                if free[outer] and clear:
                    c["exit"], free[outer] = outer, False
                else:
                    c["exit"] = "r"
                    free["r"] = False
            inner_ = "d" if outer == "u" else "u"
            for c in lk:
                if free["r"]:
                    c["exit"], c["attach"], free["r"] = "r", "r", False
                elif free[outer]:
                    c["exit"], c["attach"], free[outer] = outer, outer, False
                elif free[inner_]:
                    c["exit"], c["attach"], free[inner_] = inner_, inner_, False
                else:
                    c["exit"], c["attach"] = "r", "rs"
        else:
            sides = [outer, "d" if outer == "u" else "u"]
            for c in cs:
                if c["cls"] != "link":
                    c["exit"] = "r"
            for c in lk:
                if len(cs) == 1:
                    c["exit"], c["attach"] = "r", "r"
                elif sides:
                    sd = sides.pop(0)
                    c["exit"], c["attach"] = sd, sd
                else:
                    c["exit"], c["attach"] = "r", "rs"
    rcount, lcount, rlab, llab = {}, {}, {}, {}
    for c in C:
        if c["exit"] == "r":
            rcount[c["a"]] = rcount.get(c["a"], 0) + 1
            rlab[c["a"]] = rlab.get(c["a"], False) or bool(c["label"])
        if c["cls"] != "link":
            lcount[c["b"]] = lcount.get(c["b"], 0) + 1

    # ⑤ 경로 모양 — 통로(열 사이 세로 · 행 사이 가로)를 어느 것을 쓰는지만 먼저 정합니다
    for c in C:
        a, b, ex = c["a"], c["b"], c["exit"]
        if c["cls"] == "link":
            c["plan"] = {"t": "link"}
            continue
        ra, rb, va, vb = rank[a], rank[b], vr[a], vr[b]
        if c["cls"] == "back":
            band = outer_band(li[a]) if (li[a] == li[b] and mirrored(li[a])) else R
            band = pick(c, band, None if ex == "r" else ex)
            c["plan"] = {"t": "zz", "g1": ra, "band": band, "g2": rb - 1} if ex == "r" else \
                {"t": "vband", "band": band, "g2": rb - 1}
            continue
        if ex == "r":
            straight_ok = (N[a]["type"] != "decision" and rcount.get(a) == 1) or lcount.get(b) == 1
            mid_a, mid_b = row_clear(va, ra + 1, rb - 1), row_clear(vb, ra + 1, rb - 1)
            if va == vb and mid_a and straight_ok:
                c["plan"] = {"t": "straight"}
            elif rb == ra + 1:
                c["plan"] = {"t": "z", "g": ra}
            elif mid_a:
                c["plan"] = {"t": "z", "g": rb - 1}
            elif mid_b:
                c["plan"] = {"t": "z", "g": ra}
            else:
                band = va + 1 if vb > va else (va if vb < va else (va if mirrored(li[a]) else va + 1))
                band = pick(c, band)
                c["plan"] = {"t": "zz", "g1": ra, "band": band, "g2": rb - 1}
            continue
        down = ex == "d"
        ok = (vb > va if down else vb < va) and col_clear(ra, va + (1 if down else -1), vb) and \
            row_clear(vb, ra + 1, rb - 1)
        c["plan"] = {"t": "L"} if ok else {"t": "vband", "band": pick(c, va + 1 if down else va, ex), "g2": rb - 1}

    # ⑥ 열 사이 폭 — 곧은 선만 지나면 좁게, 통로가 필요하면 선 수만큼, 라벨 · 붙는 연결자 폭은 따로 더합니다
    gaps = dict((g, {"zone": 0.12, "tr": [], "att": 0.0}) for g in range(-1, ncol))
    for c in C:
        p = c["plan"]
        for k in ("g", "g1", "g2"):
            if k in p:
                t = _Track(("g", p[k]), c)
                gaps[p[k]]["tr"].append(t)
                c.setdefault("tracks", {})[k] = t
        if "band" in p:
            t = _Track(("b", p["band"]), c)
            c.setdefault("tracks", {})["band"] = t
        if c["label"] and c["exit"] == "r":
            gaps[rank[c["a"]]]["zone"] = max(gaps[rank[c["a"]]]["zone"], _wf_label_w(c["label"]) + 0.18)
        if c["cls"] == "link" and c["attach"] in ("r", "rs"):
            stub = (_wf_label_w(c["label"]) + 0.2) if c["label"] else 0.3
            c["stub"] = stub
            g = gaps[rank[c["a"]]]
            lw_ = links[c["b"]]["w"]
            g["att"] += (stub + lw_) if not g["att"] else (lw_ + 0.12)
        elif c["cls"] == "link":
            c["stub"] = (WF_LABEL_H + 0.26) if c["label"] else 0.22
    for g in gaps.values():
        g["zone"] = max(g["zone"], g["att"] + 0.12 if g["att"] else 0)

    def gap_need(g):
        d, n = gaps[g], len(gaps[g]["tr"])
        if g == -1:
            return 0.14 + (n - 1) * WF_TRACK + WF_TAIL if n else 0.2
        if g == ncol - 1:
            return d["zone"] + n * WF_TRACK + 0.04 if (n or d["att"]) else 0.15
        if n:
            return d["zone"] + (n - 1) * WF_TRACK + WF_TAIL + 0.04
        return max(WF_NARROW, d["zone"] + 0.12)
    gw = dict((g, gap_need(g)) for g in gaps)
    avail = w - WF_LANE_COL - sum(gw.values())
    W = min(WF_W_MAX, avail / ncol)
    overflow = ncol > WF_MAX_COLS or W < WF_W_MIN
    W = max(0.6, W)                                       # 통로 폭은 줄이지 않습니다 — 줄이면 선이 도형 안으로 들어갑니다
    left = avail - W * ncol
    if left > 0 and ncol > 1:                             # 남는 폭은 열 사이에 나눠 숨통을 줍니다(열 간격 330 쪽으로)
        add = min(left / (ncol - 1), max(0.0, 0.55 * W - min(gw[g] for g in range(ncol - 1))))
        for g in range(ncol - 1):
            gw[g] += add
        left -= add * (ncol - 1)
    xoff = max(0.0, left) / 2.0

    # ⑦ 도형 크기 — 글자가 잘리면 높이를 늘리고(fitSize), 선이 여럿 드나드는 도형은 점 사이가 벌어지게 늘립니다
    H = max(0.5, min(0.62, 0.36 * W))
    fs = 10 if W >= 1.3 else 9
    for i in ids:
        n = N[i]
        if n["type"] == "ref":
            n["w"] = n["h"] = 0.62
            continue
        pad, tw = _wf_pad(n["type"], W, H)
        th = est_lines(n["text"], tw * 0.9, fs) * line_height(fs) + line_height(9) + 0.06
        k = max(rcount.get(i, 0) if n["type"] != "decision" else 1, lcount.get(i, 0))
        step = 0.2 if (rlab.get(i) or any(c["label"] for c in C if c.get("b") == i)) else 0.15
        spread = 0.2 + (k - 1) * step if k > 1 else 0
        if n["type"] == "decision":
            n["h"] = max(H * 1.39, th * 2.0 + 0.08, spread * 2)
        else:
            n["h"] = max(H, th + (0.16 if n["type"] in ("input", "output") else 0.06), spread)  # 평행사변형은 글 영역 위아래도 안쪽
        n["w"], n["fs"], n["pad"] = W, fs, pad
    rh = [H] * R
    for i in ids:
        rh[vr[i]] = max(rh[vr[i]], N[i]["h"])

    # ⑧ 세로 — 행 사이 통로(band)마다 선 줄 수 · 붙는 연결자 자리만큼 높이를 잡습니다. 유저 구역은 경계에서 위로
    bands = [{"tr": [], "zt": 0.0, "zb": 0.0} for _ in range(R + 1)]
    for c in C:
        t = (c.get("tracks") or {}).get("band")
        if t:
            bands[c["plan"]["band"]]["tr"].append(t)
        if c["plan"]["t"] == "vband" and c["label"]:
            k = c["plan"]["band"]
            if c["exit"] == "d":
                bands[k]["zt"] = max(bands[k]["zt"], WF_LABEL_H + 0.1)
            else:
                bands[k]["zb"] = max(bands[k]["zb"], WF_LABEL_H + 0.1)
        if c["cls"] == "link" and c["attach"] != "r":
            a = c["a"]
            up = c["attach"] == "u" or (c["attach"] == "rs" and mirrored(li[a]))
            # 위 · 아래 연결자는 행 사이 통로의 도형 쪽 자리(zone)에 둡니다 — 통로의 선 줄은 그 바깥으로 비켜 갑니다
            k = vr[a] if up else vr[a] + 1
            need = (c["stub"] if c["attach"] in "ud" else 0.08) + WF_LINK_H + 0.08
            if up:
                bands[k]["zb"] = max(bands[k]["zb"], need)
            else:
                bands[k]["zt"] = max(bands[k]["zt"], need)
    def band_h(k, rg, pad):
        b, n = bands[k], len(bands[k]["tr"])
        tr = (0.2 + (n - 1) * WF_TRACK) if n else 0.0
        if k in boundary:                                 # 구역 경계 — 위 절반은 유저 쪽 자리, 선 줄은 아래(시스템) 절반
            b["half"] = max(pad, b["zt"] + 0.04)
            return b["half"] + max(pad, b["zb"] + tr + (0.08 if n else 0))
        base = pad if k in (0, R) else rg
        return max(base, b["zt"] + b["zb"] + tr)
    rg, pad = WF_RG, WF_PAD
    total = sum(rh) + sum(band_h(k, rg, pad) for k in range(R + 1))
    if total > h:                                         # 넘치면 통로 · 여백부터 줄입니다
        rg, pad = 0.26, 0.1
        total = sum(rh) + sum(band_h(k, rg, pad) for k in range(R + 1))
        if total > h:
            overflow = True
    else:
        inner = [k for k in range(1, R) if k not in boundary]
        if inner:
            rg = min(0.55, WF_RG + (h - total) / len(inner))
        total = sum(rh) + sum(band_h(k, rg, pad) for k in range(R + 1))
    y = y0 + max(0.0, h - total) * 0.3
    bt, row_cy, border = [], [], {}
    for k in range(R + 1):
        bt.append(y)
        hh = band_h(k, rg, pad)
        if k in boundary:
            border[k] = y + bands[k]["half"]
        y += hh
        bands[k]["top"], bands[k]["bot"] = bt[k], y
        if k < R:
            row_cy.append(y + rh[k] / 2.0)
            y += rh[k]
    lane_y = []
    for l in range(nl):
        f, last = lane_rows[l]
        top = bt[0] if l == 0 else border[f]
        bot = bands[R]["bot"] if l == nl - 1 else border[last + 1]
        lane_y.append((top, bot))

    # ⑨ 가로 좌표
    gx = {-1: x0 + WF_LANE_COL + xoff}
    colL = {}
    x = gx[-1] + gw[-1]
    for r in range(ncol):
        colL[r] = x
        x += W
        gx[r] = x
        x += gw[r]
    for i in ids:
        N[i]["cx"], N[i]["cy"] = colL[rank[i]] + W / 2.0, row_cy[vr[i]]
        N[i]["rank"], N[i]["vr"], N[i]["li"] = rank[i], vr[i], li[i]

    # ⑩ 이동 연결자 자리 — 오른쪽(나가는 선이 그것뿐) · 바깥쪽 위아래(유저는 위 · 시스템은 아래) · 오른쪽 아래(위)
    rs_count = {}
    for c in C:
        if c["cls"] != "link":
            continue
        a, L = N[c["a"]], N[c["b"]]
        att = c["attach"]
        if att == "r":
            L["cx"], L["cy"] = a["cx"] + a["w"] / 2.0 + c["stub"] + L["w"] / 2.0, a["cy"]
        elif att == "d":
            L["cx"], L["cy"] = a["cx"], a["cy"] + a["h"] / 2.0 + c["stub"] + WF_LINK_H / 2.0
        elif att == "u":
            L["cx"], L["cy"] = a["cx"], a["cy"] - a["h"] / 2.0 - c["stub"] - WF_LINK_H / 2.0
        else:
            k = rs_count.get(c["a"], 0)
            rs_count[c["a"]] = k + 1
            up = mirrored(li[c["a"]])
            L["cx"] = a["cx"] + W / 2.0 + c["stub"] + L["w"] / 2.0 + k * (L["w"] + 0.12)
            edge = row_cy[vr[c["a"]]] + (-1 if up else 1) * rh[vr[c["a"]]] / 2.0
            L["cy"] = edge + (-1 if up else 1) * (0.08 + WF_LINK_H / 2.0)
            L["up"] = up

    # ⑪ 점 — 나가는 선은 향하는 높이 순, 들어오는 선은 다가오는 높이 순으로 면을 나눕니다
    def band_mid(k):
        return (bands[k]["top"] + bands[k]["bot"]) / 2.0

    def toward(c):
        p, b = c["plan"], N[c["b"]]
        if p["t"] in ("zz", "vband"):
            return band_mid(p["band"])
        if p["t"] == "link":
            if c["attach"] == "rs":
                return b["cy"] + (-50 if b.get("up") else 50)
            return b["cy"]
        return b["cy"]

    def approach(c):
        p, a = c["plan"], N[c["a"]]
        if p["t"] in ("zz", "vband"):
            return band_mid(p["band"])
        return a["cy"]

    def spread(n, k, j, labeled):
        if k == 1:
            return 0.0
        step = min(0.2 if labeled else 0.15, (n["h"] * (0.5 if n["type"] == "decision" else 1) - 0.12) / (k - 1))
        return (j - (k - 1) / 2.0) * step

    def side_x(n, side, dy):
        hw = n["w"] / 2.0
        if n["type"] == "decision":
            hw *= max(0.0, 1 - abs(dy) / (n["h"] / 2.0))
        if n["type"] in ("input", "output"):
            t = max(0.0, min(1.0, (dy + n["h"] / 2.0) / n["h"]))
            return n["cx"] + hw - WF_SLANT * t if side == "r" else n["cx"] - hw + WF_SLANT * (1 - t)
        if n["type"] == "ref":
            r = n["w"] / 2.0
            hw = (max(0.0, r * r - dy * dy)) ** 0.5
        return n["cx"] + hw if side == "r" else n["cx"] - hw
    for a in set(c["a"] for c in C):
        n = N[a]
        rs = sorted([c for c in C if c["a"] == a and c["exit"] == "r"], key=lambda c: (toward(c), rank.get(c["b"], 99)))
        lab = any(c["label"] for c in rs)
        for j, c in enumerate(rs):
            dy = 0.0 if n["type"] == "decision" and len(rs) == 1 else spread(n, len(rs), j, lab)
            c["P"] = (side_x(n, "r", dy), n["cy"] + dy)
        for c in C:
            if c["a"] == a and c["exit"] in ("u", "d"):
                c["P"] = (n["cx"], n["cy"] + (n["h"] / 2.0 if c["exit"] == "d" else -n["h"] / 2.0))
    for b in ids:
        n = N[b]
        ins = sorted([c for c in C if c.get("b") == b and c["cls"] != "link"], key=lambda c: (approach(c), -rank[c["a"]]))
        lab = any(c["label"] for c in ins)
        for j, c in enumerate(ins):
            dy = spread(n, len(ins), j, lab)
            c["Q"] = (side_x(n, "l", dy), n["cy"] + dy)
    for c in C:
        if c["cls"] != "link":
            continue
        L, att = N[c["b"]], c["attach"]
        if att == "r":
            c["P"] = (c["P"][0], L["cy"]) if N[c["a"]]["type"] == "decision" else c["P"]
            L["cy"] = c["P"][1]
            c["Q"] = (L["cx"] - L["w"] / 2.0, L["cy"])
        elif att == "d":
            c["Q"] = (L["cx"], L["cy"] - WF_LINK_H / 2.0)
        elif att == "u":
            c["Q"] = (L["cx"], L["cy"] + WF_LINK_H / 2.0)
        else:
            c["Q"] = (L["cx"], L["cy"] + (WF_LINK_H / 2.0 if L.get("up") else -WF_LINK_H / 2.0))
    # 곧은 선 — 한쪽 끝만 여럿이면 다른 쪽 끝을 그 높이로 맞춥니다
    for c in C:
        if c["plan"]["t"] != "straight":
            continue
        a, b = N[c["a"]], N[c["b"]]
        if a["type"] != "decision" and rcount.get(c["a"]) == 1 and abs(c["Q"][1] - a["cy"]) < a["h"] / 2.0 - 0.06:
            c["P"] = (side_x(a, "r", c["Q"][1] - a["cy"]), c["Q"][1])
        elif lcount.get(c["b"]) == 1:
            c["Q"] = (side_x(b, "l", c["P"][1] - b["cy"]), c["P"][1])

    # ⑫ 통로 위치 — 같은 통로 안 순서는 교차가 가장 적은 순서
    groups = {}
    for c in C:
        for t in (c.get("tracks") or {}).values():
            groups.setdefault(t.group, []).append(t)

    def gap_span(g):
        lo = gx[g] + (0.14 if g == -1 else gaps[g]["zone"])
        hi = colL[g + 1] - WF_TAIL if g + 1 < ncol else gx[g] + gw[g]
        return lo, hi

    def band_span(k):
        b = bands[k]
        lo = (border[k] + 0.12) if k in boundary else b["top"] + b["zt"] + 0.1
        hi = b["bot"] - b["zb"] - 0.1
        return lo, hi

    def place(group, order):
        lo, hi = gap_span(group[1]) if group[0] == "g" else band_span(group[1])
        n = len(order)
        span = (n - 1) * WF_TRACK
        if group[0] == "g" and group[1] == ncol - 1:
            s = lo
        elif group[0] == "b" and group[1] == R:
            s = lo                                        # 맨 아래 통로는 도형 쪽부터
        elif group[0] == "b" and group[1] == 0:
            s = hi - span
        else:
            s = lo + max(0.0, (hi - lo - span) / 2.0)
        for k, t in enumerate(order):
            t.pos = s + k * WF_TRACK

    def pts_of(c):
        p, P, Q = c["plan"], c["P"], c["Q"]
        T = c.get("tracks") or {}
        a = N[c["a"]]
        if p["t"] == "straight" or (p["t"] == "link" and c["attach"] in ("r", "d", "u")):
            return [P, Q]
        if p["t"] == "link":
            return [P, (Q[0], P[1]), Q]
        if p["t"] == "z":
            x = T["g"].pos
            return [P, (x, P[1]), (x, Q[1]), Q]
        if p["t"] == "L":
            return [P, (a["cx"], Q[1]), Q]
        if p["t"] == "zz":
            x1, yb, x2 = T["g1"].pos, T["band"].pos, T["g2"].pos
            return [P, (x1, P[1]), (x1, yb), (x2, yb), (x2, Q[1]), Q]
        yb, x2 = T["band"].pos, T["g2"].pos
        return [P, (P[0], yb), (x2, yb), (x2, Q[1]), Q]
    boxes = [(N[i]["cx"] - N[i]["w"] / 2.0, N[i]["cy"] - N[i]["h"] / 2.0, N[i]["cx"] + N[i]["w"] / 2.0,
              N[i]["cy"] + N[i]["h"] / 2.0, i) for i in N]

    def segs(c):
        p = c["pts"]
        return [(p[k], p[k + 1]) for k in range(len(p) - 1)]

    def cost():
        S = []
        for c in C:
            c["pts"] = pts_of(c)
            for s in segs(c):
                S.append((c, s))
        bad = 0
        for k, (c1, (a1, b1)) in enumerate(S):
            h1 = abs(a1[1] - b1[1]) < 1e-6
            for b in boxes:                               # 선이 도형을 지나면 큰 감점
                if b[4] in (c1["a"], c1["b"]):
                    continue
                if h1 and b[1] - 0.03 < a1[1] < b[3] + 0.03 and min(a1[0], b1[0]) < b[2] and max(a1[0], b1[0]) > b[0]:
                    bad += 100
                if not h1 and b[0] - 0.03 < a1[0] < b[2] + 0.03 and min(a1[1], b1[1]) < b[3] and max(a1[1], b1[1]) > b[1]:
                    bad += 100
            for c2, (a2, b2) in S[k + 1:]:
                if c2 is c1:
                    continue
                h2 = abs(a2[1] - b2[1]) < 1e-6
                if h1 != h2:
                    hs, vs = ((a1, b1), (a2, b2)) if h1 else ((a2, b2), (a1, b1))
                    xv, yh = vs[0][0], hs[0][1]
                    if min(hs[0][0], hs[1][0]) + 0.01 < xv < max(hs[0][0], hs[1][0]) - 0.01 and \
                            min(vs[0][1], vs[1][1]) + 0.01 < yh < max(vs[0][1], vs[1][1]) - 0.01:
                        bad += 1
                else:
                    ax = 1 if h1 else 0
                    o = 0 if h1 else 1
                    if abs(a1[ax] - a2[ax]) < WF_TRACK * 0.6 and \
                            min(max(a1[o], b1[o]), max(a2[o], b2[o])) - max(min(a1[o], b1[o]), min(a2[o], b2[o])) > 0.01:
                        bad += 30                         # 나란한 두 선이 겹침
        return bad
    for g, ts in groups.items():
        ts.sort(key=lambda t: t.c["P"][1])
        place(g, ts)
    best = cost()
    for _ in range(2):
        for g, ts in groups.items():
            if len(ts) < 2:
                continue
            cands = list(_perms(ts)) if len(ts) <= 4 else [ts, ts[::-1]]
            for order in cands:
                place(g, list(order))
                cst = cost()
                if cst < best:
                    best, groups[g] = cst, list(order)
            place(g, groups[g])
    cost()
    return {"N": N, "C": C, "ids": ids, "ncol": ncol, "R": R, "W": W, "overflow": overflow, "lane_y": lane_y,
            "rank": rank, "bad": best, "boxes": boxes, "bands": bands, "height": total}


def _wf_shape(slide, n):
    """탐색기 shape() · label() — 코드(굵게) 첫 줄 + 문구. 이동 연결자는 「↩ 코드」 · 「→ 코드」 한 줄."""
    t = n["type"]
    x, y, w, h = n["cx"] - n["w"] / 2.0, n["cy"] - n["h"] / 2.0, n["w"], n["h"]
    if t == "link":
        shp = box(slide, x, y, w, h, fill=WF_JUMP_FILL, line=WF_JUMP, width=1.25, dash=True, shape="offpage",
                  name="flow-link")
        tf = shp.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = 0
        tf.margin_bottom = Inches(h * 0.18)
        tf.word_wrap = False
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = _wf_link_text(n)
        _font(r, _wf_fz(9, n["sc"]), True, WF_JUMP_TEXT)
        return shp, r
    fill = WF_DECISION_FILL if t == "decision" else (TINT if t == "ref" else WHITE)
    shp = box(slide, x, y, w, h, fill=fill, line=WF_EDGE, width=1.0, shape=FLOW_SHAPES[t], name="flow-%s" % t)
    if t == "action":
        shp.adjustments[0] = min(0.5, 0.05 / max(0.01, min(w, h)))      # 탐색기 rx 4 — 작은 반경
    elif t in ("input", "output"):
        shp.adjustments[0] = WF_SLANT * n["sc"] / max(0.01, min(w, h))
    tf = shp.text_frame
    tf.word_wrap = True
    tf.margin_top = tf.margin_bottom = 0
    if t == "ref":
        tf.margin_left = tf.margin_right = 0
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = n.get("target_code") or n["text"]
        _font(r, _wf_fz(9, n["sc"]), True, INK)
        tf.word_wrap = False
        return shp, None
    tf.margin_left = tf.margin_right = Inches(n["pad"])
    if t == "decision":
        tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.line_spacing = LINE_SPACING
    r = p.add_run()
    r.text = n["code"]
    _font(r, _wf_fz(9, n["sc"]), True, SUB)
    if n["text"]:
        p2 = tf.add_paragraph()
        p2.alignment = PP_ALIGN.CENTER
        p2.line_spacing = LINE_SPACING
        r2 = p2.add_run()
        r2.text = n["text"]
        _font(r2, _wf_fz(n["fs"], n["sc"]), False, INK)
    return shp, None


def _wf_site(n, pt):
    """점이 도형 연결점(위 0 · 왼쪽 1 · 아래 2 · 오른쪽 3)의 한가운데면 그 번호, 아니면 None(앵커로 붙임)."""
    if n["type"] in ("input", "output", "ref"):
        return None
    l, r = n["cx"] - n["w"] / 2.0, n["cx"] + n["w"] / 2.0
    t, b = n["cy"] - n["h"] / 2.0, n["cy"] + n["h"] / 2.0
    for idx, (sx, sy) in enumerate(((n["cx"], t), (l, n["cy"]), (n["cx"], b), (r, n["cy"]))):
        if abs(pt[0] - sx) < 0.005 and abs(pt[1] - sy) < 0.005:
            return idx
    return None


def _wf_overlap(a, b, m=0.0):
    return a[0] < b[2] + m and a[2] > b[0] - m and a[1] < b[3] + m and a[3] > b[1] - m


def _wf_seg_hits(rect, segs, m=0.03):
    for (p, q) in segs:
        if rect[0] - m < max(p[0], q[0]) and rect[2] + m > min(p[0], q[0]) and \
                rect[1] - m < max(p[1], q[1]) and rect[3] + m > min(p[1], q[1]):
            return True
    return False


def workflow_chart(slide, flow, section=None, feature_id=None, x0=MX, y0=TOP, w=SW - 2 * MX, h=None,
                   show_legend=True):
    """기능 흐름도 한 장 — 섹션 하나(section: 키 또는 flow_sections()의 항목) 또는 흐름 전체(None).

    위 유저 구역 · 아래 시스템 구역을 가로 띠로 두고, 탐색기 배치 규칙대로 도형을 놓고 선마다 연결선 도형
    하나로 잇습니다. 섹션 밖 · 다른 기능으로 가는 연결과 두 열 이상 되돌아가는 연결은 출발 도형 곁의
    이동 연결자(「→ 코드」 · 「↩ 코드」)입니다.
    돌려주는 값: {"cols", "rows", "overflow", "refs"} — refs는 덱 조립이 쪽 링크를 걸 글 조각
    ({"run", "screen"} 화면 쪽 표시 「p. ?」 · {"run", "feature"} 다른 기능 연결자 글)입니다.
    """
    F = _wf_norm(flow)
    if not F["order"]:
        return {"cols": 0, "rows": 0, "overflow": False, "refs": []}
    if section is None:
        ids, entry = list(F["order"]), F["start"]
    else:
        sec = section if isinstance(section, dict) else next(
            (s for s in flow_sections(flow) if s["key"] == section), None)
        if sec is None:
            raise ValueError("흐름도: 섹션 %r이 없습니다" % (section,))
        ids, entry = list(sec["ids"]), sec.get("entry") or sec["ids"][0]
    checks = [i for i in ids if F["nodes"][i]["type"] == "decision" and check_text(F["nodes"][i].get("check"))]
    h = (h or (BOTTOM - y0 - 0.45)) - 0.22 * len(checks)     # 판정 각주 자리
    # 열이 많아 도형 폭이 WF_W_MIN보다 좁아지면, 그 폭이 되는 넓은 판에 배치한 뒤 판째로 줄여 본문에 맞춥니다
    # (통로 · 글 크기가 함께 줄어 어긋나지 않습니다). 이때는 overflow로 알려 덱 조립이 경고합니다
    sc = 1.0
    vw, vh = w, h
    L = _wf_layout(F, ids, entry, x0, y0, vw, vh)
    if L["W"] < WF_W_MIN:
        vw = w + (WF_W_MIN - L["W"]) * L["ncol"]
        sc = w / vw
        vh = h / sc
        L = _wf_layout(F, ids, entry, x0, y0, vw, vh)
    over = {}
    for _ in range(2):                                    # 가로 통로 후보를 하나씩 바꿔 보고 나아질 때만 씁니다
        changed = False
        for ei, cur, ks in [(c["e"]["i"], c["plan"].get("band"), c.get("bands") or []) for c in L["C"]]:
            for k in ks:
                if k == cur or L["bad"] == 0:
                    continue
                trial = dict(over)
                trial[ei] = k
                L2 = _wf_layout(F, ids, entry, x0, y0, vw, vh, trial)
                if L2["bad"] < L["bad"]:
                    L, over, cur, changed = L2, trial, k, True
        if not changed:
            break
    N, C = L["N"], L["C"]
    if sc < 1.0:
        def tr(pt):
            return (x0 + (pt[0] - x0) * sc, y0 + (pt[1] - y0) * sc)
        for n in N.values():
            n["cx"], n["cy"] = tr((n["cx"], n["cy"]))
            n["w"], n["h"] = n["w"] * sc, n["h"] * sc
            if "pad" in n:
                n["pad"] *= sc
        for c in C:
            c["pts"] = [tr(pt) for pt in c["pts"]]
        L["lane_y"] = [(tr((0, t))[1], tr((0, b))[1]) for t, b in L["lane_y"]]
        L["boxes"] = [(n["cx"] - n["w"] / 2.0, n["cy"] - n["h"] / 2.0, n["cx"] + n["w"] / 2.0, n["cy"] + n["h"] / 2.0, i)
                      for i, n in N.items()]
    for n in N.values():
        n["sc"] = sc
    user_key = F["keys"][0]
    refs = []

    # 구역 띠 — 옅은 구역색 바탕, 왼쪽 이름 칸에 구역색 세로 띠와 글자
    for l, lane in enumerate(F["lanes"]):
        top, bot = L["lane_y"][l]
        col, fill, edge = WF_LANE_USER if lane["key"] == user_key else WF_LANE_SYSTEM
        box(slide, x0, top, w, bot - top, fill=fill, line=edge, width=0.75, name="flow-lane")
        box(slide, x0, top, 0.07, bot - top, fill=col, name="flow-lane-bar")
        line(slide, x0 + WF_LANE_COL * sc, top, x0 + WF_LANE_COL * sc, bot, color=edge, width=0.75)
        text(slide, x0 + 0.1, top, WF_LANE_COL * sc - 0.12, bot - top, v(lane.get("label")), size=_wf_fz(10, sc), bold=True,
             color=col, anchor="m")
    # 도형
    shapes = {}
    for i in N:
        n = N[i]
        if n["type"] == "ref":
            t = F["nodes"].get(str(n.get("target")))
            n["target_code"] = t["code"] if t else None
        shp, run = _wf_shape(slide, n)
        shapes[i] = shp
        if run is not None and n.get("feature"):
            refs.append({"run": run, "feature": n["feature"]})
        elif run is not None and n.get("node"):
            refs.append({"run": run, "node": n["node"]})
    # 선 — 선마다 연결선 도형 하나, 끝은 연결점이면 도형에, 아니면 보이지 않는 앵커에 붙입니다
    segs = []
    for c in C:
        a, b = N[c["a"]], N[c["b"]]
        p = c["pts"]
        sa, sb = _wf_site(a, p[0]), _wf_site(b, p[-1])
        path_connector(slide, p, color=WF_COLORS[c["kind"]], width=WF_WIDTH, arrow=True,
                       start=(shapes[c["a"]], sa) if sa is not None else None,
                       end=(shapes[c["b"]], sb) if sb is not None else None)
        segs += [(p[k], p[k + 1]) for k in range(len(p) - 1)]
    taken = [(b[0], b[1], b[2], b[3]) for b in L["boxes"]]
    borders = []
    for top, bot in L["lane_y"]:
        borders += [((x0, top), (x0 + w, top)), ((x0, bot), (x0 + w, bot))]
    # 선 라벨 — 선이 시작되는 쪽 첫 선분 위에 얹은 상자(선 색 테두리 · 흰 바탕)
    for c in C:
        if not c["label"]:
            continue
        p0, p1 = c["pts"][0], c["pts"][1]
        lw, lh = _wf_label_w(c["label"]) * sc, WF_LABEL_H * sc
        if abs(p0[1] - p1[1]) < 1e-6:
            sgn = 1 if p1[0] > p0[0] else -1
            cx, cy = p0[0] + sgn * (0.06 + lw / 2.0), p0[1]
        else:
            sgn = 1 if p1[1] > p0[1] else -1
            cx, cy = p0[0], p0[1] + sgn * (0.05 + lh / 2.0)
        col = WF_COLORS[c["kind"]]
        lb = box(slide, cx - lw / 2.0, cy - lh / 2.0, lw, lh, fill=WHITE, line=col, width=0.75, label=c["label"],
                 size=_wf_fz(WF_LABEL, sc), color=col, bold=True, name="flow-edge-label")
        tf = lb.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.word_wrap = False
        taken.append((cx - lw / 2.0, cy - lh / 2.0, cx + lw / 2.0, cy + lh / 2.0))

    def free_spot(cands, ww, hh):
        for (x, y) in cands:
            r = (x, y, x + ww, y + hh)
            if r[0] < x0 + WF_LANE_COL * sc or r[2] > x0 + w or r[1] < y0 - 0.05 or r[3] > y0 + h + 0.3:
                continue
            if any(_wf_overlap(r, t, 0.02) for t in taken) or _wf_seg_hits(r, segs + borders, 0.02):
                continue
            return r
        return None
    # 화면 쪽 표시 「p. ?」 — 도형 오른쪽 아래(안 되면 왼쪽 아래 · 오른쪽 위 · 왼쪽 위) 빈자리
    for i in ids:
        scr = F["nodes"][i].get("screen")
        if not scr:
            continue
        n = N[i]
        pw, ph = 0.42, 0.2
        l, r = n["cx"] - n["w"] / 2.0, n["cx"] + n["w"] / 2.0
        t, b = n["cy"] - n["h"] / 2.0, n["cy"] + n["h"] / 2.0
        spot = free_spot([(r - pw, b + 0.02), (l, b + 0.02), (r - pw, t - ph - 0.02), (l, t - ph - 0.02),
                          (r + 0.03, b - ph + 0.06), (r - pw - 0.25, b + 0.02), (l + 0.25, b + 0.02)], pw, ph)
        if spot is None:
            spot = (r - pw, b + 0.02, r, b + 0.02 + ph)
        tb = text(slide, spot[0], spot[1], pw, ph, "p. ?", size=8, color=SUB, align="c", name="flow-screen-page")
        tb.text_frame.margin_top = tb.text_frame.margin_bottom = 0
        taken.append(spot)
        refs.append({"run": tb.text_frame.paragraphs[0].runs[0], "screen": str(scr)})
    # 판정 기준 — 조건 도형 위 · 아래 빈자리에 작게, 자리가 없으면 ※ 표식 + 아래 각주
    notes = []
    for i in checks:
        n = N[i]
        s = check_text(F["nodes"][i].get("check"))
        cw = min(2.6, max(1.2, L["W"] + 0.5))
        lines = est_lines(s, cw - 0.08, 8)
        ch = lines * line_height(8) + 0.06
        if lines > 2:
            spot = None
        else:
            t, b = n["cy"] - n["h"] / 2.0, n["cy"] + n["h"] / 2.0
            xs = [n["cx"] - cw / 2.0, n["cx"] - cw - 0.05, n["cx"] + 0.05]
            spot = free_spot([(x, t - ch - 0.02) for x in xs] + [(x, b + 0.02) for x in xs], cw, ch)
        if spot:
            text(slide, spot[0], spot[1], cw, ch, s, size=8, color=SUB, align="c", name="flow-check")
            taken.append(spot)
        else:
            k = len(notes) + 1
            mk = "※%d" % k
            mw = _wf_text_w(mk, 8) + 0.12
            l, t = n["cx"] - n["w"] / 2.0, n["cy"] - n["h"] / 2.0
            spot = free_spot([(l + n["w"] * 0.62, t - 0.02), (l + n["w"] * 0.1, t - 0.02),
                              (l + n["w"] * 0.62, t + n["h"] - 0.18), (l + n["w"] * 0.1, t + n["h"] - 0.18)], mw, 0.2)
            spot = spot or (l + n["w"] * 0.62, t - 0.02, l + n["w"] * 0.62 + mw, t + 0.18)
            text(slide, spot[0], spot[1], mw, 0.2, mk, size=8, bold=True, color=SUB, name="flow-check-mark")
            taken.append(spot)
            notes.append("%s %s · %s" % (mk, F["nodes"][i]["code"], s))
    items = _wf_legend_items(N, C) if show_legend else []
    if items:
        legend(slide, items)
    fy = max(b for _, b in L["lane_y"]) + 0.06           # 각주 — 구역 띠 바로 아래
    for k, s in enumerate(notes):
        text(slide, x0, fy + k * 0.22, w, 0.24, s, size=8, color=SUB, name="flow-check-note")
    return {"cols": L["ncol"], "rows": L["R"], "overflow": L["overflow"], "refs": refs}


def _wf_legend_sample(t):
    def draw(s, x, y):
        if t == "link":
            box(s, x, y - 0.02, 0.28, 0.22, fill=WF_JUMP_FILL, line=WF_JUMP, dash=True, shape="offpage")
        elif t in WF_COLORS:
            line(s, x, y + 0.09, x + 0.28, y + 0.09, color=WF_COLORS[t], width=WF_WIDTH, arrow=True)
        else:
            shp = box(s, x, y, 0.28, 0.18, fill=WF_DECISION_FILL if t == "decision" else (TINT if t == "ref" else WHITE),
                      line=WF_EDGE, shape=FLOW_SHAPES[t] if t != "ref" else "oval")
            if t == "action":
                shp.adjustments[0] = 0.15
            elif t in ("input", "output"):
                shp.adjustments[0] = 0.3
    return draw


def _wf_legend_items(N, C):
    """범례 — 쓰인 도형 종류 · 선 종류 · 이동 연결자만."""
    used = set(n["type"] for n in N.values())
    items, names = [], []
    for t in ("term", "action", "input", "output", "decision", "process", "ref"):
        if t in used and FLOW_NAMES[t] not in names:
            names.append(FLOW_NAMES[t])
            items.append((_wf_legend_sample(t), FLOW_NAMES[t]))
    if "link" in used:
        items.append((_wf_legend_sample("link"), "이동 연결자"))
    kinds = set(c["kind"] for c in C)
    for k, name in (("yes", "예"), ("no", "아니오"), ("normal", "일반")):
        if k in kinds:
            items.append((_wf_legend_sample(k), name))
    return items


def flowchart(slide, nodes, edges, **kw):
    """이전 순서도 입력(start · end · screen · process · io · decision)을 기능 흐름도로 그립니다 — 호환용 얇은 감싸개."""
    old = {"start": "term", "end": "term", "screen": "output", "process": "action", "io": "input"}
    lanes = []
    for n in nodes:
        if n.get("lane") and n["lane"] not in lanes:
            lanes.append(n["lane"])
    flow = {"lanes": [{"key": l, "label": l} for l in lanes] or None,
            "nodes": [dict(n, type=old.get(n.get("type"), n.get("type")), text=n.get("text") or n.get("label"))
                      for n in nodes],
            "edges": [dict(e, kind="no" if e.get("kind") == "exception" else e.get("kind")) for e in edges]}
    return workflow_chart(slide, flow, **kw)


# ── 저니맵 ───────────────────────────────────────────────────────────

JOURNEY_ROWS = (("actions", "행동"), ("touchpoints", "접점"), ("thoughts", "생각"),
                ("emotion", "감정"), ("pains", "불편"), ("opportunities", "기회"))
JOURNEY_MAX = 6


def journey_map(slide, journey, x0=MX, y0=TOP, w=SW - 2 * MX):
    """단계(열) × 행동 · 접점 · 생각 · 감정 · 불편 · 기회(행). 감정은 -2~+2 점을 선으로 잇습니다."""
    stages = (journey.get("stages") or [])[:JOURNEY_MAX]
    if journey.get("persona"):
        text(slide, x0, y0 - 0.05, w, 0.3, "대상 — %s" % journey["persona"], size=11, color=SUB)
        y0 += 0.3
    lw = 1.1
    n = max(1, len(stages))
    cw = (w - lw) / n
    hh = 0.4
    rows = [r for r in JOURNEY_ROWS]
    rh = (BOTTOM - 0.2 - y0 - hh) / len(rows)       # 바닥글과 0.3in 이상 띄웁니다
    for i, st in enumerate(stages):
        box(slide, x0 + lw + i * cw, y0, cw, hh, fill=INK, line=WHITE, label=v(st.get("name")), size=11,
            bold=True, color=WHITE, shape="pentagon" if i < n - 1 else "rect")
    pts = []
    for r, (key, name) in enumerate(rows):
        y = y0 + hh + r * rh
        box(slide, x0, y, lw, rh, fill=TINT, line=GRID, label=name, size=10, bold=True, color=SUB)
        for i, st in enumerate(stages):
            cx = x0 + lw + i * cw
            box(slide, cx, y, cw, rh, fill=WHITE, line=GRID)
            if key == "emotion":
                e = max(-2, min(2, int(st.get("emotion", 0) or 0)))
                py = y + rh / 2 - e * (rh / 5.0)
                pts.append((cx + cw / 2, py, e))
            else:
                val = st.get(key)
                body = "\n".join(lst(val)) if isinstance(val, list) else v(val)
                text(slide, cx + 0.08, y + 0.04, cw - 0.16, rh - 0.08, body, size=10, spacing=1, anchor="m")
        if key == "emotion":
            line(slide, x0 + lw, y + rh / 2, x0 + w, y + rh / 2, color=LINE, width=0.5, dash=True)
            for a, b in zip(pts, pts[1:]):
                line(slide, a[0], a[1], b[0], b[1], color=SUB, width=1.25)
            for px, py, e in pts:
                circle(slide, px - 0.1, py - 0.1, 0.2, ACCENT if e < 0 else INK, "", size=6)


# ── 우선순위 ─────────────────────────────────────────────────────────

QUADRANTS = (("high", "low", "빠른 성과", "먼저 합니다"), ("high", "high", "큰 승부", "계획을 세워 합니다"),
             ("low", "low", "틈새 작업", "여유 있을 때"), ("low", "high", "보류", "하지 않거나 다시 봅니다"))


def priority_matrix(slide, items, x0=MX + 0.5, y0=TOP + 0.1, w=7.6, h=None):
    """영향(세로) × 노력(가로) 2×2. 항목은 칩으로 사분면에 놓습니다(사분면당 6개까지)."""
    h = h or (BOTTOM - y0 - 0.5) * 0.82
    qw, qh = w / 2, h / 2
    text(slide, x0 - 0.5, y0 + h / 2 - 0.15, 0.45, 0.3, "영향 ↑", size=10, bold=True, color=SUB, align="c")
    text(slide, x0, y0 + h + 0.05, w, 0.3, "노력  →", size=10, bold=True, color=SUB, align="c")
    for impact, effort, name, lead in QUADRANTS:
        qx = x0 + (qw if effort == "high" else 0)
        qy = y0 + (0 if impact == "high" else qh)
        quick = impact == "high" and effort == "low"
        box(slide, qx, qy, qw, qh, fill=TINT if quick else WHITE, line=GRID, name="quadrant")
        text(slide, qx + 0.12, qy + 0.08, qw - 0.24, 0.3, name, size=12, bold=True,
             color=ACCENT if quick else INK)
        text(slide, qx + 0.12, qy + 0.36, qw - 0.24, 0.25, lead, size=9, color=SUB)
        mine = [it for it in items if str(it.get("impact", "")).lower() == impact
                and str(it.get("effort", "")).lower() == effort][:6]
        for k, it in enumerate(mine):
            cx = qx + 0.12 + (k % 2) * (qw / 2 - 0.06)
            cy = qy + 0.72 + (k // 2) * 0.4
            box(slide, cx, cy, qw / 2 - 0.2, 0.32, fill=WHITE, line=INK, shape="capsule",
                label="%s %s" % (v(it.get("id")), v(it.get("name"))), size=9)
    rest = [it for it in items if str(it.get("impact", "")).lower() not in ("high", "low")
            or str(it.get("effort", "")).lower() not in ("high", "low")]
    return rest


MOSCOW = (("must", "Must", "반드시"), ("should", "Should", "해야 함"), ("could", "Could", "하면 좋음"),
          ("wont", "Won't", "이번엔 안 함"))


def moscow_board(slide, items, x0=MX, y0=TOP, w=SW - 2 * MX):
    """MoSCoW 네 칸 보드. 칸마다 카드를 위에서 쌓습니다(칸당 8개까지)."""
    cw = (w - 0.3 * 3) / 4
    for i, (key, name, lead) in enumerate(MOSCOW):
        x = x0 + i * (cw + 0.3)
        box(slide, x, y0, cw, 0.55, fill=INK if key == "must" else TINT, line=None if key == "must" else GRID,
            label="%s · %s" % (name, lead), size=12, bold=True, color=WHITE if key == "must" else INK)
        mine = [it for it in items if str(it.get("moscow", "")).lower().replace("'", "") == key][:8]
        # 칸 바탕을 아래까지 깔아 네 칸이 한 판으로 읽히게 합니다. 빈 칸은 비었다고 적습니다
        most = max(1, max(len([it for it in items if str(it.get("moscow", "")).lower().replace("'", "") == k])
                          for k, _, _ in MOSCOW))
        box(slide, x, y0 + 0.65, cw, min(BOTTOM - y0 - 0.75, 0.3 + min(most, 8) * 0.56 + 0.2), fill=TINT,
            round_=True, name="moscow-lane")
        if not mine:
            text(slide, x, y0 + 0.9, cw, 0.4, "해당 없음", size=11, color=MUTED, align="c")
        for k, it in enumerate(mine):
            box(slide, x + 0.12, y0 + 0.8 + k * 0.56, cw - 0.24, 0.46, fill=WHITE, line=GRID, round_=True,
                label="%s  %s" % (v(it.get("id")), v(it.get("name"))), size=10, align="l")


# ── 로드맵 ───────────────────────────────────────────────────────────

ROADMAP_MAX_TRACKS = 6
#: 마일스톤 별 크기(in) — ◆는 2단 글머리와 헷갈려 강조색 별을 씁니다
MS_STAR = 0.26


def roadmap(slide, rm, x0=MX, y0=TOP, w=SW - 2 * MX):
    """기간(열) × 트랙(행). 막대는 start~end 기간 칸, 마일스톤은 별 + 점선, today는 실선입니다.

    start · end · at · today는 periods의 순번(0부터)이며 소수로 칸 중간을 가리킬 수 있습니다.
    """
    periods = rm.get("periods") or []
    tracks = (rm.get("tracks") or [])[:ROADMAP_MAX_TRACKS]
    lw = 1.6
    n = max(1, len(periods))
    pw = (w - lw) / n
    ms = rm.get("milestones") or []
    top = y0 + (0.55 if ms else 0)
    hh = 0.38
    for i, p in enumerate(periods):
        box(slide, x0 + lw + i * pw, top, pw, hh, fill=TINT, line=GRID, label=p, size=10, bold=True,
            color=SUB)
    th = min(0.75, (BOTTOM - top - hh - 0.45) / max(1, len(tracks)))
    bottom = top + hh + len(tracks) * th
    for r, tr in enumerate(tracks):                       # ① 칸
        y = top + hh + r * th
        box(slide, x0, y, lw, th, fill=WHITE, line=GRID, label=v(tr.get("name")), size=10, bold=True,
            align="l")
        for i in range(n):
            box(slide, x0 + lw + i * pw, y, pw, th, fill=WHITE, line=GRID)
    for m in ms:                                          # ② 선 — 막대 아래에 깔립니다
        mx = x0 + lw + float(m.get("at", 0)) * pw
        cy = y0 + 0.05 + MS_STAR / 2                       # 별 중심 — 라벨 글자 · 점선이 여기에 맞습니다
        line(slide, mx, cy, mx, bottom, color=ACCENT, width=0.5, dash=True)
        box(slide, mx - MS_STAR / 2, cy - MS_STAR / 2, MS_STAR, MS_STAR, fill=ACCENT, shape="star",
            name="milestone")
        text(slide, mx + MS_STAR / 2 + 0.04, first_line_top(cy, 9), 1.8, 0.3, v(m.get("label")), size=9,
             bold=True, color=ACCENT)
    if rm.get("today") is not None:
        tx = x0 + lw + float(rm["today"]) * pw
        line(slide, tx, top, tx, bottom, color=INK, width=1.25)
        text(slide, tx - 0.4, bottom + 0.1, 0.8, 0.26, "오늘", size=9, bold=True, align="c")
    for r, tr in enumerate(tracks):                       # ③ 막대
        y = top + hh + r * th
        for it in tr.get("items") or []:
            s0, e = float(it.get("start", 0)), float(it.get("end", it.get("start", 0)))
            bx = x0 + lw + s0 * pw + 0.05
            bw = max(0.3, min((e - s0 + 1) * pw - 0.1, x0 + w - 0.15 - bx))   # 표 끝에서 0.15in 안쪽
            box(slide, bx, y + 0.12, bw, th - 0.24, fill=INK if it.get("main") else SUB, round_=True,
                label=v(it.get("label")), size=9, color=WHITE, bold=True)
    legend(slide, [(lambda s, x, y: box(s, x, y, 0.28, 0.18, fill=INK, round_=True), "주요 작업"),
                   (lambda s, x, y: box(s, x, y, 0.28, 0.18, fill=SUB, round_=True), "작업"),
                   (lambda s, x, y: box(s, x + 0.03, y - 0.02, 0.22, 0.22, fill=ACCENT, shape="star"), "마일스톤")],
           y=min(SH - 0.85, bottom + 0.45))          # 범례는 차트 바로 아래


# ── 비교 · 상태 ──────────────────────────────────────────────────────

def compare(slide, left, right, x0=MX, y0=TOP, w=SW - 2 * MX):
    """두 칸 비교(현행 → 개선 등). 가운데 화살표가 방향을 보입니다. 칸마다 항목 6개까지."""
    cw = (w - 1.0) / 2
    # 카드 높이는 내용에 맞춥니다 — 큰 카드에 글 몇 줄이면 비어 보입니다
    need = max(est_text_height(bullets((sd.get("items") or [])[:6]), cw - 0.6, 13, 8) for sd in (left, right))
    hgt = min(BOTTOM - y0 - 0.1, max(1.6, CARD_BODY + need + CARD_PAD))
    y0 = group_top(hgt, y0)
    for i, side in enumerate((left, right)):
        x = x0 + i * (cw + 1.0)
        box(slide, x, y0, cw, hgt, fill=TINT if i == 0 else WHITE, line=GRID if i == 0 else INK,
            round_=True, name="compare-card")
        text(slide, x + 0.3, y0 + 0.2, cw - 0.6, 0.4, v(side.get("label")), size=16, bold=True,
             color=SUB if i == 0 else ACCENT)
        text(slide, x + 0.3, y0 + CARD_BODY, cw - 0.6, hgt - 0.9,
             bullets((side.get("items") or [])[:6]) or UNKNOWN, size=13, spacing=8)
    box(slide, x0 + cw + 0.2, y0 + hgt / 2 - 0.3, 0.6, 0.6, fill=ACCENT, shape="chevron")


STATE_NAMES = (("empty", "빈 화면"), ("loading", "불러오는 중"), ("error", "오류"))


def ui_states(slide, states, header=None, y0=2.3):
    """빈 화면 · 불러오는 중 · 오류를 같은 화면 틀에 나란히 그립니다. 없는 상태는 `?` 틀로 둡니다."""
    ph = BOTTOM - y0 - 0.75
    pw = ph * 0.5
    gap = 1.6
    x0 = (SW - 3 * pw - 2 * gap) / 2
    for i, (key, name) in enumerate(STATE_NAMES):
        st = states.get(key) or {}
        regions = [{"type": "header", "label": header or "화면"}]
        if key == "loading":
            regions += [{"type": "list", "label": st.get("message") or "불러오는 중", "h": 40}]
        else:
            regions += [{"type": "text", "label": v(st.get("message")), "h": 14, "y": 38, "x": 10, "w": 80}]
            if st.get("action"):
                regions += [{"type": "button", "label": st["action"], "h": 7, "y": 56, "x": 25, "w": 50}]
        x = x0 + i * (pw + gap)
        phone(slide, x, y0, ph, regions, markers=False, title=name)
        text(slide, x - 0.3, y0 + ph + 0.08, pw + 0.6, 0.8, v(st.get("note") or st.get("sub")), size=10,
             color=SUB, align="c")


# ── 읽는 법 ──────────────────────────────────────────────────────────

def reading_guide(slide, kind="feature", change_base=None, y0=TOP + 0.05):
    """이 문서에 나오는 기호와 표기를 한 장에 모읍니다 — 처음 보는 사람이 기호에서 막히지 않게.

    kind="feature"(기능별 문서): 왼쪽 열은 화면 장(번호 표식 · 변경 배지 · 영역 유형), 오른쪽 열은 흐름도
    기호와 글 표기입니다.
    kind="overview"(서비스 개요 문서): 왼쪽 열은 IA · 화면, 오른쪽 열은 흐름 · 우선순위 · 일정입니다.
    change_base는 변경 배지의 비교 기준(예: 운영 중인 앱 1.4)이며, 없으면 미정으로 적습니다.
    견본은 열 왼쪽 0.6in 안에 그려 이름(x + 0.85)과 부딪치지 않습니다. 열마다 7줄까지입니다.
    """
    colw = (SW - 2 * MX - 0.6) / 2
    rows_l, rows_r = (_guide_overview(slide, change_base) if kind == "overview" else _guide_feature(slide))
    for c, rows in enumerate((rows_l, rows_r)):
        x = MX + c * (colw + 0.6)
        y = y0
        for draw, name, desc in rows:
            draw(x + 0.1, y + 0.08)
            text(slide, x + 0.85, first_line_top(y + 0.21, 13), colw - 0.9, 0.32, name, size=13, bold=True)
            text(slide, x + 0.85, y + 0.42, colw - 0.9, 0.3, desc, size=11, color=SUB)
            line(slide, x, y + 0.7, x + colw, y + 0.7, color=LINE, width=0.5)
            y += 0.72


def _guide_unknown(slide):
    return (lambda x, y: text(slide, x - 0.04, y - 0.03, 0.6, 0.3, "?", size=14, bold=True, color=ACCENT,
                              align="c"),
            "? · 미정", "아직 정하지 않은 값 — 문서 끝 「미결 사항」에 모여 있습니다")


def _guide_page_link(slide):
    return (lambda x, y: text(slide, x - 0.04, y - 0.03, 0.6, 0.3, "p. 4", size=12, bold=True, color=INK,
                              align="c"),
            "밑줄 쪽 번호", "누르면 그 장으로 이동합니다")


def _guide_overview(slide, change_base=None):
    """서비스 개요 문서의 읽는 법 — (왼쪽 열 IA · 화면, 오른쪽 열 흐름 · 우선순위 · 일정)."""
    def ia_kinds(x, y):                                   # ia_legend의 네 노드를 작게 나란히
        for i, k in enumerate(("page", "tab", "popup", "external")):
            shp = box(slide, x - 0.07 + i * 0.15, y + 0.04, 0.12, 0.18, fill=TAB_FILL if k == "tab" else WHITE,
                      line=INK, shape="round", dash=k in ("popup", "external"),
                      label="↗" if k == "external" else None, size=6)
            tf = shp.text_frame                           # 작은 상자라 여백을 없애야 ↗가 줄바꿈되지 않습니다
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
            tf.word_wrap = False

    def parent_leaf(x, y):                                # _node — 묶음은 옅은 바탕 + 잉크 테두리, 끝 화면은 흰 바탕 + 옅은 테두리
        box(slide, x - 0.05, y + 0.02, 0.26, 0.22, fill=TINT, line=INK, shape="round")
        box(slide, x + 0.27, y + 0.02, 0.26, 0.22, fill=WHITE, line=GRID, shape="round")

    def flow(x, y):
        box(slide, x - 0.05, y + 0.04, 0.16, 0.18, fill=WHITE, line=INK, shape="round")
        line(slide, x + 0.13, y + 0.13, x + 0.31, y + 0.13, color=INK, width=1.0, arrow=True)
        box(slide, x + 0.33, y + 0.04, 0.16, 0.18, fill=WHITE, line=INK, shape="round")

    def moscow(x, y):
        for i in range(4):
            box(slide, x - 0.05 + i * 0.14, y, 0.12, 0.26, fill=INK if i == 0 else TINT,
                line=None if i == 0 else GRID)

    def matrix(x, y):
        for r in range(2):
            for c in range(2):
                box(slide, x + 0.05 + c * 0.2, y - 0.02 + r * 0.15, 0.2, 0.15,
                    fill=TINT if (r, c) == (0, 0) else WHITE, line=GRID)

    def milestone(x, y):
        box(slide, x - 0.02, y + 0.02, 0.22, 0.22, fill=ACCENT, shape="star")
        line(slide, x + 0.38, y - 0.04, x + 0.38, y + 0.3, color=INK, width=1.25)

    rows_l = [
        (ia_kinds, "IA 노드 형태", "페이지 · 탭 · 팝업 · 외부 링크 — 점선은 잠깐 뜨는 창이나 앱 밖"),
        (lambda x, y: (badge(slide, x - 0.12, y + 0.02, "NEW", size=7), badge(slide, x + 0.28, y + 0.02, "UPDATE", size=7)),
         "변경 배지 (신규 · 수정)",
         "%s에 비해 새로 생기거나 바뀐 화면" % change_base if change_base else "비교 기준이 아직 없습니다 — 미정"),
        (parent_leaf, "굵은 테두리", "아래에 화면을 거느린 메뉴 묶음 — 옅은 테두리는 끝 화면"),
        (lambda x, y: text(slide, x - 0.08, y - 0.02, 0.7, 0.3, "S1-01", size=11, bold=True, color=INK,
                           align="c"),
         "ID 표기", "S는 화면, F-는 기능, P-는 정책 — 문서 사이는 ID로 찾습니다"),
        _guide_unknown(slide),
        _guide_page_link(slide),
    ]
    rows_r = [
        (flow, "주요 흐름", "화면이 이어지는 순서 — 화살표 방향으로 읽습니다"),
        (lambda x, y: line(slide, x, y + 0.13, x + 0.5, y + 0.13, color=ACCENT, dash=True),
         "예외 경로", "정상 흐름에서 벗어나는 길 (비로그인 · 마감 등)"),
        (moscow, "MoSCoW", "이번 출시에 넣을지 — 반드시 · 해야 함 · 하면 좋음 · 이번엔 안 함"),
        (matrix, "영향 × 노력", "범위 안 기능을 어떤 순서로 할지 — 빠른 성과부터"),
        (lambda x, y: text(slide, x - 0.08, y - 0.01, 0.7, 0.3, "범위 밖", size=10, color=SUB, align="c"),
         "범위 밖", "이번 출시에서 빠진 기능 — 목록엔 두되 기능별 문서는 없습니다"),
        (milestone, "마일스톤 · 오늘", "★은 중요한 날짜, 세로 실선은 오늘"),
    ]
    return rows_l, rows_r


def _guide_feature(slide):
    """기능별 문서의 읽는 법 — (왼쪽 열 화면 장, 오른쪽 열 흐름도 기호 · 글 표기)."""
    rows_l = [
        (lambda x, y: circle(slide, x + 0.05, y, 0.26, ACCENT, "1", size=9),
         "번호 표식", "와이어프레임의 영역과 Description의 같은 번호가 짝입니다"),
        (lambda x, y: (badge(slide, x - 0.12, y + 0.02, "NEW", size=7), badge(slide, x + 0.28, y + 0.02, "UPDATE", size=7)),
         "변경 배지 (신규 · 수정 · 삭제)", "직전 버전(문서 이력)에 비해 생기거나 바뀌거나 빠진 곳"),
        (lambda x, y: box(slide, x, y, 0.5, 0.26, fill=WF_FILL["button"], round_=True, label="버튼", size=8,
                          color=WHITE),
         "와이어프레임 영역", "회색 상자는 자리만 보입니다 — 색 · 이미지는 디자인 단계에서 정합니다"),
        (lambda x, y: (box(slide, x, y, 0.5, 0.26, fill=WF_FILL["image"], line="7F8A93"),
                       line(slide, x, y, x + 0.5, y + 0.26, color="B5BCC2", width=0.75),
                       line(slide, x, y + 0.26, x + 0.5, y, color="B5BCC2", width=0.75)),
         "이미지 자리", "X자 상자는 사진 · 그림이 들어갈 자리입니다"),
        (lambda x, y: storyboard_mini(slide, x, y),
         "화면 정보 띠", "화면 장 맨 위 — 화면 ID(S로 시작) · 화면명 · 경로 · 버전"),
        _guide_unknown(slide),
        (lambda x, y: text(slide, x - 0.08, y - 0.02, 0.7, 0.3, "{이름}", size=11, color=SUB, align="c"),
         "{동적 데이터}", "실제 값으로 바뀌어 보이는 자리"),
    ]
    # 오른쪽 열 — 기능 흐름도 기호(워크플로우 탐색기와 같은 기호 · patterns.workflow_chart)
    def fl_shape(kind, x, y, w=0.5, h=0.26):
        shp = box(slide, x, y, w, h, fill=WF_DECISION_FILL if kind == "decision" else WHITE, line=WF_EDGE,
                  shape=FLOW_SHAPES[kind])
        if kind == "action":
            shp.adjustments[0] = 0.15
        elif kind == "input":
            shp.adjustments[0] = 0.35
        return shp

    def decision(x, y):                                   # 마름모 + 예 파랑 · 아니오 빨강 선
        fl_shape("decision", x - 0.04, y - 0.04, 0.36, 0.34)
        line(slide, x + 0.32, y + 0.04, x + 0.56, y + 0.04, color=WF_YES, width=WF_WIDTH, arrow=True)
        line(slide, x + 0.32, y + 0.22, x + 0.56, y + 0.22, color=WF_NO, width=WF_WIDTH, arrow=True)

    def lanes(x, y):
        box(slide, x - 0.04, y - 0.04, 0.6, 0.17, fill=WF_LANE_USER[1], line=WF_LANE_USER[2])
        box(slide, x - 0.04, y - 0.04, 0.05, 0.17, fill=WF_LANE_USER[0])
        box(slide, x - 0.04, y + 0.13, 0.6, 0.17, fill=WF_LANE_SYSTEM[1], line=WF_LANE_SYSTEM[2])
        box(slide, x - 0.04, y + 0.13, 0.05, 0.17, fill=WF_LANE_SYSTEM[0])

    def jump(x, y):
        shp = box(slide, x - 0.06, y - 0.03, 0.66, 0.32, fill=WF_JUMP_FILL, line=WF_JUMP, dash=True,
                  shape="offpage", label="→ A2", size=8, bold=True, color=WF_JUMP_TEXT)
        tf = shp.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = 0
        tf.word_wrap = False

    rows_r = [
        (lambda x, y: fl_shape("term", x, y), "시작 · 종료", "흐름의 처음과 끝"),
        (decision, "조건 판단", "질문 하나 — 나가는 선이 예는 파랑, 아니오는 빨강, 그 밖은 검정"),
        (lambda x, y: (fl_shape("action", x - 0.04, y, 0.26), fl_shape("process", x + 0.28, y, 0.26)),
         "행동 · 처리 / 공통 처리", "네모는 한 단계, 양옆 세로선은 여러 흐름이 함께 쓰는 처리"),
        (lambda x, y: fl_shape("input", x, y), "입력 · 출력", "유저가 넣는 값 · 화면에 보이는 시트 · 안내"),
        (jump, "이동 연결자 「→ 코드」 · 「↩\ufe0e 코드」",
         "다른 섹션 · 다른 기능(F-…)으로 가거나 앞 단계로 돌아가는 곳"),
        (lanes, "유저 · 시스템 구역", "위 띠는 유저가 하는 일, 아래 띠는 시스템의 판단 · 처리 · 노출"),
        _guide_page_link(slide),
    ]
    return rows_l, rows_r


def storyboard_mini(slide, x, y):
    """읽는 법에 쓰는 정보 띠 축소판."""
    box(slide, x, y, 0.22, 0.26, fill=TABLE["head_fill"], line=GRID)
    box(slide, x + 0.22, y, 0.3, 0.26, fill=WHITE, line=GRID)


# ── 주요 흐름 ────────────────────────────────────────────────────────

#: 흐름 한 줄의 높이(in) — 예외가 없으면 칸 한 줄, 있으면 아래에 예외 상자 줄이 더 붙습니다
FLOW_ROW_H = 1.45
FLOW_ROW_EXC_H = 2.6
#: 한 줄에 놓는 화면 칸의 최대 개수
FLOW_MAX_STEPS = 7
FLOW_GAP = 0.45               # 칸 사이 가로 틈
FLOW_STEP_H = 0.8             # 화면 칸 높이
FLOW_EXC_GAP = 0.55           # 화면 칸 아래 변 ~ 예외 상자 위 변
FLOW_EXC_H = 0.62             # 예외 상자 높이


def _flow_h(f):
    return FLOW_ROW_EXC_H if f.get("exceptions") else FLOW_ROW_H


def flow_pages(flows):
    """주요 흐름을 장으로 나눕니다 — 본문 높이(BOTTOM - TOP) 안에 들어가는 만큼 앞에서부터 채웁니다."""
    pages, cur, used = [], [], 0.0
    for f in flows or []:
        h = _flow_h(f)
        if cur and used + h > BOTTOM - TOP + 0.001:
            pages.append(cur)
            cur, used = [], 0.0
        cur.append(f)
        used += h
    if cur:
        pages.append(cur)
    return pages


def main_flows(slide, flows, names, y0=TOP):
    """주요 흐름 한 장 — 흐름마다 ▼ 이름, 화면 칸을 가로로 잇고, 예외는 아래 줄의 주황 점선 상자로 갈라집니다.

    예외 상자는 출발 칸 바로 아래 열에 두고, 그 열이 이미 차 있으면 오른쪽 빈 열로 밉니다.
    연결선은 칸끼리 곧은 화살표, 예외로는 세로로 나가 꺾는 Z자(같은 열이면 곧은 세로) 하나입니다.
    """
    import re
    names = names or {}
    n = max([1] + [min(len(f.get("path") or []), FLOW_MAX_STEPS) for f in flows])
    gap = FLOW_GAP
    left = MX + TOGGLE_STEP
    cw = min(2.1, (SW - 2 * MX - TOGGLE_STEP - gap * (n - 1)) / n)
    # 슬라이드 안에 들어가는 열 수 — 예외 상자가 화면 칸보다 오른쪽으로 밀릴 때의 한계
    cols = max(n, int((SW - MX - left + gap) // (cw + gap)))

    def col_x(k):
        return left + k * (cw + gap)

    y = y0
    any_exc = False
    for f in flows:
        subhead(slide, MX, y, SW - 2 * MX, v(f.get("name")), size=14)
        path = (f.get("path") or [])[:FLOW_MAX_STEPS]
        sy = y + 0.48
        chips = []
        for k, sid in enumerate(path):
            chips.append(box(slide, col_x(k), sy, cw, FLOW_STEP_H, fill=WHITE, line=INK, round_=True,
                             label="%s\n%s" % (sid, names.get(sid, "")), size=11, name="flow-step"))
            if k:
                # 곧은 화살표 하나 — 앞 칸 오른쪽 변 가운데에서 이 칸 왼쪽 변 가운데로
                elbow(slide, col_x(k - 1) + cw, sy + FLOW_STEP_H / 2, col_x(k), sy + FLOW_STEP_H / 2,
                      color=INK, width=1.0, arrow=True, start=(chips[k - 1], 3), end=(chips[k], 1))
        excs = [e for e in (f.get("exceptions") or []) if e.get("from") in path]
        if excs:
            any_exc = True
            cb = sy + FLOW_STEP_H                     # 칸 아래 변
            ey = cb + FLOW_EXC_GAP                    # 예외 상자 위 변
            # 열 정하기 — 출발 칸 아래, 차 있으면 오른쪽 빈 열(끝까지 차면 왼쪽 빈 열)
            used, place = set(), []
            for e in excs:
                src = path.index(e["from"])
                c = src
                while c in used and c < cols - 1:
                    c += 1
                if c in used:
                    c = next((i for i in range(cols) if i not in used), src)
                used.add(c)
                place.append((e, src, c))
            # 한 칸에서 여러 예외가 나가면 출발점을 칸 아래 변에서 조금씩 비켜 겹치지 않게 합니다
            by_src = {}
            for e, src, c in place:
                by_src.setdefault(src, []).append(c)
            for e, src, c in place:
                sibs = sorted(by_src[src])
                m, j = len(sibs), sibs.index(c)
                ax = col_x(src) + cw / 2 + (j - (m - 1) / 2.0) * 0.24
                bx = col_x(c) + cw / 2
                to = v(e.get("to"))
                label = "%s %s" % (to, names.get(to, "")) if re.match(r"^S\d", to) else to
                if e.get("back"):
                    label += "\n%s" % e["back"]
                # 칸이 좁아 세 줄 넘게 접히면 9pt로 줄이고, 상자 높이는 글 줄 수에 맞춰 조금 늘립니다(줄 높이 안에서)
                fs = 10 if est_lines(label, cw - 0.14, 10) <= 2 else 9
                eh = min(FLOW_ROW_EXC_H - (0.48 + FLOW_STEP_H + FLOW_EXC_GAP) - 0.15,
                         max(FLOW_EXC_H, est_lines(label, cw - 0.14, fs) * line_height(fs) + 0.12))
                shp = box(slide, col_x(c), ey, cw, eh, fill=WHITE, line=ACCENT, dash=True, round_=True,
                          label=label, size=fs, name="flow-exception")
                kw = dict(color=ACCENT, width=1.0, arrow=True, dash=True)
                st = (chips[src], 2) if m == 1 else None
                if c == src:
                    # 같은 열 — 곧은 세로 화살표(출발점을 비켰으면 상자 위 변의 같은 x로 들어갑니다)
                    elbow(slide, ax, cb, ax, ey, start=st, end=(shp, 0) if abs(ax - bx) < 0.005 else None, **kw)
                    lx = ax + 0.06
                else:
                    # 다른 열 — 세로로 나가 칸 아래 틈의 가운데에서 꺾고, 상자 위 변 가운데로 내려갑니다.
                    # 편집기가 경로를 다시 그려도 기본 꺾임 자리가 틈 가운데라 모양이 같습니다
                    mid = cb + FLOW_EXC_GAP / 2 + 0.06 * (j - (m - 1) / 2.0)
                    elbow(slide, ax, cb, bx, ey, first="v", mid=mid, start=st, end=(shp, 0), **kw)
                    lx = bx + 0.06
                # 조건 글은 화살표 오른쪽 — 옆 열의 선까지 쓰고, 한 줄에 안 들면 8pt로 줄입니다
                lw = cw / 2 + gap - 0.12
                when = v(e.get("when"))
                text(slide, lx, ey - 0.24, lw, 0.24, when, size=9 if est_lines(when, lw - 0.06, 9) <= 1 else 8,
                     bold=True, color=ACCENT, name="flow-when")
        y += _flow_h(f)
    if any_exc:
        legend(slide, [
            (lambda s, x, y: line(s, x, y + 0.09, x + 0.28, y + 0.09, color=INK, arrow=True), "정상 흐름"),
            (lambda s, x, y: line(s, x, y + 0.09, x + 0.28, y + 0.09, color=ACCENT, dash=True), "예외 경로")])


# ── 화면 흐름 ────────────────────────────────────────────────────────

#: 이동 조건이 이 말을 담으면 예외 이동으로 그립니다(입력에 kind가 없을 때)
EXCEPTION_WORDS = ("비로그인", "데이터 없음", "네트워크", "오류", "잘못된 입력", "실패", "마감")


def is_exception_move(n):
    if n.get("kind"):
        return n["kind"] == "exception"
    return any(w in str(n.get("when", "")) for w in EXCEPTION_WORDS)


def screen_flow(slide, screens, linked=None, y0=TOP + 0.35):
    """화면 흐름 — 이 기능의 화면(와이어 축소판)과 다른 기능의 화면(이름 상자) 사이의 이동을 모두 그립니다.

    정상 이동은 실선, 예외 이동은 주황 점선이고 라벨은 「조건 (요소 번호)」입니다. 이 기능의 화면끼리는
    가로로, 다른 기능의 화면으로는 아래로 나갑니다. 선마다 가로 길(레인)을 따로 줘 겹치지 않게 합니다.
    """
    linked = {l.get("id"): l for l in (linked or [])}
    own = [sc for sc in screens[:5]]
    ids = [sc.get("id") for sc in own]
    far = []
    for sc in own:
        for n in sc.get("next") or []:
            if n.get("to") not in ids and n.get("to") not in far:
                far.append(n.get("to"))
    # 이 기능의 화면 — 위쪽 가운데
    # 아래로 나가는 선마다 레인(0.3")이 하나씩 필요합니다 — 마지막 레인도 아래 상자 위로 0.3" 띄우게 화면 높이를 줄입니다
    n_down = sum(1 for sc in own for n in sc.get("next") or [] if n.get("to") in far)
    by_top = BOTTOM - 0.55 - 0.62
    ph = max(1.8, min(2.6, by_top - 0.3 - 0.3 * max(0, n_down - 1) - 0.35 - y0)) if far else 4.4
    pw = ph * 0.5
    gap = max(1.6, min(3.2, (SW - 2 * MX - pw * len(own)) / max(1, len(own) - 1 if len(own) > 1 else 1)))
    total = pw * len(own) + gap * (len(own) - 1)
    x0 = (SW - total) / 2.0
    pos, shp = {}, {}
    for i, sc in enumerate(own):
        x = x0 + i * (pw + gap)
        # 흐름 그림의 화면은 썸네일 — 영역 글자는 생략하고 화면 이름은 제목이 맡습니다
        frames = []
        phone(slide, x, y0, ph, sc.get("regions") or [], markers=False, labels=False,
              title="%s %s" % (v(sc.get("id")), v(sc.get("name"))), frames=frames)
        pos[sc.get("id")], shp[sc.get("id")] = (x, y0, pw, ph), frames[0]
    # 다른 기능의 화면 — 아래쪽 줄
    bw, bh = 2.0, 0.62
    by = BOTTOM - 0.55 - bh
    if far:
        fgap = (SW - 2 * MX - bw * len(far)) / max(1, len(far) + 1)
        for k, fid in enumerate(far):
            bx = MX + fgap + k * (bw + fgap)
            ln = linked.get(fid, {})
            shp[fid] = box(slide, bx, by, bw, bh, fill=TINT, line=GRID, round_=True,
                           label="%s\n%s" % (v(fid), v(ln.get("name"))), size=10, name="linked-screen")
            pos[fid] = (bx, by, bw, bh)
    # 선 — 화면마다 나가는 선을 아래 변에 고르게 나눠 붙이고, 가로 길은 선마다 따로 둡니다
    lane = y0 + ph + 0.35
    top_lane = y0 - 0.55
    for sc in own:
        sx, sy, sw, sh = pos[sc.get("id")]
        outs = [n for n in sc.get("next") or [] if n.get("to") in pos]
        # 아래로 나가는 선은 목적지가 왼쪽인 것부터 왼쪽에서 나갑니다 — 선끼리 엇갈리지 않게
        down = sorted([n for n in outs if n.get("to") not in ids], key=lambda n: pos[n["to"]][0])
        for k, n in enumerate(outs):
            exc = is_exception_move(n)
            c = ACCENT if exc else INK
            label = "%s (%s)" % (v(n.get("when")), v(n.get("element")))
            tx, ty, tw, th = pos[n["to"]]
            if n["to"] in ids:                                   # 이 기능의 화면끼리
                if tx > sx:                                      # 앞으로 — 오른쪽 변 가운데에서 왼쪽 변 가운데로
                    yy = sy + sh / 2
                    elbow(slide, sx + sw, yy, tx, yy, color=c, width=1.25, arrow=True, dash=exc,
                          start=(shp[sc.get("id")], 3), end=(shp[n["to"]], 1))
                    text(slide, sx + sw + 0.05, yy - 0.32, tx - sx - sw - 0.1, 0.28, label, size=9, bold=True,
                         color=c, align="c")
                else:                                            # 되돌아감 — 위로 돌아 들어갑니다
                    ax, bxx = sx + sw / 2, tx + tw / 2
                    # ㄷ자 연결선 하나 — 화면 이름 위에서 나가 위쪽 레인을 지나 대상 화면 이름 위로 들어갑니다
                    elbow(slide, ax, sy - 0.35, bxx, ty - 0.35, first="v", mid=top_lane, color=c, width=1.0,
                          arrow=True, dash=exc)
                    text(slide, min(ax, bxx), top_lane - 0.28, abs(ax - bxx), 0.26, label, size=9, bold=True,
                         color=c, align="c")
                    top_lane -= 0.12
            else:                                                # 다른 기능의 화면으로 — 아래로
                j = down.index(n)
                ax = sx + sw * (j + 1) / (len(down) + 1)
                cx = tx + tw / 2
                # Z자 연결선 하나 — 아래로 나가 제 레인에서 꺾고, 대상 상자의 위 변 가운데에 붙습니다
                elbow(slide, ax, sy + sh, cx, ty, first="v", mid=lane, color=c, width=1.0, arrow=True, dash=exc,
                      end=(shp[n["to"]], 0))
                lx = min(ax, cx) if abs(ax - cx) > 1.2 else cx - 0.9
                text(slide, lx, lane - 0.27, max(1.8, abs(ax - cx)), 0.26, label, size=9, bold=True, color=c,
                     align="c")
                lane += 0.3
    items = [(lambda s, x, y: line(s, x, y + 0.09, x + 0.28, y + 0.09, color=INK, width=1.25), "정상 이동"),
             (lambda s, x, y: line(s, x, y + 0.09, x + 0.28, y + 0.09, color=ACCENT, dash=True), "예외 이동")]
    if far:
        items.append((lambda s, x, y: box(s, x, y, 0.28, 0.18, fill=TINT, line=GRID, round_=True), "다른 기능 화면"))
    legend(slide, items)
