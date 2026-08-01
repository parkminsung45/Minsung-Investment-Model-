import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from signals.signal_builder import aggregate_news_score, build_signal
from data_sources.analyst_fetcher import recommendation_to_score


def test_aggregate_news_score_weighted_average():
    articles = [
        {"ticker_sentiment_score": 0.8, "relevance_score": 1.0},   # 관련도 높음, 긍정적
        {"ticker_sentiment_score": -0.2, "relevance_score": 0.1},  # 관련도 낮음, 부정적
    ]
    score = aggregate_news_score(articles)
    # 관련도 높은 기사가 지배적이어야 함 -> 0에 가깝지 않고 양수 쪽으로 크게 치우쳐야 함
    assert score > 0.5


def test_aggregate_news_score_empty():
    assert aggregate_news_score([]) == 0.0


def test_build_signal_combines_scores_correctly():
    signal = build_signal("AAPL", news_score=0.6, analyst_score=0.4,
                           news_weight=0.5, analyst_weight=0.5)
    assert signal["ticker"] == "AAPL"
    assert signal["combined_score"] == 0.5  # (0.6*0.5 + 0.4*0.5)


def test_recommendation_to_score_all_strong_buy():
    rec = {"strong_buy": 10, "buy": 0, "hold": 0, "sell": 0, "strong_sell": 0}
    assert recommendation_to_score(rec) == 1.0  # 전부 강력매수 -> 최대값 1.0


def test_recommendation_to_score_all_strong_sell():
    rec = {"strong_buy": 0, "buy": 0, "hold": 0, "sell": 0, "strong_sell": 10}
    assert recommendation_to_score(rec) == -1.0  # 전부 강력매도 -> 최소값 -1.0


def test_recommendation_to_score_neutral():
    rec = {"strong_buy": 0, "buy": 0, "hold": 10, "sell": 0, "strong_sell": 0}
    assert recommendation_to_score(rec) == 0.0


def test_recommendation_to_score_empty():
    assert recommendation_to_score({}) == 0.0
