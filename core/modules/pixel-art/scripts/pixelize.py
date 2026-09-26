# -*- coding: utf-8 -*-
"""고해상도 컬러 그림을 목표 키의 픽셀 그림으로 줄이고 프로젝트 팔레트에 맞춥니다

왜 이 순서인가 (rules/pixel-pipeline.md §픽셀 변환)
----------------------------------------------
  1. 투명 영역을 잘라 인물만 남깁니다 — 여백이 섞이면 비율 계산이 어긋납니다.
  2. 면적 평균(BOX)으로 줄입니다 — 가장 가까운 픽셀만 고르면 가는 선이 끊기고 사라집니다.
  3. 팔레트의 가장 가까운 색으로 바꿉니다 — 색이 늘어나는 것을 여기서 막습니다.
  4. 외톨이 픽셀을 주변 다수 색으로 바꿉니다 — 축소가 남기는 점 노이즈입니다.
  5. 실루엣 가장자리를 셀아웃으로 바꿉니다 — 바깥 선은 재질의 가장 어두운 단계입니다.
  6. 캔버스의 발바닥 기준선과 중심선에 맞춰 놓습니다.

이 결과는 **초안**입니다. 얼굴 · 손 · 머리카락 끝은 손으로 다시 그립니다(§손으로 다듬기).

사용법
------
    python pixelize.py 입력.png --spec spec/design/pixel-spec.json --height 104 --out 출력.png
          [--ramps SKIN HAIR CLOTH] [--edge selout|outline|none] [--keep-singles]
"""
import argparse
import math
import sys

from PIL import Image

import spec as specmod

N8 = [(dx, dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy]


def _dist(a, b):
    """사람 눈에 가까운 RGB 거리(redmean). Lab 변환 없이 쓸 만한 근사입니다."""
    rm = (a[0] + b[0]) / 2
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return math.sqrt((2 + rm / 256) * dr * dr + 4 * dg * dg + (2 + (255 - rm) / 256) * db * db)


def nearest_table(sp, ramps=None):
    cands = [1] + [i for i in range(2, len(sp.palette))
                   if ramps is None or sp.ramp_of(i)[0] in ramps]
    cache = {}

    def near(rgb):
        if rgb not in cache:
            cache[rgb] = min(cands, key=lambda i: _dist(rgb, sp.palette[i]))
        return cache[rgb]
    return near


def pixelize(img, sp, height, ramps=None, edge="selout", keep_singles=False):
    img = img.convert("RGBA")
    bbox = img.getchannel("A").point(lambda a: 255 if a >= 128 else 0).getbbox()
    if not bbox:
        raise ValueError("불투명한 영역이 없습니다 — 배경을 투명으로 둔 그림을 넣습니다")
    img = img.crop(bbox)
    w = max(1, round(img.width * height / img.height))
    small = img.resize((w, height), Image.BOX)
    near = nearest_table(sp, ramps)
    grid = [[0] * w for _ in range(height)]
    for y in range(height):
        for x in range(w):
            r, g, b, a = small.getpixel((x, y))
            if a >= 128:
                grid[y][x] = near((r, g, b))

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
                if v and any(at(x + dx, y + dy) == 0 for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
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
    ap.add_argument("--height", type=int, required=True, help="인물 키 (px, 투명 여백 제외)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ramps", nargs="*", help="쓸 램프만 고릅니다 (없으면 전부)")
    ap.add_argument("--edge", choices=("selout", "outline", "none"), default="selout")
    ap.add_argument("--keep-singles", action="store_true")
    a = ap.parse_args(argv)
    sp = specmod.load(a.spec)
    out = pixelize(Image.open(a.input), sp, a.height, a.ramps, a.edge, a.keep_singles)
    out.save(a.out)
    print("픽셀 변환 — %s (%dx%d 캔버스, 키 %dpx)" % (a.out, sp.width, sp.height, a.height))
    return 0


if __name__ == "__main__":
    sys.exit(main())
