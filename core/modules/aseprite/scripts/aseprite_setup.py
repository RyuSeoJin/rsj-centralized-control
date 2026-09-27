# -*- coding: utf-8 -*-
"""새 컴퓨터에 Aseprite MCP 서버를 설치하고 Claude Code에 등록한 뒤 점검까지 한 번에 합니다

왜 도구인가
----------
  설치는 한 컴퓨터에 한 번이라 절차를 문서로만 두면 매번 새로 헤맵니다. 특히 실제로 막혔던
  자리(uv의 Python 폴더 연결 오류 · 등록할 때 빠진 PYTHONPATH)는 문서를 읽어도 또 걸립니다.
  그래서 단계마다 「이미 되어 있으면 건너뛰고, 안 되어 있으면 한다」를 도구가 합니다.

단계
----
  1. Aseprite 실행 파일      없으면 설치 안내만 하고 멈춥니다 (유료 프로그램이라 자동 설치하지 않습니다)
  2. uv                      없으면 설치 명령을 안내하고 멈춥니다
  3. MCP 서버 저장소 받기     --dest에 이미 있으면 건너뜁니다
  4. Python 환경 (uv sync)    이미 있으면 건너뜁니다. 폴더 연결 오류가 나면 받은 Python을 직접 지정해 다시 합니다
  5. .env의 ASEPRITE_PATH     이미 같으면 건너뜁니다
  6. Claude Code 등록         이미 연결되어 있으면 건너뜁니다. PYTHONPATH를 함께 줍니다
  7. 점검                     aseprite_env.py의 보고를 돌립니다

사용법
------
    python aseprite_setup.py --dry-run              무엇을 할지 보여 주기만 합니다
    python aseprite_setup.py [--dest 폴더] [--server 주소] [--package 이름] [--name 등록이름]
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aseprite_env  # noqa: E402

# 권장 서버 — 바꿔 쓸 수 있는 값입니다. 고르는 기준은 module.md §설치 절차에 있습니다
DEFAULT_SERVER = "https://github.com/diivi/aseprite-mcp"
DEFAULT_PACKAGE = "aseprite_mcp"
DEFAULT_NAME = "aseprite"
DEFAULT_DEST = os.path.join(os.path.expanduser("~"), "aseprite-mcp")
UV_LINK_ERROR = "Missing expected target directory"


def find_uv():
    """uv 실행 파일. PATH에 없으면 winget이 두는 자리도 봅니다 (설치 직후엔 셸이 PATH를 모릅니다)."""
    hit = shutil.which("uv")
    if hit:
        return hit
    local = os.environ.get("LOCALAPPDATA", "")
    for p in glob.glob(os.path.join(local, "Microsoft", "WinGet", "Packages", "astral-sh.uv*", "uv.exe")):
        return p
    return None


def venv_python(dest):
    for rel in (("Scripts", "python.exe"), ("bin", "python")):
        p = os.path.join(dest, ".venv", *rel)
        if os.path.isfile(p):
            return p
    return None


def managed_python(uv, version):
    """uv가 받아 둔 Python 실행 파일을 폴더 연결(junction)을 거치지 않고 찾습니다."""
    r = subprocess.run([uv, "python", "dir"], capture_output=True, text=True)
    base = r.stdout.strip()
    if not base:
        return None
    for d in sorted(glob.glob(os.path.join(base, "cpython-%s.*" % version)), reverse=True):
        for exe in ("python.exe", os.path.join("bin", "python3")):
            p = os.path.join(d, exe)
            if os.path.isfile(p):
                return p
    return None


def required_python(dest):
    """서버 저장소의 .python-version (없으면 3.13)."""
    p = os.path.join(dest, ".python-version")
    if os.path.isfile(p):
        with open(p, encoding="utf-8") as f:
            v = f.read().strip()
            if v:
                return v
    return "3.13"


def run(cmd, dry, cwd=None):
    print("   $ " + " ".join('"%s"' % c if " " in c else c for c in cmd))
    if dry:
        return 0, ""
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (r.stdout or "") + (r.stderr or "")
    if r.returncode:
        print("   " + out.strip().replace("\n", "\n   "))
    return r.returncode, out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dest", default=DEFAULT_DEST, help="MCP 서버를 받을 폴더")
    ap.add_argument("--server", default=DEFAULT_SERVER, help="MCP 서버 저장소 주소")
    ap.add_argument("--package", default=DEFAULT_PACKAGE, help="python -m 으로 띄울 서버 패키지")
    ap.add_argument("--name", default=DEFAULT_NAME, help="Claude Code에 등록할 서버 이름")
    ap.add_argument("--dry-run", action="store_true", help="바꾸지 않고 할 일만 보여 줍니다")
    a = ap.parse_args(argv)
    dry = a.dry_run
    dest = os.path.abspath(a.dest)
    print("Aseprite MCP 설치%s — 서버 %s → %s" % (" (미리 보기)" if dry else "", a.server, dest))

    # 1. Aseprite
    exe = aseprite_env.find_exe()
    print("\n1. Aseprite 실행 파일 — %s" % (exe or "없음"))
    if not exe:
        print("   Aseprite(1.3 이상)를 설치한 뒤 다시 돌립니다. 흔한 자리가 아니면 환경변수 "
              "ASEPRITE_PATH에 실행 파일 전체 경로를 적습니다.")
        return 1

    # 2. uv
    uv = find_uv()
    print("\n2. uv — %s" % (uv or "없음"))
    if not uv:
        print("   설치: Windows `winget install --id astral-sh.uv -e` · macOS/Linux "
              "`curl -LsSf https://astral.sh/uv/install.sh | sh` — 설치 뒤 새 셸에서 다시 돌립니다.")
        return 1

    # 3. 서버 저장소
    has_repo = os.path.isdir(os.path.join(dest, ".git"))
    print("\n3. MCP 서버 저장소 — %s" % ("있음 · 건너뜀" if has_repo else "받습니다"))
    if not has_repo:
        if os.path.exists(dest) and os.listdir(dest):
            print("   %s 가 비어 있지 않은데 git 저장소가 아닙니다 — 다른 --dest를 줍니다." % dest)
            return 1
        code, _ = run(["git", "clone", "--quiet", a.server, dest], dry)
        if code:
            return 1
        if not dry:
            print("   ⚠ 설치 전에 서버 코드를 훑어봅니다 — 외부 네트워크 호출 · 임의 명령 실행 · 파일 삭제")

    # 4. Python 환경
    py = venv_python(dest)
    print("\n4. Python 환경 — %s" % ("있음 · 건너뜀 (%s)" % py if py else "만듭니다 (uv sync)"))
    if not py:
        code, out = run([uv, "sync"], dry, cwd=dest)
        if code and UV_LINK_ERROR in out:
            pinned = managed_python(uv, required_python(dest))
            print("   uv의 Python 폴더 연결 오류 — 받은 Python을 직접 지정합니다: %s" % pinned)
            if not pinned:
                return 1
            code, _ = run([uv, "sync", "--python", pinned], dry, cwd=dest)
        if code:
            return 1
        py = venv_python(dest) or os.path.join(dest, ".venv", "Scripts" if os.name == "nt" else "bin",
                                               "python.exe" if os.name == "nt" else "python")

    # 5. .env
    env_path = os.path.join(dest, ".env")
    line = "ASEPRITE_PATH=%s" % exe
    current = open(env_path, encoding="utf-8").read() if os.path.isfile(env_path) else ""
    same = line in current.splitlines()
    print("\n5. .env — %s" % ("같음 · 건너뜀" if same else "ASEPRITE_PATH를 적습니다"))
    if not same and not dry:
        kept = [l for l in current.splitlines() if not l.startswith("ASEPRITE_PATH=")]
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(kept + [line]) + "\n")

    # 6. Claude Code 등록
    status = aseprite_env.mcp_status(a.name)
    print("\n6. Claude Code 등록(%s) — %s" % (a.name, status or "claude CLI 없음"))
    if status is None:
        print("   Claude Code CLI를 설치한 뒤 다시 돌리거나, 아래 명령을 직접 실행합니다.")
    if status != "연결됨":
        cli = shutil.which("claude") or "claude"
        if status and status != "등록 안 됨":
            run([cli, "mcp", "remove", a.name, "-s", "user"], dry or status is None)
        # PYTHONPATH가 없으면 저장소 밖에서 띄울 때 패키지를 못 찾아 「Failed to connect」가 됩니다
        code, _ = run([cli, "mcp", "add", "--scope", "user", a.name,
                       "-e", "PYTHONPATH=%s" % dest, "-e", "PYTHONIOENCODING=utf-8",
                       "--", py, "-m", a.package], dry or status is None)
        if code:
            return 1

    # 7. 점검
    print("\n7. 점검")
    if dry:
        print("   (미리 보기라 건너뜁니다)")
        return 0
    return aseprite_env.report()


if __name__ == "__main__":
    sys.exit(main())
