# kakao-briefing-action

GitHub Actions에서 독립 실행되는 카카오 업무 브리핑 전용 레포입니다.  
로컬 `_gmail_tools`, OneDrive 브리핑 파일, `.bat` 기반 키 로딩 없이 `Gmail API + Google Calendar API + OpenAI + Kakao API`만으로 브리핑을 생성하고 전송합니다.

## 실행 방식

```powershell
python main.py --mode am --dry-run
python main.py --mode pm
```

## 필수 환경변수

- `GOOGLE_TOKEN_JSON`
- `OPENAI_API_KEY`
- `KAKAO_REST_API_KEY`
- `KAKAO_REFRESH_TOKEN`
- `KAKAO_CLIENT_SECRET`

## 선택 환경변수

- `DRY_RUN=true`
- `WEATHER_LAT`
- `WEATHER_LON`
- `WEATHER_LOCATION_NAME`
- `OPENAI_MODEL`
- `KAKAO_TEMPLATE_WEB_URL`

## GitHub Actions

- `workflow_dispatch`: 수동 실행
- 평일 오전 브리핑
- 평일 오후 브리핑
- 주간 브리핑은 앱 로직에서 일요일 저녁/월요일 오전 조건으로 자동 포함

