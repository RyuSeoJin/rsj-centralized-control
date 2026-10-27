"""키트·화면 입력을 검사하고 Figma 제작 준비 상태와 계획을 출력합니다."""
# CHANGELOG · 2026-10-14: 소스 열람만으로 제작 준비 통과하지 않도록 렌더 증거 검사.
# CHANGELOG · 2026-10-14: 외부 쓰기 없는 준비 검사·결정적 계획 출력.
import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse


def figma_kind(url):
    parsed = urlparse(url or '')
    if parsed.scheme != 'https' or parsed.hostname not in ('figma.com', 'www.figma.com'):
        return None
    parts = parsed.path.strip('/').split('/')
    return parts[0] if len(parts) >= 2 and parts[1] else None


def inspect(data, base):
    errors, pending = [], []
    if data.get('schemaVersion') != 1:
        errors.append('schemaVersion must be 1')
    if not data.get('revision'):
        errors.append('revision missing')
    target = data.get('target', {})
    if not target.get('designUrl'):
        pending.append('Design target missing')
    elif figma_kind(target['designUrl']) not in ('design', 'file'):
        errors.append('target must be Figma Design, not Community or FigJam')
    if target.get('boardUrl') and figma_kind(target['boardUrl']) != 'board':
        errors.append('boardUrl must be FigJam')
    ids = set()
    kits = data.get('kits', [])
    for kit in kits:
        if not kit.get('id') or kit['id'] in ids:
            errors.append('duplicate or missing kit id')
        ids.add(kit.get('id'))
    selected = data.get('selectedKit')
    if selected not in ids:
        pending.append('one baseline kit must be selected')
    binding = data.get('kitBinding') or {}
    if not binding.get('libraryKey') and figma_kind(binding.get('designUrl')) not in ('design', 'file'):
        pending.append('actual library or duplicated Design kit missing')
    for evidence in ('accessEvidence', 'usageEvidence', 'styleEvidence'):
        if not binding.get(evidence):
            pending.append(evidence + ' missing')
    sources = data.get('sources', [])
    if not sources:
        errors.append('source references missing')
    for source in sources:
        path = (base / source.get('path', '')).resolve()
        if not path.is_file():
            errors.append('source file missing: ' + str(path))
        elif source.get('sha256') and hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
            errors.append('source changed: ' + source['path'])
        if not source.get('revision'):
            errors.append('source revision missing')
    target_key = urlparse(target.get('designUrl') or '').path.strip('/').split('/')
    target_key = target_key[1] if len(target_key) > 1 else None
    components = data.get('components', {})
    screens = data.get('screens', [])
    if not screens:
        errors.append('screens missing')
    seen = set()
    for screen in screens:
        sid = screen.get('id', '')
        if not re.fullmatch(r'screen-[a-z][a-z0-9]*(?:-[a-z0-9]+)*', sid) or sid in seen:
            errors.append('invalid or duplicate screen id: ' + sid)
        seen.add(sid)
        if screen.get('mode') not in ('common', 'first', 'normal'):
            errors.append('invalid mode: ' + sid)
        if not screen.get('sourceRefs') or not screen.get('entrySteps') or not screen.get('elements'):
            errors.append('screen evidence or contents missing: ' + sid)
        if not screen.get('observationEvidence'):
            pending.append('simulator observation missing: ' + sid)
        render = screen.get('renderEvidence') or {}
        viewport = render.get('viewport') or {}
        if (render.get('method') not in ('browser-capture', 'user-screenshot')
                or not all(render.get(k) for k in ('reference', 'state', 'capturedAt'))
                or not all(isinstance(viewport.get(k), (int, float))
                           and not isinstance(viewport.get(k), bool)
                           and viewport[k] > 0 for k in ('width', 'height'))):
            pending.append('render evidence missing or incomplete: ' + sid)

        for role in screen.get('roles', []):
            mapping = components.get(role, {})
            if not (mapping.get('componentKey') or mapping.get('nodeId')):
                pending.append('component mapping missing: ' + role)
            else:
                if mapping.get('verifiedTargetFileKey') != target_key:
                    pending.append('component not verified in target: ' + role)
                if mapping.get('kitId') != selected and mapping.get('extensionOf') != selected:
                    if mapping.get('kitId') not in data.get('supplementalKitIds', []) or not mapping.get('normalizationEvidence'):
                        errors.append('component outside baseline kit: ' + role)
    for edge in data.get('transitions', []):
        if edge.get('from') not in seen or edge.get('to') not in seen or not edge.get('action'):
            errors.append('invalid transition: ' + str(edge))
    return {'valid': not errors, 'ready': not errors and not pending,
            'errors': errors, 'pending': sorted(set(pending))}


def plan(data, report):
    digest = hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return {'schemaVersion': 1, 'inputHash': digest, 'target': data.get('target'),
            'selectedKit': data.get('selectedKit'), 'status': 'ready' if report['ready'] else 'pending',
            'checks': report, 'preserveUnmappedNodes': True, 'deleteNodes': [],
            'screens': data.get('screens', []), 'components': data.get('components', {}),
            'transitions': data.get('transitions', []),
            'execution': 'Use Figma tools after ready check; record returned IDs and visual evidence externally.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--ready', action='store_true')
    parser.add_argument('--plan', type=Path)
    args = parser.parse_args()
    data = json.loads(args.manifest.read_text(encoding='utf-8'))
    report = inspect(data, args.manifest.parent)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report['valid'] and args.plan:
        if args.plan.resolve() == args.manifest.resolve():
            parser.error('plan must not overwrite manifest')
        args.plan.parent.mkdir(parents=True, exist_ok=True)
        args.plan.write_text(json.dumps(plan(data, report), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return 0 if report['valid'] and (not args.ready or report['ready']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
