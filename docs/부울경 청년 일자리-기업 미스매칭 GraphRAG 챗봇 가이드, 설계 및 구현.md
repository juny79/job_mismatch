# 부울경 청년 일자리-기업 미스매칭 GraphRAG 챗봇 : 가이드, 설계 및 구현

# [가이드]

### [추천 과제 1] 상세 실행 가이드: 부울경 청년 일자리-기업 미스매칭 GraphRAG 챗봇

이 프로젝트는 2단계의 **GraphRAG(지식그래프)와 지능형 수집 기술을 축소 실증**하는 과제로, 완성 즉시 인터랙티브 데모가 가능하여 정부 지원사업 발표나 지자체 PoC 설득에 가장 효과적입니다.

#### 1. 프로젝트 개요

- **목표:** 부울경 핵심 거점 1개(예: 창원 국가산단 기계/방산 or 부산 센텀 IT/센텀2지구)의 채용 데이터와 청년 구직 선호 데이터를 바탕으로, **어떤 역량과 정주 조건이 결핍되어 청년이 유출되는지**를 AI로 진단하고 맞춤형 대응책을 제시하는 웹 데모 구축.
- **범위 한정:** 부울경 전체가 아닌 **특정 핵심 산단 1~2곳 + 채용 공고 500~1,000건** 규모로 압축.

#### 2. 기술 스택 (단기 개발에 최적화된 조합)

- **데이터 수집/파싱:** Python (`BeautifulSoup`, `Playwright`), 정형 CSV(워크넷 오픈API)
- **지식 추출 & 정제:** `Instructor` / Pydantic 기반 OpenAI 또는 Claude API 구조화 출력
- **데이터베이스:** `Neo4j` (AuraDB 무료 티어 클라우드 활용) + `ChromaDB` (로컬 벡터 DB)
- **RAG 파이프라인:** `LangChain` 또는 `LlamaIndex` (GraphCypherQAChain 활용)
- **프론트엔드/UI:** `Streamlit` + `pyvis` (지식그래프 시각화 라이브러리)

#### 3. 15일 일자별(Day-by-Day) 개발 스프린트

```
[Day 1-4] 데이터 파이프라인 ──► [Day 5-9] GraphRAG 코어 ──► [Day 10-13] Streamlit UI ──► [Day 14-15] 테스트&데모
```

| **일정** | **단계** | **세부 작업 내용** | **주요 마일스톤 및 산출물** |
| --- | --- | --- | --- |
| **Day 1~2** | **데이터 수집 및 정제** | • 워크넷/사람인 공공데이터 API 또는 부울경 소재 기업 채용공고 500건 수집

• 수집 데이터: 회사명, 업종, 소재지(산단), 요구 스킬, 급여, 복지 요건 | `raw_jobs_data.json` 확보 |
| **Day 3~4** | **엔티티 추출 및 정형화** | • LLM(gpt-4o-mini 등)을 활용해 비정형 공고에서 `[기업]`, `[요구기술]`, `[직무분야]`, `[학력/경력]`, `[제공혜택]` JSON 추출 | Pydantic 스키마 기반 정제 데이터 완성 |
| **Day 5~6** | **Neo4j 그래프 모델링** | • Neo4j AuraDB 설정

• 노드(`Company`, `Industry`, `Skill`, `Location`) 및 엣지(`:REQUIRES`, `:LOCATED_IN`, `:OFFERS`) 생성 스크립트 작성 및 적재 | Neo4j 지식그래프 구축 완료 (Node 2,000+ 개) |
| **Day 7~9** | **GraphRAG 질의응답 엔진** | • 자연어를 Cypher 쿼리로 변환하는 `Text2Cypher` 체인 구축

• 벡터 검색(복지/직무설명)과 그래프 쿼리(연관 기술/산단 위치) 결합

• 미스매칭 분석 프롬프트 엔지니어링 | 터미널 기반 다차원 검색 질의 테스트 통과 |
| **Day 10~11** | **Streamlit 대시보드 개발** | • 사용자 질문 입력창 및 답변 인터페이스 구현

• `pyvis` 또는 `streamlit-agraph`를 활용한 연관 기업-스킬 네트워크 시각화 컴포넌트 연동 | 동작 가능한 웹 UI 프로토타입 |
| **Day 12~13** | **진단 및 리포트 기능 추가** | • "특정 산단 내 부족한 청년 친화 일자리 유형 Top 5"

• "기업 요구 스킬 vs 청년 전공자 보유 스킬 갭 리포트" 자동 생성 버튼 추가 | 1-Click 미스매칭 진단 리포트 기능 완성 |
| **Day 14** | **버그 수정 및 튜닝** | • 잘못된 Cypher 쿼리 생성 방지를 위한 Few-shot 프롬프트 보강

• 질의응답 속도 개선 및 예외 처리 | 시스템 안정화 |
| **Day 15** | **데모 시나리오 및 시연 준비** | • 지자체 관계자 또는 투자자 대상 발표용 3분 시연 시나리오 작성

• 예시 질의 5종 준비 (예: *"창원 산단 기계 부품사들이 AI 개발자를 뽑지 못하는 원인은?"*) | **최종 15일 PoC 완료** |

#### 4. 시연 시나리오 예시 (데모 화면 구성)

1. **질문 입력:** *"부산 센텀지구와 창원국가산단의 로봇·자동화 분야에서 공통적으로 요구하는 핵심 기술과 평균 급여 격차는 얼마인가?"*
2. **AI 엔진 동작:**
    - Cypher 쿼리로 두 지역 기업들의 공통 스킬 노드(`ROS`, `Python`, `PLC`, `Computer Vision`)와 평균 급여 노드 집계.
    - 지식그래프를 화면에 렌더링하여 두 지역 기업들이 공유하는 인재 풀의 교집합을 시각화.
3. **AI 답변 출력:**
    - *"창원은 PLC/하드웨어 제어 중심인 반면 센텀은 Vision AI/SW 중심입니다. 소프트웨어 청년 인력이 창원으로 유입되지 않는 주된 원인은 급여 차이(평균 18% 격차)와 원격근무/도심 문화 인프라 부족으로 분석됩니다."*
4. **정책 제언 출력:**
    - *"창원-부산 간 광역 통근 셔틀 지원 및 센텀-창원 공동 R&D 랩 조성을 통한 청년 SW 인력 유입을 권장합니다."*

이 15일짜리 프로젝트를 완수하면, 본 프로젝트에서 다룰 거대 아키텍처(대규모 수집 파이프라인, GraphRAG, UI 연동)의 기술적 타당성을 단기간에 증명할 수 있습니다.

# [설계 및 구현]

15일 단기 프로젝트(**부울경 일자리 미스매칭 GraphRAG**)에 즉시 복사해 사용할 수 있는 **Neo4j 온톨로지 스키마 설계**와 **LangChain 기반 Text2Cypher 파이썬 구현 코드**입니다.

## 1. Neo4j 그래프 모델링 스키마 (Ontology Schema)

채용 공고에서 추출한 정형·비정형 데이터를 바탕으로 기업, 직무, 요구 역량, 정주 여건(복지), 산업단지를 연결하는 핵심 스키마입니다.

```
(IndustrialComplex:산단) ◄─[:LOCATED_IN]─ (Company:기업) ─[:BELONGS_TO]─► (Industry:산업군)
                                              │
                                       [:POSTED_JOB]
                                              ▼
(Benefit:복지/정주조건) ◄─[:OFFERS_BENEFIT]─ (JobPosting:채용공고) ─[:REQUIRES_SKILL]─► (Skill:기술스택)
```

### 1.1 노드(Nodes) 및 속성(Properties) 정의

- **`IndustrialComplex` (산업단지/권역):** `name` (예: 창원국가산단, 센텀시티), `region` (부산, 울산, 경남), `commute_score` (대중교통 접근성 점수)
- **`Industry` (산업군):** `name` (예: 방위산업, 미래차/모빌리티, 해양IT, 스마트기계)
- **`Company` (기업):** `name` (기업명), `size` (중소, 중견, 대기업), `employee_count` (사원수)
- **`JobPosting` (채용공고):** `job_id`, `title` (공고제목), `role_category` (예: AI/SW, 기계설계, 생산관리), `min_salary` (최소연봉, 만원 단위), `experience_level` (신입, 경력, 무관)
- **`Skill` (기술스택):** `name` (예: Python, ROS, PLC, C++, CAD), `type` (SW, HW, 도메인)
- **`Benefit` (복지/정주여건):** `name` (예: 기숙사제공, 주거비지원, 통근버스, 원격근무, 청년내일채움)

## 2. 초기 데이터 적재용 Cypher 쿼리 (샘플 데이터)

Neo4j AuraDB(무료 클라우드) 콘솔이나 파이썬 드라이버에서 실행하여 테스트 그래프를 즉시 생성할 수 있는 쿼리입니다.

Cypher

```
// 1. 제약조건 설정 (중복 방지)
CREATE CONSTRAINT IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (i:IndustrialComplex) REQUIRE i.name IS UNIQUE;

// 2. 산업단지 및 산업군 생성
MERGE (ic1:IndustrialComplex {name: "창원국가산단", region: "경남", commute_score: 65})
MERGE (ic2:IndustrialComplex {name: "부산센텀지구", region: "부산", commute_score: 92})
MERGE (ind1:Industry {name: "스마트방산/기계"})
MERGE (ind2:Industry {name: "피지컬AI/로보틱스"})

// 3. 기업 및 채용공고 데이터 생성 (창원 vs 부산 비교용)
MERGE (comp1:Company {name: "창원정밀기계", size: "중견기업"})
MERGE (comp1)-[:LOCATED_IN]->(ic1)
MERGE (comp1)-[:BELONGS_TO]->(ind1)

MERGE (job1:JobPosting {
  job_id: "CW-001",
  title: "자율주행 방산로봇 제어 엔지니어",
  role_category: "로봇/제어",
  min_salary: 4200,
  experience_level: "신입/경력"
})
MERGE (comp1)-[:POSTED_JOB]->(job1)

MERGE (comp2:Company {name: "센텀비전AI", size: "스타트업"})
MERGE (comp2)-[:LOCATED_IN]->(ic2)
MERGE (comp2)-[:BELONGS_TO]->(ind2)

MERGE (job2:JobPosting {
  job_id: "BS-001",
  title: "로봇 비전 딥러닝 연구원",
  role_category: "AI/SW",
  min_salary: 4000,
  experience_level: "신입"
})
MERGE (comp2)-[:POSTED_JOB]->(job2)

// 4. 요구 기술(Skill) 및 정주 복지(Benefit) 연결
MERGE (s1:Skill {name: "Python", type: "SW"})
MERGE (s2:Skill {name: "ROS2", type: "SW"})
MERGE (s3:Skill {name: "PLC", type: "HW"})
MERGE (s4:Skill {name: "PyTorch", type: "SW"})

MERGE (b1:Benefit {name: "기숙사제공"})
MERGE (b2:Benefit {name: "통근버스"})
MERGE (b3:Benefit {name: "자율출퇴근"})
MERGE (b4:Benefit {name: "원격근무"})

MERGE (job1)-[:REQUIRES_SKILL]->(s1)
MERGE (job1)-[:REQUIRES_SKILL]->(s2)
MERGE (job1)-[:REQUIRES_SKILL]->(s3)
MERGE (job1)-[:OFFERS_BENEFIT]->(b1)
MERGE (job1)-[:OFFERS_BENEFIT]->(b2)

MERGE (job2)-[:REQUIRES_SKILL]->(s1)
MERGE (job2)-[:REQUIRES_SKILL]->(s2)
MERGE (job2)-[:REQUIRES_SKILL]->(s4)
MERGE (job2)-[:OFFERS_BENEFIT]->(b3)
MERGE (job2)-[:OFFERS_BENEFIT]->(b4);
```

## 3. 파이썬 구현 코드 (데이터 추출 + Text2Cypher QA)

### 3.1 필수 패키지 설치

Bash

```
pip install langchain langchain-openai langchain-neo4j neo4j pydantic
```

### 3.2 Step 1: 비정형 채용공고에서 그래프 엔티티 자동 추출 (`extractor.py`)

크롤링한 채용공고 텍스트를 Neo4j에 넣기 위해 Pydantic으로 구조화하는 코드입니다.

Python

```
import os
from typing import List
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

# 1. 추출할 데이터 스키마 정의
class JobGraphData(BaseModel):
    company_name: str = Field(description="기업명")
    company_size: str = Field(description="기업 규모 (대기업/중견기업/중소기업/스타트업)")
    industrial_complex: str = Field(description="소재 산업단지 또는 지역권역 (예: 창원국가산단, 부산센텀지구, 울산미포산단)")
    region: str = Field(description="시/도 (부산, 울산, 경남 중 택1)")
    industry: str = Field(description="주력 산업 분야")
    job_title: str = Field(description="채용 공고 제목")
    role_category: str = Field(description="직무 카테고리 (AI/SW, 기계설계, 전장제어, 생산품질 등)")
    min_salary: int = Field(description="최소 연봉 (만원 단위 정수, 언급 없을 시 3500 기본값)")
    required_skills: List[str] = Field(description="요구 기술 스택 리스트 (예: Python, CAD, PLC, C++)")
    benefits: List[str] = Field(description="제공 복지 및 정주 여건 (예: 기숙사제공, 주거비지원, 통근버스, 유연근무)")

# 2. LLM 기반 구조화 추출기 초기화
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
structured_llm = llm.with_structured_output(JobGraphData)

# 테스트 실행 예시
raw_posting = """
[채용] (주)케이방산테크에서 스마트팩토리 및 로봇 제어 신입 연구원을 모십니다.
근무지: 경남 창원시 성산구 (창원국가산단 내)
자격요건: Python, ROS 경험자 우대, PLC 제어 가능자 필수
급여: 연봉 4,300만원 이상
복지: 타지역 거주자 사내기숙사 무상 제공, 창원/김해/부산 주요 거점 통근버스 운행
"""

extracted_data = structured_llm.invoke(raw_posting)
print(extracted_data.model_dump_json(indent=2))
```

### 3.3 Step 2: LangChain 기반 Text2Cypher 미스매칭 분석 엔진 (`graph_rag.py`)

사용자의 자연어 질문을 Cypher 쿼리로 변환해 Neo4j를 조회한 뒤, 부울경 일자리 미스매칭 관점의 정책 인사이트를 답변하는 메인 코드입니다.

Python

```
import os
from langchain_neo4j import Neo4jGraph, GraphCypherQAChain
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# 환경변수 설정
os.environ["OPENAI_API_KEY"] = "YOUR_OPENAI_API_KEY"
os.environ["NEO4J_URI"] = "bolt://localhost:7687" # 또는 neo4j+s://xxx.databases.neo4j.io
os.environ["NEO4J_USERNAME"] = "neo4j"
os.environ["NEO4J_PASSWORD"] = "your_password"

# 1. Neo4j 그래프 연결 및 스키마 자동 로드
graph = Neo4jGraph(enhanced_schema=True)
graph.refresh_schema()

# 2. Text2Cypher 생성용 Few-Shot 프롬프트 (쿼리 정확도 향상 핵심)
CYPHER_GENERATION_TEMPLATE = """
당신은 Neo4j Cypher 쿼리를 작성하는 전문가입니다.
주어진 그래프 스키마만을 사용하여 사용자의 질문에 답하기 위한 Cypher 쿼리를 작성하세요.

[스키마 정보]
{schema}

[작성 규칙]
1. 문자열 비교 시 대소문자를 구분하지 않도록 `toLower()` 또는 `CONTAINS`를 적극 활용하세요.
2. 존재하지 않는 관계나 프로퍼티를 임의로 만들지 마세요.
3. 오직 실행 가능한 Cypher 쿼리만 출력하고 설명이나 마크다운 백틱(```)은 제외하세요.

[Few-Shot 예시]
질문: 창원과 부산 지역 채용공고에서 공통으로 요구하는 기술은 무엇인가요?
Cypher:
MATCH (ic1:IndustrialComplex {region: "경남"})<-[:LOCATED_IN]-(:Company)-[:POSTED_JOB]->(:JobPosting)-[:REQUIRES_SKILL]->(s:Skill)
MATCH (ic2:IndustrialComplex {region: "부산"})<-[:LOCATED_IN]-(:Company)-[:POSTED_JOB]->(:JobPosting)-[:REQUIRES_SKILL]->(s)
RETURN DISTINCT s.name AS common_skill

질문: 각 산업단지별 평균 최소 연봉과 제공하는 주요 복지 혜택을 알려주세요.
Cypher:
MATCH (ic:IndustrialComplex)<-[:LOCATED_IN]-(c:Company)-[:POSTED_JOB]->(j:JobPosting)
OPTIONAL MATCH (j)-[:OFFERS_BENEFIT]->(b:Benefit)
RETURN ic.name AS complex, ic.region AS region, avg(j.min_salary) AS avg_salary, collect(DISTINCT b.name) AS benefits

질문: {question}
Cypher:"""

cypher_prompt = PromptTemplate(
    input_variables=["schema", "question"],
    template=CYPHER_GENERATION_TEMPLATE
)

# 3. 최종 답변 생성용 프롬프트 (미스매칭 분석가 페르소나 부여)
QA_TEMPLATE = """
당신은 부울경(부산·울산·경남) 초광역 일자리 및 산업 생태계 분석 AI입니다.
Neo4j 데이터베이스에서 조회된 [검색 결과]를 바탕으로 사용자의 질문에 답변하세요.

단순 수치 나열에 그치지 말고 다음을 포함해 분석하세요:
1. 데이터 기반 현황 요약 (기업, 연봉, 요구 스킬, 복지 차이)
2. 청년 인재 미스매칭 원인 진단 (왜 청년들이 지원하지 않거나 이탈하는지)
3. 지자체 및 기업을 위한 단기 정책/채용 개선 제언

[질문]
{question}

[검색 결과]
{context}

답변:"""

qa_prompt = PromptTemplate(
    input_variables=["context", "question"],
    template=QA_TEMPLATE
)

# 4. GraphCypherQAChain 조립
llm = ChatOpenAI(model="gpt-4o", temperature=0)

chain = GraphCypherQAChain.from_llm(
    llm=llm,
    graph=graph,
    verbose=True, # 터미널에서 생성된 Cypher 쿼리 확인 가능
    cypher_prompt=cypher_prompt,
    qa_prompt=qa_prompt,
    allow_dangerous_requests=True,
    return_intermediate_steps=True # UI에서 생성된 쿼리를 보여주기 위해 활성화
)

# 5. 실행 테스트
if __name__ == "__main__":
    question = "창원국가산단과 부산센텀지구의 로봇/AI 관련 공고를 비교했을 때 요구 스킬과 연봉, 정주 복지 차이는 어떠하며 청년 유입을 위해 무엇을 보완해야 할까?"

    response = chain.invoke({"query": question})

    print("\n[생성된 Cypher 쿼리]:")
    print(response["intermediate_steps"][0]["query"])

    print("\n[AI 분석 리포트]:")
    print(response["result"])
```

## 4. 15일 프로젝트 성공을 위한 실전 팁

- **스킬명 정규화(Normalization):** 채용공고마다 `"파이썬"`, `"Python"`, `"python3"`처럼 표기가 다릅니다. DB 적재 전 사전(Dictionary) 매핑이나 임베딩 유사도를 통해 `"Python"`이라는 단일 노드로 병합(`MERGE`)해야 그래프 연결성이 극대화됩니다.
- **하이브리드 검색 보강:** 만약 특정 질문에서 Text2Cypher가 빈 결과(`[]`)를 반환할 경우를 대비해, `JobPosting` 노드에 채용공고 원문 임베딩(`vector index`)을 함께 넣어두면 쿼리 실패 시 벡터 검색으로 Fallback 처리하여 데모 시연 중 에러를 완벽히 방지할 수 있습니다.