# -*- coding: utf-8 -*-
"""레이어 캔버스 · 외곽선 · 셀아웃 · 접촉 그림자 · Aseprite Lua 내보내기를 한곳에 모읍니다

손으로 그린 그림을 다듬든 도형으로 초안을 찍든, 마지막 단계(외곽선 → 안쪽 선 → 접촉 그림자 →
Aseprite 파일)는 같습니다. 그 단계를 캐릭터마다 다시 쓰면 캐릭터마다 선 처리가 갈리므로
여기 한 벌만 둡니다 (rules/pixel-style.md §외곽선).

팔레트 번호 규약은 spec.py를 따릅니다 — 0 = 투명, 1 = 외곽선.
"""
import os

from PIL import Image, ImageDraw

OUT = 1
NEIGH4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


class Layer:
    """팔레트 번호로 칠하는 한 장. outline 표시는 외곽선 처리 뒤 안쪽 선을 가를 때 씁니다."""

    def __init__(self, name, width, height):
        self.name = name
        self.w, self.h = width, height
        self.px = [[0] * width for _ in range(height)]
        self.outline = [[False] * width for _ in range(height)]

    def inside(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def get(self, x, y):
        return self.px[y][x] if self.inside(x, y) else 0

    def set(self, x, y, c):
        if self.inside(x, y):
            self.px[y][x] = c

    def filled(self, x, y):
        return self.get(x, y) != 0

    def empty(self):
        return not any(v for row in self.px for v in row)

    # --- 도형 ------------------------------------------------------------
    def poly(self, pts, c):
        m = Image.new("L", (self.w, self.h), 0)
        ImageDraw.Draw(m).polygon(pts, fill=1, outline=1)
        for y in range(self.h):
            for x in range(self.w):
                if m.getpixel((x, y)):
                    self.px[y][x] = c

    def ellipse(self, cx, cy, rx, ry, c):
        for y in range(self.h):
            for x in range(self.w):
                if ((x + .5 - cx) / rx) ** 2 + ((y + .5 - cy) / ry) ** 2 <= 1:
                    self.px[y][x] = c

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def pixels(self, pts, c):
        for x, y in pts:
            self.set(x, y, c)

    # --- 외곽선 ----------------------------------------------------------
    def add_outline(self):
        """칠한 영역 바깥 4방향 이웃에 1px 외곽선을 둡니다 (대각선은 비워 두어 두께가 뭉치지 않게)."""
        src = [row[:] for row in self.px]
        for y in range(self.h):
            for x in range(self.w):
                if src[y][x]:
                    continue
                for dx, dy in NEIGH4:
                    nx, ny = x + dx, y + dy
                    if self.inside(nx, ny) and src[ny][nx]:
                        self.px[y][x] = OUT
                        self.outline[y][x] = True
                        break


def from_image(name, img, spec):
    """RGBA 그림을 팔레트 번호 레이어로 바꿉니다. 팔레트에 없는 색이 있으면 멈춥니다."""
    img = img.convert("RGBA")
    lut = spec.rgb_index()
    lay = Layer(name, img.width, img.height)
    bad = set()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = img.getpixel((x, y))
            if a < 128:
                continue
            i = lut.get((r, g, b))
            if i is None:
                bad.add((r, g, b))
            else:
                lay.px[y][x] = i
    if bad:
        raise ValueError("팔레트 밖 색 %d개 — pixelize.py로 먼저 팔레트에 맞춥니다: %s"
                         % (len(bad), sorted(bad)[:5]))
    return lay


def composite(layers, order):
    w, h = layers[order[0]].w, layers[order[0]].h
    comp = [[0] * w for _ in range(h)]
    for n in order:
        for y in range(h):
            for x in range(w):
                if layers[n].px[y][x]:
                    comp[y][x] = layers[n].px[y][x]
    return comp


def finalize(layers, order, spec, soft_same_material=True, contact_shadow=True):
    """외곽선 → 셀아웃(안쪽 선) → 접촉 그림자를 규칙대로 적용합니다.

    - 실루엣 바깥에 닿는 외곽선은 외곽선 색(1)으로 둡니다.
    - 실루엣 안쪽의 선은 그 파츠 재질의 가장 어두운 단계로 바꿉니다. 아래에 같은 재질이
      있으면 한 단계 밝게 둡니다 — 소매와 옷처럼 같은 재질끼리는 선이 튀지 않게.
    - 위 파츠 바로 아래 1px은 한 단계 어둡게 합니다 (접촉 그림자).
    """
    for n in order:
        layers[n].add_outline()
    comp = composite(layers, order)
    w, h = len(comp[0]), len(comp)
    for i, n in enumerate(order):
        lay = layers[n]
        below = composite(layers, order[:i]) if i else [[0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                if not lay.outline[y][x]:
                    continue
                if any(not (0 <= x + dx < w and 0 <= y + dy < h) or comp[y + dy][x + dx] == 0
                       for dx, dy in NEIGH4):
                    continue
                own = next((lay.px[y + dy][x + dx] for dx, dy in NEIGH4
                            if lay.inside(x + dx, y + dy) and lay.px[y + dy][x + dx] > 1
                            and not lay.outline[y + dy][x + dx]), None)
                r = spec.ramp_of(own) if own else None
                if r is None:
                    continue
                under = spec.ramp_of(below[y][x])
                deep = spec.darkest(r[0])
                lay.px[y][x] = spec.darken(deep, -1) if (soft_same_material and under and under[0] == r[0]) \
                    else deep
    if contact_shadow:
        for i, n in enumerate(order):
            above = composite(layers, order[i + 1:]) if i + 1 < len(order) else None
            if above is None:
                continue
            lay = layers[n]
            for y in range(1, h):
                for x in range(w):
                    if lay.px[y][x] > 1 and not lay.outline[y][x] and above[y - 1][x] and not above[y][x]:
                        lay.px[y][x] = spec.darken(lay.px[y][x])


def write_lua(layers, order, spec, lua_path, ase_path, png_path):
    """레이어를 그대로 담은 .aseprite와 합친 PNG를 만드는 Lua를 씁니다 (Aseprite 배치 모드로 실행)."""
    w, h = spec.width, spec.height
    lines = ["local spr = Sprite(%d, %d, ColorMode.INDEXED)" % (w, h),
             "local pal = Palette(%d)" % len(spec.palette)]
    for i, c in enumerate(spec.palette):
        r, g, b = c[:3]
        a = c[3] if len(c) == 4 else 255
        lines.append("pal:setColor(%d, Color{r=%d,g=%d,b=%d,a=%d})" % (i, r, g, b, a))
    lines += ["spr:setPalette(pal)", "spr.transparentColor = 0",
              "local function fill(layer, data)",
              "  local img = Image(%d, %d, ColorMode.INDEXED)" % (w, h),
              "  img:clear(0)",
              "  for i = 1, #data // 2 do",
              "    local v = tonumber(data:sub(2 * i - 1, 2 * i), 16)",
              "    if v > 0 then img:putPixel((i - 1) %% %d, (i - 1) // %d, v) end" % (w, w),
              "  end",
              "  spr:newCel(layer, 1, img, Point(0, 0))",
              "end"]
    if len(spec.palette) > 256:
        raise ValueError("Indexed 팔레트는 256색까지입니다")
    first = True
    for i, n in enumerate(order):
        if layers[n].empty():
            continue                                   # 빈 선택 슬롯은 레이어로 만들지 않는다
        # 픽셀마다 16진 두 글자: 따옴표 · 역슬래시 · 괄호가 한 글자도 섞이지 않아 문자열이 깨지지 않는다
        data = "".join("%02x" % v for row in layers[n].px for v in row)
        lines.append(("local l%d = spr.layers[1]" if first else "local l%d = spr:newLayer()") % i)
        lines.append('l%d.name = "%s"' % (i, n))
        lines.append('fill(l%d, "%s")' % (i, data))
        first = False
    lines.append("spr:saveAs([[%s]])" % os.path.abspath(ase_path).replace("\\", "/"))
    lines.append("spr:saveCopyAs([[%s]])" % os.path.abspath(png_path).replace("\\", "/"))
    with open(lua_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
