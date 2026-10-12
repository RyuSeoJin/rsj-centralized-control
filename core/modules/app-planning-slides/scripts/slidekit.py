# -*- coding: utf-8 -*-
"""슬라이드 부품 — 글꼴 · 색 · 텍스트 상자 · 도형 · 선 · 표 · 덱 틀 · 와이어프레임

패턴(patterns.py)과 덱 조립(build_slides.py)이 모두 이 부품만으로 그립니다. 색 · 글꼴 · 여백을
한 자리에 두어야 장마다 모양이 갈리지 않습니다. Google Slides 변환 규칙(글꼴 하나 · 단색 ·
그림자 없음)도 여기서 지킵니다 — 규칙 정본은 ../rules/planning-slides.md §6입니다.
"""
import os
import re
import sys

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
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
WF_TEXT = "3D4851"              # 와이어프레임 안 글자 — 회색 바탕에서도 읽히는 짙은 슬레이트
WF_SIZE = 9                    # 와이어프레임 안 글자 크기의 하한
WF_FILL = {"header": "C9CED3", "nav": "C9CED3", "tab": "DDE1E4", "button": "6E7A85",
           "input": "FFFFFF", "list": "F1F3F4", "image": "E3E6E8", "text": "F7F8F9",
           "card": "ECEEF0", "banner": "D3D8DC", "other": "ECEEF0"}
WF_DEFAULT_H = {"header": 8, "nav": 9, "tab": 7, "button": 7, "input": 7, "list": 28,
                "image": 24, "text": 12, "card": 16, "banner": 13, "other": 10}
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
    # 자간 — 글자 크기의 일정 비율(1/100pt 단위). Google Slides에는 자간 설정이 없어 변환하면 사라질 수 있어,
    # 여유는 줄 간격(LINE_SPACING)이 함께 맡습니다
    rpr.set("spc", str(int(round(size * LETTER_SPACING * 100))))
    # 한국어로 표시해야 띄어쓰기 단위로 줄을 바꿉니다 — 언어가 없으면 한글을 글자 단위로 끊어
    # 「모임 / 은」처럼 음절 하나가 다음 줄로 떨어집니다
    rpr.set("lang", "ko-KR")
    rpr.set("altLang", "en-US")


def _plain(shape):
    """테마 스타일(그림자 등 효과 참조)을 떼어 냅니다. 색은 직접 정합니다."""
    st = shape._element.find(qn("p:style"))
    if st is not None:
        shape._element.remove(st)


#: 글머리 기호 — 단계마다 **모양 자체를** 바꿔 깊이를 보입니다(1단 ■ · 2단 ◆ · 3단 ● · 4단 －).
#: 채움만 다른 짝(◆ · ◇, ■ · □)은 작게 찍히면 구분되지 않아 쓰지 않습니다.
#: 기호는 **본문과 같은 크기**로 찍습니다 — Noto Sans KR의 도형 기호는 같은 크기일 때만 세로 중심이 한글과
#: 같고(약 0.38em), 줄이면 기준선 쪽으로 처집니다. 4단은 가운데에 그려진 전각 하이픈(－)입니다.
#: 모두 Noto Sans KR에 있는 기호라 Google Slides에서도 다른 글꼴로 바뀌지 않습니다
BULLET_MARKS = ("■", "◆", "●", "－")
BULLET_SCALE = {}
MARK_SCALE = 1.0
#: 소제목 표식 — 카드 안의 소제목 앞에 붙여 「아래가 이 묶음」임을 보입니다(토글처럼)
HEAD_MARK = "▼"
#: 토글 들여쓰기 — ▼ 뒤 글자와 소제목 아래 내용이 모두 이만큼 들어가 한 선에 맞습니다
TOGGLE_STEP = 0.28
#: 자간(글자 크기 대비)과 줄 간격(배수). 글이 빽빽해 보이지 않게 둘 다 조금 넓힙니다
LETTER_SPACING = 0.03
LINE_SPACING = 1.2
#: 기호 뒤 간격 — 공백 한 칸 너비(글자 크기 대비)
MARK_GAP = 0.35
#: Noto Sans KR의 한 줄 높이(글자 크기 대비, 줄 간격 1배 기준). 줄 간격 1.2로 렌더링해 잰 줄 사이 거리가
#: 글자 크기의 1.465배라 1배 기준으로는 1.22입니다. 카드 · 목록 높이 어림이 이 값을 씁니다
LINE_H = 1.22
TEXT_MARGIN = 0.02


def line_height(size):
    """글자 크기(pt)의 한 줄 높이(in) — 줄 간격을 넣은 높이입니다."""
    return size * LINE_H * LINE_SPACING / 72.0


#: 첫 줄 글자의 눈에 보이는 세로 중심 — 상자 위끝(여백 뒤)에서 글자 크기의 몇 배 아래인가.
#: 줄 간격 1.2 · Noto Sans KR로 렌더링해 잰 값입니다(한글 · 숫자 · 굵게 모두 11~28pt에서 0.70±0.01)
GLYPH_MID = 0.70


def glyph_mid(top, size):
    """상자 위끝이 top인 글의 첫 줄 글자 중심 y."""
    return top + TEXT_MARGIN + GLYPH_MID * size / 72.0


def first_line_top(center_y, size):
    """첫 줄 글자의 세로 중심이 center_y에 오도록 하는 텍스트 상자의 위쪽 y.

    번호 표식(원 · 큰 숫자) 오른쪽에 글을 둘 때 씁니다 — 위를 맞추면 글이 표식보다 높아 보입니다.
    줄 상자의 절반이 아니라 잰 글자 중심(GLYPH_MID)을 씁니다 — 글자 크기가 다른 둘을 맞출 때 어긋나지 않게.
    """
    return center_y - GLYPH_MID * size / 72.0 - TEXT_MARGIN


def bullets(items, level=0):
    """글머리 목록 → text()의 문단 목록. 항목 다음에 목록이 오면 그 항목의 하위(다음 단)입니다."""
    out = []
    for it in items if isinstance(items, list) else ([items] if items else []):
        if isinstance(it, list):
            out += bullets(it, min(level + 1, len(BULLET_MARKS) - 1))
        elif str(it).strip():
            out.append((str(it), {"bullet": level}))
    return out


def _hang(para, size, level, mark_scale=1.0):
    """내어쓰기 — 기호 너비 + 공백 한 칸. 둘째 줄부터 글자 시작선이 첫 줄 글자와 맞습니다."""
    step = size * (mark_scale + MARK_GAP) / 72.0
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
        para.line_spacing = LINE_SPACING
        sz, c = o.get("size", size), o.get("color", color)
        lvl = o.get("bullet")
        if lvl is not None and lvl is not False:
            lvl = 0 if lvl is True else int(lvl)
            mark = BULLET_MARKS[min(lvl, len(BULLET_MARKS) - 1)]
            scale = BULLET_SCALE.get(mark, MARK_SCALE)
            _hang(para, sz, lvl, scale)
            m = para.add_run()
            m.text = mark + "	"
            _font(m, sz * scale, False, ACCENT if lvl == 0 else MUTED)
        elif o.get("head"):
            # 글머리처럼 내어쓰기 — 소제목 글자가 TOGGLE_STEP에서 시작해, 아래 내용과 같은 선에 섭니다
            pPr = para._p.get_or_add_pPr()
            pPr.set("marL", str(int(Inches(TOGGLE_STEP))))
            pPr.set("indent", str(int(-Inches(TOGGLE_STEP))))
            m = para.add_run()
            m.text = HEAD_MARK + "	"
            # ▼만 강조색 — 소제목 글자는 짙은 잉크로 둬서 강조색이 한 장에 너무 많아지지 않게 합니다
            _font(m, sz * MARK_SCALE, False, o.get("mark_color", ACCENT))
        r = para.add_run()
        r.text = s
        _font(r, sz, o.get("bold", bold), c)
    return tb


def subhead(slide, x, y, w, label, size=15, color=INK):
    """카드 안 소제목 — ▼ 표식 + 굵은 글자. 아래 내용은 x + TOGGLE_STEP에서 시작합니다(토글처럼).

    ▼는 같은 면(카드 하나 또는 카드 없는 본문)에 소제목 묶음이 둘 이상일 때만 붙입니다 —
    제목이 하나뿐이면 card_title()을 씁니다.
    """
    return text(slide, x, y, w, line_height(size) + 0.1, [(label, {"head": True})], size=size, bold=True,
                color=color)


def card_title(slide, x, y, w, label, size=15, color=INK):
    """카드 하나에 제목 하나뿐일 때 — 카드 테두리가 이미 묶음을 보이므로 ▼를 붙이지 않고,
    본문은 제목과 같은 선에서 시작합니다."""
    return text(slide, x, y, w, line_height(size) + 0.1, [label], size=size, bold=True, color=color)


#: 도형 이름 — 순서도 기호도 여기서 고릅니다(시작·종료 capsule · 처리 rect · 입출력 para · 분기 diamond)
SHAPES = {"rect": MSO_SHAPE.RECTANGLE, "round": MSO_SHAPE.ROUNDED_RECTANGLE,
          "capsule": MSO_SHAPE.ROUNDED_RECTANGLE, "diamond": MSO_SHAPE.DIAMOND,
          "para": MSO_SHAPE.PARALLELOGRAM, "oval": MSO_SHAPE.OVAL, "chevron": MSO_SHAPE.CHEVRON,
          "pentagon": MSO_SHAPE.PENTAGON,
          "star": MSO_SHAPE.STAR_5_POINT,   # 로드맵 마일스톤 — ◆는 2단 글머리와 헷갈려 별을 씁니다
          # 기능 흐름도(워크플로우 탐색기 기호) — 공통 처리는 양옆 세로선, 이동 연결자는 아래가 뾰족한 오각형
          "predefined": MSO_SHAPE.FLOWCHART_PREDEFINED_PROCESS,
          "offpage": MSO_SHAPE.FLOWCHART_OFFPAGE_CONNECTOR}


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


#: 표 행의 최소 높이 — 표마다 다르면 장을 넘길 때 리듬이 깨집니다. 글이 길면 행이 저절로 늘어납니다
TABLE_ROW_H = 0.4


def table(slide, x, y, w, widths, header, rows, size=11, row_h=TABLE_ROW_H):
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
            tf.paragraphs[0].line_spacing = LINE_SPACING
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
        for i, chunk in enumerate(paged(qs + ["미정 — " + o for o in self.open], 9)):
            s = self.slide("미결 사항" + (" (%d)" % (i + 1) if i else ""), "확정 전에 정할 것")
            self.mark("questions")
            text(s, MX, 1.5, SW - 2 * MX, 5.2,
                 bullets(chunk), size=15, spacing=10)

    def note(self, where, val):
        if v(val) == UNKNOWN:
            self.open.append(where)

    def page_slide(self, page):
        """쪽 번호(1부터)의 슬라이드."""
        return self.prs.slides[int(page) - 1]

    def link(self, run, from_slide, page):
        """글 한 조각(run)에 그 쪽으로 이동하는 슬라이드 내부 링크를 겁니다. 쪽이 없으면 걸지 않습니다."""
        if not page:
            return
        rid = from_slide.part.relate_to(self.page_slide(page).part, RT.SLIDE)
        rpr = run._r.get_or_add_rPr()
        hl = rpr.makeelement(qn("a:hlinkClick"), {qn("r:id"): rid, "action": "ppaction://hlinksldjump"})
        rpr.append(hl)

    def _link_colors(self):
        """테마의 링크 색을 본문 잉크색으로 — 링크 글자가 파랑으로 바뀌어 디자인이 깨지지 않게 합니다."""
        theme = self.prs.slide_masters[0].part.part_related_by(RT.THEME)
        xml = theme.blob.decode("utf-8")
        for tag in ("hlink", "folHlink"):
            xml = re.sub(r"(<a:%s>)\s*<a:(srgbClr|sysClr)[^>]*/>" % tag, lambda m: m.group(1) + '<a:srgbClr val="%s"/>' % INK, xml)
        theme._blob = xml.encode("utf-8")

    def save(self, path):
        d = os.path.dirname(os.path.abspath(path))
        os.makedirs(d, exist_ok=True)
        self._link_colors()
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


def phone(slide, x, y, h, regions, markers=True, title=None, labels=True, frames=None):
    """기기 틀 안에 영역을 회색 상자로 그립니다. 색 · 이미지는 넣지 않습니다(와이어프레임).

    frames에 목록을 주면 틀 도형을 담아 줍니다 — 연결선을 틀에 붙일 때 씁니다."""
    w = h * 0.5
    frame = box(slide, x, y, w, h, fill=WHITE, line=WF_FRAME, round_=True, width=1.5, name="wf-frame")
    if frames is not None:
        frames.append(frame)
    sx, sy, sw, sh = x + 0.12, y + 0.3, w - 0.24, h - 0.5
    box(slide, sx, sy, sw, sh, fill="FBFBFC", line=LINE, name="wf-screen")
    if title:
        # 제목은 틀보다 넓게 — 화면 이름이 길어도 한 줄에 둡니다
        text(slide, x - 0.8, y - 0.35, w + 1.6, 0.3, title, size=10, bold=True, color=SUB, align="c")
    for i, r in enumerate(layout_regions(regions), 1):
        kind = r.get("type", "other")
        rx, ry = sx + sw * r["x"] / 100.0, sy + sh * r["y"] / 100.0
        rw, rh = sw * r["w"] / 100.0, sh * r["h"] / 100.0
        lbl = r.get("label") or kind
        is_btn = kind == "button"
        box(slide, rx, ry, rw, rh, fill=WF_FILL.get(kind, WF_FILL["other"]),
            line="7F8A93" if kind in ("input", "card", "image") else None, round_=is_btn,
            label=None if kind in ("image", "list", "text") or not labels else lbl, size=WF_SIZE,
            color=WHITE if is_btn else WF_TEXT, name="wf-%s" % kind)
        if not labels:                                   # 썸네일 — 배치만 보입니다
            pass
        elif kind == "image":
            line(slide, rx, ry, rx + rw, ry + rh, color="B5BCC2", width=0.75)
            line(slide, rx, ry + rh, rx + rw, ry, color="B5BCC2", width=0.75)
            text(slide, rx, ry + rh / 2 - 0.13, rw, 0.26, lbl, size=WF_SIZE, color=WF_TEXT, align="c")
        elif kind == "list":
            rows = max(2, min(5, int(rh / 0.32)))
            for k in range(1, rows):
                yy = ry + rh * k / rows
                line(slide, rx + 0.05, yy, rx + rw - 0.05, yy, color=LINE, width=0.75)
            text(slide, rx + 0.05, ry + 0.02, rw - 0.1, 0.24, lbl, size=WF_SIZE, color=WF_TEXT)
        elif kind == "text":
            text(slide, rx + 0.03, ry + 0.02, rw - 0.06, rh - 0.04, lbl, size=WF_SIZE, color=WF_TEXT)
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


def _char_em(ch):
    """Noto Sans KR의 글자 폭(em) 어림 — 글꼴에서 잰 값입니다(한글 0.92 · 공백 0.22 · 숫자 0.56)."""
    o = ord(ch)
    if 0xAC00 <= o <= 0xD7A3 or 0x3000 <= o <= 0x30FF or 0xFF00 <= o <= 0xFFEF or 0x4E00 <= o <= 0x9FFF:
        return 1.0 if ch in "「」『』" else 0.92
    if ch == " ":
        return 0.224
    if ch.isdigit():
        return 0.555
    if ch.isupper():
        return 0.64
    if ch.isalpha():
        return 0.55
    if ch in ".,:;'!|":
        return 0.28
    if ch in "()[]/-":
        return 0.36
    return 0.6 if o < 0x2000 else 0.9


def est_lines(s, width_in, size):
    """한 칸에 몇 줄로 접히는지 어림합니다. 글자 폭 + 자간으로 띄어쓰기 단위 줄바꿈을 흉내 냅니다
    (글자를 한국어로 표시해 PowerPoint가 단어 단위로 줄을 바꾸기 때문입니다)."""
    limit = max(1.0, width_in * 72.0 / size)            # 한 줄에 들어가는 폭(em)
    track = LETTER_SPACING
    total = 0
    for part in str(s).splitlines() or [""]:
        lines, cur = 1, 0.0
        for k, word in enumerate(part.split(" ")):
            wl = sum(_char_em(c) + track for c in word)
            add = wl + ((0.224 + track) if cur else 0.0)
            if cur and cur + add > limit:
                lines += 1
                cur = wl
                while cur > limit:                       # 칸보다 긴 단어는 글자 단위로 넘어갑니다
                    lines += 1
                    cur -= limit
            else:
                cur += add
        total += lines
    return total


def est_text_height(paras, width_in, size, spacing=4):
    """text()에 넘길 문단들이 차지할 높이(in) 어림 — 카드를 내용 높이에 맞출 때 씁니다."""
    if isinstance(paras, str):
        paras = [paras]
    h = TEXT_MARGIN * 2
    for p in paras:
        s, o = (p, {}) if isinstance(p, str) else p
        sz = o.get("size", size)
        lvl = o.get("bullet")
        indent = 0.0
        if lvl is not None and lvl is not False:
            indent = sz * (MARK_SCALE + MARK_GAP) / 72.0 * ((0 if lvl is True else int(lvl)) + 1)
        h += est_lines(s, width_in - 0.08 - indent, sz) * line_height(sz) + spacing / 72.0
    return h


# ── 꺾은선 연결선 ─────────────────────────────────────────────────────

def _set_geom(conn, prst, adj=None):
    """연결선의 모양(직선 · L자 · Z자 · 세 번 · 네 번 꺾기)을 바꿉니다. adj는 값 하나 또는 목록(adj1, adj2, …)입니다."""
    sp = conn._element
    geom = sp.spPr.find(qn("a:prstGeom"))
    geom.set("prst", prst)
    av = geom.find(qn("a:avLst"))
    if av is None:
        av = geom.makeelement(qn("a:avLst"), {})
        geom.append(av)
    for g in list(av):
        av.remove(g)
    if adj is not None:
        for k, a in enumerate(adj if isinstance(adj, (list, tuple)) else [adj], 1):
            gd = av.makeelement(qn("a:gd"), {"name": "adj%d" % k, "fmla": "val %d" % int(round(a * 100000))})
            av.append(gd)


def _set_xfrm(conn, x, y, w, h, rot=0, flip_h=False, flip_v=False):
    xfrm = conn._element.spPr.find(qn("a:xfrm"))
    for k in ("rot", "flipH", "flipV"):
        if k in xfrm.attrib:
            del xfrm.attrib[k]
    if rot:
        xfrm.set("rot", str(rot))
    if flip_h:
        xfrm.set("flipH", "1")
    if flip_v:
        xfrm.set("flipV", "1")
    xfrm.find(qn("a:off")).set("x", str(int(Inches(x))))
    xfrm.find(qn("a:off")).set("y", str(int(Inches(y))))
    xfrm.find(qn("a:ext")).set("cx", str(int(Inches(max(w, 0.001)))))
    xfrm.find(qn("a:ext")).set("cy", str(int(Inches(max(h, 0.001)))))


def _glue(conn, start=None, end=None):
    """연결선 끝을 도형의 연결점에 붙입니다(도형을 옮기면 선이 따라옵니다). (도형, 연결점 번호)."""
    nv = conn._element.find(qn("p:nvCxnSpPr")).find(qn("p:cNvCxnSpPr"))
    for tag, target in (("a:stCxn", start), ("a:endCxn", end)):
        if target is None:
            continue
        shp, idx = target
        el = nv.makeelement(qn(tag), {"id": str(shp.shape_id), "idx": str(idx)})
        nv.append(el)


ANCHOR = 0.08                  # 연결선 앵커(보이지 않는 정사각형) 한 변


def _sign_dir(d, axis):
    return ("r" if d > 0 else "l") if axis == "h" else ("d" if d > 0 else "u")


def _directions(sx, sy, ex, ey, first, mid):
    """(시작점에서 나가는 방향, 끝점으로 들어가는 방향) — r · l · d · u."""
    if abs(sx - ex) < 0.005:
        d = _sign_dir(ey - sy, "v")
        return d, d
    if abs(sy - ey) < 0.005:
        d = _sign_dir(ex - sx, "h")
        return d, d
    other = "v" if first == "h" else "h"
    to = mid if mid is not None else (ex if first == "h" else ey)
    dep = _sign_dir(to - (sx if first == "h" else sy), first)
    if mid is None:                                       # L자 — 마지막 선은 다른 축
        arr = _sign_dir((ey - sy) if other == "v" else (ex - sx), other)
    else:                                                 # Z · ㄷ자 — 마지막 선은 처음과 같은 축
        arr = _sign_dir((ex if first == "h" else ey) - mid, first)
    return dep, arr


def _anchor(slide, x, y, d, at_start):
    """(x, y)에 연결점이 오도록 보이지 않는 작은 도형을 두고 (도형, 연결점 번호)를 돌려줍니다.

    시작점이면 나가는 방향 쪽 변, 끝점이면 들어오는 쪽 변의 연결점을 씁니다(0 위 · 1 왼쪽 · 2 아래 · 3 오른쪽).
    """
    a = ANCHOR
    if at_start:
        place = {"r": (x - a, y - a / 2, 3), "l": (x, y - a / 2, 1), "d": (x - a / 2, y - a, 2),
                 "u": (x - a / 2, y, 0)}
    else:
        place = {"r": (x, y - a / 2, 1), "l": (x - a, y - a / 2, 3), "d": (x - a / 2, y, 0),
                 "u": (x - a / 2, y - a, 2)}
    bx, by, idx = place[d]
    return box(slide, bx, by, a, a, name="connector-anchor"), idx


def elbow(slide, sx, sy, ex, ey, first="h", mid=None, color=MUTED, width=1.0, arrow=False, dash=False,
          start=None, end=None):
    """꺾은선 연결선 하나 — 선 여러 개를 이어 붙이지 않습니다. 편집기에서 도형을 옮겨도 함께 움직입니다.

    first="h": 가로로 먼저, "v": 세로로 먼저 나갑니다. mid가 없으면 한 번 꺾는 L자,
    있으면 두 번 꺾는 Z자이고 mid는 꺾이는 자리(가로 먼저면 x, 세로 먼저면 y)입니다. mid가 양 끝 바깥이면
    ㄷ자(위로 돌아 들어가기)가 됩니다.
    start · end는 (도형, 연결점 번호) — 사각형 · 마름모는 0 위 · 1 왼쪽 · 2 아래 · 3 오른쪽입니다.
    비우면 그 자리에 보이지 않는 앵커 도형(`connector-anchor`)을 두고 붙입니다.
    """
    # ㄷ자(양 끝이 같은 높이 · 같은 열이고 mid가 바깥) — 한쪽 끝을 아주 조금 비켜 Z자 연결선으로 그립니다
    if mid is not None and first == "v" and abs(sy - ey) < 0.005:
        ey = sy + 0.01
    elif mid is not None and first == "h" and abs(sx - ex) < 0.005:
        ex = sx + 0.01
    # 도형 연결점에 붙지 않는 끝은 보이지 않는 앵커 도형을 두고 붙입니다 — 편집기(PowerPoint · Google Slides)가
    # 경로를 다시 계산해도 끝 위치와 나가고 들어오는 방향이 그대로 남습니다
    if start is None or end is None:
        dep, arr = _directions(sx, sy, ex, ey, first, mid)
        if start is None:
            start = _anchor(slide, sx, sy, dep, True)
        if end is None:
            end = _anchor(slide, ex, ey, arr, False)
    if abs(sx - ex) < 0.005 or abs(sy - ey) < 0.005:      # 일직선
        c = line(slide, sx, sy, ex, ey, color=color, width=width, arrow=arrow, dash=dash)
        _glue(c, start, end)
        return c
    c = line(slide, sx, sy, ex, ey, color=color, width=width, dash=dash)
    head = False
    if mid is None and first == "v":
        # 세로 먼저 L자 = 끝에서 시작하는 가로 먼저 L자를 거꾸로 — 화살표는 머리 쪽에 둡니다
        sx, sy, ex, ey = ex, ey, sx, sy
        start, end = end, start
        head = True
    w, h = abs(ex - sx), abs(ey - sy)
    if mid is None:
        _set_geom(c, "bentConnector2")
        _set_xfrm(c, min(sx, ex), min(sy, ey), w, h, flip_h=ex < sx, flip_v=ey < sy)
    elif first == "h":
        _set_geom(c, "bentConnector3", (mid - sx) / (ex - sx))
        _set_xfrm(c, min(sx, ex), min(sy, ey), w, h, flip_h=ex < sx, flip_v=ey < sy)
    else:
        # 세로 먼저 Z자 — 90° 돌린 가로 먼저 Z자입니다. 돌리기 전 상자는 가로 · 세로가 바뀝니다
        cx, cy = (sx + ex) / 2.0, (sy + ey) / 2.0
        _set_geom(c, "bentConnector3", (mid - sy) / (ey - sy))
        _set_xfrm(c, cx - h / 2.0, cy - w / 2.0, h, w, rot=5400000, flip_h=ey < sy, flip_v=ex > sx)
    if arrow:
        ln = c.line._get_or_add_ln()
        ln.append(ln.makeelement(qn("a:headEnd" if head else "a:tailEnd"),
                                 {"type": "triangle", "w": "med", "len": "med"}))
    _glue(c, start, end)
    return c


def _simple_pts(pts):
    """겹친 점과 한 줄로 이어지는 점을 합칩니다 — 꺾임 수를 실제 모양대로 셉니다."""
    out = []
    for p in pts:
        p = (float(p[0]), float(p[1]))
        if out and abs(out[-1][0] - p[0]) < 1e-4 and abs(out[-1][1] - p[1]) < 1e-4:
            continue
        if len(out) >= 2:
            a, b = out[-2], out[-1]
            if (abs(a[0] - b[0]) < 1e-4 and abs(b[0] - p[0]) < 1e-4) or                     (abs(a[1] - b[1]) < 1e-4 and abs(b[1] - p[1]) < 1e-4):
                out[-1] = p
                continue
        out.append(p)
    return out


def _seg_dir(a, b):
    if abs(a[1] - b[1]) < 1e-4:
        return "r" if b[0] > a[0] else "l"
    return "d" if b[1] > a[1] else "u"


def path_connector(slide, pts, color=MUTED, width=1.0, arrow=False, dash=False, start=None, end=None):
    """가로 · 세로 선분으로 이어진 점 목록을 연결선 도형 **하나**로 그립니다 — 선을 여러 개 이어 붙이지 않습니다.

    꺾임 0~2번은 elbow()(직선 · bentConnector2 · 3), 3번은 bentConnector4(가로 · 세로 · 가로 · 세로),
    4번은 bentConnector5(가로 · 세로 · 가로 · 세로 · 가로)입니다. 세로로 시작하는 3번 꺾기는 거꾸로 그리고
    화살표를 머리 쪽에 둡니다. start · end는 elbow()와 같고, 비우면 보이지 않는 앵커 도형에 붙입니다.
    """
    p = _simple_pts(pts)
    for a, b in zip(p, p[1:]):
        if abs(a[0] - b[0]) > 1e-4 and abs(a[1] - b[1]) > 1e-4:
            raise ValueError("path_connector: 가로 · 세로 선분만 됩니다 %r → %r" % (a, b))
    n = len(p) - 1
    kw = dict(color=color, width=width, arrow=arrow, dash=dash, start=start, end=end)
    if n < 1:
        raise ValueError("path_connector: 점이 둘 이상 있어야 합니다")
    first = "h" if abs(p[0][1] - p[1][1]) < 1e-4 else "v"
    if n == 1:
        return elbow(slide, p[0][0], p[0][1], p[1][0], p[1][1], **kw)
    if n == 2:
        return elbow(slide, p[0][0], p[0][1], p[2][0], p[2][1], first=first, **kw)
    if n == 3:
        mid = p[1][0] if first == "h" else p[1][1]
        return elbow(slide, p[0][0], p[0][1], p[3][0], p[3][1], first=first, mid=mid, **kw)
    if n > 5 or (first == "v" and n == 5):
        raise ValueError("path_connector: 꺾임이 너무 많습니다(%d번)" % (n - 1))
    if start is None:
        start = _anchor(slide, p[0][0], p[0][1], _seg_dir(p[0], p[1]), True)
    if end is None:
        end = _anchor(slide, p[-1][0], p[-1][1], _seg_dir(p[-2], p[-1]), False)
    head = False
    if first == "v":                                      # 세로 먼저 3번 꺾기 = 끝에서 가로 먼저로 거꾸로
        p = p[::-1]
        start, end = end, start
        head = True
    (sx, sy), (ex, ey) = p[0], p[-1]
    # 양 끝이 같은 열 · 같은 줄이면 비율을 셀 수 없어 끝을 아주 조금(0.01in) 비켜 둡니다
    if abs(ex - sx) < 0.005:
        ex = sx + 0.01
    if abs(ey - sy) < 0.005:
        ey = sy + 0.01

    def fx(x):
        return (x - sx) / (ex - sx)

    def fy(y):
        return (y - sy) / (ey - sy)
    c = line(slide, sx, sy, ex, ey, color=color, width=width, dash=dash)
    if n == 4:
        _set_geom(c, "bentConnector4", [fx(p[1][0]), fy(p[2][1])])
    else:
        _set_geom(c, "bentConnector5", [fx(p[1][0]), fy(p[2][1]), fx(p[3][0])])
    _set_xfrm(c, min(sx, ex), min(sy, ey), abs(ex - sx), abs(ey - sy), flip_h=ex < sx, flip_v=ey < sy)
    if arrow:
        ln = c.line._get_or_add_ln()
        ln.append(ln.makeelement(qn("a:headEnd" if head else "a:tailEnd"),
                                 {"type": "triangle", "w": "med", "len": "med"}))
    _glue(c, start, end)
    return c
