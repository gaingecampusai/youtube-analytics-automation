#!/usr/bin/env bash
set -euo pipefail

# ==========================
# 기본 설정 (필요시 env로 덮어쓰기)
# ==========================
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${REGION:-asia-northeast3}"               # 서울 리전
REPO="${REPO:-yt-repo}"
IMAGE_NAME="${IMAGE_NAME:-yt-monthly}"
JOB_NAME="${JOB_NAME:-yt-monthly-job}"
SCHED_NAME="${SCHED_NAME:-yt-monthly-schedule}"
CRON="${CRON:-0 2 1 * *}"                         # 매월 1일 02:00
TIMEZONE="${TIMEZONE:-Asia/Seoul}"

# 실행 모드
USE_DUAL_TOKENS="${USE_DUAL_TOKENS:-false}"       # true면 YouTube/Sheets 토큰 분리
RUN_TEST_NOW="${RUN_TEST_NOW:-true}"              # 배포 직후 1회 즉시 실행

# (옵션) 환경변수로 채널/시트 지정 가능
CHANNEL_ID="${CHANNEL_ID:-}"
SPREADSHEET_ID="${SPREADSHEET_ID:-}"
SHEET_NAME="${SHEET_NAME:-}"

# Secret 이름
SECRET_CLIENT="yt_client_secret"
SECRET_TOKEN_SINGLE="yt_token"
SECRET_TOKEN_YT="yt_token_youtube"
SECRET_TOKEN_SH="yt_token_sheets"

# 로컬 파일 경로 (현재 폴더 기준)
CLIENT_JSON="${CLIENT_JSON:-secrets/client_secret.json}"
TOKEN_SINGLE="${TOKEN_SINGLE:-secrets/token.json}"
TOKEN_YT="${TOKEN_YT:-secrets/token_youtube.json}"
TOKEN_SH="${TOKEN_SH:-secrets/token_sheets.json}"

# ==========================
# 사전 체크
# ==========================
if ! command -v gcloud >/dev/null 2>&1; then
  echo "❌ gcloud CLI가 설치되어 있지 않습니다. 설치 후 다시 실행해주세요."
  exit 1
fi

if [[ -z "${PROJECT_ID}" || "${PROJECT_ID}" == "(unset)" ]]; then
  echo "❌ GCP 프로젝트가 설정되지 않았습니다. 아래를 먼저 실행하세요:"
  echo "   gcloud auth login"
  echo "   gcloud config set project <YOUR_PROJECT_ID>"
  exit 1
fi

# 필수 파일 체크
if [[ ! -f "$CLIENT_JSON" ]]; then
  echo "❌ OAuth client_secret 파일이 없습니다: $CLIENT_JSON"
  exit 1
fi

if [[ "$USE_DUAL_TOKENS" == "true" ]]; then
  [[ -f "$TOKEN_YT" ]] || { echo "❌ YouTube 토큰 없음: $TOKEN_YT"; exit 1; }
  [[ -f "$TOKEN_SH" ]] || { echo "❌ Sheets 토큰 없음: $TOKEN_SH"; exit 1; }
else
  [[ -f "$TOKEN_SINGLE" ]] || { echo "❌ 단일 토큰 없음: $TOKEN_SINGLE"; exit 1; }
fi

echo "📌 Project : $PROJECT_ID"
echo "📌 Region  : $REGION"
echo "📌 Job     : $JOB_NAME"
echo "📌 Cron    : $CRON ($TIMEZONE)"
echo "📌 Dual    : $USE_DUAL_TOKENS"
echo

# ==========================
# API 활성화
# ==========================
echo "🔧 Enable required APIs..."
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  cloudscheduler.googleapis.com \
  youtube.googleapis.com \
  youtubeanalytics.googleapis.com \
  sheets.googleapis.com

# ==========================
# Artifact Registry
# ==========================
echo "🏗️  Ensure Artifact Registry..."
gcloud artifacts repositories create "$REPO" \
  --repository-format=docker --location="$REGION" \
  --description="YT monthly repo" 2>/dev/null || true

IMAGE="$REGION-docker.pkg.dev/$PROJECT_ID/$REPO/$IMAGE_NAME:latest"

# ==========================
# Secrets
# ==========================
echo "🔐 Upload secrets..."
gcloud secrets create "$SECRET_CLIENT" --replication-policy="automatic" 2>/dev/null || true
gcloud secrets versions add "$SECRET_CLIENT" --data-file="$CLIENT_JSON" >/dev/null

if [[ "$USE_DUAL_TOKENS" == "true" ]]; then
  gcloud secrets create "$SECRET_TOKEN_YT" --replication-policy="automatic" 2>/dev/null || true
  gcloud secrets create "$SECRET_TOKEN_SH" --replication-policy="automatic" 2>/dev/null || true
  gcloud secrets versions add "$SECRET_TOKEN_YT" --data-file="$TOKEN_YT" >/dev/null
  gcloud secrets versions add "$SECRET_TOKEN_SH" --data-file="$TOKEN_SH" >/dev/null
else
  gcloud secrets create "$SECRET_TOKEN_SINGLE" --replication-policy="automatic" 2>/dev/null || true
  gcloud secrets versions add "$SECRET_TOKEN_SINGLE" --data-file="$TOKEN_SINGLE" >/dev/null
fi

# ==========================
# 서비스 계정
# ==========================
echo "👤 Ensure service accounts..."
SA="run-job-sa@$PROJECT_ID.iam.gserviceaccount.com"
gcloud iam service-accounts create run-job-sa --display-name "Cloud Run Job SA" 2>/dev/null || true

# Secret 접근 권한
gcloud secrets add-iam-policy-binding "$SECRET_CLIENT" \
  --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" >/dev/null
if [[ "$USE_DUAL_TOKENS" == "true" ]]; then
  gcloud secrets add-iam-policy-binding "$SECRET_TOKEN_YT" \
    --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" >/dev/null
  gcloud secrets add-iam-policy-binding "$SECRET_TOKEN_SH" \
    --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" >/dev/null
else
  gcloud secrets add-iam-policy-binding "$SECRET_TOKEN_SINGLE" \
    --member="serviceAccount:$SA" --role="roles/secretmanager.secretAccessor" >/dev/null
fi

# ==========================
# 빌드 & 푸시
# ==========================
echo "📦 Build & Push image..."
gcloud builds submit --tag "$IMAGE" .

# ==========================
# Cloud Run Job
# ==========================
echo "🚀 Create/Update Cloud Run Job..."
ENV_VARS="ENV=cloud,NON_INTERACTIVE=true,CLIENT_SECRET_FILE=/secrets/client_secret.json"
SECRET_MOUNTS="/secrets/client_secret.json=$SECRET_CLIENT:latest"

# 선택적 환경변수 전달
[[ -n "$CHANNEL_ID"     ]] && ENV_VARS="$ENV_VARS,CHANNEL_ID=$CHANNEL_ID"
[[ -n "$SPREADSHEET_ID" ]] && ENV_VARS="$ENV_VARS,SPREADSHEET_ID=$SPREADSHEET_ID"
[[ -n "$SHEET_NAME"     ]] && ENV_VARS="$ENV_VARS,SHEET_NAME=$SHEET_NAME"

if [[ "$USE_DUAL_TOKENS" == "true" ]]; then
  ENV_VARS="$ENV_VARS,TOKEN_YOUTUBE=/secrets/token_youtube.json,TOKEN_SHEETS=/secrets/token_sheets.json,USE_DUAL_TOKENS=true"
  SECRET_MOUNTS="$SECRET_MOUNTS,/secrets/token_youtube.json=$SECRET_TOKEN_YT:latest,/secrets/token_sheets.json=$SECRET_TOKEN_SH:latest"
else
  ENV_VARS="$ENV_VARS,TOKEN_SINGLE=/secrets/token.json"
  SECRET_MOUNTS="$SECRET_MOUNTS,/secrets/token.json=$SECRET_TOKEN_SINGLE:latest"
fi

if gcloud run jobs describe "$JOB_NAME" --region "$REGION" >/dev/null 2>&1; then
  gcloud run jobs update "$JOB_NAME" \
    --image "$IMAGE" \
    --region "$REGION" \
    --service-account "$SA" \
    --set-env-vars "$ENV_VARS" \
    --set-secrets "$SECRET_MOUNTS" \
    --max-retries=1 --tasks=1 --task-timeout=1800s
else
  gcloud run jobs create "$JOB_NAME" \
    --image "$IMAGE" \
    --region "$REGION" \
    --service-account "$SA" \
    --set-env-vars "$ENV_VARS" \
    --set-secrets "$SECRET_MOUNTS" \
    --max-retries=1 --tasks=1 --task-timeout=1800s
fi

# ==========================
# Cloud Scheduler
# ==========================
echo "⏰ Create/Update Cloud Scheduler..."
SCHED_SA="scheduler-invoker@$PROJECT_ID.iam.gserviceaccount.com"
gcloud iam service-accounts create scheduler-invoker --display-name "Scheduler Invoker" 2>/dev/null || true
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SCHED_SA" --role="roles/run.invoker" >/dev/null

JOB_URI="https://$REGION-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/$PROJECT_ID/jobs/$JOB_NAME:run"

if gcloud scheduler jobs describe "$SCHED_NAME" >/dev/null 2>&1; then
  gcloud scheduler jobs update http "$SCHED_NAME" \
    --schedule="$CRON" --time-zone="$TIMEZONE" \
    --http-method=POST --uri="$JOB_URI" \
    --oauth-service-account-email="$SCHED_SA" \
    --oauth-token-audience="https://$REGION-run.googleapis.com/"
else
  gcloud scheduler jobs create http "$SCHED_NAME" \
    --schedule="$CRON" --time-zone="$TIMEZONE" \
    --http-method=POST --uri="$JOB_URI" \
    --oauth-service-account-email="$SCHED_SA" \
    --oauth-token-audience="https://$REGION-run.googleapis.com/"
fi

# ==========================
# 1회 테스트 실행
# ==========================
if [[ "$RUN_TEST_NOW" == "true" ]]; then
  echo "▶️  Execute job once (wait for completion)..."
  gcloud run jobs execute "$JOB_NAME" --region "$REGION" --wait
fi

echo "✅ Done!"
echo "📜 Logs: gcloud logs read --region $REGION --limit 100 --format='value(textPayload)' --order=desc"