# {저장소 이름}

{저장소가 무엇을 하는 곳인지 한두 문장}. 이 파일은 모든 작업이 따르는 규칙의 진입점입니다.

## 중앙 규칙

규칙의 정본은 `core/`이며 **중앙 저장소에서 받아 온 사본입니다**(받은 기록: `core/.source.json`).
이 저장소에서 `core/`를 고치지 않습니다 — 고칠 것은 `repo-remaining-work.md`의 「중앙에 되돌려
보낼 것」에 적고 중앙 저장소에서 고칩니다(`core/base/rules/central-sync.md`).

- 문서 제작 요청 → `core/base/doc-playbook.md`를 처음부터 끝까지 따릅니다. **확인 ① · ②를 받기
  전에는 본문을 쓰지 않습니다.**
- 요청 범위 밖의 수정은 제안만 합니다(`core/base/rules/change-scope.md`).
- 코드를 보여 줄 때(채팅 포함) → `core/base/rules/code-example.md`.
- 커밋 · push는 요청과 승인이 있을 때만 합니다(`core/base/rules/git-rules.md`).

## 이 저장소

| 자리 | 무엇 |
|---|---|
| `workspace.json` | 저장소 이름표 — 공개 범위 · 프로젝트를 찾을 자리 · 저장소 전체 모듈 |
| `repo-change-log.md` · `repo-remaining-work.md` | 저장소 설정과 중앙 받기의 이력 · 할 일 |
| {프로젝트 자리} | {프로젝트 설명} |

## 이 저장소만의 규칙

{중앙 규칙에 없는 이 저장소의 상시 규칙 — 없으면 이 절을 지웁니다}

## 참조 규칙

<!-- gen:read-gates -->
<!-- /gen:read-gates -->
