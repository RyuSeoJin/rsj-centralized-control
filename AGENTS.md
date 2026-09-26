# AGENTS.md

<!-- core/base/rules/read-gates.md에서 생성됩니다. 직접 고치지 않습니다. -->

이 저장소의 규칙 정본은 `CLAUDE.md`와 `core/base/`입니다. 이 파일은 규칙을 새로 정의하지 않고,
**작업 전에 무엇을 읽어야 하는지**만 모아 둔 게이트입니다. 내용이 어긋나면 `CLAUDE.md`가
정본입니다.

## 읽기 게이트

파일을 만들거나 고치기 전에, 해당하는 줄을 전부 실제로 열어 읽습니다. 기억이나 요약으로
대체하지 않습니다. 켠 모듈의 `module.md`에 「읽기 게이트」 절이 있으면 그 줄도 여기에 더해 읽습니다.

| 상황 | 읽는 파일 | 멈추는 자리 |
|---|---|---|
| 모든 작업 | `CLAUDE.md` · `core/base/rules/change-scope.md` | 요청 범위 밖의 수정은 제안만 합니다 |
| 프로젝트 작업 | 그 프로젝트의 change-log(「현행 기준」 먼저) · remaining-work | — |
| 프로젝트에 구조 설정이 있을 때 | 프로젝트 루트의 `{폴더}-structure.json` · 등록된 자료의 정본과 승인 상태 | archive 역할은 특정 이력 요청 때만 읽습니다 |
| 문서 제작 (설명 · 분석 · 설계 · 기획서) | `core/base/doc-playbook.md` · `core/base/rules/writing-principles.md` | 아웃라인 확인 ①과 템플릿 판별 확인 ②를 받기 전에는 본문을 쓰지 않습니다 |
| 코드를 보여 주거나 예제 코드를 쓸 때 (채팅 포함) | `core/base/rules/code-example.md` | — |
| 문서를 쓰거나 고칠 때 | `core/base/rules/doc-write-style.md` | — |
| HTML 산출물을 만들 때 | `core/base/rules/html-output.md` | — |
| change-log에 항목을 쓸 때 | `core/base/rules/change-log-writing.md` | — |
| 「이 기능(규칙 · 서식 · 도구)을 넣고 싶다」 | `core/base/rules/feature-request.md` | 무엇이 어떻게 바뀌는지 보이고 동의를 받기 전에는 손대지 않습니다 |
| 모듈을 켜야 할 때 | 그 모듈의 `module.md` | 모듈은 저절로 켜지지 않습니다. 켜면 무엇이 따라오는지 보이고 동의를 받습니다 |
| 새 프로젝트를 시작하거나 옛 폴더를 등록할 때 | `core/base/rules/project-scaffold.md` | — |
| 중앙 규칙을 받거나 되돌려 보낼 때 | `core/base/rules/central-sync.md` · `repo-change-log.md` · `repo-remaining-work.md` | 받기는 사용자 승인 뒤에만 합니다. 이 저장소에서 `core/`를 고치지 않습니다 |
| 중앙 저장소에서 `core/`를 바꿀 때 | `center-change-log.md` · `center-remaining-work.md` | 이력의 태그를 정하기 전에는 커밋을 제안하지 않습니다 |
| 규칙끼리 어긋날 때 | `core/base/rules/rule-conflict.md` | 승인 전에는 어느 쪽도 적용하지 않습니다 |
| 작업 단위 하나가 끝났을 때 | `core/base/rules/git-rules.md` §2 · §4 | 검사 셋을 돌리고 「커밋 시점 같습니다」를 제안합니다. 단위를 쌓아 두지 않습니다 — 쌓이면 원인이 섞여 나중에 커밋을 나눌 수 없습니다. 승인 없이 커밋하지 않습니다 |
| 커밋 · push | `core/base/rules/git-rules.md` | 검사와 저작권 게이트를 통과하고 승인을 받기 전에는 하지 않습니다 |

읽지 못한 파일이 있으면 추측으로 채우지 않고, **읽지 못했다는 사실을 밝힌 뒤 멈춥니다.**

---

## 착수 보고

파일을 만들거나 고치기 전에 아래를 먼저 냅니다. 게이트를 지났는지 사용자가 눈으로 확인하는
자리이므로, 해당 항목이 없으면 없다고 적습니다.

- **읽은 파일** — 경로를 그대로 나열합니다
- **현재 상태** — change-log의 현행 기준 또는 최신 항목 한 줄
- **이번 요청의 범위** — 한 줄
- **범위 밖이라 손대지 않을 것** — 한 줄
- **확인 질문** — 위 표의 「멈추는 자리」에 걸린 것을 여기서 묻습니다

---

## 경로별 참조 규칙

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

이 표가 이렇게 갈린 이유는, 지나간 정보와 미확정 정보가 평상시 작업에 섞이는 것을 막기 위해서입니다.
규칙이 같은 것끼리 폴더로 묶어, 파일마다 규칙을 외우지 않고 **경로만 보고** 판단하게 했습니다.

---

`core/base/rules/read-gates.md`에서 생성 · 고칠 곳은 그 파일이고, 고친 뒤에는 `core/base/scripts/regen.py`를 돌립니다
