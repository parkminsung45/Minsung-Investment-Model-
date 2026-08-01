"""
Alpha Vantage NEWS_SENTIMENT API를 사용해 티커별 뉴스와 감성 점수를 가져온다.
문서: https://www.alphavantage.co/documentation/#news-sentiment
무료 API 키 발급: https://www.alphavantage.co/support/#api-key
"""
import time
from typing import List, Dict

import requests

BASE_URL = "https://www.alphavantage.co/query"


def fetch_news_sentiment(ticker: str, api_key: str, limit: int = 50) -> List[Dict]:
    """
    특정 티커에 대한 최신 뉴스 기사와 감성 점수를 가져온다.

    반환되는 기사 딕셔너리 필드:
        - title, url, time_published, source
        - overall_sentiment_score: 기사 전체 감성 (-1 ~ 1)
        - ticker_sentiment_score: 해당 티커에 대한 감성 (-1 ~ 1)
        - relevance_score: 해당 티커와의 관련도 (0 ~ 1)
    """
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": ticker,
        "apikey": api_key,
        "limit": limit,
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    if "feed" not in data:
        # API 한도 초과, 잘못된 키 등으로 빈 응답이 올 수 있음
        return []

    articles = []
    for item in data["feed"]:
        ticker_sentiment_score = 0.0
        relevance_score = 0.0
        for ts in item.get("ticker_sentiment", []):
            if ts.get("ticker") == ticker:
                ticker_sentiment_score = float(ts.get("ticker_sentiment_score", 0.0))
                relevance_score = float(ts.get("relevance_score", 0.0))
                break

        articles.append({
            "ticker": ticker,
            "title": item.get("title"),
            "url": item.get("url"),
            "time_published": item.get("time_published"),
            "source": item.get("source"),
            "overall_sentiment_score": float(item.get("overall_sentiment_score", 0.0)),
            "ticker_sentiment_score": ticker_sentiment_score,
            "relevance_score": relevance_score,
        })

    return articles


def fetch_news_for_universe(
    tickers: List[str], api_key: str, delay: float = 12.0
) -> Dict[str, List[Dict]]:
    """
    여러 티커에 대해 순차적으로 뉴스를 가져온다.
    무료 티어는 분당 호출 제한이 있어 delay(초)만큼 대기한다.
    """
    result = {}
    for i, ticker in enumerate(tickers):
        result[ticker] = fetch_news_sentiment(ticker, api_key)
        if i < len(tickers) - 1:
            time.sleep(delay)
    return result
