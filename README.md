# 민법 두문자 복습장

민법(총칙·물권·채권) 두문자를 간격 반복(FSRS-5)으로 복습하는 웹 앱입니다.
앱 주소: https://dhyunchun.github.io/minbeop-dumunja/

## 구조

| 경로 | 내용 |
| --- | --- |
| `src/cards.json` | 카드 데이터(두문자·뜻·설명·근거, 판례 카드의 쟁점 질문 `q`, 증명책임 `burden`). 카드 `id`는 복습 기록과 연결되므로 바꾸지 않습니다. |
| `src/practice.json` | 연습 탭의 사례 문제(`case`)·기간·숫자와 헷갈리는 개념(`pair`, 제목이 `[기간]`·`[숫자]`로 시작하면 숫자 문제). `rel`은 관련 두문자 줄 id. `pair`는 단원별 연습에만 나옴 |
| `static/ox.json` | 연습 탭의 「변시 기출 OX」. 변호사시험 1~15회 선택형 민법(문 1~35, 1책형) 지문을 법무부 정답표로 O·X를 매긴 것. 가족법·계산형·빈칸형은 제외. `items`는 `[회-문-지문, 단원번호, O면 1, 지문, 사실관계번호]`. `exp`는 `{회-문-지문: [해설, 근거]}`(시범: 15회 X 지문 60개). 근거 판례 번호는 판례 원문과 대조했고, 대조하지 못한 것은 근거에 「근거 판례 확인 필요」라고 적는다. 앱이 처음 열 때 받아 오고 오프라인용으로 저장 |
| `src/app.html` | 앱 화면과 학습 로직. 빌드할 때 `__DATA__` 자리에 카드 데이터가 들어갑니다. |
| `src/firebase.js` | 이메일·Google 로그인과 Firestore 저장 연결 |
| `static/` | 앱 설치 정보(manifest), 아이콘, 오프라인용 service worker |
| `build.py` | `src/`와 `static/`을 합쳐 `_site/`를 만듭니다. |
| `firestore.rules` | Firestore 보안 규칙(각 사용자는 자기 기록만 읽고 쓰기) |

`main` 브랜치에 올리면 GitHub Actions가 빌드해서 GitHub Pages에 자동으로 배포합니다.

## 카드 고치기

`src/cards.json`에서 해당 카드의 `acr`(두문자), `mean`(뜻, `**글자**`는 굵게), `note`, `ref`를 고치고 커밋하면 됩니다.
새 카드는 겹치지 않는 새 `id`로 추가합니다.

## 기록 저장

- 로그인 전: 기기 브라우저에만 저장
- 로그인(이메일 또는 Google) 후: Firestore `users/<uid>/docs/state`(진도·설정·내 두문자), `users/<uid>/docs/log-YYYY-MM`(복습 이력)

## 듣기 모드 음성 (구글 Chirp 3 HD)

- 음성은 `static/audio/<해시>.mp3` 에 미리 만들어 둔다. 파일 이름은 `부분("q"|"acr"|"mean") + "\n" + 원문`의 FNV-1a 해시(`tools/tts.py` 의 `key`, 앱의 `audioKey`)라서 둘을 같이 바꿔야 한다.
- 쉼 표시·띄어 읽기 같은 발음 다듬기는 `tools/tts.py` 의 `markup`·`FIXES` 에서만 한다. 규칙을 바꾸면 `NORM_VER` 를 올린다(전체 재생성, 무료 범위 안).
- `.github/workflows/tts.yml`: `src/cards.json`·`src/tts_extra.json`·`tools/tts.py` 가 바뀌거나 수동 실행하면 바뀐 문장만 만들고 커밋한 뒤 재배포. 저장소 Secret `GOOGLE_TTS_KEY` 필요, 목소리는 `TTS_VOICE` 변수(기본 `ko-KR-Chirp3-HD-Aoede`).
- `.github/workflows/tts-request.yml`: 앱의 「구글 음성 만들기 요청」이 연 이슈(저장소 주인, 제목 "음성 요청…")를 받아 고친 두문자를 `src/tts_extra.json` 에 더하고 생성한다.
- 전체를 다시 만들 때마다 저장소 기록이 약 20MB씩 늘어나니 목소리·규칙 변경은 몰아서 한다.
- 안드로이드 크롬 등 MediaSource(audio/mpeg)를 지원하면 세션 전체를 끊김 없는 스트림 하나로 만들어 재생 중에 다음 카드 mp3와 무음(`static/sil/s500.mp3`, 0.552초)을 뒤에 덧붙인다(카드 사이에도 재생이 멈추지 않음).
- 그 밖(아이폰 등)에는 카드 한 장(주제·생각할 시간·두문자·뜻)을 WAV 하나로 이어 붙여 재생해서 화면이 꺼져도 이어진다(이어 붙이기가 안 되는 기기는 mp3와 무음 WAV를 차례로 재생, 타이머 없음). 듣기 화면 아래에 재생 방식과 빌드 번호가 나온다. 음성 파일이 없는 부분이 있는 카드(직접 만든 카드 등)는 기기 음성으로 읽어서 화면이 켜져 있어야 한다.
