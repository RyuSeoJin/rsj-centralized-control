# -*- coding: utf-8 -*-
"""픽셀 그림 한 장이 스타일 규칙을 지키는지 기계로 검사합니다

무엇을 보나 (rules/pixel-style.md §7-1)
--------------------------------------
  실패 — 종료 코드 1
  ① 팔레트 밖 색        사양 파일 팔레트에 없는 색이 하나라도 있으면 실패
  ② 색 수               캐릭터 한 장이 쓰는 색이 limits.colors_max를 넘으면 실패
  ③ 외곽선 뭉침          외곽선 색 2×2 덩어리 — 선 두께가 2px로 보이는 자리
  ④ 지면 아래 픽셀       ground 기준선 아래에 칠한 픽셀
  ⑥ 반투명 픽셀          알파가 0도 255도 아닌 픽셀. 엔진 배경 위에서 테두리가 번집니다

  경고 — 종료 코드를 바꾸지 않습니다
  ⑤ 외톨이 픽셀 (isolated)   여덟 이웃과 색이 모두 다른 점. 램프의 가장 밝은 단계(하이라이트)와
                             사양 lint.single_ok_ramps · --allow-single의 램프는 세지 않습니다
  ⑦ 이중 외곽선 (double_line) 실루엣 바깥의 외곽선 색이 안쪽으로 한 칸 더 붙어 2도트 두께가 된
                             자리(계단의 꺾이는 모서리에 남은 L자 칸 포함). ③의 2×2 덩어리는 빼고 셉니다
  ⑧ 계단 불규칙 (jaggies)    실루엣 테두리의 계단 길이가 1-3-1 · 1-2-1-3처럼 혼자 튀는 자리
  ⑨ 베개 셰이딩 (pillow)     한 재질 덩어리가 광원 쪽 테두리까지 가운데보다 어두운 자리
  ⑩ 밴딩 (banding)           한 램프의 단계들이 같은 폭으로 나란히 늘어서 줄무늬가 되고, 그 줄무늬가
                             이웃한 세 줄 이상 이어지는 자리

경고가 실패가 아닌 까닭: 기계가 의도를 판정할 수 없습니다. 눈 하이라이트는 외톨이 점이고, 직선
구간 끝의 긴 계단은 일부러 둔 평평한 면일 수 있습니다. 숫자가 크게 늘었을 때 사람이 보는 신호로 씁니다.
끄고 싶은 경고는 사양 파일의 "lint": {"off": ["banding", …]}에 이름을 적습니다(⑥도 끌 수 있습니다).

사용법
------
    python lint.py 그림.png --spec spec/design/pixel-spec.json [--allow-single EYE ACCENT]
    python lint.py --selftest      임시 폴더에 결함을 하나씩 넣은 그림을 만들어 각 검사가 잡는지 봅니다
"""
import argparse
import os
import sys
import tempfile

from PIL import Image

import spec as specmod

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))
WARN_NAMES = ("isolated", "double_line", "jaggies", "pillow", "banding", "alpha")
DIRS = {"top": (0, -1), "bottom": (0, 1), "left": (-1, 0), "right": (1, 0)}


def _options(sp, allow_single=(), off=()):
    o = sp.data.get("lint", {}) if hasattr(sp, "data") else {}
    single_ok = set(o.get("single_ok_ramps", [])) | set(allow_single)
    off = set(o.get("off", [])) | set(off)
    unknown = off - set(WARN_NAMES)
    if unknown:
        raise ValueError("lint.off에 모르는 이름: %s (쓸 수 있는 이름: %s)"
                         % (sorted(unknown), ", ".join(WARN_NAMES)))
    return single_ok, off


# --- ⑦ 이중 외곽선 --------------------------------------------------------
def find_double_lines(grid, clumped):
    """바깥(투명)에 닿은 외곽선 픽셀 P 안쪽에 외곽선 Q가 붙고, Q는 바깥에 닿지 않으며, 그 안쪽은 칠해진 자리.

    Q가 바깥에 닿지 않는다는 조건이 계단의 가로 구간(가로로 두 칸 이어진 1px 선)을 빼 줍니다.
    셀아웃의 바깥 선(램프의 가장 어두운 단계)은 보지 않습니다 — 그림자 쪽 어두운 면과 구별할 수
    없어 시험에서 정상 셰이딩을 잡았습니다.
    """
    h, w = len(grid), len(grid[0])

    def val(x, y):
        return grid[y][x] if 0 <= x < w and 0 <= y < h else 0

    hits = []
    for y in range(h):
        for x in range(w):
            if grid[y][x] != 1 or (x, y) in clumped:
                continue
            for dx, dy in N4:
                if val(x - dx, y - dy) != 0:
                    continue
                qx, qy = x + dx, y + dy
                if val(qx, qy) != 1 or (qx, qy) in clumped:
                    continue
                if any(val(qx + ex, qy + ey) == 0 for ex, ey in N4):
                    continue
                if val(qx + dx, qy + dy) not in (0, 1):
                    hits.append((x, y))
                    break
    return hits


# --- ⑧ 계단 불규칙 --------------------------------------------------------
def _runs(seq):
    out = []
    for i, v in enumerate(seq):
        if out and out[-1][0] == v:
            out[-1][2] += 1
        else:
            out.append([v, i, 1])
    return out


def _irregular(seq):
    """한 줄 윤곽(위치 → 값)에서 혼자 튀는 계단 구간의 (시작 위치, 값)."""
    hits = []
    runs = _runs(seq)
    i = 0
    while i < len(runs) - 1:
        step = runs[i + 1][0] - runs[i][0]
        if abs(step) != 1:
            i += 1
            continue
        j = i + 1
        while j + 1 < len(runs) and runs[j + 1][0] - runs[j][0] == step:
            j += 1
        seg = runs[i:j + 1]
        # 양 끝 구간은 모서리에서 잘린 길이라 세지 않고, 이웃도 안쪽 구간일 때만 판정합니다
        for k in range(2, len(seg) - 2):
            a, b, c = seg[k - 1][2], seg[k][2], seg[k + 1][2]
            # 긴 계단의 ±1~2는 눈에 띄지 않으므로, 튀는 폭이 이웃 길이의 절반 이상일 때만 봅니다
            if ((b > a and b > c) or (b < a and b < c)) and                     max(abs(b - a), abs(b - c)) >= max(2, (min(a, c) + 1) // 2):
                hits.append((seg[k][1], seg[k][0]))
        i = j
    return hits


def find_jaggies(grid):
    """실루엣의 위 · 아래 · 왼쪽 · 오른쪽 윤곽을 따로 읽어 계단 길이를 봅니다."""
    h, w = len(grid), len(grid[0])
    hits = set()

    def scan(n_pos, n_val, filled, to_xy, pick):
        seq, start = [], None
        for p in range(n_pos + 1):
            vals = [v for v in range(n_val) if p < n_pos and filled(p, v)]
            if vals:
                if start is None:
                    start = p
                seq.append(pick(vals))
            elif seq:
                for pos, v in _irregular(seq):
                    hits.add(to_xy(start + pos, v))
                seq, start = [], None

    col = lambda x, y: grid[y][x] != 0  # noqa: E731
    row = lambda y, x: grid[y][x] != 0  # noqa: E731
    scan(w, h, col, lambda p, v: (p, v), min)   # 위
    scan(w, h, col, lambda p, v: (p, v), max)   # 아래
    scan(h, w, row, lambda p, v: (v, p), min)   # 왼쪽
    scan(h, w, row, lambda p, v: (v, p), max)   # 오른쪽
    return sorted(hits)


# --- ⑨ 베개 셰이딩 --------------------------------------------------------
def _light_dirs(sp):
    words = str(sp.data.get("light", "top-left")).split("-")
    return [DIRS[k] for k in words if k in DIRS] or [DIRS["top"], DIRS["left"]]


def find_pillow(grid, sp, min_size=24, gap=0.75):
    """재질 덩어리마다 광원 쪽 테두리 · 반대쪽 테두리 · 가운데의 평균 단계를 비교합니다.

    테두리는 투명 · 외곽선 색 · 셀아웃 바깥 선에 닿은 칸만 봅니다(다른 재질과 맞닿은 칸은 접촉
    그림자일 수 있습니다).
    두 테두리가 모두 가운데보다 `gap` 단계 이상 어두우면 의심합니다.
    """
    h, w = len(grid), len(grid[0])
    light = _light_dirs(sp)
    shade = [(-dx, -dy) for dx, dy in light]
    def outside(x, y):
        return not (0 <= x < w and 0 <= y < h) or grid[y][x] == 0

    # 셀아웃의 바깥 선(투명에 닿은 가장 어두운 단계)은 외곽선으로 보고 덩어리에서 뺍니다 — 넣으면
    # 셀아웃 그림은 모두 테두리가 어두운 것으로 읽힙니다
    ramp, border = {}, set()
    for y in range(h):
        for x in range(w):
            v = grid[y][x]
            r = sp.ramp_of(v) if v > 1 else None
            if not r:
                if v in (0, 1):
                    border.add((x, y))
                continue
            if v == sp.darkest(r[0]) and any(outside(x + dx, y + dy) for dx, dy in N4):
                border.add((x, y))
            else:
                ramp[(x, y)] = r
    seen, hits = set(), []
    for p0, (name, _) in ramp.items():
        if p0 in seen:
            continue
        comp, stack = [], [p0]
        seen.add(p0)
        while stack:
            p = stack.pop()
            comp.append(p)
            for dx, dy in N4:
                q = (p[0] + dx, p[1] + dy)
                if q not in seen and q in ramp and ramp[q][0] == name:
                    seen.add(q)
                    stack.append(q)
        if len(comp) < min_size:
            continue
        cs = set(comp)

        def edge(p, dirs):
            for dx, dy in dirs:
                x, y = p[0] + dx, p[1] + dy
                if not (0 <= x < w and 0 <= y < h) or (x, y) in border:
                    return True
            return False
        lit, dark, mid = [], [], []
        for p in comp:
            s = ramp[p][1]
            a, b = edge(p, light), edge(p, shade)
            if a and not b:
                lit.append(s)
            elif b and not a:
                dark.append(s)
            elif all((p[0] + dx, p[1] + dy) in cs for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                mid.append(s)
        if len(lit) < 6 or len(dark) < 6 or len(mid) < 6:
            continue
        m = sum(mid) / len(mid)
        lm, dm = sum(lit) / len(lit), sum(dark) / len(dark)
        if lm - m >= gap and dm - m >= gap:
            x0 = min(p[0] for p in comp)
            y0 = min(p[1] for p in comp)
            hits.append((name, (x0, y0), round(lm, 1), round(m, 1), round(dm, 1)))
    return hits


# --- ⑩ 밴딩 ---------------------------------------------------------------
def _band_records(lines, sp):
    """줄마다 (시작 위치, 폭, 개수, 램프, 방향) — 한 램프의 이웃 단계가 같은 폭으로 3개 이상 이어진 곳."""
    recs = []
    for line in lines:
        runs = _runs(line)
        out = []
        i = 0
        while i < len(runs) - 2:
            r0 = sp.ramp_of(runs[i][0]) if runs[i][0] > 1 else None
            if not r0:
                i += 1
                continue
            j = i
            step = None
            while j + 1 < len(runs):
                a, b = runs[j], runs[j + 1]
                rb = sp.ramp_of(b[0]) if b[0] > 1 else None
                if not rb or rb[0] != r0[0] or b[2] != runs[i][2]:
                    break
                d = rb[1] - sp.ramp_of(a[0])[1]
                if abs(d) != 1 or (step is not None and d != step):
                    break
                step = d
                j += 1
            if j - i + 1 >= 3:
                out.append((runs[i][1], runs[i][2], j - i + 1, r0[0], step))
                i = j
            else:
                i += 1
        recs.append(out)
    return recs


def find_banding(grid, sp, min_lines=3):
    h, w = len(grid), len(grid[0])
    hits = []
    for horizontal in (True, False):
        lines = grid if horizontal else [[grid[y][x] for y in range(h)] for x in range(w)]
        recs = _band_records(lines, sp)
        prev = {}
        for li, rs in enumerate(recs):
            cur = {}
            for r in rs:
                start, width, n, name, step = r
                head, length = (li, start), 1
                for (ps, pw, pn, pname, pstep), (phead, plen) in prev.items():
                    if (pw, pname, pstep) == (width, name, step) and abs(ps - start) <= width:
                        head, length = phead, plen + 1
                        break
                cur[r] = (head, length)
                if length == min_lines:
                    li0, s0 = head
                    hits.append((s0, li0) if horizontal else (li0, s0))
            prev = cur
    return sorted(set(hits))


def lint(img, sp, allow_single=(), off=()):
    """그림 한 장을 검사해 (쓴 색 수, 실패 목록, 경고 목록)을 돌려줍니다."""
    single_ok, off = _options(sp, allow_single, off)
    img = img.convert("RGBA")
    lut = sp.rgb_index()
    w, h = img.size
    grid = [[0] * w for _ in range(h)]
    outside = set()
    partial = []
    for y in range(h):
        for x in range(w):
            r, g, b, a = img.getpixel((x, y))
            if 0 < a < 255:
                partial.append((x, y))
            if a < 128:
                continue
            i = lut.get((r, g, b))
            if i is None:
                outside.add((r, g, b))
                i = -1
            grid[y][x] = i
    fails, warns = [], []
    if outside:
        fails.append("팔레트 밖 색 %d개: %s" % (len(outside), ["#%02X%02X%02X" % c for c in sorted(outside)[:6]]))
    used = {v for row in grid for v in row if v > 0}
    if len(used) > sp.colors_max:
        fails.append("색 %d개 > 한도 %d" % (len(used), sp.colors_max))
    doubles = [(x, y) for y in range(h - 1) for x in range(w - 1)
               if grid[y][x] == grid[y][x + 1] == grid[y + 1][x] == grid[y + 1][x + 1] == 1]
    if doubles:
        fails.append("외곽선 뭉침 %d곳: %s" % (len(doubles), doubles[:6]))
    ground = sp.anchors.get("ground")
    if ground is not None:
        low = [(x, y) for y in range(ground + 1, h) for x in range(w) if grid[y][x]]
        if low:
            fails.append("지면(y=%d) 아래 픽셀 %d개: %s" % (ground, len(low), low[:6]))
    if partial and "alpha" not in off:
        fails.append("반투명 픽셀 %d개 — 알파는 0 또는 255만: %s" % (len(partial), partial[:6]))
    if "isolated" not in off:
        singles = []
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                v = grid[y][x]
                if v <= 1:
                    continue
                r = sp.ramp_of(v)
                if r and (r[1] == 0 or r[0] in single_ok):
                    continue
                if all(grid[y + dy][x + dx] != v for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy):
                    singles.append((x, y))
        if singles:
            warns.append("외톨이 픽셀 %d개: %s" % (len(singles), singles[:10]))
    if "double_line" not in off:
        clumped = {(x + dx, y + dy) for x, y in doubles for dx in (0, 1) for dy in (0, 1)}
        dl = find_double_lines(grid, clumped)
        if dl:
            warns.append("이중 외곽선 %d곳(바깥 선이 2도트 두께): %s" % (len(dl), dl[:10]))
    if "jaggies" not in off:
        jg = find_jaggies(grid)
        if jg:
            warns.append("계단 불규칙 %d곳(혼자 튀는 계단 길이): %s" % (len(jg), jg[:10]))
    if "pillow" not in off:
        for name, at, lm, m, dm in find_pillow(grid, sp):
            warns.append("베개 셰이딩 의심 — %s 덩어리(%d, %d): 광원 쪽 테두리 %.1f · 가운데 %.1f · 반대쪽 "
                         "테두리 %.1f단계(클수록 어두움)" % (name, at[0], at[1], lm, m, dm))
    if "banding" not in off:
        bd = find_banding(grid, sp)
        if bd:
            warns.append("밴딩 %d곳(같은 폭 단계가 나란히 3줄 이상): %s" % (len(bd), bd[:10]))
    return len(used), fails, warns


# --- 자기 시험 -------------------------------------------------------------
def selftest():
    """결함을 하나씩 넣은 작은 그림을 임시 폴더에 PNG로 쓰고 다시 읽어 검사가 잡는지 봅니다."""
    data = {"schema_version": 1, "canvas": {"width": 40, "height": 40}, "light": "top-left",
            "anchors": {"sole": 38, "ground": 39},
            "palette": {"outline": "#221A26",
                        "ramps": {"SKIN": ["#FFF1E4", "#F6D2BC", "#E2A895", "#B87574"],
                                  "EYE": ["#FFFFFF", "#7FD0E0", "#3E8FB8", "#2A4F80"]}}}
    sp = specmod.Spec(data)
    O = sp.palette[1] + (255,)
    S = [sp.palette[sp.c("SKIN", i)] + (255,) for i in range(4)]

    def blank():
        return Image.new("RGBA", (40, 40), (0, 0, 0, 0))

    def box(im, x0, y0, x1, y1, fill, line=O):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                edge = x in (x0, x1) or y in (y0, y1)
                im.putpixel((x, y), line if edge else fill)

    cases = []
    im = blank()
    box(im, 8, 8, 30, 30, S[1])
    cases.append(("깨끗한 상자", im, None))

    im = blank()
    box(im, 8, 8, 30, 30, S[1])
    im.putpixel((15, 15), (S[1][0], S[1][1], S[1][2], 200))
    cases.append(("반투명", im, ("실패", "반투명")))

    im = blank()
    box(im, 8, 8, 30, 30, S[1])
    im.putpixel((15, 15), (1, 2, 3, 255))
    cases.append(("팔레트 밖", im, ("실패", "팔레트 밖")))

    im = blank()
    box(im, 8, 8, 30, 30, S[1])
    im.putpixel((15, 15), S[3])
    cases.append(("외톨이", im, ("경고", "외톨이")))

    im = blank()
    box(im, 8, 8, 30, 30, S[1])
    im.putpixel((15, 15), sp.palette[sp.c("EYE", 2)] + (255,))
    sp_eye = specmod.Spec(dict(data, lint={"single_ok_ramps": ["EYE"]}))
    cases.append(("외톨이 예외(EYE)", im, None, sp_eye))

    # 이중 외곽선: 대각선 계단의 꺾이는 자리마다 바깥 선 안쪽에 외곽선 한 칸이 더 붙습니다
    im = blank()
    for y in range(6, 34):
        for x in range(6, 34):
            if x + y >= 40:
                im.putpixel((x, y), S[1])
    for k in range(6, 34):
        im.putpixel((k, 40 - k), O)
    for k in range(10, 30, 4):
        im.putpixel((k + 1, 40 - k), O)
    cases.append(("이중 외곽선", im, ("경고", "이중 외곽선")))

    # 계단 불규칙: 위 윤곽이 2-2-2-2-5-2-2-2-2로 한 번 길게 튑니다 (정상 계단 2-2-2는 잡지 않습니다)
    def stair(runs):
        im = blank()
        x, top = 2, 30
        for n in runs:
            for _ in range(n):
                for y in range(top, 38):
                    im.putpixel((x, y), S[1])
                x += 1
            top -= 1
        return im
    cases.append(("고른 계단", stair([2] * 10), None))
    cases.append(("계단 불규칙", stair([2, 2, 2, 2, 5, 2, 2, 2, 2]), ("경고", "계단 불규칙")))

    # 베개 셰이딩: 원형 덩어리 테두리를 광원 쪽까지 모두 어둡게
    def disc(pillow):
        im = blank()
        cx, cy, R = 20, 20, 11
        for y in range(40):
            for x in range(40):
                d = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                if d <= R:
                    if pillow:
                        s = 0 if d < 4 else 1 if d < 7 else 2 if d < 9.5 else 3
                    else:
                        t = (x - cx + y - cy) / (2 * R)         # 왼쪽 위가 밝습니다
                        s = max(0, min(3, int((t + 0.5) * 4)))
                    im.putpixel((x, y), S[s])
        return im
    cases.append(("방향 셰이딩", disc(False), None))
    cases.append(("베개 셰이딩", disc(True), ("경고", "베개")))

    # 밴딩: 0 · 1 · 2 · 3단계가 폭 2로 나란히, 아래 줄로 갈수록 한 칸씩 밀립니다
    im = blank()
    for y in range(10, 20):
        for x in range(4, 36):
            im.putpixel((x, y), S[((x - 4 + (y - 10)) // 2) % 4])
    cases.append(("밴딩", im, ("경고", "밴딩")))

    bad = 0
    with tempfile.TemporaryDirectory() as tmp:
        for case in cases:
            name, im, want = case[:3]
            csp = case[3] if len(case) > 3 else sp
            path = os.path.join(tmp, "case.png")
            im.save(path)
            _, fails, warns = lint(Image.open(path), csp)
            got = [("실패", f) for f in fails] + [("경고", x) for x in warns]
            if want is None:
                ok = not got
            else:
                ok = any(k == want[0] and want[1] in t for k, t in got)
            bad += not ok
            print("  %s %s — %s" % ("통과" if ok else "어긋남", name,
                                    "; ".join("%s · %s" % g for g in got) or "지적 없음"))
    print("[lint selftest] %s" % ("모두 통과" if not bad else "%d건 어긋남" % bad))
    return 1 if bad else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 epilog="검사 목록과 끄는 법은 이 파일 맨 위 설명에 있습니다.")
    ap.add_argument("image", nargs="?", help="검사할 PNG")
    ap.add_argument("--spec", help="프로젝트 사양 파일 (spec/design/pixel-spec-{용도}.json)")
    ap.add_argument("--allow-single", nargs="*", default=[], metavar="램프",
                    help="외톨이 픽셀로 세지 않을 램프 이름 (예: EYE)")
    ap.add_argument("--selftest", action="store_true", help="결함 그림을 만들어 각 검사가 잡는지 시험합니다")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.image or not a.spec:
        ap.error("그림 경로와 --spec이 필요합니다")
    sp = specmod.load(a.spec)
    n, fails, warns = lint(Image.open(a.image), sp, allow_single=a.allow_single)
    print("[lint] %s — 색 %d개" % (a.image, n))
    for f in fails:
        print("  실패 · " + f)
    for w in warns:
        print("  경고 · " + w)
    if not fails:
        print("  통과")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
