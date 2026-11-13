"""듣기 모드용 음성 파일을 구글 Cloud Text-to-Speech로 미리 만든다.

- 파일 이름은 '읽을 원문'(부분+원문)의 해시라서 앱(src/app.html 의 rawText·audioKey)과 맞춰야 한다.
  발음 다듬기(쉼, 띄어 읽기)는 여기서만 하므로 바꿔도 앱은 그대로 두면 된다(대신 전체를 새로 만든다).
- src/tts_extra.json 의 {"acr": [...]} 는 앱에서 직접 고친 두문자(이슈로 요청된 것)도 만든다.
- 이미 있는 파일은 다시 만들지 않는다(카드 문구를 고친 부분만 새로 만든다). 더 이상 쓰지 않는 파일은 지운다.
- static/ox.json(변시 기출 OX)의 사실관계(c)·지문(q)·정답 안내(acr)·해설(mean)도 만든다. 앱의 oxRow 와 맞춰야 한다.
  OX 파일 목록은 manifest 의 "ox" 에 따로 적고, build.py 가 배포용 ox.json 의 "aud" 로 옮긴다(앱 첫 화면을 가볍게).
- 목소리를 바꾸면 전부 새로 만든다.
환경변수: GOOGLE_TTS_KEY(필수, API 키)
  TTS_MODEL(선택, 기본 chirp = Chirp 3 HD(무료 제공량 내). gemini-2.5-flash-lite-preview-tts 등 Gemini 모델 이름도 가능)
  TTS_VOICE(선택, 기본 Chirp는 ko-KR-Chirp3-HD-Aoede, Gemini는 Aoede)
  TTS_PROMPT(선택, Gemini에만 쓰는 말투 지시)
사용법: python3 tools/tts.py [--dry]
"""
import base64, json, os, re, sys, time, urllib.request, urllib.error
from pathlib import Path

root = Path(__file__).resolve().parent.parent
outdir = root / "static" / "audio"
MODEL = os.environ.get("TTS_MODEL") or "chirp"
if MODEL.lower() == "chirp":
    MODEL = ""
VOICE = os.environ.get("TTS_VOICE") or ("Aoede" if MODEL else "ko-KR-Chirp3-HD-Aoede")
PROMPT = (os.environ.get("TTS_PROMPT") or "법학 공부용 암기 카드를 읽어 줍니다. 차분하고 또박또박한 강의 말투로, 군더더기 없이 적힌 글자 그대로 읽어 주세요.") if MODEL else ""


def t_hash(t: str) -> str:
    """앱의 tHash 와 같은 FNV-1a 32비트(UTF-16 코드 단위 기준)."""
    h = 0x811C9DC5
    b = t.encode("utf-16-le")
    for i in range(0, len(b), 2):
        h ^= b[i] | (b[i + 1] << 8)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


# 띄어 읽기 고치기: TTS가 조사로 잘못 끊는 붙여 쓴 법률 용어를 소리 낼 때만 띄운다. 필요하면 여기에 더한다.
FIXES = [
    (r"권이전", "권 이전"),
    (r"이전등기청구권", "이전등기 청구권"),
]
NORM_VER = "2"  # 아래 다듬기 규칙을 바꾸면 올린다(전체 재생성)
SIG = "|".join([MODEL, VOICE, PROMPT, NORM_VER, json.dumps(FIXES, ensure_ascii=False)])


def raw_texts(r):
    """앱 rawText 와 같다: (부분, 원문)"""
    return [("q", r.get("q") or r.get("topic") or "이 두문자의 뜻은?"), ("acr", r.get("acr") or ""), ("mean", r.get("mean") or "")]


def key(part, raw):
    return t_hash(part + "\n" + raw)


def markup(part, raw):
    """원문 → 구글에 보낼 markup(쉼 표시 포함)"""
    t = raw.replace("**", "")
    t = re.sub(r"\([^)]*\)", "", t)
    for a, b in FIXES:
        t = re.sub(a, b, t)
    if part == "acr":
        t = re.sub(r"\s*[·/]\s*", ", [pause] ", t)
    else:
        t = re.sub(r"\s/\s", ". [pause] ", t)
        t = re.sub(r"\s*→\s*", ", [pause short] 그래서 ", t)
        t = re.sub(r"\s*·\s*", ", [pause short] ", t)
        t = re.sub(r"\s*:\s*", ": [pause] ", t)
        t = re.sub(r",(?! \[pause)\s*", ", [pause short] ", t)
        t = re.sub(r"\s*—\s*", ". [pause] ", t)
    return re.sub(r"\s+", " ", t).strip()


OX_SAY = {1: "맞는 지문이에요.", 0: "틀린 지문이에요."}  # 앱 OX_SAY 와 같아야 한다
HANJA = {"甲": "갑", "乙": "을", "丙": "병", "丁": "정", "戊": "무", "己": "기"}


def ox_texts():
    """앱 oxRow 와 같다: [(부분, 원문)]"""
    p = root / "static" / "ox.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    out = [("acr", OX_SAY[1]), ("acr", OX_SAY[0])]
    out += [("c", c) for c in d["ctx"] if c]
    for a in d["items"]:
        out.append(("q", a[3]))
        e = d.get("exp", {}).get(a[0])
        if e and e[0]:
            out.append(("mean", e[0]))
    return out


def ox_markup(raw):
    """OX 지문·해설 → 구글에 보낼 markup"""
    t = raw
    for a, b in HANJA.items():
        t = t.replace(a, b)
    t = re.sub(r"\([\u3400-\u9fff]+\)", "", t)  # 경매인(競買人) → 경매인
    t = re.sub(r"[「」｢｣‘’“”'\"]", "", t)
    t = re.sub(r"(\d+)\s*/\s*(\d+)", lambda m: f"{m.group(2)}분의 {m.group(1)}", t)
    t = t.replace("%", " 퍼센트").replace("×", " 곱하기 ").replace("=", ", 즉 ")
    t = re.sub(r"[․ㆍ·]", ", ", t)
    t = re.sub(r"[①②③④⑤]", lambda m: f"{'①②③④⑤'.index(m.group(0)) + 1}번", t)
    t = re.sub(r"\s*:\s*", ": [pause short] ", t)
    return re.sub(r"\s+", " ", t).strip()


def synth(text, key):
    inp = {"markup": text} if not MODEL else {"text": re.sub(r"\s*\[pause[^\]]*\]\s*", " ", text)}
    voice = {"languageCode": "ko-KR", "name": VOICE}
    if MODEL:
        voice["modelName"] = MODEL
        if PROMPT:
            inp["prompt"] = PROMPT
    body = json.dumps({"input": inp, "voice": voice, "audioConfig": {"audioEncoding": "MP3"}}).encode()
    req = urllib.request.Request(
        "https://texttospeech.googleapis.com/v1/text:synthesize?key=" + key,
        data=body, headers={"Content-Type": "application/json"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                return base64.b64decode(json.load(res)["audioContent"])
        except urllib.error.HTTPError as e:
            msg = e.read().decode(errors="replace")[:500]
            if e.code in (429, 500, 503) and attempt < 4:
                time.sleep(2 ** attempt * 3)
                continue
            sys.exit(f"구글 TTS 오류 {e.code}: {msg}")


def main():
    dry = "--dry" in sys.argv
    cards = json.loads((root / "src" / "cards.json").read_text(encoding="utf-8"))
    want = {}
    for r in cards:
        for part, raw in raw_texts(r):
            if raw:
                want[key(part, raw)] = markup(part, raw)
    extra_p = root / "src" / "tts_extra.json"
    if extra_p.exists():
        for a in json.loads(extra_p.read_text(encoding="utf-8")).get("acr", []):
            if a.strip():
                want[key("acr", a.strip())] = markup("acr", a.strip())
    card_keys = sorted(want)
    ox_want = {}
    for part, raw in ox_texts():
        ox_want[key(part, raw)] = ox_markup(raw)
    want.update(ox_want)
    outdir.mkdir(parents=True, exist_ok=True)
    man_p = outdir / "manifest.json"
    man = json.loads(man_p.read_text(encoding="utf-8")) if man_p.exists() else {}
    same_voice = man.get("sig", man.get("voice")) == SIG
    todo = [h for h in want if not (same_voice and (outdir / f"{h}.mp3").exists())]
    chars = sum(len(want[h]) for h in todo)
    print(f"문장 {len(want)}개, 새로 만들 것 {len(todo)}개 ({chars}글자), 모델 {MODEL or 'Chirp 3 HD'}, 목소리 {VOICE}")
    if dry:
        for h in list(want)[:6]:
            print(" ", h, want[h][:120])
        return
    api_key = os.environ.get("GOOGLE_TTS_KEY")
    if not api_key:
        sys.exit("GOOGLE_TTS_KEY 가 없어요")
    for i, h in enumerate(todo, 1):
        (outdir / f"{h}.mp3").write_bytes(synth(want[h], api_key))
        if i % 50 == 0:
            print(f"  {i}/{len(todo)}")
    for f in outdir.glob("*.mp3"):
        if f.stem not in want:
            f.unlink()
    man_p.write_text(json.dumps({"sig": SIG, "files": card_keys, "ox": sorted(ox_want)}, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print("완료")


if __name__ == "__main__":
    main()
