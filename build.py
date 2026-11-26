import re
"""src/ 와 static/ 을 합쳐 _site/ 에 배포용 파일을 만든다.

- src/app.html 의 __DATA__ 자리에 src/cards.json 을 넣어 index.html 을 만든다.
- static/sw.js 의 __BUILD__ 를 빌드 번호로 바꿔 새 버전이 캐시를 갈아끼우게 한다.
사용법: python3 build.py [빌드번호]
"""
import hashlib, json, shutil, sys, time
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

# 목차 카드: src/toc.txt(공통 골격 개요)에서 하위 항목이 둘 이상인 제목마다 한 장. 편마다 두문자 카드 사이에 고르게 섞는다.
def parse_toc(text):
    """들여쓰기 개요를 트리로 읽는다. 하위가 있는 줄의 제목이 같은 편의 앞선 '잎'과 같으면 그 잎을 펼친 것으로 본다."""
    lines=[]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"): continue
        ind=len(raw)-len(raw.lstrip(" ")); assert ind%2==0, raw
        t=raw.strip(); title,_,desc=t.partition(" — ")
        lines.append((ind//2,title.strip(),desc.strip()))
    nodes=[]; stack=[]; leaves={}; warn=[]
    for i,(d,title,desc) in enumerate(lines):
        has_kids=i+1<len(lines) and lines[i+1][0]>d
        while stack and stack[-1][0]>=d: stack.pop()
        parent=stack[-1][1] if stack else None
        node=None
        if has_kids and d>0:
            part=stack[0][1]["title"]
            cand=[n for n in leaves.get((part,title),[]) if not n["kids"] and n is not parent]
            if cand: node=cand[-1]; leaves[(part,title)].remove(node)
            elif d<=1 and parent is not None and d==1: pass
        if node is None:
            node={"title":title,"desc":desc,"kids":[],"parent":parent}
            if parent is not None: parent["kids"].append(node)
            else: nodes.append(node)
            if d>0: leaves.setdefault((stack[0][1]["title"],title),[]).append(node)
        stack.append((d,node))
    return nodes
def path(n):
    p=[]
    while n: p.append(n["title"]); n=n["parent"]
    return p[::-1]
def toc_rows(text):
    tops=parse_toc(text); rows={}
    def walk(n):
        if len(n["kids"])>=2:
            p=path(n); key=" › ".join(p)
            acr="".join(k["title"][0] for k in n["kids"])
            r={"id":"t-"+hashlib.md5(key.encode()).hexdigest()[:8],"part":p[0],"sub":"목차","acr":"",
               "topic":" › ".join(p[1:]) or p[0],"mean":" / ".join(k["title"]+(" ("+k["desc"]+")" if k["desc"] else "") for k in n["kids"]),
               "note":n["desc"],"ref":"","tags":["목차카드"],"toc":1,
               "path":p,"kids":[[k["title"],k["desc"],1 if len(k["kids"])>=2 else 0] for k in n["kids"]]}
            rows.setdefault(p[0],[]).append(r)
        for k in n["kids"]: walk(k)
    for t in tops: walk(t)
    return rows

tocp = root / "src" / "toc.txt"
if tocp.exists():
    trows = toc_rows(tocp.read_text(encoding="utf-8"))
    tids = [r["id"] for l in trows.values() for r in l]
    assert len(tids) == len(set(tids)) and not (set(tids) & set(ids)), "목차 카드 id가 겹쳐요"
    merged = []
    for part in dict.fromkeys(c["part"] for c in cards):
        E = [c for c in cards if c["part"] == part]; T = trows.pop(part, [])
        n, m = len(E), len(T); j = 0
        for i, c in enumerate(E):
            while j < m and j * n <= i * m: merged.append(T[j]); j += 1
            merged.append(c)
        merged.extend(T[j:])
    assert not trows, f"목차의 편 이름이 카드와 달라요: {list(trows)}"
    cards = merged
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
        for d1 in (d["p"] if "p" in d else [d]):
            nn = len(d1["n"])
            for e in d1.get("e", []):
                assert 0 <= e[0] < nn and 0 <= e[1] < nn and e[0] != e[1], f"도식 {k}의 선이 잘못됐어요: {e}"
                assert len(e) == 4 and e[3] in ("l", "r", "k"), f"도식 {k}의 선 종류가 잘못됐어요: {e}"
            cells = [(n[2], n[3]) for n in d1["n"]]
            assert len(set(cells)) == len(cells), f"도식 {k}에서 상자 자리가 겹쳐요"
            seen = set()
            for e in d1.get("e", []):
                key = (min(e[0], e[1]), max(e[0], e[1]), e[2])
                if key in seen: print(f"경고: 도식 {k} 같은 두 상자 사이에 같은 이름 '{e[2]}' 선이 둘")
                seen.add(key)
        exid[k]["dg"] = d
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
