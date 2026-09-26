# -*- coding: utf-8 -*-
"""저장소 이름표(workspace.json)와 프로젝트 설정을 한 곳에서 읽습니다

왜 모듈인가
----------
  저장소마다 달라지는 값을 도구마다 따로 읽으면, 항목이 하나 늘 때마다 도구 여러 개를
  함께 고쳐야 합니다. 한쪽만 고치면 에러 없이 도구끼리 다른 저장소를 보게 됩니다.
  그래서 이름표를 읽는 코드와 기본값을 여기 한 곳에 둡니다.

이름표가 담는 것 (rules/site-structure.md §저장소 이름표)
----------
  name · subtitle · repo       저장소 이름 · 부제 · 원격 주소 (필수)
  visibility                   public | private — 저작권 게이트의 강도를 가릅니다 (기본 public)
  project_roots                프로젝트를 찾을 자리 목록 (기본 ["projects"])
  modules                      저장소 전체에 켜는 워크스페이스 모듈 목록 (기본 [])

프로젝트 설정 ({폴더}-site.json, 없어도 됩니다)
----------
  label · prefix               표시 이름 · 파일 접두 (기본 = 폴더 이름)
  files                        관리 파일 이름을 기본값과 다르게 쓸 때만 적습니다.
                               옛 배치를 옮기지 않고 등록할 때 씁니다.
"""
import io
import json
import os

#: 이름표가 담을 수 있는 항목. 여기 없는 항목은 check_rules.py가 잡습니다
WS_REQUIRED = ("name", "subtitle", "repo")
WS_OPTIONAL = ("visibility", "project_roots", "modules")

#: 관리 파일의 종류와 기본 꼬리. 파일 이름 = {접두} + 꼬리
MANAGED = {
    "change_log": "-change-log.md",
    "remaining_work": "-remaining-work.md",
    "dictionary": "-dictionary.md",
}


def repo_root(start=None):
    """workspace.json이 있는 폴더를 위로 거슬러 올라가며 찾습니다.

    중앙 규칙이 저장소 루트 바로 밑에 있든 한 단계 더 묶이든 같은 코드로 찾게 하려는
    것입니다. 끝까지 없으면 core의 부모로 물러섭니다.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    d = os.path.abspath(start) if start else here
    while True:
        if os.path.exists(os.path.join(d, "workspace.json")):
            return d
        p = os.path.dirname(d)
        if p == d:
            return os.path.dirname(core_root())
        d = p


def core_root():
    """scripts → base → core."""
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load(root=None):
    """이름표를 읽습니다. 없거나 깨졌으면 빈 dict — 검사는 check_rules.py가 맡습니다."""
    root = root or repo_root()
    try:
        with io.open(os.path.join(root, "workspace.json"), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def project_roots(root=None):
    """프로젝트를 찾을 자리. 저장소 루트 기준 상대 경로 목록입니다."""
    roots = load(root).get("project_roots") or ["projects"]
    return [r.strip("/").replace("\\", "/") for r in roots if isinstance(r, str) and r.strip()]


def workspace_modules(root=None):
    """저장소 전체에 켠 워크스페이스 모듈 이름 목록."""
    mods = load(root).get("modules") or []
    return [m for m in mods if isinstance(m, str)]


def visibility(root=None):
    v = load(root).get("visibility", "public")
    return v if v in ("public", "private") else "public"


def project_cfg(folder):
    """{폴더}-site.json. 없는 것이 기본입니다."""
    p = os.path.join(str(folder), os.path.basename(str(folder)) + "-site.json")
    try:
        with io.open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def project_prefix(folder):
    return project_cfg(folder).get("prefix", os.path.basename(str(folder)))


def managed_file(folder, kind):
    """관리 파일(change-log · remaining-work · dictionary)의 경로.

    site.json의 files에 적혀 있으면 그 이름을, 없으면 {접두}{꼬리}를 씁니다.
    """
    files = project_cfg(folder).get("files") or {}
    name = files.get(kind) or (project_prefix(folder) + MANAGED[kind])
    return os.path.join(str(folder), name)
