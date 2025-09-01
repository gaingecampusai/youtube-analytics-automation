# YouTube Analytics 월간 보고서 자동화

YouTube 채널의 월간 분석 데이터를 Google Sheets에 자동으로 기록하는 Cloud Run Job입니다.

## 🚀 주요 기능

- 📊 YouTube Analytics API를 통한 월간 데이터 수집
- 📈 조회수, 구독자, 좋아요, 댓글, 공유 등 주요 지표 수집
- 📝 Google Sheets에 자동 기록
- ⏰ Cloud Scheduler를 통한 매월 자동 실행
- 🔐 OAuth 2.0 인증 지원 (단일/이원화 토큰)

## 📋 사전 요구사항

1. **Google Cloud Project** 설정
2. **YouTube Data API v3** 활성화
3. **YouTube Analytics API** 활성화
4. **Google Sheets API** 활성화
5. **OAuth 2.0 클라이언트 ID** 생성

## 🔧 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. OAuth 클라이언트 설정

1. [Google Cloud Console](https://console.cloud.google.com/)에서 OAuth 2.0 클라이언트 ID 생성
2. `client_secret.json` 파일을 `secrets/` 폴더에 저장
3. 리디렉션 URI에 `http://localhost:8081` 추가

### 3. OAuth 토큰 생성

```bash
python generate_token.py
```

토큰 생성 모드를 선택하세요:

- **단일 토큰**: YouTube + Sheets 모두 하나의 토큰으로 처리
- **이원화 토큰**: YouTube와 Sheets를 별도 토큰으로 분리

### 4. 로컬 테스트

```bash
python test_local.py
```

모든 API 연결과 권한을 테스트합니다.

### 5. 환경변수 설정 (선택사항)

```bash
export CHANNEL_ID="your_channel_id"
export SPREADSHEET_ID="your_spreadsheet_id"
export SHEET_NAME="유튜브_월간분석"
```

## 🚀 배포 방법

### 방법 1: GitHub Actions 자동 배포 (권장)

GitHub Actions를 사용하여 자동으로 배포하는 방법입니다.

#### 1단계: GitHub Actions 서비스 계정 설정

```bash
./setup_github_actions.sh
```

#### 2단계: GitHub Secrets 설정

GitHub 저장소의 **Settings** → **Secrets and variables** → **Actions**에서 다음 시크릿들을 설정:

- `GCP_SA_KEY`: 서비스 계정 JSON 키 파일 내용
- `CLIENT_SECRET_JSON`: OAuth 클라이언트 시크릿 파일 내용
- `TOKEN_YOUTUBE_JSON`: YouTube OAuth 토큰 파일 내용
- `TOKEN_SHEETS_JSON`: Google Sheets OAuth 토큰 파일 내용

#### 3단계: 자동 배포

- `main` 또는 `master` 브랜치에 푸시하면 자동으로 배포됩니다
- 또는 GitHub Actions 탭에서 수동으로 워크플로우를 실행할 수 있습니다

자세한 설정 방법은 [GITHUB_ACTIONS_SETUP.md](GITHUB_ACTIONS_SETUP.md)를 참조하세요.

### 방법 2: 로컬 수동 배포

```bash
chmod +x deploy.sh
./deploy.sh
```

```bash
docker build -t yt-monthly .
```

2. **Cloud Run Job 생성**

```bash
gcloud run jobs create yt-monthly-job \
  --image yt-monthly \
  --region asia-northeast3 \
  --set-env-vars "NON_INTERACTIVE=true"
```

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

### 단일 토큰 모드 (기본)

- 하나의 OAuth 토큰으로 YouTube와 Sheets 모두 접근
- `token.json` 파일 사용

### 이원화 토큰 모드

- YouTube용과 Sheets용 토큰을 분리
- `token_youtube.json`, `token_sheets.json` 파일 사용
- 환경변수 `USE_DUAL_TOKENS=true` 설정

### 서비스 계정 모드 (Sheets 전용)

- Sheets만 서비스 계정 사용
- 환경변수 `USE_SA_FOR_SHEETS=true` 설정
- `SERVICE_ACCOUNT_FILE` 환경변수로 키 파일 지정

## 🛠️ 문제 해결

### 인증 오류

```
RuntimeError: Missing/invalid token at /secrets/token.json in NON_INTERACTIVE mode
```

**해결 방법:**

1. `generate_token.py`를 로컬에서 실행
2. 생성된 토큰 파일을 `secrets/` 폴더에 복사
3. `deploy.sh`로 Secret Manager에 업로드

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
3. 서비스 계정에 시트 공유 권한 부여

## 📝 환경변수

| 변수명              | 기본값                                         | 설명                         |
| ------------------- | ---------------------------------------------- | ---------------------------- |
| `CHANNEL_ID`        | `UCEtPneQeO1IE08MndfjzndQ`                     | YouTube 채널 ID              |
| `SPREADSHEET_ID`    | `17Z6bewPmkp00RHpBKymyMaFj4CvqD_QjAPzagmlkCP8` | Google Sheets ID             |
| `SHEET_NAME`        | `유튜브_월간분석`                              | 시트 이름                    |
| `USE_DUAL_TOKENS`   | `false`                                        | 이원화 토큰 사용 여부        |
| `USE_SA_FOR_SHEETS` | `false`                                        | Sheets 서비스 계정 사용 여부 |
| `NON_INTERACTIVE`   | `true`                                         | 비대화형 모드 (Cloud Run용)  |

## 📅 스케줄링

기본적으로 매월 1일 02:00 (한국 시간)에 실행됩니다.

스케줄 변경:

```bash
export CRON="0 2 1 * *"  # 매월 1일 02:00
./deploy.sh
```

## 🔍 로그 확인

```bash
gcloud run jobs executions list --job=yt-monthly-job --region=asia-northeast3
gcloud run jobs executions logs <execution-id> --region=asia-northeast3
```

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. 로그 확인
2. 토큰 유효성 검사
3. API 권한 확인
4. 환경변수 설정 확인
