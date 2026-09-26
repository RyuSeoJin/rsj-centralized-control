# dictionary — 중앙 용어집 (색인)

**워크스페이스 전반의 용어** 색인입니다 — 절차 · 구조 · 규칙 용어를 둡니다. **정의를 새로 쓰는
곳이 아닙니다.** 용어 + 한 줄 요약 + 정의가 사는 정본 문서를 가리킵니다. 정의가 두 군데 있으면
어긋나므로 상세는 반드시 정본 문서에서 확인합니다.

모듈의 용어는 그 모듈의 용어집에, 프로젝트 고유명사는 그 프로젝트의 용어집에 둡니다. 배치 기준은
**「정의 문장에서 프로젝트 이름을 지워도 성립하는가」**입니다(`rules/site-structure.md` §7).

| 용어 | 한 줄 요약 | 정본 |
|---|---|---|
| 중앙 규칙 | 모든 프로젝트가 따르는 절차 · 판단 기준 · 형식 · 도구. `core/`에 있고 정본은 중앙 저장소입니다 | `rules/site-structure.md` §1 |
| 프로젝트 규칙 | 한 프로젝트 안에서만 유효한 조사 · 판단 · 확정 사양 · 산출물 | `rules/site-structure.md` §1 |
| base | 안 켜면 워크스페이스가 성립하지 않는 중앙 규칙. 항상 읽습니다 | `rules/site-structure.md` §1-1 |
| 모듈 | 골라 켜는 중앙 규칙 · 서식 · 도구의 묶음. 켜지 않으면 읽지 않습니다 | `rules/feature-request.md` §3 |
| 워크스페이스 모듈 | 저장소 전체에 켜는 모듈(`scope: workspace`). `workspace.json`의 `modules`에 적습니다 | `rules/feature-request.md` §3 |
| 호스트 모듈 | 한 컴퓨터의 환경을 다루는 모듈(`scope: host`). 프로젝트에 켜지 않습니다 | `rules/feature-request.md` §3 |
| 저장소 이름표 | 저장소마다 달라지는 값을 담는 루트 `workspace.json` | `rules/site-structure.md` §3 |
| 중앙 받기 | 중앙 저장소의 `core/`를 받아 오는 절차. 받은 뒤 손댄 파일이 있으면 멈춥니다 | `rules/central-sync.md` §2 |
| 되돌려 보내기 | 받아 가는 저장소에서 발견한 중앙 규칙의 문제를 중앙 저장소에서 고치는 절차 | `rules/central-sync.md` §3 |
| 옛 프로젝트 등록 | 규칙보다 먼저 만든 폴더를 옮기지 않고 `{폴더}-modules.json`만 두어 프로젝트로 등록하는 것 | `rules/project-scaffold.md` §5 |
| 정본 / 파생 | 손으로 고치는 유일한 파일(정본)과 거기서 다시 만드는 출력물(파생). 파생은 직접 고치지 않습니다 | `rules/site-structure.md` §6 |
| 읽기 게이트 | 파일을 만들거나 고치기 전에 반드시 읽을 파일과 멈출 자리를 모은 표 | `rules/read-gates.md` |
| 착수 보고 | 게이트를 지났는지 사용자가 확인하도록 작업 전에 내는 다섯 줄 | `rules/read-gates.md` |
| 현행 기준 | 프로젝트 change-log 맨 위의 블록. 지금의 정본 · 용어 · 상시 규칙을 비춥니다 | `rules/change-log-writing.md` §2 |
| remaining-work | 할 일의 정본. 다음 작업 큐 · 결정 대기 · 백로그이며 끝난 항목은 지웁니다 | `rules/remaining-work.md` |
| 고정 식별자 | 이력 항목을 가리키는 「종류 + 제목 + 날짜 시각」. 번호 대신 씁니다 | `rules/change-log-writing.md` §3 |
| 파일 CHANGELOG | 파일 상단 주석에 버전별로 적는 추가 · 변경 · 제거 기록 | `rules/change-log-writing.md` §4 |
| 확인 ① · ② | 문서 제작에서 본문 전에 받는 두 확인 — 아웃라인 방향 · 템플릿과 저장 위치 | `doc-playbook.md` STEP 2 · 3 |
| Case A/B/C | 템플릿 판별 세 갈래 — 기존 템플릿 / 마스터 갱신 필요 / 신규 템플릿 필요 | `design-template/template-catalog.md` |
| 마스터 | 색 · 글꼴 · 컴포넌트의 정본 CSS와 그 시각 규칙서 | `design-template/template-catalog.md` · `rules/html-output.md` §1 |
| 스냅샷 inline | 산출물에 생성 시점의 마스터 CSS를 통째로 넣어 이후 개정에 영향받지 않게 하는 방식 | `rules/html-output.md` §1 |
| 글꼴 내장 | 문서가 쓰는 글자만 남긴 글꼴 서브셋을 파일에 담아 네트워크 요청을 없애는 것 | `rules/html-output.md` §2 |
| 탐색 층 | 허브 · 용어집 · 셸처럼 문서 사이의 이동을 맡는 자리. 본문은 다른 문서로 링크하지 않습니다 | `rules/html-output.md` §5 |
| 작성 원칙 | 처음 보는 사람도 혼자 따라 하게 쓰는 기준 — 용어 풀이 · 구체 절차 · 전제와 결과 · 근거 | `rules/writing-principles.md` |
| 교육용 압축 | 여러 자리의 코드를 설명을 위해 한 블록에 모은 것. 반드시 압축임을 적습니다 | `rules/code-example.md` §2 |
| 커밋 승인 플로우 | 검사 셋 → 제안 → 제목 · 본문 · 브랜치 · 검사 결과 제시 → 승인 뒤 커밋. push는 별도 승인 | `rules/git-rules.md` §4 |
| 저작권 게이트 | 커밋 전과 push 전에 도는 점검 넷. 도구는 사람을 불러야 하는 변경인지만 가릅니다 | `rules/git-rules.md` §5 |
| 판단 사다리 | 규칙끼리 어긋날 때 위에서부터 보는 여섯 단의 기준 | `rules/rule-conflict.md` |
| 요청 범위 | 요청을 완수하는 데 필요한 수정과 거기 기계적으로 따라오는 동기화까지. 그 밖은 제안만 합니다 | `rules/change-scope.md` |
