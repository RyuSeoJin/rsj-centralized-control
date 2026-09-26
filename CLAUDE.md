# central-rules

문서 제작과 저장소 운영의 **중앙 규칙 정본**을 관리하는 저장소입니다. 각 작업 저장소는 이 저장소의
`core/`를 받아 쓰고(`core/base/rules/central-sync.md`), 중앙 규칙은 **여기서만** 고칩니다.
이 파일은 이 저장소에서 일할 때의 진입점입니다.

## 폴더 구조

- `core/base/` — 안 켤 수 없는 중앙 규칙. `doc-playbook.md`(문서 제작 절차) · `dictionary.md`(중앙
  용어집 색인) · `rules/`(방법론 · 운영 규칙) · `scripts/`(검사 · 재생성 · 받기 도구) ·
  `design-guide/`(기본 마스터 · 시각 규칙서 · 글꼴) · `design-template/`(고르는 법 · 프로젝트와
  저장소의 빈 서식).
- `core/modules/` — 골라 켜는 모듈. 각 모듈의 `module.md`가 자기소개(언제 켜나 · 따라오는 것 ·
  전제)입니다. 목록은 `python core/base/scripts/module.py list`로 봅니다.
- `center-change-log.md` · `center-remaining-work.md` — 중앙 규칙의 이력과 남은 일.
- `README.md` — 받아 가는 법.

**base와 modules를 가르는 기준**은 「이 규칙을 안 켠 프로젝트가 있을 수 있는가」, **중앙과 프로젝트를
가르는 기준**은 「문장에서 프로젝트 이름을 지워도 성립하는가」입니다(`core/base/rules/site-structure.md`).

## 이 저장소에서 일할 때 (필수)

1. **작업 전에 `center-change-log.md`와 `center-remaining-work.md`를 읽습니다.**
2. `core/`에 **특정 저장소 · 프로젝트의 이름 · 값 · 경로를 적지 않습니다.** 예시는 자리 표시자로 씁니다.
3. base 문서는 모듈 이름이나 모듈 안의 파일을 가리키지 않습니다. `check_rules.py`의 경로 검사가 잡습니다.
4. 규칙을 바꾸면 `center-change-log.md`에 항목과 **태그**(받아 가는 쪽의 할 일)를 적습니다.
5. 커밋 전에 검사 셋을 돌립니다 — `regen.py --check` · `check_rules.py` · 모듈 점검
   (`python core/modules/{모듈}/check.py`) · 도구 시험(`python -m unittest discover -s core/base/scripts -p "test_*.py"`).
6. 커밋 · push · 태그는 요청과 승인이 있을 때만 합니다(`core/base/rules/git-rules.md`). 이 저장소의
   커밋 영역은 `[Center]`입니다.
7. 요청 범위 밖의 수정은 제안만 합니다(`core/base/rules/change-scope.md`).

## 참조 규칙

<!-- gen:read-gates -->
| 경로 | 규칙 |
|---|---|
| `core/modules/` | **기본 참조 금지.** 프로젝트 모듈은 그 프로젝트의 `{폴더}-modules.json`에 켜져 있을 때만, 워크스페이스 모듈은 `workspace.json`의 `modules`에 있을 때만 읽습니다. `scope: host` 모듈은 그 컴퓨터의 환경을 다룰 때만 읽습니다 |
| 프로젝트의 change-log | 작업 전 **항상 먼저 읽습니다** — 「현행 기준」 블록이 현재 정본 · 용어 · 상시 규칙입니다. 작성 규칙은 `core/base/rules/change-log-writing.md` |
| 프로젝트의 remaining-work | 작업 전 **항상 먼저 읽습니다** — 할 일의 정본(다음 작업 큐 · 결정 대기 · 백로그). 규칙은 `core/base/rules/remaining-work.md` |
| `{폴더}-structure.json` | 등록된 자료의 경로 · 역할 · 참조 · 생성 관계의 정본입니다. 아래 기본 자리는 설정이 없는 프로젝트의 기본안입니다 |
| `spec/design/` | **참조 자유.** 확정 사양 — 기대값과 판정 기준은 여기서만 가져옵니다 |
| `spec/rationale/` | **참조 자유.** 판단 기록 — 확정안이 아니므로 기대값으로 쓰지 않습니다 |
| `spec/archive/` · 구조 설정의 archive 역할 | **기본 참조 금지.** 지나간 상태입니다. 사용자가 특정 기능의 행방 · 이력을 물을 때만 열어 「언제 삭제 · 수정되어 현재 미사용」 형태로 답합니다 |
| `analysis/` · `reference/` | 조사 자료입니다. 수치는 아직 남의 값이거나 미확정 값이라 기대값으로 쓰지 않습니다 — 확정되면 `spec/`으로 옮깁니다 |
| `core/.source.json` | 중앙 규칙을 받은 기록입니다. 손으로 고치지 않습니다 — `sync_core.py`가 씁니다 |
<!-- /gen:read-gates -->
