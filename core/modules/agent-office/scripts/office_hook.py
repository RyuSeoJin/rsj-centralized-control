# -*- coding: utf-8 -*-
"""Claude Code 훅 — 서브에이전트의 배정 · 시작 · 끝을 로컬 AI 사무실에 알립니다

규칙은 `rules/agent-office.md` §5입니다. 훅이 표준 입력으로 주는 JSON 하나를 읽어, 사무실의
`POST /api/activity`로 짧은 알림 하나를 보냅니다.

지키는 것
--------
  - **작업을 막지 않습니다.** 사무실이 꺼져 있든, 입구가 없든, 입력이 깨졌든 늘 0으로 끝납니다.
  - **표준 출력에 아무것도 쓰지 않습니다.** 훅의 출력은 세션이 읽는 자리입니다.
  - **이 컴퓨터로만 보냅니다.** `AGENT_OFFICE_URL`이 루프백 주소가 아니면 보내지 않습니다.
  - **지시 원문 · 결과는 보내지 않습니다.** 맡은 일 한 줄 설명만 120자로 잘라 보냅니다.
"""
import datetime
import json
import os
import sys
import urllib.parse
import urllib.request

DEFAULT_URL = "http://127.0.0.1:4318"
LOOPBACK = ("127.0.0.1", "localhost", "::1")
TITLE_MAX = 120


def office_url():
    return (os.environ.get("AGENT_OFFICE_URL") or DEFAULT_URL).rstrip("/")


def is_loopback(url):
    """이 컴퓨터를 가리키는 http 주소인지 — 다른 곳으로 작업 정보가 나가지 않게 합니다."""
    try:
        u = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    return u.scheme == "http" and (u.hostname or "") in LOOPBACK


def build_event(hook, now=None):
    """훅 입력 → 사무실 알림. 서브에이전트와 관계없는 입력이면 None."""
    if not isinstance(hook, dict):
        return None
    name = hook.get("hook_event_name", "")
    if name == "PreToolUse":
        if hook.get("tool_name") != "Agent":
            return None
        ti = hook.get("tool_input") or {}
        kind, agent_id = "assign", ""
        agent_type = ti.get("subagent_type") or "general-purpose"
        title = (ti.get("description") or "").strip()
    elif name in ("SubagentStart", "SubagentStop"):
        kind = "start" if name == "SubagentStart" else "stop"
        agent_id = hook.get("agent_id") or ""
        agent_type = hook.get("agent_type") or ""
        title = ""
    else:
        return None
    cwd = os.environ.get("CLAUDE_PROJECT_DIR") or hook.get("cwd") or ""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    return {
        "source": "claude-code",
        "event": kind,
        "sessionId": hook.get("session_id") or "",
        "agentId": agent_id,
        "agentType": agent_type,
        "title": title[:TITLE_MAX],
        "project": os.path.basename(os.path.normpath(cwd)) if cwd else "",
        "time": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def send(url, event, timeout=2):
    """보내고 결과를 신경 쓰지 않습니다. 실패는 조용히 넘어갑니다."""
    req = urllib.request.Request(
        url + "/api/activity",
        data=json.dumps(event, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Origin": url},
    )
    try:
        urllib.request.urlopen(req, timeout=timeout).close()
        return True
    except Exception:
        return False


def main():
    try:
        hook = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
        event = build_event(hook)
        url = office_url()
        if event and is_loopback(url):
            send(url, event)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
