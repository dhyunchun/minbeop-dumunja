"""기출 OX 지문 훑어보기.
  python3 tools/ox/list.py 7          # 7회 X 지문(사실관계 포함)
  python3 tools/ox/list.py 7 all      # 7회 전체 지문 + 단원
"""
import json, sys
from pathlib import Path

d = json.loads((Path(__file__).resolve().parents[2] / "static" / "ox.json").read_text(encoding="utf-8"))
n = sys.argv[1]
allx = len(sys.argv) > 2
last = None
for a in d["items"]:
    if a[0].split("-")[0] != n or (a[2] != 0 and not allx):
        continue
    c = d["ctx"][a[4]] if a[4] >= 0 else ""
    if c and c != last:
        print("  [사실관계]", c[:400])
        last = c
    print(a[0], "O" if a[2] else "X", d["units"][a[1]], "|", a[3])
