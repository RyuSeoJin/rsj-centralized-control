# center-remaining-work — 중앙 규칙에 남은 일

중앙 규칙(`core/`)과 이 저장소 구조에 남은 일입니다. 끝난 항목은 지웁니다. 규칙은
`core/base/rules/remaining-work.md`입니다. 특정 저장소 · 프로젝트의 이름과 값은 적지 않습니다.

---

## 다음 작업 큐

1. **QA 워크스페이스에 받기 시험** — 원래 저장소에 `sync_core.py`로 받아 `regen.py` · `check_rules.py` ·
   진입 페이지 재생성까지 통과하는지 봅니다. 산출물: 그 저장소의 `repo-change-log.md` 항목
2. **번역 도구 일반화** — 시트 ↔ `.po` 변환 도구를 `ue-localization/scripts/`로 올리고, 머리글 모양이
   다른 시트(`Key | {언어 이름}…`)도 읽게 합니다. 산출물: 도구 + `check.py`
3. **창 조작 점검 도구 일반화** — 빌드 · 실행 · 스크린샷 · 앞 창 확인 입력을 경로 자리 표시자로
   바꿔 `ue-build/scripts/`로 올립니다. 산출물: 도구 + `check.py`
4. **범위 물결표 규칙과 도구** — 규칙 「Markdown 범위 물결표는 `\~`로 씁니다」는 중앙 생성기가 `\~`를
   되돌리지 못해 보류했습니다(2026-10-28 사용자 결정). 규칙 원문은 커밋 `b6acdb9`의 `doc-write-style.md` 8절입니다.
   되돌리기(`unescape_tilde` — 코드 표시 · 코드 블록 · 주석 밖에서만), 산출물 누출 검사(`find_tilde_leaks`),
   원문 점검(`find_unescaped_range_tildes`)을 document-site · app-planning-slides 생성기와 `check_rules.py`에
   둔 뒤, 규칙과 용어집 행을 다시 넣습니다. 해시는 원본 바이트로 계산합니다. 구현 명세는
   `center-tool-specs/tilde-escape.md`. 산출물: 함수 + 시험 + 규칙 복원
5. **제품 공통 모듈 설정 읽기** — `site-structure.md` 「프로젝트 묶음」의 `{제품}-module-config.json`을
   `module.py` · `regen.py` · 셸 메뉴(`shell.navigation_entries`)가 읽게 합니다(업무 설정과의 합집합 ·
   중복 등록 거절). 들어오면 「현재 도구 지원 범위」 표를 고칩니다. 구현 명세는 `center-tool-specs/product-group.md`. 산출물: 도구 + 시험
6. **요약본 대조 검사기** — planning-spec 「요약본과 정본을 자동으로 대조합니다」의 다섯 검사(실행 노드 덮음 ·
   없는 ID · 깨진 상대 링크 · 외부 디자인 링크 · 정본 해시)를 `planning-spec/scripts/check_briefs.py`와 `check.py`로
   둡니다. 원본 정본은 「정본 대조」 표의 첫 행으로 찾습니다. 구현 명세는 `center-tool-specs/brief-check.md`. 산출물: 도구 + `check.py`
7. **슬라이드 쪽 나눔 · 생성 후 대조** — app-planning-slides 「넘치는 내용을 다음 장으로 나눕니다」 · 「링크는 도형에
   겁니다」 · 「만든 뒤 원본과 대조합니다」를 kit 함수(`group_blocks` · `paginate` · `split_table_rows` ·
   `Deck.page_marks` · `Deck.link_shape` · `verify_deck`)로 둡니다. 구현 명세는 `center-tool-specs/slide-pagination.md`. 산출물: 함수 + 점검 케이스
8. **정본 입력 계약 검사 도구** — app-simulator 「정본 입력 계약 검사」(ID · 개정 머리 줄 · 노드 중복 · 없는 도착점 ·
   상태 키별 이동 구현 · 입력 지문 `--check`)를 도구로 둡니다. `read_node_table`이 있는 workflow-explorer
   쪽을 제안합니다. 구현 명세는 `center-tool-specs/planning-contract.md`. 산출물: 도구 + 시험
9. **탐색기 직각 우회** — 길 찾기에 실패하면 실행기가 `var fb=first||[S,T]`로 대각선을 그립니다. 직각 우회로
   바꾸고, 그때까지 쓰는 「대각선 선분 0 검사」를 점검에 둡니다. 구현 명세는 `center-tool-specs/explorer-orthogonal-fallback.md`. 산출물: 런타임 + `check.py` 케이스
10. **탐색기 구역 경계선 폭** — `buildLanes`가 기본 상자의 구역 경계선을 하위 섹션까지 포함한 전체 폭(`_wT`)으로
   등록해, 오른쪽 하위 섹션 안의 가로선이 그 높이와 겹치면 길 찾기가 거절되고 섹션이 끝없이 넓어집니다.
   기본 상자 폭(`_w`)으로 등록합니다. 구현 명세는 `center-tool-specs/explorer-lane-border-width.md`. 산출물: 런타임 + 케이스
11. **탐색기 캡처의 흐름별 개정** — 캡처 낡음을 시뮬레이터 파일 전체 해시로 판정해 한 화면만 고쳐도 모두 다시
   찍어야 합니다. 흐름 코드별 개정(bump · stamp · apply · `--stale`)을 `capture_ui.py` ·
   `project_data.attach_thumbs`의 선택 기능으로 둡니다. 구현 명세는 `center-tool-specs/explorer-capture-scope.md`. 산출물: 도구 + 시험
12. **탐색기 도착 면 지정** — 배치 지정에 나가는 꼭짓점(`exit`)만 있고 들어갈 면이 없습니다. `exit`와 같은 형식의
   `enter`([출발, 도착, u/d/l])를 둡니다. 구현 명세는 `center-tool-specs/explorer-enter-side.md`. 산출물: 런타임 + 규칙 · 케이스
13. **와이어프레임 보드 배치 도구** — app-wireframe 「보드 배치 — 설명 상자 쌓기」(실제 바닥 기준으로 쌓기 · 행 안
   띠별 위끝 맞춤 · 연결 표식 함께 이동 · 겹침 0 확인)를 도구로 둡니다. 구현 명세는 `center-tool-specs/wireframe-board-layout.md`. 산출물: 도구
14. **원문 행 골격 도구** — tc 「기획 원문 표에서 골격을 만드는 선택지」의 생성 · `--check` · `--stamp`(행 해시
   `basis`)를 tc 도구로 둡니다. 구현 명세는 `center-tool-specs/tc-basis.md`. 산출물: 도구 + 시험
15. **tc 기능 골격 HTML 생성기 경로** — `gen_feature_tree_html.py`가 `dirname`을 세 번만 올라가 `core/modules/modules/
   document-site/…`를 찾고 실패합니다(같은 실행의 다른 작업도 멈춤). 파일 기준 상대 경로로 고치고 `check.py`에
   골격 HTML 생성 한 번을 더합니다. 구현 명세는 `center-tool-specs/tc-feature-tree-path-fix.md`. 산출물: 수정 + 케이스
16. **용어집 생성기의 상단 주석** — document-site `gen_dictionary_html.py`가 md 첫 줄의 파일 CHANGELOG 주석을
   머리말 문단에 글자로 보입니다. `parse()`가 주석을 먼저 지우게 합니다. 같은 갈래의 결함(번호 없는 `##`에서
   멈춤 · 주석을 h1로 씀)을 공용 렌더러를 들일 때 함께 막습니다. 구현 명세는 `center-tool-specs/document-site-generator-fixes.md`. 산출물: 수정 + 케이스
17. **묶음 허브 생성기** — document-site 「묶음 허브 — 통합 허브와 업무별 허브」의 생성기를 둡니다. 구현 명세는 `center-tool-specs/product-hub.md`.
   산출물: 도구 + 시험
18. **app-wireframe 규칙의 서비스 용어** — `wireframe.md` 「화면과 상태를 배치합니다」 · 「순서도 배치」에 특정 서비스의
   첫 체험 흐름 이름이 남아 있습니다. 「첫 체험 · 일반」처럼 일반 표현으로 바꿉니다.
19. **출시 스펙 확정 점검표 생성기** — planning-spec 「출시 스펙 확정 점검표는 정본에서 만듭니다」의 생성기를
   planning-spec 도구로 둡니다(정본 폴더 · 출력 · 먼저 정할 것 설정을 인자로 받음 · 「만든 날」을 뺀 `--check`).
   요약본 대조 검사기와 같은 때 넣으면 `check.py` 하나로 둘을 봅니다. 구현 명세는
   `center-tool-specs/launch-checklist.md`. 산출물: 도구 + `check.py`
20. **document-site 점검이 다른 드라이브에서 실패함** — `core/modules/document-site/check.py`가 임시 폴더에
   견본을 만들어 `gen_dictionary_html.py`를 돌리는데, 생성기가 `os.path.relpath`로 입력과 저장소의 상대 경로를
   구합니다. Windows에서 임시 폴더와 저장소의 드라이브가 다르면 `ValueError`로 멈춥니다(2026-10-28 확인 ·
   임시 폴더 C:, 저장소 E:). 점검의 임시 폴더를 저장소와 같은 드라이브에 만들지, 생성기가 다른 드라이브를
   견디게 할지 정해 고칩니다. 산출물: 수정 + 점검 통과

## 사용자 결정 대기

- **중앙 버전 태그** — 이번 병합 상태에 `core-v2.0.0`을 달지. 옛 판이 `v1.0.0`이고 구조 · base 디자인이
  바뀌어 주 버전이 오릅니다. 달면 `change-log-writing.md` §7에 따라 보관 이력을 자르는 시점입니다.
- **독자용 산출물 문체의 기본값** — `doc-write-style.md` 「독자용 산출물 문체」를 지금처럼 프로젝트가
  고르는 선택지로 둘지, 독자용 산출물의 기본값으로 올릴지.
- **파일 CHANGELOG 모양** — 2026-10-27에 고친 base · 모듈 문서 상단에 버전 블록형 기록(v1.1)을 더했습니다. 기존
  하단 한 줄 기록과 둘 중 하나로 통일할지.
- **제품 공통 모듈의 `creates` 폴더** — 제품에서 켠 모듈의 폴더를 묶음의 모든 업무에 만들지.
  `project-scaffold.md` 「폴더는 필요할 때 생깁니다」와 부딪칩니다.
- **소개 페이지 규칙 묶음** — document-site `gen_intro_html.py`의 `RULE_GROUPS`에 `completion-evidence.md`
  (「무엇을 어떤 순서로 하는가」) · `external-material.md`(「문서를 어떻게 쓰고 어디에 두는가」)를 넣을지.
  지금은 「그 밖에」로 떨어집니다.
- **발표물 목차 링크** — app-planning-slides는 목차 · 쪽 칸만 글자 링크(밑줄을 누름 표시로)로 남기고 나머지를
  도형 링크로 정했습니다. 목차도 도형 링크로 통일할지(`Deck.link` 변경). 공유본으로 바꾼 뒤 도형 링크가
  동작하는지는 확인하지 못했습니다.
- **탐색기 구역 상자 폭** — 구역 상자를 기본 상자 폭으로 줄이면 하위 섹션 위 빈 띠가 구역 색 없이 보입니다. 이
  모양을 받아들일지.
- **분기 값과 보충 설명** — 지금은 라벨 하나에 「값 · 설명」으로 적습니다. 두 상자로 나눠 그리는 필드(`note` 등)를
  실행기에 둘지.
- **정본 입력 계약의 자리** — 규칙은 app-simulator, 도구는 workflow-explorer를 제안했습니다. 도구가 들어오면 규칙
  본문도 `explorer.md`로 옮기고 app-simulator가 가리키게 할지.
- **산출물 크기 경고** — app-simulator 「산출물 크기 예산」의 경고를 프로젝트 조립 스크립트에 맡길지,
  `build_simulator.write_or_check(..., warn_bytes=)`로 모듈 도구에 넣을지.
- **허브 규칙 파일** — document-site의 허브 규칙을 `document-design.md`에 둘지 별도 규칙 파일(예: document-hub.md)로 뗄지.
- **묶음 허브 생성기의 기반** — html-design-kit 위에 지을지(document-site에 그 전제가 생김), document-site 셸 위에
  다시 지을지. 원본 생성기는 모듈 합집합에서 저장소 모듈을 빼고 계산했습니다 — base 「프로젝트 묶음」과 다릅니다.
- **원문 행 해시 알고리즘** — `basis`를 SHA-1 앞 10자리로 유지할지. 바꾸면 받는 쪽에 기록된 `basis`가 모두
  「재검수 필요」가 되므로 변환 명령이 필요합니다.
- **묶음 단위 생성 작업** — `jobs.py`가 묶음(제품) 단위 작업을 받는 자리를 base에 둘지.
- **근거 단위 해시의 공통 원리** — tc 원문 행 `basis`와 탐색기 캡처 흐름별 개정을 「근거 단위 해시로 낡음 판정」
  한 원리로 묶어 base에 둘지.
- **용어 「독자용 요약본」** — 중앙 용어집에 등록할지.


## 백로그

- **§번호 참조를 항목 제목으로** — 원격 미배포 작업을 옮길 때 원격이 같은 자리를 새로 쓴 곳은 원격 문장을 따라
  §번호 참조가 남았습니다: `central-sync.md` 「되돌려 보내기」와 그것을 가리키는 `remaining-work.md` · 저장소 서식
  `repo-remaining-work.md`, pixel-art 규칙 · 용어집, ue-build 함정 표. `doc-write-style.md` 「참조는 문서 이름과 항목
  제목으로 씁니다」에 맞춰 바꿉니다.
- **pixel-art 사양 종류 구분** — `spec.py`의 읽기 함수는 `canvas` · `anchors`를 필수로 요구해 타일 · UI 사양을 읽지
  못합니다. 지금은 `tile_check.py` · `icon_check.py`가 JSON을 따로 읽습니다. 사양 파일에 `kind`(캐릭터 · 타일 · UI ·
  이펙트)를 두고 읽기 함수가 종류별 필수 키를 보게 할지 정합니다. `render` 절을 둘 사양 파일 자리도 함께 정합니다.
- **pixel-art 사람 검수 보조** — `lineup.py`에 실루엣(한 색 채우기) · 회색조 출력을 더하면 `pixel-style.md` §7-2 ·
  §7-3 검수를 도구로 할 수 있습니다.
- **pixel-art 엔진 설정 실측** — `pixel-render.md` §10 · `pixel-tile.md` §12의 엔진 설정 중 Unreal Paper2D의
  Pixels per unit 기본값, 저해상도 렌더 타깃 구성, Godot Terrain 모드 이름은 문서로 확인하지 못했습니다. 첫
  프로젝트에서 실제 엔진으로 확인해 고칩니다.

- app-planning-slides 기능별 문서에서 다른 기능의 화면 · 「→ F-…」 연결자를 그 기능의 기획서로 잇는 링크를 나중에 만듭니다(2026-10-12 사용자 결정 · 보류). 안: 전체 문서 `features[].doc`(필요하면 `linked_screens[].doc`)에 Google Slides 공유본 주소를 적고, 화면 주소 → 기능 문서 주소 → 「이 기능의 화면」 장 순으로 링크합니다. 지금은 「이 기능의 화면」 장으로 갑니다.

- app-planning-slides 기능 흐름도의 하위 섹션 · 서브루틴(워크플로우 탐색기 §3)은 필요할 때 옮깁니다(2026-10-12 사용자 결정). 하위 섹션 조건(한 화면의 행동 2개 이상 · 그 뒤 도형 5개 이상)에 걸리는 기능 흐름이 실제로 생기면 별도 장 · 보라 서브루틴 도형 · 오가는 슬라이드 링크로 구현하고 그 흐름으로 렌더링해 확인합니다.

- app-planning-slides 기능별 예시의 `A2-04`(마감 · 대기 제안 시트 · 이전 형식의 `n8`) 노드 다음 경로를 정합니다. 새 검사가 출구 누락을 경고합니다. 대기 신청 정책이 미결이므로 종료·복귀·다음 기능 이동 중 실제 의도를 확인한 뒤 예시 입력과 견본을 함께 갱신합니다.

- `qa-site`의 진입 페이지 생성기에 있는 「`base/design-guide/` — 형식의 정본」 카드는 이제 base 마스터
  (UE 마스터)를 가리킵니다. 문구가 사용자 확정 문구라 바꾸지 않았고, 그 저장소 사용자에게 확인이
  필요합니다(`change-scope.md` §3).
- **모듈 소개 페이지** — 옛 판의 「TC 설계 규칙」 장을 `tc` 모듈의 소개로 다시 만듭니다. 프로젝트
  데이터를 읽는 장이라 모듈이 켜졌을 때만 만들어져야 합니다.
- **모듈 삭제 절차** — 켜고 끄는 것은 도구가 하지만, 어느 곳도 안 쓰게 된 모듈을 중앙에서 지우는
  기준은 아직 없습니다.
- **원문 텍스트 감시 목록** — 저작권 게이트가 못 잡는 붙여 넣은 원문을 잡으려면 감시 단어가
  필요한데, 그 목록은 프로젝트 고유명사라 중앙에 둘 수 없습니다. 실제로 새어 나간 적이 생기면 만듭니다.
- 모듈마다 용어집 이름 규칙(`{모듈}-dictionary.md` 또는 `module.md` 절)을 하나로 정할지.
- **pixel-art 점검 두껍게** — 지금은 예시 흐름만 봅니다. 실제 프로젝트에서 걸린 것(변환이 놓친 선 ·
  슬롯 순서 어긋남 등)이 나오면 그 케이스를 모듈 점검에 더합니다.
- **pixel-art 표준 슬롯 · 기본 자세 검증** — 아직 Spine에서 열어 보지 않았습니다. 첫 프로젝트에서
  Spine에 실제로 불러 스킨 교체와 애니메이션 공유가 되는지 확인한 뒤 리깅 규약을 고칩니다.
- **aseprite 설치 도구 실측** — 새 컴퓨터에서 `aseprite_setup.py`를 처음부터 끝까지 돌려 본 적이
  없습니다. 처음 돌릴 때 걸린 것을 도구와 알려진 함정에 더합니다. macOS · Linux 경로도 아직 미확인입니다.
- **증거 보관본 해시 확인 도구** — `site-structure.md` 「증거 자료는 원문 그대로 보관합니다」의 확인(인용 표시 벗기기
  → 원문 줄바꿈으로 되돌리기 → 해시 비교)을 도구로 만들지. 지금은 규칙 문장만 있습니다.
- **md ↔ 스프레드시트 보기본** — md 정본을 시트로 보일 때 숨긴 열에 행마다 되읽기 열쇠를 두고 서식까지 담은
  xlsx 한 장으로 가져오는 방식이 한 프로젝트에서 쓰였습니다. 시트 → md 되읽기가 한 번도 돌지 않았고 근거가
  하나라 모듈로 올리지 않았습니다. 두 번째 프로젝트가 쓰거나 되읽기를 실제로 돌리면 올립니다
  (구현 명세는 `center-tool-specs/md-sheet-view.md`).
- **렌더 캡처 도구** — app-wireframe 「렌더 캡처 교체」의 정적 HTML 굳히기 · 기존 프레임 안 교체 · 아이콘
  대응을 모듈 도구로 올릴지. 지금은 규칙만 있습니다.
