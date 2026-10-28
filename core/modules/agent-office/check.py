# -*- coding: utf-8 -*-
"""agent-office 모듈 자기 점검 — 도구가 뜨는지와 훅 · 점검의 판정만 봅니다

실제 사무실 점검(`scripts/office_check.py`)은 사무실 앱이 떠 있는 컴퓨터에서 사람이 돌립니다.
중앙 게이트에는 사무실이 없으므로 여기서 연결까지 보면 게이트가 늘 실패합니다.
"""
import datetime
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "base", "scripts"))
sys.path.insert(0, os.path.join(HERE, "scripts"))

import modcheck  # noqa: E402

NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


def hook_rule():
    """훅 입력 → 알림 변환이 `rules/agent-office.md` §5-3 약속대로인지 봅니다."""
    import office_hook as h
    fails = []
    pre = {"hook_event_name": "PreToolUse", "tool_name": "Agent", "session_id": "s1",
           "tool_input": {"description": "가" * 200, "prompt": "비밀 지시", "subagent_type": "Explore"}}
    e = h.build_event(pre, NOW)
    if not e or e["event"] != "assign" or e["agentType"] != "Explore" or len(e["title"]) != h.TITLE_MAX:
        fails.append("PreToolUse(Agent)는 assign · 종류 · 120자 설명이어야 합니다: %r" % e)
    if e and "비밀 지시" in json.dumps(e, ensure_ascii=False):
        fails.append("지시 원문이 알림에 들어갔습니다")
    for name, kind in (("SubagentStart", "start"), ("SubagentStop", "stop")):
        e = h.build_event({"hook_event_name": name, "agent_id": "a1", "agent_type": "Plan"}, NOW)
        if not e or e["event"] != kind or e["agentId"] != "a1":
            fails.append("%s는 %s · agentId여야 합니다: %r" % (name, kind, e))
    keys = {"source", "event", "sessionId", "agentId", "agentType", "title", "project", "time"}
    e = h.build_event({"hook_event_name": "SubagentStop"}, NOW)
    if not e or set(e) != keys:
        fails.append("알림 필드가 약속과 다릅니다: %r" % (sorted(e) if e else e))
    for skip in ({"hook_event_name": "PreToolUse", "tool_name": "Bash"}, {"hook_event_name": "Stop"}, [], None):
        if h.build_event(skip, NOW) is not None:
            fails.append("서브에이전트와 관계없는 입력은 보내지 않아야 합니다: %r" % (skip,))
    loop = {"http://127.0.0.1:4318": True, "http://localhost:1": True, "http://[::1]:4318": True,
            "http://example.com": False, "https://127.0.0.1": False, "http://127.0.0.1.evil.test": False}
    fails += ["루프백 판정 — %s는 %s이어야 합니다" % (u, want) for u, want in loop.items() if h.is_loopback(u) != want]
    return fails


def check_rule():
    """점검 도구의 판정(Node 버전 · 층 찾기 · 역할 문구)을 봅니다."""
    import office_check as c
    fails = []
    for v, want in {"v20.0.0": True, "v22.19.0": True, "v18.20.1": False, "": False}.items():
        if c.node_ok(v) != want:
            fails.append("Node.js 판정 — %r는 %s이어야 합니다" % (v, want))
    repo = os.path.abspath(os.path.join(HERE, "repo"))
    floors = [{"id": "old", "folders": [repo], "archived": True},
              {"id": "x", "folders": [os.path.join(repo, "sub")]},
              {"id": "hit", "folders": [repo + os.sep]}]
    f = c.floor_for_repo(floors, repo)
    if not f or f["id"] != "hit":
        fails.append("층 찾기 — 보관하지 않은 같은 폴더의 층을 골라야 합니다: %r" % f)
    gaps = c.role_gaps({"writerRole": "먼저 CLAUDE.md를 읽습니다", "reviewerRole": "검토합니다"})
    if gaps != ["검토"]:
        fails.append("역할 문구 판정 — 검토만 빠져야 합니다: %r" % gaps)
    return fails


def templates_rule():
    """훅 견본이 세 이벤트에 office_hook.py를 비동기로 거는지 봅니다."""
    with open(os.path.join(HERE, "templates", "claude-hooks.json"), encoding="utf-8") as f:
        hooks = json.load(f)["hooks"]
    fails = []
    for name in ("PreToolUse", "SubagentStart", "SubagentStop"):
        hs = [x for g in hooks.get(name, []) for x in g.get("hooks", [])]
        if not any("office_hook.py" in x.get("command", "") and x.get("async") for x in hs):
            fails.append("훅 견본 — %s에 비동기 office_hook.py가 없습니다" % name)
    if [g.get("matcher") for g in hooks.get("PreToolUse", [])] != ["Agent"]:
        fails.append("훅 견본 — PreToolUse는 Agent 도구에만 걸려야 합니다")
    with open(os.path.join(HERE, "templates", "office-layout.json"), encoding="utf-8") as f:
        layout = json.load(f)
    ids = {r.get("id") for r in layout.get("rooms", [])}
    cols, rows = layout.get("grid", {}).get("cols", 0), layout.get("grid", {}).get("rows", 0)
    if not ids or len(ids) > cols * rows:
        fails.append("배치 견본 — 방 수가 가로 × 세로 안에 들어야 합니다")
    if any(v not in ids for v in layout.get("places", {}).values()):
        fails.append("배치 견본 — 방의 쓰임이 없는 방을 가리킵니다")
    return fails


def main():
    return modcheck.done("agent-office", modcheck.imports(__file__),
                         hook_rule() + check_rule() + templates_rule())


if __name__ == "__main__":
    sys.exit(main())
