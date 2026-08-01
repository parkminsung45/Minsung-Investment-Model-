"""
FinBERT(금융 특화 사전학습 언어모델)로 뉴스 제목/본문의 감성을 직접 계산한다.

Alpha Vantage가 자체 감성 점수를 제공하지만, 서로 다른 모델로 한 번 더
검증(앙상블)하고 싶을 때 이 모듈을 사용한다. 필수는 아니고, 정확도를
높이고 싶을 때 signal_builder에서 선택적으로 결합하면 된다.

최초 실행 시 모델 가중치(약 400MB)를 인터넷에서 내려받는다.
"""
from functools import lru_cache
from typing import List


@lru_cache(maxsize=1)
def _load_pipeline():
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
    """
    if not texts:
        return []

    clf = _load_pipeline()
    results = clf(texts, truncation=True)

    scores = []
    for result in results:
        prob = {r["label"].lower(): r["score"] for r in result}
        score = prob.get("positive", 0.0) - prob.get("negative", 0.0)
        scores.append(score)
    return scores
