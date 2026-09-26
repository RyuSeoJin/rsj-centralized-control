# -*- coding: utf-8 -*-
"""프로젝트 골격 생성 — 폴더와 세 정본 파일을 규칙대로 한 번에 세웁니다

왜 도구인가
----------
  손으로 만들면 매번 조금씩 달라집니다. 어떤 프로젝트에는 remaining-work가 없고 어떤
  프로젝트에는 spec/rationale이 없는 식입니다. **자리가 달라지면 「어디를 보면 되는가」가
  프로젝트마다 갈리므로**, 규칙(rules/project-scaffold.md)이 정한 모양을 도구가 찍습니다.

무엇을 만드나
------------
  {프로젝트 자리}/{제품}/{슬러그}/        프로젝트 자리 = workspace.json project_roots의 첫 항목
      {슬러그}-change-log.md · {슬러그}-remaining-work.md · {슬러그}-dictionary.md
      {슬러그}-modules.json          어느 모듈을 켰는가 (처음에는 비어 있습니다)
      spec/design/ · spec/rationale/ · spec/archive/
      analysis/ · reference/
      rules/                         이 프로젝트에서만 통하는 규칙이 자라는 자리
      docs/                          읽는 HTML이 놓이는 자리 (regen.py가 채웁니다)

  세 md는 base/design-template/project/의 서식을 복사해 `{프로젝트}`와 `{날짜}`만 채웁니다.
  문구를 이 코드 안에 두지 않는 이유는, 서식을 고치려고 도구를 열어야 하는 상태를 피하려는
  것입니다.

만들지 않는 것
-------------
  `spec/{슬러그}-feature-tree.md` — 빈 정본이 있으면 생성기가 0노드 문서를 찍어내고, 그것이
  「골격이 있다」는 신호로 읽힙니다. 골격은 서식이 아니라 내용이라 도구가 만들 수 없습니다.

사용법
------
    python core/base/scripts/new_project.py {제품}/{슬러그}
"""
import argparse
import datetime
import io
import json
import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from project_structure import load_structure, local_path  # noqa: E402
from project_paths import validate_key, new_project_base  # noqa: E402

#: 프로젝트면 반드시 갖는 폴더. 규칙 정본은 rules/project-scaffold.md이며,
#: 여기 목록과 그 문서가 어긋나면 문서 쪽이 정본입니다
DIRS = ("spec/design", "spec/rationale", "spec/archive",
        "analysis", "reference", "rules", "docs")

#: (서식 파일, 만들 파일의 꼬리)
DOCS = (("change-log.md", "-change-log.md"),
        ("remaining-work.md", "-remaining-work.md"),
        ("dictionary.md", "-dictionary.md"))


def core_root():
    """scripts → base → core."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def repo_root():
    """저장소 루트 — workspace.json이 있는 폴더. 없으면 core의 부모로 물러선다."""
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(d, "workspace.json")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.dirname(core_root())
        d = parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", help="프로젝트 슬러그 (kebab-case). 폴더 이름이자 파일 접두입니다")
    ap.add_argument("--repo-root", default=None)
    ap.add_argument("--structure", help="폴더 역할을 정의한 구조 JSON. 생략하면 기존 기본 구조를 만듭니다")
    args = ap.parse_args()
    # 한글 출력이 콘솔 기본 인코딩으로 나가면, 다른 도구가 받아 읽을 때 깨집니다.
    # 오류는 stderr로 나가므로 둘 다 맞춥니다
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    slug = args.slug.strip()
    try:
        parts = validate_key(slug)
    except ValueError as error:
        sys.exit(str(error))

    root = args.repo_root or repo_root()
    base = str(new_project_base(root))
    if len(parts) == 2 and os.path.isfile(os.path.join(base, parts[0], parts[0] + '-modules.json')):
        sys.exit('업무 프로젝트 안에는 다른 업무 프로젝트를 만들 수 없습니다')
    proj = os.path.join(base, slug)
    if os.path.exists(proj):
        sys.exit("이미 있습니다: %s" % proj)
    project_key = slug
    slug = parts[-1]
    structure = None
    directories = DIRS
    if args.structure:
        structure = json.loads(Path(args.structure).read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / slug
            candidate.mkdir()
            (candidate / (slug + '-structure.json')).write_text(json.dumps(structure), encoding='utf-8')
            load_structure(candidate, require_files=False)
        if structure.get('jobs') or any(r['kind'] != 'directory' for r in structure['resources']):
            sys.exit('새 프로젝트 구조에는 폴더만 등록합니다. 내용과 생성기는 작성 후 등록합니다')
        directories = tuple(dict.fromkeys(['rules', 'docs'] + [r['path'] for r in structure['resources']]))

    tpl_dir = os.path.join(core_root(), "base", "design-template", "project")
    today = datetime.date.today().isoformat()

    made = []
    for d in directories:
        p = os.path.join(proj, *d.split("/"))
        os.makedirs(p, exist_ok=True)
        # 빈 폴더는 git이 버리므로 자리를 지킬 파일을 하나 둔다
        io.open(os.path.join(p, ".gitkeep"), "w", encoding="utf-8").close()
        made.append(d + "/")

    for tpl, tail in DOCS:
        with io.open(os.path.join(tpl_dir, tpl), encoding="utf-8") as f:
            body = f.read()
        body = body.replace("{프로젝트}", slug).replace("{날짜}", today)
        out = os.path.join(proj, slug + tail)
        with io.open(out, "w", encoding="utf-8", newline="") as f:
            f.write(body)
        made.append(slug + tail)

    # 켠 모듈의 정본. 처음에는 아무것도 켜져 있지 않다 —
    # 무엇을 켜는지는 rules/feature-request.md의 흐름으로 정하고 동의를 받는다
    with io.open(os.path.join(proj, slug + "-modules.json"), "w",
                 encoding="utf-8", newline="") as f:
        json.dump({"on": []}, f, ensure_ascii=False, indent=2)
    made.append(slug + "-modules.json")
    if structure:
        Path(proj, slug + '-structure.json').write_text(json.dumps(structure, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        made.append(slug + '-structure.json')

    print("만듦: %s" % os.path.relpath(proj, root).replace(os.sep, "/"))
    for m in made:
        print("   " + m)
    print("")
    print("다음 - change-log의 프로젝트 정의를 채우고, 필요한 모듈을 켭니다.")
    print("  python core/base/scripts/module.py list " + project_key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
