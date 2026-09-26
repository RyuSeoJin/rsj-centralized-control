"""프로젝트를 찾고 제품 묶음과 업무 프로젝트의 경로를 구별합니다."""
from pathlib import Path
import re

from workspace import project_roots

#: 새로 만드는 프로젝트의 이름 — 소문자 kebab-case
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
#: 옮기지 않고 등록한 옛 프로젝트의 이름 — 대문자·밑줄을 허용합니다.
#: 이름을 바꾸면 그 폴더를 가리키는 링크와 이력이 함께 흔들리기 때문입니다
LEGACY = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*')


def validate_key(key, strict=True):
    """프로젝트 경로(`업무` 또는 `제품/업무`)를 검사합니다.

    strict는 새 프로젝트를 만들 때입니다. 등록된 옛 프로젝트를 읽을 때는 strict=False로
    대문자·밑줄을 허용합니다.
    """
    pattern = SLUG if strict else LEGACY
    parts = key.split('/')
    if len(parts) not in (1, 2) or any(not pattern.fullmatch(p) for p in parts):
        raise ValueError('프로젝트 경로는 소문자 slug 또는 제품/업무-slug 형식이어야 합니다')
    return parts


def _marker(folder):
    return folder / (folder.name + '-modules.json')


def discover(root):
    """(key, 폴더) 목록. key는 자기 자리(project_roots의 한 항목) 기준 상대 경로입니다.

    자리 자체가 프로젝트이면(그 폴더에 `{폴더}-modules.json`이 있으면) key는 폴더 이름입니다.
    같은 폴더가 두 자리에서 잡히면 먼저 적힌 자리를 따릅니다.
    """
    root = Path(root)
    found, seen = [], set()
    for rel in project_roots(str(root)):
        base = root / rel
        if not base.is_dir():
            continue
        if _marker(base).is_file():
            candidates = [(base.name, base)]
        else:
            candidates = []
            for marker in list(base.glob('*/*-modules.json')) + list(base.glob('*/*/*-modules.json')):
                folder = marker.parent
                if marker.name == folder.name + '-modules.json':
                    candidates.append((folder.relative_to(base).as_posix(), folder))
        for key, folder in sorted(candidates):
            real = folder.resolve()
            if real in seen:
                continue
            seen.add(real)
            found.append((key, folder))
    return sorted(found)


def resolve(root, key):
    validate_key(key, strict=False)
    projects = discover(root)
    direct = [p for k, p in projects if k == key]
    if len(direct) == 1:
        return direct[0]
    matches = [p for _, p in projects if p.name == key]
    if len(matches) == 1:
        return matches[0]
    raise ValueError('프로젝트를 찾을 수 없거나 이름이 중복됩니다: ' + key)


def relative_key(root, key):
    folder = resolve(root, key)
    for k, p in discover(root):
        if p == folder:
            return k
    return folder.name


def new_project_base(root):
    """새 프로젝트를 만들 자리 — project_roots의 첫 항목입니다."""
    return Path(root) / project_roots(str(root))[0]
