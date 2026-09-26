# -*- coding: utf-8 -*-
"""서식 문체 정규화 — Test-Step은 '~한다', Expected-Result는 '~된다' 체."""
import re

# 말미 동작명사 → 서술형
_END = {
    "정규화": "정규화된다", "미차감": "미차감된다", "비노출": "비노출된다",
    "차단": "차단된다", "일치": "일치한다", "가능": "가능하다", "동작": "동작한다",
    "안내": "안내된다", "표시": "표시된다", "반영": "반영된다", "유지": "유지된다",
    "노출": "노출된다", "차감": "차감된다", "처리": "처리된다", "동일": "동일하다",
    "불가": "불가하다", "렌더": "렌더된다", "검증": "검증된다", "유도": "유도된다",
    "전이": "전이된다", "발동": "발동된다", "고지": "고지된다", "경고": "경고된다",
    "환급": "환급된다", "부합": "부합한다", "진입": "진입된다", "발급": "발급된다",
    "생성": "생성된다", "적용": "적용된다", "지급": "지급된다", "삭제": "삭제된다",
    "수신": "수신된다", "성공": "성공한다", "실패": "실패한다", "복구": "복구된다",
    "회수": "회수된다", "제외": "제외된다", "갱신": "갱신된다", "승인": "승인된다",
    "거절": "거절된다", "확인": "확인된다", "복귀": "복귀된다", "요구": "요구된다",
    "제한": "제한된다", "제재": "제재된다", "승격": "승격된다", "기록": "기록된다",
    "인식": "인식된다", "준수": "준수된다", "허용": "허용된다", "수렴": "수렴된다",
    "통지": "통지된다", "증가": "증가한다", "감소": "감소한다", "회상": "회상된다",
    "초기화": "초기화된다", "해금": "해금된다", "활성화": "활성화된다",
}

_RULES = [
    (r"되지 않음$", "되지 않는다"),
    (r"하지 않음$", "하지 않는다"),
    (r"지 않음$", "지 않는다"),
    (r"없음$", "없다"),
    (r"있음$", "있다"),
    (r"([가-힣])됨$", r"\1된다"),
    (r"([가-힣])함$", r"\1한다"),
    (r"([가-힣])짐$", r"\1진다"),
    (r"([가-힣])림$", r"\1린다"),
    (r"([가-힣])음$", r"\1는다"),
]

# 자동 변환 시 의미가 뒤집히거나 어색해지는 말미 — 원문 유지
_SKIP = ("정합",)
_MEASURE = ("이하", "이상", "미만", "초과", "범위 내", "0턴", "0건", " 내")


def to_step(s):
    s = s.strip().rstrip(".")
    if not s:
        return s
    if re.search(r"다$", s):
        return s
    return s + "한다"


def to_expected(s):
    """말미 괄호주는 떼었다가 변환 후 다시 붙인다."""
    s = s.strip().rstrip(".")
    if not s:
        return s
    tail = ""
    m = re.search(r"\s*(\([^()]*\))$", s)
    if m:
        tail = " " + m.group(1)
        s = s[: m.start()].rstrip()
    if not s:
        return (tail or "").strip()
    if s.endswith("다"):
        return s + tail
    if s.endswith(_SKIP):
        return s + tail
    if s.endswith(_MEASURE):
        return s + "이다" + tail
    if s.endswith("금지"):
        base = s[:-2].rstrip()
        if base.endswith("발생"):
            return base[:-2].rstrip() + " 발생하지 않는다" + tail
        if base.endswith("미동작"):
            return base[:-3].rstrip() + " 미동작이 없다" + tail
        return base + "되지 않는다" + tail
    for pat, rep in _RULES:
        new = re.sub(pat, rep, s)
        if new != s:
            return new + tail
    for noun in sorted(_END, key=len, reverse=True):
        if s.endswith(noun):
            return s[: -len(noun)] + _END[noun] + tail
    return s + tail


def split_steps(raw):
    parts = [p.strip() for p in raw.split("\n") if p.strip()]
    out = [re.sub(r"^\d+\.\s*", "", p) for p in parts]
    return out or [raw.strip()]


def split_expected(exp):
    """문장 단위 분리. 버전 표기(1.2.20)는 마침표 뒤 공백이 없어 걸리지 않는다."""
    parts = re.split(r"\.\s+", exp.strip())
    parts = [p.strip().rstrip(".") for p in parts if p.strip()]
    return [to_expected(p) for p in parts] or [to_expected(exp)]
