"""앱 시뮬레이터를 에셋까지 담은 자기완결 HTML 한 장으로 조립할 때 쓰는 공용 도구입니다.

규칙: rules/simulator.md. 프로젝트 조립 스크립트는 어떤 소스를 어떤 순서로 붙일지만 정하고, 아래 일은 여기서 합니다.

- data_url(path) / js_json(value)        파일 → data URL, 값 → <script> 안에 안전한 JSON
- inline_assets(css, asset_dir)          CSS의 {{asset:이름}}을 그 파일의 data URL로 바꿉니다
- collect_assets(dirs, keep)             에셋 폴더를 훑어 {이름: data URL}과 같은 내용의 별칭 {이름: 원래 이름}을 만듭니다
- runtime(name)                          모듈 실행기(runtime/) 파일 내용 — 셸의 {{sim-shell-js}} 자리에 넣습니다
- fill(template, tokens)                 {{토큰}}을 채우고, 채우지 못한 토큰이 남으면 멈춥니다
- write_or_check(output, result, check)  산출물을 쓰거나(--check면) 지금 파일과 같은지만 봅니다
"""
import base64
import hashlib
import json
import mimetypes
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
#: 에셋으로 담는 확장자
ASSET_SUFFIXES = ('.png', '.jpg', '.webp', '.svg', '.mp4', '.wav', '.mp3', '.m4a')


def data_url(path):
    path = Path(path)
    mime = mimetypes.guess_type(path.name)[0] or 'application/octet-stream'
    return 'data:' + mime + ';base64,' + base64.b64encode(path.read_bytes()).decode()


def js_json(value):
    """<script> 안에 넣어도 태그가 끊기지 않는 JSON."""
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def inline_assets(css, asset_dir):
    asset_dir = Path(asset_dir)
    return re.sub(r'\{\{asset:([\w.-]+)\}\}', lambda m: data_url(asset_dir / m[1]), css)


def collect_assets(dirs, keep=None, assets=None):
    """에셋 폴더를 이름순으로 훑습니다. 내용이 같은 파일은 한 번만 담고 나머지는 별칭으로 돌려줍니다.

    keep(path) — 담을지 고르는 함수(선택). assets — 앞서 담은 {이름: data URL}(선택 · 이어서 채웁니다)
    """
    assets = {} if assets is None else assets
    aliases, hashes = {}, {}
    for d in [dirs] if isinstance(dirs, (str, Path)) else dirs:
        for p in sorted(Path(d).iterdir()):
            if p.suffix not in ASSET_SUFFIXES or (keep and not keep(p)):
                continue
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            if digest in hashes:
                aliases[p.stem] = hashes[digest]
            else:
                hashes[digest] = p.stem
                assets[p.stem] = data_url(p)
    return assets, aliases


def runtime(name='sim-shell.js'):
    return (ROOT / 'runtime' / name).read_text(encoding='utf-8')


def fill(template, tokens):
    for key, value in tokens.items():
        template = template.replace('{{%s}}' % key, value)
    left = re.findall(r'\{\{[a-z-]+\}\}', template)
    if left:
        raise ValueError('채우지 못한 토큰: %s' % ', '.join(sorted(set(left))))
    return template


def write_or_check(output, result, check=False, label='시뮬레이터'):
    output = Path(output)
    if check:
        if not output.exists() or output.read_text(encoding='utf-8') != result:
            raise SystemExit('%s 재생성이 필요합니다' % label)
        print('%s build: PASS' % label)
    else:
        output.write_text(result, encoding='utf-8')
        print(output)
