#!/usr/bin/env bash
set -euo pipefail

# ==========================
# GitHub Actions 서비스 계정 설정
# ==========================

PROJECT_ID="${PROJECT_ID:-chanel-analytics}"
SA_NAME="github-actions"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🔧 GitHub Actions 서비스 계정 설정"
echo "📌 Project: $PROJECT_ID"
echo "👤 Service Account: $SA_EMAIL"
echo

# 1. 서비스 계정 생성
echo "1️⃣ 서비스 계정 생성 중..."
gcloud iam service-accounts create "$SA_NAME" \
  --display-name="GitHub Actions Service Account" \
  --description="Service account for GitHub Actions deployment" 2>/dev/null || echo "서비스 계정이 이미 존재합니다."

# 2. 필요한 권한 부여
echo "2️⃣ 권한 부여 중..."

# Cloud Run 관리자
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.admin" >/dev/null

# Secret Manager 관리자
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.admin" >/dev/null

# Cloud Build 빌더
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/cloudbuild.builds.builder" >/dev/null

# Cloud Scheduler 관리자
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/cloudscheduler.admin" >/dev/null

# Artifact Registry 관리자
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/artifactregistry.admin" >/dev/null

# Service Usage 관리자 (API 활성화용)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/serviceusage.serviceUsageAdmin" >/dev/null

# 3. 서비스 계정 키 생성
echo "3️⃣ 서비스 계정 키 생성 중..."
KEY_FILE="github-actions-key.json"
gcloud iam service-accounts keys create "$KEY_FILE" \
  --iam-account="$SA_EMAIL"

echo "✅ 서비스 계정 설정 완료!"
echo
echo "📋 다음 단계:"
echo "1. 생성된 '$KEY_FILE' 파일의 내용을 복사하세요"
echo "2. GitHub 저장소의 Settings → Secrets and variables → Actions로 이동하세요"
echo "3. 'GCP_SA_KEY' 이름으로 시크릿을 추가하고 키 파일 내용을 붙여넣으세요"
echo
echo "🔐 키 파일 내용:"
echo "===================="
cat "$KEY_FILE"
echo "===================="
echo
echo "⚠️  보안 주의사항:"
echo "- 이 키 파일을 안전하게 보관하세요"
echo "- GitHub Secrets에 설정한 후 로컬 키 파일을 삭제하세요"
echo "- 키 파일을 버전 관리 시스템에 커밋하지 마세요"
