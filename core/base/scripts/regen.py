# -*- coding: utf-8 -*-
"""다시 만들 수 있는 것을 전부 다시 만듭니다 — 그리고 낡은 것이 있는지 봅니다

왜 필요한가
----------
  산출물은 정본에서 찍어내는 파생물인데, 정본을 고치고 다시 만들지 않으면 **에러가 나지
  않습니다.** 옛 HTML은 그냥 보이고 옛 xlsx는 그냥 열립니다. 그래서 사람이 기억하는 것에
  기대지 않고, 한 명령으로 전부 다시 만들고 `--check`로 낡은 것을 잡습니다.

무엇을 다시 만드나
-----------------
  base           읽기 게이트 두 자리(AGENTS.md · CLAUDE.md 참조 규칙)
                 프로젝트 구조 설정({폴더}-structure.json)에 등록된 생성 작업
  켠 모듈        그 모듈의 jobs.py가 내놓는 작업 — 워크스페이스 모듈은 저장소 전체에,
                 프로젝트 모듈은 켠 프로젝트에만

  **base는 모듈 이름을 모릅니다.** 모듈이 자기 산출물을 jobs.py로 알려 주고, 여기서는
  켠 모듈의 jobs.py를 훑어 돌리기만 합니다. 그래야 core/base/만 떼어내도 이 도구가
  없는 모듈을 부르지 않습니다(rules/site-structure.md §base와 modules).

jobs.py의 모양 (모듈 폴더 바로 밑, 필요한 함수만 둡니다)
-----------------
    def workspace_jobs(ctx): return [(설명, 정본 목록, 산출물, 명령), ...]
    def project_jobs(ctx):   return [(설명, 정본 목록, 산출물, 명령), ...]

  ctx는 dict입니다 — root · core · python, 프로젝트 작업이면 folder · key · slug · prefix ·
  managed(종류 → 경로 함수)가 더해집니다.

사용법
------
    python core/base/scripts/regen.py            다시 만든다
    python core/base/scripts/regen.py --check    낡은 것만 알려준다 (만들지 않음)
"""
import argparse
import importlib.util
import io
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import workspace  # noqa: E402
from project_paths import discover  # noqa: E402
from project_structure import load_structure, local_path, path_role  # noqa: E402

CORE = workspace.core_root()
ROOT = workspace.repo_root()


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def module_hook(name):
    """켠 모듈의 jobs.py를 불러옵니다. 없으면 None — 산출물이 없는 모듈입니다."""
    path = os.path.join(CORE, "modules", name, "jobs.py")
    if not os.path.isfile(path):
        return None
    spec = importlib.util.spec_from_file_location("jobs_" + name.replace("-", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def enabled(folder):
    """프로젝트가 켠 모듈 — {폴더}-modules.json의 on에 워크스페이스 모듈을 더합니다."""
    p = os.path.join(str(folder), os.path.basename(str(folder)) + "-modules.json")
    try:
        with io.open(p, encoding="utf-8") as f:
            on = json.load(f).get("on", [])
    except (OSError, ValueError):
        on = []
    return list(dict.fromkeys(workspace.workspace_modules(ROOT) + on))


def base_jobs():
    out = []
    #: 읽기 게이트는 두 자리에 찍힌다 — 한쪽만 다시 만들면 도구마다 규칙이 갈린다
    gates = os.path.join(CORE, "base", "rules", "read-gates.md")
    gen_g = os.path.join(CORE, "base", "scripts", "gen_read_gates.py")
    for target, out_path, label in (
            ("agents", os.path.join(ROOT, "AGENTS.md"), "읽기 게이트 — AGENTS.md"),
            ("claude", os.path.join(ROOT, "CLAUDE.md"), "읽기 게이트 — CLAUDE.md 참조 규칙")):
        out.append((label, [gates, gen_g], out_path,
                    [sys.executable, gen_g, "--repo-root", ROOT, "--target", target]))
    return out


def structure_jobs(folder):
    """구조 설정에 등록된 생성 작업. 정본은 프로젝트의 {폴더}-structure.json입니다."""
    out = []
    structure = load_structure(folder)
    if not structure:
        return out
    slug = folder.name
    resources = {r['id']: r for r in structure['resources']}
    config = folder / (slug + '-structure.json')
    for job in structure.get('jobs', []):
        sources = [str(config), str(local_path(folder, job['script']))]
        for key in job['inputs']:
            target = local_path(folder, resources[key]['path'])
            if target.is_dir():
                sources.extend(str(f) for f in target.rglob('*')
                               if f.is_file() and '__pycache__' not in f.parts
                               and path_role(folder, f) not in ('archive', 'output'))
            else:
                sources.append(str(target))
        for value in job['outputs']:
            out.append((job['label'] + ' — ' + slug, sources, str(local_path(folder, value)),
                        [sys.executable, str(local_path(folder, job['script']))]))
    return out


def jobs():
    """(설명, 정본 목록, 산출물, 명령) 목록. 정본이 없는 것은 모듈이 넣지 않는다."""
    out = base_jobs()
    ctx = {"root": ROOT, "core": CORE, "python": sys.executable}
    for name in workspace.workspace_modules(ROOT):
        hook = module_hook(name)
        if hook and hasattr(hook, "workspace_jobs"):
            out += hook.workspace_jobs(dict(ctx))
    for key, folder in discover(ROOT):
        out += structure_jobs(folder)
        pctx = dict(ctx, folder=str(folder), key=key, slug=folder.name,
                    prefix=workspace.project_prefix(folder),
                    managed=lambda kind, _f=folder: workspace.managed_file(_f, kind))
        for name in enabled(folder):
            hook = module_hook(name)
            if hook and hasattr(hook, "project_jobs"):
                out += hook.project_jobs(dict(pctx))
    return out


def stale(srcs, out_path):
    """산출물이 정본보다 오래됐는가. 산출물이 없으면 만들어야 하는 것으로 본다."""
    if not os.path.exists(out_path):
        return True
    o = os.path.getmtime(out_path)
    return any(os.path.exists(s) and os.path.getmtime(s) > o for s in srcs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="다시 만들지 않고 낡은 것만 알려줍니다")
    args = ap.parse_args()
    # 한글 출력이 콘솔 기본 인코딩으로 나가면, 다른 도구가 받아 읽을 때 깨집니다.
    # 오류는 stderr로 나가므로 둘 다 맞춥니다
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8")
        except AttributeError:
            pass

    todo = jobs()
    if not todo:
        print("다시 만들 것이 없습니다.")
        return 0

    old = [j for j in todo if stale(j[1], j[2])]
    if args.check:
        # 읽기 게이트는 수정 시각이 아니라 내용으로 봅니다 — CLAUDE.md는 손으로 고치는
        # 부분이 있어 시각만 보면 늘 낡은 것으로 잡힙니다
        old = [j for j in old if not j[0].startswith("읽기 게이트")]
        gate_fail = []
        for name, _s, out_path, cmd in todo:
            if name.startswith("읽기 게이트"):
                r = subprocess.run(cmd + ["--check"], capture_output=True, text=True,
                                   encoding="utf-8", errors="replace")
                if r.returncode:
                    gate_fail.append((name, out_path))
        if not old and not gate_fail:
            print("낡은 산출물이 없습니다.")
            return 0
        print("정본보다 오래된 산출물 %d개 — regen.py로 다시 만드세요."
              % (len(old) + len(gate_fail)))
        for name, _s, out_path, _c in old:
            print("   %-22s %s" % (name, rel(out_path)))
        for name, out_path in gate_fail:
            print("   %-22s %s" % (name, rel(out_path)))
        return 1

    executed = set()
    for name, _s, out_path, cmd in todo:
        d = os.path.dirname(out_path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        # 자식이 콘솔 기본 인코딩으로 찍으면 디코딩이 깨집니다 — utf-8을 강제하고
        # 그래도 못 읽는 바이트는 버립니다. 여기서 필요한 것은 실패 여부와 메시지뿐입니다
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        if tuple(cmd) not in executed:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", env=env)
            if r.returncode:
                print("실패 %-18s %s" % (name, rel(out_path)))
                print((r.stderr or r.stdout or "").strip()[-500:])
                return r.returncode
            executed.add(tuple(cmd))
        if not os.path.isfile(out_path):
            print("생성기가 등록한 출력을 만들지 않았습니다: " + rel(out_path))
            return 1
        print("  ok  %-22s %s" % (name, rel(out_path)))
    print("\n%d개를 다시 만들었습니다." % len(todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
