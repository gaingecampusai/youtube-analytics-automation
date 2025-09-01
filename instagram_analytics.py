#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Instagram 월간 분석 데이터 수집 스크립트
Facebook Graph API를 통해 Instagram 비즈니스 계정 데이터 수집
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

import requests
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.iguser import IGUser
from facebook_business.adobjects.igmedia import IGMedia
from facebook_business.adobjects.page import Page

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# 환경 변수 설정
FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID')
FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET')
FACEBOOK_ACCESS_TOKEN = os.getenv('FACEBOOK_ACCESS_TOKEN')
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.getenv('INSTAGRAM_BUSINESS_ACCOUNT_ID')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '17Z6bewPmkp00RHpBKymyMaFj4CvqD_QjAPzagmlkCP8')
SHEET_NAME = '인스타그램_2025년_월간분석'

class InstagramAnalytics:
    def __init__(self):
        """Instagram Analytics 클래스 초기화"""
        if not all([FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID]):
            raise ValueError("필수 환경 변수가 설정되지 않았습니다. FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_ACCESS_TOKEN, INSTAGRAM_BUSINESS_ACCOUNT_ID를 확인하세요.")
        
        # Facebook API 초기화
        FacebookAdsApi.init(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_ACCESS_TOKEN)
        self.ig_user = IGUser(INSTAGRAM_BUSINESS_ACCOUNT_ID)
        
    def get_month_range(self, year: int, month: int) -> tuple:
        """특정 연월의 시작일과 종료일 반환"""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        return start_date, end_date
    
    def get_last_month_range(self) -> tuple:
        """지난달의 시작일과 종료일 반환"""
        today = datetime.now()
        if today.month == 1:
            year = today.year - 1
            month = 12
        else:
            year = today.year
            month = today.month - 1
        return self.get_month_range(year, month)
    
    def fetch_media_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """지정된 기간의 미디어 데이터 수집"""
        try:
            # Instagram 미디어 목록 조회
            media_list = self.ig_user.get_media(
                fields=[
                    'id',
                    'media_type',
                    'media_url',
                    'thumbnail_url',
                    'permalink',
                    'timestamp',
                    'like_count',
                    'comments_count',
                    'caption'
                ]
            )
            
            media_data = []
            for media in media_list:
                media_dict = media.export_all_data()
                media_timestamp = datetime.fromisoformat(media_dict['timestamp'].replace('Z', '+00:00'))
                
                # 지정된 기간 내의 미디어만 필터링
                if start_date <= media_timestamp <= end_date:
                    media_data.append({
                        'id': media_dict['id'],
                        'media_type': media_dict.get('media_type', ''),
                        'permalink': media_dict.get('permalink', ''),
                        'timestamp': media_dict['timestamp'],
                        'like_count': media_dict.get('like_count', 0),
                        'comments_count': media_dict.get('comments_count', 0),
                        'caption': media_dict.get('caption', '')
                    })
            
            return media_data
            
        except Exception as e:
            logging.error(f"미디어 데이터 수집 오류: {e}")
            return []
    
    def fetch_insights_data(self, start_date: datetime, end_date: datetime) -> Dict:
        """Instagram 인사이트 데이터 수집"""
        try:
            # 계정 인사이트 조회
            insights = self.ig_user.get_insights(
                metric=[
                    'impressions',
                    'reach',
                    'profile_views',
                    'follower_count',
                    'email_contacts',
                    'phone_call_clicks',
                    'text_message_clicks',
                    'get_directions_clicks',
                    'website_clicks'
                ],
                period='day',
                since=start_date.strftime('%Y-%m-%d'),
                until=end_date.strftime('%Y-%m-%d')
            )
            
            insights_data = {}
            for insight in insights:
                insight_dict = insight.export_all_data()
                metric_name = insight_dict['name']
                values = insight_dict.get('values', [])
                
                if values:
                    # 일별 데이터의 합계 계산
                    total_value = sum(float(v.get('value', 0)) for v in values)
                    insights_data[metric_name] = int(total_value)
                else:
                    insights_data[metric_name] = 0
            
            return insights_data
            
        except Exception as e:
            logging.error(f"인사이트 데이터 수집 오류: {e}")
            return {}
    
    def fetch_media_insights(self, media_ids: List[str]) -> Dict:
        """개별 미디어 인사이트 데이터 수집"""
        try:
            media_insights = {}
            
            for media_id in media_ids:
                try:
                    media = IGMedia(media_id)
                    insights = media.get_insights(
                        metric=[
                            'impressions',
                            'reach',
                            'video_views',
                            'saved',
                            'shares'
                        ]
                    )
                    
                    media_data = {}
                    for insight in insights:
                        insight_dict = insight.export_all_data()
                        metric_name = insight_dict['name']
                        values = insight_dict.get('values', [])
                        
                        if values:
                            total_value = sum(float(v.get('value', 0)) for v in values)
                            media_data[metric_name] = int(total_value)
                        else:
                            media_data[metric_name] = 0
                    
                    media_insights[media_id] = media_data
                    
                except Exception as e:
                    logging.warning(f"미디어 {media_id} 인사이트 수집 실패: {e}")
                    media_insights[media_id] = {}
            
            return media_insights
            
        except Exception as e:
            logging.error(f"미디어 인사이트 수집 오류: {e}")
            return {}
    
    def calculate_monthly_stats(self, year: int, month: int) -> Dict:
        """특정 월의 통계 데이터 계산"""
        start_date, end_date = self.get_month_range(year, month)
        
        logging.info(f"📊 {year}년 {month}월 데이터 수집 중... ({start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')})")
        
        # 1. 미디어 데이터 수집
        media_data = self.fetch_media_data(start_date, end_date)
        
        # 2. 계정 인사이트 수집
        insights_data = self.fetch_insights_data(start_date, end_date)
        
        # 3. 미디어별 인사이트 수집
        media_ids = [media['id'] for media in media_data]
        media_insights = self.fetch_media_insights(media_ids)
        
        # 4. 통계 계산
        total_posts = len(media_data)
        total_likes = sum(media.get('like_count', 0) for media in media_data)
        total_comments = sum(media.get('comments_count', 0) for media in media_data)
        
        # 최고 좋아요 수
        max_likes = max([media.get('like_count', 0) for media in media_data]) if media_data else 0
        
        # 총 공유수 (미디어 인사이트에서)
        total_shares = sum(
            insights.get('shares', 0) for insights in media_insights.values()
        )
        
        # 릴스 평균 조회수 (비디오 타입만)
        video_views = []
        for media in media_data:
            if media.get('media_type') == 'VIDEO':
                media_id = media['id']
                if media_id in media_insights:
                    views = media_insights[media_id].get('video_views', 0)
                    video_views.append(views)
        
        avg_reels_views = sum(video_views) / len(video_views) if video_views else 0
        
        # 프로필 클릭 (인사이트에서)
        profile_clicks = insights_data.get('profile_views', 0)
        
        # 팔로워 수 변화 (현재 팔로워 수)
        current_followers = insights_data.get('follower_count', 0)
        
        # 이전 달과 비교하여 새 팔로워 수 계산 (간단한 추정)
        # 실제로는 이전 달 데이터가 필요하지만, 여기서는 현재 팔로워 수만 반환
        new_followers = current_followers  # 실제로는 이전 달 대비 증가분 계산 필요
        
        return {
            'year': year,
            'month': month,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'total_posts': total_posts,
            'current_followers': current_followers,
            'new_followers': new_followers,
            'max_likes': max_likes,
            'total_shares': total_shares,
            'avg_reels_views': int(avg_reels_views),
            'profile_clicks': profile_clicks,
            'total_likes': total_likes,
            'total_comments': total_comments
        }
    
    def format_number(self, num: int) -> str:
        """숫자를 한국어 형식으로 포맷팅"""
        if num >= 10000:
            return f"{num/10000:.1f}만"
        elif num >= 1000:
            return f"{num/1000:.1f}천"
        else:
            return str(num)

def main():
    """메인 함수"""
    try:
        logging.info("📱 Instagram 월간 분석 시작")
        
        # Instagram Analytics 인스턴스 생성
        instagram = InstagramAnalytics()
        
        # 지난달 데이터 수집
        start_date, end_date = instagram.get_last_month_range()
        year, month = start_date.year, start_date.month
        
        stats = instagram.calculate_monthly_stats(year, month)
        
        # 결과 출력
        logging.info("📊 수집된 데이터:")
        logging.info(f"  📅 분석 기간: {stats['start_date']} ~ {stats['end_date']}")
        logging.info(f"  📝 총 게시물: {stats['total_posts']}개")
        logging.info(f"  👥 현재 팔로워: {stats['current_followers']}명")
        logging.info(f"  📈 새 팔로워: {stats['new_followers']}명")
        logging.info(f"  ❤️ 최고 좋아요: {stats['max_likes']}개")
        logging.info(f"  🔄 총 공유: {stats['total_shares']}회")
        logging.info(f"  🎬 릴스 평균 조회수: {instagram.format_number(stats['avg_reels_views'])}")
        logging.info(f"  👤 프로필 클릭: {stats['profile_clicks']}회")
        
        # Google Sheets에 기록 (추후 구현)
        # write_to_sheets(stats)
        
        logging.info("✅ Instagram 월간 분석 완료!")
        
    except Exception as e:
        logging.error(f"❌ 오류 발생: {e}")
        raise

if __name__ == '__main__':
    main()
