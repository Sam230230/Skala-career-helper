"""
Phase 1 스모크 테스트 — 에이전트 로직 이전에 'API 키·모델·CrewAI 설치'만 확인한다.

실행:
    python smoke_test.py

기대 결과:
    콘솔에 '연결 성공' 이라는 짧은 응답이 출력되면 LLM 연결이 정상이다.
    (여기서 실패하면 crew.py 를 돌려도 실패하므로, 문제 범위를 좁힐 수 있다.)
"""
from dotenv import load_dotenv

load_dotenv(override=True)

import os

from crewai import Agent, Crew, Process, Task

from crew import build_llm  # crew.py 의 LLM 설정을 그대로 재사용


def main() -> None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise SystemExit("[실패] .env 의 OPENAI_API_KEY 가 비어 있습니다.")
    print(f"[체크] API Key: {key[:12]}...{key[-4:]}")
    print(f"[체크] MODEL  : {os.getenv('OPENAI_MODEL_NAME')}")
    print(f"[체크] SERPER : {'설정됨(실시간 검색 ON)' if os.getenv('SERPER_API_KEY') else '없음(검색 OFF, 정상)'}")

    tester = Agent(
        role="연결 테스터",
        goal="한 문장으로만 응답한다.",
        backstory="시스템 연결 확인용 최소 에이전트.",
        llm=build_llm(),
        verbose=True,
    )
    task = Task(
        description="'연결 성공' 이라고만 답하라. 다른 말은 하지 마라.",
        expected_output="짧은 한 문장",
        agent=tester,
    )
    result = Crew(agents=[tester], tasks=[task], process=Process.sequential).kickoff()
    print("\n===== 응답 =====")
    print(result.raw)


if __name__ == "__main__":
    main()
