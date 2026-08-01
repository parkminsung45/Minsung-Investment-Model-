"""
전체 파이프라인 실행:
  1. 티커별 뉴스 수집 (Alpha Vantage)
  2. 티커별 애널리스트 컨센서스 수집 (Finnhub)
  3. 뉴스 감성 요약 + 애널리스트 점수 결합
  4. 결과를 CSV로 저장 (output/signals_YYYY-MM-DD.csv)

실행 방법: python main.py
"""
import csv
import os
from datetime import datetime

import config
from data_pipeline import (
    fetch_news_for_universe,
    fetch_recommendation_trends,
    fetch_price_target,
    recommendation_to_score,
    aggregate_news_score,
    build_signal,
)


def run():
    if not config.ALPHA_VANTAGE_API_KEY or not config.FINNHUB_API_KEY:
        raise RuntimeError(
            ".env 파일에 ALPHA_VANTAGE_API_KEY와 FINNHUB_API_KEY를 설정하세요. "
            ".env.example을 복사해서 사용하면 됩니다."
        )

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    print(f"[1/3] 뉴스 수집 중... 대상: {config.WATCHLIST}")
    news_by_ticker = fetch_news_for_universe(
        config.WATCHLIST, config.ALPHA_VANTAGE_API_KEY, config.NEWS_FETCH_DELAY_SEC
    )

    signals = []
    for ticker in config.WATCHLIST:
        print(f"[2/3] {ticker} 애널리스트 데이터 수집 중...")
        rec = fetch_recommendation_trends(ticker, config.FINNHUB_API_KEY)
        target = fetch_price_target(ticker, config.FINNHUB_API_KEY)
        analyst_score = recommendation_to_score(rec)

        news_score = aggregate_news_score(news_by_ticker.get(ticker, []))

        signal = build_signal(
            ticker, news_score, analyst_score,
            config.NEWS_WEIGHT, config.ANALYST_WEIGHT,
        )
        signal["target_mean_price"] = target.get("target_mean")
        signal["num_articles"] = len(news_by_ticker.get(ticker, []))
        signals.append(signal)

    print("[3/3] 결과 저장 중...")
    today = datetime.now().strftime("%Y-%m-%d")
    out_path = os.path.join(config.OUTPUT_DIR, f"signals_{today}.csv")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=signals[0].keys())
        writer.writeheader()
        writer.writerows(signals)

    print(f"완료: {out_path}")
    return signals


if __name__ == "__main__":
    run()
