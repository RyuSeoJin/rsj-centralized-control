<!-- CHANGELOG · v1.0 · 2026-10-27: (추가) 첫 작성 — slidekit 공통 장 나눔 · 도형 링크 · 생성 후 대조 함수의 구현 명세 -->

# slide-pagination — slidekit 장 나눔 · 도형 링크 · 생성 후 대조 구현 명세

app-planning-slides `slide-patterns.md`의 「넘치는 내용을 다음 장으로 나눕니다」 · 「링크는 도형에 겁니다」 ·
「만든 뒤 원본과 대조합니다」를 kit 공통 함수로 구현하기 위한 명세입니다. 한 업무 프로젝트의 요약본 발표물
생성기(약 680줄)에 들어 있던 장 나눔 루프 · 표 나누기 · 도형 링크 · `check()`를 패턴과 무관한 부분만 떼어
일반화했습니다. 프로젝트 고유값(쪽 좌표 · 글자 크기 · 표지 문구 · 블록 종류 이름)은 인자로 받습니다.

## 1. 자리

| 함수 · 클래스 | 자리 | 비고 |
|---|---|---|
| `group_blocks` · `paginate` · `split_table_rows` | `scripts/slidekit.py` 새 절 「장 나눔」 | 그리기와 분리된 순수 계산. 슬라이드 객체를 만들지 않으므로 점검이 쉽습니다 |
| `Deck.link_shape` · `Deck.link_url` · `Deck.resolve_links` · `Deck.page_marks` | `scripts/slidekit.py`의 `Deck` | 기존 `Deck.link`(글자 링크)는 목차 · 쪽 칸용으로 그대로 둡니다 |
| `verify_deck` | `scripts/slidekit.py` 새 절 「생성 후 대조」 | `build_slides.py`의 `run` 끝과 프로젝트 생성기가 함께 부릅니다 |
| 시험 | `check.py`에 ⑤ 「장 나눔 · 링크 · 대조」 | 아래 「시험 케이스」 |

`patterns.py`의 기존 패턴(Description 이어지는 장 등)을 이 함수로 바꾸는 일은 별도 작업입니다. 바꾸면
기존 견본 덱의 장 수가 달라질 수 있으므로 이력 태그에 「재생성해야 함」을 답니다.

## 2. 데이터 모양

```python
# 블록 — 그리기 단위. kind만 이 함수들이 읽고, 나머지 키는 그리는 쪽이 씁니다.
{"kind": "head" | "para" | "rule" | "bullet" | "note" | "table", ...}
# table 블록은 추가로
{"kind": "table", "head": [str, ...], "rows": [[str, ...], ...]}
```

- `TEXT_KINDS = {"para", "rule", "bullet", "note"}` — 「이어지는 글 묶음」을 이루는 종류. 인자로 바꿀 수 있습니다.
- `measure(block, width_in) -> float` — 블록 높이(in). 그리는 쪽이 줍니다. 기존 `est_lines` · `est_text_height` ·
  `line_height`로 계산합니다.
- `table_heights(block, width_in) -> (head_h, [row_h, ...])` — 표 머리줄과 행 높이. 그리는 쪽이 줍니다.

## 3. `group_blocks(blocks, text_kinds=TEXT_KINDS) -> list[dict]`

각 블록에 묶음 번호 `gid`를 붙인 사본을 돌려줍니다.

```
gid = 0; in_head = False; prev_text = False
for b in blocks:
    is_text = b.kind in text_kinds
    if b.kind == "head":
        gid += 1; in_head = True
    elif not in_head and not (is_text and prev_text):
        gid += 1
    prev_text = is_text
    yield b + {gid}
```

- 소제목이 한 번 나오면 다음 소제목 전까지 표를 포함한 모든 블록이 그 묶음입니다.
- 소제목이 없는 자리에서는 글 블록끼리 이어지면 같은 묶음, 표가 끼면 표가 새 묶음이고 그 뒤 글도 새 묶음입니다.

## 4. `paginate(blocks, measure, table_heights, *, top, bottom, width_first, width_rest, keep_with_next=1.0, min_rows_first=3) -> list[list[Placed]]`

블록을 장별로 나눈 결과를 돌려줍니다. `Placed = (block, y, height, width)`. 그리지 않습니다.

- `width_first` — 첫 장 본문 폭(곁 칸이 있으면 좁음). `width_rest` — 이어지는 장 폭(전체 폭).
- 블록은 `group_blocks`를 거친 것이어야 합니다(없으면 안에서 부릅니다).

```
queue = grouped(blocks); pages = []
while queue:
    page_no += 1; w = width_first if page_no == 1 else width_rest
    y = top; placed = []; last_gid = None
    while queue:
        b = queue[0]; h = measure(b, w)
        # ① 묶음 단위 넘김 — 묶음의 첫 블록에서만 판단
        if placed and b.gid != last_gid:
            group = 앞에서부터 같은 gid인 연속 블록
            if y + Σ measure(g, w) > bottom and top + Σ measure(g, width_rest) <= bottom:
                break                                  # 다음 장에서 한 번에
        # ② 소제목은 다음 블록과 함께
        if b.kind == "head" and len(queue) > 1 and placed:
            if y + h + min(measure(queue[1], w), keep_with_next) > bottom:
                break
        # ③ 넘침
        if y + h > bottom:
            if b.kind == "table":
                first, rest = split_table_rows(b, table_heights, w, bottom - y, fresh=not placed, min_rows_first)
                if first: placed.append((first, y, …)); queue[0] = rest; break
            if placed: break
            raise PaginationError(b, "블록 하나가 한 장보다 깁니다" 또는 "표 한 행이 한 장보다 깁니다")
        placed.append((b, y, h, w)); queue.pop(0); y += h; last_gid = b.gid
    pages.append(placed)
```

- ①의 둘째 조건(새 장에는 들어감)이 거짓이면 묶음이 한 장보다 긴 경우이므로 넘기지 않고 지금 장에서 이어 씁니다.
  이렇게 해야 긴 묶음이 매 장 넘겨져 빈 장이 끝없이 생기지 않습니다.
- 새 장에 아무것도 놓지 못하는 블록은 `PaginationError`(블록 종류 · 첫 글 40자 · 높이 · 남은 자리)를 냅니다.
  호출한 쪽이 그대로 실패로 보고합니다. 글자를 줄여 다시 시도하지 않습니다.
- 결과는 입력이 같으면 항상 같습니다(무작위 · 시각 의존 없음).

## 5. `split_table_rows(block, table_heights, width, room, *, fresh, min_rows_first=3) -> (first | None, rest)`

```
head_h, row_hs = table_heights(block, width)
used = head_h + TABLE_PAD; n = 0
for h in row_hs:
    if used + h > room: break
    used += h; n += 1
if n == 0 or (not fresh and n < min(min_rows_first, len(rows))):
    return None, block                       # 표 전체를 다음 장으로
if len(rows) - n == 1 and n > min_rows_first:
    n -= 1                                   # 마지막 한 행만 넘어가지 않게
return block(rows=rows[:n]), block(rows=rows[n:])   # 두 쪽 모두 head를 그대로 가짐 → 머리줄 반복
```

- `fresh`는 「새 장의 첫 블록」입니다. 새 장에서는 한두 행만 들어가도 나눕니다 — 넘겨도 더 나아지지 않습니다.
- `TABLE_PAD`는 표 위아래 여백(기존 표 그리기와 같은 값)입니다.

## 6. 이어지는 장 표시 — `Deck.page_marks(groups, size=None, color=SUB)`

- `groups`: `{제목 키: [slide, ...]}`. 생성기가 장을 만들 때 같은 제목의 장을 모읍니다.
- 장이 둘 이상인 묶음만, 제목 상자(`name == "title"`)의 첫 문단 끝에 글 조각 `"  (k/n)"`을 더합니다.
- 크기 기본값은 제목 크기의 약 60%(제목 26pt면 16pt), 색은 옅은 색(`SUB`). 굵게 하지 않습니다.
- 한 장뿐인 제목에는 붙이지 않습니다. 「(계속)」은 쓰지 않습니다.
- 덱을 다 만든 뒤 한 번 부릅니다.

## 7. 도형 링크 — `Deck.link_shape` · `Deck.link_url` · `Deck.resolve_links`

```python
deck.link_shape(shape, key)         # 장 링크 예약 — key는 생성기가 정하는 대상 이름(예: ("step", 3))
deck.link_url(shape, url)           # 외부 링크 — 바로 겁니다
deck.resolve_links(targets)         # targets: {key: 쪽 번호}. 덱을 다 만든 뒤 한 번
```

- 장 링크: `shape.click_action.target_slide = deck.page_slide(page)`. 글 조각(run)에는 `hlinkClick`을 만들지 않습니다
  — 그래서 밑줄이 생기지 않습니다.
- 외부 링크: `shape.click_action.hyperlink.address = url`. 글 끝의 ↗는 그리는 쪽이 넣습니다.
- `resolve_links`에서 key의 쪽을 찾지 못하면 링크를 걸지 않고 경고 목록에 `(도형 이름, key)`를 남깁니다.
  `verify_deck`가 이 목록을 문제로 올립니다.
- 지금 장을 가리키는 칸은 생성기가 예약하지 않습니다(함수가 막지 않습니다).
- 기존 `Deck._link_colors`(테마 링크 색을 잉크색으로)는 그대로 둡니다.

## 8. 생성 후 대조 — `verify_deck(pptx_path, expected, rendered, *, clean=None, markers=MD_MARKERS, images=(), counts=(), link_warnings=(), est_overflow=True) -> list[str]`

| 인자 | 뜻 |
|---|---|
| `expected` | 입력에서 기대한 글 목록(문장 · 규칙 · 하위 항목 · 소제목 · 표 칸 · 개요 · 의도 표 칸 등) |
| `rendered` | 그리는 함수가 실제로 그린 글을 모은 목록 |
| `clean` | 두 목록에 같은 정리 함수를 적용합니다. 생성기가 입력을 그릴 때 쓴 것과 같은 함수를 넘깁니다 |
| `markers` | 기본 `("**", "\\~", "](", "`")` |
| `images` | 넣기로 한 그림 경로 목록 — 있는지 봅니다 |
| `counts` | `[(이름, 기대 수, 실제 수), ...]` — 예: 흐름 띠 칸 수와 단계 수 |
| `link_warnings` | `resolve_links`가 남긴 목록 |

검사 순서와 문제 문구:

1. **빠진 글** — `[e for e in expected if e not in set(rendered)]`. 있으면 `빠진 글 N개: {처음 3개}`.
2. **남은 표시 기호** — pptx를 zip으로 열어 `ppt/slides/slide*.xml`마다 `<a:t>…</a:t>`의 글을 이어 붙이고,
   `markers`가 들어 있으면 `slide{n}.xml에 Markdown 표시 {기호}`. 이 검사는 `expected`가 아니라 실제 파일을 봅니다.
3. **넘친 글** — `est_overflow`가 참이면 글 상자마다 `est_text_height(글, 상자 폭 - 여백, 글자 크기)`가 상자 높이보다
   0.05in 넘게 크면 `slide{n} {도형 이름}: 글이 상자보다 깁니다(어림)`. 어림 검사이므로 렌더링 확인을 대신하지 않습니다.
4. **그림** — 없는 파일마다 `없는 그림 {경로}`.
5. **개수** — 다르면 `{이름} {기대} · 실제 {실제}`.
6. **링크** — `link_warnings`마다 `링크 대상을 찾지 못함 {도형} → {key}`.

문제 목록을 돌려줄 뿐 종료하지 않습니다. 생성기가 보고서에 담고, 하나라도 있으면 종료 코드 1로 끝냅니다.

### 보고서

생성기는 실행마다 출력 폴더에 `build-report.json`을 씁니다.

```json
[{"file": "brief-account-profile.pptx", "input": "brief/brief-account-profile.md",
  "inputSha256": "…", "slides": 14,
  "sections": [{"no": 1, "title": "프로필 보기", "pages": [4, 5]}],
  "problems": [], "rendered": false}]
```

- `rendered`는 렌더링으로 넘침을 확인했는지입니다. 렌더러(PowerPoint · LibreOffice)가 없어 확인하지 못했으면
  `false`로 두고, 사람에게 하는 보고에도 「렌더링 확인 못 함」을 적습니다.
- 한 덱만 다시 만들 때(`--only`)는 기존 보고서의 그 덱 항목만 바꿉니다. 원래 생성기는 이때 보고서를 쓰지 않았습니다.

## 9. 시험 케이스 (check.py ⑤)

가짜 `measure`(블록마다 고정 높이)와 `table_heights`로 순수 계산 함수를 시험하고, 작은 덱 하나로 링크와 대조를 시험합니다.
`top=0, bottom=10`(단위 in)으로 둡니다.

| # | 입력 | 기대 |
|---|---|---|
| 1 | `group_blocks([head, para, table, head, rule])` | gid `[1, 1, 1, 2, 2]` |
| 2 | `group_blocks([para, rule, table, para, bullet])` | gid `[1, 1, 2, 3, 3]` |
| 3 | `[para 6, table 1, para 3, bullet 3]` — 마지막 두 블록이 한 묶음(높이 6), 1장 남은 자리 3 | 마지막 묶음이 통째로 2장. 1장에는 para · table만 |
| 4 | `[para 6, table 1, rule 4, rule 4, rule 4]` — 마지막 묶음 높이 12로 한 장보다 김 | 묶음을 넘기지 않고 블록 단위로 이어 씀: 1장 para · table, 2장 rule · rule, 3장 rule. 빈 장 없음 · 무한 반복 없음 |
| 5 | 높이 9.5 글 다음 소제목(0.5) + 글(2) | 소제목이 1장 끝에 홀로 남지 않고 2장으로 |
| 6 | 1장 남은 자리에 표 2행만 들어감(전체 10행) | 표 전체가 2장으로 |
| 7 | 1장에 표 9행 들어감(전체 10행) | 1장 8행 · 2장 2행, 두 쪽 모두 같은 `head` |
| 8 | 새 장에서 표 1행만 들어감 | 나눔(fresh) |
| 9 | 표 한 행이 높이 11 | `PaginationError`, 메시지에 「표 한 행」 |
| 10 | 글 블록 하나가 높이 11 | `PaginationError`, 메시지에 「블록 하나」 |
| 11 | 같은 입력을 두 번 | 같은 결과 |
| 12 | `page_marks` — 같은 제목 3장 · 1장 | 3장에 `(1/3)(2/3)(3/3)`, 1장에는 없음 |
| 13 | `link_shape` 후 `resolve_links` | 도형의 click action이 대상 장, 그 도형 글 조각에 `hlinkClick` 없음 |
| 14 | 없는 key로 `link_shape` | `link_warnings`에 남고 `verify_deck`가 문제로 올림 |
| 15 | 글에 `**굵게**` · `2\~16자` · `[a](b)` · `` `코드` ``가 남은 덱 | 기호마다 문제 하나 |
| 16 | `expected`에 있는 표 칸 하나를 그리지 않음 | `빠진 글 1개` |
| 17 | 높이 0.3in 상자에 긴 글 | 넘친 글(어림) 문제 |
| 18 | 깨끗한 덱 | 문제 0 |

## 10. 원래 코드와 다른 점

- 쪽 좌표 · 곁 칸 폭 · 글자 크기 · 블록 종류 이름을 상수에서 인자로 바꿨습니다.
- 장 나눔을 그리기와 분리했습니다(원래는 한 루프에서 계산과 그리기를 함께 했습니다).
- 소제목을 다음 블록과 함께 두는 기준값(원래 1.0in 고정)을 `keep_with_next` 인자로 뺐습니다.
- 「참조 줄」을 장 바닥에 붙이던 특수 처리는 원래 프로젝트에서도 없앤 기능이라 옮기지 않았습니다.
- 넘친 글의 어림 검사와 링크 대상 누락 검사를 더했습니다(원래는 렌더링을 사람이 보는 것뿐이었습니다).
- 보고서에 `rendered`를 더했고, 한 덱만 만들 때도 보고서를 갱신합니다.
