"""기출 OX 해설의 근거 판례 번호를 판례 원문(legalize-kr/precedent-kr)과 대조한다.

준비(한 번, 수 분): 원문은 필요한 파일만 받아 오도록 blobless 로 복제한다.
  git clone --filter=blob:none --no-checkout https://github.com/legalize-kr/precedent-kr.git /tmp/pk
  git -C /tmp/pk ls-tree -r --name-only HEAD > /tmp/pk-tree.txt

사용:
  python3 tools/ox/verify_precedents.py /tmp/pk /tmp/pk-tree.txt            # 「확인 필요」 해설만
  python3 tools/ox/verify_precedents.py /tmp/pk /tmp/pk-tree.txt --all      # 전체
출력: 지문 id, 판례 번호, 선고일, 판시사항 앞부분 → 해설 내용과 맞는지 사람이(또는 Claude가) 읽고 판단한다.
맞으면 static/ox.json 의 exp[id][1](근거)에 판례 번호를 적고 「근거 판례 확인 필요」를 지운다.
"""
import json, re, subprocess, sys
from pathlib import Path

pk, treef = sys.argv[1], sys.argv[2]
allx = "--all" in sys.argv
tree = Path(treef).read_text(encoding="utf-8").split("\n")
d = json.loads((Path(__file__).resolve().parents[2] / "static" / "ox.json").read_text(encoding="utf-8"))
NUM = r"(\d{2,4}(?:다카|다|므|마|그|두|누|도)\d+)"
for k, (e, ref) in d["exp"].items():
    if not allx and "확인 필요" not in ref:
        continue
    nums = re.findall(NUM, ref + " " + e)
    if not nums:
        print(k, "(판례 번호 없음) |", e[:120])
        continue
    for num in nums:
        p = [t for t in tree if re.search("_" + num + r"[._]", t)]
        if not p:
            print(k, num, "NOT IN REPO")
            continue
        txt = subprocess.run(["git", "-C", pk, "cat-file", "-p", "HEAD:" + p[0]],
                             capture_output=True, text=True, timeout=120).stdout
        dt = re.search(r"선고일자:\s*(\S+)", txt)
        s = re.search(r"## 판시사항(.*?)## ", txt, re.S)
        s = re.sub(r"\s+", " ", s.group(1))[:260] if s else "(판시사항 없음)"
        print(k, num, dt.group(1) if dt else "", "|", s)
