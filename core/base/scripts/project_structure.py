"""프로젝트의 자료 역할과 경로를 검증하고 구조 안내를 생성합니다."""
import json
from pathlib import Path, PurePosixPath

ROLES = {'specification', 'policy', 'workflow', 'implementation', 'evidence',
         'reference', 'archive', 'output', 'tool', 'navigation'}


def local_path(project, value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('구조 경로는 프로젝트 상대 POSIX 경로여야 합니다')
    parts = PurePosixPath(value)
    if parts.is_absolute() or '..' in parts.parts or value == '.':
        raise ValueError('프로젝트 밖 경로는 허용하지 않습니다: ' + value)
    target = (Path(project) / value).resolve()
    if not target.is_relative_to(Path(project).resolve()):
        raise ValueError('프로젝트 밖 실제 경로입니다: ' + value)
    return target


def load_structure(project, require_files=True):
    project = Path(project).resolve()
    config = project / (project.name + '-structure.json')
    if not config.exists():
        return None
    data = json.loads(config.read_text(encoding='utf-8'))
    if set(data) - {'schema_version', 'resources', 'jobs'} or data.get('schema_version') != 1:
        raise ValueError('지원하지 않는 프로젝트 구조 설정: ' + str(config))
    resources = data.get('resources')
    if not isinstance(resources, list):
        raise ValueError('resources는 배열이어야 합니다')
    ids, paths = {}, set()
    for item in resources:
        if not isinstance(item, dict) or set(item) - {'id', 'label', 'path', 'role', 'kind', 'parent', 'depends_on'}:
            raise ValueError('잘못된 자료 정의입니다')
        key = item.get('id')
        if not isinstance(key, str) or not key or key in ids or not isinstance(item.get('label'), str):
            raise ValueError('자료 식별자와 표시 이름을 확인해주세요')
        if item.get('role') not in ROLES or item.get('kind') not in ('file', 'directory'):
            raise ValueError('자료 역할·종류를 확인해주세요: ' + key)
        target = local_path(project, item.get('path'))
        if target in paths:
            raise ValueError('자료 경로가 중복됩니다: ' + str(target))
        paths.add(target)
        exists = target.is_file() if item['kind'] == 'file' else target.is_dir()
        if require_files and item['role'] != 'output' and not exists:
            raise ValueError('등록된 자료가 없습니다: ' + str(target))
        deps = item.get('depends_on', [])
        if not isinstance(deps, list) or any(not isinstance(x, str) for x in deps):
            raise ValueError('depends_on은 식별자 배열이어야 합니다')
        ids[key] = item
    def visit(key, field, active, done):
        if key in active:
            raise ValueError('구조 참조가 순환합니다: ' + key)
        if key in done:
            return
        active.add(key)
        item = ids[key]
        refs = item.get('depends_on', []) if field == 'depends_on' else ([item['parent']] if 'parent' in item else [])
        for ref in refs:
            if ref not in ids:
                raise ValueError('없는 자료 참조: ' + str(ref))
            if field == 'parent' and ids[ref]['kind'] != 'directory':
                raise ValueError('부모 자료는 폴더여야 합니다')
            visit(ref, field, active, done)
        active.remove(key)
        done.add(key)
    for field in ('parent', 'depends_on'):
        done = set()
        for key in ids:
            visit(key, field, set(), done)
    outputs = set()
    jobs = data.get('jobs', [])
    if not isinstance(jobs, list):
        raise ValueError('jobs는 배열이어야 합니다')
    for job in jobs:
        if not isinstance(job, dict) or set(job) != {'label', 'script', 'inputs', 'outputs'}:
            raise ValueError('생성 작업의 항목을 확인해주세요')
        script = local_path(project, job['script'])
        if script.suffix != '.py' or (require_files and not script.is_file()):
            raise ValueError('생성기는 프로젝트의 Python 파일이어야 합니다')
        if not isinstance(job['inputs'], list) or not isinstance(job['outputs'], list) or not job['outputs']:
            raise ValueError('입력·출력 목록을 확인해주세요')
        for ref in job['inputs']:
            if ref not in ids or ids[ref]['role'] in ('output', 'archive'):
                raise ValueError('잘못된 생성 입력: ' + str(ref))
        for value in job['outputs']:
            target = local_path(project, value)
            if target in outputs or target == config or target == script:
                raise ValueError('생성 출력이 중복되거나 설정·도구와 충돌합니다')
            for item in resources:
                source = local_path(project, item['path'])
                if item['role'] != 'output' and (target == source or (item['kind'] == 'directory' and target.is_relative_to(source))):
                    raise ValueError('생성 출력과 원본 자료가 겹칩니다: ' + value)
            outputs.add(target)
    return data


def resource_path(project, key, legacy=None):
    data = load_structure(project)
    if data is None:
        if legacy is None:
            raise ValueError('구조 설정이 없습니다')
        return local_path(project, legacy)
    for item in data['resources']:
        if item['id'] == key:
            return local_path(project, item['path'])
    raise ValueError('구조 설정에 자료가 없습니다: ' + key)


def path_role(project, path):
    data = load_structure(project, require_files=False)
    if data is None:
        return None
    target = Path(path).resolve()
    matches = []
    for item in data['resources']:
        base = local_path(project, item['path'])
        if target == base or (item['kind'] == 'directory' and target.is_relative_to(base)):
            matches.append((len(base.parts), item['role']))
    return max(matches)[1] if matches else None


def structure_markdown(project):
    data = load_structure(project)
    if data is None:
        return ''
    rows = ['# 프로젝트 자료 구조', '', '구조 설정에서 생성한 안내입니다. 직접 수정하지 않습니다.', '',
            '폴더 위치는 사양 승인을 뜻하지 않습니다. 승인·미확인 상태는 각 정본에서 확인합니다.', '',
            '| 자료 | 역할 | 경로 | 참조 |', '|---|---|---|---|']
    for item in data['resources']:
        refs = ', '.join(item.get('depends_on', []))
        rows.append(f"| {item['label']} | {item['role']} | `{item['path']}` | {refs} |")
    return '\n'.join(rows) + '\n'
