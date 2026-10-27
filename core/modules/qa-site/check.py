"""QA 서식이 공통 디자인과 연결되고 메뉴 자료가 유효한지 검사합니다."""
from pathlib import Path
import json
import re

HERE = Path(__file__).resolve().parent
rows = json.loads((HERE / "navigation.json").read_text(encoding="utf-8"))["project_items"]
assert len({row["id"] for row in rows}) == len(rows)
for name in ("01-feature-tree.html", "02-reverse-analysis.html", "03-spec-analysis.html"):
    path = HERE / "design-template" / name
    text = path.read_text(encoding="utf-8")
    for ref in re.findall(r'(?:href|src)="([^"#]+)"', text):
        if ref.startswith("../../document-site/"):
            assert (path.parent / ref).is_file(), ref
    assert "../../document-site/design-guide/" in text
print("qa-site 서식 연결 · 메뉴 자료 검사 통과")

import sys
import tempfile
sys.path.insert(0, str(HERE.parent / "document-site/scripts"))
import shell
with tempfile.TemporaryDirectory() as tmp:
    folder = Path(tmp) / "projects/sample"
    folder.mkdir(parents=True)
    (Path(tmp) / "workspace.json").write_text("{}", encoding="utf-8")
    (folder / "sample-modules.json").write_text('{"on": []}', encoding="utf-8")
    saved = shell.ROOT, shell.WS
    try:
        shell.ROOT, shell.WS = tmp, {"modules": ["document-site"]}
        assert [k for k, _, _ in shell.navigation_entries("sample")] == ["central", "project", "dict"]
        shell.WS["modules"].append("qa-site")
        assert [k for k, _, _ in shell.navigation_entries("sample") if k not in shell.WORKSPACE_INTRO] == ["tree", "tcsheet", "dict", "report", "trace"]
        import io
        from unittest.mock import patch
        for target in ("projects/../outside.html", "projects/..\\outside.html"):
            payload = json.dumps({"project_items": [{"id": "bad", "label": "bad", "path": target}]})
            with patch.object(shell.io, "open", return_value=io.StringIO(payload)):
                try:
                    shell.navigation_entries("sample")
                except ValueError:
                    pass
                else:
                    raise AssertionError("상위 경로 메뉴를 허용했습니다")
        shell.WS["modules"].remove("qa-site")
        assert [k for k, _, _ in shell.navigation_entries("sample")] == ["central", "project", "dict"]
    finally:
        shell.ROOT, shell.WS = saved
print("qa-site 활성화 · 비활성화 메뉴 격리 통과")
