# -*- coding: utf-8 -*-
"""여러 캐릭터를 같은 기준선 위에 나란히 놓은 라인업 시트를 만듭니다

캐릭터 한 장씩 보면 비율이 어긋난 것을 알아채지 못합니다. 같은 배율로 나란히 놓고 사양
파일의 기준선(anchors)을 가로줄로, 중심선을 세로줄로 그으면 눈높이 · 어깨 · 발바닥이 어긋난
캐릭터가 바로 드러납니다 (rules/pixel-style.md §검수).

사용법
------
    python lineup.py --spec 사양.json --out export/lineup.png 캐릭터1.png 캐릭터2.png … [--scale 4]
"""
import argparse
import sys

from PIL import Image, ImageDraw

import spec as specmod


def lineup(images, sp, scale=4):
    w, h = sp.width * scale, sp.height * scale
    sheet = Image.new("RGBA", (w * len(images), h), (120, 120, 130, 255))
    for i, im in enumerate(images):
        big = im.convert("RGBA").resize((w, h), Image.NEAREST)
        sheet.alpha_composite(big, (i * w, 0))
    d = ImageDraw.Draw(sheet)
    for name, y in sorted(sp.anchors.items(), key=lambda kv: kv[1]):
        yy = y * scale + scale // 2
        d.line([(0, yy), (sheet.width, yy)], fill=(255, 230, 0, 255))
        d.text((3, yy - 11), name, fill=(255, 230, 0, 255))
    for i in range(len(images)):
        x = int(i * w + sp.center_x * scale)
        d.line([(x, 0), (x, h)], fill=(0, 220, 255, 255))
    return sheet


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("images", nargs="+")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--scale", type=int, default=4)
    a = ap.parse_args(argv)
    sp = specmod.load(a.spec)
    lineup([Image.open(p) for p in a.images], sp, a.scale).save(a.out)
    print("라인업 시트 — %s (%d명)" % (a.out, len(a.images)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
