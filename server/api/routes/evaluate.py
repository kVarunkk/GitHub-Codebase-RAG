from fastapi import APIRouter, HTTPException
from api.models import EvaluateRequest, EvaluateResponse, MetricResult
from core.generator import ask
from deepeval import evaluate
from deepeval.test_case import LLMTestCase
from deepeval.models import GeminiModel
from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
)
import asyncio
import os
from constants import GEMINI_MODEL

router = APIRouter()

def run_evaluation(question, answer, retrieved_contexts, expected_answer):
    gemini_judge = GeminiModel(model=GEMINI_MODEL, api_key=os.getenv("GOOGLE_API_KEY"))

    test_case = LLMTestCase(
        input=question,
        actual_output=answer,
        retrieval_context=retrieved_contexts,
        expected_output=expected_answer,
    )

    # only include recall + precision if expected_answer is provided
    metrics = [
        AnswerRelevancyMetric(threshold=0.7, model=gemini_judge),
        FaithfulnessMetric(threshold=0.7, model=gemini_judge),
    ]
    if expected_answer:
        metrics += [
            ContextualPrecisionMetric(threshold=0.7, model=gemini_judge),
            ContextualRecallMetric(threshold=0.7, model=gemini_judge),
        ]

    return evaluate([test_case], metrics=metrics)


@router.post("/evaluate", response_model=EvaluateResponse)
async def evaluate_query(body: EvaluateRequest):
    try:
        answer, reranked = await ask(
            question=body.question,
            repo=body.repo,
            candidate_k=body.candidate_k,
            final_k=body.final_k,
        )

        if not answer:
            raise HTTPException(status_code=500, detail="Failed to generate answer")

        retrieved_contexts = [r.payload["content"] for r in reranked]

        # run sync evaluate() in threadpool so event loop isn't blocked
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: run_evaluation(body.question, answer, retrieved_contexts, body.expected_answer)
        )

        test = result.test_results[0]
        metrics = [
            MetricResult(
                name=m.name,
                score=m.score,
                threshold=m.threshold,
                passed=m.success,
                reason=m.reason,
            )
            for m in (test.metrics_data or [])
        ]

        return EvaluateResponse(
            question=body.question,
            answer=answer,
            passed=test.success,
            metrics=metrics,
            confident_link=result.confident_link,
        )

    except Exception as e:
        print(f"[evaluate] Failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))