import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// 빠른 테스트용 샘플(백엔드 MOCK_TRAINEES 와 동일 인물)
const SAMPLE = {
  trainee_id: 'SKALA-2025-014',
  trainee_name: '김지훈',
  desired_job: '백엔드 개발자',
  cover_letter:
    '저는 기계공학을 전공했지만 3학년 때 참여한 스마트팩토리 캡스톤 과제에서 설비 센서 데이터를 ' +
    '수집·처리하는 파트를 맡으며 소프트웨어에 관심을 갖게 되었습니다. 엑셀로 수기 집계하던 불량 데이터를 ' +
    'Python 스크립트로 자동화해 주간 집계 작업 시간을 4시간에서 20분으로 줄였습니다. 이 경험을 계기로 ' +
    'SKALA 과정에 지원했고 Java와 Spring Boot 기반 백엔드 개발을 집중 학습했습니다. 팀 프로젝트에서는 ' +
    '5명 팀의 API 설계를 담당하며 REST 규칙을 문서화해 프론트와의 재작업을 줄였습니다.',
  resume:
    '[학력] OO대학교 기계공학과 졸업 (2025.02), 학점 3.7/4.5\n' +
    '[교육] SKALA 2기 수료 예정, Java/Spring Boot/JPA/AWS\n' +
    '[프로젝트] 1) 설비 이상탐지 대시보드 - 팀4, Python/Pandas/InfluxDB, 불량 집계 자동화로 작업시간 92% 단축\n' +
    '2) 중고거래 플랫폼 API 서버 - 팀5, API 설계/인증, Java/Spring Boot/JPA/MySQL/Redis, 조회 320ms→110ms\n' +
    '[자격] 정보처리기사, SQLD, TOEIC 820',
  portfolio: 'GitHub: 중고거래 API 서버 리포지토리(ERD·API 명세 포함), AWS EC2 배포, Swagger 문서화.',
}

const EMPTY = {
  trainee_id: '',
  trainee_name: '',
  desired_job: '',
  cover_letter: '',
  resume: '',
  portfolio: '',
}

const STAGES = [
  '서류 분석가가 키워드와 강점을 추출하고 있어요',
  '채용 트렌드 분석가가 직무·기업을 조사하고 있어요',
  '인사담당자가 적합도와 검증 질문을 설계하고 있어요',
  '리포트 에디터가 상담 문서를 편집하고 있어요',
]

export default function App() {
  const [form, setForm] = useState(EMPTY)
  const [loading, setLoading] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const timerRef = useRef(null)

  useEffect(() => {
    if (loading) {
      setElapsed(0)
      timerRef.current = setInterval(() => setElapsed((e) => e + 1), 1000)
    } else {
      clearInterval(timerRef.current)
    }
    return () => clearInterval(timerRef.current)
  }, [loading])

  const update = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault()
    setError('')
    setResult(null)
    setLoading(true)
    try {
      const res = await fetch('/consult', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `요청 실패 (${res.status})`)
      }
      setResult(await res.json())
    } catch (err) {
      setError(err.message || '알 수 없는 오류가 발생했습니다.')
    } finally {
      setLoading(false)
    }
  }

  const stageIdx = Math.min(Math.floor(elapsed / 12), STAGES.length - 1)
  const score = result?.hr_review?.total_score
  const topJob = result?.market?.recommended_jobs?.[0]?.job_title

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo">SKALA</span>
          <span className="brand-sub">Career Helper</span>
        </div>
        <div className="brand-tag">AI 기반 취업 컨설팅 지원 플랫폼 · SK AX</div>
      </header>

      <main className="layout">
        {/* 입력 폼 */}
        <section className="panel form-panel">
          <div className="panel-head">
            <h2>교육생 서류 입력</h2>
            <div className="panel-actions">
              <button type="button" className="ghost" onClick={() => setForm(SAMPLE)}>
                샘플 채우기
              </button>
              <button type="button" className="ghost" onClick={() => setForm(EMPTY)}>
                초기화
              </button>
            </div>
          </div>

          <form onSubmit={submit}>
            <div className="row2">
              <label>
                이름
                <input value={form.trainee_name} onChange={update('trainee_name')} placeholder="홍길동" />
              </label>
              <label>
                식별자
                <input value={form.trainee_id} onChange={update('trainee_id')} placeholder="SKALA-2025-000" />
              </label>
            </div>

            <label>
              희망 진로 <span className="opt">선택 · 미입력 시 서류 기반 자동 추론</span>
              <input value={form.desired_job} onChange={update('desired_job')} placeholder="예: 백엔드 개발자" />
            </label>

            <label>
              자기소개서 <span className="req">필수</span>
              <textarea rows={7} value={form.cover_letter} onChange={update('cover_letter')} placeholder="자기소개서 원문을 붙여넣으세요." />
            </label>

            <label>
              이력서 <span className="req">필수</span>
              <textarea rows={6} value={form.resume} onChange={update('resume')} placeholder="학력·경력·프로젝트·자격증 등" />
            </label>

            <label>
              포트폴리오 <span className="opt">선택</span>
              <textarea rows={3} value={form.portfolio} onChange={update('portfolio')} placeholder="GitHub, 배포 URL, 산출물 설명 등" />
            </label>

            <button type="submit" className="primary" disabled={loading || !form.cover_letter || !form.resume}>
              {loading ? '분석 중…' : '컨설팅 리포트 생성'}
            </button>
          </form>
        </section>

        {/* 결과 */}
        <section className="panel result-panel">
          {!result && !loading && !error && (
            <div className="placeholder">
              <div className="ph-mark">SKALA</div>
              <p>좌측에 서류를 입력하고 <b>리포트 생성</b>을 누르면<br />4개의 AI 에이전트가 상담 리포트를 만들어 드립니다.</p>
            </div>
          )}

          {loading && (
            <div className="loading">
              <div className="spinner" />
              <p className="stage">{STAGES[stageIdx]}</p>
              <p className="elapsed">경과 {elapsed}초 · 보통 30~90초 소요됩니다</p>
              <div className="steps">
                {STAGES.map((_, i) => (
                  <span key={i} className={`dot ${i <= stageIdx ? 'on' : ''}`} />
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="error">
              <b>오류</b>
              <p>{error}</p>
              <small>백엔드 서버(8000)가 켜져 있는지, .env 의 API 키가 유효한지 확인하세요.</small>
            </div>
          )}

          {result && (
            <>
              <div className="summary">
                {topJob && (
                  <div className="chip">
                    <span className="chip-label">1순위 추천 직무</span>
                    <span className="chip-value">{topJob}</span>
                  </div>
                )}
                {typeof score === 'number' && (
                  <div className="chip score">
                    <span className="chip-label">적합도 점수</span>
                    <span className="chip-value">{score}<small>/100</small></span>
                  </div>
                )}
                <div className="chip">
                  <span className="chip-label">대상</span>
                  <span className="chip-value">{result.trainee_name}</span>
                </div>
              </div>
              <article className="report">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.report_markdown}</ReactMarkdown>
              </article>
            </>
          )}
        </section>
      </main>

      <footer className="footer">SKALA · SK AX 교육 프로젝트 · 로컬 MVP</footer>
    </div>
  )
}
