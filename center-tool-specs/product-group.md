# product-group — 제품 공통 모듈 설정을 중앙 도구가 읽게 하는 구현 명세

규칙 정본: `core/base/rules/site-structure.md` 「프로젝트 묶음 — 한 제품의 여러 업무 프로젝트」.
그 절의 「현재 도구 지원 범위」 표에서 「지원하지 않습니다」인 줄을 지원으로 바꾸기 위한 계획입니다.

## 1. 현재 상태 (2026-10-27 사본 기준으로 확인)

| 읽는 곳 | 지금 읽는 것 | 제품 설정을 읽는가 |
|---|---|---|
| `core/base/scripts/module.py` `validate_enabled` | `workspace.json` `modules` · `{업무}-modules.json` `on` | 아니오 |
| `module.py` `cmd_list` · `cmd_on` · `cmd_off` | `read_state`(업무 설정) + `workspace.workspace_modules` | 아니오 — 그래서 제품 설정에만 있는 모듈을 전제로 하는 모듈을 켜면 「먼저 켜야 하는 모듈」로 멈춥니다 |
| `core/base/scripts/regen.py` `enabled(folder)` | 업무 설정 + 저장소 모듈 | 아니오 — 제품 설정에만 켠 모듈의 `jobs.py`는 돌지 않습니다 |
| `core/modules/document-site/scripts/shell.py` `navigation_entries` | 저장소 모듈 + 업무 설정 | 아니오 — 제품 설정에만 켠 모듈의 메뉴가 빠집니다 |
| `core/base/scripts/project_paths.py` `discover` | `*/*-modules.json` · `*/*/*-modules.json` 표지 | 해당 없음 — `{제품}-module-config.json`은 표지 이름과 달라 프로젝트로 잡히지 않습니다(올바른 동작) |

받아 가는 저장소에서는 제품 생성기가 `{제품}-module-config.json`을 따로 읽어 합집합을 계산하고 있습니다(업무 설정 ∪ 제품 설정으로 「활성화되지 않은 모듈」을 판정). 형식은 `{"on": ["모듈 이름", …]}`이고, `on`이 문자열 배열이 아니면 오류로 멈춥니다.

## 2. 설정 파일

- 자리: `{프로젝트 자리}/{제품}/{제품}-module-config.json`. 업무 key가 `제품/업무` 두 단일 때만 그 부모 폴더를 봅니다. 한 단 key(제품 없는 프로젝트)는 제품 설정이 없습니다.
- 형식: `{"on": [...]}`만 허용합니다. 다른 항목이 있으면 오류입니다(`workspace.json`의 모르는 항목 검사와 같은 이유 — 목록이 이중 정본이 되는 것을 막습니다).
- 없으면 `{"on": []}`로 봅니다.
- 이름에 `-modules.json`을 쓰지 않습니다. 쓰면 `discover`가 제품 폴더를 프로젝트로 등록합니다.

## 3. 새 함수와 바꿀 곳

`module.py`(또는 `project_paths.py`)에 둡니다.

```python
def product_config_path(root, slug) -> Path | None
    """업무 key가 제품/업무이면 제품 폴더의 {제품}-module-config.json 경로, 아니면 None."""

def read_product_config(root, slug) -> list[str]
    """제품 설정의 on. 파일이 없으면 []. 형식이 틀리면 ValueError."""

def effective_modules(root, slug) -> list[str]
    """업무가 쓸 수 있는 모듈 — 저장소 모듈, 제품 설정, 업무 설정 순으로 중복 없이."""
```

| 바꿀 곳 | 바꿀 내용 |
|---|---|
| `validate_enabled(root, slug)` | `have = ws | product | project`로 계산합니다. 제품 설정 모듈의 scope는 `project`여야 합니다. **같은 이름이 제품 설정과 업무 설정에 함께 있으면 오류**(「중복 등록: {모듈} — 제품 공통 설정과 {업무} 설정」) |
| `cmd_list` | 표에 「어디서 켰나」 열을 더합니다(저장소 · 제품 · 업무) |
| `cmd_on(slug, name)` | 이미 제품 설정에 있으면 멈춥니다(「제품 공통 설정에 이미 켜져 있습니다」). 전제 검사의 `have`에 제품 설정을 더합니다 |
| `cmd_off(slug, name)` | 업무 설정에 없고 제품 설정에만 있으면 멈추고, 제품 설정에서 끄는 명령을 안내합니다 |
| `regen.enabled(folder)` | `effective_modules`를 씁니다 |
| `document-site` `shell.navigation_entries` | `effective_modules`를 씁니다(모듈 쪽 변경 — document-site 담당) |

## 4. 새 명령

```bash
python core/base/scripts/module.py product-list {제품}
python core/base/scripts/module.py product-on {제품} {모듈}
python core/base/scripts/module.py product-off {제품} {모듈}
```

- `product-on`
  1. 모듈의 scope가 `project`인지 봅니다.
  2. 전제 모듈이 **저장소 모듈 ∪ 제품 설정**에 모두 있는지 봅니다. 업무 설정에만 있는 전제는 인정하지 않습니다 — 제품 설정은 묶음의 모든 업무에 걸리므로 모든 업무에서 성립해야 합니다.
  3. 묶음의 업무 중 이미 그 모듈을 자기 설정에 켠 곳이 있으면 목록을 보이고 멈춥니다. 옮기려면 사용자가 업무 쪽을 먼저 끕니다(자동으로 옮기지 않습니다 — 무엇이 바뀌는지 사용자가 알아야 하기 때문입니다).
  4. 모듈의 `creates`(켜면 만드는 폴더)는 **묶음의 모든 업무 프로젝트에** 만듭니다. → 열린 질문 1
  5. 무엇이 켜지고 어떤 폴더가 생기는지 보이고 동의를 받은 뒤 씁니다(`module.py on`과 같은 흐름 — `feature-request.md` 「모듈의 모양」).
- `product-off`
  1. 묶음의 어느 업무든 이 모듈을 전제로 하는 모듈을 (제품 · 업무 어느 쪽이든) 켜 두었으면 그 목록을 보이고 멈춥니다.
  2. 만든 폴더는 지우지 않습니다(기존 `cmd_off`와 같은 원칙).

## 5. 검사

- `validate_workspace`가 묶음마다 제품 설정을 읽어 형식 · scope · 중복을 봅니다. `regen.py` 앞단에서 이미 이 함수를 부르므로 따로 연결하지 않습니다.
- `check_rules.py`에는 더하지 않습니다(프로젝트 파일이므로). → 열린 질문 2

## 6. 시험 케이스 (`core/base/scripts/test_module.py`에 더함)

| 갈래 | 준비 | 기대 |
|---|---|---|
| 합집합 | 제품 on `[a]`, 업무 on `[b]`, 저장소 `[w]` | `effective_modules` = `[w, a, b]` |
| 제품 설정 없음 | 업무 on `[b]` | `[w, b]` |
| 한 단 key | 제품 없는 프로젝트 | 제품 설정을 찾지 않음 |
| 중복 | 제품 on `[a]`, 업무 on `[a]` | `validate_enabled` 오류 |
| 형식 | 제품 설정에 `{"on": "a"}` 또는 다른 항목 | 오류 |
| scope | 제품 on에 workspace 모듈 | 오류 |
| 전제 · 업무에서 켜기 | 제품 on `[parent]`, 업무에서 `child` on | 통과 |
| 전제 · 제품에서 켜기 | 업무 A on `[parent]`, 제품에서 `child` on | 멈춤(전제가 묶음 전체에 없음) |
| 이미 업무에 켜짐 | 업무 A on `[a]`, `product-on a` | 멈추고 업무 A를 보임 |
| 업무에서 끄기 | 제품 on `[a]`, 업무에서 `off a` | 멈추고 `product-off` 안내 |
| 제품에서 끄기 · 의존 | 제품 on `[parent]`, 업무 on `[child]`, `product-off parent` | 멈춤 |
| regen | 제품 on `[a]`, `a`에 `jobs.py` | `regen.py --check`가 `a`의 작업을 묶음의 각 업무에서 셈 |
| discover | 제품 폴더에 `{제품}-module-config.json`만 있음 | 제품 폴더는 프로젝트 목록에 없음 |

## 7. 문서 반영

- `site-structure.md` 「현재 도구 지원 범위」 표와 그 아래 「감수합니다」 목록을 지원 내용으로 바꿉니다.
- `feature-request.md` 「모듈의 모양」의 scope 표에 「제품 공통 설정에서도 켤 수 있음(project scope)」을 적습니다.
- `project-scaffold.md`에 제품 폴더가 갖는 파일(제품 change-log · remaining-work · readme · 제품 설정)을 적을지는 열린 질문 3입니다.
- 중앙 이력 태그: `{제품} 생성기 방식 변경됨`(제품 생성기가 직접 계산하던 합집합을 `effective_modules` 호출로 바꿀 수 있음) · 제품 설정과 업무 설정에 같은 모듈이 있으면 `{업무}-modules.json 직접 수정해야 함`.

## 8. 열린 질문

1. 제품에서 켠 모듈의 `creates` 폴더를 모든 업무에 만들지, 실제로 그 모듈을 쓰는 업무가 생길 때 만들지. 명세는 「모든 업무」로 두었습니다 — 켜는 순간 어디에 무엇이 생기는지 한 번에 보이기 때문입니다. 반대로 쓰지 않는 업무에 빈 폴더가 생기는 단점이 있습니다(`project-scaffold.md` 「폴더는 필요할 때 생깁니다」와 부딪칩니다).
2. 제품 설정의 형식 검사를 `check_rules.py` ④처럼 규칙 검사에도 넣을지.
3. 제품 폴더를 `new_project.py`가 만들 때 제품 공통 관리 파일(change-log · remaining-work)도 함께 만들지. 지금은 업무 프로젝트만 만듭니다.
