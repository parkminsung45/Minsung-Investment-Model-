"""
뉴스/애널리스트 데이터 수집, S&P500·NASDAQ100 종목 유니버스 조회,
시그널 결합, FinBERT 앙상블을 한 곳에 모은 모듈.
"""
import json
import os
import time
from functools import lru_cache
from io import StringIO
from typing import Callable, Dict, List

import pandas as pd
import requests


# ---------------------------------------------------------------------------
# 뉴스 감성 (Alpha Vantage)
# 문서: https://www.alphavantage.co/documentation/#news-sentiment
# ---------------------------------------------------------------------------

ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"


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
    resp = requests.get(ALPHA_VANTAGE_BASE_URL, params=params, timeout=15)
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


# ---------------------------------------------------------------------------
# 애널리스트 컨센서스 (Finnhub)
# 문서: https://finnhub.io/docs/api
# ---------------------------------------------------------------------------

FINNHUB_BASE_URL = "https://finnhub.io/api/v1"


def fetch_recommendation_trends(ticker: str, api_key: str) -> Dict:
    resp = requests.get(
        f"{FINNHUB_BASE_URL}/stock/recommendation",
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
        f"{FINNHUB_BASE_URL}/stock/price-target",
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


def fetch_basic_financials(ticker: str, api_key: str) -> Dict:
    """Finnhub Basic Financials (stock/metric). 무료 티어에서 사용 가능."""
    resp = requests.get(
        f"{FINNHUB_BASE_URL}/stock/metric",
        params={"symbol": ticker, "metric": "all", "token": api_key},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("metric", {})


def passes_financial_health(
    metrics: Dict,
    min_net_margin: float = 0.0,
    min_roe: float = 0.0,
    max_debt_to_equity: float = 2.0,
) -> bool:
    """
    재무 건전성 필터 (기본값: 순이익률(TTM)>0, ROE(TTM)>0, 부채비율(D/E)<2.0).
    fetch_basic_financials()가 반환한 netProfitMarginTTM, roeTTM,
    totalDebt/totalEquityAnnual 지표를 사용한다.
    지표가 없으면 보수적으로 통과시키지 않는다.
    """
    if not metrics:
        return False

    net_margin = metrics.get("netProfitMarginTTM")
    roe = metrics.get("roeTTM")
    debt_to_equity = metrics.get("totalDebt/totalEquityAnnual")

    if net_margin is None or roe is None or debt_to_equity is None:
        return False

    return net_margin > min_net_margin and roe > min_roe and debt_to_equity < max_debt_to_equity


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


# ---------------------------------------------------------------------------
# 시그널 결합
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# FinBERT 앙상블 (선택)
# Alpha Vantage 자체 점수와 별개로, 금융특화 언어모델(FinBERT)로 뉴스 제목을
# 직접 채점해 두 점수를 앙상블하고 싶을 때 사용한다. 필수는 아니다.
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_sentiment_pipeline():
    from transformers import pipeline
    return pipeline(
        "text-classification",
        model="ProsusAI/finbert",
        top_k=None,
    )


def score_texts(texts: List[str]) -> List[float]:
    """
    각 텍스트에 대해 -1(부정) ~ +1(긍정) 사이 감성 점수를 반환한다.
    FinBERT는 positive/negative/neutral 확률을 주므로
    (positive 확률 - negative 확률)로 하나의 점수로 변환한다.
    최초 호출 시 모델 가중치(약 400MB)를 인터넷에서 내려받는다.
    """
    if not texts:
        return []

    clf = _load_sentiment_pipeline()
    results = clf(texts, truncation=True)

    scores = []
    for result in results:
        prob = {r["label"].lower(): r["score"] for r in result}
        score = prob.get("positive", 0.0) - prob.get("negative", 0.0)
        scores.append(score)
    return scores


# ---------------------------------------------------------------------------
# S&P 500 / NASDAQ 100 유니버스
#
# 구성종목은 분기별 리밸런싱으로 바뀌므로, 하드코딩하지 않고 실행 시점마다
# 새로 가져오는 것을 기본으로 한다.
#
# 소스 우선순위:
#   1. stockanalysis.com 종목 리스트 표 (두 지수 모두 지원, 기본)
#   2. (S&P500 한정) 위키피디아 "List of S&P 500 companies" 표
#      - Nasdaq-100 위키피디아 문서는 더 이상 구성종목 표를 포함하지 않아 제외
#   3. 위 소스가 모두 실패하면 마지막으로 성공했던 결과를 로컬 캐시
#      (.cache/universe_cache.json)에서 불러온다.
# ---------------------------------------------------------------------------

_UNIVERSE_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-pipeline/1.0)"}

_CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
_CACHE_PATH = os.path.join(_CACHE_DIR, "universe_cache.json")

SP500_STOCKANALYSIS_URL = "https://stockanalysis.com/list/sp-500-stocks/"
NASDAQ100_STOCKANALYSIS_URL = "https://stockanalysis.com/list/nasdaq-100-stocks/"
SP500_WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def _tickers_from_stockanalysis(url: str) -> List[str]:
    resp = requests.get(url, headers=_UNIVERSE_HEADERS, timeout=15)
    resp.raise_for_status()
    table = pd.read_html(StringIO(resp.text))[0]
    return sorted(set(table["Symbol"].astype(str).str.strip()))


def _sp500_from_wikipedia() -> List[str]:
    resp = requests.get(SP500_WIKI_URL, headers=_UNIVERSE_HEADERS, timeout=15)
    resp.raise_for_status()
    table = pd.read_html(StringIO(resp.text))[0]
    tickers = table["Symbol"].astype(str).str.strip().str.replace(".", "-", regex=False)
    return sorted(set(tickers))


def _load_universe_cache() -> Dict:
    if os.path.exists(_CACHE_PATH):
        with open(_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_universe_cache(cache: Dict) -> None:
    os.makedirs(_CACHE_DIR, exist_ok=True)
    with open(_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def _get_universe_tickers(key: str, fetchers: List[Callable[[], List[str]]]) -> List[str]:
    for fetch in fetchers:
        try:
            tickers = fetch()
            if tickers:
                cache = _load_universe_cache()
                cache[key] = {
                    "tickers": tickers,
                    "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                }
                _save_universe_cache(cache)
                return tickers
        except Exception as e:
            print(f"[universe] {key} 조회 실패 ({fetch!r}): {e}")

    cache = _load_universe_cache()
    cached = cache.get(key)
    if cached:
        print(f"[universe] 실시간 조회 실패, 캐시된 {key} 목록 사용 (기준: {cached['fetched_at']})")
        return cached["tickers"]

    raise RuntimeError(f"{key} 종목 리스트를 가져오지 못했고, 캐시도 없습니다.")


def get_sp500_tickers() -> List[str]:
    return _get_universe_tickers(
        "sp500",
        [lambda: _tickers_from_stockanalysis(SP500_STOCKANALYSIS_URL), _sp500_from_wikipedia],
    )


def get_nasdaq100_tickers() -> List[str]:
    return _get_universe_tickers(
        "nasdaq100",
        [lambda: _tickers_from_stockanalysis(NASDAQ100_STOCKANALYSIS_URL)],
    )


def get_universe_tickers() -> List[str]:
    """S&P 500과 NASDAQ 100의 합집합(중복 제거, 정렬)."""
    return sorted(set(get_sp500_tickers()) | set(get_nasdaq100_tickers()))
