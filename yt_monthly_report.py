# /workspace/yt_analytics_job.py
# -*- coding: utf-8 -*-
"""
YouTube(브랜드 채널) 지난달 요약을 수집해 Google Sheets에 기록하는 배치 잡.
- 기본: 단일 OAuth 토큰(YouTube+Sheets)
- 옵션: 토큰 이원화(YouTube/Sheets) 또는 Sheets만 서비스계정 사용
- Cloud Run Job(비대화형)에서 동작하도록 환경변수/시크릿 대응
- 4행부터 기록, 지난달 기록 후 '전월' 4행이 비어있으면 자동 보충
"""

import os
import json
import logging
import datetime as dt
from dateutil.relativedelta import relativedelta
import isodate

from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ──────────────────────────────────────────────────────────────────────────────
# 환경/설정
# ──────────────────────────────────────────────────────────────────────────────

def env_bool(name: str, default: bool = False) -> bool:
    return str(os.getenv(name, str(default))).lower() in ("1", "true", "yes", "y")

# 기본 경로 (로컬/클라우드 모두 커버)
BASE_DIR = os.getenv("BASE_DIR", "/workspace")

# 필수 파라미터 (필요 시 환경변수로 오버라이드)
CHANNEL_ID     = os.getenv("CHANNEL_ID", "UCEtPneQeO1IE08MndfjzndQ")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "17Z6bewPmkp00RHpBKymyMaFj4CvqD_QjAPzagmlkCP8")
SHEET_NAME     = os.getenv("SHEET_NAME", "유튜브_월간분석")

# 인증 파일/토큰 경로 (Secret Manager로 마운트 권장)
CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE", os.path.join(BASE_DIR, "client_secret.json"))
TOKEN_SINGLE  = os.getenv("TOKEN_SINGLE",  os.path.join(BASE_DIR, "token.json"))
TOKEN_YOUTUBE = os.getenv("TOKEN_YOUTUBE", os.path.join(BASE_DIR, "token_youtube.json"))
TOKEN_SHEETS  = os.getenv("TOKEN_SHEETS",  os.path.join(BASE_DIR, "token_sheets.json"))
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")  # Sheets 전용 서비스계정 키(선택)

# 모드 스위치
USE_DUAL_TOKENS = env_bool("USE_DUAL_TOKENS", True)                  # 유튜브/시트 토큰 분리 (기본값을 True로 변경)
USE_SERVICE_ACCOUNT_FOR_SHEETS = env_bool("USE_SA_FOR_SHEETS", False)  # 시트만 서비스계정
NON_INTERACTIVE = env_bool("NON_INTERACTIVE", True)                   # Cloud Run에선 True

# OAuth 포트(로컬에서만 사용)
OAUTH_PORT_YT = int(os.getenv("OAUTH_PORT_YT", "8081"))
OAUTH_PORT_SH = int(os.getenv("OAUTH_PORT_SH", "8081"))  # 두 플로우 같은 포트 권장

# 스코프
SCOPES_YOUTUBE = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]
SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]
SCOPES_SINGLE = SCOPES_YOUTUBE + SCOPES_SHEETS

# 시트 기록 시작행(4로 고정)
START_ROW = 4

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ──────────────────────────────────────────────────────────────────────────────
# 인증
# ──────────────────────────────────────────────────────────────────────────────

def get_oauth_credentials(token_path: str, scopes: list, port: int) -> Credentials:
    """사람 계정 OAuth 토큰 발급/갱신. NON_INTERACTIVE=True면 브라우저 플로우 금지."""
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)
        logging.info(f"Found token: {token_path}")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info("Refreshing expired token...")
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        else:
            if NON_INTERACTIVE:
                raise RuntimeError(
                    f"Missing/invalid token at {token_path} in NON_INTERACTIVE mode. "
                    "Generate token locally, then mount via secrets."
                )
            logging.info("Starting OAuth browser flow...")
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes)
            creds = flow.run_local_server(port=port, access_type="offline", prompt="consent")
            with open(token_path, "w") as f:
                f.write(creds.to_json())
    return creds

def build_services():
    """YouTube/Analytics + Sheets 서비스 생성 (토큰 이원화/서비스계정 옵션 지원)"""
    # YouTube/Analytics
    if USE_DUAL_TOKENS:
        yt_creds = get_oauth_credentials(TOKEN_YOUTUBE, SCOPES_YOUTUBE, OAUTH_PORT_YT)
    else:
        yt_creds = get_oauth_credentials(TOKEN_SINGLE, SCOPES_SINGLE, OAUTH_PORT_YT)

    youtube = build("youtube", "v3", credentials=yt_creds)
    yta = build("youtubeAnalytics", "v2", credentials=yt_creds)

    # Sheets
    if USE_SERVICE_ACCOUNT_FOR_SHEETS and SERVICE_ACCOUNT_FILE:
        sh_creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES_SHEETS
        )
        logging.info("Using Service Account for Sheets.")
    elif USE_DUAL_TOKENS:
        sh_creds = get_oauth_credentials(TOKEN_SHEETS, SCOPES_SHEETS, OAUTH_PORT_SH)
    else:
        sh_creds = yt_creds

    sheets = build("sheets", "v4", credentials=sh_creds)
    return youtube, yta, sheets

# ──────────────────────────────────────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────────────────────────────────────

def parse_duration_seconds(iso_duration: str) -> int:
    try:
        return int(isodate.parse_duration(iso_duration).total_seconds())
    except Exception:
        return 0

def col_to_a1(col_idx: int) -> str:
    s = ""
    while col_idx:
        col_idx, r = divmod(col_idx - 1, 26)
        s = chr(65 + r) + s
    return s

def get_last_month_range():
    today = dt.date.today()
    first_day_this_month = today.replace(day=1)
    last_day_prev = first_day_this_month - dt.timedelta(days=1)
    first_day_prev = last_day_prev.replace(day=1)
    return first_day_prev.isoformat(), last_day_prev.isoformat(), last_day_prev.year, last_day_prev.month

def get_month_range(year: int, month: int):
    start = dt.date(year, month, 1)
    if month == 12:
        next_first = dt.date(year + 1, 1, 1)
    else:
        next_first = dt.date(year, month + 1, 1)
    end = next_first - dt.timedelta(days=1)
    return start.isoformat(), end.isoformat()

# ──────────────────────────────────────────────────────────────────────────────
# 데이터 수집
# ──────────────────────────────────────────────────────────────────────────────

def fetch_month_stats(youtube, yta, channel_id, year: int, month: int):
    start_date, end_date = get_month_range(year, month)

    # 업로드된 신규 영상 목록
    uploads = youtube.search().list(
        part="id",
        channelId=channel_id,
        publishedAfter=start_date + "T00:00:00Z",
        publishedBefore=end_date + "T23:59:59Z",
        type="video",
        maxResults=50
    ).execute()
    video_ids = [it["id"]["videoId"] for it in uploads.get("items", [])]

    shorts = longs = 0
    title_map = {}
    if video_ids:
        vd = youtube.videos().list(part="contentDetails,snippet", id=",".join(video_ids)).execute()
        for v in vd.get("items", []):
            secs = parse_duration_seconds(v["contentDetails"]["duration"])
            shorts += 1 if secs <= 60 else 0
            longs  += 1 if secs > 60 else 0
            title_map[v["id"]] = v["snippet"]["title"]

    # 집계 메트릭
    res = yta.reports().query(
        ids=f"channel=={channel_id}",
        startDate=start_date,
        endDate=end_date,
        metrics="views,subscribersGained,subscribersLost,likes,comments,shares"
    ).execute()
    row = res.get("rows", [[0,0,0,0,0,0]])[0]
    total_views, subs_gained, subs_lost, likes, comments, shares = row

    # 현재 총 구독자수
    ch = youtube.channels().list(part="statistics", id=channel_id).execute()
    subscriber_count = int(ch["items"][0]["statistics"]["subscriberCount"])

    # 주요 시청자 (연령/성별 최대 비중)
    aud = yta.reports().query(
        ids=f"channel=={channel_id}",
        startDate=start_date,
        endDate=end_date,
        metrics="viewerPercentage",
        dimensions="ageGroup,gender"
    ).execute()
    audience_rows = aud.get("rows", [])
    top_audience_label = ""
    if audience_rows:
        best = max(audience_rows, key=lambda r: float(r[2]))
        age, gender, _ = best
        age_label = age.replace("age", "").replace("-", "–")
        gender_label = "남성" if gender == "male" else "여성"
        top_audience_label = f"{age_label}세 {gender_label}"

    # 신규영상 중 최대 조회수
    max_video_title, max_views = "", 0
    if video_ids:
        vv = yta.reports().query(
            ids=f"channel=={channel_id}",
            startDate=start_date,
            endDate=end_date,
            metrics="views",
            dimensions="video",
            filters=f"video=={','.join(video_ids)}"
        ).execute()
        for r in vv.get("rows", []):
            vid, v = r[0], int(r[1])
            if v > max_views:
                max_views = v
                max_video_title = title_map.get(vid, vid)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "month": month,
        "shorts": int(shorts),
        "longs": int(longs),
        "total_views": int(total_views),
        "subs_net": int(subs_gained) - int(subs_lost),
        "subs_total": int(subscriber_count),
        "likes": int(likes),
        "comments": int(comments),
        "shares": int(shares),
        "top_audience": top_audience_label,
        "max_video_title": max_video_title,
        "max_video_views": int(max_views),
    }

# ──────────────────────────────────────────────────────────────────────────────
# Sheets
# ──────────────────────────────────────────────────────────────────────────────

def find_or_create_month_column(sheets, month_label: str) -> int:
    rng = f"{SHEET_NAME}!1:3"
    vals = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range=rng
    ).execute().get("values", [])
    row3 = vals[2] if len(vals) >= 3 else []

    for idx, v in enumerate(row3, start=1):
        if v and v.strip() == month_label:
            return idx

    current_cols = max((len(r) for r in vals), default=1)
    target_col = current_cols + 1
    a1 = col_to_a1(target_col)
    sheets.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!{a1}3",
        valueInputOption="USER_ENTERED",
        body={"values": [[month_label]]}
    ).execute()
    return target_col

def write_month_summary_to_sheet(sheets, summary: dict):
    month_label = f"{summary['month']}월"
    col = find_or_create_month_column(sheets, month_label)
    colA1 = col_to_a1(col)

    values = [
        [f"{summary['start_date']} ~ {summary['end_date']}"],  # row 4
        [summary["shorts"]],                                   # row 5
        [summary["longs"]],                                    # row 6
        [summary["total_views"]],                              # row 7
        [summary["subs_net"]],                                 # row 8
        [summary["subs_total"]],                               # row 9
        [summary["top_audience"] or ""],                       # row10
        [summary["likes"]],                                    # row11
        [summary["comments"]],                                 # row12
        [summary["shares"]],                                   # row13
        [summary["max_video_title"] or ""],                    # row14
        [summary["max_video_views"]],                          # row15
    ]

    start_row = START_ROW
    end_row = start_row + len(values) - 1
    rng = f"{SHEET_NAME}!{colA1}{start_row}:{colA1}{end_row}"

    sheets.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=rng,
        valueInputOption="USER_ENTERED",
        body={"values": values}
    ).execute()

def is_month_column_empty(sheets, month_label: str) -> bool:
    col_idx = find_or_create_month_column(sheets, month_label)
    colA1 = col_to_a1(col_idx)
    resp = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!{colA1}{START_ROW}"  # 4행 분석 기간
    ).execute()
    vals = resp.get("values", [])
    return not vals or not vals[0] or (len(vals[0]) == 0) or (str(vals[0][0]).strip() == "")

# ──────────────────────────────────────────────────────────────────────────────
# 메인 플로우
# ──────────────────────────────────────────────────────────────────────────────

def main():
    youtube, yta, sheets = build_services()

    # 1) 지난달 집계/기록
    start, end, y, m = get_last_month_range()
    logging.info(f"Target (지난달): {y}-{m:02d} {start} ~ {end}")
    summary_last = fetch_month_stats(youtube, yta, CHANNEL_ID, y, m)
    write_month_summary_to_sheet(sheets, summary_last)
    print("✅ 지난달 기록 완료:", f"{summary_last['month']}월", summary_last["start_date"], "~", summary_last["end_date"])

    # 2) 전월이 비어있으면 자동 보충
    if m == 1:
        prev_y, prev_m = y - 1, 12
    else:
        prev_y, prev_m = y, m - 1
    prev_label = f"{prev_m}월"

    if is_month_column_empty(sheets, prev_label):
        logging.info(f"{prev_label} 4행(분석 기간)이 비어있어 자동 보충")
        summary_prev = fetch_month_stats(youtube, yta, CHANNEL_ID, prev_y, prev_m)
        write_month_summary_to_sheet(sheets, summary_prev)
        print("✅ 전월 보충 완료:", f"{summary_prev['month']}월", summary_prev["start_date"], "~", summary_prev["end_date"])
    else:
        logging.info(f"{prev_label} 컬럼은 이미 값이 있어 보충 생략")

if __name__ == "__main__":
    try:
        main()
    except HttpError as e:
        logging.exception("Google API HttpError")
        raise
    except Exception:
        logging.exception("Unhandled error")
        raise