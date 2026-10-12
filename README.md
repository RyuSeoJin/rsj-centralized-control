# central-rules — 여러 저장소가 함께 쓰는 중앙 규칙 저장소

여러 작업 저장소가 **같은 규칙으로 문서를 만들고 운영되도록**, 그 규칙을 한 곳에 모아 두고 나눠 주는
저장소입니다. 규칙은 이 저장소에서만 고치고, 각 작업 저장소는 `core/`를 받아 씁니다.

## 왜 만들었나

게임 기획서 · 프로그램 개발 · 언리얼 엔진 공부 · QA 테스트 · 앱 기획 · 발표 자료처럼 성격이 다른
프로젝트를 AI(Claude Code · Codex)와 함께 진행하다 보면 두 가지 문제가 생깁니다.

- 한 프로젝트에서 겪은 일로 규칙을 고쳐도, 다른 저장소에는 예전 규칙이 그대로 남습니다.
- 새 프로젝트마다 같은 설명을 다시 해야 하고, 결과물의 모양이 들쭉날쭉해집니다.

그래서 「모든 저장소가 따르는 규칙」은 이 저장소 한 곳에서만 고치고, 작업 저장소는 그것을 받아 쓰도록
나눴습니다.

## 무엇이 들어 있나

| 자리 | 내용 |
|---|---|
| `core/base/` | 꼭 따르는 기본 규칙 — 문서 제작 절차 · 작성 원칙 · 변경 이력과 남은 일 기록법 · git 규칙 · HTML 출력 규칙 · 디자인 마스터 · 검사와 받기 도구 |
| `core/modules/` | 필요한 저장소 · 프로젝트만 골라 켜는 모듈. 켜면 그 모듈의 규칙 · 서식 · 도구가 따라오고, 켜지 않은 모듈은 AI가 읽지 않습니다 |
| `center-change-log.md` | 규칙이 언제 · 왜 바뀌었는지와, 받아 가는 쪽이 할 일(태그) |

## 처음 받기

1. 받는 저장소 루트에 이름표 `workspace.json`을 씁니다(`core/base/rules/site-structure.md` §3).
2. 이 저장소의 도구로 받습니다. 태그가 붙은 판으로 받으려면 `--ref {태그}`를 더합니다.

   ```bash
   python {이 저장소 clone}/core/base/scripts/sync_core.py --from https://github.com/RyuSeoJin/rsj-centralized-control --repo-root {받는 저장소}
   ```
3. 받는 저장소 루트에 진입점과 저장소 이력을 둡니다 — 빈 서식은 `core/base/design-template/repo/`.
4. 기존 프로젝트 폴더가 있으면 옮기지 않고 등록합니다(`core/base/rules/project-scaffold.md` §5).
5. `python core/base/scripts/regen.py`로 읽기 게이트(`AGENTS.md` · `CLAUDE.md` 참조 규칙)와 모듈 지도를
   만들고, `python core/base/scripts/check_rules.py`로 확인합니다.

## 다시 받기

```bash
python core/base/scripts/sync_core.py --from https://github.com/RyuSeoJin/rsj-centralized-control --check
python core/base/scripts/sync_core.py --from https://github.com/RyuSeoJin/rsj-centralized-control
```

1. `--check`로 무엇이 바뀌는지와 새 중앙 이력 항목을 먼저 봅니다.
2. 받은 뒤 **새 중앙 이력 항목의 태그를 처리합니다** — 받는 쪽이 할 일이 거기 적혀 있습니다.
3. `regen.py`와 `check_rules.py`를 돌립니다.
4. 받는 저장소의 `repo-change-log.md`에 받은 커밋과 처리한 태그를 적습니다.

자세한 절차는 `core/base/rules/central-sync.md` §2입니다.

## 프로젝트와 모듈

```bash
python core/base/scripts/new_project.py {프로젝트}          # 관리 파일만 가진 새 프로젝트
python core/base/scripts/module.py list {프로젝트}          # 모듈 목록과 켜짐 상태
python core/base/scripts/module.py on {프로젝트} {모듈}     # 켜기 (off로 끄기)
```

목록은 분야별로 묶여 나옵니다. 하는 일에서 켤 모듈을 찾을 때는 [모듈 지도](core/modules/module-map.md)(분야별
질문 · 함께 쓰는 모듈 · 둘 중 하나를 고르는 기준)를 봅니다 — `regen.py`가 다시 만드는 생성물입니다.
모듈 하나하나의 소개는 그 모듈 폴더의 `module.md`에 있습니다. 모듈이 늘 때마다 어긋나지 않도록 이 파일에는
모듈 목록을 따로 적지 않습니다.

## 중앙 규칙을 바꾸고 싶을 때

받은 저장소에서 `core/`를 직접 고치지 않습니다. 고친 파일이 있으면 다음 받기에서 도구가 멈추고, 덮어쓰면
그 수정이 사라집니다. 문제와 고칠 방향을 받는 저장소의 `repo-remaining-work.md`에 「중앙에 되돌려 보낼
것」으로 적고, 프로젝트 이름과 값을 벗겨 이 저장소에서 고친 뒤 다시 받습니다(`core/base/rules/central-sync.md` §3).

## 지키는 원칙

- **규칙은 여기서만 고칩니다.** 작업 저장소에서 고치면 다음에 받을 때 사라집니다.
- **중앙 규칙에는 특정 프로젝트의 이름 · 값을 적지 않습니다.** 「문장에서 프로젝트 이름을 지워도
  성립하는가」로 중앙 규칙과 프로젝트 규칙을 가릅니다(`core/base/rules/site-structure.md` §2).
- **사람이 지키길 기대하지 않고 도구로 막습니다.** 검사 도구와 GitHub Actions(`.github/workflows/central-gate.yml`)가
  돌고, 프로젝트 파일이 중앙에 섞여 들어오면 합쳐지지 않습니다.

이 저장소에서 규칙을 고칠 때의 절차와 커밋 전 검사 셋은 [CLAUDE.md](CLAUDE.md)에 있습니다.
