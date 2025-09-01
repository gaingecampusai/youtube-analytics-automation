FROM python:3.11-slim

WORKDIR /workspace

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 보고서 스크립트를 컨테이너로 복사
COPY yt_monthly_report.py .

ENV ENV=cloud
ENV NON_INTERACTIVE=true
ENV CLIENT_SECRET_FILE=/secrets/client_secret.json
ENV TOKEN_YOUTUBE=/secrets/token_youtube.json
ENV TOKEN_SHEETS=/secrets/token_sheets.json
ENV USE_DUAL_TOKENS=true

# 컨테이너 실행 시 자동으로 보고서 실행
CMD ["python", "yt_monthly_report.py"]