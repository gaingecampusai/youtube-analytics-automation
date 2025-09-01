#!/usr/bin/env bash
set -euo pipefail

# ==========================
# 간단한 로그 확인
# ==========================

PROJECT_ID="${PROJECT_ID:-chanel-analytics}"
REGION="${REGION:-asia-northeast3}"
JOB_NAME="${JOB_NAME:-yt-monthly-job}"

echo "📊 YouTube Analytics 로그 확인"
echo "📌 Project: $PROJECT_ID"
echo "🌍 Region: $REGION"
echo "📊 Job: $JOB_NAME"
echo

# 최근 실행 확인
echo "🔍 최근 실행 기록:"
gcloud run jobs executions list --job="$JOB_NAME" --region="$REGION" --limit=3 --format="table(name,createTime,completionTime,state)" || {
    echo "❌ Job이 존재하지 않거나 실행 기록이 없습니다."
    echo "💡 GitHub Actions에서 배포를 먼저 실행하세요."
    exit 1
}

echo
echo "📋 로그 확인 방법:"
echo "1. GitHub Actions: https://github.com/gaingecampusai/youtube-analytics-automation/actions"
echo "2. Cloud Console: https://console.cloud.google.com/run/jobs/$JOB_NAME?project=$PROJECT_ID&region=$REGION"
echo "3. 실시간 모니터링: ./monitor_logs.sh"
echo
echo "🚀 수동 실행: gcloud run jobs execute $JOB_NAME --region=$REGION --wait"
