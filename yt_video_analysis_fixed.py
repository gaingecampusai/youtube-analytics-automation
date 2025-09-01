#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube 영상별 분석 스크립트 (개선 버전)
- 롱폼/숏폼 분리 기록
- 배치 조회로 속도/쿼터 효율 개선
- 시트는 한번에 업데이트
- (옵션) YouTube Analytics 평균 시청시간/시청비율 추가
"""

import os
import re
import datetime as dt
from datetime import datetime
from typing import List, Dict, Any

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import gspread

# ========================
# 설정
# ========================
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.readonly']
SHEETS_SCOPES  = ['https://www.googleapis.com/auth/spreadsheets']
# (선택) YouTube Analytics 사용 시 주석 해제
USE_YT_ANALYTICS = True
YT_ANALYTICS_SCOPES = ['https://www.googleapis.com/auth/yt-analytics.readonly']

CHANNEL_ID = os.getenv('CHANNEL_ID', 'UCEtPneQeO1IE08MndfjzndQ')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '17Z6bewPmkp00RHpBKymyMaFj4CvqD_QjAPzagmlkCP8')
LONGFORM_SHEET_NAME = '유튜브_영상별분석(롱폼)'
SHORTFORM_SHEET_NAME = '유튜브_영상별분석(숏폼)'

BASE_DIR = os.getenv('BASE_DIR', os.getcwd())
CLIENT_SECRET_FILE = os.getenv('CLIENT_SECRET_FILE', os.path.join(BASE_DIR, 'secrets/client_secret.json'))
TOKEN_YOUTUBE  = os.getenv('TOKEN_YOUTUBE',  os.path.join(BASE_DIR, 'secrets/token_youtube.json'))
TOKEN_SHEETS   = os.getenv('TOKEN_SHEETS',   os.path.join(BASE_DIR, 'secrets/token_sheets.json'))
TOKEN_YTANALYT = os.getenv('TOKEN_YTANALYT', os.path.join(BASE_DIR, 'secrets/token_ytanalytics.json'))

# ========================
# 공통: OAuth
# ========================
def load_installed_app_creds(token_path: str, client_secret_path: str, scopes: List[str], local_port: int) -> Credentials:
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, scopes)
            # 포트 충돌 방지를 위해 포트 인자 분리
            creds = flow.run_local_server(port=local_port)
        with open(token_path, 'w') as f:
            f.write(creds.to_json())
    return creds

def get_youtube_client() -> Any:
    yt_creds = load_installed_app_creds(TOKEN_YOUTUBE, CLIENT_SECRET_FILE, YOUTUBE_SCOPES, local_port=8081)
    return build('youtube', 'v3', credentials=yt_creds), yt_creds

def get_sheets_client() -> gspread.Client:
    sheets_creds = load_installed_app_creds(TOKEN_SHEETS, CLIENT_SECRET_FILE, SHEETS_SCOPES, local_port=8082)
    return gspread.authorize(sheets_creds)

def get_yt_analytics_client() -> Any:
    # YouTube Analytics는 YouTube와 같은 토큰 사용 (yt_monthly_report_test.py 참고)
    yt_analyt_creds = load_installed_app_creds(TOKEN_YOUTUBE, CLIENT_SECRET_FILE, YOUTUBE_SCOPES + YT_ANALYTICS_SCOPES, local_port=8081)
    return build('youtubeAnalytics', 'v2', credentials=yt_analyt_creds)

# ========================
# YouTube 데이터 수집
# ========================
DUR_RE_H = re.compile(r'(\d+)H')
DUR_RE_M = re.compile(r'(\d+)M')
DUR_RE_S = re.compile(r'(\d+)S')

def parse_duration_to_seconds(iso_dur: str) -> int:
    """ISO 8601 duration (e.g., PT2H37M15S) → seconds"""
    if not iso_dur or not iso_dur.startswith('PT'):
        return 0
    total = 0
    h = DUR_RE_H.search(iso_dur)
    m = DUR_RE_M.search(iso_dur)
    s = DUR_RE_S.search(iso_dur)
    if h: total += int(h.group(1)) * 3600
    if m: total += int(m.group(1)) * 60
    if s: total += int(s.group(1))
    return total

def fetch_uploads_playlist_id(youtube, channel_id: str) -> str:
    resp = youtube.channels().list(part='contentDetails', id=channel_id).execute()
    items = resp.get('items', [])
    if not items:
        raise ValueError(f'채널을 찾을 수 없습니다: {channel_id}')
    return items[0]['contentDetails']['relatedPlaylists']['uploads']

def fetch_all_playlist_video_ids(youtube, playlist_id: str, max_videos: int = 50) -> List[str]:
    """업로드 재생목록에서 최신 영상 ID들을 가져오기 (최대 max_videos개)"""
    ids = []
    req = youtube.playlistItems().list(
        part='contentDetails',
        playlistId=playlist_id,
        maxResults=50
    )
    while req and len(ids) < max_videos:
        resp = req.execute()
        for it in resp.get('items', []):
            if len(ids) >= max_videos:
                break
            vid = it['contentDetails']['videoId']
            ids.append(vid)
        req = youtube.playlistItems().list_next(req, resp)
    return ids

def chunked(iterable: List[str], size: int):
    for i in range(0, len(iterable), size):
        yield iterable[i:i+size]

def fetch_videos_meta(youtube, video_ids: List[str]) -> List[Dict[str, Any]]:
    """videos().list를 배치로 호출하여 메타/통계를 수집"""
    out = []
    for batch in chunked(video_ids, 50):
        resp = youtube.videos().list(
            part='snippet,statistics,contentDetails',
            id=','.join(batch),
            maxResults=50
        ).execute()
        for v in resp.get('items', []):
            sn = v.get('snippet', {})
            st = v.get('statistics', {})
            cd = v.get('contentDetails', {})
            dur = cd.get('duration', 'PT0S')
            sec = parse_duration_to_seconds(dur)
            is_short = sec <= 60  # Shorts 휴리스틱

            out.append({
                'id': v.get('id'),
                'title': sn.get('title', ''),
                'upload_date': (sn.get('publishedAt', '')[:10] or ''),
                'views': int(st.get('viewCount', 0) or 0),
                'likes': int(st.get('likeCount', 0) or 0),
                'comments': int(st.get('commentCount', 0) or 0),
                'duration': dur,
                'duration_seconds': sec,
                'is_short': is_short,
                'url': f"https://www.youtube.com/watch?v={v.get('id')}"
            })
    return out

# ========================
# (선택) YouTube Analytics
# ========================
def fetch_yt_analytics_for_videos(yt_analytics, video_ids: List[str]) -> Dict[str, Dict[str, float]]:
    """
    각 비디오별로 평균 시청시간(초), 평균 시청 비율(%)을 조회
    - yt_monthly_report_test.py 스타일로 구현
    """
    results = {}
    
    # 배치로 처리 (50개씩)
    for batch in chunked(video_ids, 50):
        try:
            # 최근 30일 데이터로 조회 (더 안정적)
            end_date = datetime.utcnow().date()
            start_date = end_date - dt.timedelta(days=30)
            
            resp = yt_analytics.reports().query(
                ids=f'channel=={CHANNEL_ID}',
                startDate=start_date.isoformat(),
                endDate=end_date.isoformat(),
                metrics='averageViewDuration,averageViewPercentage',
                dimensions='video',
                filters=f'video=={",".join(batch)}'
            ).execute()
            
            rows = resp.get('rows', [])
            for row in rows:
                vid, avg_dur, avg_pct = row
                results[vid] = {
                    'avg_view_duration': float(avg_dur or 0.0),
                    'avg_view_percentage': float(avg_pct or 0.0),
                }
            
            # 데이터가 없는 비디오는 0으로 설정
            for vid in batch:
                if vid not in results:
                    results[vid] = {'avg_view_duration': 0.0, 'avg_view_percentage': 0.0}
                    
        except HttpError as e:
            print(f"Analytics API 오류 (배치): {e}")
            # 실패한 배치는 모두 0으로 설정
            for vid in batch:
                results[vid] = {'avg_view_duration': 0.0, 'avg_view_percentage': 0.0}
    
    return results

# ========================
# Sheets 기록
# ========================
LONG_HEADERS = [
    'No', 'videoId', '영상 제목', '업로드일', '조회수', '좋아요', '댓글',
    '시청 유지율(%)', '평균 시청시간(초)', '길이(초)', 'Shorts 여부', '영상 링크', '비고'
]

def build_sheet_rows(videos: List[Dict[str, Any]], analytics: Dict[str, Dict[str, float]] = None) -> List[List[Any]]:
    rows = []
    for i, v in enumerate(videos, 1):
        vid = v['id']
        avg_pct = ''
        avg_dur = ''
        if analytics is not None and vid in analytics:
            avg_pct = round(analytics[vid].get('avg_view_percentage', 0.0), 2)
            avg_dur = round(analytics[vid].get('avg_view_duration', 0.0), 2)
        rows.append([
            i,
            vid,
            v['title'],
            v['upload_date'],
            v['views'],
            v['likes'],
            v['comments'],
            avg_pct,            # 시청 유지율(%)
            avg_dur,            # 평균 시청시간(초)
            v['duration_seconds'],
            'Y' if v['is_short'] else 'N',
            v['url'],
            ''                  # 비고
        ])
    return rows

def write_sheet(gc: gspread.Client, sheet_name: str, headers: List[str], rows: List[List[Any]]):
    sh = gc.open_by_key(SPREADSHEET_ID)
    try:
        ws = sh.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=sheet_name, rows=1000, cols=len(headers))

    # 전체 지우고 헤더+데이터 한번에 업데이트 (빠름)
    ws.clear()
    values = [headers] + rows
    ws.update('A1', values, value_input_option='RAW')

# ========================
# 메인
# ========================
def main():
    print("🎬 YouTube 영상별 분석 시작")
    print(f"📊 채널 ID: {CHANNEL_ID}")
    print(f"📝 스프레드시트 ID: {SPREADSHEET_ID}")

    try:
        # 클라이언트 준비
        print("🔐 YouTube 인증 중...")
        youtube, yt_creds = get_youtube_client()

        print("📹 업로드 재생목록 조회...")
        uploads_pid = fetch_uploads_playlist_id(youtube, CHANNEL_ID)

        print("📹 영상 ID 수집 중... (최신 100개)")
        video_ids = fetch_all_playlist_video_ids(youtube, uploads_pid, max_videos=100)
        if not video_ids:
            print("❌ 업로드된 영상을 찾을 수 없습니다.")
            return
        print(f"✅ 총 {len(video_ids)}개 영상 ID 수집")

        print("📦 메타/통계 배치 조회 중...")
        videos = fetch_videos_meta(youtube, video_ids)

        # 롱폼/숏폼 분리 후 TOP 20개씩만 선택
        long_videos  = [v for v in videos if not v['is_short']]
        short_videos = [v for v in videos if v['is_short']]
        
        # 조회수 기준으로 정렬하여 TOP 20개 선택
        long_videos.sort(key=lambda x: x['views'], reverse=True)
        short_videos.sort(key=lambda x: x['views'], reverse=True)
        
        long_videos = long_videos[:20]
        short_videos = short_videos[:20]
        
        print(f"📏 롱폼 TOP {len(long_videos)}개, 숏폼 TOP {len(short_videos)}개")

        # (선택) YouTube Analytics
        analytics_map = None
        if USE_YT_ANALYTICS:
            print("📈 YouTube Analytics 인증/조회 중...")
            yt_analytics = get_yt_analytics_client()
            # TOP 20개 영상만 Analytics 조회
            top_video_ids = [v['id'] for v in long_videos + short_videos]
            analytics_map = fetch_yt_analytics_for_videos(yt_analytics, top_video_ids)

        # 시트 기록
        print("📊 Google Sheets 인증 중...")
        gc = get_sheets_client()

        print("📝 시트에 쓰는 중 (일괄 업데이트)...")
        long_rows  = build_sheet_rows(long_videos, analytics_map)
        short_rows = build_sheet_rows(short_videos, analytics_map)

        write_sheet(gc, LONGFORM_SHEET_NAME,  LONG_HEADERS, long_rows)
        write_sheet(gc, SHORTFORM_SHEET_NAME, LONG_HEADERS, short_rows)

        print("🎉 영상별 분석 완료!")

    except HttpError as e:
        print(f"❌ YouTube API 오류: {e}")
    except Exception as e:
        print(f"❌ 일반 오류: {e}")

if __name__ == '__main__':
    main()