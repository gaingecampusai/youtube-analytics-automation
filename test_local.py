#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
로컬에서 인증과 기본 기능을 테스트하는 스크립트
"""

import os
import sys
import logging
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from yt_monthly_report import build_services, get_last_month_range

def test_authentication():
    """인증 테스트"""
    print("🔐 인증 테스트 중...")
    
    try:
        # 로컬 테스트를 위해 환경변수 설정 (모듈 import 전에 설정)
        os.environ["NON_INTERACTIVE"] = "false"
        os.environ["ENV"] = "local"
        os.environ["BASE_DIR"] = "/Users/adam/Documents/dev/program/channel_analytics"
        os.environ["CLIENT_SECRET_FILE"] = "/Users/adam/Documents/dev/program/channel_analytics/secrets/client_secret.json"
        os.environ["TOKEN_YOUTUBE"] = "/Users/adam/Documents/dev/program/channel_analytics/secrets/token_youtube.json"
        os.environ["TOKEN_SHEETS"] = "/Users/adam/Documents/dev/program/channel_analytics/secrets/token_sheets.json"
        os.environ["USE_DUAL_TOKENS"] = "true"
        
        # 모듈을 다시 import하여 환경변수 적용
        import importlib
        import yt_monthly_report
        importlib.reload(yt_monthly_report)
        
        youtube, yta, sheets = yt_monthly_report.build_services()
        
        print("✅ YouTube API 연결 성공")
        print("✅ YouTube Analytics API 연결 성공") 
        print("✅ Google Sheets API 연결 성공")
        
        return youtube, yta, sheets
        
    except Exception as e:
        print(f"❌ 인증 실패: {e}")
        print("\n💡 해결 방법:")
        print("1. generate_token.py를 실행하여 토큰을 생성하세요")
        print("2. client_secret.json 파일이 올바른지 확인하세요")
        return None, None, None

def test_youtube_api(youtube):
    """YouTube API 테스트"""
    print("\n📺 YouTube API 테스트 중...")
    
    try:
        # 채널 정보 가져오기
        channel_id = os.getenv("CHANNEL_ID", "UCEtPneQeO1IE08MndfjzndQ")
        response = youtube.channels().list(
            part="snippet,statistics",
            id=channel_id
        ).execute()
        
        if response.get("items"):
            channel = response["items"][0]
            snippet = channel["snippet"]
            stats = channel["statistics"]
            
            print(f"✅ 채널명: {snippet['title']}")
            print(f"✅ 구독자 수: {stats.get('subscriberCount', 'N/A')}")
            print(f"✅ 총 조회수: {stats.get('viewCount', 'N/A')}")
            print(f"✅ 총 동영상 수: {stats.get('videoCount', 'N/A')}")
        else:
            print("❌ 채널을 찾을 수 없습니다")
            return False
            
    except Exception as e:
        print(f"❌ YouTube API 테스트 실패: {e}")
        return False
    
    return True

def test_sheets_api(sheets):
    """Google Sheets API 테스트"""
    print("\n📊 Google Sheets API 테스트 중...")
    
    try:
        spreadsheet_id = os.getenv("SPREADSHEET_ID", "17Z6bewPmkp00RHpBKymyMaFj4CvqD_QjAPzagmlkCP8")
        sheet_name = os.getenv("SHEET_NAME", "유튜브_월간분석")
        
        # 시트 정보 가져오기
        response = sheets.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()
        
        print(f"✅ 스프레드시트 제목: {response['properties']['title']}")
        
        # 시트 존재 확인
        sheets_list = [sheet['properties']['title'] for sheet in response['sheets']]
        if sheet_name in sheets_list:
            print(f"✅ 시트 '{sheet_name}' 존재 확인")
        else:
            print(f"⚠️  시트 '{sheet_name}'이 없습니다. 다음 시트들이 있습니다:")
            for sheet in sheets_list:
                print(f"   - {sheet}")
        
    except Exception as e:
        print(f"❌ Google Sheets API 테스트 실패: {e}")
        return False
    
    return True

def test_analytics_api(yta):
    """YouTube Analytics API 테스트"""
    print("\n📈 YouTube Analytics API 테스트 중...")
    
    try:
        channel_id = os.getenv("CHANNEL_ID", "UCEtPneQeO1IE08MndfjzndQ")
        
        # 최근 7일 데이터 가져오기
        from datetime import datetime, timedelta
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=7)
        
        response = yta.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start_date.isoformat(),
            endDate=end_date.isoformat(),
            metrics="views,subscribersGained"
        ).execute()
        
        if response.get("rows"):
            views, subs = response["rows"][0]
            print(f"✅ 최근 7일 조회수: {views}")
            print(f"✅ 최근 7일 구독자 증가: {subs}")
        else:
            print("⚠️  최근 7일 데이터가 없습니다")
        
    except Exception as e:
        print(f"❌ YouTube Analytics API 테스트 실패: {e}")
        return False
    
    return True

def main():
    print("🧪 YouTube Analytics 로컬 테스트")
    print("=" * 50)
    
    # 환경변수 설정
    if not os.getenv("CHANNEL_ID"):
        print("💡 CHANNEL_ID 환경변수가 설정되지 않았습니다. 기본값을 사용합니다.")
    
    if not os.getenv("SPREADSHEET_ID"):
        print("💡 SPREADSHEET_ID 환경변수가 설정되지 않았습니다. 기본값을 사용합니다.")
    
    # 인증 테스트
    youtube, yta, sheets = test_authentication()
    if not youtube:
        return
    
    # 각 API 테스트
    test_youtube_api(youtube)
    test_sheets_api(sheets)
    test_analytics_api(yta)
    
    print("\n🎉 모든 테스트가 완료되었습니다!")
    print("\n다음 단계:")
    print("1. 모든 테스트가 성공했다면 deploy.sh를 실행하세요")
    print("2. 실패한 테스트가 있다면 해당 권한을 확인하세요")

if __name__ == "__main__":
    main()
