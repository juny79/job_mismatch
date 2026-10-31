# 부울경 청년 일자리-기업 미스매칭 GraphRAG PoC

15영업일 PoC의 아키텍처와 실행 기준은 다음 문서를 참조하세요.

- [01. 아키텍처 초안](docs/01_GraphRAG_프로젝트_아키텍처_초안.md)
- [02. 15일 실행계획·핵심 산출물·완료 기준](docs/02_PoC_15일_실행계획.md)
- [03. 데이터 확보 및 품질 관리](docs/03_데이터_확보_및_품질관리.md)
- [04. G0/G1 범위·출처 승인 결정 가이드](docs/04_G0_G1_결정가이드.md)
- [05. G0/G1 작업 기준 및 G2 착수안](docs/05_G0_G1_작업기준_및_G2_착수.md)
- [06. G1 공식 출처 후보 1차 검토](docs/06_G1_공식출처_후보_검토.md)
- [07. 통합 흐름 및 로컬 GraphRAG 데모](docs/07_통합흐름_로컬_GraphRAG_데모.md)
- [08. G0 분석 범위 결정안 (승인 완료)](docs/08_G0_범위_결정안.md)
- [09. G2 소량 파일럿 착수안 (실행 차단: 출처별 G1 대기)](docs/09_G2_소량_파일럿_착수안.md)
- [10. 한국고용정보원 이용조건 확인 요청안](docs/10_G1_한국고용정보원_이용조건_확인요청안.md)
- [11. 로컬 웹 UI MVP 및 실행 가이드](docs/11_웹_UI_MVP_실행가이드.md)
- [12. GraphRAG 기능 구현 및 의존 정보 계획](docs/12_GraphRAG_기능구현_단계계획.md)
- [13. 근거 기반 일자리 추천 시스템 전환·통합 업그레이드 계획](docs/13_recommendation_upgrade_plan.md)
- 종합계획서: `docs/부울경 청년 일자리-기업 미스매칭 GraphRAG 챗봇 종합계획서.md`

## 문서 번호 규칙

프로젝트 진행 단계에서 새로 생성되는 문서·보고서·결정 기록은 `docs/`에서 `03_`, `04_`처럼 두 자리 순번을 앞에 붙여 생성합니다. `01_`과 `02_` 문서를 현재 기준본으로 사용하고, 기존에 참조되던 번호 없는 아키텍처·PoC 파일은 구버전 보관본입니다. 종합계획서와 참고 가이드는 원본 문서이므로 기존 이름을 유지합니다. 코드와 데이터 파일은 import·도구 호환성을 위해 경로/형식별 이름을 유지하고, 순번은 단계별 산출물 문서에 적용합니다. 새 산출물을 만들 때는 다음 사용 가능 번호를 확인하고 README의 목차도 갱신합니다.

## 현재 구현 범위

현재는 Python 표준 라이브러리 기반의 로컬 스캐폴드입니다. 출처 승인 레지스트리 검증, 합성 데이터 사용의 명시적 opt-in, JSONL 데이터 계약·검수, 검수 완료 레코드만의 검색, 근거·출처를 포함한 CLI 결과와 품질 요약을 제공합니다. 웹 UI는 키워드·그래프·설명 가능한 lexical+graph 하이브리드 검색 기준선을 제공합니다. 하이브리드는 임베딩이나 LLM이 아닌 휴리스틱 순위화이며, 점수는 평가 전 기준선입니다. 세부 흐름은 [07 문서](docs/07_통합흐름_로컬_GraphRAG_데모.md), [11 웹 UI 가이드](docs/11_웹_UI_MVP_실행가이드.md), [12 GraphRAG 구현 계획](docs/12_GraphRAG_기능구현_단계계획.md)을 참조하세요. 최종 목표를 근거 기반 일자리 추천 시스템으로 확장하는 제안은 [13 통합 업그레이드 계획](docs/13_recommendation_upgrade_plan.md)을 참조하세요. 이 목표 전환은 제안 단계이며, 추천 기능이나 출처 승인이 완료됐다는 뜻은 아닙니다. 실제 출처 API·Neo4j·벡터 DB·LLM·운영 배포용 인증/권한 관리는 연결되어 있지 않습니다. `data/demo_jobs.jsonl`은 합성 데모 자료이며 실제 채용시장 결과로 해석하면 안 됩니다.

## 실행

저장소 루트에서:

```bash README.md
python -m src.app.cli --data data/demo_jobs.jsonl --allow-synthetic --query Python
python -m src.app.cli --data data/demo_jobs.jsonl --allow-synthetic --graph --query Python --region 부산
python -m src.app.web --data data/demo_jobs.jsonl --allow-synthetic --host 127.0.0.1 --port 8000
python -m src.app.evaluate --data data/demo_jobs.jsonl --allow-synthetic --cases data/retrieval_eval_synthetic.json --k 5
python -m unittest discover -s tests -v
```

실제 데이터를 입력할 때는 승인된 출처만 `data/source_registry_template.csv` 형식으로 등록하고 `--source-registry`로 전달해야 합니다. 허가되지 않은 출처는 적재되지 않습니다. 실제 데이터를 입력하기 전에 출처의 이용 조건, 관측 범위, 스키마와 검수 기준을 승인해야 합니다. 레코드 필드는 `src/domain/models.py`와 `src/domain/validation.py`를 기준으로 하며, 각 JSONL 행은 하나의 JSON 객체입니다.
