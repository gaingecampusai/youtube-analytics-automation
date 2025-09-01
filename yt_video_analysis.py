#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 영상별 분석 스크립트
롱폼과 숏폼 영상의 상세 정보를 Google Sheets에 기록
"""

import os
import json
import datetime
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# OAuth 스코프
SCOPES = [
    'https://www.googleapis.com/auth/youtube.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]

# 환경변수 설정
CHANNEL_ID = os.getenv('CHANNEL_ID', 'UCEtPneQeO1IE08MndfjzndQ')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '17Z6bewPmkp00RHpBKymyMaFj4CvqD_QjAPzagmlkCP8')
LONGFORM_SHEET_NAME = '유튜브_영상별분석(롱폼)'
SHORTFORM_SHEET_NAME = '유튜브_영상별분석(숏폼)'

# 파일 경로 설정
BASE_DIR = os.getenv('BASE_DIR', os.getcwd())
CLIENT_SECRET_FILE = os.getenv('CLIENT_SECRET_FILE', os.path.join(BASE_DIR, 'secrets/client_secret.json'))
TOKEN_YOUTUBE = os.getenv('TOKEN_YOUTUBE', os.path.join(BASE_DIR, 'secrets/token_youtube.json'))
TOKEN_SHEETS = os.getenv('TOKEN_SHEETS', os.path.join(BASE_DIR, 'secrets/token_sheets.json'))

def get_credentials():
    """OAuth 인증 정보 가져오기"""
    creds = None
    
    # YouTube 토큰 파일이 있으면 로드
    if os.path.exists(TOKEN_YOUTUBE):
        creds = Credentials.from_authorized_user_file(TOKEN_YOUTUBE, SCOPES)
    
    # 토큰이 없거나 만료되었으면 새로 생성
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=8081)
        
        # 토큰 저장
        with open(TOKEN_YOUTUBE, 'w') as token:
            token.write(creds.to_json())
    
    return creds

def get_sheets_credentials():
    """Google Sheets 인증 정보 가져오기"""
    creds = None
    
    # Sheets 토큰 파일이 있으면 로드
    if os.path.exists(TOKEN_SHEETS):
        creds = Credentials.from_authorized_user_file(TOKEN_SHEETS, SCOPES)
    
    # 토큰이 없거나 만료되었으면 새로 생성
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=8082)
        
        # 토큰 저장
        with open(TOKEN_SHEETS, 'w') as token:
            token.write(creds.to_json())
    
    return creds

def get_videos(youtube, channel_id, max_results=50):
    """채널의 모든 영상 가져오기"""
    videos = []
    
    try:
        # 채널의 업로드 재생목록 ID 가져오기
        request = youtube.channels().list(
            part='contentDetails',
            id=channel_id
        )
        response = request.execute()
        
        if not response['items']:
            print(f"채널을 찾을 수 없습니다: {channel_id}")
            return videos
        
        uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # 업로드 재생목록에서 영상들 가져오기
        request = youtube.playlistItems().list(
            part='snippet,contentDetails',
            playlistId=uploads_playlist_id,
            maxResults=max_results
        )
        
        while request:
            response = request.execute()
            
            for item in response['items']:
                video_id = item['contentDetails']['videoId']
                snippet = item['snippet']
                
                # 영상 상세 정보 가져오기
                video_request = youtube.videos().list(
                    part='snippet,statistics,contentDetails',
                    id=video_id
                )
                video_response = video_request.execute()
                
                if video_response['items']:
                    video_info = video_response['items'][0]
                    video_snippet = video_info['snippet']
                    video_stats = video_info['statistics']
                    video_content = video_info['contentDetails']
                    
                    # 영상 길이로 롱폼/숏폼 구분
                    duration = video_content['duration']
                    is_short = duration.startswith('PT') and 'M' not in duration and int(duration.replace('PT', '').replace('S', '')) <= 60
                    
                    video_data = {
                        'id': video_id,
                        'title': video_snippet['title'],
                        'upload_date': video_snippet['publishedAt'][:10],
                        'views': int(video_stats.get('viewCount', 0)),
                        'likes': int(video_stats.get('likeCount', 0)),
                        'comments': int(video_stats.get('commentCount', 0)),
                        'duration': duration,
                        'is_short': is_short
                    }
                    
                    videos.append(video_data)
            
            # 다음 페이지가 있으면 계속
            request = youtube.playlistItems().list_next(request, response)
    
    except HttpError as e:
        print(f"YouTube API 오류: {e}")
    
    return videos

def write_to_sheets(sheets_creds, videos):
    """Google Sheets에 데이터 기록"""
    try:
        # Google Sheets 클라이언트 생성
        gc = gspread.authorize(sheets_creds)
        sheet = gc.open_by_key(SPREADSHEET_ID)
        
        # 롱폼과 숏폼 영상 분리
        longform_videos = [v for v in videos if not v['is_short']]
        shortform_videos = [v for v in videos if v['is_short']]
        
        # 롱폼 영상 기록
        if longform_videos:
            try:
                longform_worksheet = sheet.worksheet(LONGFORM_SHEET_NAME)
            except:
                longform_worksheet = sheet.add_worksheet(title=LONGFORM_SHEET_NAME, rows=1000, cols=10)
                # 헤더 추가
                longform_worksheet.append_row(['No', '영상 제목', '업로드일', '조회수', '좋아요', '댓글', '시청 유지율(%)', '비고'])
            
            # 기존 데이터 삭제 (헤더 제외)
            if longform_worksheet.row_count > 1:
                longform_worksheet.delete_rows(2, longform_worksheet.row_count)
            
            # 새 데이터 추가
            for i, video in enumerate(longform_videos, 1):
                row = [
                    i,
                    video['title'],
                    video['upload_date'],
                    video['views'],
                    video['likes'],
                    video['comments'],
                    '',  # 시청 유지율 (API로는 가져올 수 없음)
                    ''   # 비고
                ]
                longform_worksheet.append_row(row)
            
            print(f"롱폼 영상 {len(longform_videos)}개 기록 완료")
        
        # 숏폼 영상 기록
        if shortform_videos:
            try:
                shortform_worksheet = sheet.worksheet(SHORTFORM_SHEET_NAME)
            except:
                shortform_worksheet = sheet.add_worksheet(title=SHORTFORM_SHEET_NAME, rows=1000, cols=10)
                # 헤더 추가
                shortform_worksheet.append_row(['No', '영상 제목', '업로드일', '조회수', '좋아요', '댓글', '시청 유지율(%)', '비고'])
            
            # 기존 데이터 삭제 (헤더 제외)
            if shortform_worksheet.row_count > 1:
                shortform_worksheet.delete_rows(2, shortform_worksheet.row_count)
            
            # 새 데이터 추가
            for i, video in enumerate(shortform_videos, 1):
                row = [
                    i,
                    video['title'],
                    video['upload_date'],
                    video['views'],
                    video['likes'],
                    video['comments'],
                    '',  # 시청 유지율 (API로는 가져올 수 없음)
                    ''   # 비고
                ]
                shortform_worksheet.append_row(row)
            
            print(f"숏폼 영상 {len(shortform_videos)}개 기록 완료")
    
    except Exception as e:
        print(f"Google Sheets 오류: {e}")

def main():
    """메인 함수"""
    print("🎬 YouTube 영상별 분석 시작")
    print(f"📊 채널 ID: {CHANNEL_ID}")
    print(f"📝 스프레드시트 ID: {SPREADSHEET_ID}")
    
    try:
        # YouTube API 클라이언트 생성
        youtube_creds = get_credentials()
        youtube = build('youtube', 'v3', credentials=youtube_creds)
        
        # 영상 데이터 가져오기
        print("📹 영상 정보 수집 중...")
        videos = get_videos(youtube, CHANNEL_ID)
        
        if not videos:
            print("❌ 영상을 찾을 수 없습니다.")
            return
        
        print(f"✅ 총 {len(videos)}개 영상 발견")
        
        # Google Sheets에 기록
        print("📊 Google Sheets에 기록 중...")
        sheets_creds = get_sheets_credentials()
        write_to_sheets(sheets_creds, videos)
        
        print("🎉 영상별 분석 완료!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == '__main__':
    main()
