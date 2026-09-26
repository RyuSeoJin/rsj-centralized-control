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
        out = pixelize.pixelize(big, sp, height=102)
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
    return fails


def main():
    ok = modcheck.imports(__file__)
    return modcheck.done("pixel-art", ok, flow())


if __name__ == "__main__":
    sys.exit(main())
