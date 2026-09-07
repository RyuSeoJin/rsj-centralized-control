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
| 프로젝트에 생기는 것 | `test-case/` (골격에서 이미 만들어져 있습니다) |
| 프로젝트가 정해야 하는 값 | `gate_states` · `state_default` — 이 서비스의 게이팅 상태 |

## 전제 모듈

없습니다.
