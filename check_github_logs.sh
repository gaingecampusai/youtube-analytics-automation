#!/usr/bin/env bash
set -euo pipefail

# ==========================
# GitHub Actions 로그 확인
# ==========================

REPO="gaingecampusai/youtube-analytics-automation"
WORKFLOW="run-analytics"

echo "🔍 GitHub Actions 로그 확인"
echo "📌 Repository: $REPO"
echo "📊 Workflow: $WORKFLOW"
echo

# 1. GitHub CLI 인증 확인
if ! gh auth status >/dev/null 2>&1; then
    echo "❌ GitHub CLI 인증이 필요합니다."
    echo "💡 gh auth login 명령어로 인증하세요."
    exit 1
fi

# 2. 최근 워크플로우 실행 확인
echo "1️⃣ 최근 워크플로우 실행 확인 중..."
echo "📋 최근 5개 실행:"
gh run list --repo="$REPO" --workflow="$WORKFLOW" --limit=5

# 3. 최신 실행 로그 확인
echo
echo "2️⃣ 최신 실행 로그 확인 중..."
LATEST_RUN=$(gh run list --repo="$REPO" --workflow="$WORKFLOW" --limit=1 --json databaseId --jq '.[0].databaseId')

if [[ -n "$LATEST_RUN" ]]; then
    echo "🔍 실행 ID: $LATEST_RUN"
    echo "📊 로그 다운로드 중..."
    gh run view "$LATEST_RUN" --repo="$REPO" --log
else
    echo "❌ 실행 기록이 없습니다."
fi

echo
echo "📋 추가 확인 방법:"
echo "1. 웹 브라우저: https://github.com/$REPO/actions"
echo "2. 특정 실행 로그: gh run view <run_id> --repo=$REPO --log"
echo "3. 실시간 로그: gh run watch <run_id> --repo=$REPO"
echo
echo "🚀 수동 실행: https://github.com/$REPO/actions/workflows/run_analytics.yml"
