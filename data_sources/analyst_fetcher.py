"""
Finnhub API를 사용해 애널리스트 컨센서스 데이터를 가져온다.

주의: 실제 애널리스트 리포트 원문(PDF)은 대부분 유료/기관 전용이라
공개 API로는 접근할 수 없다. 대신 다음 두 공개 데이터를
'애널리스트 시그널'의 근거로 사용한다:
    1. Recommendation Trends: 최근 매수/보유/매도 추천 건수
    2. Price Target: 평균/최고/최저 목표주가

문서: https://finnhub.io/docs/api
무료 API 키 발급: https://finnhub.io/register
"""
from typing import Dict

import requests

BASE_URL = "https://finnhub.io/api/v1"


def fetch_recommendation_trends(ticker: str, api_key: str) -> Dict:
    resp = requests.get(
        f"{BASE_URL}/stock/recommendation",
        params={"symbol": ticker, "token": api_key},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return {}
    latest = data[0]  # 가장 최근 월 데이터
    return {
        "period": latest.get("period"),
        "strong_buy": latest.get("strongBuy", 0),
        "buy": latest.get("buy", 0),
        "hold": latest.get("hold", 0),
        "sell": latest.get("sell", 0),
        "strong_sell": latest.get("strongSell", 0),
    }


def fetch_price_target(ticker: str, api_key: str) -> Dict:
    """
    무료 티어 API 키는 이 엔드포인트에서 403(Forbidden)을 반환한다
    (Finnhub Price Target은 프리미엄 전용). 이 경우 빈 dict를 반환해
    전체 파이프라인이 멈추지 않도록 한다.
    """
    resp = requests.get(
        f"{BASE_URL}/stock/price-target",
        params={"symbol": ticker, "token": api_key},
        timeout=15,
    )
    if resp.status_code == 403:
        return {}
    resp.raise_for_status()
    data = resp.json()
    return {
        "target_high": data.get("targetHigh"),
        "target_low": data.get("targetLow"),
        "target_mean": data.get("targetMean"),
        "target_median": data.get("targetMedian"),
        "last_updated": data.get("lastUpdated"),
    }


def recommendation_to_score(rec: Dict) -> float:
    """
    추천등급 분포를 -1(강한 매도) ~ +1(강한 매수) 사이 점수로 변환한다.

    가중치: strong_buy=+2, buy=+1, hold=0, sell=-1, strong_sell=-2
    이후 (2 * 전체 건수)로 나누어 [-1, 1] 범위로 정규화한다.
    """
    if not rec:
        return 0.0

    weights = {
        "strong_buy": 2, "buy": 1, "hold": 0,
        "sell": -1, "strong_sell": -2,
    }
    total_count = sum(rec.get(k, 0) for k in weights)
    if total_count == 0:
        return 0.0

    weighted_sum = sum(rec.get(k, 0) * w for k, w in weights.items())
    return weighted_sum / (2 * total_count)
