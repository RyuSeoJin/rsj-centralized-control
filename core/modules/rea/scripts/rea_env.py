# -*- coding: utf-8 -*-
"""이 컴퓨터에서 REA를 돌릴 준비가 되었는지 점검합니다 — Node.js · npx · MCP 등록 · 분석 엔진

왜 따로 있나
----------
  REA는 npx로 받아 MCP 서버로 띄우므로 Node.js 버전과 MCP 등록이 컴퓨터마다 다릅니다.
  네이티브 분석 엔진(Ghidra · Hopper)의 자리도 그렇습니다. 이 값을 역분석 규칙에 넣으면
  컴퓨터를 바꿀 때마다 규칙을 고쳐야 하므로, 점검을 이 호스트 모듈 한 곳에 둡니다.

  이 도구는 아무것도 설치하거나 고치지 않습니다. 설치는 REA 자신의 설치 도구
  (`npx rea-agents@latest setup`)가 계획을 보여 주고 승인을 받아 합니다.

사용법
------
    python rea_env.py             점검 보고 (필수 항목이 실패하면 exit 1)
    python rea_env.py --doctor    REA 자신의 읽기 전용 점검(rea doctor)도 함께 돌립니다 — 네트워크 필요
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# REA가 받는 Node.js — 주 버전별 최소 (부, 수) 버전. 27 이상은 모두 받습니다.
# REA 자신의 하한(22.19 · 24.11 · 26)보다 높게, Brotli 해제기 결함(CVE-2026-111497)을
# 고친 2026-10-21 보안 릴리스를 하한으로 둡니다.
NODE_MIN = {22: (23, 4), 24: (22, 1), 26: (12, 1)}
NODE_OPEN_FROM = 27
NODE_NEED = "22.23.4+ · 24.22.1+ · 26.12.1+"


def _run(args, timeout=120):
    """명령을 돌려 (종료 코드, 출력)을 돌려줍니다. 못 돌리면 (None, 이유)."""
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return None, str(e)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def node_ok(text):
    """`node --version` 출력이 REA가 받는 버전인지. (통과 여부, 읽은 버전)"""
    m = re.search(r"v?(\d+)\.(\d+)\.(\d+)", text or "")
    if not m:
        return False, None
    major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
    ver = "%s.%s.%s" % m.groups()
    if major >= NODE_OPEN_FROM:
        return True, ver
    if major in NODE_MIN:
        return (minor, patch) >= NODE_MIN[major], ver
    return False, ver


def node_status():
    exe = shutil.which("node")
    if not exe:
        return False, "찾지 못함 (Node.js %s 설치 필요)" % NODE_NEED
    code, out = _run([exe, "--version"], timeout=30)
    ok, ver = node_ok(out)
    if ver is None:
        return False, "버전을 읽지 못함"
    return ok, ver + ("" if ok else " — 맞지 않음 (%s)" % NODE_NEED)


def mcp_status(name="rea"):
    """Claude Code에 MCP 서버가 등록 · 연결되어 있는지. CLI가 없으면 None."""
    cli = shutil.which("claude")
    if not cli:
        return None
    code, text = _run([cli, "mcp", "get", name])
    if code is None:
        return None
    if "Connected" in text or "✓" in text:
        return "연결됨"
    if "No MCP server" in text or code != 0:
        return "등록 안 됨"
    return "등록됨 · 연결 실패"


def rea_cli():
    """전역 설치된 `rea` 명령의 버전. 없으면 None."""
    exe = shutil.which("rea")
    if not exe:
        return None
    code, out = _run([exe, "--version"], timeout=60)
    line = (out or "").strip().splitlines()
    return line[0] if code == 0 and line else "있음 · 버전을 읽지 못함"


def engines():
    """네이티브 분석 엔진의 단서. 찾기만 하고 실행하지 않습니다."""
    found = []
    gh = os.environ.get("GHIDRA_INSTALL_DIR")
    if gh:
        found.append("Ghidra (GHIDRA_INSTALL_DIR=%s%s)" % (gh, "" if os.path.isdir(gh) else " — 폴더 없음"))
    elif shutil.which("ghidraRun") or shutil.which("ghidra"):
        found.append("Ghidra (PATH)")
    hp = os.environ.get("HOPPER_LAUNCHER_PATH")
    if hp:
        found.append("Hopper (HOPPER_LAUNCHER_PATH)")
    return found


def doctor(npx):
    """REA 자신의 읽기 전용 점검을 Claude Code 등록 범위로 돌립니다."""
    args = [npx, "-y", "rea-agents@latest", "doctor", "--client", "claude_code", "--json"]
    if sys.platform.startswith("win"):
        # npx는 Windows에서 .cmd 스크립트라 cmd.exe로 감싸야 뜹니다 (module.md 알려진 함정)
        args = ["cmd.exe", "/d", "/c", "npx"] + args[1:]
    code, out = _run(args, timeout=600)
    if code is None:
        return False, "돌리지 못함 — %s" % out
    healthy = re.search(r'"healthy"\s*:\s*(true|false)', out or "")
    if healthy:
        return healthy.group(1) == "true", "healthy=%s" % healthy.group(1)
    return code == 0, "종료 코드 %s" % code


def report(run_doctor=False):
    fails = 0
    ok, text = node_status()
    print("Node.js           — %s" % text)
    fails += not ok
    npx = shutil.which("npx")
    print("npx               — %s" % (npx or "찾지 못함"))
    fails += not npx
    m = mcp_status()
    print("MCP 서버(rea)     — %s" % (m or "claude CLI 없음 · 건너뜀"))
    if m and m != "연결됨":
        fails += 1
    c = rea_cli()
    print("rea 명령(전역)    — %s" % (c or "없음 · npx로 씀"))
    e = engines()
    print("네이티브 분석 엔진 — %s" % (" · ".join(e) if e else "없음 · JS/Electron · .NET 정적 분석만 가능"))
    if run_doctor and npx:
        ok, text = doctor(npx)
        print("rea doctor        — %s" % text)
        fails += not ok
    return 1 if fails else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--doctor", action="store_true",
                    help="REA 자신의 읽기 전용 점검도 돌립니다 (npm에서 받으므로 네트워크 필요)")
    a = ap.parse_args(argv)
    return report(a.doctor)


if __name__ == "__main__":
    sys.exit(main())
