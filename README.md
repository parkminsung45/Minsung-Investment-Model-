# 뉴스 + 애널리스트 컨센서스 감성분석 파이프라인

미국 주식 종목별로 뉴스 감성점수와 애널리스트 컨센서스(추천등급/목표주가)를
결합해 하나의 시그널(-1 ~ 1)로 만드는 파이프라인입니다.

## 왜 "애널리스트 리포트 원문"이 아닌가?

실제 애널리스트 리포트 PDF(예: 골드만삭스, 모건스탠리 리포트)는 대부분
기관 전용 유료 데이터라 공개 API로는 가져올 수 없습니다. 대신 여러 애널리스트
의견을 요약한 **공개 컨센서스 데이터**(매수/보유/매도 추천 분포, 평균 목표주가)를
사용합니다. 이는 "여러 리포트 결론의 요약본"으로 볼 수 있습니다.

## 1. 준비물 (본인이 직접 가입)

| 서비스 | 용도 | 가입 링크 |
|---|---|---|
| Alpha Vantage | 뉴스 + 감성점수 | https://www.alphavantage.co/support/#api-key |
| Finnhub | 애널리스트 컨센서스 | https://finnhub.io/register |

두 곳 모두 무료 티어로 시작 가능합니다 (호출 횟수 제한 있음).

## 2. 설치

```bash
pip install -r requirements.txt
cp .env.example .env
# .env 파일을 열어 발급받은 키를 입력
```

## 폴더 구조

```
.
├── main.py                   # 전체 파이프라인 실행 진입점
├── config.py                 # 설정값 (티커, 가중치, API 키 로딩)
├── data_sources/
│   ├── news_fetcher.py       # Alpha Vantage 뉴스+감성 수집
│   └── analyst_fetcher.py    # Finnhub 애널리스트 컨센서스 수집
├── signals/
│   └── signal_builder.py     # 뉴스+애널리스트 점수 결합
├── nlp/
│   └── sentiment_model.py    # FinBERT 앙상블 (선택)
├── tests/
│   └── test_signal_builder.py
└── output/                    # signals_YYYY-MM-DD.csv 생성 위치
```

## 3. 실행

```bash
python main.py
```

`output/signals_YYYY-MM-DD.csv` 파일이 생성됩니다. 컬럼:

- `ticker`: 종목 코드
- `news_score`: 뉴스 감성 점수 (-1 ~ 1, relevance로 가중평균)
- `analyst_score`: 애널리스트 컨센서스 점수 (-1 ~ 1)
- `combined_score`: 최종 결합 시그널
- `target_mean_price`: 애널리스트 평균 목표주가
- `num_articles`: 수집된 기사 수

## 4. 설정 변경 (config.py)

- `TICKERS`: 분석 대상 종목 리스트
- `NEWS_WEIGHT`, `ANALYST_WEIGHT`: 뉴스 vs 애널리스트 가중치 (합=1)
- `NEWS_FETCH_DELAY_SEC`: Alpha Vantage 무료 티어 호출 제한 대응 대기시간

## 5. FinBERT로 자체 감성분석 추가 (선택)

`nlp/sentiment_model.py`의 `score_texts()`를 사용하면 Alpha Vantage 자체
점수와 별개로, 금융특화 언어모델(FinBERT)로 뉴스 제목을 직접 채점해
두 점수를 앙상블할 수 있습니다. 최초 실행 시 모델(~400MB)을 다운로드합니다.

```python
from nlp.sentiment_model import score_texts
titles = [a["title"] for a in news_by_ticker["AAPL"]]
finbert_scores = score_texts(titles)
```

## 6. 매일 자동 실행 (선택)

리눅스/맥에서 cron으로 매일 아침 실행 예시:

```
0 8 * * 1-5 cd /path/to/news_analyst_pipeline && /usr/bin/python3 main.py >> log.txt 2>&1
```

## 다음 단계

이 파이프라인이 만드는 `signals_*.csv`가 다음 단계(백테스팅, 포트폴리오
최적화/리밸런싱)의 입력이 됩니다. 준비되면 이어서 요청해주세요.

## 참고 (중요)

- 이 신호는 리서치/교육 목적이며 투자 자문이 아닙니다.
- 실제 매매 주문 실행(브로커 API 연동)은 본인 책임 하에 별도 환경에서
  진행해야 합니다.
