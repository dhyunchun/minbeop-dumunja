"""듣기 모드용 음성 파일을 구글 Cloud Text-to-Speech로 미리 만든다.

- 앱(src/app.html 의 speakText)이 읽는 것과 똑같은 문장을 만들어, 문장의 해시를 이름으로 static/audio/<해시>.mp3 에 저장한다.
- 이미 있는 파일은 다시 만들지 않는다(카드 문구를 고친 부분만 새로 만든다). 더 이상 쓰지 않는 파일은 지운다.
- 목소리를 바꾸면 전부 새로 만든다.
환경변수: GOOGLE_TTS_KEY(필수, API 키)
  TTS_MODEL(선택, 기본 gemini-2.5-flash-lite-preview-tts. "chirp"로 주면 Chirp 3 HD 사용)
  TTS_VOICE(선택, 기본 Gemini는 Aoede, Chirp는 ko-KR-Chirp3-HD-Kore)
  TTS_PROMPT(선택, Gemini에만 쓰는 말투 지시)
사용법: python3 tools/tts.py [--dry]
"""
import base64, json, os, re, sys, time, urllib.request, urllib.error
from pathlib import Path

root = Path(__file__).resolve().parent.parent
outdir = root / "static" / "audio"
MODEL = os.environ.get("TTS_MODEL") or "gemini-2.5-flash-lite-preview-tts"
if MODEL.lower() == "chirp":
    MODEL = ""
VOICE = os.environ.get("TTS_VOICE") or ("Aoede" if MODEL else "ko-KR-Chirp3-HD-Kore")
PROMPT = (os.environ.get("TTS_PROMPT") or "법학 공부용 암기 카드를 읽어 줍니다. 차분하고 또박또박한 강의 말투로, 군더더기 없이 적힌 글자 그대로 읽어 주세요.") if MODEL else ""
SIG = "|".join([MODEL, VOICE, PROMPT])


def t_hash(t: str) -> str:
    """앱의 tHash 와 같은 FNV-1a 32비트(UTF-16 코드 단위 기준)."""
    h = 0x811C9DC5
    b = t.encode("utf-16-le")
    for i in range(0, len(b), 2):
        h ^= b[i] | (b[i + 1] << 8)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return f"{h:08x}"


def speak_texts(r):
    q = r.get("q") or r.get("topic") or "이 두문자의 뜻은?"
    a = r.get("acr") or ""
    acr = ("두문자는, " + re.sub(r"\s+", " ", re.sub(r"[·/]", ", ", a))) if a else ""
    m = r.get("mean") or ""
    m = re.sub(r"\*\*", "", m)
    m = re.sub(r"\([^)]*\)", "", m)
    m = re.sub(r"\s/\s", ". ", m)
    m = m.replace("·", ", ").replace("→", "그래서")
    m = re.sub(r"\s+", " ", m).strip()
    return [x for x in (q, acr, m) if x]


def synth(text, key):
    inp = {"text": text}
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
        for t in speak_texts(r):
            want[t_hash(t)] = t
    outdir.mkdir(parents=True, exist_ok=True)
    man_p = outdir / "manifest.json"
    man = json.loads(man_p.read_text(encoding="utf-8")) if man_p.exists() else {}
    same_voice = man.get("sig", man.get("voice")) == SIG
    todo = [h for h in want if not (same_voice and (outdir / f"{h}.mp3").exists())]
    chars = sum(len(want[h]) for h in todo)
    print(f"문장 {len(want)}개, 새로 만들 것 {len(todo)}개 ({chars}글자), 모델 {MODEL or 'Chirp 3 HD'}, 목소리 {VOICE}")
    if dry:
        return
    key = os.environ.get("GOOGLE_TTS_KEY")
    if not key:
        sys.exit("GOOGLE_TTS_KEY 가 없어요")
    for i, h in enumerate(todo, 1):
        (outdir / f"{h}.mp3").write_bytes(synth(want[h], key))
        if i % 50 == 0:
            print(f"  {i}/{len(todo)}")
    for f in outdir.glob("*.mp3"):
        if f.stem not in want:
            f.unlink()
    man_p.write_text(json.dumps({"sig": SIG, "files": sorted(want)}, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print("완료")


if __name__ == "__main__":
    main()
