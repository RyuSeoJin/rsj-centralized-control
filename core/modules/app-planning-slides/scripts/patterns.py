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


#: 카드 높이 = 본문 시작 위치(소제목 아래) + 내용 높이 + 아래 여백 — 카드마다 같은 공식이라 여백이 같습니다
CARD_BODY = 0.72
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
    d = round(lh * 0.82, 3)
    gap = size * MARK_GAP / 72.0 + 0.04
    tw = w - d - gap
    for no, body in enumerate(items, 1):
        mid = y + TEXT_MARGIN + lh / 2.0 - 0.025          # 한글 글자의 눈에 보이는 중심은 줄 상자 중심보다 조금 위
        circle(slide, x, mid - d / 2.0, d, fill, str(no), size=max(8, int(size * 0.72)))
        th = est_text_height(body, tw, size, 0)
        text(slide, x + d + gap, y, tw, th + 0.05, body, size=size)
        y += max(th, d) + NUM_GAP
    return y - NUM_GAP


# ── 목차 ──────────────────────────────────────────────────────────────

def draw_toc(slide, entries, x=MX, w=SW - 2 * MX, top=1.5, step=None):
    """번호 · 제목 · 설명과 오른쪽 끝의 쪽 번호. 제목과 쪽 번호 사이를 옅은 선으로 잇습니다."""
    step = step or min(1.05, (SH - top - 0.7) / max(1, len(entries)))
    for i, (no, t, lead, page) in enumerate(entries):
        y = top + i * step
        text(slide, x, y, 1.0, 0.7, no, size=28, bold=True, color=ACCENT)
        # 제목 첫 줄을 큰 번호의 세로 중심에 맞춥니다 — 쪽 번호도 같은 줄에 둡니다
        mid = y + TEXT_MARGIN + line_height(28) / 2.0
        ty = first_line_top(mid, 18)
        text(slide, x + 1.1, ty, w - 2.4, line_height(18) + 0.06, t, size=18, bold=True)
        text(slide, x + 1.1, ty + line_height(18) + 0.04, w - 2.4, 0.36, lead, size=12, color=SUB)
        line(slide, x + 1.1, y + step - 0.12, x + w, y + step - 0.12, color=LINE, width=0.75)
        text(slide, x + w - 1.2, first_line_top(mid, 16), 1.2, line_height(16) + 0.06, "p. %s" % (page or "—"),
             size=16, bold=True, color=INK, align="r")


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
    box(slide, x, y, w, h, fill=fill,
        line=None if root else (INK if has_children else GRID),
        shape="round",
        dash=kind in ("popup", "external"), label=label.strip(), size=fs,
        color=WHITE if root else INK, bold=has_children, align="l", name="ia-node")
    if n.get("change"):
        badge(slide, x + w - 0.5, y - 0.1, n["change"], size=7)


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
            ys = [place(c, k + 1) for c in ch]
            y = (ys[0] + ys[-1]) / 2.0
            mid = x + cw + gap / 2.0
            line(slide, x + cw, y + nh / 2, mid, y + nh / 2, color=MUTED)
            line(slide, mid, ys[0] + nh / 2, mid, ys[-1] + nh / 2, color=MUTED)
            for cy in ys:
                line(slide, mid, cy + nh / 2, mid + gap / 2.0, cy + nh / 2, color=MUTED)
        else:
            y = cursor[0] + (slot - nh) / 2.0
            cursor[0] += slot
        _node(slide, x, y, cw, nh, n, k, bool(ch), fs)
        return y
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
    subhead(slide, x, y, w, title, size=12)
    line(slide, x, y + 0.34, x + w, y + 0.34, color=GRID, width=0.75)
    x, w = x + TOGGLE_STEP, w - TOGGLE_STEP              # 토글 아래 — 소제목 글자 선에 맞춥니다
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


# ── 순서도 · 스윔레인 ─────────────────────────────────────────────────

#: 순서도 기호 — 시작·종료 캡슐, 화면 사각형, 처리 둥근 사각, 입출력 평행사변형, 분기 마름모
FLOW_SHAPES = {"start": "capsule", "end": "capsule", "screen": "rect", "process": "round",
               "io": "para", "decision": "diamond"}
FLOW_NAMES = {"start": "시작 · 종료", "screen": "화면", "process": "처리", "io": "입력 · 출력",
              "decision": "분기"}
FLOW_MAX = 15


def _layers(nodes, edges):
    """시작점에서 가장 긴 경로로 열을 정합니다. 되돌아가는 연결은 열 계산에서 뺍니다."""
    ids = [n["id"] for n in nodes]
    col = {i: 0 for i in ids}
    incoming = {e["to"] for e in edges}
    order = [i for i in ids if i not in incoming] or ids[:1]
    seen, queue = set(order), list(order)
    rank = {i: k for k, i in enumerate(ids)}
    while queue:
        cur = queue.pop(0)
        for e in edges:
            if e["from"] != cur or e["to"] not in col:
                continue
            nxt = e["to"]
            if rank.get(nxt, 0) < rank.get(cur, 0) and nxt in seen:
                continue                                   # 되돌아가는 연결
            if col[nxt] < col[cur] + 1:
                col[nxt] = col[cur] + 1
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
    return col


def flowchart(slide, nodes, edges, x0=MX, y0=TOP, w=SW - 2 * MX, h=None):
    """순서도. 노드에 lane이 있으면 가로 레인(스윔레인)으로 나눠 그립니다. 예외 경로는 점선입니다."""
    h = h or (BOTTOM - y0 - 0.45)
    col = _layers(nodes, edges)
    ncol = max(col.values()) + 1 if col else 1
    lanes = []
    for n in nodes:
        if n.get("lane") and n["lane"] not in lanes:
            lanes.append(n["lane"])
    label_w = 1.0 if lanes else 0.0
    colw = (w - label_w) / ncol
    nw = min(2.0, colw - 0.4)
    pos = {}
    if lanes:
        lh = h / len(lanes)
        for i, ln in enumerate(lanes):
            ly = y0 + i * lh
            box(slide, x0, ly, w, lh, fill=TINT if i % 2 == 0 else WHITE, line=GRID, name="lane")
            box(slide, x0, ly, label_w, lh, fill=INK, label=ln, size=10, bold=True, color=WHITE)
        groups = {}
        for n in nodes:
            groups.setdefault((col[n["id"]], n.get("lane", lanes[0])), []).append(n)
        for (c, ln), ns in groups.items():
            li = lanes.index(ln)
            for k, n in enumerate(ns):
                cy = y0 + li * lh + lh * (k + 1) / (len(ns) + 1)
                pos[n["id"]] = (x0 + label_w + c * colw + (colw - nw) / 2, cy)
    else:
        groups = {}
        for n in nodes:
            groups.setdefault(col[n["id"]], []).append(n)
        for c, ns in groups.items():
            for k, n in enumerate(ns):
                cy = y0 + h * (k + 1) / (len(ns) + 1)
                pos[n["id"]] = (x0 + c * colw + (colw - nw) / 2, cy)
    size = {}
    for n in nodes:
        t = n.get("type", "process")
        nh = 0.78 if t == "decision" else 0.56
        size[n["id"]] = (nw, nh)
    types = {n["id"]: n.get("type", "process") for n in nodes}
    for e in edges:
        if e["from"] not in pos or e["to"] not in pos:
            continue
        (ax, ay), (bx, by) = pos[e["from"]], pos[e["to"]]
        (aw, ah), (bw, bh) = size[e["from"]], size[e["to"]]
        exc = e.get("kind") == "exception"
        c, d = (ACCENT if exc else INK), exc
        same_row = abs(ay - by) < 0.01
        if bx > ax and same_row:                           # 같은 줄 앞으로 — 오른쪽 변에서 왼쪽 변으로
            line(slide, ax + aw, ay, bx, by, color=c, width=1.0, arrow=True, dash=d)
            lx, ly = ax + aw + 0.02, ay - 0.27
        elif bx > ax and types[e["from"]] == "decision":   # 분기의 위 · 아래 갈래 — 위 · 아래 꼭짓점에서 나갑니다
            sx = ax + aw / 2
            sy = ay - ah / 2 if by < ay else ay + ah / 2
            line(slide, sx, sy, sx, by, color=c, width=1.0, dash=d)
            line(slide, sx, by, bx, by, color=c, width=1.0, arrow=True, dash=d)
            lx, ly = sx + 0.04, (sy - 0.3 if by < ay else sy + 0.02)
        elif bx > ax:                                      # 다른 줄 앞으로 — 꺾어서 들어갑니다
            mx = ax + aw + 0.2
            line(slide, ax + aw, ay, mx, ay, color=c, width=1.0, dash=d)
            line(slide, mx, ay, mx, by, color=c, width=1.0, dash=d)
            line(slide, mx, by, bx, by, color=c, width=1.0, arrow=True, dash=d)
            lx, ly = mx + 0.04, (ay + by) / 2 - 0.12
        else:                                              # 되돌아감 — 왼쪽으로 나가 대상의 위 · 아래로 들어갑니다
            tx = bx + bw / 2
            ty = by - bh / 2 if ay < by else by + bh / 2
            if same_row:
                ty, top = by - bh / 2, by - bh / 2 - 0.3
                line(slide, ax + aw / 2, ay - ah / 2, ax + aw / 2, top, color=c, width=1.0, dash=d)
                line(slide, ax + aw / 2, top, tx, top, color=c, width=1.0, dash=d)
                line(slide, tx, top, tx, ty, color=c, width=1.0, arrow=True, dash=d)
                lx, ly = (ax + tx) / 2, top - 0.26
            else:
                # 출발 상자의 위 · 아래 변에서 대상의 높이까지 간 뒤, 대상의 오른쪽 변으로 들어갑니다.
                # 분기의 위 · 아래 꼭짓점은 앞으로 가는 갈래가 쓰므로 비워 둡니다
                sx = ax + aw / 2
                sy = ay + ah / 2 if by > ay else ay - ah / 2
                line(slide, sx, sy, sx, by, color=c, width=1.0, dash=d)
                line(slide, sx, by, bx + bw, by, color=c, width=1.0, arrow=True, dash=d)
                lx, ly = sx + 0.04, (sy + by) / 2 - 0.12
        if e.get("label"):
            text(slide, lx, ly, 0.9, 0.24, e["label"], size=9, bold=True, color=c)
    for n in nodes:
        t = n.get("type", "process")
        (x, cy), (bw, bh) = pos[n["id"]], size[n["id"]]
        root = t in ("start", "end")
        box(slide, x, cy - bh / 2, bw, bh, fill=INK if root else WHITE, line=INK,
            shape=FLOW_SHAPES.get(t, "round"), label=v(n.get("label")), size=9 if t == "decision" else 10,
            color=WHITE if root else INK, bold=root, name="flow-%s" % t)
    kinds = []
    for n in nodes:
        t = "start" if n.get("type") in ("start", "end") else n.get("type", "process")
        if t not in kinds:
            kinds.append(t)
    items = [(lambda s, x, y, t=t: box(s, x, y, 0.28, 0.18, fill=INK if t == "start" else WHITE, line=INK,
                                      shape=FLOW_SHAPES[t]), FLOW_NAMES[t]) for t in kinds if t in FLOW_NAMES]
    if any(e.get("kind") == "exception" for e in edges):
        items.append((lambda s, x, y: line(s, x, y + 0.09, x + 0.28, y + 0.09, color=ACCENT, dash=True),
                      "예외 경로"))
    legend(slide, items)


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


def roadmap(slide, rm, x0=MX, y0=TOP, w=SW - 2 * MX):
    """기간(열) × 트랙(행). 막대는 start~end 기간 칸, 마일스톤은 마름모, today는 점선입니다.

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
        box(slide, mx - 0.12, y0 + 0.05, 0.24, 0.24, fill=ACCENT, shape="diamond")
        text(slide, mx + 0.14, y0 + 0.02, 1.8, 0.3, v(m.get("label")), size=9, bold=True, color=ACCENT)
        line(slide, mx, y0 + 0.3, mx, bottom, color=ACCENT, width=0.5, dash=True)
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
                   (lambda s, x, y: box(s, x + 0.05, y, 0.18, 0.18, fill=ACCENT, shape="diamond"), "마일스톤")],
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
