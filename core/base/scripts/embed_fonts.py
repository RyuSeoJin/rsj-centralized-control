# -*- coding: utf-8 -*-
"""HTML 문서에 글꼴을 내장합니다 — 네트워크 @import를 없애고 woff2를 파일 안에 담습니다

왜 필요한가
  결과물 문서는 마스터 CSS를 <style>에 통째로 넣은 단일 파일이지만, 글꼴만은
  Google Fonts에서 받아 오고 있었다. 그래서 인터넷이 없는 컴퓨터에서 열면
  글꼴이 시스템 기본으로 바뀌었다. 게다가 Google Fonts는 Pretendard를 제공하지
  않아(2026-09-21 확인) 본문 글꼴은 애초에 한 번도 적용된 적이 없었다.

무엇을 하나
  1) 대상 문서들의 본문에서 실제로 쓰인 글자를 모은다(태그 · <style> 제외).
  2) 그 글자만 남기고 글꼴을 깎아 woff2로 만든다.
  3) base64 @font-face 블록을 만들어 각 문서의 @import 자리에 넣는다.
  4) font-family 스택에 기호 전용 글꼴을 2순위로 끼운다.

다시 돌려도 안전하다(idempotent)
  이미 내장된 문서는 RT-FONTS-BEGIN/END 표시 사이를 새 블록으로 갈아 끼운다.
  문서를 고쳐 새 글자가 생겼으면 다시 돌리면 된다.

쓰는 법
  python core/base/scripts/embed_fonts.py <폴더 또는 파일> [...] [--profile docs|prototype] [--dry-run]
  예) python core/base/scripts/embed_fonts.py {프로젝트 폴더} --profile docs

글꼴 원본
  core/base/design-guide/fonts/ — 네트워크 없이 다시 만들 수 있도록 원본을 함께 둔다.
  Pretendard · IBM Plex Mono · Cinzel · DM Serif Display: SIL OFL 1.1 / DejaVu Sans: Bitstream Vera · Public Domain.
  전부 임베딩과 재배포가 허용된 라이선스다.

표시 이름
  RT-FONTS-BEGIN/END 표시와 'RT Symbols' 글꼴 이름은 이미 내장된 문서가 이 이름으로 찾는
  식별자라 바꾸지 않는다(바꾸면 옛 문서에서 블록을 못 찾아 두 벌이 들어간다).

필요한 것
  pip install fonttools brotli
"""
import argparse, base64, glob, os, pathlib, re, subprocess, sys

# 윈도 콘솔 기본 인코딩(cp949)은 이모지를 못 찍어 출력 도중 죽는다.
# 이 도구는 "어느 글꼴에도 없는 글자"로 이모지를 그대로 나열하므로 UTF-8로 못박는다.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = pathlib.Path(__file__).resolve().parent
FONTS = HERE.parent / "design-guide" / "fonts"
BEGIN = "/* ===== RT-FONTS-BEGIN ===== */"
END = "/* ===== RT-FONTS-END ===== */"

# ── 프로필: 어떤 글꼴을 어떤 이름·굵기로 넣을지
#    fallback=True 인 글꼴은 "앞 글꼴들에 없는 글자만" 담는다(기호 보충용).
PROFILES = {
    "docs": {
        "faces": [
            ("Pretendard",    "300 700", "normal", "PretendardVariable.woff2", False),
            ("IBM Plex Mono", "400",     "normal", "PlexMono-Regular.woff2",   False),
            ("IBM Plex Mono", "500",     "normal", "PlexMono-Medium.woff2",    False),
            ("IBM Plex Mono", "600",     "normal", "PlexMono-SemiBold.woff2",  False),
            ("RT Symbols",    "400",     "normal", "DejaVuSans.ttf",           True),
        ],
        # (찾을 스택, 바꿀 스택) — 기호 글꼴을 2순위로 끼운다
        "stacks": [
            ("font-family: 'Pretendard', 'Noto Sans KR', sans-serif;",
             "font-family: 'Pretendard', 'RT Symbols', 'Noto Sans KR', sans-serif;"),
            ("font-family: 'IBM Plex Mono', monospace",
             "font-family: 'IBM Plex Mono', 'RT Symbols', monospace"),
        ],
    },
    # 프로토타입은 장식 글꼴(라틴 전용)만 담는다 — 본문 Pretendard는 일부러 넣지 않는다.
    # 매번 고치는 실행물이라 260KB 덩어리를 얹으면 파일을 훑기가 번거로워진다.
    "prototype": {
        "faces": [
            ("Cinzel",           "500 700", "normal", "Cinzel.ttf",           False),
            ("DM Serif Display", "400",     "normal", "DMSerif-Regular.ttf",  False),
            ("DM Serif Display", "400",     "italic", "DMSerif-Italic.ttf",   False),
        ],
        "stacks": [],
    },
}

IMPORT_RE = re.compile(r"@import url\('https://fonts\.googleapis\.com/[^']*'\);")
# 이 도구가 생기기 전(2026-09-21 1차 작업)에 표시 없이 들어간 블록 — 한 번만 갈아 끼우면 된다
LEGACY_RE = re.compile(r"/\* 글꼴 내장 —.*?\*/\n(?:@font-face\{[^\n]*\}\n?)+", re.S)
LINK_RE = re.compile(r'<link href="https://fonts\.googleapis\.com/[^"]*" rel="stylesheet">')


def visible_chars(html):
    """문서에서 사람이 보게 될 글자를 모은다.

    <style>은 뺀다 — 내장된 base64가 들어 있어 셀 이유가 없다(전부 ASCII라 어차피 덮인다).
    <script>는 남긴다 — 복사 버튼이 '복사됨 ✓' 같은 글자를 실행 중에 만들어 넣으므로,
    빼 버리면 그 글자가 서브셋에서 누락돼 버튼 문구만 시스템 글꼴로 튄다.
    """
    import html as htmlmod
    body = html[html.find("<body"):] or html
    body = re.sub(r"<style[^>]*>.*?</style>", " ", body, flags=re.S)
    body = re.sub(r"<[^>]+>", " ", body)
    return set(htmlmod.unescape(body))


def coverage(path):
    from fontTools.ttLib import TTFont
    f = TTFont(path)
    cov = set()
    for t in f["cmap"].tables:
        cov |= set(t.cmap)
    f.close()
    return cov


def subset(src, dst, codepoints):
    uf = dst.with_suffix(".unicodes.txt")
    uf.write_text("\n".join("U+%04X" % u for u in sorted(codepoints)), encoding="utf-8")
    subprocess.run(
        [sys.executable, "-m", "fontTools.subset", str(src),
         "--output-file=" + str(dst), "--flavor=woff2",
         "--unicodes-file=" + str(uf),
         "--layout-features=kern,liga,calt", "--no-hinting",
         "--desubroutinize", "--name-IDs=1,2,3,4,6", "--notdef-outline"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    uf.unlink()
    return dst.stat().st_size


def build_block(profile, chars, tmp):
    """프로필대로 서브셋을 만들고 @font-face 블록 문자열을 돌려준다."""
    faces, used, lines = [], set(), []
    for fam, weight, style, fname, is_fallback in profile["faces"]:
        src = FONTS / fname
        cov = coverage(src)
        want = {ord(c) for c in chars if ord(c) in cov}
        if is_fallback:
            want -= used                      # 앞 글꼴들이 이미 덮은 글자는 뺀다
        if not want:
            continue
        used |= want
        out = tmp / ("%s-%s-%s.woff2" % (fam.replace(" ", ""), weight.replace(" ", "_"), style))
        size = subset(src, out, want)
        b64 = base64.b64encode(out.read_bytes()).decode("ascii")
        faces.append((fam, weight, style, len(want), size))
        lines.append(
            "@font-face{font-family:'%s';font-style:%s;font-weight:%s;font-display:swap;"
            "src:url(data:font/woff2;base64,%s) format('woff2');}" % (fam, style, weight, b64))
    missing = sorted(c for c in chars if ord(c) not in used)
    head = [
        BEGIN,
        "/* 글꼴 내장 — core/base/scripts/embed_fonts.py 가 생성. 손으로 고치지 말 것.",
        "   이 문서 묶음에 실제로 쓰인 글자 %d자만 남긴 woff2 서브셋이다." % len(chars),
    ]
    for fam, weight, style, n, size in faces:
        head.append("     %-17s %-8s %-7s  글자 %5d   %6d B" % (fam, weight, style, n, size))
    head.append("   그림 문자(이모지)는 담지 않는다 — 색을 가진 글꼴이라 용량이 수십 배이고,")
    head.append("   시스템 이모지 글꼴로 그리는 편이 각 OS에서 더 정확하다. */")
    return "\n".join(head) + "\n" + "\n".join(lines) + "\n" + END, faces, missing


def collect(targets):
    files = []
    for t in targets:
        p = pathlib.Path(t)
        if p.is_dir():
            files += sorted(glob.glob(str(p / "**" / "*.html"), recursive=True))
        else:
            files += sorted(glob.glob(t))
    return [pathlib.Path(f) for f in dict.fromkeys(files)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="+", help="폴더 또는 HTML 파일")
    ap.add_argument("--profile", default="docs", choices=sorted(PROFILES))
    ap.add_argument("--exclude", action="append", default=[],
                    help="파일 이름(부분 일치)을 대상에서 뺀다. 프로필이 다른 파일에 쓴다.")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    profile = PROFILES[a.profile]

    files = [f for f in collect(a.targets)
             if not any(x in f.name for x in a.exclude)]
    if not files:
        sys.exit("대상 문서가 없습니다.")

    # 1) 대상 전체에서 쓰인 글자를 모은다 — 한 묶음이 같은 글꼴을 공유해야 파일마다 달라지지 않는다
    chars = set()
    for f in files:
        chars |= visible_chars(f.read_text(encoding="utf-8"))
    chars = {c for c in chars if c.strip()}
    print("대상 문서 %d건 · 고유 문자 %d자" % (len(files), len(chars)))

    tmp = HERE / "_build"
    tmp.mkdir(exist_ok=True)
    block, faces, missing = build_block(profile, chars, tmp)
    print("내장 글꼴 %d벌, 블록 %d KB (base64 포함)" % (len(faces), len(block) // 1024))
    if missing:
        print("어느 글꼴에도 없어 시스템으로 넘어가는 글자 %d자: %s" % (len(missing), "".join(missing)))

    done = skipped = 0
    for f in files:
        t = f.read_text(encoding="utf-8")
        before = len(t)
        if BEGIN in t and END in t:                       # 다시 돌리는 경우 — 갈아 끼운다
            t = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda m: block, t, count=1, flags=re.S)
        elif LEGACY_RE.search(t):                          # 표시 없던 1차분 → 표시 있는 블록으로
            t = LEGACY_RE.sub(lambda m: block + "\n", t, count=1)
        elif IMPORT_RE.search(t):
            t = IMPORT_RE.sub(lambda m: block, t, count=1)
        elif LINK_RE.search(t):                            # <link>로 받아 오던 문서(프로토타입)
            t = LINK_RE.sub("", t, count=1)
            t = t.replace("</head>", "<style>\n%s\n</style>\n</head>" % block, 1)
        else:
            skipped += 1
            print("  %-42s 글꼴 참조가 없어 건너뜀" % f.name)
            continue
        for old, new in profile["stacks"]:
            if new not in t:
                t = t.replace(old, new)
        if not a.dry_run:
            f.write_text(t, encoding="utf-8")
        done += 1
        print("  %-42s %5d KB -> %5d KB" % (f.name, before // 1024, len(t) // 1024))
    for p in tmp.glob("*"):
        p.unlink()
    tmp.rmdir()
    print("\n적용 %d건 · 건너뜀 %d건%s" % (done, skipped, " (시험 실행 — 저장 안 함)" if a.dry_run else ""))


if __name__ == "__main__":
    main()
