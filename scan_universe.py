"""
S&P 500 + NASDAQ 100 전체 종목에 대해 Finnhub 애널리스트 컨센서스 점수만 수집한다.

뉴스 감성(Alpha Vantage)은 무료 티어 하루 25회 한도 때문에 이 규모(약 550개
종목)에서는 감당할 수 없어 제외한다. 뉴스+애널리스트 결합 시그널이 필요하면
main.py의 소수 관심종목(config.WATCHLIST) 파이프라인을 사용할 것.

실행 방법: python scan_universe.py
결과: output/universe_analyst_scores_YYYY-MM-DD.csv
"""
import csv
import os
import time
from datetime import datetime

import config
from data_pipeline import get_universe_tickers, fetch_recommendation_trends, recommendation_to_score


def run():
    if not config.FINNHUB_API_KEY:
        raise RuntimeError(".env 파일에 FINNHUB_API_KEY를 설정하세요.")

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    tickers = get_universe_tickers()
    print(f"[universe] S&P500 + NASDAQ100 대상 종목 수: {len(tickers)}")

    rows = []
    for i, ticker in enumerate(tickers):
        rec = fetch_recommendation_trends(ticker, config.FINNHUB_API_KEY)
        rows.append({
            "ticker": ticker,
            "analyst_score": round(recommendation_to_score(rec), 4),
            "strong_buy": rec.get("strong_buy", 0),
            "buy": rec.get("buy", 0),
            "hold": rec.get("hold", 0),
            "sell": rec.get("sell", 0),
            "strong_sell": rec.get("strong_sell", 0),
        })
        print(f"  [{i + 1}/{len(tickers)}] {ticker} 완료")
        if i < len(tickers) - 1:
            time.sleep(config.FINNHUB_UNIVERSE_DELAY_SEC)

    today = datetime.now().strftime("%Y-%m-%d")
    out_path = os.path.join(config.OUTPUT_DIR, f"universe_analyst_scores_{today}.csv")

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"완료: {out_path}")
    return rows


if __name__ == "__main__":
    run()
