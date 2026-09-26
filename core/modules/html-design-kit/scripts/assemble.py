#!/usr/bin/env python3
"""조립기 — choice.json 을 읽어 HTML 한 파일을 만든다.
사용:
  python3 assemble.py personal-html/<이름>/choice-1.json            → candidate-1.html (후보)
  python3 assemble.py personal-html/<이름>/choice.json --final      → page.html + DESIGN.md (완성본 + 규칙)
  python3 assemble.py <choice.json> --out <경로>                     → 원하는 경로로
personal-html/ 은 html-design-kit/ 의 형제 폴더에서 자동 탐지 (--personal <dir> 로 지정 가능).
personal-html/<이름>/parts/, themes/ 에 있는 파일은 공용보다 우선한다 (그 HTML 전용 부품·테마).

choice.json 형식:
{
  "title": "페이지 제목",
  "theme": "indigo", "mode": "dark",
  "frame": "frame.sidebar-shell",
  "regions": {                       # frame 의 data-region 별로 부품을 넣는다 (문자열 또는 목록)
    "sidebar": "sidebar.collapsible-icon",
    "topbar":  "topbar.admin-bar",
    "content": ["card.stat-compact", "table.data-grid"],
    "footer":  "footer.minimal-line"
  },
  "slots": {                         # "part.variant/slot": 값  — 첫 인스턴스의 해당 슬롯 내용을 교체
    "topbar.admin-bar/title": "주문 관리",
    "table.data-grid/title": "최근 주문"
  },
  "attrs": { "card.stat-compact": {"data-trend": "up"} }   # 루트 data-* 속성
}
슬롯 값이 "part.variant" 형태면 그 부품을 통째로 끼운다 (예: "empty-state.minimal/cta": "button.solid").
"""
import re, json, sys, pathlib, html
ROOT = pathlib.Path(__file__).parent.parent
LOCAL = None  # personal-html/<이름>/ — 조립 중인 HTML 의 폴더 (choice.json 위치에서 결정)
def _local():
    return LOCAL if LOCAL and pathlib.Path(LOCAL).is_dir() else None
def find(rel):
    """로컬 → 공용 순으로 파일을 찾는다."""
    l = _local()
    if l and (l / rel).exists(): return l / rel
    return ROOT / rel
META_RE = re.compile(r"<!--\s*(.*?)-->", re.S)

def load_part(key):
    part, var = key.split(".", 1)
    t = find(f"parts/{part}/{var}.html").read_text(encoding="utf-8")
    return META_RE.sub("", t, count=1).strip()

def set_slot(body, slot, value):
    if re.fullmatch(r"[\w-]+\.[\w-]+", value or ""):  # 부품 삽입
        value = load_part(value)
    return re.sub(rf'(<(\w+)[^>]*data-slot="{slot}"[^>]*>).*?(</\2>)', lambda m: m.group(1)+value+m.group(3), body, count=1, flags=re.S)

def set_region(frame, name, inner):
    return re.sub(rf'(<(\w+)[^>]*data-region="{name}"[^>]*>).*?(</\2>)', lambda m: m.group(1)+inner+m.group(3), frame, count=1, flags=re.S)

def add_attrs(body, attrs):
    for k, v in attrs.items(): body = body.replace("<section ", f'<section {k}="{v}" ', 1)
    return body

def build(choice):
    attrs = choice.get("attrs", {}); slots = choice.get("slots", {})
    def render(key):
        b = add_attrs(load_part(key), attrs.get(key, {}))
        for sk, v in slots.items():
            k, slot = sk.split("/", 1)
            if k == key: b = set_slot(b, slot, v)
        return b
    frame = render(choice["frame"])
    for region, keys in choice.get("regions", {}).items():
        keys = [keys] if isinstance(keys, str) else keys
        frame = set_region(frame, region, "".join(render(k) for k in keys))
    theme = choice.get('theme','indigo')
    theme_path = find(f"tokens/themes/{theme}.css")
    if not theme_path.exists() and _local(): theme_path = _local() / f"themes/{theme}.css"   # 페이지 폴더의 themes/ 도 허용
    css = "\n".join(p.read_text(encoding="utf-8") for p in [ROOT/"tokens/base.css", ROOT/"tokens/reset.css", theme_path])
    # 페이지 전용 색 덮어쓰기 (choice.json "overrides": {"--hdk-accent": "#..."} )
    ov = choice.get("overrides", {})
    if ov: css += "\n/* page overrides */\n.hdk-root, .hdk-root[data-theme] { " + " ".join(f"{k}: {v};" for k, v in ov.items()) + " }"
    js = (ROOT / "hdk.js").read_text(encoding="utf-8")
    inline_scripts = []
    for rel in choice.get("scripts", []):
        script_path = find(rel)
        if not script_path.is_file():
            raise FileNotFoundError(f"인라인할 스크립트를 찾을 수 없습니다: {rel}")
        inline_scripts.append(f"<script>\n{script_path.read_text(encoding='utf-8')}\n</script>")
    inline_script_html = "\n".join(inline_scripts)
    return f"""<!doctype html>
<html lang="ko" class="hdk-root" data-theme="{choice.get('mode','dark')}">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(choice.get('title','html-design-kit'))}</title>
<style>
{css}
</style>
<script>{js}</script>
</head>
<body>
{frame}
{inline_script_html}
</body></html>"""

def design_md(choice):
    parts_used = [choice["frame"]] + [k for v in choice.get("regions", {}).values() for k in ([v] if isinstance(v, str) else v)]
    parts_used += [v for v in choice.get("slots", {}).values() if re.fullmatch(r"[\w-]+\.[\w-]+", str(v))]
    cat = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))["parts"]
    moods = {f"{p['part']}.{p['variant']}": p["mood"] for p in cat}
    density = {}
    for k in parts_used:
        for m in moods.get(k, []):
            if m in ("dense", "airy"): density[m] = density.get(m, 0) + 1
    tone = max(density, key=density.get) if density else "?"
    ov = choice.get("overrides", {})
    lines = [f"# {choice.get('title','')} 디자인 기준", "",
             "이 문서는 이 HTML을 수정하거나 확장할 때 따르는 기준입니다. 페이지 구성의 정본은 `choice.json`이며, `page.html`은 조립 결과물입니다.", "",
             "## 테마", f"- 테마는 `{choice.get('theme','indigo')}`, 표시 모드는 `{choice.get('mode','dark')}`입니다.",
             "- 페이지 전용 색 덮어쓰기는 " + (", ".join(f"`{k}: {v}`" for k, v in ov.items()) if ov else "없음") + "입니다.",
             "", "## 톤", f"- 기본 밀도는 `{tone}`입니다. 새 부품은 같은 밀도의 변형을 우선 사용합니다.", "",
             "## 골격과 부품", f"- 프레임은 `{choice['frame']}`입니다."]
    for r, v in choice.get("regions", {}).items():
        lines.append(f"- {r} 영역은 " + ", ".join(f"`{k}`" for k in ([v] if isinstance(v, str) else v)) + "입니다.")
    lines += ["", "## 조립과 수정",
              "1. 공용 부품을 추가할 때는 중앙 html-design-kit의 catalog.json에서 맞는 변형을 골라 choice.json에 기록합니다.",
              "2. 색을 변경할 때는 choice.json의 `overrides`에 `--hdk-*` 값만 추가합니다.",
              "3. 페이지 전용 부품과 테마는 이 폴더의 parts/, themes/에 두고 공용 자산보다 먼저 적용합니다.",
              "4. 변경 뒤에는 `python core/modules/html-design-kit/scripts/assemble.py choice.json --final`로 파생물을 다시 만듭니다."]
    if choice.get("scripts"):
        lines.append("5. choice.json의 scripts 배열에 기록한 JavaScript는 page.html에 인라인합니다.")
    return "\n".join(lines) + "\n"

if __name__ == "__main__":
    args = sys.argv[1:]
    def take(flag):
        if flag in args:
            i = args.index(flag); v = args[i+1]; del args[i:i+2]; return v
    personal = take("--personal"); out_arg = take("--out"); final = "--final" in args
    if final: args.remove("--final")
    src = pathlib.Path(args[0]); LOCAL = pathlib.Path(personal) if personal else src.parent
    choice = json.loads(src.read_text(encoding="utf-8"))
    if out_arg: out = pathlib.Path(out_arg)
    elif final: out = src.with_name("page.html")
    else: out = src.with_name(src.stem.replace("choice", "candidate") + ".html")
    out.write_text(build(choice), encoding="utf-8"); print("→", out)
    if final:
        md = src.with_name("DESIGN.md"); md.write_text(design_md(choice), encoding="utf-8"); print("→", md)
