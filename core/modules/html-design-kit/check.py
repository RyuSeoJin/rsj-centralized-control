#!/usr/bin/env python3
"""html-design-kit 모듈이 프로젝트 없이도 성립하는지 확인한다."""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent
blocked = {"designmodo/html-website-templates", "iGaoWei/BigDataView", "bcosca/fatfree"}

result = subprocess.run([sys.executable, str(ROOT / "scripts/lint.py")], cwd=ROOT)
if result.returncode:
    raise SystemExit(result.returncode)

catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
for part in catalog["parts"]:
    if part["source"] in blocked:
        raise SystemExit(f"제한·미확인 출처 부품이 카탈로그에 있습니다: {part['path']}")
    if not (ROOT / part["path"]).is_file():
        raise SystemExit(f"카탈로그가 없는 파일을 가리킵니다: {part['path']}")
print("html-design-kit 통과")
