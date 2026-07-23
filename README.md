# SKALA Career Helper

SKALA 교육생의 **자기소개서·이력서·포트폴리오**를 4개의 AI 에이전트가 순차 분석해,
**자기소개서 요약 → 추천 직무/기업 → 포트폴리오 보완 가이드 → 검증 질문 5선**을
상담용 마크다운 리포트로 만들어 주는 CrewAI 기반 컨설팅 지원 도구입니다.

구조·설계는 [ARCHITECTURE.md](ARCHITECTURE.md), 프롬프트 기법은 [PROMPT_TECHNIQUES.md](PROMPT_TECHNIQUES.md) 참조.

---

## 1. 설치

```powershell
# 프로젝트 루트(llm_code)에서 가상환경 생성 (최초 1회)
cd C:\Users\pds20\Desktop\llm_code
py -m venv .venv
.\.venv\Scripts\Activate.ps1

# 의존성 설치
cd skala_career_helper
pip install -r requirements.txt
```

## 2. 환경 변수 (`.env`)

```env
OPENAI_API_KEY=sk-...            # 필수
OPENAI_MODEL_NAME=openai/gpt-4o-mini   # 필수 (openai/ 접두어 권장)

# 선택 — 실시간 채용공고 검색을 켜려면 (serper.dev 무료 발급)
# 없어도 동작하며, 이 경우 공고 수치는 '데이터 확인 불가'로 표기됩니다.
SERPER_API_KEY=

CREWAI_DISABLE_TELEMETRY=true
OTEL_SDK_DISABLED=true
```

---

## 3. 실행 (3단계 검증)

### Phase 1 — 연결 확인 (가장 먼저)
LLM 키·모델·설치가 정상인지 최소 비용으로 확인합니다.
```powershell
python smoke_test.py
```
→ 콘솔에 `연결 성공` 이 출력되면 통과.

### Phase 2 — 전체 파이프라인 (Mock 데이터)
내장된 교육생 2명(`MOCK_TRAINEES`)으로 4개 에이전트를 순차 실행합니다.
```powershell
python crew.py
```
→ 4단계가 순서대로 실행되고 `output/report_SKALA-2025-014.md` 등이 생성되면 **에이전트 검증 완료**.
> 실시간 검색(`SERPER_API_KEY`) 없이도 돌아갑니다. 실검색을 켜면 `job_trend_analyst`가 실제 채용 데이터를 조사합니다.

### Phase 3 — 내 데이터로 단건/배치 실행
```python
from crew import run_single, run_batch

# 단건
result = run_single({
    "trainee_id": "SKALA-2025-100",
    "trainee_name": "홍길동",
    "desired_job": "데이터 엔지니어",      # 미입력 시 "" → 서류 기반 자동 추론
    "cover_letter": "자기소개서 원문...",
    "resume": "이력서 원문...",
    "portfolio": "포트폴리오 설명...",      # 미입력 시 "" 가능
})
print(result.raw)                          # 최종 리포트(마크다운) 텍스트

# 배치 (여러 명 한 번에)
results = run_batch([trainee_a, trainee_b, ...])
for r in results:
    print(r.raw)
```

---

## 4. 결과 활용

| 산출물 | 위치 | 용도 |
|---|---|---|
| 최종 상담 리포트 | `output/report_{trainee_id}.md` | 매니저가 상담 직전 3분 브리핑 |
| 단계별 구조화 출력 | 각 task 의 `.output.pydantic` | 백엔드 API 응답 / 프론트 렌더링 |

각 단계의 구조화 결과에 직접 접근:
```python
crew = SkalaConsultingCrew()
crew.crew().kickoff(inputs=...)
profile = crew.analyze_documents_task().output.pydantic     # ApplicantProfile
market  = crew.analyze_job_trend_task().output.pydantic     # JobMarketReport
review  = crew.hr_fit_review_task().output.pydantic         # HRFitReview
```

---

## 5. 웹 앱 실행 (백엔드 + 프론트엔드)

`api/`(FastAPI)와 `web/`(React·Vite)이 구현되어 있습니다.
백엔드는 `crew.py` 를 그대로 감싸고, 프론트는 SK 아이덴티티 UI로 입력·리포트를 렌더합니다.
**터미널 2개**를 동시에 띄웁니다.

### ① 백엔드 (FastAPI) — 포트 8001
```powershell
# 레포 루트(skala_career_helper)에서, venv 활성화 상태
cd C:\Users\pds20\Desktop\llm_code\skala_career_helper
..\.venv\Scripts\Activate.ps1          # 이미 활성화됐으면 생략
python -m uvicorn api.main:app --reload --port 8001
```
→ `Uvicorn running on http://127.0.0.1:8001` 이 뜨면 성공.
- API 문서(Swagger): http://localhost:8001/docs
- 엔드포인트: `POST /consult`(단건), `POST /consult/batch`(배치), `GET /health`

### ② 프론트엔드 (React + Vite) — 포트 5173
```powershell
# 새 터미널에서
cd C:\Users\pds20\Desktop\llm_code\skala_career_helper\web
npm install     # 최초 1회
npm run dev
```
→ 브라우저에서 **http://localhost:5173** 접속 → "샘플 채우기" → "컨설팅 리포트 생성".

> ⚠️ 포트 주의: 프론트(`web/vite.config.js`)의 프록시가 **백엔드 8001** 을 바라봅니다.
> 백엔드를 다른 포트로 띄우려면 `vite.config.js` 의 `proxy` 값도 함께 바꿔야 합니다.
> 프론트에서 `http proxy error ... ECONNREFUSED` 가 나면 **백엔드가 8001에 안 떠 있는 것**입니다.

### 응답 형태
```jsonc
POST /consult  →
{
  "trainee_id": "...", "trainee_name": "...",
  "report_markdown": "# SKALA 취업 컨설팅 브리핑 ...",  // 프론트가 렌더하는 최종 리포트
  "profile":   { ... },   // ApplicantProfile (서류 분석)
  "market":    { ... },   // JobMarketReport (채용시장)
  "hr_review": { ... }    // HRFitReview (적합도·질문)
}
```

---

## 6. 트러블슈팅

| 증상 | 원인 / 해결 |
|---|---|
| `OPENAI_API_KEY 가 비어 있습니다` | `.env` 에 실제 키 입력 |
| `KeyError` (태스크 실행 중) | tasks.yaml 본문에 `{}` 중괄호 사용 금지 (placeholder 외). 스키마는 코드의 `output_pydantic` 로만 강제 |
| `config/agents.yaml not found` | `crew.py` 와 같은 폴더에 `config/` 가 있어야 함 |
| job_trend 결과가 '데이터 확인 불가' 뿐 | `SERPER_API_KEY` 미설정 (정상). 실검색이 필요하면 키 등록 |
| 프론트 `http proxy error ... ECONNREFUSED` | 백엔드가 8001에 안 떠 있음 → 백엔드 터미널을 8001로 실행 |
| `error while attempting to bind ... 8000/8001` | 포트를 이미 쓰는 중. 점유 프로세스 종료 또는 다른 포트 사용(+`vite.config.js` 프록시도 변경) |
| rate limit / 비용 | 배치 규모를 줄이거나 모델을 `gpt-4o-mini` 로 유지 |
