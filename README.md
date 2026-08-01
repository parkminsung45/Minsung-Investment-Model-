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
├── main.py              # 관심종목(WATCHLIST) 뉴스+애널리스트 결합 시그널 실행
├── scan_universe.py     # S&P500+NASDAQ100 전체 종목 애널리스트 스코어 스캔
├── config.py            # 설정값 (티커, 가중치, API 키 로딩)
├── data_pipeline.py     # 뉴스/애널리스트/유니버스 수집 + 시그널 결합 + FinBERT
├── broker.py            # 토스증권 Open API 클라이언트 (계좌/주문, 기본 드라이런)
├── tests/
│   ├── test_data_pipeline.py
│   └── test_broker.py
├── .cache/               # data_pipeline.py의 종목 리스트 캐시 (git 제외)
└── output/               # signals_*.csv, universe_analyst_scores_*.csv 생성 위치
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

- `WATCHLIST`: 뉴스+애널리스트 결합 시그널(main.py)을 계산할 소수 관심종목.
  Alpha Vantage 무료 티어(하루 25회)로 감당 가능한 규모로 유지할 것
- `NEWS_WEIGHT`, `ANALYST_WEIGHT`: 뉴스 vs 애널리스트 가중치 (합=1)
- `NEWS_FETCH_DELAY_SEC`: Alpha Vantage 무료 티어 호출 제한 대응 대기시간
- `FINNHUB_UNIVERSE_DELAY_SEC`: scan_universe.py에서 Finnhub 호출 간 대기시간

## 4-1. S&P500 + NASDAQ100 전체 스캔 (scan_universe.py)

```bash
python scan_universe.py
```

`data_pipeline.py`의 유니버스 조회 함수가 stockanalysis.com(실패 시 위키피디아, 그마저
실패하면 `.cache/universe_cache.json`의 직전 결과)에서 S&P500·NASDAQ100
구성종목(중복 제거 후 약 520개)을 매번 새로 가져와 Finnhub 애널리스트
컨센서스 점수만 계산합니다.

뉴스 감성(Alpha Vantage)은 이 규모에서 하루 호출 한도(25회)를 크게 초과하므로
제외했습니다. 뉴스까지 포함한 결합 시그널이 필요한 종목은 `WATCHLIST`에
추가해 `main.py`로 계산하세요.

`output/universe_analyst_scores_YYYY-MM-DD.csv` 컬럼:

- `ticker`, `analyst_score`, `strong_buy`, `buy`, `hold`, `sell`, `strong_sell`

전체 스캔은 티커당 `FINNHUB_UNIVERSE_DELAY_SEC`(기본 1초)씩 대기하므로
약 8~10분 소요됩니다.

## 5. FinBERT로 자체 감성분석 추가 (선택)

`data_pipeline.py`의 `score_texts()`를 사용하면 Alpha Vantage 자체
점수와 별개로, 금융특화 언어모델(FinBERT)로 뉴스 제목을 직접 채점해
두 점수를 앙상블할 수 있습니다. 최초 실행 시 모델(~400MB)을 다운로드합니다.

```python
from data_pipeline import score_texts
titles = [a["title"] for a in news_by_ticker["AAPL"]]
finbert_scores = score_texts(titles)
```

## 6. 매일 자동 실행 (선택)

리눅스/맥에서 cron으로 매일 아침 실행 예시:

```
0 8 * * 1-5 cd /path/to/news_analyst_pipeline && /usr/bin/python3 main.py >> log.txt 2>&1
```

## 7. 토스증권 Open API 연동 (실거래, broker.py)

`broker.py`는 [토스증권 Open API](https://developers.tossinvest.com/docs)로
계좌 조회와 실제 주문 실행을 담당합니다. client_id/client_secret은 토스증권
WTS 로그인 후 설정 > Open API에서 발급받아 `.env`에 입력합니다
(`TOSS_CLIENT_ID`, `TOSS_CLIENT_SECRET`).

**⚠️ 이 API는 샌드박스/모의투자 환경이 없습니다.** 주문 생성 요청은 즉시
실제 계좌·실제 자금에 반영됩니다. 그래서 `broker.py`는 이중 안전장치로
동작합니다.

1. `config.TOSS_LIVE_TRADING`이 `false`(기본값)인 동안은 실제로 주문을
   보내지 않고, 보낼 요청 내용만 출력/반환합니다 (dry-run).
2. `.env`에서 `TOSS_LIVE_TRADING=true`로 실거래를 켠 상태에서도, 각 함수
   호출 시 `confirm=True`를 명시하지 않으면 실행을 거부합니다.

두 조건을 모두 충족해야 실제 주문이 나갑니다.

```python
import broker
import config

client = broker.TossClient(config.TOSS_CLIENT_ID, config.TOSS_CLIENT_SECRET)
accts = broker.get_accounts(client)          # 계좌 목록 조회 (읽기 전용)
# client.set_account(accountSeq) 로 이후 요청에 쓸 계좌를 지정

result = broker.create_order(
    client, symbol="AAPL", side="BUY", order_type="MARKET", quantity=1,
)
# TOSS_LIVE_TRADING=false 인 동안은 항상 {"dry_run": True, "would_send": {...}} 반환
```

현재 API 신청은 승인 대기 중이라 계좌/주문 엔드포인트는 실제 자격증명으로
아직 검증하지 못했습니다. 승인되면 `get_accounts()`부터 먼저 호출해
응답 형식을 확인한 뒤 필요하면 파싱 로직을 다듬어야 합니다.

## 다음 단계

- `signals_*.csv`의 `combined_score`를 실제 매수/매도 판단(임계값, 포지션
  크기, 리밸런싱 주기 등)으로 연결하는 매매 전략 설계
- 백테스팅 엔진: 과거 시그널·가격 데이터로 전략 수익률 검증
- 토스증권 API 승인 후 `broker.py` 실제 계좌로 검증

## 참고 (중요)

- 이 신호는 리서치/교육 목적이며 투자 자문이 아닙니다.
- `broker.py`로 실제 주문을 실행하는 것은 전적으로 본인 책임이며,
  `TOSS_LIVE_TRADING=true` 전환은 신중하게 결정해야 합니다.
