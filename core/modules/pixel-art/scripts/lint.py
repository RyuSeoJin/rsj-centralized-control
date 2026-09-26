# -*- coding: utf-8 -*-
"""픽셀 그림 한 장이 스타일 규칙을 지키는지 기계로 검사합니다

무엇을 보나 (rules/pixel-style.md §검수)
-------------------------------------
  ① 팔레트 밖 색        사양 파일 팔레트에 없는 색이 하나라도 있으면 실패
  ② 색 수               캐릭터 한 장이 쓰는 색이 limits.colors_max를 넘으면 실패
  ③ 외곽선 뭉침          외곽선 색 2×2 덩어리 — 선 두께가 2px로 보이는 자리. 실패
  ④ 지면 아래 픽셀       ground 기준선 아래에 칠한 픽셀. 실패
  ⑤ 외톨이 픽셀          여덟 이웃과 색이 모두 다른 점 — 경고. 램프의 가장 밝은 단계(하이라이트)는
                        의도한 점이라 세지 않습니다

경고는 종료 코드를 바꾸지 않습니다. 외톨이 픽셀은 눈 · 입처럼 일부러 찍은 점도 있어 기계가
판정할 수 없고, 숫자가 크게 늘었을 때 사람이 보는 신호로 씁니다.

사용법
------
    python lint.py 그림.png --spec spec/design/pixel-spec.json
"""
import argparse
import sys

from PIL import Image

import spec as specmod


def lint(img, sp):
    img = img.convert("RGBA")
    lut = sp.rgb_index()
    w, h = img.size
    grid = [[0] * w for _ in range(h)]
    outside = set()
    for y in range(h):
        for x in range(w):
            r, g, b, a = img.getpixel((x, y))
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
    singles = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            v = grid[y][x]
            if v <= 1:
                continue
            r = sp.ramp_of(v)
            if r and r[1] == 0:
                continue
            if all(grid[y + dy][x + dx] != v for dy in (-1, 0, 1) for dx in (-1, 0, 1) if dx or dy):
                singles.append((x, y))
    if singles:
        warns.append("외톨이 픽셀 %d개: %s" % (len(singles), singles[:10]))
    return len(used), fails, warns


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("image")
    ap.add_argument("--spec", required=True)
    a = ap.parse_args(argv)
    sp = specmod.load(a.spec)
    n, fails, warns = lint(Image.open(a.image), sp)
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
