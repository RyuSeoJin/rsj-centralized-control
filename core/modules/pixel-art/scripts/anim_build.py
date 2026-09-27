# -*- coding: utf-8 -*-
"""공통 몸체 동작 프레임 위에 캐릭터 파츠를 앵커 이동량만큼 옮겨 얹어 동작 스프라이트를 만듭니다

왜 이 방식인가 (rules/pixel-anim.md)
----------------------------------
  캐릭터가 많아질수록 동작 프레임을 캐릭터마다 그리면 일이 캐릭터 수만큼 늘어납니다. 그래서 동작은
  **공통 몸체**에 한 번만 그리고, 캐릭터마다 다른 머리카락 · 옷 · 소품은 **기본 자세 한 장**으로만
  그립니다. 프레임마다 머리 · 몸 · 손 같은 앵커가 기본 자세에서 몇 칸 움직였는지(사양 파일
  `animations.{태그}.offsets`)만큼 파츠를 평행 이동해 얹습니다. 회전 · 확대가 없어 도트가 깨지지 않습니다.

입력
----
  --body  공통 몸체 프레임: {폴더}/{태그}/{00,01,…}.png (캔버스 크기, 기본 방향)
  --parts 캐릭터 파츠: {폴더}/parts.json + {폴더}/{파츠}.png (캔버스 크기, 기본 자세)
          동작에 따라 모양이 달라지는 파츠는 {파츠}@{태그}.png를 두면 그 동작에서만 바꿔 씁니다.

  parts.json 예:
    {"order": ["hair_back", "BODY", "outfit", "hair_front", "pan"],
     "parts": {"hair_back": {"anchor": "head"}, "outfit": {"anchor": "body"},
               "hair_front": {"anchor": "head"}, "pan": {"anchor": "hand_R", "tags": ["cook"]}}}
    order의 BODY 자리에 공통 몸체가 들어갑니다(뒤 → 앞).

출력 (--out 폴더)
----------------
  {이름}.lua               .aseprite(레이어 · 프레임 · 태그)를 만드는 Lua — 호스트 모듈로 실행
  {이름}_sheet.png / .json 동작마다 한 줄인 스프라이트 시트와 프레임 정보(게임 엔진용)
  {이름}_sheet_R.png       좌우 반전 시트 — 기준 방향의 반대쪽을 바라보는 그림
  {이름}_preview.gif       동작을 차례로 돌려 보는 미리보기(4배)

사용법
------
    python anim_build.py --spec 사양.json --body 몸체 --parts 캐릭터/파츠 --name 이름 \\
        --out export/이름 --ase sprites/이름.aseprite
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageOps

import pixkit
import spec as specmod

BODY = "BODY"


def load_parts(parts_dir):
    with open(os.path.join(parts_dir, "parts.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    order = cfg["order"]
    if order.count(BODY) != 1:
        raise ValueError("parts.json의 order에 BODY가 한 번 있어야 합니다")
    for n in order:
        if n != BODY and n not in cfg["parts"]:
            raise ValueError("order의 %r가 parts에 없습니다" % n)
    return order, cfg["parts"]


def shifted(lay, dx, dy):
    out = pixkit.Layer(lay.name, lay.w, lay.h)
    for y in range(lay.h):
        for x in range(lay.w):
            v = lay.px[y][x]
            if v:
                out.set(x + dx, y + dy, v)
    return out


def compose(sp, body_dir, parts_dir):
    """태그 순서대로 프레임을 만듭니다. 돌려주는 것: 레이어 순서, 프레임별 레이어, 태그 목록."""
    if not sp.animations:
        raise ValueError("사양 파일에 animations가 없습니다 — 프레임 애니메이션 사양이 아닙니다")
    order, parts = load_parts(parts_dir)
    names = ["body" if n == BODY else n for n in order]
    cache = {}

    def part(name, tag):
        for key in ("%s@%s" % (name, tag), name):
            p = os.path.join(parts_dir, key + ".png")
            if os.path.exists(p):
                if p not in cache:
                    cache[p] = pixkit.from_image(name, Image.open(p), sp)
                return cache[p]
        raise FileNotFoundError("파츠 그림이 없습니다: %s.png" % name)

    frames, durations, tags = [], [], []
    for tag, a in sp.animations.items():
        start = len(frames)
        for f in range(a["frames"]):
            p = os.path.join(body_dir, tag, "%02d.png" % f)
            if not os.path.exists(p):
                raise FileNotFoundError("공통 몸체 프레임이 없습니다: %s" % p)
            layers = {"body": pixkit.from_image("body", Image.open(p), sp)}
            for n in order:
                if n == BODY:
                    continue
                cfg = parts[n]
                if cfg.get("tags") and tag not in cfg["tags"]:
                    continue
                dx, dy = sp.offset(tag, cfg["anchor"], f)
                layers[n] = shifted(part(n, tag), dx, dy)
            frames.append(layers)
            durations.append(a["ms"][f])
        tags.append((tag, start, len(frames) - 1))
    return names, frames, durations, tags


def to_image(sp, names, layers):
    img = Image.new("RGBA", (sp.width, sp.height), (0, 0, 0, 0))
    px = img.load()
    for n in names:
        lay = layers.get(n)
        if lay is None:
            continue
        for y in range(sp.height):
            for x in range(sp.width):
                v = lay.px[y][x]
                if v:
                    px[x, y] = tuple(sp.palette[v][:3]) + (255,)
    return img


def export(sp, names, frames, durations, tags, out_dir, name):
    os.makedirs(out_dir, exist_ok=True)
    imgs = [to_image(sp, names, f) for f in frames]
    cols = max(b - a + 1 for _, a, b in tags)
    sheet = Image.new("RGBA", (cols * sp.width, len(tags) * sp.height), (0, 0, 0, 0))
    sheet_r = sheet.copy()
    info = {"image": name + "_sheet.png", "mirrored": name + "_sheet_R.png",
            "cell": [sp.width, sp.height], "facing": sp.facing,
            "ground": sp.anchors.get("ground"), "center_x": sp.center_x, "tags": {}}
    if abs(sp.center_x - sp.width / 2) > 0.5:
        raise ValueError("좌우 반전 시트는 중심선이 캔버스 가운데여야 합니다 (center_x %.1f)" % sp.center_x)
    for row, (tag, a, b) in enumerate(tags):
        for col, i in enumerate(range(a, b + 1)):
            xy = (col * sp.width, row * sp.height)
            sheet.alpha_composite(imgs[i], xy)
            sheet_r.alpha_composite(ImageOps.mirror(imgs[i]), xy)
        info["tags"][tag] = {"row": row, "frames": b - a + 1, "ms": durations[a:b + 1],
                             "loop": sp.animations[tag]["loop"]}
    sheet.save(os.path.join(out_dir, name + "_sheet.png"))
    sheet_r.save(os.path.join(out_dir, name + "_sheet_R.png"))
    with open(os.path.join(out_dir, name + "_sheet.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    big = []
    for im in imgs:
        bg = Image.new("RGBA", im.size, (120, 120, 130, 255))
        bg.alpha_composite(im)
        big.append(bg.resize((im.width * 4, im.height * 4), Image.NEAREST).convert("P"))
    big[0].save(os.path.join(out_dir, name + "_preview.gif"), save_all=True, append_images=big[1:],
                duration=durations, loop=0, disposal=2)
    return imgs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--spec", required=True)
    ap.add_argument("--body", required=True)
    ap.add_argument("--parts", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--ase", required=True)
    a = ap.parse_args(argv)
    sp = specmod.load(a.spec)
    names, frames, durations, tags = compose(sp, a.body, a.parts)
    export(sp, names, frames, durations, tags, a.out, a.name)
    os.makedirs(os.path.dirname(os.path.abspath(a.ase)), exist_ok=True)
    lua = os.path.join(a.out, a.name + ".lua")
    pixkit.write_lua_anim(names, frames, durations, tags, sp, lua, a.ase)
    print("동작 스프라이트 — %s (%d프레임 · 태그 %s) · 시트 · 반전 시트 · 미리보기 · Lua"
          % (a.name, len(frames), ", ".join(t for t, _, _ in tags)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
