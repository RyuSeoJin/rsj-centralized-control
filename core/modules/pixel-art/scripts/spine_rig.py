# -*- coding: utf-8 -*-
"""사양 파일의 뼈대 · 슬롯으로 Spine 뼈대 JSON 한 장을 만들고 캐릭터마다 스킨을 붙입니다

한 뼈대에 스킨만 갈아 끼우면 같은 애니메이션이 모든 캐릭터에 그대로 걸립니다. 그러려면 슬롯
이름 · 순서 · 관절 좌표가 캐릭터마다 같아야 하므로, 그 값은 캐릭터가 아니라 사양 파일이
정합니다 (rules/pixel-rig.md).

첨부(attachment)는 캔버스 전체 크기의 레이어 PNG입니다. 캔버스 원점이 모든 파츠에서 같아
Spine에서 위치를 손으로 맞출 일이 없습니다. Spine 좌표는 발바닥 기준선의 중심이 원점이고
y가 위로 커집니다.

사용법
------
    python spine_rig.py --spec 사양.json --out export/skeleton.json --root export 캐릭터1 캐릭터2 …
    (각 캐릭터의 레이어 PNG는 {root}/{캐릭터}/layers/{슬롯}.png)
"""
import argparse
import json
import os
import sys

import spec as specmod


def build(sp, characters, root, spine_version="4.2.00"):
    if not sp.bones or not sp.slots:
        raise ValueError("사양 파일에 bones · slots · slot_bone이 있어야 합니다")
    gx, gy = sp.center_x, sp.anchors["ground"]

    def world(b):
        return sp.bones[b][1] - gx, gy - sp.bones[b][2]

    bones = []
    for b, (parent, _, _) in sp.bones.items():
        wx, wy = world(b)
        if parent:
            px, py = world(parent)
            bones.append({"name": b, "parent": parent, "x": wx - px, "y": wy - py})
        else:
            bones.append({"name": b})
    slots = [{"name": s, "bone": sp.slot_bone[s], "attachment": s} for s in sp.slots]
    cx, cy = sp.width / 2 - gx, gy - sp.height / 2           # 캔버스 중심의 Spine 좌표
    skins = [{"name": "default", "attachments": {}}]
    missing = {}
    for ch in characters:
        att = {}
        for s in sp.slots:
            path = os.path.join(root, ch, "layers", s + ".png")
            if not os.path.exists(path):
                continue                                     # 빈 선택 슬롯
            bx, by = world(sp.slot_bone[s])
            att[s] = {s: {"path": "%s/layers/%s" % (ch, s), "x": cx - bx, "y": cy - by,
                          "width": sp.width, "height": sp.height}}
        if not att:
            missing[ch] = "레이어 PNG가 하나도 없습니다"
        skins.append({"name": ch, "attachments": att})
    if missing:
        raise ValueError("스킨을 만들 수 없습니다: %s" % missing)
    return {"skeleton": {"spine": spine_version, "images": "./", "width": sp.width, "height": sp.height},
            "bones": bones, "slots": slots, "skins": skins, "animations": {}}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("characters", nargs="+")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--root", required=True, help="캐릭터 폴더들이 있는 export 폴더")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    doc = build(specmod.load(a.spec), a.characters, a.root)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)
    print("Spine 뼈대 — %s (뼈 %d개 · 슬롯 %d개 · 스킨 %d개)"
          % (a.out, len(doc["bones"]), len(doc["slots"]), len(doc["skins"]) - 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
