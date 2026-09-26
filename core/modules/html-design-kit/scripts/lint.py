#!/usr/bin/env python3
"""SPEC 7장 자동 검사 (필수 강도). 사용: python3 lint.py"""
import re, pathlib, sys
ROOT = pathlib.Path(__file__).parent.parent
RULES = [
  (r'#[0-9a-fA-F]{3,8}\b', "색 하드코딩"),
  (r'\brgba?\(|\bhsla?\(', "색 함수 하드코딩"),
  (r'border-radius:\s*[1-9]', "라운딩 하드코딩"),
  (r'box-shadow:\s*[0-9]', "그림자 하드코딩"),
  (r'font-family:(?!\s*var\()', "폰트 하드코딩"),
  (r'--hdk-[\w-]+\s*:', "부품 내 --hdk-* 재정의"),
  (r'@media\s*\(min-width:(?!\s*(640px|1024px|1440px))', "비표준 브레이크포인트"),
]
SPEC_VERSION = "0.5"
HTML_RULES = [
  (r'\sid="', "id 사용 금지 (같은 부품 2개 시 충돌)"),
  (r'document\.currentScript', "currentScript 금지 → hdk.register 규약"),
  (r'<script>(?!(?:.|\n)*hdk\.register\()', "script 가 hdk.register 형태가 아님"),
]
bad = 0
for f in sorted(ROOT.glob("parts/*/*.html")):
    t = f.read_text(encoding="utf-8"); meta = re.search(r"<!--(.*?)-->", t, re.S).group(1)
    for key in ("part","variant","source","fits","mood","slots","requires","added"):
        if not re.search(rf"^{key}:", meta, re.M): print(f"{f}: 메타 누락 {key}"); bad += 1
    if len(re.findall(r'<\w+ data-part="', t)) != 1: print(f"{f}: data-part 루트가 1개가 아님"); bad += 1
    if not re.search(rf"^spec: {re.escape(SPEC_VERSION)}$", meta, re.M): print(f"{f}: spec 버전이 {SPEC_VERSION} 이 아님"); bad += 1
    if "<script>" in t and 'data-init="' not in t: print(f"{f}: script 가 있는데 data-init 이 없음"); bad += 1
    for pat, msg in HTML_RULES:
        if re.search(pat, t): print(f"{f}: {msg}"); bad += 1
    style = "\n".join(re.findall(r"<style>(.*?)</style>", t, re.S))
    for pat, msg in RULES:
        for m in re.finditer(pat, style):
            line = style[:m.start()].count("\n")+1
            print(f"{f}:{line}: {msg} → {style.splitlines()[line-1].strip()[:80]}"); bad += 1
    for cls in set(re.findall(r'class="([^"]+)"', t)):
        for c in cls.split():
            if not c.startswith("hdk-"): print(f"{f}: 접두어 없는 클래스 {c}"); bad += 1
print("통과" if not bad else f"{bad}건"); sys.exit(1 if bad else 0)
