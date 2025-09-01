# YouTube Analytics 월간 보고서 자동화

YouTube 채널의 월간 분석 데이터를 Google Sheets에 자동으로 기록하는 GitHub Actions 워크플로우입니다.

## 🚀 주요 기능

- 📊 YouTube Analytics API를 통한 월간 데이터 수집
- 📈 조회수, 구독자, 좋아요, 댓글, 공유 등 주요 지표 수집
- 📝 Google Sheets에 자동 기록
- ⏰ GitHub Actions를 통한 매일 자동 실행 (오후 1시 15분)
- 🔐 OAuth 2.0 인증 지원 (이원화 토큰)
- 🌍 GitHub Actions에서 직접 실행 (Google Cloud 불필요)

## 📋 사전 요구사항

1. **GitHub 저장소** 생성
2. **YouTube Data API v3** 활성화
3. **YouTube Analytics API** 활성화
4. **Google Sheets API** 활성화
5. **OAuth 2.0 클라이언트 ID** 생성

## 🔧 설치 및 설정

### 1. OAuth 클라이언트 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 OAuth 2.0 클라이언트 ID 생성
2. `client_secret.json` 파일을 `secrets/` 폴더에 저장
3. 리디렉션 URI에 `http://localhost:8081` 추가

### 2. OAuth 토큰 생성

```bash
python generate_token.py
```

**이원화 토큰 모드**를 선택하세요:

- YouTube용 토큰: `token_youtube.json`
- Sheets용 토큰: `token_sheets.json`

### 3. 로컬 테스트

```bash
python test_local.py
```

모든 API 연결과 권한을 테스트합니다.

### 4. 환경변수 설정 (선택사항)

```bash
export CHANNEL_ID="your_channel_id"
export SPREADSHEET_ID="your_spreadsheet_id"
export SHEET_NAME="유튜브_월간분석"
```

## 🚀 GitHub Actions 설정

### 1단계: GitHub Secrets 설정

GitHub 저장소의 **Settings** → **Secrets and variables** → **Actions**에서 다음 시크릿들을 설정:

#### CLIENT_SECRET_JSON

```json
{
  "web": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "your-project-id",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "javascript_origins": ["http://localhost:8081"]
  }
}
```

#### TOKEN_YOUTUBE_JSON

```json
{
  "token": "YOUR_YOUTUBE_ACCESS_TOKEN",
  "refresh_token": "YOUR_YOUTUBE_REFRESH_TOKEN",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
  "client_secret": "YOUR_CLIENT_SECRET",
  "scopes": [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly"
  ],
  "universe_domain": "googleapis.com",
  "account": "",
  "expiry": "2025-01-01T00:00:00Z"
}
```

#### TOKEN_SHEETS_JSON

```json
{
  "token": "YOUR_SHEETS_ACCESS_TOKEN",
  "refresh_token": "YOUR_SHEETS_REFRESH_TOKEN",
  "token_uri": "https://oauth2.googleapis.com/token",
  "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
  "client_secret": "YOUR_CLIENT_SECRET",
  "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
  "universe_domain": "googleapis.com",
  "account": "",
  "expiry": "2025-01-01T00:00:00Z"
}
```

### 2단계: 자동 실행

- **매 5분마다** 자동 실행
- GitHub Actions 탭에서 수동으로 워크플로우를 실행할 수 있습니다
- 실행 결과는 GitHub Actions 아티팩트로 저장됩니다

## 📊 데이터 구조

Google Sheets에 기록되는 데이터:

| 행  | 내용                    | 설명                     |
| --- | ----------------------- | ------------------------ |
| 4   | 분석 기간               | YYYY-MM-DD ~ YYYY-MM-DD  |
| 5   | Shorts 수               | 60초 이하 동영상 수      |
| 6   | Longs 수                | 60초 초과 동영상 수      |
| 7   | 총 조회수               | 해당 월 총 조회수        |
| 8   | 구독자 순증가           | 구독자 증가 - 감소       |
| 9   | 총 구독자 수            | 월말 기준 총 구독자 수   |
| 10  | 주요 시청자             | 연령대 + 성별            |
| 11  | 좋아요 수               | 총 좋아요 수             |
| 12  | 댓글 수                 | 총 댓글 수               |
| 13  | 공유 수                 | 총 공유 수               |
| 14  | 최고 조회수 영상 제목   | 해당 월 최고 조회수 영상 |
| 15  | 최고 조회수 영상 조회수 | 해당 영상의 조회수       |

## 🔐 인증 모드

### 이원화 토큰 모드 (기본)

- YouTube용과 Sheets용 토큰을 분리
- `token_youtube.json`, `token_sheets.json` 파일 사용
- 환경변수 `USE_DUAL_TOKENS=true` 설정

## 🛠️ 문제 해결

### 인증 오류

```
RuntimeError: Missing/invalid token at /secrets/token.json in NON_INTERACTIVE mode
```

**해결 방법:**

1. `generate_token.py`를 로컬에서 실행
2. 이원화 토큰 모드로 토큰 생성
3. GitHub Secrets에 올바른 JSON 내용 설정

### API 권한 오류

```
HttpError: 403 Forbidden
```

**해결 방법:**

1. Google Cloud Console에서 필요한 API 활성화
2. OAuth 클라이언트에 올바른 스코프 설정
3. 토큰 재생성

### 시트 접근 오류

```
HttpError: 404 Not Found
```

**해결 방법:**

1. 스프레드시트 ID 확인
2. 시트 이름 확인
3. OAuth 토큰에 시트 접근 권한 확인

## 📝 환경변수

| 변수명            | 기본값                                         | 설명                             |
| ----------------- | ---------------------------------------------- | -------------------------------- |
| `CHANNEL_ID`      | `UCEtPneQeO1IE08MndfjzndQ`                     | YouTube 채널 ID                  |
| `SPREADSHEET_ID`  | `17Z6bewPmkp00RHpBKymyMaFj4CvqD_QjAPzagmlkCP8` | Google Sheets ID                 |
| `SHEET_NAME`      | `유튜브_월간분석`                              | 시트 이름                        |
| `USE_DUAL_TOKENS` | `true`                                         | 이원화 토큰 사용 여부            |
| `NON_INTERACTIVE` | `true`                                         | 비대화형 모드 (GitHub Actions용) |

## 📅 스케줄링

기본적으로 매 5분마다 실행됩니다.

스케줄 변경은 `.github/workflows/run_analytics.yml` 파일의 `cron` 설정을 수정하세요:

```yaml
schedule:
  - cron: "*/5 * * * *" # 매 5분마다
```

## 🔍 로그 확인

### GitHub Actions 로그

```bash
./check_github_logs.sh
```

### 웹 브라우저에서 확인

1. GitHub 저장소 → **Actions** 탭
2. **"Run YouTube Analytics"** 워크플로우 클릭
3. 각 실행의 로그 확인

### 수동 실행

GitHub Actions 탭에서 **"Run workflow"** 버튼을 클릭하여 수동으로 실행할 수 있습니다.

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. GitHub Actions 로그 확인
2. 토큰 유효성 검사
3. API 권한 확인
4. GitHub Secrets 설정 확인

## 🎯 장점

- ✅ **Google Cloud 불필요**: GitHub Actions에서 직접 실행
- ✅ **비용 절약**: Cloud Run 비용 없음
- ✅ **간단한 설정**: GitHub Secrets만 설정하면 완료
- ✅ **실시간 모니터링**: GitHub Actions에서 로그 확인
- ✅ **자동 백업**: 실행 결과를 아티팩트로 저장
