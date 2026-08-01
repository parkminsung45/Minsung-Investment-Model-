"""
전역 설정 파일.
API 키는 .env 파일에서 불러온다 (.env.example 참고).
"""
import os
from dotenv import load_dotenv

load_dotenv()

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# 분석 대상 티커 (자유롭게 수정)
TICKERS = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]

# 결과 저장 경로
OUTPUT_DIR = "output"

# 신호 결합 가중치: NEWS_WEIGHT + ANALYST_WEIGHT = 1 이어야 함
NEWS_WEIGHT = 0.5
ANALYST_WEIGHT = 0.5

# Alpha Vantage 무료 티어는 분당 호출 제한이 있어 티커 간 대기 시간(초) 필요
NEWS_FETCH_DELAY_SEC = 12.0
