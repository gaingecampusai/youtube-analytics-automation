# GitHub Personal Access Token 설정 가이드

GitHub Actions 워크플로우 파일을 푸시하기 위해서는 적절한 권한을 가진 Personal Access Token이 필요합니다.

## 🔧 Personal Access Token 생성

### 1단계: GitHub에서 토큰 생성

1. **GitHub.com**에 로그인
2. 우측 상단 프로필 아이콘 클릭 → **Settings**
3. 좌측 메뉴에서 **Developer settings** 클릭
4. **Personal access tokens** → **Tokens (classic)** 클릭
5. **Generate new token** → **Generate new token (classic)** 클릭

### 2단계: 토큰 설정

**Note**: `YouTube Analytics Automation Token`

**Expiration**: `No expiration` (또는 원하는 만료일)

**Scopes** (권한 범위):

- ✅ `repo` (전체 저장소 접근)
- ✅ `workflow` (GitHub Actions 워크플로우 관리)
- ✅ `admin:org` (조직 관리 - 조직 저장소인 경우)

### 3단계: 토큰 생성 및 저장

1. **Generate token** 클릭
2. 생성된 토큰을 안전한 곳에 복사 (다시 볼 수 없음)
3. **Done** 클릭

## 🔐 GitHub CLI에 토큰 설정

생성된 토큰을 사용하여 GitHub CLI에 인증:

```bash
# GitHub CLI 로그아웃 (기존 인증 제거)
gh auth logout

# Personal Access Token으로 인증
gh auth login --with-token < YOUR_TOKEN_HERE >
```

또는 대화형으로:

```bash
gh auth login
# "Paste an authentication token" 선택
# 생성한 토큰 붙여넣기
```

## 🚀 저장소 푸시

토큰 설정 후 다시 푸시:

```bash
git push -u origin main
```

## 🔒 보안 주의사항

- Personal Access Token을 안전하게 보관하세요
- 토큰을 버전 관리 시스템에 커밋하지 마세요
- 필요시 토큰을 재생성하세요
- 최소 권한 원칙에 따라 필요한 스코프만 부여하세요

## 🛠️ 문제 해결

### "workflow scope" 오류

GitHub Actions 워크플로우 파일을 푸시할 때 이 오류가 발생하면:

1. Personal Access Token에 `workflow` 스코프가 포함되어 있는지 확인
2. 토큰을 재생성하여 올바른 권한 부여

### 권한 부족 오류

다른 권한 오류가 발생하면:

1. 토큰에 필요한 스코프가 모두 포함되어 있는지 확인
2. 저장소에 대한 적절한 권한이 있는지 확인
