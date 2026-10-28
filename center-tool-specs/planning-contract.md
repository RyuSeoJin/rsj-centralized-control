# 도구 명세 — 정본 입력 계약 검사(`planning_contract.py`)

<!-- v1.0 · 2026-10-27: (추가) app-simulator 「정본 입력 계약 검사」를 모듈 도구로 옮기는 명세 -->

규칙 본문은 `core/modules/app-simulator/rules/simulator.md` 「정본 입력 계약 검사」입니다. 이 문서는 그 검사를
모듈 도구로 옮길 때의 구현 명세이며, 중앙 저장소에서 구현한 뒤에는 지웁니다(규칙에 복제하지 않습니다).

## 1. 왜 모듈 도구로 옮기나

지금은 프로젝트 생성기가 같은 검사를 직접 구현합니다. 프로젝트마다 다시 짜면 오류 문구 · 지문 계산 방식이
갈라지고, 지문이 다르게 계산되면 `--check`가 서로 다른 것을 비교하게 됩니다. 정본 노드 표를 읽는 함수
(`read_node_table`)가 이미 workflow-explorer에 있으므로 같은 자리에 둡니다.

## 2. 자리와 공개 함수

자리: `core/modules/workflow-explorer/scripts/planning_contract.py`(app-simulator는 탐색기 없이도 동작하므로
app-simulator에 두지 않습니다. app-simulator 규칙은 이 도구를 「탐색기와 함께 쓸 때」로 가리킵니다).

```python
def spec_text(path) -> str
    """정본 Markdown 본문. 본문의 `\~`(취소선 방지 표기)를 `~`로 되돌립니다. 해시는 원본 바이트로 계산합니다."""

def read_identity(text, *, id_pattern, revision_pattern) -> tuple[str, str] | None
    """정본 머리의 ID 줄과 개정 줄을 읽습니다. 형식은 프로젝트가 정규식으로 넘깁니다."""

def load(specs, *, implemented_states, contract_text='', contract_revision='') -> dict
    """정본 목록을 읽어 계약을 검사하고 생성 입력(payload)을 돌려줍니다. 어기면 ValueError로 멈춥니다.

    specs: [{'path': Path, 'required': bool, 'tables': [흐름 코드, …]}, …]
           required가 참이면 ID·개정 줄이 없을 때 실패, 거짓이면 건너뜁니다(참고 문서).
    implemented_states: 시뮬레이터가 구현한 상태 이동 이름의 집합(읽는 방법은 프로젝트 몫)
    contract_text: 표현 계약(배치 · 구획 규칙) 원문 — 지문에 함께 들어갑니다
    """

def stamp(html, payload, *, marker='PLANNING-CONTRACT') -> str
    """산출물 맨 앞에 `<!-- {marker}:{digest} -->` 줄을 붙입니다."""

def read_stamp(html, *, marker='PLANNING-CONTRACT') -> str | None
```

## 3. `load`가 하는 일과 오류 문구

| 순서 | 검사 | 오류(`ValueError`) |
|---|---|---|
| 1 | `required` 정본마다 ID · 개정 줄 | `정본 ID·개정 누락: {경로}` |
| 2 | 노드 표 읽기(`read_node_table`), 노드마다 `sourceId` 붙이기 | 표 오류는 `read_node_table`의 것 그대로 |
| 3 | 전체 노드 ID 중복 | `정본 노드 ID 중복: {ID 목록}` |
| 4 | 연결의 도착 노드 존재 | `정본에 없는 도착점: {ID}` |
| 5 | 노드 `state` ⊆ `implemented_states` | `시뮬레이터 상태 이동 미구현: {정렬한 키 목록}` |

돌려주는 값:

```json
{"sources": [{"id": "spec-…", "revision": "canonical-03", "path": "…", "sha256": "…"}],
 "nodes": [], "edges": [], "states": ["…"], "checks": ["판정 경로 …"],
 "reproductionRevision": "…", "digest": "{sha256}"}
```

`digest` = SHA-256( `json.dumps(payload 중 digest를 뺀 것, sort_keys=True, ensure_ascii=False)` + `contract_text` ).
경로는 저장소 루트 기준 `/` 구분으로 적어, 운영체제가 달라도 같은 지문이 나오게 합니다.

## 4. `build_simulator.write_or_check`와의 연결

- 프로젝트 생성기는 `load` → 시뮬레이터 조립 → `stamp` → 탐색기 조립 → `stamp` 순서로 두 산출물을 만듭니다.
- `--check`는 지금처럼 재생성 결과와 파일을 비교하고, 그에 더해 두 산출물의 `read_stamp` 값이 서로 같은지 봅니다.
  다르면 `두 산출물의 정본 입력 지문이 다릅니다: {a} ≠ {b}`로 실패합니다.

## 5. 점검(`check.py`)에 더할 경우

임시 폴더에 정본 두 개를 만들고 다음을 확인합니다.

1. 정상 입력에서 `load`가 성공하고, 같은 입력이면 `digest`가 같습니다.
2. `required` 정본의 개정 줄을 지우면 「정본 ID·개정 누락」으로 실패합니다. `required`가 거짓이면 건너뜁니다.
3. 두 정본에 같은 노드 ID를 두면 「정본 노드 ID 중복」으로 실패합니다.
4. 없는 도착점을 가리키면 「정본에 없는 도착점」으로 실패합니다.
5. `implemented_states`에서 상태 하나를 빼면 「시뮬레이터 상태 이동 미구현」으로 실패하고 그 키가 문구에 나옵니다.
6. 정본 한 글자를 바꾸면 `digest`가 바뀝니다. `\~`를 쓴 정본은 `spec_text`가 `~`로 돌려줍니다.

## 6. 프로젝트 이행

원본 구현은 받아 가는 저장소의 한 프로젝트 생성기 안에 있습니다(`planning_contract.py` · 2026-10-12 도입).
모듈 도구가 생기면 프로젝트는 정본 목록 · 정규식 · 상태 이동 목록 읽기만 남기고 나머지를 모듈 함수로 바꿉니다.
바꾼 뒤 두 산출물의 지문이 바뀌는지 확인하고, 바뀌면 계산 방식 차이(경로 구분자 · 키 순서)를 이력에 적습니다.
