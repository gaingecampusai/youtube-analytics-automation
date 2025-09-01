# GitHub Actions 자동 배포 설정 가이드

이 문서는 YouTube Analytics 프로젝트를 GitHub Actions를 통해 자동으로 Cloud Run에 배포하는 방법을 설명합니다.

## 🔧 사전 요구사항

1. **GitHub 저장소**에 코드가 푸시되어 있어야 함
2. **Google Cloud 프로젝트**가 설정되어 있어야 함
3. **서비스 계정 키**가 생성되어 있어야 함

## 📋 GitHub Secrets 설정

GitHub 저장소의 **Settings** → **Secrets and variables** → **Actions**에서 다음 시크릿들을 설정해야 합니다:

### 1. GCP_SA_KEY
Google Cloud 서비스 계정의 JSON 키 파일 내용

**생성 방법:**
```bash
# 서비스 계정 생성
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions Service Account"

# 필요한 권한 부여
gcloud projects add-iam-policy-binding chanel-analytics \
  --member="serviceAccount:github-actions@chanel-analytics.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding chanel-analytics \
  --member="serviceAccount:github-actions@chanel-analytics.iam.gserviceaccount.com" \
  --role="roles/secretmanager.admin"

gcloud projects add-iam-policy-binding chanel-analytics \
  --member="serviceAccount:github-actions@chanel-analytics.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.builder"

gcloud projects add-iam-policy-binding chanel-analytics \
  --member="serviceAccount:github-actions@chanel-analytics.iam.gserviceaccount.com" \
  --role="roles/cloudscheduler.admin"

# 키 파일 생성
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions@chanel-analytics.iam.gserviceaccount.com
```

**설정 방법:**
1. 생성된 `github-actions-key.json` 파일의 전체 내용을 복사
2. GitHub Secrets에 `GCP_SA_KEY` 이름으로 저장

### 2. CLIENT_SECRET_JSON
Google OAuth 클라이언트 시크릿 파일 내용

**설정 방법:**
1. `secrets/client_secret.json` 파일의 전체 내용을 복사
2. GitHub Secrets에 `CLIENT_SECRET_JSON` 이름으로 저장

### 3. TOKEN_YOUTUBE_JSON
YouTube OAuth 토큰 파일 내용

**설정 방법:**
1. `secrets/token_youtube.json` 파일의 전체 내용을 복사
2. GitHub Secrets에 `TOKEN_YOUTUBE_JSON` 이름으로 저장

### 4. TOKEN_SHEETS_JSON
Google Sheets OAuth 토큰 파일 내용

**설정 방법:**
1. `secrets/token_sheets.json` 파일의 전체 내용을 복사
2. GitHub Secrets에 `TOKEN_SHEETS_JSON` 이름으로 저장

## 🚀 자동 배포 트리거

### 자동 배포 조건
- `main` 또는 `master` 브랜치에 푸시
- `channel_analytics/` 폴더 내 파일이 변경된 경우

### 수동 배포
GitHub 저장소의 **Actions** 탭에서 **"Deploy YouTube Analytics to Cloud Run"** 워크플로우를 수동으로 실행할 수 있습니다.

## 📊 배포 과정

1. **코드 체크아웃**: GitHub에서 최신 코드 다운로드
2. **Google 인증**: 서비스 계정을 사용한 GCP 인증
3. **API 활성화**: 필요한 Google Cloud API 활성화
4. **Secret 업로드**: OAuth 토큰들을 Secret Manager에 업로드
5. **Docker 빌드**: 애플리케이션을 Docker 이미지로 빌드
6. **Cloud Run 배포**: Cloud Run Job 생성/업데이트
7. **스케줄러 설정**: 매월 자동 실행을 위한 Cloud Scheduler 설정
8. **테스트 실행**: 배포된 Job을 테스트 실행

## 🔍 모니터링

### 배포 상태 확인
- GitHub Actions 탭에서 워크플로우 실행 상태 확인
- Google Cloud Console에서 Cloud Run Job 상태 확인

### 로그 확인
```bash
# Cloud Run Job 실행 로그 확인
gcloud run jobs executions list --job=yt-monthly-job --region=asia-northeast3
gcloud run jobs executions logs <execution-id> --region=asia-northeast3
```

### 스케줄러 상태 확인
```bash
# Cloud Scheduler 작업 상태 확인
gcloud scheduler jobs describe yt-monthly-schedule
```

## 🛠️ 문제 해결

### 일반적인 문제들

1. **권한 오류**
   - 서비스 계정에 필요한 권한이 부여되었는지 확인
   - GitHub Secrets가 올바르게 설정되었는지 확인

2. **Secret 업로드 실패**
   - JSON 파일 형식이 올바른지 확인
   - GitHub Secrets에 전체 JSON 내용이 포함되었는지 확인

3. **배포 실패**
   - Google Cloud 프로젝트 ID가 올바른지 확인
   - 리전 설정이 올바른지 확인

### 디버깅
GitHub Actions 로그에서 오류 메시지를 확인하고, 필요시 로컬에서 `deploy.sh` 스크립트를 실행하여 문제를 진단할 수 있습니다.

## 📅 스케줄

기본적으로 매월 1일 02:00 (한국 시간)에 자동으로 실행됩니다.

스케줄 변경이 필요한 경우 `.github/workflows/deploy.yml` 파일의 `--schedule` 파라미터를 수정하세요.

## 🔐 보안 고려사항

- GitHub Secrets는 암호화되어 저장됩니다
- 서비스 계정 키는 최소 권한 원칙에 따라 설정됩니다
- OAuth 토큰은 Secret Manager를 통해 안전하게 관리됩니다
