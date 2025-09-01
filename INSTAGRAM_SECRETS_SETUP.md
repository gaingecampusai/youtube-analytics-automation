# Instagram API GitHub Secrets 설정 가이드

## 📋 필요한 GitHub Secrets

Instagram API를 사용하기 위해 다음 GitHub Secrets를 설정해야 합니다:

### 1. 기존 Secrets (YouTube와 공유)
- `CLIENT_SECRET_JSON` - Google OAuth 클라이언트 시크릿
- `TOKEN_SHEETS_JSON` - Google Sheets 액세스 토큰

### 2. 새로운 Instagram Secrets
- `FACEBOOK_APP_ID` - Facebook 앱 ID
- `FACEBOOK_APP_SECRET` - Facebook 앱 시크릿
- `FACEBOOK_ACCESS_TOKEN` - Facebook 액세스 토큰
- `INSTAGRAM_BUSINESS_ACCOUNT_ID` - Instagram 비즈니스 계정 ID

## 🔧 설정 방법

### 1. Facebook 개발자 계정에서 정보 가져오기

#### 1.1 Facebook 앱 ID와 시크릿
1. https://developers.facebook.com 접속
2. 앱 선택 → 설정 → 기본 설정
3. **앱 ID**와 **앱 시크릿** 복사

#### 1.2 액세스 토큰 생성
1. 개발자 대시보드 → 도구 → Graph API 탐색기
2. 앱 선택 → 사용자 토큰 생성
3. 필요한 권한 선택:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
4. **액세스 토큰** 복사

#### 1.3 Instagram 비즈니스 계정 ID 찾기
1. Graph API 탐색기에서 다음 URL 호출:
   ```
   https://graph.facebook.com/v18.0/me/accounts?access_token=YOUR_ACCESS_TOKEN
   ```
2. 연결된 페이지 목록에서 Instagram 계정이 연결된 페이지 찾기
3. 페이지 ID로 다음 URL 호출:
   ```
   https://graph.facebook.com/v18.0/{PAGE_ID}?fields=instagram_business_account&access_token=YOUR_ACCESS_TOKEN
   ```
4. **instagram_business_account.id** 값이 Instagram 비즈니스 계정 ID

### 2. GitHub Secrets 설정

#### 2.1 GitHub 저장소에서 Secrets 설정
1. GitHub 저장소 → Settings → Secrets and variables → Actions
2. "New repository secret" 클릭
3. 다음 Secrets 추가:

```
FACEBOOK_APP_ID=123456789012345
FACEBOOK_APP_SECRET=abcdef1234567890abcdef1234567890
FACEBOOK_ACCESS_TOKEN=EAABwzLixnjYBO...
INSTAGRAM_BUSINESS_ACCOUNT_ID=17841412345678901
```

## 🧪 테스트 방법

### 1. 로컬 테스트
```bash
# 환경 변수 설정
export FACEBOOK_APP_ID="your_app_id"
export FACEBOOK_APP_SECRET="your_app_secret"
export FACEBOOK_ACCESS_TOKEN="your_access_token"
export INSTAGRAM_BUSINESS_ACCOUNT_ID="your_instagram_business_account_id"

# 테스트 실행
python instagram_analytics.py
```

### 2. GitHub Actions 테스트
1. GitHub 저장소 → Actions
2. "Run Instagram Analytics" 워크플로우 선택
3. "Run workflow" 클릭
4. 수동 실행으로 테스트

## ⚠️ 주의사항

### 1. 액세스 토큰 관리
- **액세스 토큰은 60일 후 만료**됩니다
- 만료 전에 새 토큰을 생성하여 GitHub Secrets 업데이트 필요
- 토큰은 절대 공개하지 마세요

### 2. API 제한
- **시간당 제한**: 앱당 200회 호출
- **일일 제한**: 앱당 5,000회 호출
- 제한에 도달하면 24시간 대기 필요

### 3. 권한 설정
- Instagram 계정이 **비즈니스 계정**이어야 합니다
- Facebook 페이지와 연결되어 있어야 합니다
- 앱 검토 승인이 완료되어야 합니다

## 🔍 문제 해결

### 1. 일반적인 오류

#### "Invalid access token"
- 액세스 토큰이 만료되었거나 잘못됨
- 새 토큰 생성 필요

#### "Instagram business account not found"
- Instagram 계정이 비즈니스 계정이 아님
- Facebook 페이지와 연결되지 않음

#### "Insufficient permissions"
- 앱에 필요한 권한이 없음
- 앱 검토 승인 대기 중

### 2. 디버깅 방법
```python
# instagram_analytics.py에 디버그 코드 추가
import logging
logging.basicConfig(level=logging.DEBUG)

# API 응답 확인
print(f"Instagram Business Account ID: {INSTAGRAM_BUSINESS_ACCOUNT_ID}")
```

## 📞 지원

문제가 발생하면 다음을 확인하세요:
1. Facebook 개발자 문서: https://developers.facebook.com/docs/instagram-api
2. Instagram Graph API 가이드: https://developers.facebook.com/docs/instagram-api/getting-started
3. GitHub Actions 로그 확인
