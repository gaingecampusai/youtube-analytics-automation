#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram 월간 분석 보고서 생성 및 Google Sheets 기록
Facebook Graph API + Google Sheets API 연동
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

from instagram_analytics import InstagramAnalytics

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# 환경 변수 설정
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '17Z6bewPmkp00RHpBKymyMaFj4CvqD_QjAPzagmlkCP8')
SHEET_NAME = '인스타그램_2025년_월간분석'

# Google Sheets OAuth 설정
SHEETS_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
BASE_DIR = os.getenv('BASE_DIR', os.getcwd())
CLIENT_SECRET_FILE = os.getenv('CLIENT_SECRET_FILE', os.path.join(BASE_DIR, 'secrets/client_secret.json'))
TOKEN_SHEETS = os.getenv('TOKEN_SHEETS', os.path.join(BASE_DIR, 'secrets/token_sheets.json'))

class InstagramMonthlyReport:
    def __init__(self):
        """Instagram 월간 보고서 클래스 초기화"""
        self.instagram = InstagramAnalytics()
        self.sheets_client = self._get_sheets_client()
        
    def _get_sheets_client(self) -> gspread.Client:
        """Google Sheets 클라이언트 생성"""
        creds = None
        
        # 토큰 파일이 있으면 로드
        if os.path.exists(TOKEN_SHEETS):
            creds = Credentials.from_authorized_user_file(TOKEN_SHEETS, SHEETS_SCOPES)
        
        # 토큰이 없거나 만료되었으면 새로 생성
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SHEETS_SCOPES)
                creds = flow.run_local_server(port=8082)
            
            # 토큰 저장
            with open(TOKEN_SHEETS, 'w') as token:
                token.write(creds.to_json())
        
        return gspread.authorize(creds)
    
    def find_or_create_month_column(self, month_label: str) -> int:
        """월 라벨에 해당하는 열 인덱스 찾기 또는 생성"""
        try:
            sheet = self.sheets_client.open_by_key(SPREADSHEET_ID)
            worksheet = sheet.worksheet(SHEET_NAME)
            
            # 3행에서 월 라벨 찾기
            row3 = worksheet.row_values(3)
            
            for idx, value in enumerate(row3, start=1):
                if value and value.strip() == month_label:
                    return idx
            
            # 월 라벨이 없으면 새 열에 추가
            next_col = len(row3) + 1
            col_letter = self._col_to_letter(next_col)
            worksheet.update(f'{col_letter}3', month_label)
            return next_col
            
        except Exception as e:
            logging.error(f"월 열 찾기/생성 오류: {e}")
            return 3  # 기본값
    
    def _col_to_letter(self, col_idx: int) -> str:
        """열 인덱스를 A1 표기법으로 변환"""
        result = ""
        while col_idx > 0:
            col_idx, remainder = divmod(col_idx - 1, 26)
            result = chr(65 + remainder) + result
        return result
    
    def write_monthly_data(self, stats: Dict):
        """월간 데이터를 Google Sheets에 기록"""
        try:
            month_label = f"{stats['month']}월"
            col_idx = self.find_or_create_month_column(month_label)
            col_letter = self._col_to_letter(col_idx)
            
            sheet = self.sheets_client.open_by_key(SPREADSHEET_ID)
            worksheet = sheet.worksheet(SHEET_NAME)
            
            # 데이터 준비 (4행부터 시작)
            data = [
                [f"{stats['start_date']} ~ {stats['end_date']}"],  # 4행: 분석 기간
                [stats['total_posts']],                           # 5행: 총 게시물 업로드 수
                [stats['current_followers']],                     # 6행: 현재 팔로워 수
                [stats['new_followers']],                         # 7행: 새 팔로워 수(전달대비)
                [stats['max_likes']],                             # 8행: 좋아요 최고 수
                [stats['total_shares']],                          # 9행: 총 공유수
                [self.instagram.format_number(stats['avg_reels_views'])],  # 10행: 릴스 평균 조회수
                [stats['profile_clicks']],                        # 11행: 프로필 클릭
            ]
            
            # 데이터 기록
            start_row = 4
            for i, row_data in enumerate(data):
                row = start_row + i
                worksheet.update(f'{col_letter}{row}', row_data)
            
            logging.info(f"✅ {month_label} 데이터 기록 완료")
            
        except Exception as e:
            logging.error(f"Google Sheets 기록 오류: {e}")
            raise
    
    def create_sheet_if_not_exists(self):
        """시트가 없으면 생성"""
        try:
            sheet = self.sheets_client.open_by_key(SPREADSHEET_ID)
            
            # 시트 존재 여부 확인
            try:
                worksheet = sheet.worksheet(SHEET_NAME)
                logging.info(f"✅ 시트 '{SHEET_NAME}' 이미 존재")
                return worksheet
            except:
                # 시트가 없으면 생성
                worksheet = sheet.add_worksheet(title=SHEET_NAME, rows=20, cols=10)
                
                # 헤더 설정
                headers = [
                    ['항목', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월'],
                    ['', '', '', '', '', '', '', '', ''],
                    ['', '', '', '', '', '', '', '', '']
                ]
                
                # 행별 항목 설정
                row_items = [
                    '분석 기간',
                    '총 게시물 업로드 수',
                    '현재 팔로워 수',
                    '새 팔로워 수(전달대비)',
                    '좋아요 최고 수',
                    '총 공유수',
                    '릴스 평균 조회수',
                    '프로필 클릭'
                ]
                
                # 헤더 기록
                worksheet.update('A1:I3', headers)
                
                # 항목 기록
                for i, item in enumerate(row_items, 4):
                    worksheet.update(f'A{i}', item)
                
                logging.info(f"✅ 새 시트 '{SHEET_NAME}' 생성 완료")
                return worksheet
                
        except Exception as e:
            logging.error(f"시트 생성 오류: {e}")
            raise
    
    def run_monthly_report(self, year: int = None, month: int = None):
        """월간 보고서 실행"""
        try:
            logging.info("📱 Instagram 월간 보고서 시작")
            
            # 시트 준비
            self.create_sheet_if_not_exists()
            
            # 분석할 연월 결정
            if year is None or month is None:
                start_date, end_date = self.instagram.get_last_month_range()
                year, month = start_date.year, start_date.month
            
            logging.info(f"📊 {year}년 {month}월 데이터 분석 중...")
            
            # 데이터 수집
            stats = self.instagram.calculate_monthly_stats(year, month)
            
            # Google Sheets에 기록
            self.write_monthly_data(stats)
            
            # 결과 출력
            logging.info("📊 분석 결과:")
            logging.info(f"  📅 분석 기간: {stats['start_date']} ~ {stats['end_date']}")
            logging.info(f"  📝 총 게시물: {stats['total_posts']}개")
            logging.info(f"  👥 현재 팔로워: {stats['current_followers']}명")
            logging.info(f"  📈 새 팔로워: {stats['new_followers']}명")
            logging.info(f"  ❤️ 최고 좋아요: {stats['max_likes']}개")
            logging.info(f"  🔄 총 공유: {stats['total_shares']}회")
            logging.info(f"  🎬 릴스 평균 조회수: {self.instagram.format_number(stats['avg_reels_views'])}")
            logging.info(f"  👤 프로필 클릭: {stats['profile_clicks']}회")
            
            logging.info("✅ Instagram 월간 보고서 완료!")
            
        except Exception as e:
            logging.error(f"❌ 월간 보고서 오류: {e}")
            raise

def main():
    """메인 함수"""
    try:
        # Instagram 월간 보고서 실행
        report = InstagramMonthlyReport()
        report.run_monthly_report()
        
    except Exception as e:
        logging.error(f"❌ 메인 함수 오류: {e}")
        raise

if __name__ == '__main__':
    main()
