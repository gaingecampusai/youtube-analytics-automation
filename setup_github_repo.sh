#!/usr/bin/env bash
set -euo pipefail

# ==========================
# GitHub 저장소 설정
# ==========================

REPO_NAME="youtube-analytics-automation"
DESCRIPTION="YouTube Analytics 월간 보고서 자동화 - Cloud Run + GitHub Actions"

echo "🔧 GitHub 저장소 설정"
echo "📌 Repository: $REPO_NAME"
echo "📝 Description: $DESCRIPTION"
echo

# 1. Git 초기화 (이미 초기화되어 있지 않은 경우)
if [ ! -d ".git" ]; then
    echo "1️⃣ Git 저장소 초기화 중..."
    git init
    echo "✅ Git 초기화 완료"
else
    echo "1️⃣ Git 저장소가 이미 초기화되어 있습니다."
fi

# 2. .gitignore 파일 생성
echo "2️⃣ .gitignore 파일 생성 중..."
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
env/
ENV/
.venv/
.env/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
secrets/
*.json
!requirements.txt
!package.json
!package-lock.json

# Logs
*.log
logs/

# Temporary files
*.tmp
*.temp
EOF
echo "✅ .gitignore 파일 생성 완료"

# 3. 초기 커밋
echo "3️⃣ 초기 커밋 생성 중..."
git add .
git commit -m "Initial commit: YouTube Analytics 자동화 프로젝트

- YouTube Analytics API를 통한 월간 데이터 수집
- Google Sheets 자동 기록
- Cloud Run Job 배포
- GitHub Actions 자동 배포 설정
- OAuth 2.0 인증 (이원화 토큰 모드)"

echo "✅ 초기 커밋 완료"

# 4. GitHub CLI 확인 및 저장소 생성
if command -v gh >/dev/null 2>&1; then
    echo "4️⃣ GitHub CLI를 사용하여 저장소 생성 중..."
    
    # GitHub 인증 확인
    if gh auth status >/dev/null 2>&1; then
        echo "✅ GitHub 인증 확인됨"
        
        # 저장소 생성
        gh repo create "$REPO_NAME" \
            --description "$DESCRIPTION" \
            --public \
            --source=. \
            --remote=origin \
            --push
        
        echo "✅ GitHub 저장소 생성 및 푸시 완료"
    else
        echo "❌ GitHub CLI 인증이 필요합니다."
        echo "다음 명령어로 인증하세요:"
        echo "  gh auth login"
        echo
        echo "또는 수동으로 GitHub에서 저장소를 생성하고 다음 명령어를 실행하세요:"
        echo "  git remote add origin https://github.com/YOUR_USERNAME/$REPO_NAME.git"
        echo "  git push -u origin main"
    fi
else
    echo "4️⃣ GitHub CLI가 설치되어 있지 않습니다."
    echo
    echo "📋 수동 설정 방법:"
    echo "1. https://github.com/new 에서 새 저장소 생성"
    echo "   - Repository name: $REPO_NAME"
    echo "   - Description: $DESCRIPTION"
    echo "   - Public 선택"
    echo "   - README, .gitignore, license 체크 해제"
    echo
    echo "2. 다음 명령어로 원격 저장소 연결:"
    echo "   git remote add origin https://github.com/YOUR_USERNAME/$REPO_NAME.git"
    echo "   git push -u origin main"
    echo
    echo "3. GitHub CLI 설치 (선택사항):"
    echo "   brew install gh  # macOS"
    echo "   gh auth login"
fi

echo
echo "🎉 GitHub 저장소 설정 완료!"
echo
echo "📋 다음 단계:"
echo "1. GitHub 저장소가 생성되었는지 확인"
echo "2. GitHub Secrets 설정 (GITHUB_ACTIONS_SETUP.md 참조)"
echo "3. 코드 수정 후 푸시하여 자동 배포 테스트"
echo
echo "🔗 저장소 URL: https://github.com/YOUR_USERNAME/$REPO_NAME"
