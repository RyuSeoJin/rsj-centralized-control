# -*- coding: utf-8 -*-
"""프로젝트의 픽셀 사양 파일을 읽어 캔버스 · 기준선 · 팔레트 · 슬롯 · 뼈대를 돌려줍니다

왜 사양 파일인가
--------------
  캔버스 크기, 등신, 팔레트 색, 관절 좌표는 프로젝트마다 다른 **값**입니다. 값을 도구에
  박아 두면 모듈이 한 프로젝트의 것이 되고, 다른 프로젝트는 도구를 고쳐야 씁니다.
  그래서 도구는 방법만 갖고, 값은 프로젝트의 사양 파일 한 곳에서 읽습니다
  (rules/pixel-pipeline.md §사양 파일).

팔레트 번호
----------
  0 = 투명, 1 = 외곽선, 2부터 램프를 선언한 순서대로 이어 붙입니다. 램프 안의 단계는
  밝은 쪽이 0입니다. 번호가 이렇게 고정되어 있어야 모든 캐릭터가 같은 팔레트 파일을 쓰고,
  팔레트 교체(색만 바꾸기)가 그림을 건드리지 않습니다.
"""
import io
import json
import os
import sys

# 한글 출력이 콘솔 기본 인코딩(cp949 등)으로 나가면 도구가 출력 도중에 멈춥니다.
# 모든 도구가 이 파일을 불러오므로 여기서 한 번 맞춥니다
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

SCHEMA_VERSION = 1
REQUIRED = ("schema_version", "canvas", "anchors", "palette")


def hex_rgb(h):
    h = h.lstrip("#")
    if len(h) != 6:
        raise ValueError("색은 #RRGGBB로 적습니다: %r" % h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Spec:
    """사양 파일 한 장. 없는 항목은 오류로 멈춥니다 — 조용히 기본값을 쓰지 않습니다."""

    def __init__(self, data, path="(memory)"):
        missing = [k for k in REQUIRED if k not in data]
        if missing:
            raise ValueError("%s: 필수 항목이 없습니다 — %s" % (path, ", ".join(missing)))
        if data["schema_version"] != SCHEMA_VERSION:
            raise ValueError("%s: 모르는 schema_version %r" % (path, data["schema_version"]))
        self.path = path
        self.data = data
        self.width = int(data["canvas"]["width"])
        self.height = int(data["canvas"]["height"])
        self.center_x = float(data.get("center_x", self.width / 2))
        self.anchors = {k: int(v) for k, v in data["anchors"].items()}
        pal = data["palette"]
        self.ramp_names = list(pal["ramps"])
        self.ramps = {n: [hex_rgb(h) for h in pal["ramps"][n]] for n in self.ramp_names}
        self.palette = [(0, 0, 0, 0), hex_rgb(pal["outline"])]
        self._start = {}
        for n in self.ramp_names:
            self._start[n] = len(self.palette)
            self.palette += self.ramps[n]
        self.colors_max = int(data.get("limits", {}).get("colors_max", 48))
        self.slots = list(data.get("slots", []))
        self.bones = {k: (v[0], float(v[1]), float(v[2])) for k, v in data.get("bones", {}).items()}
        self.slot_bone = dict(data.get("slot_bone", {}))
        for s in self.slots:
            if self.bones and self.slot_bone.get(s) not in self.bones:
                raise ValueError("%s: 슬롯 %r의 뼈대가 bones에 없습니다" % (path, s))

    # --- 팔레트 ---------------------------------------------------------
    def c(self, ramp, step):
        """램프 `ramp`의 `step`단계(0 = 가장 밝음) 팔레트 번호."""
        n = len(self.ramps[ramp])
        if not 0 <= step < n:
            raise IndexError("%s 램프는 %d단계입니다: %d" % (ramp, n, step))
        return self._start[ramp] + step

    def ramp_of(self, idx):
        """팔레트 번호의 (램프 이름, 단계). 투명 · 외곽선이면 None."""
        for n in self.ramp_names:
            s = self._start[n]
            if s <= idx < s + len(self.ramps[n]):
                return n, idx - s
        return None

    def darkest(self, ramp):
        return self.c(ramp, len(self.ramps[ramp]) - 1)

    def darken(self, idx, n=1):
        r = self.ramp_of(idx)
        if r is None:
            return idx
        return self.c(r[0], min(len(self.ramps[r[0]]) - 1, r[1] + n))

    def rgb_index(self):
        """RGB → 팔레트 번호 사전 (외곽선 포함, 투명 제외)."""
        return {tuple(p[:3]): i for i, p in enumerate(self.palette) if i > 0}


def load(path):
    with io.open(path, encoding="utf-8") as f:
        return Spec(json.load(f), os.path.abspath(path))
