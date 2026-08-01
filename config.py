"""
전역 설정 파일.
API 키는 .env 파일에서 불러온다 (.env.example 참고).
"""
import os
from dotenv import load_dotenv

load_dotenv()

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")

# 토스증권 Open API (실거래 연동, 샌드박스 없음 - broker/orders.py 참고)
TOSS_CLIENT_ID = os.getenv("TOSS_CLIENT_ID", "")
TOSS_CLIENT_SECRET = os.getenv("TOSS_CLIENT_SECRET", "")

# 반드시 명시적으로 "true"를 설정해야 실제 주문이 나간다. 기본값은 항상 드라이런.
TOSS_LIVE_TRADING = os.getenv("TOSS_LIVE_TRADING", "false").strip().lower() == "true"

# 뉴스+애널리스트 결합 시그널(main.py)을 계산할 소수 관심종목.
# Alpha Vantage 무료 티어(하루 25회)로 감당 가능한 규모로 유지할 것.
WATCHLIST = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"]

# 결과 저장 경로
OUTPUT_DIR = "output"

# 신호 결합 가중치: NEWS_WEIGHT + ANALYST_WEIGHT = 1 이어야 함
NEWS_WEIGHT = 0.5
ANALYST_WEIGHT = 0.5

# Alpha Vantage 무료 티어는 분당 호출 제한이 있어 티커 간 대기 시간(초) 필요
NEWS_FETCH_DELAY_SEC = 12.0

# scan_universe.py: S&P500+NASDAQ100 전체 스캔 시 Finnhub 호출 간 대기시간(초).
# 무료 티어 분당 60회 한도에 대응.
FINNHUB_UNIVERSE_DELAY_SEC = 1.0
