# document-site-generator-fixes — 허브 본문 생성기의 결함 두 가지

<!-- CHANGELOG · v1.0 · 2026-10-27: (추가) 번호 없는 2단계 제목에서 멈춤 · 상단 CHANGELOG 주석을 h1로 씀 — 원인 줄과 수정안, 대조 중 찾은 중앙 용어집 생성기의 상단 주석 노출 -->

받아 가는 저장소의 한 프로젝트 이력(2026-10-15 11:10 「허브 생성기가 읽지 못하던 작성 가이드 제목 정리」)에
남은 결함입니다. 아직 「중앙에 되돌려 보낼 것」에 등록되지 않았습니다.

## 0. 먼저 — 결함은 중앙 document-site가 아니라 프로젝트 생성기에 있습니다

중앙 `core/modules/document-site/scripts/`의 생성기 세 개를 대조했습니다.

| 생성기 | 번호 없는 `##` | 첫 줄 주석 |
|---|---|---|
| `gen_dictionary_html.py` | `##`을 모두 묶음 제목으로 받으므로 해당 없음 | **비슷한 결함 있음** — 제목으로 쓰지는 않지만 머리말 문단으로 새어 나옵니다(아래 3장) |
| `gen_intro_html.py` | md 본문을 렌더하지 않음 | 해당 없음 |
| `shell.py` | 셸 마크업만 냄 | 해당 없음 |

이력에 적힌 「허브 생성기」는 받는 쪽 프로젝트가 html-design-kit 위에 직접 만든 Markdown → 허브 본문
렌더러(프로젝트의 `scripts/docs/` 아래 두 파일)입니다. 그래서 **결함 ① · ②를 그대로 고칠 줄은 중앙에
없습니다.** 다만 「주제별 문서 허브」(`core/modules/document-site/rules/document-design.md`)를 도는 공용
렌더러를 이 모듈에 들일 때 같은 결함을 가져오지 않도록 원인과 수정안을 남기고, 받는 쪽에는 프로젝트
렌더러를 고치라는 안내로 돌려보냅니다. 대조하다 찾은 중앙 용어집 생성기의 같은 갈래 결함은 3장에
적습니다 — 이것은 중앙에서 고칩니다.

## 1. 결함 ① — 번호 없는 `##` 제목에서 「지원하지 않는 Markdown 문법」으로 멈춤

### 증상

정책 문서에 `## {번호 없는 제목}`을 하나 더하자 허브 생성이 `ValueError: 지원하지 않는 Markdown 문법:
## …`로 멈췄고, 같은 생성 작업에 묶인 허브 HTML 열 장이 함께 갱신되지 못했습니다. 받는 쪽은 그 제목을
`###`로 내려 우회했습니다.

### 원인 줄 (프로젝트 렌더러 기준)

1. 장 나누기 — 기획 문서 렌더러의 `planning_sections()`

   ```python
   split=re.split(r'^## (\d+) ([^\n]+)\n',source,flags=re.M)
   ```

   번호가 있는 `## N 제목`만 장으로 자릅니다. 번호 없는 `## 제목` 줄은 앞 장 본문에 그대로 남습니다.

2. 소제목 나누기 — 같은 파일의 `planning_fragment()`는 장 본문을 `^### `로만 자르고, 블록 렌더러
   `markdown_blocks()`는 `^#{4,6} `만 제목으로 처리합니다. `## ` 줄은 어느 쪽에도 걸리지 않아 일반 문단
   후보(`plain`)로 넘어갑니다.

3. 문단 렌더러 — 공용 블록 함수 `blocks()`

   ```python
   while i < len(lines) and lines[i].strip() and not lines[i].startswith(('|', '- ', '#')):
       ...
   if not para:
       raise ValueError('지원하지 않는 Markdown 문법: '+lines[i])
   ```

   `#`로 시작하는 줄은 문단에 넣지 않으므로 `para`가 비고, 예외로 멈춥니다.

즉 「장은 번호 있는 `##`」이라는 문서 형식을 렌더러가 강제하는데, 그 강제가 형식 검사가 아니라 렌더링
중의 예외로 드러납니다. 메시지가 「문법」을 탓해서 원인(장 번호 누락)을 찾기 어렵습니다.

### 수정안

- **입력 검사로 앞당깁니다.** 장을 자르기 전에 `^## (?!\d+ )`에 걸리는 줄을 찾아, 「`##` 제목에는 장
  번호가 필요합니다: {줄 번호} {제목} — 장이 아니면 `###`로 내립니다」로 멈춥니다. 그러면 같은 실패라도
  고칠 자리가 바로 보입니다.
- **허용하는 쪽을 고르면** 번호 없는 `##`을 장으로 받아 목차 번호 없이 싣습니다. 어느 쪽으로 할지는
  문서 형식의 결정이므로, 공용 렌더러에서는 설정(`numbered_sections: true`)으로 두고 기본은 검사로
  멈추는 쪽을 권합니다.
- **블록 렌더러의 예외 메시지**는 줄 번호와 「어느 구문 목록에 없는지」를 함께 내게 합니다.

### 점검 케이스

번호 있는 장 둘 사이에 번호 없는 `##` 하나를 둔 시험 문서를 렌더해, 위 입력 검사 메시지로 멈추는지
봅니다. 허용 설정이면 장이 셋으로 나오는지 봅니다.

## 2. 결함 ② — 문서 맨 위 CHANGELOG 주석을 페이지 제목(h1)으로 씀

### 증상

파일 CHANGELOG를 md 첫 줄 주석(`<!-- CHANGELOG · … -->`)으로 둔 문서는 허브 본문의 큰 제목이 문서 제목이
아니라 그 주석 문자열로 나옵니다. 받는 쪽은 이 결함을 알고도 고치지 않은 채 두었습니다.

### 원인 줄 (프로젝트 렌더러 기준)

```python
title=source.splitlines()[0].removeprefix('# ')        # 기획 문서 렌더러 planning_fragment()
title = text.splitlines()[0].removeprefix('# ')        # 공용 블록 렌더러 read_document()
```

첫 줄이 `# 제목`이라고 가정합니다. 첫 줄이 주석이면 `removeprefix`가 아무것도 떼지 않아 주석 전체가
제목이 됩니다. 같은 함수가 머리말에서는 `re.sub(r'<!--.*?-->', '', header, flags=re.S)`로 주석을
지우지만, 제목은 그 전에 원문 첫 줄에서 뽑습니다. 이 저장소의 규칙(`change-log-writing.md` 「파일
CHANGELOG」)은 md의 CHANGELOG를 「상단 개정 이력이나 하단 CHANGELOG 절」에 두게 하므로, 첫 줄 주석은
규칙이 허용하는 정상 입력입니다.

### 수정안

```python
def doc_title(source):
    body = re.sub(r'<!--.*?-->', '', source, flags=re.S)
    m = re.search(r'^# (.+)$', body, flags=re.M)
    if not m:
        raise ValueError('문서 제목(# …)이 없습니다')
    return m.group(1).strip()
```

제목은 주석을 지운 본문에서 처음 나오는 `# ` 줄로 찾고, 없으면 멈춥니다. 머리말(제목과 첫 장 사이)을
고를 때도 같은 주석 제거 결과를 씁니다.

### 점검 케이스

첫 줄이 CHANGELOG 주석이고 둘째 줄이 `# 시험 문서`인 md를 렌더해, 결과 HTML의 `<h1>`이 「시험 문서」이고
주석 문자열이 본문 어디에도 보이지 않는지 봅니다.

## 3. 중앙 결함 — 용어집 생성기가 상단 주석을 머리말로 보임

### 증상

2026-10-27 이 작업본에서 재현했습니다. 첫 줄이 `<!-- CHANGELOG · … -->`인 용어집 md를 만들면, 결과
HTML의 머리말 문단에 `&lt;!-- CHANGELOG · … --&gt;`가 글자 그대로 보입니다(제목 아래 리드 자리).

```text
python core/modules/document-site/scripts/gen_dictionary_html.py {임시}/probe-dictionary.md \
    --css core/modules/document-site/design-guide/design-guide-master.css -o {임시}/out.html
→ out.html 안에 「&lt;!-- CHANGELOG · v1.1 · 2026-10-27: (추가) 시험 --&gt;」가 머리말 문단으로 들어감
```

### 원인 줄

`core/modules/document-site/scripts/gen_dictionary_html.py`의 `parse()` (64~95번 줄)

```python
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("# "):
            continue
        ...
        if cur is None:
            if s:
                buf.append(s)          # 첫 묶음 앞의 모든 줄을 머리말 문단으로 모읍니다
```

첫 `##` 앞의 비지 않은 줄은 `# ` 제목만 빼고 전부 머리말 문단이 됩니다. HTML 주석을 거르는 단계가
없습니다. 출력할 때 이스케이프하므로 주석이 아니라 글자로 보입니다.

### 수정안

`parse()` 첫머리에서 주석을 지우고 시작합니다.

```python
def parse(text):
    """(머리말 문단들, [(묶음, [(용어, 요약, 정본), …]), …])"""
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)   # 파일 CHANGELOG 주석은 본문이 아닙니다
    lead, groups = [], []
```

`re`는 이미 불러와 있습니다. 파일 CHANGELOG 줄에 `(변경) 상단 주석을 머리말에서 제외`를 더합니다.

### 점검 케이스

`core/modules/document-site/check.py`가 이미 시험 용어집을 한 장 만듭니다. 그 시험 md의 첫 줄에
CHANGELOG 주석을 넣고, 결과 HTML에 `CHANGELOG` 글자가 `<!--` 주석 밖에 없는지 봅니다.

## 4. 중앙에서 할 일

1. **지금** — 3장의 용어집 생성기 수정과 점검 케이스를 넣습니다. 태그: `{프로젝트 용어집 HTML}
   재생성해야 함`(상단 주석이 있는 용어집 md를 가진 프로젝트만 결과가 바뀝니다).
2. **공용 렌더러를 들일 때** — 결함 ① · ②의 수정과 점검 케이스를 처음부터 넣습니다(`product-hub.md`
   「4. 본문 렌더러」).
3. **들이기 전까지** — 받는 쪽에 「프로젝트 렌더러의 두 자리를 이렇게 고친다」는 안내를 되돌려 보냅니다.
   태그: `{프로젝트 허브 렌더러} 직접 수정해야 함`.
