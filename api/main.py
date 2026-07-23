"""
SKALA Career Helper - FastAPI 백엔드

crew.py 의 run_single / run_batch 를 그대로 감싸는 얇은 API 계층이다.
에이전트 계층과 같은 Python 프로세스에서 돌기 때문에 별도 브리지가 필요 없다.

실행 (레포 루트에서):
    python -m uvicorn api.main:app --reload --port 8000

문서(자동): http://localhost:8000/docs
"""
from __future__ import annotations

from typing import Any, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# crew.py 는 레포 루트에 있으므로 그대로 import 된다(uvicorn 을 레포 루트에서 실행).
from crew import run_single, run_batch

app = FastAPI(
    title="SKALA Career Helper API",
    description="교육생 서류를 4개 AI 에이전트로 분석해 상담 리포트를 생성한다.",
    version="0.1.0",
)

# 로컬 전용 MVP — 프론트(Vite 기본 5173 등) 어디서 호출하든 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------
# 요청 스키마 (프론트 입력 폼과 1:1)
# ---------------------------------------------------------------------
class ConsultRequest(BaseModel):
    cover_letter: str = Field(..., description="자기소개서 원문 (필수)")
    resume: str = Field(..., description="이력서 원문 (필수)")
    portfolio: Optional[str] = Field("", description="포트폴리오 (선택)")
    desired_job: Optional[str] = Field("", description="희망 진로 (선택, 미입력 시 자동 추론)")
    trainee_id: Optional[str] = Field("SKALA-UNKNOWN", description="식별자")
    trainee_name: Optional[str] = Field("익명", description="이름")


class ConsultResponse(BaseModel):
    trainee_id: str
    trainee_name: str
    report_markdown: str = Field(description="최종 상담 리포트 (마크다운)")
    profile: Optional[dict] = Field(None, description="서류 분석 결과 (ApplicantProfile)")
    market: Optional[dict] = Field(None, description="채용시장 분석 (JobMarketReport)")
    hr_review: Optional[dict] = Field(None, description="적합도 진단 (HRFitReview)")


# ---------------------------------------------------------------------
# CrewOutput -> 응답 변환
# ---------------------------------------------------------------------
def _pydantic_of(crew_output: Any, index: int) -> Optional[dict]:
    """CrewOutput.tasks_output[index] 의 구조화 결과를 dict 로 변환(없으면 None)."""
    try:
        task_out = crew_output.tasks_output[index]
        if getattr(task_out, "pydantic", None) is not None:
            return task_out.pydantic.model_dump()
        if getattr(task_out, "json_dict", None):
            return task_out.json_dict
    except (IndexError, AttributeError):
        pass
    return None


def _to_response(raw: dict, crew_output: Any) -> ConsultResponse:
    return ConsultResponse(
        trainee_id=raw.get("trainee_id", "SKALA-UNKNOWN"),
        trainee_name=raw.get("trainee_name", "익명"),
        report_markdown=crew_output.raw,
        profile=_pydantic_of(crew_output, 0),   # analyze_documents_task
        market=_pydantic_of(crew_output, 1),     # analyze_job_trend_task
        hr_review=_pydantic_of(crew_output, 2),  # hr_fit_review_task
    )


# ---------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/consult", response_model=ConsultResponse)
def consult(req: ConsultRequest) -> ConsultResponse:
    """단건 분석. 크루 실행에 수십 초 걸릴 수 있으니 프론트에서 로딩 표시 필요."""
    raw = req.model_dump()
    try:
        result = run_single(raw)
    except Exception as exc:  # LLM/네트워크 오류 등을 400 으로 전달
        raise HTTPException(status_code=500, detail=f"크루 실행 실패: {exc}") from exc
    return _to_response(raw, result)


@app.post("/consult/batch", response_model=List[ConsultResponse])
def consult_batch(reqs: List[ConsultRequest]) -> List[ConsultResponse]:
    """배치 분석(확장 요구사항). 여러 교육생을 한 번에 처리한다."""
    raws = [r.model_dump() for r in reqs]
    try:
        results = run_batch(raws)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"배치 실행 실패: {exc}") from exc
    return [_to_response(raw, out) for raw, out in zip(raws, results)]
