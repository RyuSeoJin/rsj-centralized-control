# tc — 테스트 케이스를 설계하고 시트로 냅니다

기능을 Depth 트리로 정규화하고, 노드마다 검증유형을 판정하고, 케이스를 전개해 실행용
TC 시트(xlsx)로 냅니다. 커버리지 대조로 「빠진 것이 없는가」를 기계가 확인합니다.

## 언제 켜나

**이 프로젝트에서 테스트 케이스를 만드는가?** 만든다면 켭니다.

UI 기획과 워크플로우만 정리하고 검증은 다른 팀이 하는 프로젝트라면 켜지 않습니다.

## 켜면 따라오는 것

| | |
|---|---|
| 규칙 | `depth-and-tn` · `verification-types` · `case-expansion` · `tc-relations` · `tc-sheet-format` |
| 서식 | `design-template/` — TC 시트 기준 서식 · 입력 골격 · xlsx 서식 정본. 목록은 `tc-template-catalog.md`이며, 고르는 법은 base 카탈로그가 정본입니다 |
| 도구 | 골격 파서 · 커버리지 대조 · TC xlsx 생성 · 기능 골격/TC 시트/추적 매트릭스 HTML |
| 프로젝트에 생기는 것 | `test-case/` |
| 용어 | `tc-dictionary.md` — 이 모듈의 용어 색인 |
| 프로젝트가 정해야 하는 값 | `gate_states` · `state_default` — 이 서비스의 게이팅 상태 |

## 전제 모듈

`qa-site` — 기능 골격 · TC 시트 · 추적 매트릭스 HTML이 그 모듈의 셸(사이드바 · 상단 바)과 마스터로 그려집니다.

## 읽기 게이트

| 상황 | 읽는 파일 | 멈추는 자리 |
|---|---|---|
| 기능 골격 정본 수정 | `rules/depth-and-tn.md` · `rules/verification-types.md` | 정본 수정 · HTML 재생성 · 골격 이력 기록 · 커밋 시점 제안까지가 한 묶음입니다 |
| TC 시트 작업 | `rules/tc-sheet-format.md` · `design-template/tc-sheet-master.xlsx`의 '명세서' 시트 | 둘이 어긋나면 임의로 판단하지 않고 어느 쪽 기준인지 묻습니다 |

## 경로별 참조 규칙

| 경로 | 규칙 |
|---|---|
| `spec/{프로젝트}-feature-tree.md` | 기능 골격의 **유일한 정본**입니다. HTML과 xlsx는 여기서 다시 만드는 파생물입니다 |
| `spec/archive/{프로젝트}-tree-change-log.md` | 골격 이력 — 기본 참조 금지. 특정 기능의 행방을 물을 때만 엽니다 |
| `spec/design/` | 기획 TC의 기대값은 골격과 여기에서만 가져옵니다 |
