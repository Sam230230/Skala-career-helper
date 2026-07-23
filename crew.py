# =====================================================================
# SKALA 취업 컨설팅 지원 자동화 플랫폼 - Crew 조립 & 실행
# 파일 배치 예시
#   src/skala_consulting/crew.py          <- 이 파일
#   src/skala_consulting/config/agents.yaml
#   src/skala_consulting/config/tasks.yaml
# =====================================================================
from __future__ import annotations

import os
from typing import List, Literal, Optional

# --- .env 자동 로드 (crew.py 를 직접 import 하는 백엔드/CLI/노트북 어디서든 동작) ---
from dotenv import load_dotenv

load_dotenv(override=True)

from pydantic import BaseModel, Field

from crewai import LLM, Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task

# 검색 툴은 SERPER_API_KEY 가 있을 때만 사용. 미설치/미설정 환경에서도 크루가 뜨도록 안전 처리.
try:
    from crewai_tools import ScrapeWebsiteTool, SerperDevTool
except Exception:  # crewai_tools 미설치
    ScrapeWebsiteTool = SerperDevTool = None  # type: ignore


# ---------------------------------------------------------------------
# 0. 공용 LLM / 검색 툴 팩토리
# ---------------------------------------------------------------------
def build_llm() -> LLM:
    """.env 의 OPENAI_MODEL_NAME 을 사용해 LLM 을 구성한다.

    - 모델명은 litellm 규칙상 provider 접두어가 필요하므로 'openai/' 를 보장한다.
    - api_key 는 LLM 이 환경변수 OPENAI_API_KEY 에서 자동으로 읽는다.
    """
    model = os.getenv("OPENAI_MODEL_NAME") or "openai/gpt-4o-mini"
    if not model.startswith("openai/"):
        model = f"openai/{model}"
    return LLM(model=model, temperature=0.3)


# 크루 전체가 공유하는 단일 LLM 인스턴스
SHARED_LLM = build_llm()


def search_tools() -> list:
    """SERPER_API_KEY 가 설정돼 있고 crewai_tools 가 설치돼 있으면 실시간 검색 툴을 반환.

    키가 없으면 빈 리스트를 반환하며, 이 경우 job_trend_analyst 는 실시간 검색 없이
    모델 지식만으로 동작한다(공고 수치는 프롬프트 규칙에 따라 '데이터 확인 불가'로 표기).
    """
    if os.getenv("SERPER_API_KEY") and SerperDevTool is not None:
        return [SerperDevTool(), ScrapeWebsiteTool()]
    return []


# ---------------------------------------------------------------------
# 1. 출력 스키마 (Structured Output 강제 - 프롬프트 기법: Schema Enforcement)
#    tasks.yaml 의 expected_output 은 '설명', 실제 강제는 여기 Pydantic 이 담당
# ---------------------------------------------------------------------
Level = Literal["상", "중", "하"]
Badge = Literal["✅ 보유", "⚠️ 부분보유", "❌ 미보유"]


class SkillKeyword(BaseModel):
    keyword: str = Field(description="표준 표기로 정규화된 키워드")
    proficiency: Level = Field(description="서류 근거로 추정한 숙련도")
    evidence: str = Field(description="원문 근거 인용, 30자 이내")


class ProjectItem(BaseModel):
    name: str
    role: str = Field(description="본인이 실제 담당한 역할")
    tech_stack: List[str]
    outcome: str = Field(description="수치·결과 중심 성과. 없으면 '정보 없음'")


class DesiredJobInfo(BaseModel):
    job_title: str
    is_inferred: bool = Field(description="사용자 미입력으로 추론한 값이면 True")
    alignment: Level = Field(description="서류 근거와 희망 직무의 정합성")
    alignment_reason: str


class ApplicantProfile(BaseModel):
    trainee_id: str
    trainee_name: str
    one_line_definition: str = Field(description="25자 내외 한 줄 정의")
    summary: str = Field(description="자기소개서 요약 3~5문장, 서술형")
    tech_keywords: List[SkillKeyword]
    domain_keywords: List[str]
    soft_skill_keywords: List[str]
    projects: List[ProjectItem] = Field(max_length=3)
    certificates: List[str]
    hidden_strengths: List[str] = Field(description="숨은 강점 2개 + 시장가치 설명")
    information_gaps: List[str] = Field(description="상담에서 확인할 설명 공백 2~3개")
    desired_job: DesiredJobInfo


class RequiredSkillRank(BaseModel):
    rank: int
    skill: str
    has_it: bool


class RecommendedJob(BaseModel):
    priority: int
    job_title: str
    synonyms: List[str]
    reason: str
    entry_difficulty: Level
    posting_volume_12m: str = Field(description="수치 또는 '데이터 확인 불가'")
    junior_open_ratio: str
    required_skills: List[RequiredSkillRank]


class DistributionItem(BaseModel):
    category: str
    share: str = Field(description="비중 또는 공고 수. 미확인 시 '데이터 확인 불가'")
    note: str = ""


class RecommendedCompany(BaseModel):
    company: str
    industry: str
    open_position: str
    reason: str
    junior_friendly: bool
    source: str


class JobMarketReport(BaseModel):
    surveyed_at: str
    sources: List[str]
    recommended_jobs: List[RecommendedJob] = Field(max_length=3)
    industry_distribution: List[DistributionItem]
    company_size_distribution: List[DistributionItem]
    recommended_companies: List[RecommendedCompany]
    market_comment: str


class FitMatrixRow(BaseModel):
    required_skill: str
    badge: Badge
    evidence: str


class ScoreBreakdown(BaseModel):
    tech_stack: int = Field(ge=0, le=40)
    experience: int = Field(ge=0, le=30)
    domain: int = Field(ge=0, le=15)
    soft_skill: int = Field(ge=0, le=15)


class PortfolioSuggestion(BaseModel):
    title: str
    tech_stack: List[str]
    deliverable: str = Field(description="리포지토리 / 배포 URL / 문서 등 산출물 형태")
    duration_weeks: int
    difficulty: Level
    covers_gap: str
    interview_pitch: str


class InterviewQuestion(BaseModel):
    q_type: Literal["경험 검증형", "기술 심화형", "문제 해결형", "직무 적합·지원 동기형"]
    question: str
    intent: str
    good_answer_checkpoints: List[str] = Field(min_length=2, max_length=3)
    follow_up: str


class HRFitReview(BaseModel):
    target_job: str
    fit_matrix: List[FitMatrixRow]
    total_score: int = Field(ge=0, le=100)
    score_breakdown: ScoreBreakdown
    grade: Literal["즉시 지원 권장", "보완 후 지원", "직무 재설정 검토"]
    critical_gaps: List[str] = Field(max_length=3)
    portfolio_suggestions: List[PortfolioSuggestion] = Field(min_length=3, max_length=3)
    interview_questions: List[InterviewQuestion] = Field(min_length=5, max_length=5)
    hr_comment: str


# ---------------------------------------------------------------------
# 2. Crew 정의
# ---------------------------------------------------------------------
@CrewBase
class SkalaConsultingCrew:
    """SKALA 교육생 취업 컨설팅 지원 Crew"""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    # ---- Agents -----------------------------------------------------
    @agent
    def cv_analyst(self) -> Agent:
        return Agent(config=self.agents_config["cv_analyst"], llm=SHARED_LLM, verbose=True)

    @agent
    def job_trend_analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["job_trend_analyst"],
            tools=search_tools(),  # SERPER_API_KEY 있으면 실시간 채용공고 조사, 없으면 빈 리스트
            llm=SHARED_LLM,
            verbose=True,
        )

    @agent
    def hr_specialist(self) -> Agent:
        return Agent(config=self.agents_config["hr_specialist"], llm=SHARED_LLM, verbose=True)

    @agent
    def consulting_reporter(self) -> Agent:
        return Agent(
            config=self.agents_config["consulting_reporter"], llm=SHARED_LLM, verbose=True
        )

    # ---- Tasks ------------------------------------------------------
    @task
    def analyze_documents_task(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_documents_task"],
            agent=self.cv_analyst(),
            output_pydantic=ApplicantProfile,
        )

    @task
    def analyze_job_trend_task(self) -> Task:
        return Task(
            config=self.tasks_config["analyze_job_trend_task"],
            agent=self.job_trend_analyst(),
            context=[self.analyze_documents_task()],
            output_pydantic=JobMarketReport,
        )

    @task
    def hr_fit_review_task(self) -> Task:
        return Task(
            config=self.tasks_config["hr_fit_review_task"],
            agent=self.hr_specialist(),
            context=[self.analyze_documents_task(), self.analyze_job_trend_task()],
            output_pydantic=HRFitReview,
        )

    @task
    def build_consulting_report_task(self) -> Task:
        return Task(
            config=self.tasks_config["build_consulting_report_task"],
            agent=self.consulting_reporter(),
            context=[
                self.analyze_documents_task(),
                self.analyze_job_trend_task(),
                self.hr_fit_review_task(),
            ],
            output_file="output/report_{trainee_id}.md",
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
            memory=False,
        )


# ---------------------------------------------------------------------
# 3. 입력 전처리 (희망 진로 선택 입력 / 포트폴리오 선택 입력 처리)
# ---------------------------------------------------------------------
def build_inputs(raw: dict) -> dict:
    """프론트에서 넘어온 원본 dict -> Crew inputs 로 정규화."""
    return {
        "trainee_id": raw.get("trainee_id", "UNKNOWN"),
        "trainee_name": raw.get("trainee_name", "익명"),
        "desired_job": (raw.get("desired_job") or "").strip() or "없음",
        "cover_letter": raw["cover_letter"].strip(),
        "resume": raw["resume"].strip(),
        "portfolio": (raw.get("portfolio") or "").strip() or "없음",
    }


# ---------------------------------------------------------------------
# 4. 실행 (단건 / 배치)
# ---------------------------------------------------------------------
def run_single(raw: dict):
    os.makedirs("output", exist_ok=True)
    return SkalaConsultingCrew().crew().kickoff(inputs=build_inputs(raw))


def run_batch(raw_list: List[dict]):
    """확장 요구사항: 여러 교육생 자기소개서를 한 번에 처리."""
    os.makedirs("output", exist_ok=True)
    inputs = [build_inputs(r) for r in raw_list]
    return SkalaConsultingCrew().crew().kickoff_for_each(inputs=inputs)


# ---------------------------------------------------------------------
# 5. Mock 입력 데이터 (작업순서 5번용)
# ---------------------------------------------------------------------
MOCK_TRAINEES = [
    {
        "trainee_id": "SKALA-2025-014",
        "trainee_name": "김지훈",
        "desired_job": "백엔드 개발자",
        "cover_letter": (
            "저는 기계공학을 전공했지만 3학년 때 참여한 스마트팩토리 캡스톤 과제에서 "
            "설비 센서 데이터를 수집·처리하는 파트를 맡으며 소프트웨어에 관심을 갖게 되었습니다. "
            "당시 엑셀로 수기 집계하던 불량 데이터를 Python 스크립트로 자동화해 "
            "주간 집계 작업 시간을 4시간에서 20분으로 줄였습니다. "
            "이 경험을 계기로 SKALA 과정에 지원했고, Java와 Spring Boot 기반 백엔드 개발을 "
            "집중적으로 학습했습니다. 팀 프로젝트에서는 5명 팀의 API 설계를 담당하며 "
            "REST 규칙을 문서화해 프론트와의 재작업을 줄였습니다. "
            "제조 현장에 대한 이해를 가진 백엔드 개발자가 되고 싶습니다."
        ),
        "resume": (
            "[학력] OO대학교 기계공학과 졸업 (2025.02), 학점 3.7/4.5\n"
            "[교육] SKALA 2기 수료 예정 (2025.03~2025.08), Java/Spring Boot/JPA/AWS\n"
            "[프로젝트]\n"
            "1) 설비 이상탐지 대시보드 (2024.09~2024.12) - 팀 4명, 데이터 파이프라인 담당, "
            "Python/Pandas/InfluxDB, 불량 집계 자동화로 작업시간 92% 단축\n"
            "2) 중고거래 플랫폼 API 서버 (2025.05~2025.07) - 팀 5명, API 설계 및 인증 구현, "
            "Java/Spring Boot/JPA/MySQL/Redis, JWT 인증 및 Redis 캐싱으로 조회 응답 320ms→110ms\n"
            "[자격/어학] 정보처리기사(2025.06), SQLD(2024.11), TOEIC 820\n"
            "[기타] GitHub 커밋 400+, 기술 블로그 운영(포스트 22건)"
        ),
        "portfolio": (
            "GitHub: 중고거래 플랫폼 API 서버 리포지토리 (README에 ERD, API 명세 포함), "
            "AWS EC2 배포 경험, Swagger 문서화. 테스트 코드는 일부 서비스 계층만 작성."
        ),
    },
    {
        "trainee_id": "SKALA-2025-027",
        "trainee_name": "이서연",
        "desired_job": "",  # 희망 진로 미입력 케이스
        "cover_letter": (
            "경영학을 전공하며 마케팅 동아리에서 소비자 설문 데이터를 다루던 중 "
            "숫자가 의사결정을 바꾸는 순간을 경험했습니다. "
            "졸업 프로젝트에서 카페 프랜차이즈의 3년치 매출 데이터를 분석해 "
            "요일·시간대별 발주량 조정안을 제안했고, 시범 매장에서 폐기율이 감소했습니다. "
            "SKALA 과정에서는 SQL과 Python을 활용한 데이터 처리와 시각화를 학습했습니다."
        ),
        "resume": (
            "[학력] OO대학교 경영학과 졸업 (2025.02), 학점 4.0/4.5\n"
            "[교육] SKALA 2기 수료 예정, Python/SQL/Tableau/기초 머신러닝\n"
            "[프로젝트]\n"
            "1) 프랜차이즈 매출 분석 (2024.03~2024.06) - 개인, Python/Pandas/Tableau, "
            "시간대별 수요 예측 기반 발주안 제안, 시범 매장 폐기율 개선\n"
            "2) 고객 이탈 예측 모델 (2025.06~2025.07) - 팀 3명, 데이터 전처리 담당, "
            "scikit-learn 로지스틱 회귀, 정확도 0.81\n"
            "[자격/어학] ADsP(2024.09), 컴활 1급, TOEIC 900\n"
        ),
        "portfolio": "",  # 포트폴리오 미제출 케이스
    },
]


if __name__ == "__main__":
    os.makedirs("output", exist_ok=True)
    results = run_batch(MOCK_TRAINEES)
    for r in results:
        print(r.raw)
