# -*- coding: utf-8 -*-
"""Penpot 화면 대응표(design/penpot-screen-map.md)의 화면 키 · 보드 링크 · 흐름 요약을 검사합니다.

Penpot에는 접속하지 않습니다. 대응표 글만 읽고, 문제를 한 줄씩 돌려줍니다.
"""
# CHANGELOG · 2026-10-30: 첫 판 — 키 중복 · 보드 링크 누락 · 다른 파일 링크 · 흐름 요약에만 있는 키.
import argparse
import io
import re
import sys
from urllib.parse import parse_qs, urlparse

DEFAULT_KEY = r"[A-Z]{1,3}\d{2,3}"
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")


def sections(text):
    """`## 제목` → 그 아래 줄 목록."""
    out, name = {}, ""
    for line in text.split("\n"):
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            name = m.group(1)
            out[name] = []
        elif name:
            out[name].append(line)
    return out


def workspace_params(url):
    """Penpot 작업 화면 주소의 `#/workspace?...` 값. 아니면 None."""
    frag = urlparse(url).fragment
    if not frag.startswith("/workspace"):
        return None
    query = frag.split("?", 1)[1] if "?" in frag else ""
    return {k: v[0] for k, v in parse_qs(query).items()}


def file_id(text):
    """머리말 「파일」 줄의 Penpot 파일 id."""
    for line in text.split("\n"):
        if line.lstrip("- ").startswith("**파일**"):
            for _, url in LINK.findall(line):
                p = workspace_params(url)
                if p and p.get("file-id"):
                    return p["file-id"]
    return None


def check(text, key=DEFAULT_KEY):
    """문제 목록을 돌려줍니다. 비어 있으면 통과입니다."""
    errors = []
    key_re = re.compile(r"^(?:%s)$" % key)
    sec = sections(text)
    fid = file_id(text)
    if not fid:
        errors.append("머리말에 「파일」 줄의 Penpot 파일 링크(file-id)가 없습니다")
    if "화면 대응표" not in sec:
        return errors + ["「## 화면 대응표」 절이 없습니다"]

    keys = []
    for line in sec["화면 대응표"]:
        if not line.startswith("|") or re.match(r"^\|\s*[-:]", line) or "화면 키" in line:
            continue
        first = line.strip("|").split("|")[0].strip()
        m = LINK.fullmatch(first)
        if not m:
            errors.append("첫 열이 `[화면 키](보드 링크)`가 아닙니다: %s" % first)
            continue
        k, url = m.group(1), m.group(2)
        if not key_re.match(k):
            errors.append("화면 키 `%s`이(가) 형식 `%s`에 맞지 않습니다" % (k, key))
        if k in keys:
            errors.append("화면 키 `%s`이(가) 겹칩니다" % k)
        keys.append(k)
        p = workspace_params(url)
        if p is None:
            errors.append("`%s`의 링크가 Penpot 작업 화면 주소(#/workspace)가 아닙니다" % k)
            continue
        for need in ("file-id", "board-id"):
            if not p.get(need):
                errors.append("`%s`의 보드 링크에 `%s`이(가) 없습니다" % (k, need))
        if fid and p.get("file-id") and p["file-id"] != fid:
            errors.append("`%s`의 링크가 「파일」 줄과 다른 Penpot 파일을 가리킵니다" % k)
    if not keys:
        errors.append("화면 대응표에 화면 행이 없습니다")

    flow = re.sub(r"`[^`]*`", "", "\n".join(sec.get("흐름 요약", [])))
    token = re.compile(r"(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])" % key)
    for k in sorted(set(token.findall(flow)) - set(keys)):
        errors.append("흐름 요약의 `%s`이(가) 화면 대응표에 없습니다" % k)
    return errors


def main(argv=None):
    ap = argparse.ArgumentParser(description="Penpot 화면 대응표를 검사합니다.")
    ap.add_argument("path", help="화면 대응표 md 파일")
    ap.add_argument("--key", default=DEFAULT_KEY, help="화면 키 정규식(기본 %(default)s)")
    args = ap.parse_args(argv)
    with io.open(args.path, encoding="utf-8") as f:
        errors = check(f.read(), args.key)
    for e in errors:
        print("x " + e)
    if errors:
        return 1
    print("ok 화면 대응표 검사 통과")
    return 0


if __name__ == "__main__":
    sys.exit(main())
