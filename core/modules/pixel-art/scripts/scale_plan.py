# -*- coding: utf-8 -*-
"""기준 해상도를 대상 화면마다 몇 배로 키우고 띠가 얼마나 남는지 표로 냅니다

왜 필요한가 (rules/pixel-render.md §1 · §2)
---------------------------------------
  픽셀 아트는 정수배로만 키웁니다. 그러면 화면마다 남는 자리(레터박스 · 필러박스)가 생기고,
  그 크기는 기준 해상도를 무엇으로 고르느냐에 따라 크게 달라집니다. 화면 목록이 길어지면
  손으로 나눠 보기 어려우므로, 배율 · 실제 그림 크기 · 띠 · 빈 면적 비율을 한 번에 계산합니다.

계산
----
  배율        = min(화면 폭 // 기준 폭, 화면 높이 // 기준 높이)   (1보다 작으면 0 — 「안 들어감」)
  그림 크기    = 기준 × 배율
  띠          = 화면 − 그림 크기 (좌우 · 위아래 합)
  빈 면적      = 1 − 그림 면적 ÷ 화면 면적
  expand 모드  = 같은 배율에서 남는 칸만큼 월드를 더 보여 줍니다. 더 보이는 칸 = (화면 // 배율) − 기준,
                 그래도 남는 화면 픽셀(화면 % 배율)만 띠가 됩니다

사양 파일의 render 절 (없으면 인자로 줍니다)
-----------------------------------------
    "render": {
      "reference": [384, 216],
      "candidates": [[320, 180], [384, 216], [480, 270]],
      "targets": [[1920, 1080], [2560, 1440], [1280, 800], [2532, 1170]],
      "scale_mode": "letterbox",        # letterbox | expand | fractional
      "max_margin": 0.15                # letterbox: 빈 면적 한도 · expand: 더 보이는 범위 한도
    }

사용법
------
    python scale_plan.py --spec spec/design/pixel-spec-field.json
    python scale_plan.py --ref 384x216 --target 1920x1080 2560x1440 1280x800 2532x1170
    python scale_plan.py --ref 384x216 --target 1920x1080 2532x1170 --search
    python scale_plan.py --self-test

  종료 코드: 0 = 모든 화면이 한도 안, 1 = 「넘침」 · 「안 들어감」 화면이 있음, 2 = 입력 오류
"""
import argparse
import io
import json
import os
import sys
import tempfile

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

MODES = ("letterbox", "expand", "fractional")
DEFAULT_MAX_MARGIN = 0.15


def size(text):
    """'384x216' 또는 [384, 216] → (384, 216)."""
    try:
        if isinstance(text, (list, tuple)):
            w, h = text
        else:
            w, h = str(text).lower().replace("×", "x").split("x")
        w, h = int(w), int(h)
    except ValueError:
        raise ValueError("크기는 폭x높이로 적습니다(예: 384x216): %r" % (text,))
    if w <= 0 or h <= 0:
        raise ValueError("크기는 양의 정수입니다: %r" % (text,))
    return w, h


def fit(ref, screen, mode="letterbox"):
    """기준 해상도 하나를 화면 하나에 올린 결과."""
    (rw, rh), (sw, sh) = ref, screen
    scale = min(sw // rw, sh // rh)
    r = {"ref": ref, "screen": screen, "scale": scale}
    if scale < 1:
        r.update(image=(0, 0), bars=(sw, sh), extra=(0, 0), margin=1.0)
        return r
    if mode == "expand":
        vw, vh = sw // scale, sh // scale          # 보이는 칸 수 (기준보다 크거나 같음)
        image = (vw * scale, vh * scale)
        extra = (vw - rw, vh - rh)
    else:
        image = (rw * scale, rh * scale)
        extra = (0, 0)
    if mode == "fractional":
        f = min(sw / rw, sh / rh)
        image = (round(rw * f), round(rh * f))
        r["scale"] = round(f, 3)
    bars = (sw - image[0], sh - image[1])
    r.update(image=image, bars=bars, extra=extra,
             margin=1 - (image[0] * image[1]) / float(sw * sh))
    return r


def cost(r, mode):
    """비교 기준 — letterbox · fractional은 빈 면적, expand는 기준보다 더 보이는 범위의 비율(가로 · 세로 중 큰 쪽).

    expand는 띠가 거의 없어 빈 면적으로는 후보가 갈리지 않습니다. 대신 화면마다 보이는 월드 범위가
    달라지므로(rules/pixel-render.md §2-2), 더 보이는 범위가 작을수록 좋은 후보로 봅니다.
    """
    if mode == "expand":
        (rw, rh), (ew, eh) = r["ref"], r["extra"]
        return max(ew / float(rw), eh / float(rh))
    return r["margin"]


def best(cands, screen, mode):
    """후보 가운데 이 화면에서 비교 기준이 가장 작은 것 (같으면 배율이 작은 쪽 — 도트가 큰 쪽)."""
    rs = [fit(c, screen, mode) for c in cands]
    rs = [r for r in rs if r["scale"] >= 1]
    return min(rs, key=lambda r: (round(cost(r, mode), 4), r["scale"])) if rs else None


def search_candidates(ref, targets, spread=0.3, max_scale=12):
    """탐색 후보 두 갈래를 만듭니다.

    ① 대상 화면을 정수로 나눠 떨어지는 크기 가운데 기준 높이 ±spread 안의 것 — 기준 해상도 하나로 갈 때
    ② 기준 높이는 그대로 두고 폭만 그 화면에 맞춘 것 — 화면비별로 기준 해상도를 여러 개 둘 때
       (rules/pixel-render.md §2-3, 도트 크기와 보이는 높이가 모든 화면에서 같습니다)
    """
    lo, hi = ref[1] * (1 - spread), ref[1] * (1 + spread)
    out = set()
    for sw, sh in targets:
        for s in range(1, max_scale + 1):
            if sw % s == 0 and sh % s == 0 and lo <= sh // s <= hi:
                out.add((sw // s, sh // s))
        s = sh // ref[1]
        if s >= 1:
            out.add((sw // s, ref[1]))
    out.add(tuple(ref))
    return sorted(out, key=lambda c: (c[1], c[0]))


def rank(cands, targets, mode):
    """후보마다 전체 화면의 비교 기준 평균 · 최악을 내고 평균 순으로 정렬합니다."""
    rows = []
    for c in cands:
        rs = [fit(c, t, mode) for t in targets]
        if any(r["scale"] < 1 for r in rs):
            continue
        ms = [cost(r, mode) for r in rs]
        rows.append({"ref": c, "mean": sum(ms) / len(ms), "worst": max(ms),
                     "scales": [r["scale"] for r in rs]})
    return sorted(rows, key=lambda r: (round(r["mean"], 4), round(r["worst"], 4)))


def plan(render):
    """render 절(사전) → 표에 쓸 결과. 사양 파일 · 인자 어느 쪽에서 와도 같은 형식입니다."""
    if "reference" not in render or not render.get("targets"):
        raise ValueError("render에 reference와 targets가 필요합니다")
    mode = render.get("scale_mode", "letterbox")
    if mode not in MODES:
        raise ValueError("scale_mode는 %s 중 하나입니다: %r" % (" · ".join(MODES), mode))
    ref = size(render["reference"])
    targets = [size(t) for t in render["targets"]]
    cands = [ref]
    for c in render.get("candidates", []):
        if size(c) not in cands:
            cands.append(size(c))
    limit = float(render.get("max_margin", DEFAULT_MAX_MARGIN))
    rows = []
    for t in targets:
        r = fit(ref, t, mode)
        alt = best(cands, t, mode) if len(cands) > 1 else None
        # 1%p도 나아지지 않는 대안은 적지 않습니다 — 표가 의미 없는 대안으로 채워집니다
        if alt and (alt["ref"] == ref or cost(r, mode) - cost(alt, mode) < 0.01):
            alt = None
        # 화면비별 기준(§2-3): 높이 칸 수 · 배율은 그대로 두고 폭만 이 화면에 맞춥니다
        same_h = None
        if r["scale"] >= 1 and mode != "fractional" and t[0] // int(r["scale"]) != ref[0]:
            same_h = fit((t[0] // int(r["scale"]), ref[1]), t, mode)
        rows.append({"fit": r, "alt": alt, "same_h": same_h, "over": cost(r, mode) > limit})
    return {"ref": ref, "mode": mode, "limit": limit, "rows": rows,
            "rank": rank(cands, targets, mode) if len(cands) > 1 else []}


def fmt_size(s):
    return "%d×%d" % s


def render_table(res):
    what = "더 보이는 범위" if res["mode"] == "expand" else "빈 면적"
    lines = ["기준 해상도 %s · 방식 %s · %s 한도 %.0f%%" % (fmt_size(res["ref"]), res["mode"], what,
                                                    res["limit"] * 100), ""]
    if res["mode"] == "fractional":
        lines.append("⚠️ fractional은 소수배라 도트 크기가 들쭉날쭉합니다(rules/pixel-render.md §2-1). 비교용으로만 봅니다.")
        lines.append("")
    head = ("| 화면 | 배율 | 그림 크기 | 띠 (좌우 합 · 위아래 합) | 더 보이는 칸 | 빈 면적 | 판정 | 대안 (%s) "
            "| 화면비별 기준 (높이 고정 · 빈 면적) |" % what)
    lines += [head, "|---|---|---|---|---|---|---|---|---|"]
    for row in res["rows"]:
        r, alt = row["fit"], row["alt"]
        if r["scale"] < 1:
            verdict, scale = "안 들어감", "—"
        else:
            verdict, scale = ("넘침" if row["over"] else "좋음"), "×%s" % r["scale"]
        extra = "%d · %d" % r["extra"] if res["mode"] == "expand" else "—"
        alt_s = ("%s ×%s (%.1f%%)" % (fmt_size(alt["ref"]), alt["scale"], cost(alt, res["mode"]) * 100)
                 if alt else "—")
        sh = row["same_h"]
        sh_s = "%s ×%s (%.1f%%)" % (fmt_size(sh["ref"]), sh["scale"], sh["margin"] * 100) if sh else "—"
        lines.append("| %s | %s | %s | %d · %d | %s | %.1f%% | %s | %s | %s |" % (
            fmt_size(r["screen"]), scale, fmt_size(r["image"]), r["bars"][0], r["bars"][1], extra,
            r["margin"] * 100, verdict, alt_s, sh_s))
    if res["rank"]:
        lines += ["", "후보 순위 (전체 화면 %s 평균이 작은 순)" % what, "",
                  "| 순위 | 기준 해상도 | 평균 | 최악 | 화면별 배율 |", "|---|---|---|---|---|"]
        for i, r in enumerate(res["rank"][:10], 1):
            mark = " ← 지금" if r["ref"] == res["ref"] else ""
            lines.append("| %d | %s%s | %.1f%% | %.1f%% | %s |" % (
                i, fmt_size(r["ref"]), mark, r["mean"] * 100, r["worst"] * 100,
                " · ".join("×%s" % s for s in r["scales"])))
    return "\n".join(lines)


def load_render(path):
    with io.open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "render" not in data:
        raise ValueError("%s: render 절이 없습니다 — rules/pixel-render.md §2를 보고 적거나 --ref · --target으로 줍니다" % path)
    return dict(data["render"])


def self_test():
    """알려진 값으로 계산을 확인하고, 임시 폴더에 사양 파일을 써서 읽기까지 돌려 봅니다."""
    fails = []
    r = fit((384, 216), (1920, 1080))
    if (r["scale"], r["image"], r["bars"]) != (5, (1920, 1080), (0, 0)):
        fails.append("384×216 → 1920×1080: %s" % r)
    r = fit((384, 216), (2532, 1170))
    if (r["scale"], r["image"], r["bars"]) != (5, (1920, 1080), (612, 90)):
        fails.append("384×216 → 2532×1170: %s" % r)
    r = fit((384, 216), (2532, 1170), "expand")
    if (r["extra"], r["bars"]) != ((122, 18), (2, 0)):
        fails.append("expand 384×216 → 2532×1170: %s" % r)
    if fit((640, 360), (320, 200))["scale"] != 0:
        fails.append("화면보다 큰 기준이 들어간다고 나옵니다")
    found = search_candidates((384, 216), [(1920, 1080), (2560, 1440), (2532, 1170)])
    if (320, 180) not in found or (506, 216) not in found:
        fails.append("탐색 후보에 320×180(나눠 떨어짐) · 506×216(높이 고정)이 없습니다: %s" % found)
    with tempfile.TemporaryDirectory() as tmp:
        p = os.path.join(tmp, "pixel-spec-test.json")
        with io.open(p, "w", encoding="utf-8") as f:
            json.dump({"schema_version": 1, "render": {
                "reference": [384, 216], "candidates": [[320, 180], [384, 240]],
                "targets": [[1920, 1080], [1280, 800]], "max_margin": 0.1}}, f)
        res = plan(load_render(p))
        # 1280×800: 384×216 ×3은 빈 면적 27%(넘침), 320×180 ×4는 10%로 가장 작습니다
        if not res["rows"][1]["over"] or res["rows"][1]["alt"]["ref"] != (320, 180):
            fails.append("1280×800의 대안이 320×180이 아닙니다: %s" % res["rows"][1])
        if res["rows"][0]["alt"] is not None:
            fails.append("빈 면적 0%인 1920×1080에 대안이 붙었습니다")
    if plan({"reference": [384, 216], "targets": [[2532, 1170]]})["rows"][0]["same_h"]["ref"] != (506, 216):
        fails.append("2532×1170의 화면비별 기준이 506×216이 아닙니다")
    r = fit((384, 216), (2532, 1170), "expand")
    if abs(cost(r, "expand") - 122 / 384.0) > 1e-9:
        fails.append("expand 비교 기준이 더 보이는 가로 비율이 아닙니다")
        if "|" not in render_table(res):
            fails.append("표가 비었습니다")
    for f in fails:
        print("실패:", f)
    print("자기 시험 %s" % ("통과" if not fails else "실패 %d건" % len(fails)))
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="기준 해상도를 대상 화면마다 정수배로 키웠을 때의 배율 · 띠 · 빈 면적을 표로 냅니다 (rules/pixel-render.md §2).")
    ap.add_argument("--spec", help="사양 파일 — render 절을 읽습니다")
    ap.add_argument("--ref", help="기준 해상도, 예: 384x216 (사양보다 우선)")
    ap.add_argument("--target", nargs="+", help="대상 화면들, 예: 1920x1080 2532x1170 (사양보다 우선)")
    ap.add_argument("--candidates", nargs="+", help="비교할 기준 해상도 후보들 (사양보다 우선)")
    ap.add_argument("--mode", choices=MODES, help="남는 자리 처리 — letterbox(띠) · expand(더 보여 줌) · fractional(소수배, 비교용)")
    ap.add_argument("--max-margin", type=float, help="이 비율을 넘는 빈 면적은 「넘침」 (기본 0.15)")
    ap.add_argument("--search", action="store_true",
                    help="대상 화면을 정수로 나눠 떨어지는 크기와, 기준 높이를 고정하고 폭만 화면에 맞춘 크기를 후보로 더해 순위를 냅니다")
    ap.add_argument("--json", action="store_true", help="표 대신 JSON으로 냅니다")
    ap.add_argument("--self-test", action="store_true", help="알려진 값과 임시 사양 파일로 도구를 시험합니다")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()
    render = load_render(a.spec) if a.spec else {}
    if a.ref:
        render["reference"] = a.ref
    if a.target:
        render["targets"] = a.target
    if a.candidates:
        render["candidates"] = a.candidates
    if a.mode:
        render["scale_mode"] = a.mode
    if a.max_margin is not None:
        render["max_margin"] = a.max_margin
    try:
        if a.search:
            if "reference" not in render or not render.get("targets"):
                raise ValueError("--search에는 기준 해상도와 대상 화면이 필요합니다")
            found = search_candidates(size(render["reference"]), [size(t) for t in render["targets"]])
            render["candidates"] = [list(c) for c in found] + list(render.get("candidates", []))
        res = plan(render)
    except ValueError as e:
        print("오류:", e, file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2, default=list))
    else:
        print(render_table(res))
    return 1 if any(r["over"] or r["fit"]["scale"] < 1 for r in res["rows"]) else 0


if __name__ == "__main__":
    sys.exit(main())
