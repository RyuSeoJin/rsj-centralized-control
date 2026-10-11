# workflow-explorer-template-catalog — workflow-explorer 모듈이 더하는 서식

`base/design-template/template-catalog.md`가 **고르는 법**의 정본이고, 이 문서는 **workflow-explorer를 켠 프로젝트에만 있는 것**의 목록입니다. 두 카탈로그를 함께 보고 고릅니다.

**이 모듈을 켜지 않았으면 이 문서를 읽지 않습니다.** 무엇이 켜져 있는지는 프로젝트의 `{프로젝트}-modules.json`이 정본입니다.

## 목록

| 파일 | 용도 | 이런 요청일 때 |
|---|---|---|
| `workflow-explorer-sample.json` | 탐색기 입력 예시 — 유저·시스템 구역, 조건 분기, 반복 지점, 흐름 사이 연결을 모두 담은 최소 데이터 | 「앱 전체 워크플로우를 한 번에 보고, 도형을 골라 화면과 다음 동작을 따라가고 싶다」 |
| `workflow-explorer-node-table-sample.md` | 기획서 노드 표 예시 — 흐름 하나를 표 하나로 적는 형식(`rules/explorer.md` §6-1) | 「기획서의 표를 정본으로 두고 탐색기 데이터를 생성하고 싶다」 |

HTML 템플릿 파일은 따로 두지 않습니다. 화면 구조는 실행기(`runtime/`)가 정하고 문서마다 바뀌는 것은 데이터뿐이라, 템플릿을 두면 실행기와 같은 것을 두 벌 관리하게 됩니다. 미리보기는 예시 데이터로 만듭니다.

```bash
python core/modules/workflow-explorer/scripts/build_explorer.py core/modules/workflow-explorer/design-template/workflow-explorer-sample.json 출력.html
```

## 판별 기준 — 여기로 오는 경우

요청의 **산출이 조작하며 따라가는 흐름도**면 여기입니다. base 카탈로그의 판별 기준 2번에서 갈라져 나옵니다 — 읽는 문서는 base가, 도형을 골라 경로를 따라가는 탐색기는 이 모듈이 담당합니다.

Case A/B/C 판별과 템플릿 공통 규칙은 **base 카탈로그가 정본**입니다.

## 왜 base가 아니라 여기인가

base와 modules를 가르는 질문은 「**이걸 안 켠 프로젝트가 있을 수 있는가**」입니다. 앱 흐름이 없는 프로젝트(분석 문서·TC만 만드는 프로젝트)는 탐색기를 쓰지 않으므로 모듈에 속합니다.
