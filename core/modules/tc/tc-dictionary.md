# tc-dictionary — tc 모듈의 용어 색인

tc 모듈을 켠 프로젝트에서 쓰는 용어입니다. 정의를 새로 쓰지 않고 정의가 사는 규칙 문서를
가리킵니다. 워크스페이스 전반의 용어는 `core/base/dictionary.md`에 있습니다.

| 용어 | 한 줄 요약 | 정본 |
|---|---|---|
| Depth | 기능 트리의 계층. 화면 → 영역 → 구성 요소 → 세부 순으로 내려가며, 의미 있는 깊이까지만 씁니다 | `rules/depth-and-tn.md` |
| 도달 경로 뎁스 | 뎁스를 기능 분류가 아니라 앱 진입부터의 화면 도달 경로로 쓰는 방식 | `rules/depth-and-tn.md` §도달 경로 뎁스 |
| 상태 축 | 게이팅 · 세션 상태처럼 여러 기능 단위를 가로지르는 횡단 축 | `rules/depth-and-tn.md` §상태 축 |
| 기생 상태 | 자기 기능 단위가 없어 트리에 집이 없는 상태. 동작이 갈리는 기능 단위마다 선언합니다 | `rules/depth-and-tn.md` §상태 축 |
| 케이스 (TC) | 세는 단위이자 결과를 읽는 단위. TC ID 하나가 케이스 하나입니다 | `rules/depth-and-tn.md` · `rules/tc-sheet-format.md` |
| 확인 항목 | 실제로 확인해야 하는 문장 하나. TC 시트의 한 행입니다 | `rules/tc-sheet-format.md` |
| TN | 한 케이스 안의 스텝 번호. 세어서 보여 주는 수치가 아닙니다 | `rules/depth-and-tn.md` |
| Pre-Condition | 케이스 실행의 전제 상태. 상태는 Depth로 쪼개지 않고 여기로 흡수합니다 | `rules/depth-and-tn.md` |
| 지원 표기 | O 확인 / X 미지원 확인 / △ 부분 · 조건부 / ? 미확인 | `rules/depth-and-tn.md` |
| 우선순위 | 케이스의 속성. High는 금전 · 보호 · 유실 · 중단 · 법규 축 | `rules/depth-and-tn.md` |
| 검증유형 | 결정적 · 확률적 · 루브릭 · 금칙. 유형이 반복 횟수와 판정 규칙을 정합니다 | `rules/verification-types.md` |
| 실행 주체 | 자동화 전용 · 공통 · 사람 전용 | `rules/tc-sheet-format.md` |
| 케이스 전개 | 노드 하나를 정상 · 경계 · 예외 · 우회로 펼치는 규칙 | `rules/case-expansion.md` |
| 경계값 | 수치 제약마다 경계-1 · 경계 · 경계+1 세 점을 찍는 전개 | `rules/case-expansion.md` |
| TC 관계도 | 케이스 사이의 선행 · 실행 순서 층위 | `rules/tc-relations.md` |
| Blocked · NI | 확인할 수 없는 상태 · 미구현. Pass율 분모에서 뺍니다 | `rules/tc-sheet-format.md` |
| Total Result | 그 행의 Result를 Fail 우선으로 요약하는 수식 열 | `rules/tc-sheet-format.md` |
| 명세서 시트 | `tc-sheet-master.xlsx` 안의 서식 규칙 정본 시트 | `design-template/tc-template-catalog.md` |
| 기능 골격 | 기능을 Depth 계층으로 정규화한 트리. 정본은 하나뿐입니다 | `rules/tc-pipeline.md` §1 |
| 골격 이력 | 골격 변경만 모은 이력. 기본 참조 금지입니다 | `rules/tc-pipeline.md` §1 |
| 미확인 목록 | 정본 안의 `?` 항목 모음. 실측으로 확정하는 대기열 | `rules/tc-pipeline.md` §1 |
