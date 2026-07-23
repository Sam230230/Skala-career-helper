# SKALA Career Helper — 아키텍처 설계서

> SKALA 교육생 취업 컨설팅 지원 자동화 플랫폼

---

## 1. 서비스 목적

본 서비스는 SKALA 교육생의 **이력서·자기소개서·포트폴리오** 데이터를 AI 기반으로 다각도 분석하여,
운영진·매니저의 1:1 취업 컨설팅 준비 시간을 혁신적으로 단축하고,
데이터 기반의 맞춤형 **직무·기업 추천 및 포트폴리오 보완 가이드**를 즉시 제공하는
**컨설팅 지원 자동화 플랫폼**이다.

### 핵심 가치
| 가치 | 내용 |
|---|---|
| **운영 효율화** | 컨설턴트의 교육생 서류 분석 시간 절감 |
| **상담 질 향상** | 객관적 데이터 기반의 맞춤형 직무/기업 타겟팅 및 포트폴리오 전략 제공 |
| **표준화** | 매니저별 컨설팅 품질 격차 해소 (30초 요약 카드 + 표준 서식) |

---

## 2. 입·출력 명세

### Input (string)
| 필드 | 필수 | 설명 |
|---|---|---|
| `cover_letter` | ✅ | 자기소개서 원문 |
| `resume` | ✅ | 이력서 원문 |
| `portfolio` | ⬜ | 포트폴리오 (옵션, 미입력 시 "없음") |
| `desired_job` | ⬜ | 희망 진로 (확장 요구사항, 미입력 시 서류 기반 추론) |
| `trainee_id`, `trainee_name` | ⬜ | 식별자·이름 |

### Output
1. **구조화 데이터** — 각 단계별 Pydantic 스키마 (백엔드/프론트 렌더링용 JSON)
2. **상담용 마크다운 리포트** — `output/report_{trainee_id}.md`
   - 자기소개서 요약 · 추천 직무/기업 · 포트폴리오 보완 가이드 · 검증 질문 5선

---

## 3. 시스템 아키텍처 (전체)

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (예정)                                                 │
│  · 서류 입력 폼(자소서/이력서/포폴/희망직무)  · 리포트 뷰어      │
└───────────────────────────────┬─────────────────────────────────┘
                                 │ HTTP (JSON)
┌───────────────────────────────▼─────────────────────────────────┐
│  Backend API (예정 — FastAPI 권장)                               │
│  · POST /consult        (단건)   → run_single()                  │
│  · POST /consult/batch  (배치)   → run_batch()                   │
│  · 입력 검증 · 결과 저장 · 인증                                   │
└───────────────────────────────┬─────────────────────────────────┘
                                 │ Python 함수 호출
┌───────────────────────────────▼─────────────────────────────────┐
│  AI Agent Layer  ── crew.py (CrewAI, 현재 구현 완료)             │
│                                                                  │
│   build_inputs() ─► SkalaConsultingCrew().crew().kickoff()       │
│                                                                  │
│   [Sequential Pipeline]                                          │
│   ┌────────────┐  ┌───────────────┐  ┌────────────┐  ┌─────────┐ │
│   │ cv_analyst │─►│ job_trend_    │─►│ hr_        │─►│consulting│ │
│   │ (서류분석) │  │ analyst(시장) │  │ specialist │  │_reporter │ │
│   └────────────┘  └───────┬───────┘  └────────────┘  └─────────┘ │
│         │                 │ context 전달 (앞 결과 → 뒤 입력)     │
│    Pydantic 구조화 출력   │                                      │
└─────────┼─────────────────┼──────────────────────────────────────┘
          │                 │
     ┌────▼─────┐     ┌──────▼──────────────┐
     │ OpenAI   │     │ Serper / Scrape     │
     │ LLM      │     │ (실시간 채용 검색,  │
     │ (litellm)│     │  SERPER_API_KEY 시) │
     └──────────┘     └─────────────────────┘
```

---

## 4. 에이전트 설계 (4-Agent Sequential Pipeline)

기획서의 3개 에이전트에 더해, "output 예쁘게 만들기" 요구사항을 위해
**리포트 에디터(consulting_reporter)** 를 분리했다. (분석 ↔ 표현 관심사 분리)

| # | Agent | 역할 | 입력(context) | 출력 스키마 | 툴 |
|---|---|---|---|---|---|
| 1 | **cv_analyst** | 서류 분석·키워드 추출·요약·숨은강점/공백 진단 | 원본 서류 | `ApplicantProfile` | — |
| 2 | **job_trend_analyst** | 채용시장 조사·산업/기업규모 분포·직무·기업 추천 | ①결과 | `JobMarketReport` | Serper·Scrape |
| 3 | **hr_specialist** | 적합도 매트릭스·점수·갭·포트폴리오 과제·검증질문 5개 | ①②결과 | `HRFitReview` | — |
| 4 | **consulting_reporter** | 상담 흐름 순 마크다운 리포트 편집 | ①②③결과 | 마크다운 파일 | — |

- **Process**: `sequential` — 앞 태스크의 출력이 `context` 로 다음 태스크에 주입된다.
- **데이터 흐름**: 각 에이전트는 원본을 다시 보지 않고 **앞 단계의 구조화 결과**를 근거로 작업 → 환각 억제.

### 에이전트 ↔ 기획서 매핑
| 기획서 에이전트 | 구현 에이전트 |
|---|---|
| cv cover letter summarizer | `cv_analyst` |
| Job trend analyst | `job_trend_analyst` |
| HR Specialist | `hr_specialist` |
| (output 예쁘게 만들기) | `consulting_reporter` ← 신설 |

---

## 5. 적용 프롬프트 기법

상세는 [PROMPT_TECHNIQUES.md](PROMPT_TECHNIQUES.md) 참조. 요약:

| # | 기법 | 적용 위치 |
|---|---|---|
| 1 | Role Prompting | agents.yaml `role`/`backstory` (연차·처리건수·직업윤리 부여) |
| 2 | Constraint Prompting | 전 task `[준수 규칙]` |
| 3 | Chain-of-Thought | 전 task `절차` 블록 ("내부 사고 후 결과만 출력") |
| 4 | Delimiter/XML Tagging | task1 `<자기소개서>…</자기소개서>` |
| 5 | **Schema Enforcement** | 코드의 `output_pydantic` (⚠️ YAML 아님 — 중괄호 KeyError 회피) |
| 6 | Rubric Prompting | task3 적합도 40/30/15/15 루브릭 |
| 7 | Negative Prompting | 상투어·개조식·막연한 권유 금지 |
| 8 | Grounding/Citation | 근거 인용 30자·출처 기재 |
| 9 | Task Decomposition | 4-에이전트 분할 |

---

## 6. 기술 스택

| 계층 | 기술 | 상태 |
|---|---|---|
| AI Orchestration | **CrewAI** (`@CrewBase`, Sequential Process) | ✅ 구현 |
| LLM | OpenAI `gpt-4o-mini` (litellm 경유, `build_llm()`) | ✅ 구현 |
| 구조화 출력 | Pydantic v2 스키마 | ✅ 구현 |
| 실시간 검색 | Serper / ScrapeWebsite (선택, `SERPER_API_KEY`) | ✅ 조건부 |
| 설정 관리 | `.env` + `config/*.yaml` | ✅ 구현 |
| Backend | FastAPI (권장) | ⏳ 예정 |
| Frontend | React / Next.js (권장) | ⏳ 예정 |

---

## 7. 파일 구조

```
skala_career_helper/
├─ crew.py                 # 에이전트·태스크·크루 조립 + 실행 진입점(run_single/run_batch)
├─ config/
│  ├─ agents.yaml          # 4개 에이전트 role/goal/backstory
│  └─ tasks.yaml           # 4개 태스크 description/expected_output
├─ smoke_test.py           # Phase1: LLM 연결 최소 검증
├─ requirements.txt
├─ .env                    # OPENAI_API_KEY / OPENAI_MODEL_NAME (+ SERPER_API_KEY 선택)
├─ output/                 # 생성 리포트(report_*.md) 저장 (자동 생성)
├─ ARCHITECTURE.md         # (본 문서)
├─ PROMPT_TECHNIQUES.md    # 프롬프트 기법 상세
└─ README.md               # 설치·실행·사용법
```

---

## 8. 확장 요구사항 대응

| 요구사항 | 대응 |
|---|---|
| **배치 처리** | `run_batch()` → `kickoff_for_each()`. 프롬프트는 1인 기준 유지, 반복은 실행 레벨 처리 |
| **희망 진로 입력** | `desired_job` 필드. 미입력→서류 기반 추론(`is_inferred=True`) / 입력→1순위 후보 포함 + 정합성(상/중/하) 판정 + 대안 직무 제시 |

---

## 9. 개발 로드맵

1. ✅ **에이전트 정의** — role/goal/backstory, 입력 분석 description, 출력 expected_output
2. ✅ **Mock 입력 데이터** — `crew.py` 의 `MOCK_TRAINEES` (2인: 희망직무 입력/미입력 케이스)
3. 🔄 **모델 실행 검증** — `smoke_test.py`(연결) → `python crew.py`(전체 파이프라인)
4. ⏳ **백엔드 연결** — FastAPI 로 `run_single`/`run_batch` 래핑
5. ⏳ **프론트엔드 연결** — 입력 폼 + 리포트 뷰어
6. ⏳ **배포**
