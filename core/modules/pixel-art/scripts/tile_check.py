# -*- coding: utf-8 -*-
"""타일셋 PNG 한 장이 격자 · 색 · 이음매 규칙을 지키는지 기계로 검사합니다

무엇을 보나 (rules/pixel-tile.md §검수)
------------------------------------
  ① 격자            이미지 크기가 「여백 + 타일(+늘림) × 칸 수 + 간격」으로 딱 나뉘는가. 실패
  ② 늘림 테두리      extrude가 있으면 테두리 픽셀이 타일 가장자리 픽셀을 그대로 복사했는가. 실패
  ③ 반투명 픽셀      알파가 0도 255도 아닌 픽셀. 허용하지 않으면 실패
  ④ 팔레트 밖 색      사양 팔레트(공유 램프 포함)에 없는 색. 실패. 사양이 없으면 건너뜁니다
  ⑤ 색 수            limits.colors_max를 넘으면 실패
  ⑥ 이음매           반복 묶음의 타일들을 좌우 · 상하로 붙였을 때 경계가 타일 안쪽보다 눈에 띄게
                    끊기는가. 실패
  ⑦ 빈 타일          완전히 투명한 칸 목록. 경고 — 시트 끝의 빈칸은 흔해서 판정하지 않습니다

이음매 판정
----------
  A의 오른쪽 열과 B의 왼쪽 열의 평균 색 거리(이음매 거리)를, 두 타일 안에서 이웃한 열끼리의
  평균 색 거리(바탕 거리)와 비교합니다. 이음매 거리가 바탕 거리 × --seam-ratio와 --seam-floor를
  모두 넘으면 끊겨 보인다고 봅니다. 잔무늬가 많은 타일은 바탕 거리가 커서 너그럽고, 매끈한
  타일은 작은 단차도 잡힙니다. 상하도 같은 방법으로 행을 비교합니다. 자기 자신과의 짝도 봅니다.

타일 지정
--------
  번호(왼쪽 위 0부터 행 순서) 또는 「열:행」. 예: --repeat 0,1,2  --repeat 4:0,5:0

사용법
------
    python tile_check.py 타일셋.png --spec spec/design/pixel-spec-tile.json
    python tile_check.py 타일셋.png --tile 16 --margin 0 --spacing 1 --repeat 0,1,2
    python tile_check.py --self-test
"""
import argparse
import io
import json
import math
import os
import sys
import tempfile

from PIL import Image

import spec as specmod  # 출력 인코딩 맞추기 · hex_rgb


# --- 사양 ---------------------------------------------------------------
def load_tile_spec(path):
    """타일 사양 파일을 읽어 검사에 쓰는 값만 돌려줍니다. 캐릭터 사양과 형식이 달라 spec.load를 쓰지 않습니다."""
    with io.open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("schema_version") != specmod.SCHEMA_VERSION:
        raise ValueError("%s: 모르는 schema_version %r" % (path, data.get("schema_version")))
    if "tile" not in data:
        raise ValueError("%s: 필수 항목 tile이 없습니다" % path)
    base = os.path.dirname(os.path.abspath(path))
    t = data["tile"]
    sheet = data.get("sheet", {})
    out = {
        "tile": (int(t["width"]), int(t["height"])),
        "margin": int(sheet.get("margin", 0)),
        "spacing": int(sheet.get("spacing", 0)),
        "extrude": int(sheet.get("extrude", 0)),
        "translucent": bool(data.get("limits", {}).get("translucent", False)),
        "colors_max": data.get("limits", {}).get("colors_max"),
        "palette": None,
        "repeat": [list(g) for g in data.get("seamless", [])],
        "notes": [],
    }
    pal = data.get("palette")
    if pal:
        cols = set()
        if pal.get("outline"):
            cols.add(specmod.hex_rgb(pal["outline"]))
        for ramp in pal.get("ramps", {}).values():
            cols.update(specmod.hex_rgb(h) for h in ramp)
        shared = pal.get("shared")
        if shared:
            sp = os.path.join(base, shared["spec"])
            if not os.path.exists(sp):
                raise ValueError("%s: 공유 팔레트 사양 %s이(가) 없습니다" % (path, shared["spec"]))
            with io.open(sp, encoding="utf-8") as f:
                other = json.load(f)["palette"]
            names = shared.get("ramps") or list(other["ramps"])
            for n in names:
                if n not in other["ramps"]:
                    raise ValueError("%s: 공유 램프 %s가 %s에 없습니다" % (path, n, shared["spec"]))
                cols.update(specmod.hex_rgb(h) for h in other["ramps"][n])
            if shared.get("outline", False):
                cols.add(specmod.hex_rgb(other["outline"]))
        out["palette"] = cols
    return out


# --- 격자 ---------------------------------------------------------------
def grid(size, tile, margin, spacing, extrude):
    """한 축의 칸 수. 나뉘지 않으면 None."""
    cell = tile + 2 * extrude
    inner = size - 2 * margin + spacing
    if inner <= 0 or inner % (cell + spacing):
        return None
    return inner // (cell + spacing)


def origin(c, r, tw, th, margin, spacing, extrude):
    """c열 r행 타일 그림의 왼쪽 위 좌표 (늘림 테두리 안쪽)."""
    return (margin + extrude + c * (tw + 2 * extrude + spacing),
            margin + extrude + r * (th + 2 * extrude + spacing))


def parse_refs(text, cols):
    refs = []
    for tok in str(text).split(","):
        tok = tok.strip()
        if not tok:
            continue
        if ":" in tok:
            c, r = tok.split(":")
            refs.append((int(c), int(r)))
        else:
            i = int(tok)
            refs.append((i % cols, i // cols))
    return refs


# --- 색 거리 -------------------------------------------------------------
def dist(p, q):
    """두 RGBA 픽셀의 거리 0~1. 한쪽만 투명하면 1, 둘 다 투명하면 0."""
    if p[3] == 0 and q[3] == 0:
        return 0.0
    if p[3] == 0 or q[3] == 0:
        return 1.0
    return math.sqrt(sum((p[i] - q[i]) ** 2 for i in range(3))) / 441.673


def col(px, x0, y0, x, h):
    return [px[x0 + x, y0 + y] for y in range(h)]


def row(px, x0, y0, y, w):
    return [px[x0 + x, y0 + y] for x in range(w)]


def mean_pair(a, b):
    return sum(dist(p, q) for p, q in zip(a, b)) / len(a)


def baseline(px, o, w, h, horizontal):
    """타일 안에서 이웃한 열(가로) 또는 행(세로)끼리의 평균 거리."""
    if horizontal:
        ds = [mean_pair(col(px, o[0], o[1], x, h), col(px, o[0], o[1], x + 1, h)) for x in range(w - 1)]
    else:
        ds = [mean_pair(row(px, o[0], o[1], y, w), row(px, o[0], o[1], y + 1, w)) for y in range(h - 1)]
    return sum(ds) / len(ds) if ds else 0.0


# --- 검사 ---------------------------------------------------------------
def check(img, tile, margin=0, spacing=0, extrude=0, translucent=False, palette=None,
          colors_max=None, repeat=(), seam_ratio=2.0, seam_floor=0.06):
    img = img.convert("RGBA")
    W, H = img.size
    tw, th = tile
    fails, warns, info = [], [], {}
    cols = grid(W, tw, margin, spacing, extrude)
    rows = grid(H, th, margin, spacing, extrude)
    if cols is None or rows is None:
        fails.append("이미지 %d×%d가 타일 %d×%d · 여백 %d · 간격 %d · 늘림 %d로 나뉘지 않습니다"
                     % (W, H, tw, th, margin, spacing, extrude))
        return info, fails, warns
    info["grid"] = (cols, rows)
    px = img.load()

    # ② 늘림 테두리
    if extrude:
        bad = []
        for r in range(rows):
            for c in range(cols):
                x0, y0 = origin(c, r, tw, th, margin, spacing, extrude)
                ok = True
                for e in range(1, extrude + 1):
                    for y in range(th):
                        if px[x0 - e, y0 + y] != px[x0, y0 + y] or px[x0 + tw - 1 + e, y0 + y] != px[x0 + tw - 1, y0 + y]:
                            ok = False
                    for x in range(-extrude, tw + extrude):
                        sx = min(max(x, 0), tw - 1)
                        if px[x0 + x, y0 - e] != px[x0 + sx, y0] or px[x0 + x, y0 + th - 1 + e] != px[x0 + sx, y0 + th - 1]:
                            ok = False
                if not ok:
                    bad.append(r * cols + c)
        if bad:
            fails.append("늘림 테두리가 가장자리 복사가 아닌 타일 %d개: %s" % (len(bad), bad[:10]))

    # ③ ④ ⑤ ⑦ — 타일 그림 안쪽만 봅니다
    semi, outside, used, empty = 0, set(), set(), []
    for r in range(rows):
        for c in range(cols):
            x0, y0 = origin(c, r, tw, th, margin, spacing, extrude)
            any_px = False
            for y in range(th):
                for x in range(tw):
                    p = px[x0 + x, y0 + y]
                    if p[3] == 0:
                        continue
                    any_px = True
                    if p[3] != 255:
                        semi += 1
                    used.add(p[:3])
                    if palette is not None and p[:3] not in palette:
                        outside.add(p[:3])
            if not any_px:
                empty.append(r * cols + c)
    info["colors"] = len(used)
    if semi and not translucent:
        fails.append("반투명 픽셀 %d개 — 허용하려면 limits.translucent 또는 --allow-translucent" % semi)
    if outside:
        fails.append("팔레트 밖 색 %d개: %s" % (len(outside), ["#%02X%02X%02X" % c for c in sorted(outside)[:6]]))
    if colors_max is not None and len(used) > int(colors_max):
        fails.append("색 %d개 > 한도 %d" % (len(used), int(colors_max)))
    if empty:
        warns.append("빈 타일 %d개: %s" % (len(empty), empty[:20]))

    # ⑥ 이음매
    for group in repeat:
        refs = parse_refs(group, cols) if isinstance(group, str) else \
            parse_refs(",".join(str(g) for g in group), cols)
        for c, r in refs:
            if not (0 <= c < cols and 0 <= r < rows):
                fails.append("반복 묶음의 타일 %d:%d가 시트 밖입니다" % (c, r))
                refs = []
                break
        org = {ref: origin(ref[0], ref[1], tw, th, margin, spacing, extrude) for ref in refs}
        for a in refs:
            for b in refs:
                oa, ob = org[a], org[b]
                for horizontal, axis in ((True, "좌우"), (False, "상하")):
                    if horizontal:
                        seam = mean_pair(col(px, oa[0], oa[1], tw - 1, th), col(px, ob[0], ob[1], 0, th))
                    else:
                        seam = mean_pair(row(px, oa[0], oa[1], th - 1, tw), row(px, ob[0], ob[1], 0, tw))
                    base = (baseline(px, oa, tw, th, horizontal) + baseline(px, ob, tw, th, horizontal)) / 2
                    if seam > max(base * seam_ratio, seam_floor):
                        fails.append("이음매 %s %s → %s: 경계 %.3f > 바탕 %.3f × %.1f"
                                     % (axis, "%d:%d" % a, "%d:%d" % b, seam, base, seam_ratio))
    return info, fails, warns


def report(path, info, fails, warns, tile):
    g = info.get("grid")
    head = "%d×%d 타일 %d×%d칸" % (tile[0], tile[1], g[0], g[1]) if g else "격자 없음"
    if "colors" in info:
        head += " · 색 %d개" % info["colors"]
    print("[tile] %s — %s" % (path, head))
    for f in fails:
        print("  실패 · " + f)
    for w in warns:
        print("  경고 · " + w)
    if not fails:
        print("  통과")


# --- 자기 시험 -------------------------------------------------------------
def self_test():
    """임시 폴더에 가짜 타일셋을 만들어 각 검사가 잡을 것을 잡고 놓을 것을 놓는지 봅니다."""
    fails = []
    T = 8
    green = [(70, 140, 60, 255), (90, 165, 70, 255), (55, 110, 55, 255)]

    def noise_tile(seed):
        # 무늬가 가장자리에서 이어지도록 좌표를 감아(mod) 색을 고릅니다
        return [[green[(x * 3 + y * 5 + seed * (x == 3) * (y == 4)) % 3] for x in range(T)] for y in range(T)]

    def grad_tile():
        # 왼쪽에서 오른쪽으로 밝아지는 띠 — 자기 자신과 이으면 경계에서 끊깁니다
        return [[(40 + x * 25, 120, 60, 255) for x in range(T)] for y in range(T)]

    def sheet(tiles, cols, margin=0, spacing=0, extrude=0, fill=(0, 0, 0, 0)):
        rows = (len(tiles) + cols - 1) // cols
        cell = T + 2 * extrude
        W = 2 * margin + cols * cell + (cols - 1) * spacing
        Hh = 2 * margin + rows * cell + (rows - 1) * spacing
        im = Image.new("RGBA", (W, Hh), fill)
        for i, t in enumerate(tiles):
            c, r = i % cols, i // cols
            x0, y0 = origin(c, r, T, T, margin, spacing, extrude)
            for y in range(-extrude, T + extrude):
                for x in range(-extrude, T + extrude):
                    if t is None:
                        continue
                    sx, sy = min(max(x, 0), T - 1), min(max(y, 0), T - 1)
                    im.putpixel((x0 + x, y0 + y), t[sy][sx])
        return im

    pal = {p[:3] for p in green} | {(40 + x * 25, 120, 60) for x in range(T)}
    with tempfile.TemporaryDirectory() as tmp:
        # 1) 정상 시트 — 여백 1 · 간격 2 · 늘림 1, 반복 묶음 0 · 1 · 2는 이어져야 합니다
        tiles = [noise_tile(0), noise_tile(1), noise_tile(2), grad_tile(), None, None]
        im = sheet(tiles, 3, margin=1, spacing=2, extrude=1)
        p = os.path.join(tmp, "ok.png")
        im.save(p)
        info, f, w = check(Image.open(p), (T, T), 1, 2, 1, palette=pal, repeat=["0,1,2"])
        if f:
            fails.append("정상 시트에서 실패가 나왔습니다: %s" % f)
        if info.get("grid") != (3, 2):
            fails.append("격자 %s(기대 (3, 2))" % (info.get("grid"),))
        if not w or "빈 타일 2개" not in w[0]:
            fails.append("빈 타일 2개를 경고하지 않았습니다: %s" % w)
        # 2) 크기가 안 맞는 시트
        _, f, _ = check(im.crop((0, 0, im.width - 1, im.height)), (T, T), 1, 2, 1)
        if not f or "나뉘지 않습니다" not in f[0]:
            fails.append("격자 불일치를 잡지 못했습니다")
        # 3) 끊기는 반복 타일 (띠 그라데이션)
        _, f, _ = check(im, (T, T), 1, 2, 1, repeat=["3"])
        if not any("이음매 좌우" in s for s in f):
            fails.append("자기 자신과 끊기는 타일을 잡지 못했습니다")
        # 4) 반투명 · 팔레트 밖 · 늘림 테두리 오류
        bad = im.copy()
        x0, y0 = origin(0, 0, T, T, 1, 2, 1)
        bad.putpixel((x0 + 3, y0 + 3), (255, 0, 255, 128))
        bad.putpixel((x0 - 1, y0 + 2), (1, 2, 3, 255))
        _, f, _ = check(bad, (T, T), 1, 2, 1, palette=pal)
        need = ("반투명", "팔레트 밖", "늘림 테두리")
        for n in need:
            if not any(n in s for s in f):
                fails.append("%s 오류를 잡지 못했습니다: %s" % (n, f))
        _, f, _ = check(bad, (T, T), 1, 2, 1, translucent=True)
        if any("반투명" in s for s in f):
            fails.append("반투명 허용 옵션이 듣지 않습니다")
        # 5) 예시 사양 파일을 읽을 수 있어야 합니다
        ex = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pixel-spec-tile.example.json")
        if os.path.exists(ex):
            try:
                s = load_tile_spec(ex)
                if not s["palette"]:
                    fails.append("예시 사양의 팔레트가 비었습니다")
            except Exception as e:  # noqa: BLE001
                fails.append("예시 사양을 읽지 못했습니다: %s" % e)
    return fails


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="타일 번호는 왼쪽 위 0부터 행 순서, 또는 「열:행」으로 적습니다.")
    ap.add_argument("image", nargs="?", help="검사할 타일셋 PNG")
    ap.add_argument("--spec", help="타일 사양 파일(spec/design/pixel-spec-tile.json). 주면 아래 값의 기본이 됩니다")
    ap.add_argument("--tile", help="타일 크기 — 16 또는 16x16")
    ap.add_argument("--margin", type=int, help="시트 바깥 여백(px)")
    ap.add_argument("--spacing", type=int, help="타일 사이 간격(px)")
    ap.add_argument("--extrude", type=int, help="타일마다 가장자리를 복사해 늘린 폭(px)")
    ap.add_argument("--allow-translucent", action="store_true", help="반투명 픽셀을 허용합니다")
    ap.add_argument("--repeat", action="append", default=[], metavar="타일,타일,…",
                    help="서로 이어져야 하는 반복 묶음. 여러 번 줄 수 있습니다")
    ap.add_argument("--seam-ratio", type=float, default=2.0, help="이음매 거리 / 바탕 거리의 허용 배수 (기본 2.0)")
    ap.add_argument("--seam-floor", type=float, default=0.06, help="이음매 거리의 최소 허용값 0~1 (기본 0.06)")
    ap.add_argument("--self-test", action="store_true", help="임시 폴더에서 가짜 타일셋으로 도구를 시험합니다")
    a = ap.parse_args(argv)

    if a.self_test:
        fails = self_test()
        print("[tile] 자기 시험 — %s" % ("통과" if not fails else "실패 %d건" % len(fails)))
        for f in fails:
            print("  실패 · " + f)
        return 1 if fails else 0
    if not a.image:
        ap.error("검사할 이미지를 주세요")

    s = load_tile_spec(a.spec) if a.spec else {
        "tile": None, "margin": 0, "spacing": 0, "extrude": 0, "translucent": False,
        "colors_max": None, "palette": None, "repeat": []}
    if a.tile:
        parts = a.tile.lower().replace("×", "x").split("x")
        s["tile"] = (int(parts[0]), int(parts[-1]))
    if not s["tile"]:
        ap.error("타일 크기를 --tile 또는 --spec으로 주세요")
    for k in ("margin", "spacing", "extrude"):
        if getattr(a, k) is not None:
            s[k] = getattr(a, k)
    repeat = a.repeat or s["repeat"]
    info, fails, warns = check(Image.open(a.image), s["tile"], s["margin"], s["spacing"], s["extrude"],
                               a.allow_translucent or s["translucent"], s["palette"], s["colors_max"],
                               repeat, a.seam_ratio, a.seam_floor)
    report(a.image, info, fails, warns, s["tile"])
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
