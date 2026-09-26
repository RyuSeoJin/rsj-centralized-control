#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# 기획서 조립 · 검사 · 글꼴 내장 (rules/gdd-workflow.md §5)
#
#   사용법:  build_gdd.sh <프로젝트 폴더> <slug> [작업폴더]
#   예)      build_gdd.sh Project/MyGame gdd-07-archive /tmp/work
#            GDD_WORK=/tmp/work build_gdd.sh Project/MyGame gdd-07-archive
#
#   입력:   <작업폴더>/<slug>-head.html  +  <작업폴더>/<slug>-body.html
#   출력:   <프로젝트 폴더>/gdd/<slug>.html
#
#   조립 순서: head → <style>마스터 CSS 통째로</style> → </head> → body
#   마지막에 글꼴 내장을 돌린다. 이 단계를 빼면 완성된 문서가 다시 네트워크 글꼴로
#   되돌아가므로 빌드에 붙박아 둔다.
# ─────────────────────────────────────────────────────────────────────────────
set -e

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CORE="$(cd "$HERE/../../.." && pwd)"
CSS="$CORE/base/design-guide/design-guide-ue-master.css"
FONTS="$CORE/base/scripts/embed_fonts.py"

DOCS="${1:?프로젝트 폴더를 지정하세요 — 예) build_gdd.sh Project/MyGame gdd-07-archive}"
SLUG="${2:?slug을 지정하세요 — 예) build_gdd.sh Project/MyGame gdd-07-archive}"
S="${3:-${GDD_WORK:?작업폴더를 인자나 GDD_WORK 환경변수로 지정하세요}}"
OUT="$DOCS/gdd/$SLUG.html"
BANNED="$DOCS/gdd/banned-terms.txt"
mkdir -p "$DOCS/gdd"

# ── 1) 조립
{ cat "$S/$SLUG-head.html"; echo; echo '<style>'; cat "$CSS"; echo '</style>'; echo '</head>'; cat "$S/$SLUG-body.html"; } > "$OUT"
echo "[built] $OUT ($(wc -c < "$OUT") bytes)"

# ── 2) 마스터 CSS에 없는 클래스 — 있으면 Case B 신호
echo "[check] classes missing from master.css:"
miss=0
for c in $(grep -o 'class="[^"]*"' "$S/$SLUG-body.html" | sed 's/class="//;s/"//' | tr ' ' '\n' | sort -u); do
  grep -q "\.$c\b" "$CSS" || { echo "  MISSING: $c"; miss=1; }
done
[ $miss = 0 ] && echo "  none"

# ── 3) 쓰지 않기로 한 용어 — 프로젝트가 gdd/banned-terms.txt에 한 줄에 하나씩 적는다
echo "[check] banned terms:"
if [ -f "$BANNED" ]; then
  pat=$(grep -v '^\s*#' "$BANNED" | grep -v '^\s*$' | paste -sd'|' -)
  if [ -n "$pat" ]; then grep -n -E "$pat" "$S/$SLUG-body.html" || echo "  none"; else echo "  (목록 비어 있음)"; fi
else
  echo "  (gdd/banned-terms.txt 없음 — 건너뜀)"
fi

# ── 4) 태그 균형
echo "[check] tag balance (div / table / svg):"
for t in div table svg; do
  o=$(grep -o "<$t[ >]" "$S/$SLUG-body.html" | wc -l); c=$(grep -o "</$t>" "$S/$SLUG-body.html" | wc -l)
  echo "  $t open=$o close=$c"
done

# ── 5) 와이어프레임 번호 — UI 표 행 수와 맞는지 눈으로 대조할 목록
echo "[check] w-mark numbers vs UI table rows (visual check list):"
grep -o '<span class="w-mark">[0-9]*</span>' "$S/$SLUG-body.html" | sed 's/[^0-9]//g' | sort -n | uniq -c | tr '\n' ' '; echo

# ── 6) 글꼴 내장 — 묶음 전체를 다시 훑는다(서브셋을 묶음이 나눠 쓴다)
echo "[fonts] embedding..."
python "$FONTS" "$DOCS" --profile docs --exclude _prototype.html | tail -3
if [ -f "$DOCS/_prototype.html" ]; then
  python "$FONTS" "$DOCS/_prototype.html" --profile prototype | tail -2
fi
