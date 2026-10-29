# 민법 두문자 복습장

민법(총칙·물권·채권) 두문자를 간격 반복(FSRS-5)으로 복습하는 웹 앱입니다.
앱 주소: https://dhyunchun.github.io/minbeop-dumunja/

## 구조

| 경로 | 내용 |
| --- | --- |
| `src/cards.json` | 카드 데이터(두문자·뜻·설명·근거). 카드 `id`는 복습 기록과 연결되므로 바꾸지 않습니다. |
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
