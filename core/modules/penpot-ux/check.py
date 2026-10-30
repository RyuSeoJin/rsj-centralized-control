# -*- coding: utf-8 -*-
"""penpot-ux 모듈의 필수 파일과 화면 대응표 검사 도구를 점검합니다."""
# CHANGELOG · 2026-10-30: 첫 판 — 서식 통과 · 깨진 대응표 거르기.
import io
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / 'scripts'))
import screen_map as sm

for path in ('module.md', 'module.json', 'rules/penpot.md', 'templates/penpot-screen-map.md', 'scripts/screen_map.py'):
    assert (root / path).is_file(), path

template = io.open(root / 'templates/penpot-screen-map.md', encoding='utf-8').read()
assert sm.check(template) == [], sm.check(template)

BOARD = 'https://design.penpot.app/#/workspace?team-id=t&file-id=f1&page-id=p&board-id=%s'
HEAD = '# x\n\n- **파일**: [파일](https://design.penpot.app/#/workspace?team-id=t&file-id=f1&page-id=p)\n\n'


def doc(rows, flow='- S01 → S02'):
    table = '## 화면 대응표\n\n| 화면 키 | 화면 |\n|---|---|\n' + ''.join('| %s | 이름 |\n' % r for r in rows)
    return HEAD + table + '\n## 흐름 요약\n\n' + flow + '\n'


ok = doc(['[S01](%s)' % (BOARD % 'b1'), '[S02](%s)' % (BOARD % 'b2')])
assert sm.check(ok) == [], sm.check(ok)


def fails(text, word):
    errors = sm.check(text)
    assert any(word in e for e in errors), (word, errors)


fails(doc(['[S01](%s)' % (BOARD % 'b1'), '[S01](%s)' % (BOARD % 'b2')], '- S01'), '겹칩니다')
fails(doc(['[S01](%s)' % (BOARD % 'b1'), '[S02](https://design.penpot.app/#/workspace?file-id=f1&page-id=p)']), 'board-id')
fails(doc(['[S01](%s)' % (BOARD % 'b1'), '[S02](%s)' % (BOARD % 'b2').replace('f1', 'f9')]), '다른 Penpot 파일')
fails(doc(['[S01](%s)' % (BOARD % 'b1')], '- S01 → S03'), '`S03`')
fails(doc(['[S01](%s)' % (BOARD % 'b1'), 'S02']), '첫 열')
fails(doc(['[S01](%s)' % (BOARD % 'b1'), '[S02](https://example.com/s02)']), '#/workspace')
fails(ok.replace('- **파일**', '- **원본**'), 'file-id')
assert sm.check(doc(['[S01](%s)' % (BOARD % 'b1')], '- S01 · `S99`는 코드 표시')) == []
assert sm.check(doc(['[HOME](%s)' % (BOARD % 'b1')], '- HOME'), key=r'[A-Z]+') == []

print('penpot-ux: files, template and screen-map checks passed')
