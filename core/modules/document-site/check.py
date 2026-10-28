"""공통 문서 셸의 메뉴 격리와 용어집 생성을 검사합니다."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "scripts"))
import shell

# 생성기는 입력과 저장소의 상대 경로를 구하므로, 임시 폴더를 저장소와 같은 드라이브(이 모듈 폴더 안)에 둡니다.
# 시스템 임시 폴더를 쓰면 Windows에서 드라이브가 다를 때 os.path.relpath가 ValueError로 멈춥니다.
with tempfile.TemporaryDirectory(dir=HERE, prefix=".check-") as tmp:
    root = Path(tmp)
    (root / "workspace.json").write_text("{}", encoding="utf-8")
    project = root / "projects" / "sample"
    project.mkdir(parents=True)
    state = project / "sample-modules.json"
    state.write_text('{"on": []}', encoding="utf-8")
    saved_root, saved_ws = shell.ROOT, shell.WS
    try:
        shell.ROOT, shell.WS = str(root), {"modules": ["document-site"]}
        plain = shell.navigation_entries("sample")
        assert [row[0] for row in plain] == ["central", "project", "dict"]
    finally:
        shell.ROOT, shell.WS = saved_root, saved_ws
    inp = project / "sample-dictionary.md"
    inp.write_text("# 용어집\n\n## 기본\n\n| 용어 | 뜻 | 정본 |\n|---|---|---|\n| 예시 | 설명 | 기준 |\n", encoding="utf-8")
    out = root / "dictionary.html"
    subprocess.run([sys.executable, str(HERE / "scripts/gen_dictionary_html.py"), str(inp), "--css", str(HERE / "design-guide/design-guide-master.css"), "-o", str(out)], check=True)
    assert "설명" in out.read_text(encoding="utf-8")
print("document-site 기본 메뉴 · 용어집 생성 검사 통과")
