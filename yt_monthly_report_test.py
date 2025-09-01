# /Users/adam/Documents/dev/program/channel_analytics/ty_test.py
# -*- coding: utf-8 -*-

"""
YouTube Analytics (브랜드 채널) + Google Sheets 기록 스크립트 (지난달 요약)
- 기본: 단일 토큰(OAuth 한 번)로 YouTube/Sheets 모두 접근
- 옵션: USE_DUAL_TOKENS=True 로 두 개 토큰을 분리(유튜브용/시트용) 가능

시트 구조(고정 행):
  3행: 월 헤더(예: "8월")
  5행: 분석 기간 (YYYY-MM-DD ~ YYYY-MM-DD)
  6행: 총 숏폼영상 업로드 수
  7행: 총 롱폼영상 업로드 수
  8행: 총 조회수
  9행: 총 구독자 증가수(순증)
  10행: 현재 총 구독자수
  11행: 주요 시청자 구분 (예: "35–44세 남성")
  12행: 총 좋아요 수
  13행: 총 댓글 수
  14행: 총 공유 수
  15행: 최대조회수 신규영상 (제목)
  16행: 신규영상 최대 조회수 (숫자)
"""

import os, sys
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
# 🔧 사용자 환경 설정
# ──────────────────────────────────────────────────────────────────────────────
CHANNEL_ID = "UCEtPneQeO1IE08MndfjzndQ"   # 브랜드 채널 ID
CLIENT_SECRET_FILE = "/Users/adam/Documents/dev/keys/client_secret_838571130307-4el8inhvj5ikqd0jncjac49tieslqklv.apps.googleusercontent.com.json"

BASE_DIR = "/Users/adam/Documents/dev/program/channel_analytics" if os.getenv("ENV","local")=="local" else "/workspace"
os.makedirs(BASE_DIR, exist_ok=True)

CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE", CLIENT_SECRET_FILE)
TOKEN_SINGLE  = os.getenv("TOKEN_SINGLE",  TOKEN_SINGLE)
TOKEN_YOUTUBE = os.getenv("TOKEN_YOUTUBE", TOKEN_YOUTUBE)
TOKEN_SHEETS  = os.getenv("TOKEN_SHEETS",  TOKEN_SHEETS)

NON_INTERACTIVE = os.getenv("NON_INTERACTIVE", "false").lower() == "true"  # Cloud Run 에서 true 설정

# 스프레드시트
SPREADSHEET_ID = "17Z6bewPmkp00RHpBKymyMaFj4CvqD_QjAPzagmlkCP8"
SHEET_NAME = "유튜브_월간분석"

# 기록 시작 행
START_ROW = 4

# 리디렉션 URI는 Cloud Console에 등록되어 있어야 함 (예: http://localhost:8081/, 8082/)
OAUTH_PORT_YT = 8081     # 유튜브용 OAuth 콜백 포트
OAUTH_PORT_SH = 8081     # (이원화 사용 시) 시트용 OAuth 콜백 포트

# 토큰 파일 (단일/이원화 둘 다 지원)
# TOKEN_SINGLE = os.path.join(BASE_DIR, "token.json")
TOKEN_YOUTUBE = os.path.join(BASE_DIR, "token_youtube.json")
TOKEN_SHEETS = os.path.join(BASE_DIR, "token_sheets.json")

# 서비스 계정(선택) — Sheets만 서비스 계정으로 쓰고 싶을 때 경로 지정
SERVICE_ACCOUNT_FILE = None  # 예: "/Users/adam/Documents/dev/keys/service_account.json"

# 모드 스위치
USE_DUAL_TOKENS = True      # True: 유튜브/시트 토큰 분리, False: 단일 토큰
USE_SERVICE_ACCOUNT_FOR_SHEETS = False  # True: Sheets는 서비스계정으로 접근

# 스코프
SCOPES_YOUTUBE = [
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
]
SCOPES_SHEETS = ["https://www.googleapis.com/auth/spreadsheets"]
SCOPES_SINGLE = SCOPES_YOUTUBE + SCOPES_SHEETS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)


# ──────────────────────────────────────────────────────────────────────────────
# 🔐 인증 유틸
# ──────────────────────────────────────────────────────────────────────────────
def get_oauth_credentials(token_path: str, scopes: list, port: int) -> Credentials:
    """비대화형 모드에서는 브라우저 인증을 시도하지 않는다."""
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as f: f.write(creds.to_json())
        else:
            if NON_INTERACTIVE:
                raise RuntimeError(
                    f"Missing/invalid token at {token_path} in NON_INTERACTIVE mode. "
                    "Generate token locally and mount via Secret Manager."
                )
            # 로컬에서만 브라우저 플로우 허용
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes)
            creds = flow.run_local_server(port=port, access_type="offline", prompt="consent")
            with open(token_path, "w") as f: f.write(creds.to_json())
    return creds


def build_services():
    """
    YouTube/Analytics + Sheets 서비스 객체 생성
    - USE_DUAL_TOKENS: 토큰 분리
    - USE_SERVICE_ACCOUNT_FOR_SHEETS: 시트는 서비스계정 사용
    """
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
        # 단일 토큰 재사용
        sh_creds = yt_creds

    sheets = build("sheets", "v4", credentials=sh_creds)
    return youtube, yta, sheets, yt_creds, sh_creds


# ──────────────────────────────────────────────────────────────────────────────
# 🔎 보조 유틸
# ──────────────────────────────────────────────────────────────────────────────
def debug_print_scopes(creds, title="Granted scopes"):
    print(f"🔎 {title}:")
    for s in sorted(getattr(creds, "scopes", []) or []):
        print(" -", s)

def verify_sheets_access(sheets, spreadsheet_id, sheet_name=SHEET_NAME):
    try:
        resp = sheets.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1:C3"
        ).execute()
        print("✅ Sheets 접근 OK, preview:", resp.get("values", []))
    except Exception as e:
        print("❌ Sheets 접근 실패:", e)
        print("대처 체크리스트:")
        print(" 1) SCOPES에 spreadsheets 포함?")
        print(" 2) 올바른 계정/서비스계정에 문서 편집권한 공유?")
        print(" 3) Cloud Console에서 Google Sheets API 활성?")
        raise

def parse_duration_seconds(iso_duration: str) -> int:
    try:
        return int(isodate.parse_duration(iso_duration).total_seconds())
    except Exception:
        return 0

def col_to_a1(col_idx: int) -> str:
    # 1 -> A, 2 -> B ...
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
    return first_day_prev.isoformat(), last_day_prev.isoformat(), last_day_prev.month


# ──────────────────────────────────────────────────────────────────────────────
# 📊 데이터 수집
# ──────────────────────────────────────────────────────────────────────────────
def check_selected_channel(youtube):
    resp = youtube.channels().list(part="id,snippet", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        return None, None
    ch = items[0]
    return ch["id"], ch["snippet"].get("title")


def fetch_last_month_stats(youtube, yta, channel_id):
    start_date, end_date, target_month = get_last_month_range()

    # 1) 지난달 업로드 목록
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
        vd = youtube.videos().list(
            part="contentDetails,snippet",
            id=",".join(video_ids)
        ).execute()
        for v in vd.get("items", []):
            dur = v["contentDetails"]["duration"]
            secs = parse_duration_seconds(dur)
            if secs <= 60:
                shorts += 1
            else:
                longs += 1
            title_map[v["id"]] = v["snippet"]["title"]

    # 2) 집계 메트릭 (조회/구독/좋아요/댓글/공유)
    res = yta.reports().query(
        ids=f"channel=={channel_id}",
        startDate=start_date,
        endDate=end_date,
        metrics="views,subscribersGained,subscribersLost,likes,comments,shares"
    ).execute()
    row = res["rows"][0] if res.get("rows") else [0, 0, 0, 0, 0, 0]
    total_views, subs_gained, subs_lost, likes, comments, shares = row

    # 3) 현재 총 구독자수
    ch = youtube.channels().list(part="statistics", id=channel_id).execute()
    subscriber_count = ch["items"][0]["statistics"]["subscriberCount"]

    # 4) 주요 시청자 구분 (연령/성별 비중 Top1)
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
        best = max(audience_rows, key=lambda r: float(r[2]))   # [ageGroup, gender, pct]
        age, gender, pct = best
        age_label = age.replace("age", "").replace("-", "–")
        gender_label = "남성" if gender == "male" else "여성"
        top_audience_label = f"{age_label}세 {gender_label}"

    # 5) 지난달 신규 영상 중 최대 조회수
    max_video_id, max_views = None, 0
    max_video_title = ""
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
                max_video_id = vid
        if max_video_id:
            max_video_title = title_map.get(max_video_id, max_video_id)

    return {
        "start_date": start_date,
        "end_date": end_date,
        "month": target_month,
        "shorts": shorts,
        "longs": longs,
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
# 🧾 Sheets 쓰기
# ──────────────────────────────────────────────────────────────────────────────
def find_or_create_month_column(sheets, month_label: str):
    """
    월 라벨은 시트의 '3행'에 있다고 가정합니다.
    - 존재하면 그 열 인덱스를 반환
    - 없으면 가장 오른쪽 다음 열에 라벨을 쓰고 그 열을 반환
    """
    rng = f"{SHEET_NAME}!1:3"
    vals = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=rng
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


def write_month_summary_to_sheet(sheets, summary):
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

# === 추가: 특정 연-월의 시작/끝일 계산 ===
def get_month_range(year: int, month: int):
    start = dt.date(year, month, 1)
    # 다음달 1일 - 1일
    if month == 12:
        next_first = dt.date(year + 1, 1, 1)
    else:
        next_first = dt.date(year, month + 1, 1)
    end = next_first - dt.timedelta(days=1)
    return start.isoformat(), end.isoformat()

# === 추가: 임의의 월을 받아 집계하는 범용 함수 ===
def fetch_month_stats(youtube, yta, channel_id, year: int, month: int):
    start_date, end_date = get_month_range(year, month)
    target_month = month

    # 1) 지난달 업로드 목록
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
        vd = youtube.videos().list(
            part="contentDetails,snippet",
            id=",".join(video_ids)
        ).execute()
        for v in vd.get("items", []):
            secs = parse_duration_seconds(v["contentDetails"]["duration"])
            shorts += 1 if secs <= 60 else 0
            longs  += 1 if secs > 60 else 0
            title_map[v["id"]] = v["snippet"]["title"]

    # 2) 집계 메트릭
    res = yta.reports().query(
        ids=f"channel=={channel_id}",
        startDate=start_date,
        endDate=end_date,
        metrics="views,subscribersGained,subscribersLost,likes,comments,shares"
    ).execute()
    row = res["rows"][0] if res.get("rows") else [0,0,0,0,0,0]
    total_views, subs_gained, subs_lost, likes, comments, shares = row

    # 3) 현재 구독자수
    ch = youtube.channels().list(part="statistics", id=channel_id).execute()
    subscriber_count = ch["items"][0]["statistics"]["subscriberCount"]

    # 4) 주요 시청자
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

    # 5) 신규영상 최대 조회수
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
        "month": target_month,
        "shorts": shorts,
        "longs": longs,
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

# === 추가: 특정 월 컬럼의 4행(분석 기간) 비어있는지 확인 ===
def is_month_column_empty(sheets, month_label: str) -> bool:
    col_idx = find_or_create_month_column(sheets, month_label)  # 헤더 없으면 생성
    colA1 = col_to_a1(col_idx)
    # 4행 분석기간 확인
    resp = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"{SHEET_NAME}!{colA1}4"
    ).execute()
    vals = resp.get("values", [])
    return not vals or not vals[0] or (len(vals[0]) == 0) or (str(vals[0][0]).strip() == "")


# ──────────────────────────────────────────────────────────────────────────────
# 🧪 테스트(최근 7일 로그) & 메인
# ──────────────────────────────────────────────────────────────────────────────
def run_last7days_smoketest(youtube, yta):
    authed_channel_id, authed_channel_title = check_selected_channel(youtube)
    logging.info("Authenticated Channel (mine=True)")
    logging.info(f"ID:   {authed_channel_id}")
    logging.info(f"Name: {authed_channel_title}")

    if authed_channel_id and authed_channel_id != CHANNEL_ID:
        logging.warning(f"OAuth selected channel != target brand channel ({authed_channel_id} != {CHANNEL_ID})")

    today = dt.date.today()
    start_date = (today - relativedelta(days=7)).isoformat()
    end_date = (today - relativedelta(days=1)).isoformat()

    query_params = {
        "ids": f"channel=={CHANNEL_ID}",
        "startDate": start_date,
        "endDate": end_date,
        "metrics": "views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost",
        "dimensions": "day",
        "sort": "day",
    }
    logging.info(f"Query: {json.dumps(query_params)}")

    try:
        result = yta.reports().query(**query_params).execute()
        headers = [h["name"] for h in result.get("columnHeaders", [])]
        rows = result.get("rows", [])
        logging.info("=== YouTube Analytics Result ===")
        if not rows:
            logging.info("No data rows. Check period/channel/permissions.")
        else:
            print("\t".join(headers), flush=True)
            for r in rows:
                print("\t".join(str(x) for x in r), flush=True)
            h_index = {name: idx for idx, name in enumerate(headers)}
            total_views = sum(int(r[h_index["views"]]) for r in rows)
            total_minutes = sum(float(r[h_index["estimatedMinutesWatched"]]) for r in rows)
            subs_gained = sum(int(r[h_index["subscribersGained"]]) for r in rows)
            subs_lost = sum(int(r[h_index["subscribersLost"]]) for r in rows)
            print("\n=== Summary (최근 7일) ===")
            print(f"조회수 합계: {total_views:,}")
            print(f"시청시간 합계(분): {total_minutes:,.2f}")
            print(f"구독자 증감: +{subs_gained} / -{subs_lost} (순변화 {subs_gained - subs_lost})")
    except HttpError:
        logging.exception("API HttpError during smoketest")


def main():
    youtube, yta, sheets, yt_creds, sh_creds = build_services()

    # 필요 시 디버그
    # debug_print_scopes(yt_creds, "YouTube token scopes")
    # debug_print_scopes(sh_creds, "Sheets token scopes")
    # verify_sheets_access(sheets, SPREADSHEET_ID, SHEET_NAME)

    # 1) 지난달 집계 & 기록
    last_start, last_end, last_month = get_last_month_range()
    summary_last = fetch_month_stats(
        youtube, yta, CHANNEL_ID,
        year=dt.date.today().year, month=last_month
    )
    write_month_summary_to_sheet(sheets, summary_last)
    print("✅ 지난달 기록 완료:", f"{summary_last['month']}월", summary_last["start_date"], "~", summary_last["end_date"])

    # 2) 지난달의 “바로 전 달”이 비어 있으면 자동 보충
    prev_month = 12 if last_month == 1 else last_month - 1
    prev_year = dt.date.today().year - 1 if last_month == 1 else dt.date.today().year
    prev_label = f"{prev_month}월"

    if is_month_column_empty(sheets, prev_label):
        print(f"ℹ️ {prev_label} 컬럼의 4행(분석 기간)이 비어있어 자동 보충합니다.")
        summary_prev = fetch_month_stats(
            youtube, yta, CHANNEL_ID,
            year=prev_year, month=prev_month
        )
        write_month_summary_to_sheet(sheets, summary_prev)
        print("✅ 전월 보충 완료:", f"{summary_prev['month']}월", summary_prev["start_date"], "~", summary_prev["end_date"])
    else:
        print(f"👍 {prev_label} 컬럼은 이미 값이 있어 보충 생략합니다.")


if __name__ == "__main__":
    main()