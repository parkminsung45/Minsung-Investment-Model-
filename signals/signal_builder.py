"""
뉴스 감성 + 애널리스트 컨센서스를 하나의 종목별 시그널로 결합한다.
"""
from typing import Dict, List


def aggregate_news_score(articles: List[Dict]) -> float:
    """
    한 티커의 기사 리스트를 relevance_score로 가중평균하여
    하나의 뉴스 감성 점수로 요약한다.
    관련도가 낮은 기사(단순 언급 수준)가 점수를 왜곡하지 않도록
    가중치로 반영한다.

        NewsScore = sum(r_i * s_i) / sum(r_i)
    """
    if not articles:
        return 0.0

    weighted_sum = 0.0
    weight_total = 0.0
    for a in articles:
        w = max(a.get("relevance_score", 0.0), 0.01)  # 0으로 나누기 방지
        weighted_sum += a.get("ticker_sentiment_score", 0.0) * w
        weight_total += w

    return weighted_sum / weight_total if weight_total > 0 else 0.0


def build_signal(
    ticker: str,
    news_score: float,
    analyst_score: float,
    news_weight: float = 0.5,
    analyst_weight: float = 0.5,
) -> Dict:
    """
    두 점수를 가중합하여 최종 시그널을 만든다.

        S = news_weight * news_score + analyst_weight * analyst_score
    """
    combined = news_weight * news_score + analyst_weight * analyst_score
    return {
        "ticker": ticker,
        "news_score": round(news_score, 4),
        "analyst_score": round(analyst_score, 4),
        "combined_score": round(combined, 4),
    }
