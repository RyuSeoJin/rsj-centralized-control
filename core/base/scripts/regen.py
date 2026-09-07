# -*- coding: utf-8 -*-
"""다시 만들 수 있는 것을 전부 다시 만듭니다 — 그리고 낡은 것이 있는지 봅니다

왜 필요한가
----------
  산출물은 정본에서 찍어내는 파생물인데, 정본을 고치고 다시 만들지 않으면 **에러가 나지
  않습니다.** 옛 HTML은 그냥 보이고 옛 xlsx는 그냥 열립니다. 그래서 사람이 기억하는 것에
  기대지 않고, 한 명령으로 전부 다시 만들고 `--check`로 낡은 것을 잡습니다.

무엇을 다시 만드나
-----------------
  워크스페이스   index.html 한 장 (설명서가 늘어도 절이 늘 뿐입니다)
  프로젝트       정본이 있는 것만 — 용어집 HTML · 기능 골격 HTML · TC 시트 xlsx

  **정본이 없으면 건너뜁니다.** 켜지 않은 모듈의 산출물을 억지로 만들지 않습니다.

사용법
------
    python core/base/scripts/regen.py            다시 만든다
    python core/base/scripts/regen.py --check    낡은 것만 알려준다 (만들지 않음)
"""
import argparse
import io
import json
import os
import subprocess
import sys

CORE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def repo_root():
    d = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.exists(os.path.join(d, "workspace.json")):
            return d
        p = os.path.dirname(d)
        if p == d:
            return os.path.dirname(CORE)
        d = p


ROOT = repo_root()
CSS = os.path.join(CORE, "base", "design-guide", "design-guide-master.css")


def rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, "/")


def jobs():
    """(설명, 정본 목록, 산출물, 명령) 목록. 정본이 없는 것은 넣지 않는다."""
    out = []
    intro = os.path.join(CORE, "base", "scripts", "gen_intro_html.py")
    #: 소개 한 장은 폴더를 훑어 만들므로 정본이 따로 없다 — 규칙·도구가 바뀌면 낡는다
    rules_srcs = []
    for kind in ("base", "modules"):
        base = os.path.join(CORE, kind)
        for cur, _d, names in os.walk(base):
            if "__pycache__" in cur:
                continue
            rules_srcs += [os.path.join(cur, n) for n in names
                           if n.endswith((".md", ".py"))]
    idx = os.path.join(ROOT, "index.html")
    out.append(("워크스페이스 문서", rules_srcs, idx,
                [sys.executable, intro, "--repo-root", ROOT,
                 "--slug", "none", "--css", CSS, "-o", idx]))

    projects = os.path.join(ROOT, "projects")
    if not os.path.isdir(projects):
        return out
    for slug in sorted(os.listdir(projects)):
        p = os.path.join(projects, slug)
        if not os.path.isdir(p):
            continue
        pre = slug            # 파일 접두 — {slug}-site.json이 있으면 그것을 따른다
        cfg = os.path.join(p, "%s-site.json" % slug)
        if os.path.exists(cfg):
            try:
                pre = json.load(io.open(cfg, encoding="utf-8")).get("prefix", slug)
            except ValueError:
                pass

        d_md = os.path.join(p, "%s-dictionary.md" % slug)
        if os.path.exists(d_md):
            o = os.path.join(p, "docs", "%s-dictionary.html" % pre)
            out.append(("용어집 — " + slug, [d_md], o,
                        [sys.executable,
                         os.path.join(CORE, "base", "scripts", "gen_dictionary_html.py"),
                         d_md, "--css", CSS, "-o", o]))

        t_md = os.path.join(p, "spec", "%s-feature-tree.md" % slug)
        if os.path.exists(t_md):
            o = os.path.join(p, "docs", "%s-feature-tree.html" % pre)
            out.append(("기능 골격 — " + slug, [t_md], o,
                        [sys.executable,
                         os.path.join(CORE, "modules", "tc", "scripts",
                                      "gen_feature_tree_html.py"), t_md, "-o", o]))

        tc_in = os.path.join(p, "test-case", "%s-tc-input-v1.0.json" % slug)
        if os.path.exists(tc_in):
            o = os.path.join(p, "test-case", "%s-tc-v1.0.xlsx" % slug)
            out.append(("TC 시트 — " + slug, [tc_in], o,
                        [sys.executable,
                         os.path.join(CORE, "modules", "tc", "scripts",
                                      "build_tc_template_xlsx.py"), tc_in, "-o", o]))
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
        if not old:
            print("낡은 산출물이 없습니다.")
            return 0
        print("정본보다 오래된 산출물 %d개 — regen.py로 다시 만드세요." % len(old))
        for name, _s, out_path, _c in old:
            print("   %-22s %s" % (name, rel(out_path)))
        return 1

    for name, _s, out_path, cmd in todo:
        d = os.path.dirname(out_path)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        # 자식이 콘솔 기본 인코딩으로 찍으면 디코딩이 깨집니다 — utf-8을 강제하고
        # 그래도 못 읽는 바이트는 버립니다. 여기서 필요한 것은 실패 여부와 메시지뿐입니다
        env = dict(os.environ, PYTHONIOENCODING="utf-8")
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
        if r.returncode:
            print("실패 %-18s %s" % (name, rel(out_path)))
            print((r.stderr or "").strip()[-500:])
            return r.returncode
        print("  ok  %-22s %s" % (name, rel(out_path)))
    print("\n%d개를 다시 만들었습니다." % len(todo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
