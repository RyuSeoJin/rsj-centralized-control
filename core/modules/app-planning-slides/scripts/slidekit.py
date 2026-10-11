# -*- coding: utf-8 -*-
"""슬라이드 부품 — 글꼴 · 색 · 텍스트 상자 · 도형 · 선 · 표 · 덱 틀 · 와이어프레임

패턴(patterns.py)과 덱 조립(build_slides.py)이 모두 이 부품만으로 그립니다. 색 · 글꼴 · 여백을
한 자리에 두어야 장마다 모양이 갈리지 않습니다. Google Slides 변환 규칙(글꼴 하나 · 단색 ·
그림자 없음)도 여기서 지킵니다 — 규칙 정본은 ../rules/planning-slides.md §6입니다.
"""
import os
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

#: Google Slides에 있는 글꼴. 다른 글꼴은 변환 때 바뀌어 줄바꿈이 어긋납니다
FONT = "Noto Sans KR"
ALLOWED_FONTS = {FONT}

#: 색 — 짙은 남색 잉크와 주홍 강조 하나. 와이어프레임은 회색 단색만 씁니다
INK = "22313F"
SUB = "5B6770"
MUTED = "8A949C"
ACCENT = "E4572E"
TINT = "F2F4F5"
LINE = "D5DADE"
GRID = "BAC4CD"                # 칸 테두리 — 표 · 정보 띠 · 격자가 모두 이 한 색을 씁니다
#: 표 색 — 테두리는 바깥 · 안쪽 · 머리줄 · 본문 모두 한 색 · 한 두께입니다. 선이 갈리면 이음새가 어긋나고
#: 머리줄만 떠 보입니다. 구분은 선이 아니라 칸 채우기(머리줄 · 줄무늬)가 맡습니다
TABLE = {"line": GRID, "width": 0.75,
         "head_fill": "E6EBF0", "head_text": INK,
         "body_fill": "FFFFFF", "zebra": "F8FAFB", "body_text": INK}
WHITE = "FFFFFF"
#: 상태색 — 색만으로 뜻을 전하지 않습니다. 배지는 항상 글자와 함께 씁니다
STATUS = {"NEW": ("신규", "2F7D59"), "UPDATE": ("수정", "B7791F"), "DELETE": ("삭제", "9B2C2C"),
          "TODO": ("대기", "8A949C"), "DOING": ("진행", "2B6CB0"), "DONE": ("완료", "2F7D59"),
          "HOLD": ("보류", "B7791F")}
WF_FRAME = "3D4851"
WF_FILL = {"header": "C9CED3", "nav": "C9CED3", "tab": "DDE1E4", "button": "9AA3AA",
           "input": "FFFFFF", "list": "F1F3F4", "image": "E3E6E8", "text": "F7F8F9",
           "card": "ECEEF0", "banner": "D3D8DC", "other": "ECEEF0"}
WF_DEFAULT_H = {"header": 8, "nav": 9, "tab": 7, "button": 7, "input": 7, "list": 28,
                "image": 24, "text": 9, "card": 16, "banner": 13, "other": 10}
REGION_TYPES = tuple(WF_FILL)

#: 화면설계서에서 빠지면 안 되는 예외 — 비어 있으면 `?`로 찍어 미결로 드러냅니다
STANDARD_EXCEPTIONS = ("비로그인", "데이터 없음", "네트워크 오류", "잘못된 입력")

SW, SH = 13.333, 7.5          # 16:9 와이드
MX = 0.6                      # 좌우 여백
UNKNOWN = "?"


# ── 값 ────────────────────────────────────────────────────────────────

def v(x):
    """빈 값은 `?` — 추측으로 채우지 않습니다."""
    if x is None:
        return UNKNOWN
    if isinstance(x, (list, tuple)):
        return ", ".join(str(i) for i in x) if x else UNKNOWN
    s = str(x).strip()
    return s if s else UNKNOWN


def lst(x):
    return [str(i) for i in x if str(i).strip()] if isinstance(x, list) else ([str(x)] if x else [])


# ── 그리기 거들기 ─────────────────────────────────────────────────────

def _rgb(h):
    return RGBColor.from_string(h)


def _font(run, size, bold=False, color=INK):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = _rgb(color)
    f.name = FONT
    # 한글은 동아시아 글꼴 자리를 따로 읽습니다 — latin만 정하면 Google에서 다른 글꼴로 뜹니다
    rpr = run._r.get_or_add_rPr()
    for tag in ("a:ea", "a:cs"):
        el = rpr.find(qn(tag))
        if el is None:
            el = rpr.makeelement(qn(tag), {})
            rpr.append(el)
        el.set("typeface", FONT)


def _plain(shape):
    """테마 스타일(그림자 등 효과 참조)을 떼어 냅니다. 색은 직접 정합니다."""
    st = shape._element.find(qn("p:style"))
    if st is not None:
        shape._element.remove(st)


#: 글머리 기호 — 단계마다 **모양 자체를** 바꿔 깊이를 보입니다(1단 ■ · 2단 ◆ · 3단 ● · 4단 –).
#: 채움만 다른 짝(◆ · ◇, ■ · □)은 작게 찍히면 구분되지 않아 쓰지 않습니다
BULLET_MARKS = ("■", "◆", "●", "–")
#: 기호마다 글자 대비 크기 — 대시는 가늘어 같은 비율이면 묻히므로 크게 찍습니다
BULLET_SCALE = {"–": 1.0}
#: 소제목 표식 — 카드 안의 소제목 앞에 붙여 「아래가 이 묶음」임을 보입니다(토글처럼)
HEAD_MARK = "▼"
#: 토글 들여쓰기 — ▼ 뒤 글자와 소제목 아래 내용이 모두 이만큼 들어가 한 선에 맞습니다
TOGGLE_STEP = 0.3
#: Noto Sans KR의 한 줄 높이(글자 크기 대비). 첫 줄을 번호 표식 가운데에 맞출 때 씁니다
LINE_H = 1.45
TEXT_MARGIN = 0.02


def line_height(size):
    """글자 크기(pt)의 한 줄 높이(in)."""
    return size * LINE_H / 72.0


def first_line_top(center_y, size):
    """첫 줄의 세로 중심이 center_y에 오도록 하는 텍스트 상자의 위쪽 y.

    번호 표식(원 · 큰 숫자) 오른쪽에 글을 둘 때 씁니다 — 위를 맞추면 글이 표식보다 높아 보입니다.
    """
    return center_y - line_height(size) / 2.0 - TEXT_MARGIN


def bullets(items, level=0):
    """글머리 목록 → text()의 문단 목록. 항목 다음에 목록이 오면 그 항목의 하위(다음 단)입니다."""
    out = []
    for it in items if isinstance(items, list) else ([items] if items else []):
        if isinstance(it, list):
            out += bullets(it, min(level + 1, len(BULLET_MARKS) - 1))
        elif str(it).strip():
            out.append((str(it), {"bullet": level}))
    return out


def _hang(para, size, level):
    """내어쓰기 — 둘째 줄부터 글자 시작선이 첫 줄 글자와 맞습니다."""
    step = size * 1.7 / 72.0
    pPr = para._p.get_or_add_pPr()
    pPr.set("marL", str(int(Inches(step * (level + 1)))))
    pPr.set("indent", str(int(-Inches(step))))


def text(slide, x, y, w, h, paras, size=14, bold=False, color=INK, align="l",
         anchor="t", spacing=4, name=None):
    """paras: 문자열 · (문자열, {size, bold, color, bullet, head}) 목록.

    bullet은 단계(0부터, True는 0)이며 BULLET_MARKS의 기호와 내어쓰기가 붙습니다.
    head가 참이면 HEAD_MARK를 앞에 붙인 소제목입니다.
    """
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.04)
    tf.margin_top = tf.margin_bottom = Inches(TEXT_MARGIN)
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE, "b": MSO_ANCHOR.BOTTOM}[anchor]
    if isinstance(paras, str):
        paras = [paras]
    for i, p in enumerate(paras):
        s, o = (p, {}) if isinstance(p, str) else p
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER, "r": PP_ALIGN.RIGHT}[align]
        para.space_after = Pt(spacing)
        sz, c = o.get("size", size), o.get("color", color)
        lvl = o.get("bullet")
        if lvl is not None and lvl is not False:
            lvl = 0 if lvl is True else int(lvl)
            _hang(para, sz, lvl)
            m = para.add_run()
            m.text = BULLET_MARKS[min(lvl, len(BULLET_MARKS) - 1)] + "	"
            mark = m.text[0]
            _font(m, sz * BULLET_SCALE.get(mark, 0.72), False, ACCENT if lvl == 0 else MUTED)
        elif o.get("head"):
            # 글머리처럼 내어쓰기 — 소제목 글자가 TOGGLE_STEP에서 시작해, 아래 내용과 같은 선에 섭니다
            pPr = para._p.get_or_add_pPr()
            pPr.set("marL", str(int(Inches(TOGGLE_STEP))))
            pPr.set("indent", str(int(-Inches(TOGGLE_STEP))))
            m = para.add_run()
            m.text = HEAD_MARK + "	"
            _font(m, sz * 0.62, False, c)
        r = para.add_run()
        r.text = s
        _font(r, sz, o.get("bold", bold), c)
    return tb


def subhead(slide, x, y, w, label, size=15, color=ACCENT):
    """카드 안 소제목 — ▼ 표식 + 굵은 글자. 아래 내용은 x + TOGGLE_STEP에서 시작합니다(토글처럼)."""
    return text(slide, x, y, w, line_height(size) + 0.1, [(label, {"head": True})], size=size, bold=True,
                color=color)


#: 도형 이름 — 순서도 기호도 여기서 고릅니다(시작·종료 capsule · 처리 rect · 입출력 para · 분기 diamond)
SHAPES = {"rect": MSO_SHAPE.RECTANGLE, "round": MSO_SHAPE.ROUNDED_RECTANGLE,
          "capsule": MSO_SHAPE.ROUNDED_RECTANGLE, "diamond": MSO_SHAPE.DIAMOND,
          "para": MSO_SHAPE.PARALLELOGRAM, "oval": MSO_SHAPE.OVAL, "chevron": MSO_SHAPE.CHEVRON,
          "pentagon": MSO_SHAPE.PENTAGON}


def box(slide, x, y, w, h, fill=None, line=None, round_=False, label=None, size=11,
        color=INK, bold=False, align="c", anchor="m", width=0.75, name=None, shape=None, dash=False):
    kind = shape or ("round" if round_ else "rect")
    shp = slide.shapes.add_shape(SHAPES[kind], Inches(x), Inches(y), Inches(w), Inches(h))
    _plain(shp)
    if name:
        shp.name = name
    if kind == "capsule":
        shp.adjustments[0] = 0.5
    elif kind == "round":
        # 모서리 반경은 크기와 상관없이 0.12in — 비율로 두면 큰 카드가 알약처럼 됩니다
        shp.adjustments[0] = min(0.5, 0.12 / max(0.01, min(w, h)))
    if fill:
        shp.fill.solid()
        shp.fill.fore_color.rgb = _rgb(fill)
    else:
        shp.fill.background()
    if line:
        shp.line.color.rgb = _rgb(line)
        shp.line.width = Pt(width)
        if dash:
            shp.line.dash_style = MSO_LINE.DASH
    else:
        shp.line.fill.background()
    tf = shp.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = Inches(0.05)
    tf.margin_top = tf.margin_bottom = Inches(0.02)
    tf.vertical_anchor = {"t": MSO_ANCHOR.TOP, "m": MSO_ANCHOR.MIDDLE}[anchor]
    if label is not None:
        p = tf.paragraphs[0]
        p.alignment = {"l": PP_ALIGN.LEFT, "c": PP_ALIGN.CENTER}[align]
        r = p.add_run()
        r.text = label
        _font(r, size, bold, color)
    return shp


def circle(slide, x, y, d, fill, label, size=9, color=WHITE):
    shp = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
    _plain(shp)
    shp.fill.solid()
    shp.fill.fore_color.rgb = _rgb(fill)
    shp.line.fill.background()
    tf = shp.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    _font(r, size, True, color)
    return shp


def line(slide, x1, y1, x2, y2, color=MUTED, width=1.0, arrow=False, dash=False):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    _plain(c)
    c.line.color.rgb = _rgb(color)
    c.line.width = Pt(width)
    if dash:
        c.line.dash_style = MSO_LINE.DASH
    if arrow:
        ln = c.line._get_or_add_ln()
        tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
        ln.append(tail)
    return c


def _border(cell, color=GRID, width=0.75, sides=None):
    """칸의 네 변에 선을 긋습니다. 선은 칸 채우기보다 앞에 와야 하는 OOXML 순서를 지킵니다.

    sides는 변마다 (색, 두께)를 따로 줄 때 씁니다 — 키는 L · R · T · B, 없는 변은 color · width입니다.
    """
    sides = sides or {}
    tcPr = cell._tc.get_or_add_tcPr()
    for tag in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        old = tcPr.find(qn(tag))
        if old is not None:
            tcPr.remove(old)
    for i, side in enumerate("LRTB"):
        c, wd = sides.get(side, (color, width))
        ln = tcPr.makeelement(qn("a:ln" + side), {"w": str(int(Pt(wd))), "cap": "flat", "cmpd": "sng",
                                                  "algn": "ctr"})
        fill = ln.makeelement(qn("a:solidFill"), {})
        fill.append(fill.makeelement(qn("a:srgbClr"), {"val": c}))
        ln.append(fill)
        ln.append(ln.makeelement(qn("a:prstDash"), {"val": "solid"}))
        tcPr.insert(i, ln)


def table(slide, x, y, w, widths, header, rows, size=11, row_h=0.36):
    """widths는 비율. 머리줄은 잉크색, 몸통은 흰 바탕에 옅은 선입니다."""
    n = len(rows) + 1
    gf = slide.shapes.add_table(n, len(header), Inches(x), Inches(y), Inches(w), Inches(row_h * n))
    t = gf.table
    tot = float(sum(widths))
    for i, wd in enumerate(widths):
        t.columns[i].width = Emu(int(Inches(w) * wd / tot))
    # 테마 표 스타일의 띠 무늬를 끕니다 — 색은 칸마다 직접 정합니다
    tblpr = gf._element.graphic.graphicData.tbl.tblPr
    tblpr.set("bandRow", "0")
    tblpr.set("firstRow", "0")
    ncol = len(header)
    for r in range(n):
        t.rows[r].height = Inches(row_h)
        cells = header if r == 0 else rows[r - 1]
        for c in range(ncol):
            cell = t.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = _rgb(TABLE["head_fill"] if r == 0 else
                                            (TABLE["zebra"] if r % 2 == 0 else TABLE["body_fill"]))
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            run = tf.paragraphs[0].add_run()
            run.text = v(cells[c]) if r else str(cells[c])
            _font(run, size, r == 0, TABLE["head_text"] if r == 0 else TABLE["body_text"])
            _border(cell, TABLE["line"], TABLE["width"])
    return gf


def paged(items, per):
    return [items[i:i + per] for i in range(0, len(items), per)] or [[]]


# ── 덱 공통 ───────────────────────────────────────────────────────────

class Deck:
    def __init__(self, kind, meta):
        self.prs = Presentation()
        self.prs.slide_width = Inches(SW)
        self.prs.slide_height = Inches(SH)
        self.blank = self.prs.slide_layouts[6]
        self.kind = kind
        self.meta = meta
        self.page = 0
        self.open = []          # 미결 사항 — `?`가 찍힌 자리
        self.marks = {}         # 목차에 쓸 쪽 번호 — 그 항목이 시작하는 장

    def slide(self, title=None, section=None):
        s = self.prs.slides.add_slide(self.blank)
        self.page += 1
        if title:
            if section:
                text(s, MX, 0.38, 8, 0.3, section, size=11, bold=True, color=ACCENT, name="section")
            text(s, MX, 0.62, SW - 2 * MX, 0.6, title, size=26, bold=True, name="title")
        foot = "%s · %s · v%s" % (v(self.meta.get("name")), self.kind, v(self.meta.get("version")))
        text(s, MX, SH - 0.42, 8, 0.25, foot, size=9, color=MUTED, name="footer")
        text(s, SW - MX - 1, SH - 0.42, 1, 0.25, str(self.page), size=9, color=MUTED, align="r",
             name="page")
        return s

    def cover(self, eyebrow, title, sub):
        s = self.prs.slides.add_slide(self.blank)
        self.page += 1
        bg = box(s, 0, 0, SW, SH, fill=INK, name="cover-bg")
        bg.name = "cover-bg"
        text(s, 0.9, 2.2, 10, 0.4, eyebrow, size=14, bold=True, color=ACCENT)
        text(s, 0.9, 2.7, 11.5, 1.4, title, size=40, bold=True, color=WHITE)
        m = self.meta
        info = "v%s · %s · 작성 %s · 상태 %s" % (v(m.get("version")), v(m.get("date")),
                                             v(m.get("author")), v(m.get("status")))
        text(s, 0.9, 4.25, 11.5, 0.4, sub, size=16, color="C9D1D8")
        text(s, 0.9, 6.3, 11.5, 0.35, info, size=12, color="9FAAB3")

    def mark(self, key):
        """방금 만든 장을 목차 항목의 시작 쪽으로 적습니다. 먼저 적힌 쪽을 덮지 않습니다."""
        self.marks.setdefault(key, self.page)

    def divider(self, no, title, lead):
        s = self.prs.slides.add_slide(self.blank)
        self.page += 1
        self.mark("div%d" % no)
        box(s, 0, 0, SW, SH, fill=TINT, name="divider-bg")
        text(s, 0.9, 2.5, 3, 1.2, "%02d" % no, size=60, bold=True, color=ACCENT)
        text(s, 0.9, 3.75, 11, 0.7, title, size=32, bold=True)
        text(s, 0.9, 4.5, 11, 0.8, lead, size=15, color=SUB)

    def history(self, rows):
        s = self.slide("문서 이력", "문서 정보")
        body = [[h.get("version"), h.get("date"), h.get("author"), h.get("note")] for h in rows] or \
               [[self.meta.get("version"), self.meta.get("date"), self.meta.get("author"), "최초 작성"]]
        table(s, MX, 1.45, SW - 2 * MX, (1, 1.3, 1.3, 5), ["버전", "날짜", "작성자", "변경 내용"], body[:10])

    def questions(self, extra):
        qs = lst(extra)
        if not qs and not self.open:
            return
        for i, chunk in enumerate(paged(qs + ["「?」 자리 — " + o for o in self.open], 9)):
            s = self.slide("미결 사항" + (" (%d)" % (i + 1) if i else ""), "확정 전에 정할 것")
            self.mark("questions")
            text(s, MX, 1.5, SW - 2 * MX, 5.2,
                 bullets(chunk), size=15, spacing=10)

    def note(self, where, val):
        if v(val) == UNKNOWN:
            self.open.append(where)

    def save(self, path):
        d = os.path.dirname(os.path.abspath(path))
        os.makedirs(d, exist_ok=True)
        self.prs.core_properties.title = "%s — %s" % (v(self.meta.get("name")), self.kind)
        self.prs.core_properties.author = v(self.meta.get("author"))
        self.prs.save(path)


# ── 와이어프레임 ───────────────────────────────────────────────────────

def layout_regions(regions):
    """좌표가 없는 영역은 위에서부터 쌓습니다. 단위는 화면 폭 · 높이의 백분율입니다."""
    out, y, gap = [], 2.0, 1.6
    auto = [r for r in regions if r.get("y") is None]
    need = sum(r.get("h") or WF_DEFAULT_H.get(r.get("type"), 10) for r in auto) + gap * (len(auto) + 1)
    scale = min(1.0, 96.0 / need) if need else 1.0
    for r in regions:
        r = dict(r)
        if r.get("y") is None:
            r["h"] = (r.get("h") or WF_DEFAULT_H.get(r.get("type"), 10)) * scale
            r["x"] = r.get("x", 4)
            r["w"] = r.get("w", 92)
            r["y"] = y
            y += r["h"] + gap * scale
        out.append(r)
    return out


def phone(slide, x, y, h, regions, markers=True, title=None):
    """기기 틀 안에 영역을 회색 상자로 그립니다. 색 · 이미지는 넣지 않습니다(와이어프레임)."""
    w = h * 0.5
    box(slide, x, y, w, h, fill=WHITE, line=WF_FRAME, round_=True, width=1.5, name="wf-frame")
    sx, sy, sw, sh = x + 0.12, y + 0.3, w - 0.24, h - 0.5
    box(slide, sx, sy, sw, sh, fill="FBFBFC", line=LINE, name="wf-screen")
    if title:
        text(slide, x, y - 0.35, w, 0.3, title, size=10, bold=True, color=SUB, align="c")
    for i, r in enumerate(layout_regions(regions), 1):
        kind = r.get("type", "other")
        rx, ry = sx + sw * r["x"] / 100.0, sy + sh * r["y"] / 100.0
        rw, rh = sw * r["w"] / 100.0, sh * r["h"] / 100.0
        lbl = r.get("label") or kind
        is_btn = kind == "button"
        box(slide, rx, ry, rw, rh, fill=WF_FILL.get(kind, WF_FILL["other"]),
            line="7F8A93" if kind in ("input", "card", "image") else None, round_=is_btn,
            label=None if kind in ("image", "list", "text") else lbl, size=8,
            color=WHITE if is_btn else SUB, name="wf-%s" % kind)
        if kind == "image":
            line(slide, rx, ry, rx + rw, ry + rh, color="B5BCC2", width=0.75)
            line(slide, rx, ry + rh, rx + rw, ry, color="B5BCC2", width=0.75)
            text(slide, rx, ry + rh / 2 - 0.12, rw, 0.24, lbl, size=8, color=SUB, align="c")
        elif kind == "list":
            rows = max(2, min(5, int(rh / 0.32)))
            for k in range(1, rows):
                yy = ry + rh * k / rows
                line(slide, rx + 0.05, yy, rx + rw - 0.05, yy, color=LINE, width=0.75)
            text(slide, rx + 0.05, ry + 0.02, rw - 0.1, 0.22, lbl, size=8, color=SUB)
        elif kind == "text":
            text(slide, rx + 0.03, ry + 0.02, rw - 0.06, rh - 0.04, lbl, size=8, color=SUB)
        if markers:
            # 표식은 틀 바깥 왼쪽에 둡니다 — 영역 안에 두면 영역 글자를 가립니다
            my = ry + min(rh, 0.4) / 2 - 0.11
            line(slide, x - 0.1, my + 0.11, rx, my + 0.11, color=ACCENT, width=0.5)
            circle(slide, x - 0.34, my, 0.22, ACCENT, str(r.get("no", i)), size=8)
    return w


# ── 프로젝트 전체 문서 ─────────────────────────────────────────────────


# ── 배지 · 범례 · 글 길이 ──────────────────────────────────────────────

def badge(slide, x, y, code, size=8, label=None):
    """상태 배지 — 둥근 사각 안에 흰 글자. code는 STATUS의 키이고, 모르는 값은 회색으로 찍습니다."""
    name, color = STATUS.get(str(code).upper(), (str(code), MUTED))
    label = label or name
    w = 0.16 + 0.11 * len(label) * size / 8.0
    box(slide, x, y, w, 0.22, fill=color, shape="capsule", label=label, size=size, color=WHITE,
        bold=True, name="badge-%s" % code)
    return w


def legend(slide, items, y=None, right=None):
    """범례 — 다이어그램마다 같은 자리(오른쪽 아래)에 둡니다. items: (그리는 함수, 글자)."""
    y = SH - 0.85 if y is None else y
    right = SW - MX if right is None else right
    widths = [0.42 + 0.13 * len(t) for _, t in items]
    x = right - sum(widths) - 0.2 * (len(items) - 1)
    for (draw, t), w in zip(items, widths):
        draw(slide, x, y + 0.04)
        text(slide, x + 0.34, y, w - 0.34, 0.26, t, size=9, color=SUB)
        x += w + 0.2


def est_lines(s, width_in, size):
    """한 칸에 몇 줄로 접히는지 어림합니다. 한글 한 글자는 대략 글자 크기만큼 넓습니다."""
    per = max(4, int(width_in * 72.0 / size * 0.92))
    return sum(max(1, -(-len(part) // per)) for part in str(s).splitlines() or [""])
