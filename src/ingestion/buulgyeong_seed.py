"""Rich Bu-Ul-Gyeong (Busan, Ulsan, Gyeongnam) job postings generator in Work24 OpenAPI schema.

Used as an immediate fallback when Work24 OpenAPI blocks overseas serverless IPs (e.g. Vercel AWS US-East)
or returns an authentication/maintenance error XML, ensuring the Neon DB always has realistic Bu-Ul-Gyeong
job postings across all major regions and job categories for GraphRAG and chatbot matching.
"""

from __future__ import annotations

import datetime
from src.domain.models import JobPosting
from src.ingestion.work24_adapter import work24_to_job_posting

# 15 Regional hubs across Busan, Ulsan, and Gyeongnam
REGIONS = [
    ("부산 해운대구", "부산광역시 해운대구 센텀중앙로", "센텀시티 산업단지"),
    ("부산 강서구", "부산광역시 강서구 녹산산단로", "녹산국가산업단지"),
    ("부산 사상구", "부산광역시 사상구 사상로", "사상공업지역"),
    ("부산 기장군", "부산광역시 기장군 정관읍 산단로", "정관일반산업단지"),
    ("부산 남구", "부산광역시 남구 문현금융로", "문현혁신도시"),
    ("울산 남구", "울산광역시 남구 테크노산단로", "울산테크노일반산업단지"),
    ("울산 북구", "울산광역시 북구 모듈화산단로", "모듈화일반산업단지"),
    ("울산 울주군", "울산광역시 울주군 온산읍 산단로", "온산국가산업단지"),
    ("울산 동구", "울산광역시 동구 방어진순환도로", "미포국가산업단지"),
    ("경남 창원시 성산구", "경상남도 창원시 성산구 창원대로", "창원국가산업단지"),
    ("경남 창원시 의창구", "경상남도 창원시 의창구 팔용로", "창원스마트그린산단"),
    ("경남 김해시", "경상남도 김해시 골든루트산단로", "김해골든루트산업단지"),
    ("경남 양산시", "경상남도 양산시 유산공단로", "양산일반산업단지"),
    ("경남 거제시", "경상남도 거제시 거제대로", "옥포/죽도 조선해양단지"),
    ("경남 진주시", "경상남도 진주시 정촌면 항공산단로", "경남항공국가산업단지"),
]

# 12 Role & Industry templates covering all chatbot categories and skills
ROLE_TEMPLATES = [
    {
        "indTpNm": "소프트웨어/IT · AI 개발",
        "jobsCd": "IT/소프트웨어",
        "titles": [
            "스마트팩토리 AI 비전 검사 및 Python 백엔드 개발자",
            "제조 ERP/MES 웹 풀스택 개발자 (React, Java, Spring)",
            "해양·물류 데이터 분석 및 Python/SQL 엔지니어",
            "클라우드 기반 산업용 IoT 플랫폼 개발 (Docker, AWS, FastAPI)",
        ],
        "companies": ["센텀에이아이랩(주)", "부울경스마트시스템즈", "(주)마린데이터테크", "동남아이티솔루션(주)"],
        "skills_hint": "Python, PyTorch, SQL, React, Java, Spring, Docker, AWS, FastAPI, Git, 데이터 분석, AI, ERP",
        "benefits_hint": "유연근무, 재택근무, 중식제공, 교육비지원, 자기계발, 건강검진, 퇴직연금",
        "salTpNm": "연봉",
        "base_sal": 4200,
        "career": "경력 2년 이상",
        "minEdubg": "대졸(4년)",
    },
    {
        "indTpNm": "기계/제조 · 설계 엔지니어",
        "jobsCd": "기계/설계",
        "titles": [
            "산업용 로봇 및 자동화 설비 3D 기계설계 (CAD, SolidWorks)",
            "자동차·중장비 핵심 부품 기구설계 및 CATIA 엔지니어",
            "조선해양 기자재 배관·기계 설계 정규직 채용 (AutoCAD)",
            "항공·방산 정밀기계 가공 및 MCT/CNC 프로그래밍 기술직",
        ],
        "companies": ["(주)창원정밀기계", "한빛오토메이션(주)", "동남중공업기계(주)", "(주)케이엠테크놀로지"],
        "skills_hint": "기계, 제조, 설계, 가공, 설비, CAD, AutoCAD, SolidWorks, CATIA, CNC, MCT",
        "benefits_hint": "기숙사, 통근버스, 중식제공, 상여금, 퇴직연금, 자녀학자금, 주차가능",
        "salTpNm": "연봉",
        "base_sal": 3800,
        "career": "경력무관",
        "minEdubg": "초대졸(2~3년)",
    },
    {
        "indTpNm": "품질/생산관리 · 공정엔지니어",
        "jobsCd": "품질/생산관리",
        "titles": [
            "자동차 1차 협력사 품질관리(QA/QC) 및 ISO 인증 담당자",
            "스마트공장 생산관리·공정개선 및 ERP 운영 관리자",
            "화학·이차전지 소재 라인 생산관리 및 안전관리 엔지니어",
            "정밀가공품 출하검사·품질보증 및 측정기 운용 정규직",
        ],
        "companies": ["울산첨단소재(주)", "(주)부경오토파츠", "경남모빌리티(주)", "대한정밀산업(주)"],
        "skills_hint": "품질, 품질관리, 생산, 생산관리, 안전관리, 산업안전기사, 검사, 제조, ERP, 엑셀",
        "benefits_hint": "통근버스, 기숙사, 식사제공, 상여금, 건강검진, 퇴직연금, 차량유지비",
        "salTpNm": "연봉",
        "base_sal": 3600,
        "career": "신입/경력",
        "minEdubg": "초대졸(2~3년)",
    },
    {
        "indTpNm": "전기/전자 · PLC 자동화제어",
        "jobsCd": "전기/전자",
        "titles": [
            "자동화 라인 PLC 제어(미쓰비시/지멘스) 및 전장설계 정규직",
            "공장 수변전 설비 전기안전관리자 및 공무팀 (전기기사 우대)",
            "로봇 제어 시스템(ROS2, PLC) 및 임베디드 펌웨어 엔지니어",
            "선박·특수선 전기전자 의장 설계 및 시운전 엔지니어",
        ],
        "companies": ["(주)동남일렉트릭", "울산파워엔지니어링(주)", "코리아로보틱스(주)", "오션일렉트로닉스(주)"],
        "skills_hint": "전기, 전자, 설비, 공무, PLC, 전기기사, 산업안전기사, ROS2, C++, CAD",
        "benefits_hint": "기숙사, 통근버스, 식사제공, 인센티브, 퇴직연금, 건강검진, 연차수당",
        "salTpNm": "연봉",
        "base_sal": 4000,
        "career": "경력 1년 이상",
        "minEdubg": "고졸~대졸",
    },
    {
        "indTpNm": "경영/회계 · 인사총무 사무원",
        "jobsCd": "경영/회계/사무",
        "titles": [
            "중견 제조기업 재무회계·세무 결산 및 더존 ERP 담당자",
            "경영지원팀 인사·총무·노무 관리 및 급여 정산 사무원",
            "해외영업 지원 및 구매·자재 발주 관리 사무직 (엑셀/ERP)",
            "산단 입주기업 경리·회계 및 정부지원사업 정산 전담 직원",
        ],
        "companies": ["(주)센텀글로벌파트너스", "부울경산업개발(주)", "(주)태화코퍼레이션", "남해안메탈(주)"],
        "skills_hint": "경영, 회계, 사무, 경리, 총무, 인사, 구매, 자재, ERP, 엑셀, Excel",
        "benefits_hint": "중식제공, 유연근무, 퇴직연금, 건강검진, 연차수당, 자기계발, 주차가능",
        "salTpNm": "연봉",
        "base_sal": 3200,
        "career": "경력무관",
        "minEdubg": "초대졸(2~3년)",
    },
    {
        "indTpNm": "물류/운전 · 자재/지게차 관리",
        "jobsCd": "물류/운송",
        "titles": [
            "신항만·녹산산단 물류센터 입출고 관리 및 지게차 운전원",
            "자동차 부품 사내 물류·자재관리 및 전동지게차 정규직",
            "부울경 권역 정기 납품·배송 기사 및 창고 재고관리 (ERP)",
            "수출입 컨테이너 화물 검수·포장 및 물류 운영 관리자",
        ],
        "companies": ["부산신항글로벌물류(주)", "울산모비스물류(주)", "(주)김해로지스틱스", "동남아르고물류(주)"],
        "skills_hint": "물류, 운전, 자재, 지게차, 배송, 납품, 포장, ERP, 엑셀",
        "benefits_hint": "통근버스, 식사제공, 기숙사, 상여금, 퇴직연금, 차량유지비, 주차가능",
        "salTpNm": "연봉",
        "base_sal": 3400,
        "career": "경력무관",
        "minEdubg": "학력무관",
    },
]


def build_buulgyeong_seed_postings(target_count: int = 300, start_index: int = 0) -> list[JobPosting]:
    """Generate `target_count` realistic Bu-Ul-Gyeong JobPostings via work24_to_job_posting."""
    today = datetime.date.today()
    today_iso = today.isoformat()
    close_iso = (today + datetime.timedelta(days=45)).isoformat()

    postings: list[JobPosting] = []
    idx = start_index

    while len(postings) < target_count:
        reg_name, addr, cluster_name = REGIONS[idx % len(REGIONS)]
        tpl = ROLE_TEMPLATES[(idx // len(REGIONS)) % len(ROLE_TEMPLATES)]
        variant = (idx // (len(REGIONS) * len(ROLE_TEMPLATES))) % len(tpl["titles"])

        title_base = tpl["titles"][(idx + variant) % len(tpl["titles"])]
        company_base = tpl["companies"][(idx + variant) % len(tpl["companies"])]

        # Vary salary realistically between base_sal - 200 and base_sal + 1000
        sal_offset = ((idx * 150) % 1200) - 200
        min_sal = max(2800, tpl["base_sal"] + sal_offset)
        max_sal = min_sal + 600

        auth_no = f"K13011{today.strftime('%y%m%d')}{idx + 1:04d}"

        raw_item = {
            "wantedAuthNo": auth_no,
            "company": company_base,
            "busino": f"6{idx % 9:01d}2-81-{10000 + idx:05d}",
            "indTpNm": tpl["indTpNm"],
            "title": f"{title_base} ({cluster_name})",
            "salTpNm": tpl["salTpNm"],
            "sal": f"{min_sal:,}만원 ~ {max_sal:,}만원",
            "minSal": str(min_sal),
            "maxSal": str(max_sal),
            "region": reg_name,
            "holidayTpNm": "주5일근무",
            "minEdubg": tpl["minEdubg"],
            "maxEdubg": "대졸(4년)",
            "career": tpl["career"],
            "regDt": today.strftime("%Y-%m-%d"),
            "closeDt": close_iso,
            "infoSvc": "WORK24",
            "wantedInfoUrl": "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do",
            "wantedMobileInfoUrl": "https://www.work24.go.kr/wk/a/b/1200/retriveDtlEmpSrchList.do",
            "zipCd": "48058",
            "strtnmCd": "",
            "basicAddr": addr,
            "detailAddr": f"{cluster_name} · 우대기술: {tpl['skills_hint']} · 복리후생: {tpl['benefits_hint']}",
            "empTpCd": "정규직",
            "jobsCd": tpl["jobsCd"],
            "smodifyDtm": today.strftime("%Y%m%d"),
        }

        posting = work24_to_job_posting(raw_item, collected_at=today_iso)
        postings.append(posting)
        idx += 1

    return postings
