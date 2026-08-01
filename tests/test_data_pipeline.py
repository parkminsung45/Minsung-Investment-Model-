import sys
import os

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import data_pipeline as dp


def test_aggregate_news_score_weighted_average():
    articles = [
        {"ticker_sentiment_score": 0.8, "relevance_score": 1.0},   # 관련도 높음, 긍정적
        {"ticker_sentiment_score": -0.2, "relevance_score": 0.1},  # 관련도 낮음, 부정적
    ]
    score = dp.aggregate_news_score(articles)
    # 관련도 높은 기사가 지배적이어야 함 -> 0에 가깝지 않고 양수 쪽으로 크게 치우쳐야 함
    assert score > 0.5


def test_aggregate_news_score_empty():
    assert dp.aggregate_news_score([]) == 0.0


def test_build_signal_combines_scores_correctly():
    signal = dp.build_signal("AAPL", news_score=0.6, analyst_score=0.4,
                              news_weight=0.5, analyst_weight=0.5)
    assert signal["ticker"] == "AAPL"
    assert signal["combined_score"] == 0.5  # (0.6*0.5 + 0.4*0.5)


def test_recommendation_to_score_all_strong_buy():
    rec = {"strong_buy": 10, "buy": 0, "hold": 0, "sell": 0, "strong_sell": 0}
    assert dp.recommendation_to_score(rec) == 1.0  # 전부 강력매수 -> 최대값 1.0


def test_recommendation_to_score_all_strong_sell():
    rec = {"strong_buy": 0, "buy": 0, "hold": 0, "sell": 0, "strong_sell": 10}
    assert dp.recommendation_to_score(rec) == -1.0  # 전부 강력매도 -> 최소값 -1.0


def test_recommendation_to_score_neutral():
    rec = {"strong_buy": 0, "buy": 0, "hold": 10, "sell": 0, "strong_sell": 0}
    assert dp.recommendation_to_score(rec) == 0.0


def test_recommendation_to_score_empty():
    assert dp.recommendation_to_score({}) == 0.0


def test_passes_financial_health_true_for_healthy_metrics():
    metrics = {"netProfitMarginTTM": 27.6, "roeTTM": 137.2, "totalDebt/totalEquityAnnual": 1.35}
    assert dp.passes_financial_health(metrics) is True


def test_passes_financial_health_false_for_negative_margin():
    metrics = {"netProfitMarginTTM": -5, "roeTTM": 10, "totalDebt/totalEquityAnnual": 1.0}
    assert dp.passes_financial_health(metrics) is False


def test_passes_financial_health_false_for_high_debt_to_equity():
    metrics = {"netProfitMarginTTM": 10, "roeTTM": 10, "totalDebt/totalEquityAnnual": 5.0}
    assert dp.passes_financial_health(metrics) is False


def test_passes_financial_health_false_when_metrics_missing():
    assert dp.passes_financial_health({}) is False
    assert dp.passes_financial_health({"netProfitMarginTTM": 10}) is False


def test_passes_financial_health_respects_custom_thresholds():
    metrics = {"netProfitMarginTTM": 1, "roeTTM": 1, "totalDebt/totalEquityAnnual": 1.5}
    assert dp.passes_financial_health(metrics, max_debt_to_equity=2.0) is True
    assert dp.passes_financial_health(metrics, max_debt_to_equity=1.0) is False


@pytest.fixture(autouse=True)
def isolated_universe_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(dp, "_CACHE_PATH", str(tmp_path / "universe_cache.json"))
    monkeypatch.setattr(dp, "_CACHE_DIR", str(tmp_path))


def test_get_tickers_uses_first_successful_fetcher():
    result = dp._get_universe_tickers("test", [lambda: ["AAPL", "MSFT"]])
    assert result == ["AAPL", "MSFT"]


def test_get_tickers_falls_back_to_second_fetcher_on_failure():
    def failing():
        raise RuntimeError("boom")

    result = dp._get_universe_tickers("test", [failing, lambda: ["NVDA"]])
    assert result == ["NVDA"]


def test_get_tickers_caches_successful_result():
    dp._get_universe_tickers("test", [lambda: ["AAPL"]])
    cache = dp._load_universe_cache()
    assert cache["test"]["tickers"] == ["AAPL"]
    assert "fetched_at" in cache["test"]


def test_get_tickers_falls_back_to_cache_when_all_fetchers_fail():
    dp._get_universe_tickers("test", [lambda: ["AAPL", "MSFT"]])

    def failing():
        raise RuntimeError("network down")

    result = dp._get_universe_tickers("test", [failing])
    assert result == ["AAPL", "MSFT"]


def test_get_tickers_raises_when_no_fetcher_and_no_cache():
    def failing():
        raise RuntimeError("network down")

    with pytest.raises(RuntimeError):
        dp._get_universe_tickers("nonexistent", [failing])


def test_get_universe_tickers_unions_and_dedupes(monkeypatch):
    monkeypatch.setattr(dp, "get_sp500_tickers", lambda: ["AAPL", "MSFT", "NVDA"])
    monkeypatch.setattr(dp, "get_nasdaq100_tickers", lambda: ["MSFT", "GOOGL"])

    result = dp.get_universe_tickers()
    assert result == ["AAPL", "GOOGL", "MSFT", "NVDA"]
