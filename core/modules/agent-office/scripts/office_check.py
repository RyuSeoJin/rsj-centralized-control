# -*- coding: utf-8 -*-
"""AI 사무실 점검 — 이 저장소를 사무실에 맡기고 지켜볼 준비가 되었는지 읽기만 해서 봅니다

규칙은 `rules/agent-office.md` §6입니다. 층을 만들거나 설정을 바꾸지 않습니다.

    python core/modules/agent-office/scripts/office_check.py --repo .

종료 코드: 실패가 하나라도 있으면 1, 경고만 있으면 0.
"""
import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from office_hook import office_url, is_loopback  # noqa: E402

NODE_MIN = 20
HOOK_SCRIPT = "office_hook.py"
RULE_ENTRY = "CLAUDE.md"


def node_ok(version):
    """`node --version` 출력이 20 이상인지 — 사무실 앱이 받는 최소 버전입니다."""
    m = re.match(r"v?(\d+)\.", (version or "").strip())
    return bool(m) and int(m.group(1)) >= NODE_MIN


def same_path(a, b):
    na = os.path.normcase(os.path.normpath(os.path.abspath(a)))
    nb = os.path.normcase(os.path.normpath(os.path.abspath(b)))
    return na == nb


def floor_for_repo(floors, repo):
    """보관하지 않은 층 중 이 저장소 루트를 폴더로 가진 첫 층."""
    for f in floors or []:
        if f.get("archived"):
            continue
        if any(same_path(p, repo) for p in f.get("folders") or []):
            return f
    return None


def role_gaps(config):
    """역할 문구가 규칙 진입 파일을 읽게 하지 않는 담당 — `rules/agent-office.md` §2."""
    config = config or {}
    return [who for key, who in (("writerRole", "작성"), ("reviewerRole", "검토"))
            if RULE_ENTRY not in (config.get(key) or "")]


def hook_installed(repo):
    """프로젝트 `.claude/settings*.json`에 사무실 훅이 걸려 있는지."""
    for path in glob.glob(os.path.join(repo, ".claude", "settings*.json")):
        try:
            with open(path, encoding="utf-8") as f:
                if HOOK_SCRIPT in f.read():
                    return True
        except OSError:
            continue
    return False


def get_json(url, timeout=5):
    """(상태 코드, 본문). 연결이 안 되면 (None, 오류 문장)."""
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8") or "null")
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception as e:  # 연결 거부 · 시간 초과 · 깨진 JSON
        return None, str(e)


class Report:
    def __init__(self):
        self.fails, self.warns = 0, 0

    def line(self, mark, msg):
        print("  [%s] %s" % (mark, msg))

    def ok(self, msg):
        self.line("통과", msg)

    def warn(self, msg):
        self.warns += 1
        self.line("경고", msg)

    def fail(self, msg):
        self.fails += 1
        self.line("실패", msg)


def check_tools(rep):
    node = shutil.which("node")
    if not node:
        rep.fail("node가 PATH에 없습니다 — Node.js %d 이상을 설치합니다" % NODE_MIN)
    else:
        try:
            v = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=10).stdout
        except Exception:
            v = ""
        (rep.ok if node_ok(v) else rep.fail)("Node.js %s" % (v.strip() or "버전 모름"))
    # 사무실 앱은 PATH 밖의 설치 자리도 찾습니다 — 판정은 아래 사무실의 로그인 확인이 기준입니다
    for cli in ("claude", "codex"):
        if shutil.which(cli):
            rep.ok("%s CLI 있음" % cli)
        else:
            rep.warn("%s CLI가 PATH에 없습니다 — 사무실이 찾지 못하면 아래 로그인 항목이 실패합니다" % cli)


def check_office(rep, url, repo):
    if not is_loopback(url):
        rep.fail("사무실 주소가 이 컴퓨터가 아닙니다: %s — 127.0.0.1 · localhost만 씁니다" % url)
        return
    code, health = get_json(url + "/api/health")
    if code != 200:
        rep.fail("사무실이 응답하지 않습니다(%s) — 사무실 앱을 켭니다" % url)
        return
    rep.ok("사무실 응답 %s" % url)
    for who in ("claude", "codex"):
        h = (health or {}).get(who) or {}
        ready = h.get("ready")
        (rep.ok if ready else rep.fail)("%s 로그인 %s" % (who, "확인" if ready else "안 됨 — " + str(h.get("message") or h)))

    code, floors = get_json(url + "/api/floors")
    floor = floor_for_repo(floors if code == 200 else [], repo)
    if not floor:
        rep.fail("이 저장소 루트를 폴더로 가진 층이 없습니다 — 층을 추가하고 폴더를 저장소 루트로 지정합니다")
    else:
        rep.ok("층 「%s」이 이 저장소를 가리킵니다" % floor.get("name", floor.get("id")))
        gaps = role_gaps(floor.get("config"))
        if gaps:
            rep.fail("%s 역할 문구가 %s를 읽게 하지 않습니다 — templates/office-roles.md로 채웁니다" % (" · ".join(gaps), RULE_ENTRY))
        else:
            rep.ok("역할 문구가 %s를 읽게 합니다" % RULE_ENTRY)
        if not os.path.isdir(os.path.join(repo, "core")):
            rep.warn("저장소에 core/가 없습니다 — 사무실이 읽을 중앙 규칙이 없습니다")

    code, _ = get_json(url + "/api/activity")
    if code == 200:
        rep.ok("활동 입구 있음 — 서브에이전트가 사무실에 보입니다")
    else:
        rep.warn("활동 입구(GET /api/activity)가 없습니다 — 맡기기는 되지만 지켜보기는 화면에 안 나옵니다(§5-3)")


def main(argv=None):
    ap = argparse.ArgumentParser(description="AI 사무실 준비 점검(읽기 전용)")
    ap.add_argument("--repo", default=".", help="점검할 저장소 루트(기본: 현재 폴더)")
    ap.add_argument("--url", default=None, help="사무실 주소(기본: AGENT_OFFICE_URL 또는 http://127.0.0.1:4318)")
    a = ap.parse_args(argv)
    repo = os.path.abspath(a.repo)
    url = (a.url or office_url()).rstrip("/")
    rep = Report()
    print("AI 사무실 점검 — %s" % repo)
    check_tools(rep)
    check_office(rep, url, repo)
    (rep.ok if hook_installed(repo) else rep.warn)(
        "서브에이전트 훅 %s" % ("있음" if hook_installed(repo) else "없음 — templates/claude-hooks.json을 .claude/settings.json에 더합니다"))
    print("결과: 실패 %d · 경고 %d" % (rep.fails, rep.warns))
    return 1 if rep.fails else 0


if __name__ == "__main__":
    sys.exit(main())
