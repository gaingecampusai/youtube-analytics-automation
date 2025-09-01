#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로컬에서 OAuth 토큰을 생성하는 스크립트
Cloud Run에 배포하기 전에 이 스크립트로 토큰을 생성해야 합니다.
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# OAuth 스코프
SCOPES_YOUTUBE = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]
SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]
SCOPES_SINGLE = SCOPES_YOUTUBE + SCOPES_SHEETS

# 기본 경로 설정
BASE_DIR = "/Users/adam/Documents/dev/program/channel_analytics" if os.getenv("ENV","local")=="local" else "/workspace"
os.makedirs(BASE_DIR, exist_ok=True)

# 파일 경로 (환경변수로 오버라이드 가능)
CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE", os.path.join(BASE_DIR, "secrets/client_secret.json"))
TOKEN_SINGLE = os.getenv("TOKEN_SINGLE", os.path.join(BASE_DIR, "secrets/token.json"))
TOKEN_YOUTUBE = os.getenv("TOKEN_YOUTUBE", os.path.join(BASE_DIR, "secrets/token_youtube.json"))
TOKEN_SHEETS = os.getenv("TOKEN_SHEETS", os.path.join(BASE_DIR, "secrets/token_sheets.json"))

# OAuth 포트 설정
OAUTH_PORT_YT = int(os.getenv("OAUTH_PORT_YT", "8081"))
OAUTH_PORT_SH = int(os.getenv("OAUTH_PORT_SH", "8081"))

# 비대화형 모드 (로컬에서는 false)
NON_INTERACTIVE = os.getenv("NON_INTERACTIVE", "false").lower() == "true"

def generate_token(token_path: str, scopes: list, description: str, port: int = 8081):
    
    """OAuth 토큰 생성"""
    print(f"\n🔐 {description} 토큰 생성 중...")
    
    if os.path.exists(token_path):
        print(f"⚠️  기존 토큰 파일이 존재합니다: {token_path}")
        response = input("덮어쓰시겠습니까? (y/N): ")
        if response.lower() != 'y':
            print("건너뜁니다.")
            return True
    
    try:
        # secrets 디렉토리 생성
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE, 
            scopes
        )
        
        print(f"🌐 브라우저가 열립니다. Google 계정으로 로그인하고 권한을 승인해주세요.")
        print(f"   포트: {port}")
        print(f"   URL: http://localhost:{port}")
        
        creds = flow.run_local_server(
            port=port, 
            access_type="offline", 
            prompt="consent"
        )
        
        # 토큰 저장
        with open(token_path, "w") as f:
            f.write(creds.to_json())
        
        print(f"✅ 토큰이 생성되었습니다: {token_path}")
        
    except Exception as e:
        print(f"❌ 토큰 생성 실패: {e}")
        print(f"💡 확인사항:")
        print(f"   1. {CLIENT_SECRET_FILE} 파일이 존재하는지 확인")
        print(f"   2. Google Cloud Console에서 OAuth 2.0 클라이언트 ID 설정 확인")
        print(f"   3. 리디렉션 URI에 http://localhost:{port} 추가되었는지 확인")
        return False
    
    return True

def main():
    print("🚀 YouTube Analytics OAuth 토큰 생성기")
    print("=" * 50)
    
    # client_secret.json 확인
    if not os.path.exists(CLIENT_SECRET_FILE):
        print(f"❌ {CLIENT_SECRET_FILE} 파일이 없습니다.")
        print("Google Cloud Console에서 OAuth 2.0 클라이언트 ID를 다운로드하세요.")
        return
    
    # secrets 디렉토리 생성
    os.makedirs("secrets", exist_ok=True)
    
    print("\n📋 토큰 생성 모드를 선택하세요:")
    print("1. 단일 토큰 (YouTube + Sheets)")
    print("2. 이원화 토큰 (YouTube + Sheets 분리)")
    print("3. 모든 토큰 생성")
    
    choice = input("\n선택 (1-3): ").strip()
    
    if choice == "1":
        generate_token(TOKEN_SINGLE, SCOPES_SINGLE, "단일", OAUTH_PORT_YT)
    elif choice == "2":
        generate_token(TOKEN_YOUTUBE, SCOPES_YOUTUBE, "YouTube", OAUTH_PORT_YT)
        generate_token(TOKEN_SHEETS, SCOPES_SHEETS, "Sheets", OAUTH_PORT_SH)
    elif choice == "3":
        generate_token(TOKEN_SINGLE, SCOPES_SINGLE, "단일", OAUTH_PORT_YT)
        generate_token(TOKEN_YOUTUBE, SCOPES_YOUTUBE, "YouTube", OAUTH_PORT_YT)
        generate_token(TOKEN_SHEETS, SCOPES_SHEETS, "Sheets", OAUTH_PORT_SH)
    else:
        print("❌ 잘못된 선택입니다.")
        return
    
    print("\n🎉 토큰 생성이 완료되었습니다!")
    print("\n다음 단계:")
    print("1. 생성된 토큰 파일들을 확인하세요")
    print("2. deploy.sh 스크립트를 실행하여 Cloud Run에 배포하세요")

if __name__ == "__main__":
    main()
