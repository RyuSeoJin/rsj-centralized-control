# -*- coding: utf-8 -*-
"""슬롯별 PNG를 표준 슬롯 순서의 레이어로 쌓아 .aseprite를 만드는 Lua를 씁니다

입력은 캐릭터 폴더의 `parts/{슬롯}.png`입니다(팔레트에 맞춘 캔버스 크기 그림). 파츠로 나누지
않은 초안이면 `--single`로 한 장을 `body` 슬롯에 넣습니다. `--finalize`를 주면 외곽선 · 셀아웃 ·
접촉 그림자를 규칙대로 더합니다 — 이미 선을 그린 그림에는 주지 않습니다.

만든 Lua는 Aseprite 배치 모드로 실행합니다. 실행 파일 찾기와 실행은 이 컴퓨터의 환경 일이라
Aseprite 호스트 모듈의 도구가 맡습니다(rules/pixel-pipeline.md §Aseprite로 옮기기).

사용법
------
    python sprite_build.py --spec 사양.json --parts 캐릭터/parts --name 이름 \\
        --lua 출력.lua --ase sprites/이름.aseprite --png export/이름/이름.png [--finalize]
    python sprite_build.py --spec 사양.json --single 초안.png --name 이름 --lua … --ase … --png …
"""
import argparse
import os
import sys

from PIL import Image

import pixkit
import spec as specmod


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spec", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--parts", help="parts/{슬롯}.png가 있는 폴더")
    g.add_argument("--single", help="파츠로 나누지 않은 한 장")
    ap.add_argument("--name", required=True)
    ap.add_argument("--lua", required=True)
    ap.add_argument("--ase", required=True)
    ap.add_argument("--png", required=True)
    ap.add_argument("--finalize", action="store_true")
    a = ap.parse_args(argv)
    sp = specmod.load(a.spec)
    order = sp.slots or ["body"]
    layers = {n: pixkit.Layer(n, sp.width, sp.height) for n in order}
    if a.single:
        if "body" not in layers:
            order = order + ["body"]
        layers["body"] = pixkit.from_image("body", Image.open(a.single), sp)
    else:
        unknown = [f for f in os.listdir(a.parts)
                   if f.endswith(".png") and f[:-4] not in layers]
        if unknown:
            raise SystemExit("표준 슬롯이 아닌 파일: %s — 사양 파일의 slots를 봅니다" % unknown)
        for n in order:
            p = os.path.join(a.parts, n + ".png")
            if os.path.exists(p):
                layers[n] = pixkit.from_image(n, Image.open(p), sp)
    if a.finalize:
        pixkit.finalize(layers, order, sp)
    for p in (a.lua, a.ase, a.png):
        os.makedirs(os.path.dirname(os.path.abspath(p)), exist_ok=True)
    pixkit.write_lua(layers, order, sp, a.lua, a.ase, a.png)
    print("Lua 작성 — %s (레이어 %d장)" % (a.lua, sum(not layers[n].empty() for n in order)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
