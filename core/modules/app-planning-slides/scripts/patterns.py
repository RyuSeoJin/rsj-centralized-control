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


# ── 순서도 · 스윔레인 ─────────────────────────────────────────────────

#: 순서도 기호 — 시작·종료 캡슐, 화면 사각형, 처리 둥근 사각, 입출력 평행사변형, 분기 마름모
FLOW_SHAPES = {"start": "capsule", "end": "capsule", "screen": "rect", "process": "round",
               "io": "para", "decision": "diamond"}
FLOW_NAMES = {"start": "시작 · 종료", "screen": "화면", "process": "처리", "io": "안내 · 입력",
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
    # 도형을 먼저 만들고 선을 붙입니다 — 연결선 끝을 도형의 연결점에 붙여 편집기에서 옮겨도 따라오게
    shapes = {}
    for n in nodes:
        t = n.get("type", "process")
        (x, cy), (bw, bh) = pos[n["id"]], size[n["id"]]
        root = t in ("start", "end")
        shp = box(slide, x, cy - bh / 2, bw, bh, fill=INK if root else WHITE, line=INK,
                  shape=FLOW_SHAPES.get(t, "round"), label=v(n.get("label")),
                  size=9 if t in ("decision", "io") else 10, color=WHITE if root else INK, bold=root,
                  name="flow-%s" % t)
        if t in ("decision", "io"):
            # 마름모 · 평행사변형은 안쪽 글 영역이 좁습니다 — 여백을 없애 짧은 질문이 두 줄로 꺾이지 않게
            tf = shp.text_frame
            tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        shapes[n["id"]] = shp

    def site(nid, idx):
        # 사각형 · 둥근 사각형 · 마름모만 연결점 번호가 0 위 · 1 왼쪽 · 2 아래 · 3 오른쪽입니다(평행사변형은 붙이지 않음)
        return None if types[nid] == "io" else (shapes[nid], idx)

    for e in edges:
        if e["from"] not in pos or e["to"] not in pos:
            continue
        a, b = e["from"], e["to"]
        (ax, ay), (bx, by) = pos[a], pos[b]
        (aw, ah), (bw, bh) = size[a], size[b]
        exc = e.get("kind") == "exception"
        kw = dict(color=ACCENT if exc else INK, width=1.0, arrow=True, dash=exc)
        c = kw["color"]
        same_row = abs(ay - by) < 0.01
        if abs(bx - ax) < 0.01 and not same_row:          # 같은 열 위아래 — 곧은 세로 화살표
            sx = ax + aw / 2
            down = by > ay
            sy, ey = (ay + ah / 2, by - bh / 2) if down else (ay - ah / 2, by + bh / 2)
            elbow(slide, sx, sy, sx, ey, start=site(a, 2 if down else 0), end=site(b, 0 if down else 2), **kw)
            lx, ly = sx + 0.06, (sy + ey) / 2 - 0.12
        elif bx > ax and same_row:                         # 같은 줄 앞으로 — 오른쪽 변에서 왼쪽 변으로
            elbow(slide, ax + aw, ay, bx, by, start=site(a, 3), end=site(b, 1), **kw)
            lx, ly = ax + aw + 0.02, ay - 0.27
        elif bx > ax and types[a] == "decision":           # 분기의 위 · 아래 갈래 — 위 · 아래 꼭짓점에서 L자로
            sx = ax + aw / 2
            up = by < ay
            sy = ay - ah / 2 if up else ay + ah / 2
            elbow(slide, sx, sy, bx, by, first="v", start=site(a, 0 if up else 2), end=site(b, 1), **kw)
            lx, ly = sx + 0.04, (sy - 0.3 if up else sy + 0.02)
        elif bx > ax:                                      # 다른 줄 앞으로 — Z자로 꺾어 들어갑니다
            mx = ax + aw + 0.2
            elbow(slide, ax + aw, ay, bx, by, first="h", mid=mx, start=site(a, 3), end=site(b, 1), **kw)
            lx, ly = mx + 0.04, (ay + by) / 2 - 0.12
        elif same_row:                                     # 같은 줄 되돌아감 — 위로 돌아 대상의 위 변으로(ㄷ자)
            tx, ty, top = bx + bw / 2, by - bh / 2, by - bh / 2 - 0.3
            elbow(slide, ax + aw / 2, ay - ah / 2, tx, ty, first="v", mid=top, start=site(a, 0), end=site(b, 0),
                  **kw)
            lx, ly = (ax + tx) / 2, top - 0.26
        else:
            # 다른 줄 되돌아감 — 출발 상자의 위 · 아래 변에서 L자로 대상의 오른쪽 변에 들어갑니다.
            # 분기의 위 · 아래 꼭짓점은 앞으로 가는 갈래가 쓰므로 비워 둡니다
            sx = ax + aw / 2
            down = by > ay
            sy = ay + ah / 2 if down else ay - ah / 2
            elbow(slide, sx, sy, bx + bw, by, first="v", start=site(a, 2 if down else 0), end=site(b, 3), **kw)
            lx, ly = sx + 0.04, (sy + by) / 2 - 0.12
        if e.get("label"):
            text(slide, lx, ly, 0.9, 0.24, e["label"], size=9, bold=True, color=c)
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
    rows_r = [
        (lambda x, y: box(slide, x, y, 0.5, 0.26, fill=INK, shape="capsule"),
         "시작 · 종료", "흐름도의 처음과 끝"),
        (lambda x, y: box(slide, x + 0.06, y - 0.04, 0.38, 0.34, fill=WHITE, line=INK, shape="diamond"),
         "분기", "질문 하나 — 나가는 선에 「예 · 아니오」"),
        (lambda x, y: (box(slide, x, y, 0.22, 0.26, fill=WHITE, line=INK),
                       box(slide, x + 0.28, y, 0.22, 0.26, fill=WHITE, line=INK, round_=True)),
         "화면 · 처리", "네모는 화면, 둥근 네모는 시스템이 하는 일"),
        (lambda x, y: box(slide, x, y, 0.5, 0.26, fill=WHITE, line=INK, shape="para"),
         "안내 · 입력", "사용자에게 보이는 시트 · 알림 · 입력창"),
        (lambda x, y: line(slide, x, y + 0.13, x + 0.5, y + 0.13, color=ACCENT, dash=True),
         "예외 경로", "정상 흐름에서 벗어나는 길 — 점선"),
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
