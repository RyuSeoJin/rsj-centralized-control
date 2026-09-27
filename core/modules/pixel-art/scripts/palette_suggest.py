# -*- coding: utf-8 -*-
"""캐릭터 그림에서 색을 뽑아 색조별 램프 후보를 만들고 사양 파일 팔레트로 제안합니다

왜 도구인가
----------
  사양 파일의 램프 색이 캐릭터와 맞지 않으면, 변환 도구가 가장 가까운 색을 골라도 피부가 창백해지고
  옷 색이 다른 재질로 바뀝니다. 캐릭터 설정 그림에서 실제로 쓰인 색을 뽑아 램프로 묶으면 그
  어긋남이 줄어듭니다. **결과는 후보입니다** — 램프 이름을 재질로 바꾸고 단계를 다듬은 뒤, 승인을
  받아 사양 파일에 넣습니다(rules/pixel-style.md §팔레트).

어떻게 묶나
----------
  1. 불투명 픽셀만 모아 median cut으로 N색으로 줄입니다. 드물지만 뚜렷한 색(눈동자 등)은 median cut이
     이웃 색에 삼키므로, 가장 가까운 후보와 멀리 떨어진 색을 8개까지 되살립니다.
  2. 가장 어두운 색 하나를 외곽선 후보로 따로 둡니다.
  3. 나머지를 색조 · 채도 평면에서 군집으로 묶습니다(k-means). 명도는 약하게만 봐서, 같은 재질의
     밝은 색과 어두운 색이 한 램프에 모입니다. 피부 · 머리카락 · 가죽처럼 색조가 가까운 재질은
     색조 간격만으로는 갈리지 않기 때문입니다.
  4. 묶음마다 밝은 색부터 늘어놓습니다. 단계가 너무 많으면 명도로 고르게 추립니다.

사용법
------
    python palette_suggest.py 그림.png [--colors 40] [--max-steps 6] [--bg-key auto] [--native]
                              [--spec 사양.json --out-spec 새사양.json]
"""
import argparse
import colorsys
import copy
import json
import math
import sys

from PIL import Image

import pixelize
import spec as specmod

HUE_NAMES = [(15, "RED"), (45, "ORANGE"), (70, "YELLOW"), (160, "GREEN"), (200, "CYAN"),
             (250, "BLUE"), (290, "PURPLE"), (340, "PINK"), (361, "RED")]


def hue_name(h):
    deg = h * 360
    return next(n for lim, n in HUE_NAMES if deg < lim)


def hexs(c):
    return "#%02X%02X%02X" % tuple(c[:3])


def _features(c):
    h, l, s_ = colorsys.rgb_to_hls(*(v / 255 for v in c))
    return (s_ * math.cos(2 * math.pi * h), s_ * math.sin(2 * math.pi * h), 0.35 * l)


def _kmeans(points, k, rounds=30):
    """결정적 k-means — 가장 먼 점부터 씨앗을 고릅니다(실행마다 같은 결과)."""
    seeds = [max(points, key=lambda p: p[2])]
    while len(seeds) < min(k, len(points)):
        seeds.append(max(points, key=lambda p: min(sum((a - b) ** 2 for a, b in zip(p, s)) for s in seeds)))
    for _ in range(rounds):
        groups = [[] for _ in seeds]
        for p in points:
            groups[min(range(len(seeds)), key=lambda i: sum((a - b) ** 2 for a, b in zip(p, seeds[i])))].append(p)
        new = [tuple(sum(v) / len(g) for v in zip(*g)) if g else seeds[i] for i, g in enumerate(groups)]
        if new == seeds:
            break
        seeds = new
    return groups


def suggest(img, colors=40, max_steps=8, groups=None, extra=8, accent_dist=90.0):
    img = img.convert("RGBA")
    opaque = [p[:3] for p in img.getdata() if p[3] >= 128]
    if not opaque:
        raise ValueError("불투명한 픽셀이 없습니다")
    strip = Image.new("RGB", (len(opaque), 1))
    strip.putdata(opaque)
    q = strip.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    idx = sorted(i for _, i in (q.getcolors(colors * 2) or []))
    cols = sorted(set(tuple(pal[i * 3:i * 3 + 3]) for i in idx))
    # 드물지만 뚜렷한 색(눈동자 · 보석 같은 포인트)은 median cut이 이웃 색에 삼킵니다 — 되살립니다
    # 비슷한 색은 한 칸(채널당 16단계)으로 묶어 셉니다 — 평균으로 읽은 입력은 색마다 1픽셀씩이라서
    bins = {}
    for c in opaque:
        k = (c[0] >> 4, c[1] >> 4, c[2] >> 4)
        n, acc = bins.get(k, (0, (0, 0, 0)))
        bins[k] = (n + 1, (acc[0] + c[0], acc[1] + c[1], acc[2] + c[2]))
    freq = {tuple(v // n for v in acc): n for n, acc in bins.values()}
    # 가장 가까운 후보에서 먼 색부터 봅니다. 하나를 되살리면 그 이웃은 더 이상 멀지 않으므로
    # 같은 포인트 색이 여러 개 들어오지 않습니다
    while extra > 0:
        far = max(freq, key=lambda c: min(pixelize._dist(c, p) for p in cols))
        if min(pixelize._dist(far, p) for p in cols) <= accent_dist:
            break
        cols.append(far)
        extra -= 1

    def light(c):
        return colorsys.rgb_to_hls(*(v / 255 for v in c))[1]

    outline = min(cols, key=light)
    rest = [c for c in cols if c != outline]
    feat = {_features(c): c for c in rest}
    k = groups or max(2, round(len(rest) / 5))
    clusters = [sorted({feat[p] for p in g}, key=lambda c: -light(c)) for g in _kmeans(list(feat), k) if g]

    ramps, used = {}, {}
    for g in sorted(clusters, key=lambda g: -len(g)):
        if len(g) > max_steps:
            g = [g[round(i * (len(g) - 1) / (max_steps - 1))] for i in range(max_steps)]
        mid = g[len(g) // 2]
        h, l, s_ = colorsys.rgb_to_hls(*(v / 255 for v in mid))
        base = "NEUTRAL" if s_ < 0.15 else hue_name(h)
        used[base] = used.get(base, 0) + 1
        name = base if used[base] == 1 else "%s_%d" % (base, used[base])
        ramps[name] = [hexs(c) for c in g]
    return {"outline": hexs(outline), "ramps": ramps}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("image")
    ap.add_argument("--colors", type=int, default=40)
    ap.add_argument("--max-steps", type=int, default=8)
    ap.add_argument("--groups", type=int, help="램프 개수 (없으면 색 수 / 5)")
    ap.add_argument("--bg-key", help="단색 배경을 지웁니다 — auto 또는 #RRGGBB")
    ap.add_argument("--native", action="store_true", help="도트 그림을 키운 입력이면 격자대로 읽은 뒤 뽑습니다")
    ap.add_argument("--grid", type=float, help="--native의 격자 간격을 직접 줍니다")
    ap.add_argument("--spec", help="팔레트를 바꿔 끼울 사양 파일")
    ap.add_argument("--out-spec", help="팔레트만 바꾼 사양 파일을 여기 씁니다 (원본은 건드리지 않습니다)")
    a = ap.parse_args(argv)
    img = Image.open(a.image).convert("RGBA")
    if a.bg_key:
        img = pixelize.remove_background(img, a.bg_key)
    if a.native:
        g, ox, oy, _ = pixelize.detect_grid(img, a.grid)
        img = pixelize.sample_native(img, g, ox, oy)
    pal = suggest(img, a.colors, a.max_steps, a.groups)
    n = 1 + sum(len(v) for v in pal["ramps"].values())
    print("팔레트 후보 — 외곽선 1 + 램프 %d개 = %d색" % (len(pal["ramps"]), n))
    print(json.dumps(pal, ensure_ascii=False, indent=1))
    if a.spec and a.out_spec:
        with open(a.spec, encoding="utf-8") as f:
            data = json.load(f)
        new = copy.deepcopy(data)
        new["palette"] = pal
        new.setdefault("limits", {})["colors_max"] = max(n, data.get("limits", {}).get("colors_max", 48))
        specmod.Spec(new, a.out_spec)                           # 형식 검사
        with open(a.out_spec, "w", encoding="utf-8") as f:
            json.dump(new, f, ensure_ascii=False, indent=1)
        print("사양 파일 — %s (팔레트만 바꿈)" % a.out_spec)
    return 0


if __name__ == "__main__":
    sys.exit(main())
