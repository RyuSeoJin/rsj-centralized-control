# -*- coding: utf-8 -*-
"""아이콘 시트를 칸마다 나눠 크기 배수 · 색 수 · 반투명 · 팔레트 · 안전 여백을 기계로 검사합니다

무엇을 보나 (rules/pixel-ui.md §1 · §2 · §10)
---------------------------------------------
  ① 시트 크기       가로 · 세로가 칸 크기의 배수가 아니면 실패 — 칸이 어긋나 아이콘이 잘립니다
  ② 반투명 픽셀     알파가 0도 255도 아닌 픽셀. 실패 — 배경마다 테두리 색이 달라 보입니다
  ③ 칸별 색 수      투명을 뺀 색 수가 한도를 넘으면 실패. 한도를 주지 않으면 칸 크기로 정합니다
                    (16 이하 5 · 24 이하 8 · 그 위 12 — pixel-ui.md §2-2의 기본값)
  ④ 팔레트 밖 색    --spec을 주고 그 파일에 palette가 있을 때만. 실패
  ⑤ 안전 여백       칸 가장자리 --margin 줄(기본 1)에 칠한 픽셀. 실패 — 등급 · 선택 테두리가 그림을 먹습니다.
                    이펙트 시트처럼 여백 규칙이 없는 시트는 --margin 0으로 끕니다
  빈 칸은 검사하지 않고 개수만 알립니다.

한도를 사양 파일에서 읽기
------------------------
  사양 파일의 ui.icon.colors_max가 숫자면 모든 칸에, {"16": 5, "24": 8}처럼 크기별이면 그 칸 크기의 값을
  씁니다. 명령줄의 --colors-max가 사양보다 앞섭니다.

사용법
------
    python icon_check.py 아이콘시트.png --cell 16 [--colors-max 5] [--margin 1] [--spec 사양.json]
    python icon_check.py --selftest          임시 폴더에 시험 시트를 만들어 스스로 확인합니다
"""
import argparse
import json
import os
import sys
import tempfile

from PIL import Image

import spec as specmod  # 콘솔 한글 출력 설정과 hex_rgb를 함께 씁니다

DEFAULT_MAX = ((16, 5), (24, 8))
DEFAULT_MAX_LARGE = 12


def default_colors_max(cell):
    for size, n in DEFAULT_MAX:
        if cell <= size:
            return n
    return DEFAULT_MAX_LARGE


def load_spec(path):
    """사양 파일에서 팔레트 색 집합과 아이콘 색 한도를 읽습니다. UI 사양은 기준선이 없어 spec.load를 쓰지 않습니다."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    colors = None
    pal = data.get("palette")
    if pal:
        colors = {specmod.hex_rgb(pal["outline"])} if pal.get("outline") else set()
        for ramp in pal.get("ramps", {}).values():
            colors.update(specmod.hex_rgb(h) for h in ramp)
    limit = data.get("ui", {}).get("icon", {}).get("colors_max")
    return colors, limit


def resolve_max(cell, cli, spec_limit):
    if cli is not None:
        return cli
    if isinstance(spec_limit, int):
        return spec_limit
    if isinstance(spec_limit, dict) and str(cell) in spec_limit:
        return int(spec_limit[str(cell)])
    return default_colors_max(cell)


def check(img, cell, colors_max, palette=None, margin=1):
    """시트 한 장을 검사해 (실패 목록, 알림 목록)을 돌려줍니다."""
    img = img.convert("RGBA")
    w, h = img.size
    fails, notes = [], []
    if w % cell or h % cell:
        fails.append("시트 크기 %dx%d가 칸 %d의 배수가 아닙니다" % (w, h, cell))
    px = img.load()
    empty = 0
    for cy in range(h // cell):
        for cx in range(w // cell):
            x0, y0 = cx * cell, cy * cell
            used, semi, outside, edge = set(), [], set(), []
            for y in range(y0, y0 + cell):
                for x in range(x0, x0 + cell):
                    r, g, b, a = px[x, y]
                    if a == 0:
                        continue
                    if a != 255:
                        semi.append((x, y))
                    used.add((r, g, b))
                    if palette is not None and (r, g, b) not in palette:
                        outside.add((r, g, b))
                    lx, ly = x - x0, y - y0
                    if margin and (lx < margin or ly < margin or lx >= cell - margin or ly >= cell - margin):
                        edge.append((x, y))
            if not used:
                empty += 1
                continue
            where = "칸 (%d,%d)" % (cx, cy)
            if semi:
                fails.append("%s 반투명 픽셀 %d개: %s" % (where, len(semi), semi[:4]))
            if len(used) > colors_max:
                fails.append("%s 색 %d개 > 한도 %d" % (where, len(used), colors_max))
            if outside:
                fails.append("%s 팔레트 밖 색 %d개: %s" % (where, len(outside),
                                                       ["#%02X%02X%02X" % c for c in sorted(outside)[:4]]))
            if edge:
                fails.append("%s 안전 여백(%dpx)에 칠한 픽셀 %d개: %s" % (where, margin, len(edge), edge[:4]))
    if empty:
        notes.append("빈 칸 %d개는 검사하지 않았습니다" % empty)
    return fails, notes


def selftest():
    """시험 시트를 만들어 통과해야 할 것은 통과하고 걸려야 할 것은 걸리는지 봅니다."""
    ink = [(34, 26, 38, 255), (200, 120, 60, 255), (240, 190, 110, 255), (120, 70, 40, 255)]
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        good = Image.new("RGBA", (32, 16), (0, 0, 0, 0))
        for i, c in enumerate(ink):
            for x in range(2, 14):
                good.putpixel((x, 2 + i * 3), c)
        path = os.path.join(tmp, "good.png")
        good.save(path)
        fails, notes = check(Image.open(path), 16, 5)
        if fails or notes != ["빈 칸 1개는 검사하지 않았습니다"]:
            problems.append("깨끗한 시트가 걸렸습니다: %s %s" % (fails, notes))
        bad = good.copy()
        bad.putpixel((5, 12), (255, 255, 255, 128))       # 반투명
        bad.putpixel((0, 0), ink[0])                      # 안전 여백
        for i in range(6):                                # 색 수 초과 (4 + 6 = 10 > 5)
            bad.putpixel((3 + i, 13), (10 * i, 200, 30, 255))
        fails, _ = check(bad, 16, 5, palette={c[:3] for c in ink})
        for word in ("반투명", "한도", "팔레트 밖", "안전 여백"):
            if not any(word in f for f in fails):
                problems.append("'%s'를 잡지 못했습니다" % word)
        fails, _ = check(Image.new("RGBA", (30, 16)), 16, 5)
        if not any("배수" in f for f in fails):
            problems.append("칸 배수가 아닌 시트를 잡지 못했습니다")
        sp = os.path.join(tmp, "ui.json")
        with open(sp, "w", encoding="utf-8") as f:
            json.dump({"palette": {"outline": "#221A26", "ramps": {"UI": ["#FFFFFF"]}},
                       "ui": {"icon": {"colors_max": {"16": 4}}}}, f)
        pal, limit = load_spec(sp)
        if resolve_max(16, None, limit) != 4 or resolve_max(24, None, limit) != 8 or len(pal) != 2:
            problems.append("사양 파일의 한도 · 팔레트를 잘못 읽었습니다")
    for p in problems:
        print("  실패 · " + p)
    print("[icon_check] 자체 시험 %s" % ("통과" if not problems else "실패"))
    return 1 if problems else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="\n".join(__doc__.split("\n")[2:]))
    ap.add_argument("image", nargs="?", help="검사할 아이콘 시트 PNG")
    ap.add_argument("--cell", type=int, help="칸(아이콘) 한 변의 크기 px — 시트 하나에 한 크기만 담습니다")
    ap.add_argument("--colors-max", type=int, help="칸 하나의 색 수 한도(투명 제외). 주지 않으면 사양 · 칸 크기로 정합니다")
    ap.add_argument("--margin", type=int, default=1, help="칸 가장자리의 비워 둘 줄 수(기본 1, 0이면 검사 안 함)")
    ap.add_argument("--spec", help="사양 파일 — palette가 있으면 팔레트 밖 색도 봅니다")
    ap.add_argument("--selftest", action="store_true", help="임시 폴더에서 스스로 시험합니다")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.image or not a.cell:
        ap.error("시트 경로와 --cell이 필요합니다")
    palette, limit = load_spec(a.spec) if a.spec else (None, None)
    cmax = resolve_max(a.cell, a.colors_max, limit)
    fails, notes = check(Image.open(a.image), a.cell, cmax, palette, a.margin)
    print("[icon_check] %s — 칸 %d · 색 한도 %d · 여백 %d" % (a.image, a.cell, cmax, a.margin))
    for f in fails:
        print("  실패 · " + f)
    for n in notes:
        print("  알림 · " + n)
    if not fails:
        print("  통과")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
