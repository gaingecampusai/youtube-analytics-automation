# Instagram API 설정 가이드

## 1. Facebook 개발자 계정 설정

### 1.1 Facebook 개발자 계정 생성

1. https://developers.facebook.com 접속
2. "시작하기" 클릭
3. Facebook 계정으로 로그인
4. 개발자 계정 정보 입력 (이름, 이메일 등)

### 1.2 앱 생성

1. 개발자 대시보드에서 "앱 만들기" 클릭
2. 앱 유형 선택:
   - **비즈니스** 선택 (Instagram Basic Display API 사용 시)
   - **소비자** 선택 (Instagram Graph API 사용 시)
3. 앱 이름 입력 (예: "Instagram Analytics Tool")
4. 연락처 이메일 입력

## 2. Instagram API 권한 설정

### 2.1 Instagram Basic Display API (개인 계정용)

- **용도**: 개인 Instagram 계정 데이터 접근
- **권한**: 프로필 정보, 미디어 데이터
- **제한**: 비즈니스 계정이 아닌 개인 계정만 가능

### 2.2 Instagram Graph API (비즈니스 계정용) ⭐ **권장**

- **용도**: 비즈니스/크리에이터 Instagram 계정 데이터 접근
- **권한**: 더 많은 데이터 접근 가능
- **필요 조건**: Instagram 비즈니스 계정 또는 크리에이터 계정

## 3. Instagram 계정을 비즈니스 계정으로 변경

### 3.1 Instagram 앱에서 설정

1. Instagram 앱 열기
2. 프로필 → 설정 → 계정
3. "비즈니스 계정으로 전환" 또는 "크리에이터 계정으로 전환"
4. 카테고리 선택 (예: "콘텐츠 크리에이터")
5. 연락처 정보 입력

### 3.2 Facebook 페이지 연결

1. Facebook 페이지 생성 (없는 경우)
2. Instagram 계정을 Facebook 페이지에 연결
3. 비즈니스 관리자에서 Instagram 계정 추가

## 4. API 권한 및 토큰 설정

### 4.1 Facebook 앱에서 Instagram 권한 추가

1. Facebook 개발자 대시보드 → 앱 선택
2. 제품 → Instagram Basic Display 또는 Instagram Graph API 추가
3. 필요한 권한 추가:
   - `instagram_basic` (기본 정보)
   - `instagram_content_publish` (게시물 정보)
   - `pages_show_list` (페이지 목록)
   - `pages_read_engagement` (페이지 참여도)

### 4.2 앱 검토 및 승인

1. 개발자 대시보드 → 앱 검토
2. 필요한 권한에 대한 검토 요청
3. Facebook 승인 대기 (보통 1-3일)

### 4.3 액세스 토큰 생성

1. **사용자 액세스 토큰** 생성
2. **페이지 액세스 토큰** 생성
3. **Instagram 비즈니스 계정 ID** 확인

## 5. Python 코드 구현 준비

### 5.1 필요한 라이브러리

```bash
pip install facebook-business
pip install requests
```

### 5.2 환경 변수 설정

```bash
# .env 파일 또는 환경 변수
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
FACEBOOK_ACCESS_TOKEN=your_user_access_token
INSTAGRAM_BUSINESS_ACCOUNT_ID=your_instagram_business_account_id
```

## 6. API 제한 및 주의사항

### 6.1 API 호출 제한

- **시간당 제한**: 앱당 200회 호출
- **일일 제한**: 앱당 5,000회 호출
- **페이지당 제한**: 페이지당 100회 호출

### 6.2 데이터 접근 제한

- **개인 계정**: 제한된 데이터만 접근 가능
- **비즈니스 계정**: 더 많은 데이터 접근 가능
- **릴스 데이터**: 별도 권한 필요

## 7. 다음 단계

설정이 완료되면 다음 파일들을 생성할 예정:

- `instagram_analytics.py` - Instagram 데이터 수집 스크립트
- `instagram_monthly_report.py` - 월간 보고서 생성
- `.github/workflows/run_instagram_analytics.yml` - 자동화 워크플로우

## 8. 문제 해결

### 8.1 일반적인 오류

- **권한 오류**: 앱 검토 승인 대기
- **토큰 만료**: 토큰 갱신 필요
- **계정 연결 오류**: Facebook 페이지와 Instagram 계정 연결 확인

### 8.2 도움말

- Facebook 개발자 문서: https://developers.facebook.com/docs/instagram-api
- Instagram Graph API 가이드: https://developers.facebook.com/docs/instagram-api/getting-started
