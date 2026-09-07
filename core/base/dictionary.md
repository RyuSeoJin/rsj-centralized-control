# dictionary — 중앙 용어집 (색인)

**워크스페이스 전반의 용어** 색인입니다 — QA 용어에 한정하지 않고 절차·구조·규칙 용어도 여기 둡니다. **정의를 새로 쓰는 곳이 아닙니다** — 용어 + 한 줄 요약 + 정의가 사는 정본 문서를 가리킵니다. 정의가 두 군데 존재하면 어긋나므로, 상세는 반드시 정본 문서에서 확인합니다.

프로젝트 고유명사는 여기 두지 않는다 → 각 프로젝트의 `{프로젝트}-dictionary.html`. 배치 기준: "정의 문장에서 프로젝트 이름을 지워도 성립하는가?"

| 용어 | 한 줄 요약 | 정본 |
|---|---|---|
| Depth | 기능 트리의 계층. 화면→영역→구성 요소→세부 순으로 내려가며, 의미 있는 깊이까지만 쓴다 | `rules/depth-and-tn.md` |
| 도달 경로 뎁스 | 뎁스를 기능 분류가 아니라 앱 진입부터의 화면 도달 경로로 쓰는 방식. 영역은 TC ID 접두가 담는다 | `rules/depth-and-tn.md` §도달 경로 뎁스 |
| 뎁스 경계·소속 규칙 | 도달 경로 뎁스에서 어떤 화면이 1-Depth가 되는지(경계 기준 셋 — 합류점·전역·오버레이)와 케이스가 어디 놓이는지(소속 규칙 — 트리거 화면)를 정하는 규칙 | `rules/depth-and-tn.md` §도달 경로 뎁스 |
| 상태 축 | 게이팅·세션 상태처럼 여러 기능 단위를 가로지르는 횡단 축. 기능 단위의 [상태:] 선언과 TC 상태 열이 맞물려 기능 단위×상태 조합의 커버리지를 요구하고, 같은 값이 상태별 TC 추출 축이 된다 | `rules/depth-and-tn.md` §상태 축 |
| 기생 상태 | 자기 기능 단위가 없어 트리에 집이 없는 상태. 동작이 갈리는 기능 단위마다 [상태:]로 선언해야 하며, 선언이 그 상태의 유일한 커버리지 요구 지점이다 | `rules/depth-and-tn.md` §상태 축 |
| 케이스 (TC) | 세는 단위이자 결과를 읽는 단위. **TC ID 하나가 케이스 하나**이며 `TC-{영역코드}-{번호}` 형식이다. 검증유형과 Total Result가 케이스 단위 값이라, ID를 나누고 합치는 판단이 곧 결과를 어느 단위로 읽을지를 정한다. 쪼개는 기준은 넷(연쇄 여부·검증유형·판정 단위·선행 관계) | `rules/depth-and-tn.md` §케이스를 쪼개는 기준 · `rules/tc-sheet-format.md` §TC ID와 영역코드 |
| 확인 항목 | 실제로 확인해야 하는 문장 하나. **TC 시트의 한 행이 확인 항목 하나**다. 한 케이스가 확인 항목을 여럿 가지므로 케이스 수보다 크다 — 문서에 두 수를 함께 적는 이유다 | `rules/tc-sheet-format.md` §셀 병합 규칙 |
| TN (테스트 넘버링) | 한 케이스 **안**의 스텝 번호. 마지막 Depth에서 이어지는 동작을 1→2→3으로 눕힌 것. 케이스 사이의 순서가 아니며, **세어서 보여 주는 수치가 아니다** — 읽기 좋게 흐름을 나눈 것이다 | `rules/depth-and-tn.md` |
| Pre-Condition | 케이스 실행의 전제 상태(로그인·구독·플랫폼 등). 상태는 Depth로 쪼개지 않고 여기로 흡수한다 | `rules/depth-and-tn.md` |
| 지원 표기 (O/X/△/?) | 노드별 지원 여부. O 확인 / X 미지원 확인 / △ 부분·조건부 / ? 미확인(실측 필요) | `rules/depth-and-tn.md` |
| 우선순위 (High/Medium/Low) | 케이스의 속성(스텝 아님). High는 금전·보호·유실·중단·법규 축 | `rules/depth-and-tn.md` |
| 검증유형 | 모든 TC가 갖는 판정 방식 분류 — 결정적·확률적·루브릭·금칙. 유형이 반복 횟수와 판정 규칙을 결정한다. **반복은 자동화가 하고 사람은 어떤 유형이든 1회** | `rules/verification-types.md` · `rules/tc-sheet-format.md` §검증유형과 반복 |
| 실행 주체 | 케이스마다 정하는 「누가 수행하는가」 — 자동화 전용·공통·사람 전용. 공통은 자동화가 있으면 자동화가 돌린다 | `rules/tc-sheet-format.md` §실행 주체 |
| 결정적 (Deterministic) | 출력이 매번 같아야 하는 것 — 시스템이 보장해야 하는 값·상태 전이. 1회 실행, 불일치 즉 FAIL | `rules/verification-types.md` |
| 확률적 (Probabilistic) | 출력 품질에 의존하나 통계 임계로 관리 가능한 항목. N회 반복 후 성공률을 임계와 비교 | `rules/verification-types.md` |
| 루브릭 (Rubric) | 정량화 어려운 품질을 5점 루브릭으로 채점. 기본 합격선 4점 | `rules/verification-types.md` |
| 금칙 (Prohibited) | 단 1건도 발생하면 안 되는 항목. 우회 변형 포함 다회 시도, 0건이어야 PASS | `rules/verification-types.md` |
| 케이스 전개 | 트리 노드 하나를 정상·경계·예외·우회 네 갈래로 TC로 펼치는 규칙 | `rules/case-expansion.md` |
| 경계값 (Boundary) | 수치 제약마다 경계-1/경계/경계+1 세 점을 찍는 전개. 등호 포함 여부 확인 필수 | `rules/case-expansion.md` |
| TC 관계도 | 케이스 **사이**의 선행·실행 순서 층위(test dependency). TN과 다른 층위다 | `rules/tc-relations.md` |
| 실행 단계 | 선행을 루트까지 거슬러 올라간 깊이. 깊을수록 실행 비용이 높다 | `rules/tc-relations.md` |
| Blocked | 기능은 구현됐으나 확인할 수 없는 상태(선행 Fail·환경 결함·데이터 준비 불가 등). 사유는 실행 중 Comment에 적는다. Fail로 적으면 결함이 과대 계상되므로 Pass율 분모에서 제외하되 개수를 Summary에 별도 노출 | `rules/tc-sheet-format.md` §상태값 4종 |
| NI (Not Implemented) | 미구현이거나 스펙에 없어 실행 대상이 아닌 상태. Pass율 분모에서 제외 | `rules/tc-sheet-format.md` §상태값 4종 |
| 한 행 = 확인 항목 하나 | TC 시트의 핵심 배치 규칙. 케이스 단위 값(No·Depth·Priority·실행 주체·TC ID·검증유형)은 행마다 반복, TN·Test-Step·Note는 스텝 범위 병합. **병합 범위는 스텝 하나뿐**이며, 스텝 하나가 기대 결과를 여럿 가지면 그만큼 행이 늘어난다 — 그래서 행 수는 스텝 수가 아니라 확인 항목 수다 | `rules/tc-sheet-format.md` §셀 병합 규칙 |
| Total Result | **그 행의** Result를 Fail 우선으로 요약하는 수식 열. 같은 플랫폼에 단말이 여럿일 때 요약하는 자리이며 병합하지 않는다 | `rules/tc-sheet-format.md` |
| 명세서 시트 | `tc-sheet-master.xlsx` 안의 서식 규칙 정본 시트. `tc-sheet-format.md`와 교차 검증하는 짝 | `CLAUDE.md` §TC 시트 규칙 |
| 기능 골격 / feature-tree | 프로젝트 기능을 Depth 계층으로 정규화한 트리. 정본은 `spec/{프로젝트}-feature-tree.md` 하나뿐 | `CLAUDE.md` §정본과 파생 |
| 정본 / 파생 | 손으로 고치는 유일한 파일(정본)과 거기서 재생성되는 출력물(파생). 파생은 직접 수정 금지 | `CLAUDE.md` §정본과 파생 |
| archive | 지나간 상태를 격리 보관하는 폴더. 골격 이력과 major 개정 직전의 동결 스냅샷이 함께 들어가며, 기본 참조 금지 | `CLAUDE.md` §참조 규칙 |
| rationale | 판단 기록을 모으는 폴더. 도메인 판단(addition-rationale)과 SUT 판단(sut-rationale)을 파일로 나누며, 참조 자유 — 확정안이 아니므로 TC 기대값으로 쓰지 않음 | `doc-playbook.md` STEP 5 |
| SUT (System Under Test) | 테스트 대상 시스템. 테스트 코드가 아니라 테스트를 당하는 쪽이며, 역분석 대상과 테스트 대상이 다른 프로젝트에서는 직접 제작함 | `modules/sut/rules/sut-build.md` |
| SUT 테스트 인터페이스 | SUT가 테스트 코드에 공식적으로 열어주는 접점 — 요소 셀렉터(data-testid) · 상태 조회/제어 API · 실행 조건 파라미터(시드·결함 주입). 격리 계열 검증과 실패 재현을 가능하게 함 | `rules/sut-build.md` §1 |
| 결함 주입 매트릭스 | 행=주입한 결함, 열=담당 TC로 짠 표. 대각선만 FAIL이면 정상이고, 대각선이 PASS면 그 TC가 결함을 못 잡는다는 증거 | `rules/sut-build.md` §5 |
| change-log 이원화 | 문서 이력(항상 먼저 읽음)과 골격 이력(기본 참조 금지)을 분리하는 규칙 | `CLAUDE.md` §참조 규칙 |
| remaining-work | 할 일의 정본 파일. 다음 작업 큐·결정 대기·백로그 3섹션이며 완료 항목은 삭제(완료 기록은 change-log 담당). 작업 전 change-log와 함께 항상 읽음 | `rules/remaining-work.md` |
| 미확인 목록 | 정본 안의 `?` 항목 모음. 추측으로 채우지 않고 실측으로 확정하는 대기열 | `doc-playbook.md` STEP 5 |
| Case A/B/C | 문서 제작 시 템플릿 판별 3분류 — 기존 템플릿 / 마스터 갱신 필요 / 신규 템플릿 필요 | `base/design-template/template-catalog.md` |
| 중앙 규칙 | 모든 프로젝트가 따르는 절차·판단 기준·형식·소개. 바뀌면 전 프로젝트에 영향을 주므로 직접 수정을 요청받지 않는 한 바뀌지 않는다 | `rules/site-structure.md` §중앙 규칙과 프로젝트 규칙 |
| 프로젝트 규칙 | 한 프로젝트 안에서만 유효한 조사·판단·확정 사양·산출물. 프로젝트끼리 서로를 오염시키지 않게 격리하는 단위 | `rules/site-structure.md` §중앙 규칙과 프로젝트 규칙 |
| 골격 재사용 | 신규 프로젝트가 기존 프로젝트 골격에서 선택분만 복사해 시작하는 절차. 복사 후 완전 독립 | `doc-playbook.md` §신규 프로젝트 시작 절차 |
| 커밋 승인 플로우 | 커밋은 사용자 요청 시 제목·본문·브랜치·저작권 게이트 결과 제시 → 승인 후 수행. push는 별도 승인 | `rules/git-rules.md` §4 |
| 저작권 게이트 | 커밋 전과 push 전 두 곳에서 도는 점검 넷. 도구는 저작권을 판단하지 않고 사람을 불러야 하는 변경인지만 가른다 | `rules/git-rules.md` §5 |
