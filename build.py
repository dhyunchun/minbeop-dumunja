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
(out / "index.html").write_text(html.replace("__DATA__", data), encoding="utf-8")
shutil.copy(root / "src" / "firebase.js", out / "firebase.js")
sw = out / "sw.js"
sw.write_text(sw.read_text(encoding="utf-8").replace("__BUILD__", build), encoding="utf-8")
(out / ".nojekyll").write_text("")
print(f"built {len(cards)} cards -> {out} (build {build})")
