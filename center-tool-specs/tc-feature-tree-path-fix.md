# tc-feature-tree-path-fix — 기능 골격 HTML 생성기의 옛 마스터 경로 수정안

<!-- CHANGELOG · v1.0 · 2026-10-27: (추가) 원인 줄 · 재현 · 수정안 · 점검 케이스 -->

받아 가는 저장소의 「중앙에 되돌려 보낼 것」에 「TC 기능 골격 생성기의 옛 마스터 경로」로 등록된
결함입니다. 기능 골격 정본(`spec/{슬러그}-feature-tree.md`)이 있는 프로젝트에서 regen이 골격 HTML을
만들려다 실패하고, 같은 실행의 다른 작업까지 멈춥니다. 받는 쪽은 이 결함 때문에 골격을 기본 자리 대신
다른 폴더에 두어 작업을 피하고 있습니다.

## 1. 고칠 자리

`core/modules/tc/scripts/gen_feature_tree_html.py`

```python
113    # scripts → tc → modules → core. 이름이 repo면 저장소 루트로 읽혀 다음 이동에서 조용히 틀린다
114    core = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
115    css_path = os.path.join(core, "modules", "document-site", "design-guide", "design-guide-master.css")
...
118    js_path = os.path.join(core, "modules", "document-site", "design-guide", "design-guide-master.js")
```

## 2. 원인

`os.path.abspath(__file__)`는 `core/modules/tc/scripts/gen_feature_tree_html.py`입니다. `dirname`을 세 번
하면 `scripts` → `tc` → `modules`까지 올라가므로 114번 줄의 `core`는 실제로 `core/modules`입니다. 그
위에 다시 `"modules"`를 붙여 `core/modules/modules/document-site/…`를 찾습니다. 113번 줄 주석은 네 단계
(scripts → tc → modules → core)를 적었지만 코드는 세 번만 올라갑니다.

마스터가 qa-site에서 document-site로 옮겨질 때 경로 문자열만 바뀌고 올라가는 횟수는 그대로 남은 것으로
보입니다(추측 — 이관 커밋을 대조하지 않았습니다). 같은 파일 35번 줄의 셸 경로는
`os.path.join(_HERE, "..", "..", "document-site", "scripts")`로 맞게 계산합니다.

`check.py`는 도구를 불러 보기(`modcheck.imports`)와 TC 시트 생성만 하고 골격 HTML을 실제로 만들지 않아,
이 결함을 잡지 못했습니다. CSS는 `main()` 안에서 읽으므로 불러오기만으로는 드러나지 않습니다.

## 3. 재현

2026-10-27 이 작업본에서 확인했습니다. 프로젝트 골격 한 장을 임시 폴더로 복사해 돌리면 다음으로
끝납니다.

```text
python core/modules/tc/scripts/gen_feature_tree_html.py {임시}/spec/probe-feature-tree.md -o {임시}/probe.html
FileNotFoundError: … core\modules\modules\document-site\design-guide\design-guide-master.css
```

## 4. 수정안

이웃 줄(35번)과 같은 방식으로 이 파일 기준 상대 경로를 씁니다. `core` 변수는 다른 곳에서 쓰지 않습니다.

```python
    # 마스터는 document-site가 소유합니다 — scripts → tc → modules 다음 형제 모듈입니다
    guide = os.path.join(_HERE, "..", "..", "document-site", "design-guide")
    css_path = os.path.join(guide, "design-guide-master.css")
    with io.open(css_path, encoding="utf-8") as f:
        css = f.read()
    js_path = os.path.join(guide, "design-guide-master.js")
```

작업본 사본에 이 수정을 넣어 같은 골격으로 돌렸을 때 253노드 HTML이 정상으로 만들어졌습니다. 파일
CHANGELOG 줄(2번 줄)에 `2026-10-27: (변경) document-site 마스터 경로를 이 파일 기준 상대 경로로 계산`을
더합니다.

## 5. 점검 케이스

`core/modules/tc/check.py`에 골격 HTML 생성 한 번을 더합니다. 시험 골격은 프로젝트 이름 없이 두
노드짜리로 임시 폴더에 씁니다.

```python
tree = os.path.join(tmp, "spec", "probe-feature-tree.md")
# 형식 v2 골격 두 노드 — 「## 트리」 아래 「- 영역 [범위: 구현]」과 그 자식 잎 하나
r = subprocess.run([sys.executable, os.path.join(here, "scripts", "gen_feature_tree_html.py"),
                    tree, "-o", os.path.join(tmp, "probe.html")], capture_output=True)
```

실패하면 stderr 마지막 줄을 그대로 보고합니다. 이 케이스가 있으면 마스터를 다시 옮길 때 같은 결함이
지나가지 않습니다.

## 6. 받는 쪽 후속

중앙에서 고쳐 받은 뒤, 기본 자리를 피해 다른 폴더에 둔 골격을 `spec/{슬러그}-feature-tree.md`로 되돌리고
regen으로 골격 HTML을 만듭니다. 원문 행 골격 도구(`tc-basis.md`)의 `tree_path` 기본값도 이 자리입니다.
