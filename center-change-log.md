# center-change-log — 중앙 규칙(core/)에 일어난 일

중앙 규칙과 이 저장소 구조의 변경 이력입니다. 작성 · 열람 규칙은
`core/base/rules/change-log-writing.md`이며, **중앙 규칙을 건드리기 전에 읽습니다.** 받아 가는
저장소는 새 항목의 `태그`를 처리합니다(`core/base/rules/central-sync.md` §2).

`core-v1.0.0`까지의 이력은 `archive/center-change-log-v1.0.0.md`에 보관되어 있습니다. 기본 참조
대상이 아니며, 특정 변경의 시점이나 이유를 확인할 때만 엽니다.

---

## 변경 이력 (최신이 위)

### 2026-09-27 08:05 — (정정) 이력 항목 두 개의 적용 시각

아래 두 항목의 제목 줄 시각은 실제 작업 시각이 아니라 잘못 적힌 값입니다. 커밋 본문이 제목 줄
그대로를 가리키고 있어 제목은 고치지 않고 여기에 실제 시각을 남깁니다(`change-log-writing.md` §3).

| 항목 제목 (제목 줄 그대로) | 실제 시각 | 커밋 |
|---|---|---|
| 두 중앙 규칙 병합 · UE 문서 규칙 합류 · 「2026-09-27 23:30」 | 2026-09-27 07:52 | `f00faf2` |
| 주소로 받기 · push 때도 중앙 게이트 · 그림 자리 주석 정정 · 「2026-09-28 00:50」 | 2026-09-27 07:57 | `5327435` |

qa-site 마스터 CSS의 CHANGELOG 주석 「이관 (2026-09-28 …)」도 실제로는 2026-09-27입니다.

**태그**

- 변경할 사항 없음

### 2026-09-28 00:50 — 주소로 받기 · push 때도 중앙 게이트 · 그림 자리 주석 정정

병합 뒤 점검에서 나온 세 가지를 고쳤습니다(사용자 요청).

- **주소로 받기**: `sync_core.py --from`이 git 주소를 받습니다. 임시 폴더로 얕게 받아 쓰고 지우므로
  받는 컴퓨터에 중앙 저장소를 clone해 둘 필요가 없습니다. `--ref`로 태그 · 브랜치를 고릅니다.
  받은 기록의 `source`에는 주소가 남습니다. 도구 시험(`test_sync_core.py`)을 더했습니다.
- **push 때도 중앙 게이트**: 자동 검사가 PR에서만 돌아 `main`에 직접 올린 변경은 검사 없이
  들어왔습니다. push에서도 돌게 하고, 비교 기준을 사건 종류(PR · push)에 맞게 고릅니다.
  `workspace.json` 변경 차단은 fork에서 보내는 PR에만 겁니다.
- **그림 자리 주석**: qa-site 마스터 CSS 14절 주석이 옛 자리(`base/diagrams`)를 안내하던 것을 고쳤습니다.

**태그**

- qa-site 마스터 CSS 스타일 변경할 사항 없음
1. 중앙 규칙 받기 방식 변경됨 — 로컬 폴더 대신 주소로 받을 수 있습니다(`central-sync.md` §2)

### 2026-09-27 23:30 — 두 중앙 규칙 병합 · UE 문서 규칙 합류

UE 문서 저장소의 규칙(문서 제작 절차 · 작성 원칙 · 트랙 · UE 마스터)과 앱 QA 워크스페이스의 중앙
규칙(base/modules 분리 · 읽기 게이트 · 규칙 충돌 · 이력/남은 작업 · git · 검사 도구)을 하나로
합쳤습니다. 사용자 결정 네 가지를 따랐습니다 — ① 기존 폴더는 옮기지 않고 등록만, ② 문체 검사는
규칙 문서만, ③ UE 마스터를 base 디자인으로, ④ 중앙 규칙은 이 중앙 저장소에서만 관리.
`core-v1.0.0` 판 위에 얹었으며 그 판의 이력은 보관본에 그대로 있습니다.

- **뼈대**: QA 워크스페이스의 `core/base` + `core/modules` 구조를 그대로 쓰고, UE 문서 규칙을 그 안에
  옮겼습니다. 작성 원칙(`writing-principles.md`) · 코드 표기(`code-example.md`) · HTML 출력
  (`html-output.md`) · 요청 범위(`change-scope.md`) · 중앙 받기(`central-sync.md`)를 base에 새로 두었습니다.
- **디자인**: base 마스터는 UE 마스터(v1.13)입니다. 인디고 마스터 · 셸 · 진입 페이지 생성기 · 템플릿
  01~04 · 설명 그림은 워크스페이스 모듈 `qa-site`로 옮겼습니다. `tc`는 `qa-site`를 전제합니다.
- **UE 모듈 신설**: `ue-doc`(트랙 · 카테고리 · 템플릿 01~04 · C++ 문서 규칙), `gdd`(기획서 05-A/B ·
  기획서 → 프로토타입 → 구현 · 빌드 도구), `ue-build`(명령 빌드 · 창 조작 점검 · 함정),
  `ue-localization`(시트 → UE 표준 번역).
- **도구**: 프로젝트를 `workspace.json`의 `project_roots`에서 찾고 옛 이름(대문자 · 밑줄)을 허용합니다.
  관리 파일 이름은 `{폴더}-site.json`의 `files`로 바꿀 수 있습니다. `regen.py`는 모듈 이름을 모르고
  켠 모듈의 `jobs.py`를 훑습니다. 모듈이 만드는 폴더는 `module.json`의 `creates`가 알립니다.
  `check_rules.py`는 문체를 규칙 문서에서만 보고, **규칙 문서가 적은 경로가 실재하는지**를 새로 봅니다.
  `sync_core.py`(받기 · 손댄 파일 감지)를 새로 두었습니다.
- **고친 결함**: base 문서가 모듈 안 파일을 틀린 경로로 가리키던 것, 이름표에 없는 절(§6-3)을
  가리키던 것, 저장소 주소 · 담당자 이름이 규칙에 박혀 있던 것, Windows 짧은 경로에서 실패하던 시험.
- **받는 방식**: fork 후 upstream merge 외에, `core/`만 복사해 받는 `sync_core.py`를 더했습니다.
  루트 소개 페이지(`index.html` · `structure.svg`)는 `qa-site` 모듈의 몫이 되어 이 저장소에서는
  만들지 않습니다.
- **공개 저장소 정리**: 파일 CHANGELOG의 지난 사유 줄과 템플릿 예시 값에 있던 프로젝트 이름을
  일반 표현으로 바꿨습니다(사용자 결정). 이 저장소는 공개이므로 `visibility`를 `public`으로 둡니다.
- **이력 형식**: 항목에 번호를 붙이지 않고 `### YYYY-MM-DD hh:mm — 제목`으로 씁니다. 프로젝트
  change-log 맨 위에 「현행 기준」 블록을 둡니다.

**태그**

- `core/modules/tc` · `sut` · `automation` · `llm` 규칙 본문 변경할 사항 없음
1. `workspace.json` 값 입력해야 함 — QA 워크스페이스는 `"modules": ["qa-site"]`, 공개 범위 `visibility`
2. `CLAUDE.md` 직접 수정해야 함 — `core/base/design-template/repo/CLAUDE.md` 서식을 기준으로 옛 경로
   (`html-report-guide.md` · base의 `template-catalog` 목록)를 새 자리로 바꾸고 참조 규칙 표시 주석을 둠
3. 루트 `structure.svg` 방식 변경됨 — 구조도는 그 저장소 것이라 core 밖 루트에 둡니다
4. `center-change-log.md` · `center-remaining-work.md` 방식 변경됨 — 받는 저장소는 `repo-change-log.md` ·
   `repo-remaining-work.md`를 씁니다
5. 프로젝트 change-log 방식 변경됨 — 새 항목은 번호 없이 날짜 · 시각 제목
6. `AGENTS.md` · `CLAUDE.md` 참조 규칙 · `index.html` 재생성해야 함 — `python core/base/scripts/regen.py`
