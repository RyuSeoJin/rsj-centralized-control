# -*- coding: utf-8 -*-
"""컬러 그림을 목표 키의 픽셀 그림으로 바꾸고 프로젝트 팔레트에 맞춥니다

왜 이 순서인가 (rules/pixel-pipeline.md §픽셀 변환)
----------------------------------------------
  0. (선택) 단색 배경을 지웁니다 — 가장자리에서 이어지는 배경색만 지우므로 인물 안의 같은 색은 남습니다.
  1. 투명 영역을 잘라 인물만 남깁니다 — 여백이 섞이면 비율 계산이 어긋납니다.
  2. 크기를 맞춥니다.
     - 일반 그림: 면적 평균(BOX)으로 줄입니다 — 가장 가까운 픽셀만 고르면 가는 선이 끊깁니다.
     - 이미 도트 그림을 키운 입력(--native): 격자를 찾아 칸마다 한 점씩 읽습니다. 다시 줄이면
       도트가 번지고 섞여 원본보다 흐려지기 때문입니다.
  3. 팔레트의 가장 가까운 색으로 바꿉니다 — 외곽선 색은 후보에서 뺍니다. 어두운 색이 외곽선 색으로
     바뀐 뒤 5단계에서 선을 한 번 더 두르면 선이 두 겹이 됩니다.
  4. 외톨이 픽셀을 주변 다수 색으로 바꿉니다 — 축소가 남기는 점 노이즈입니다.
  5. 실루엣 가장자리를 셀아웃으로 바꿉니다 — 바깥 선은 재질의 가장 어두운 단계입니다.
  6. 캔버스의 발바닥 기준선과 중심선에 맞춰 놓습니다.

이 결과는 **초안**입니다. 얼굴 · 손 · 머리카락 끝은 손으로 다시 그립니다(§손으로 다듬기).

사용법
------
    python pixelize.py 입력.png --spec 사양.json --height 126 --out 출력.png
          [--ramps SKIN HAIR …] [--edge selout|outline|none] [--keep-singles]
          [--bg-key auto|#RRGGBB] [--native [--grid 간격]]
"""
import argparse
import math
import sys
from collections import Counter, deque

from PIL import Image

import spec as specmod

N8 = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def _dist(a, b):
    """사람 눈에 가까운 RGB 거리(redmean). Lab 변환 없이 쓸 만한 근사입니다."""
    rm = (a[0] + b[0]) / 2
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return math.sqrt((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db)


def nearest_table(sp, ramps=None):
    """램프 색 중 가장 가까운 번호. 외곽선 색(1)은 후보가 아닙니다 — 가장자리 처리만 씁니다."""
    cands = [i for i in range(2, len(sp.palette)) if ramps is None or sp.ramp_of(i)[0] in ramps]
    if not cands:
        raise ValueError("고른 램프가 사양 파일에 없습니다: %s" % ramps)
    cache = {}

    def near(rgb):
        if rgb not in cache:
            cache[rgb] = min(cands, key=lambda i: _dist(rgb, sp.palette[i]))
        return cache[rgb]
    return near


def remove_background(img, key="auto", tol=40.0):
    """가장자리에서 이어지는 배경색 영역만 투명으로 바꿉니다. key=auto면 네 모서리의 가장 흔한 색입니다."""
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    if key == "auto":
        corners = [px[0, 0][:3], px[w - 1, 0][:3], px[0, h - 1][:3], px[w - 1, h - 1][:3]]
        key_rgb = Counter(corners).most_common(1)[0][0]
    else:
        key_rgb = specmod.hex_rgb(key)
    seen = bytearray(w * h)
    q = deque([(x, 0) for x in range(w)] + [(x, h - 1) for x in range(w)]
              + [(0, y) for y in range(h)] + [(w - 1, y) for y in range(h)])
    while q:
        x, y = q.popleft()
        if not (0 <= x < w and 0 <= y < h) or seen[y * w + x]:
            continue
        seen[y * w + x] = 1
        c = px[x, y]
        if c[3] < 128 or _dist(c[:3], key_rgb) > tol:
            continue
        px[x, y] = (0, 0, 0, 0)
        q.extend((x + dx, y + dy) for dx, dy in N4)
    return img


def _edge_profile(gray, w, h, axis):
    """열(axis=0) 또는 행(axis=1) 경계마다 밝기 차이의 합."""
    prof = [0.0] * (w if axis == 0 else h)
    for y in range(h):
        row = gray[y * w:(y + 1) * w]
        if axis == 0:
            for x in range(1, w):
                prof[x] += abs(row[x] - row[x - 1])
        elif y:
            prev = gray[(y - 1) * w:y * w]
            prof[y] = sum(abs(a - b) for a, b in zip(row, prev))
    return prof


def _period(prof, lo=2.0, hi=24.0, step=0.05, fixed=None):
    """경계 프로필에서 격자 간격과 시작 위치를 찾습니다 — 같은 간격의 경계에 차이가 몰리는 값.

    웹에서 받은 그림은 도트 그림을 소수배로 키운 경우가 많아(예: 8.47px) 간격을 소수로 찾습니다.
    간격의 배수(2배 · 3배 …)도 점수가 높게 나옵니다 — 배수 간격은 여러 경계 묶음 중 센 쪽을 골라
    오히려 조금 더 높게 나오기도 합니다. 그래서 1/2 ~ 1/6 간격 중 점수가 75% 이상인 가장 작은 간격을
    고릅니다. 진짜 간격의 절반은 칸 가운데를 절반쯤 짚어 50% 안팎으로 떨어지므로 걸러집니다.
    """
    n = len(prof)
    mean = sum(prof) / max(n, 1) or 1.0

    def score(g):
        best = (0.0, 0.0)
        for i in range(int(math.ceil(g * 4))):
            ph = i / 4.0
            # int(x + .5): 파이썬 round는 .5를 짝수 쪽으로 보내 경계 자리가 들쭉날쭉해집니다
            idx = [int(ph + k * g + .5) for k in range(int((n - ph) / g))]
            # 소수배로 키운 그림은 경계가 ±1px 흔들립니다(가장 가까운 픽셀 확대의 반올림) — 둘레 1px 안의
            # 가장 큰 값을 씁니다. 간격이 좁으면 이 창이 칸의 절반을 덮어 틀린 간격도 경계를 짚으므로
            # 6px 이상에서만 씁니다
            win = 1 if g >= 6 else 0
            vals = [max(prof[max(1, j - win):min(n, j + win + 1)] or [0]) for j in idx if 0 < j < n]
            if vals:
                s = (sum(vals) / len(vals)) / mean
                if s > best[0]:
                    best = (s, ph)
        return best

    if fixed:
        s, ph = score(fixed)
        return s, fixed, ph

    cands = []
    g = lo
    while g <= hi:
        s, ph = score(g)
        cands.append((s, g, ph))
        g += step
    s, g, ph = max(cands)

    def refine(g0):
        """g0 둘레 ±0.15를 0.01 간격으로 다시 봅니다 — 나눈 간격의 작은 오차가 칸마다 쌓이기 때문입니다."""
        return max((score(g0 + d / 100.0) + (g0 + d / 100.0,) for d in range(-15, 16)), key=lambda t: t[0])

    s, ph, g = refine(g)
    best = (s, g, ph)
    for k in range(2, 7):
        if g / k < lo:
            break
        s2, ph2, g2 = refine(g / k)
        if s2 >= s * 0.75:
            best = (s2, g2, ph2)
    return best


def detect_grid(img, grid=None):
    """도트 그림을 키운 입력의 격자 간격(소수)과 시작 위치 (가로, 세로), 점수.

    grid를 주면 간격은 그 값으로 두고 시작 위치만 찾습니다. 자동 탐지는 6배 이상 키운 입력에서
    확인했고, 3~5배처럼 작게 키운 입력은 배수 간격을 고를 수 있어 간격을 직접 줍니다.
    """
    gray_img = img.convert("L")
    w, h = gray_img.size
    gray = list(gray_img.getdata())
    sx, gx, px = _period(_edge_profile(gray, w, h, 0), fixed=grid)
    sy, gy, py = _period(_edge_profile(gray, w, h, 1), fixed=grid)
    g = (gx + gy) / 2 if abs(gx - gy) < 0.5 else min(gx, gy)
    return g, px % g, py % g, min(sx, sy)


def sample_native(img, g, ox, oy):
    """칸 가운데 절반 영역의 평균색으로 한 점씩 읽습니다. 불투명이 절반 미만인 칸은 투명입니다."""
    w, h = img.size
    px = img.load()
    cols, rows = int((w - ox) / g), int((h - oy) / g)
    out = Image.new("RGBA", (cols, rows), (0, 0, 0, 0))
    for cy in range(rows):
        for cx in range(cols):
            x0, y0 = ox + cx * g, oy + cy * g
            xs = range(int(round(x0 + g * .25)), max(int(round(x0 + g * .75)), int(round(x0 + g * .25)) + 1))
            ys = range(int(round(y0 + g * .25)), max(int(round(y0 + g * .75)), int(round(y0 + g * .25)) + 1))
            cells = [px[x, y] for y in ys for x in xs if x < w and y < h]
            opaque = [c for c in cells if c[3] >= 128]
            if not cells or len(opaque) * 2 < len(cells):
                continue
            n = len(opaque)
            out.putpixel((cx, cy), tuple(sum(c[i] for c in opaque) // n for i in range(3)) + (255,))
    return out


def pixelize(img, sp, height=None, ramps=None, edge="selout", keep_singles=False,
             bg_key=None, native=False, grid=None):
    img = img.convert("RGBA")
    if bg_key:
        img = remove_background(img, bg_key)
    bbox = img.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox()
    if not bbox:
        raise ValueError("불투명한 영역이 없습니다 — 배경을 투명으로 두거나 --bg-key를 줍니다")
    if native:
        g, ox, oy, score = detect_grid(img, grid)
        if g < 2 or score < 1.5:
            raise ValueError("도트 격자를 찾지 못했습니다(간격 %.2f · 점수 %.2f) — --native 없이 돌립니다" % (g, score))
        small = sample_native(img, g, ox, oy)
        sb = small.getbbox()
        small = small.crop(sb)
        print("격자 %.2fpx (시작 %.2f,%.2f · 점수 %.2f) → 원본 도트 %dx%d" % (g, ox, oy, score, small.width, small.height))
        w, height = small.size
    else:
        if not height:
            raise ValueError("--height가 필요합니다 (--native일 때만 생략합니다)")
        img = img.crop(bbox)
        w = max(1, round(img.width * height / img.height))
        small = img.resize((w, height), Image.BOX)
    near = nearest_table(sp, ramps)
    grid = [[0] * w for _ in range(height)]
    for y in range(height):
        for x in range(w):
            r, g_, b, a = small.getpixel((x, y))
            if a >= 128:
                grid[y][x] = near((r, g_, b))

    def at(x, y):
        return grid[y][x] if 0 <= x < w and 0 <= y < height else 0

    if not keep_singles:
        for _ in range(2):
            out = [row[:] for row in grid]
            for y in range(height):
                for x in range(w):
                    v = grid[y][x]
                    if not v:
                        continue
                    nb = [at(x + dx, y + dy) for dx, dy in N8]
                    if v in nb:
                        continue
                    opaque = [n for n in nb if n]
                    if opaque:
                        out[y][x] = max(set(opaque), key=opaque.count)
            grid = out
    if edge != "none":
        out = [row[:] for row in grid]
        for y in range(height):
            for x in range(w):
                v = grid[y][x]
                if v and any(at(x + dx, y + dy) == 0 for dx, dy in N4):
                    r = sp.ramp_of(v)
                    out[y][x] = 1 if (edge == "outline" or r is None) else sp.darkest(r[0])
        grid = out

    canvas = Image.new("RGBA", (sp.width, sp.height), (0, 0, 0, 0))
    sole = sp.anchors.get("sole", sp.height - 1)
    ox = round(sp.center_x - w / 2)
    oy = sole - height + 1
    if ox < 0 or oy < 0 or ox + w > sp.width:
        raise ValueError("캔버스(%dx%d)에 들어가지 않습니다 — 키 %d, 폭 %d"
                         % (sp.width, sp.height, height, w))
    for y in range(height):
        for x in range(w):
            if grid[y][x]:
                canvas.putpixel((ox + x, oy + y), tuple(sp.palette[grid[y][x]][:3]) + (255,))
    return canvas


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("input")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--height", type=int, help="인물 키 (px, 투명 여백 제외). --native면 생략합니다")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ramps", nargs="*", help="쓸 램프만 고릅니다 (없으면 전부)")
    ap.add_argument("--edge", choices=("selout", "outline", "none"), default="selout")
    ap.add_argument("--keep-singles", action="store_true")
    ap.add_argument("--bg-key", help="단색 배경을 지웁니다 — auto(네 모서리의 색) 또는 #RRGGBB")
    ap.add_argument("--native", action="store_true", help="이미 도트 그림을 키운 입력 — 격자대로 한 점씩 읽습니다")
    ap.add_argument("--grid", type=float, help="--native의 격자 간격을 직접 줍니다 (3~5배처럼 작게 키운 입력)")
    a = ap.parse_args(argv)
    sp = specmod.load(a.spec)
    out = pixelize(Image.open(a.input), sp, a.height, a.ramps, a.edge, a.keep_singles,
                   a.bg_key, a.native or bool(a.grid), a.grid)
    out.save(a.out)
    print("픽셀 변환 — %s (%dx%d 캔버스)" % (a.out, sp.width, sp.height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
