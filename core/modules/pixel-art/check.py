# -*- coding: utf-8 -*-
"""pixel-art 모듈 자기 점검 — 도구가 뜨는지와 한 벌 흐름이 도는지 봅니다

한 벌 흐름: 예시 사양 파일을 읽고 → 합성한 그림을 픽셀로 바꾸고 → 검사하고 → Lua를 쓰고 →
Spine 뼈대를 만듭니다. Aseprite 실행은 컴퓨터 환경이라 여기서 하지 않습니다(중앙 게이트에는
Aseprite가 없습니다). 점검은 얕게 시작하고, 실제로 걸린 것이 나오면 그 케이스를 더합니다.
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "base", "scripts"))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import modcheck  # noqa: E402


def flow():
    from PIL import Image, ImageDraw
    import lint
    import palette_suggest
    import pixelize
    import pixkit
    import spec as specmod
    import spine_rig

    fails = []
    sp = specmod.load(os.path.join(HERE, "pixel-spec.example.json"))
    with tempfile.TemporaryDirectory() as tmp:
        # 합성 그림: 머리 · 몸 · 다리를 가진 인물 실루엣을 목표 키의 8배로 그립니다
        big = Image.new("RGBA", (400, 820), (0, 0, 0, 0))
        d = ImageDraw.Draw(big)
        d.ellipse((130, 0, 270, 140), fill=sp.palette[sp.c("SKIN", 1)])
        d.rectangle((120, 140, 280, 460), fill=sp.palette[sp.c("CLOTH_A", 1)])
        d.rectangle((130, 460, 190, 820), fill=sp.palette[sp.c("SKIN", 2)])
        d.rectangle((210, 460, 270, 820), fill=sp.palette[sp.c("SKIN", 2)])
        out = pixelize.pixelize(big, sp, height=sp.anchors["sole"] - sp.anchors["head_top"] + 1)
        png = os.path.join(tmp, "probe.png")
        out.save(png)
        n, lint_fails, _ = lint.lint(out, sp)
        fails += ["예시 흐름 검사 — %s" % f for f in lint_fails]
        lay = {s: pixkit.Layer(s, sp.width, sp.height) for s in sp.slots}
        lay["torso"] = pixkit.from_image("torso", out, sp)
        lua = os.path.join(tmp, "probe.lua")
        pixkit.write_lua(lay, sp.slots, sp, lua, os.path.join(tmp, "p.aseprite"), png)
        fails += modcheck.wrote(lua, "Lua가 비었습니다")
        os.makedirs(os.path.join(tmp, "probe", "layers"))
        out.save(os.path.join(tmp, "probe", "layers", "torso.png"))
        doc = spine_rig.build(sp, ["probe"], tmp)
        if len(doc["bones"]) != len(sp.bones) or len(doc["slots"]) != len(sp.slots):
            fails.append("Spine 뼈대의 뼈 · 슬롯 수가 사양과 다릅니다")
        # 도트 그림을 소수배(7.5배)로 키운 입력: 격자를 찾아 원본 도트를 그대로 되읽어야 합니다
        import random
        rnd = random.Random(7)
        dots = Image.new("RGBA", (24, 40), (0, 0, 0, 0))
        for y in range(2, 38):
            for x in range(3, 21):
                dots.putpixel((x, y), sp.palette[sp.c(rnd.choice(sp.ramp_names), rnd.randrange(3))] + (255,))
        scaled = dots.resize((180, 300), Image.NEAREST)
        g, ox, oy, _ = pixelize.detect_grid(scaled)
        back = pixelize.sample_native(scaled, g, ox, oy)
        if abs(g - 7.5) > 0.2 or back.crop(back.getbbox()).size != (18, 36):
            fails.append("도트 격자 되읽기 — 간격 %.2f(기대 7.5), 크기 %s(기대 18x36)"
                         % (g, back.crop(back.getbbox()).size))
        # --native는 일부러 찍은 한 점(눈동자 등)을 지우면 안 됩니다
        lone = Image.new("RGBA", (24, 40), (0, 0, 0, 0))
        for y in range(4, 36):
            for x in range(6, 18):
                lone.putpixel((x, y), sp.palette[sp.c("SKIN", 1)] + (255,))
        eye = sp.palette[sp.c("EYE", 2)] + (255,)
        lone.putpixel((11, 10), eye)
        # 경계가 거의 없는 그림이라 격자는 직접 줍니다 — 여기서 보는 것은 외톨이 정리입니다
        drawn = pixelize.pixelize(lone.resize((192, 320), Image.NEAREST), sp, native=True, grid=8,
                                  edge="none")
        if eye not in [p for p in drawn.getdata()]:
            fails.append("--native가 한 점짜리 포인트 색(눈동자)을 지웠습니다")
        small = dots.resize((96, 160), Image.NEAREST)                  # 4배 — 간격을 직접 줍니다
        g, ox, oy, _ = pixelize.detect_grid(small, 4)
        back = pixelize.sample_native(small, g, ox, oy)
        if back.crop(back.getbbox()).size != (18, 36):
            fails.append("격자 직접 지정(4배) — 크기 %s(기대 18x36)" % (back.crop(back.getbbox()).size,))
        pal = palette_suggest.suggest(dots)
        if not pal["ramps"]:
            fails.append("팔레트 제안이 램프를 만들지 못했습니다")
        fails += anim_flow(tmp)
    return fails


def anim_flow(tmp):
    """공통 몸체 + 파츠 합성: 파츠가 앵커 이동량만큼 옮겨지고 시트 · 반전 시트 · Lua가 나오는지."""
    import json
    from PIL import Image
    import anim_build
    import spec as specmod
    fails = []
    sp = specmod.load(os.path.join(HERE, "pixel-spec-field.example.json"))
    body, parts, out = (os.path.join(tmp, d) for d in ("body", "parts", "out"))
    skin = sp.palette[sp.c("SKIN", 1)] + (255,)
    hair = sp.palette[sp.c("HAIR", 1)] + (255,)
    for tag, a in sp.animations.items():
        os.makedirs(os.path.join(body, tag))
        for f in range(a["frames"]):
            im = Image.new("RGBA", (sp.width, sp.height), (0, 0, 0, 0))
            dx, dy = sp.offset(tag, "body", f)
            for y in range(30, 60):
                for x in range(26, 38):
                    im.putpixel((x + dx, min(59, y + dy)), skin)
            im.save(os.path.join(body, tag, "%02d.png" % f))
    os.makedirs(parts)
    h = Image.new("RGBA", (sp.width, sp.height), (0, 0, 0, 0))
    for y in range(14, 20):
        for x in range(26, 38):
            h.putpixel((x, y), hair)
    h.save(os.path.join(parts, "hair_front.png"))
    with open(os.path.join(parts, "parts.json"), "w", encoding="utf-8") as f:
        json.dump({"order": ["BODY", "hair_front"], "parts": {"hair_front": {"anchor": "head"}}}, f)
    names, frames, durations, tags = anim_build.compose(sp, body, parts)
    imgs = anim_build.export(sp, names, frames, durations, tags, out, "probe")
    # idle 세 번째 프레임에서 머리 앵커는 (0, 1) — 머리카락 맨 윗줄이 14 → 15로 내려가야 합니다
    top = min(y for y in range(sp.height) for x in range(sp.width) if frames[2]["hair_front"].px[y][x])
    if top != 15:
        fails.append("파츠 이동 — idle 3번째 프레임 머리카락 윗줄 %d(기대 15)" % top)
    if len(frames) != sum(a["frames"] for a in sp.animations.values()):
        fails.append("프레임 수가 사양의 합과 다릅니다")
    for fn in ("probe_sheet.png", "probe_sheet_R.png", "probe_sheet.json", "probe_preview.gif"):
        fails += modcheck.wrote(os.path.join(out, fn), "동작 스프라이트 산출물이 비었습니다")
    import pixkit
    lua = os.path.join(out, "probe.lua")
    pixkit.write_lua_anim(names, frames, durations, tags, sp, lua, os.path.join(out, "probe.aseprite"))
    fails += modcheck.wrote(lua, "동작 Lua가 비었습니다")
    return fails


def main():
    ok = modcheck.imports(__file__)
    return modcheck.done("pixel-art", ok, flow())


if __name__ == "__main__":
    sys.exit(main())
