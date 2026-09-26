#!/usr/bin/env python3
"""안전한 공용 부품과 테마에서 catalog.json·preview.html·hdk.parts.js를 만든다."""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).parent.parent
META_RE = re.compile(r"<!--\s*(.*?)-->", re.S)


def meta_and_body(path):
    text = path.read_text(encoding="utf-8")
    match = META_RE.search(text)
    if not match:
        raise ValueError(f"부품 메타가 없습니다: {path}")
    meta = {}
    for line in match.group(1).strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    for key in ("fits", "mood", "slots"):
        if key in meta:
            meta[key] = [item.strip() for item in meta[key].split(",")]
    meta["path"] = str(path.relative_to(ROOT)).replace("\\", "/")
    return meta, META_RE.sub("", text, count=1).strip()


parts, scripts, rows = [], [], []
for path in sorted((ROOT / "parts").glob("*/*.html")):
    meta, body = meta_and_body(path)
    if meta["source"] in {"designmodo/html-website-templates", "iGaoWei/BigDataView", "bcosca/fatfree"}:
        raise ValueError(f"제한·미확인 출처 부품이 포함되었습니다: {path}")
    parts.append(meta)
    scripts.extend(re.findall(r"<script>(.*?)</script>", body, re.S))
    label = f"{meta['part']}.{meta['variant']} · {meta['source']}"
    rows.append(f"<article class=\"part\"><h2>{html.escape(label)}</h2>{body}</article>")

themes = sorted(path.stem for path in (ROOT / "tokens/themes").glob("*.css"))
(ROOT / "catalog.json").write_text(json.dumps({"parts": parts, "themes": themes}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(ROOT / "hdk.parts.js").write_text("/* 생성물: 공용 부품 초기화 함수 */\n" + "\n".join(scripts) + "\n", encoding="utf-8")

base = (ROOT / "tokens/base.css").read_text(encoding="utf-8")
reset = (ROOT / "tokens/reset.css").read_text(encoding="utf-8")
theme = (ROOT / "tokens/themes/indigo.css").read_text(encoding="utf-8")
runtime = (ROOT / "hdk.js").read_text(encoding="utf-8")
preview = f"""<!doctype html>
<html lang=\"ko\" class=\"hdk-root\" data-theme=\"dark\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>HTML 디자인 킷 미리보기</title>
<style>{base}\n{reset}\n{theme}\nbody{{padding:2rem}} .catalog{{display:grid;gap:1.5rem}} .part{{padding:1rem;border:1px solid var(--hdk-line);border-radius:var(--hdk-radius-lg);background:var(--hdk-bg-elev)}} .part h2{{margin:0 0 1rem;font:var(--hdk-fw-medium) var(--hdk-fs-sm) var(--hdk-font-mono);color:var(--hdk-fg-muted)}}</style>
<script>{runtime}</script></head><body><main><h1>HTML 디자인 킷</h1><p>안전 출처 또는 자체 제작 부품 {len(parts)}개 · 테마 {len(themes)}개</p><div class=\"catalog\">{''.join(rows)}</div></main></body></html>"""
(ROOT / "preview.html").write_text(preview, encoding="utf-8")
print(f"parts: {len(parts)}, themes: {themes} → catalog.json, preview.html")
