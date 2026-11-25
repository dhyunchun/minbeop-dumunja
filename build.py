import re
"""src/ 와 static/ 을 합쳐 _site/ 에 배포용 파일을 만든다.

- src/app.html 의 __DATA__ 자리에 src/cards.json 을 넣어 index.html 을 만든다.
- static/sw.js 의 __BUILD__ 를 빌드 번호로 바꿔 새 버전이 캐시를 갈아끼우게 한다.
사용법: python3 build.py [빌드번호]
"""
import json, shutil, sys, time
from pathlib import Path

root = Path(__file__).parent
out = root / "_site"
build = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y%m%d%H%M%S")

if out.exists():
    shutil.rmtree(out)
shutil.copytree(root / "static", out)

cards = json.loads((root / "src" / "cards.json").read_text(encoding="utf-8"))
ids = [c["id"] for c in cards]
assert len(ids) == len(set(ids)), "카드 id가 중복됐어요"
for c in cards:
    for k in ("id", "part", "acr", "mean", "note", "ref", "tags"):
        assert k in c, f"{c.get('id')} 카드에 {k} 가 없어요"

data = json.dumps(cards, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = (root / "src" / "app.html").read_text(encoding="utf-8")
assert "__DATA__" in html
ex = json.loads((root / "src" / "practice.json").read_text(encoding="utf-8"))
row_ids = set(ids)
for x in ex:
    for k in ("id", "kind", "part", "rel", "title", "q", "a", "acr"):
        assert k in x, f"연습문제 {x.get('id')}에 {k} 가 없어요"
    assert all(r in row_ids for r in x["rel"]), f"연습문제 {x['id']}의 관련 카드 id가 없어요"
assert len({x["id"] for x in ex}) == len(ex), "연습문제 id가 중복됐어요"
dgp = root / "src" / "diagrams.json"
if dgp.exists():
    dgs = json.loads(dgp.read_text(encoding="utf-8"))
    exid = {x["id"]: x for x in ex}
    for k, d in dgs.items():
        assert k in exid, f"도식 {k}에 맞는 사례가 없어요"
        nn = len(d["n"])
        for e in d.get("e", []):
            assert 0 <= e[0] < nn and 0 <= e[1] < nn and e[0] != e[1], f"도식 {k}의 선이 잘못됐어요: {e}"
            assert len(e) < 5 or e[4] in ("c", "r", "t", "x", "q"), f"도식 {k}의 선 종류가 잘못됐어요: {e}"
        cells = [(n[2], n[3]) for n in d["n"]]
        assert len(set(cells)) == len(cells), f"도식 {k}에서 상자 자리가 겹쳐요"
        exid[k]["dg"] = d
        seen = set()
        for e in d.get("e", []):
            key = (min(e[0], e[1]), max(e[0], e[1]), e[2])
            if key in seen: print(f"경고: 도식 {k} 같은 두 상자 사이에 같은 이름 '{e[2]}' 선이 둘")
            seen.add(key)
        txt = [t for e in d.get("e", []) for t in e[2:4]] + [d.get("m", "")]
        for t in txt:
            for mm in re.finditer(r"(?<![\d.])(\d{4}\. )?(?<!\d)\d{1,2}\. \d{1,2}\.", t or ""):
                if not mm.group(1): print(f"경고: 도식 {k} 연도 없는 날짜 '{mm.group(0)}' in '{t}'")
exdata = json.dumps(ex, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
assert "__EXDATA__" in html
man = root / "static" / "audio" / "manifest.json"
audio = man.read_text(encoding="utf-8") if man.exists() else '{"files":[]}'
audio = json.loads(audio)
# OX 음성 목록은 첫 화면에 넣지 않고 ox.json 에 붙인다(기출 OX를 처음 열 때 함께 받는다).
oxp = out / "ox.json"
if oxp.exists():
    oxd = json.loads(oxp.read_text(encoding="utf-8"))
    oxd["aud"] = audio.get("ox", [])
    oxp.write_text(json.dumps(oxd, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
audio = json.dumps({"files": audio.get("files", [])}, separators=(",", ":"))
assert "__AUDIO__" in html
html = html.replace("__AUDIO__", audio)
html = html.replace("__BUILD__", build)
(out / "index.html").write_text(html.replace("__EXDATA__", exdata).replace("__DATA__", data), encoding="utf-8")
shutil.copy(root / "src" / "firebase.js", out / "firebase.js")
sw = out / "sw.js"
sw.write_text(sw.read_text(encoding="utf-8").replace("__BUILD__", build), encoding="utf-8")
(out / ".nojekyll").write_text("")
print(f"built {len(cards)} cards + {len(ex)} practice -> {out} (build {build})")
