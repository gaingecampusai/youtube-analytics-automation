#!/usr/bin/env bash
set -euo pipefail

# ==========================
# YouTube Analytics 로그 모니터링
# ==========================

PROJECT_ID="${PROJECT_ID:-chanel-analytics}"
REGION="${REGION:-asia-northeast3}"
JOB_NAME="${JOB_NAME:-yt-monthly-job}"

echo "🔍 YouTube Analytics 로그 모니터링"
echo "📌 Project: $PROJECT_ID"
echo "🌍 Region: $REGION"
echo "📊 Job: $JOB_NAME"
echo

# 1. Cloud Run Job 상태 확인
echo "1️⃣ Cloud Run Job 상태 확인 중..."
if gcloud run jobs describe "$JOB_NAME" --region="$REGION" >/dev/null 2>&1; then
    echo "✅ Job이 존재합니다"
else
    echo "❌ Job이 존재하지 않습니다. 배포를 먼저 실행하세요."
    exit 1
fi

# 2. 최근 실행 기록 확인
echo
echo "2️⃣ 최근 실행 기록 확인 중..."
echo "📋 최근 5개 실행:"
gcloud run jobs executions list --job="$JOB_NAME" --region="$REGION" --limit=5 --format="table(name,createTime,completionTime,state)"

# 3. 실시간 로그 모니터링
echo
echo "3️⃣ 실시간 로그 모니터링 시작..."
echo "💡 Ctrl+C로 종료할 수 있습니다"
echo "⏳ 새로운 실행을 기다리는 중..."
echo

# 실시간 로그 스트리밍
gcloud run jobs executions list --job="$JOB_NAME" --region="$REGION" --limit=1 --format="value(name)" | while read -r execution_name; do
    if [[ -n "$execution_name" ]]; then
        echo "🔍 실행 로그 확인: $execution_name"
        gcloud run jobs executions logs read "$execution_name" --region="$REGION" --format="value(logMessage)" || echo "로그가 없습니다"
    fi
done

# 4. 로그 필터링 옵션
echo
echo "📋 추가 로그 확인 명령어:"
echo "• 전체 로그: gcloud run jobs executions logs read <execution_name> --region=$REGION"
echo "• 특정 실행 로그: gcloud run jobs executions describe <execution_name> --region=$REGION"
echo "• 실시간 로그: gcloud run jobs executions logs tail <execution_name> --region=$REGION"
echo
echo "🔗 Cloud Console: https://console.cloud.google.com/run/jobs/$JOB_NAME?project=$PROJECT_ID&region=$REGION"
