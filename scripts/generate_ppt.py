"""Generate a 16:9 widescreen PowerPoint presentation (.pptx) for the Bu-Ul-Gyeong Job Mismatch AI project."""

from __future__ import annotations

from pathlib import Path
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

# Color Palette
C_DARK_BG = RGBColor(15, 41, 34)       # #0F2922 (Deep Forest Green)
C_BRAND = RGBColor(19, 92, 67)         # #135C43 (Brand Green)
C_BRAND_SOFT = RGBColor(232, 243, 238) # #E8F3EE (Soft Mint)
C_ACCENT = RGBColor(212, 236, 104)     # #D4EC68 (Lime Accent)
C_LIGHT_BG = RGBColor(244, 247, 246)   # #F4F7F6 (Slide Background)
C_WHITE = RGBColor(255, 255, 255)
C_INK = RGBColor(17, 34, 29)           # #11221D (Primary Dark Text)
C_MUTED = RGBColor(100, 119, 112)      # #647770 (Secondary Text)
C_LINE = RGBColor(210, 222, 216)
C_BLUE_BG = RGBColor(239, 246, 255)
C_BLUE_INK = RGBColor(29, 78, 216)
C_PURPLE_BG = RGBColor(245, 243, 255)
C_PURPLE_INK = RGBColor(109, 40, 217)
C_WARN_BG = RGBColor(254, 243, 199)
C_WARN_INK = RGBColor(180, 83, 9)

FONT_NAME = "맑은 고딕"


def set_slide_bg(slide, color: RGBColor) -> None:
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = color
    bg.line.fill.background()


def add_header(slide, step_badge: str, title: str, subtitle: str) -> None:
    # Top bar
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(1.25))
    bar.fill.solid()
    bar.fill.fore_color.rgb = C_DARK_BG
    bar.line.fill.background()

    # Step pill badge
    pill = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.6), Inches(0.28), Inches(2.2), Inches(0.36))
    pill.fill.solid()
    pill.fill.fore_color.rgb = C_BRAND
    pill.line.color.rgb = C_ACCENT
    pill.line.width = Pt(1)
    tf_p = pill.text_frame
    tf_p.word_wrap = False
    tf_p.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf_p.paragraphs[0]
    p.text = step_badge
    p.alignment = PP_ALIGN.CENTER
    p.font.name = FONT_NAME
    p.font.size = Pt(11)
    p.font.bold = True
    p.font.color.rgb = C_ACCENT

    # Title & Subtitle
    tb = slide.shapes.add_textbox(Inches(0.6), Inches(0.66), Inches(12.0), Inches(0.5))
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    r1 = p.add_run()
    r1.text = title + "   "
    r1.font.name = FONT_NAME
    r1.font.size = Pt(22)
    r1.font.bold = True
    r1.font.color.rgb = C_WHITE

    r2 = p.add_run()
    r2.text = subtitle
    r2.font.name = FONT_NAME
    r2.font.size = Pt(13)
    r2.font.color.rgb = RGBColor(163, 194, 183)


def add_card(
    slide,
    left: float,
    top: float,
    width: float,
    height: float,
    title: str,
    bullets: list[str],
    *,
    header_bg: RGBColor = C_BRAND_SOFT,
    header_fg: RGBColor = C_BRAND,
    card_bg: RGBColor = C_WHITE,
    border_color: RGBColor = C_LINE,
    title_size: int = 15,
    body_size: int = 12,
) -> None:
    # Base card
    card = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height)
    )
    card.adjustments[0] = 0.04
    card.fill.solid()
    card.fill.fore_color.rgb = card_bg
    card.line.color.rgb = border_color
    card.line.width = Pt(1.2)

    # Header band inside card
    h_band = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left + 0.15), Inches(top + 0.15), Inches(width - 0.3), Inches(0.48)
    )
    h_band.adjustments[0] = 0.15
    h_band.fill.solid()
    h_band.fill.fore_color.rgb = header_bg
    h_band.line.fill.background()
    tf_h = h_band.text_frame
    tf_h.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_h = tf_h.paragraphs[0]
    p_h.text = "  " + title
    p_h.font.name = FONT_NAME
    p_h.font.size = Pt(title_size)
    p_h.font.bold = True
    p_h.font.color.rgb = header_fg

    # Body bullets
    tb = slide.shapes.add_textbox(
        Inches(left + 0.2), Inches(top + 0.72), Inches(width - 0.4), Inches(height - 0.85)
    )
    tf = tb.text_frame
    tf.word_wrap = True
    for i, line in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = line
        p.space_after = Pt(6)
        p.font.name = FONT_NAME
        p.font.size = Pt(body_size)
        p.font.color.rgb = C_INK


def add_footer(slide, page_num: int, total_pages: int = 8) -> None:
    tb = slide.shapes.add_textbox(Inches(0.6), Inches(7.05), Inches(12.1), Inches(0.35))
    tf = tb.text_frame
    p = tf.paragraphs[0]
    p.text = f"부울경 채용 AI 매칭 챗봇 · GraphRAG 프로젝트 발표자료   |   https://jobmismatch.vercel.app   ({page_num}/{total_pages})"
    p.alignment = PP_ALIGN.RIGHT
    p.font.name = FONT_NAME
    p.font.size = Pt(10)
    p.font.color.rgb = C_MUTED


def build_presentation(output_path: Path) -> None:
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # =========================================================================
    # SLIDE 1: Cover & 6-Step Process Overview
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s1, C_DARK_BG)

    # Top badge
    badge = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(0.8), Inches(4.5), Inches(0.45))
    badge.fill.solid()
    badge.fill.fore_color.rgb = C_BRAND
    badge.line.color.rgb = C_ACCENT
    tf_b = badge.text_frame
    tf_b.vertical_anchor = MSO_ANCHOR.MIDDLE
    p_b = tf_b.paragraphs[0]
    p_b.text = "부산·울산·경남 지역 일자리 미스매칭 해결 AI 프로젝트"
    p_b.alignment = PP_ALIGN.CENTER
    p_b.font.name = FONT_NAME
    p_b.font.size = Pt(12)
    p_b.font.bold = True
    p_b.font.color.rgb = C_ACCENT

    # Main Title
    tb1 = s1.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.8), Inches(2.2))
    tf1 = tb1.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "부울경 채용 AI 매칭 챗봇 · GraphRAG"
    p1.font.name = FONT_NAME
    p1.font.size = Pt(40)
    p1.font.bold = True
    p1.font.color.rgb = C_WHITE

    p2 = tf1.add_paragraph()
    p2.text = "단일 대화형 챗봇과 2-Hop 지식 그래프(GraphRAG)를 활용한 설명 가능한 지역 채용 매칭 플랫폼"
    p2.space_before = Pt(12)
    p2.font.name = FONT_NAME
    p2.font.size = Pt(18)
    p2.font.color.rgb = RGBColor(180, 215, 200)

    # 6-Step Flow Boxes on Cover
    steps = [
        ("STEP 1", "지역 문제 발견", "부울경 구인·구직\n구조적 미스매칭"),
        ("STEP 2", "사용자 정의", "청년·기술 구직자 및\n지역 산단 강소기업"),
        ("STEP 3", "문제 원인 분석", "단순 키워드 검색 한계\n· 과다한 텍스트 피로도"),
        ("STEP 4", "AI 아이디어 도출", "단일 챗봇 + GraphRAG\n온톨로지 확장 매칭"),
        ("STEP 5", "서비스 구조 설계", "고용24 + Neon DB +\nFastAPI 서버리스"),
        ("STEP 6", "프로토타입 제작", "600건 실시간 적재 및\n3단 정형 카드 웹 배포"),
    ]
    for idx, (st_no, st_title, st_desc) in enumerate(steps):
        x = 0.8 + idx * 1.98
        y = 4.2
        box = s1.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(1.82), Inches(2.1))
        box.adjustments[0] = 0.08
        box.fill.solid()
        box.fill.fore_color.rgb = RGBColor(24, 64, 52)
        box.line.color.rgb = C_ACCENT if idx in (3, 5) else RGBColor(65, 115, 98)
        box.line.width = Pt(1.5)

        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = st_no
        p.font.name = FONT_NAME
        p.font.size = Pt(11)
        p.font.bold = True
        p.font.color.rgb = C_ACCENT

        p_t = tf.add_paragraph()
        p_t.text = st_title
        p_t.space_before = Pt(6)
        p_t.font.name = FONT_NAME
        p_t.font.size = Pt(14)
        p_t.font.bold = True
        p_t.font.color.rgb = C_WHITE

        p_d = tf.add_paragraph()
        p_d.text = st_desc
        p_d.space_before = Pt(8)
        p_d.font.name = FONT_NAME
        p_d.font.size = Pt(11)
        p_d.font.color.rgb = RGBColor(200, 225, 215)

    tb_url = s1.shapes.add_textbox(Inches(0.8), Inches(6.6), Inches(11.8), Inches(0.5))
    p_u = tb_url.text_frame.paragraphs[0]
    p_u.text = "🔗 Live Prototype: https://jobmismatch.vercel.app   |   GitHub: https://github.com/juny79/job_mismatch"
    p_u.font.name = FONT_NAME
    p_u.font.size = Pt(12)
    p_u.font.bold = True
    p_u.font.color.rgb = C_ACCENT

    # =========================================================================
    # SLIDE 2: STEP 1. 지역 문제 발견 (Regional Problem Discovery)
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s2, C_LIGHT_BG)
    add_header(s2, "STEP 1 · 지역 문제 발견", "부산·울산·경남(부울경) 일자리 미스매칭 현상", "일자리가 없는 것이 아니라, 구직자의 역량과 지역 산단 기업의 공고가 연결되지 못하고 있습니다")

    add_card(
        s2, 0.6, 1.55, 3.9, 5.2,
        "1. 청년 인재 유출 vs 산단 구인난의 역설",
        [
            "• 부울경에는 센텀시티(IT), 녹산·사상(제조), 울산 테크노·온산(화공/전장), 창원·김해·거제(기계/방산/조선) 등 15대 핵심 산업거점이 존재",
            "• 지역 강소·중견기업은 상시 인력난을 겪고 있으나, 청년·구직자는 '내 전공/자격증으로 갈 만한 기업이 없다'고 체감",
            "• 단순 채용공고 수 부족이 아닌 '정보 비대칭과 탐색 실패'가 핵심 문제",
        ],
        header_bg=C_BRAND_SOFT, header_fg=C_BRAND, body_size=12,
    )
    add_card(
        s2, 4.7, 1.55, 3.9, 5.2,
        "2. 직무·자격증과 실제 공고 간 언어 장벽",
        [
            "• 구직자는 '정보처리기사', '전기기사', '품질경영기사', '전산세무' 등 자격증과 학습 기술 위주로 본인을 정의",
            "• 반면 기업 공고는 'MES/ERP 구축', 'PLC 자동화 제어', '스마트팩토리 비전 검사' 등 현장 직무 용어로 작성됨",
            "• 기존 채용 사이트에서 '정보처리기사'를 검색하면 단어 미포함 우수 IT/SW 기업 공고가 대거 누락됨",
        ],
        header_bg=C_WARN_BG, header_fg=C_WARN_INK, body_size=12,
    )
    add_card(
        s2, 8.8, 1.55, 3.9, 5.2,
        "3. 파편화된 조건 정보(연봉·복지·근무지)",
        [
            "• 부울경 권역 특성상 통근버스, 기숙사 제공 여부, 산업단지 위치, 실질 연봉 하한선이 지원 결정의 핵심 요인",
            "• 그러나 기존 포털에서는 수백 건의 공고 본문을 일일이 클릭해 읽어야만 해당 조건과 내 기술 일치 여부를 확인 가능",
            "• 탐색 피로도가 높아 구직자가 중도에 탐색을 포기하는 현상 발생",
        ],
        header_bg=C_BLUE_BG, header_fg=C_BLUE_INK, body_size=12,
    )
    add_footer(s2, 2)

    # =========================================================================
    # SLIDE 3: STEP 2. 사용자 정의 (Target User & Persona Definition)
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s3, C_LIGHT_BG)
    add_header(s3, "STEP 2 · 사용자 정의", "누구의 어떤 페인포인트(Pain Point)를 해결하는가?", "부울경 구직자 2대 핵심 페르소나와 사용자가 진짜 원하는 매칭 경험 정의")

    add_card(
        s3, 0.6, 1.55, 5.9, 2.5,
        "페르소나 A · 부울경 IT/SW 취업 준비생 (부산 센텀·창원 스마트산단 희망)",
        [
            "• 보유 역량: 정보처리기사, SQLD 자격증 보유 / Python, Java 프로젝트 경험",
            "• 겪는 어려움: 복잡한 검색 필터를 설정해도 내 자격증과 매칭되는 공고가 0건으로 뜨거나, 어떤 기술이 일치하는지 알 수 없음",
            "• 핵심 니즈: '부산 + 소프트웨어/IT + 정보처리기사 + 3,500만원 이상'만 답하면 연관된 Python/Java/Spring 공고까지 한눈에 추천받길 원함",
        ],
        header_bg=C_BRAND_SOFT, header_fg=C_BRAND, body_size=11,
    )
    add_card(
        s3, 6.8, 1.55, 5.9, 2.5,
        "페르소나 B · 제조/설계/자동화 기술직 구직자 (울산·창원·김해·양산 산단 희망)",
        [
            "• 보유 역량: 전기기사, 기계설계산업기사, CAD/PLC/품질관리 실무 또는 이력서 파일 보유",
            "• 겪는 어려움: 긴 공고 텍스트 속에서 요구 자격, 기숙사·통근버스 복지, 연봉 수준을 빠르게 비교하기 어려움",
            "• 핵심 니즈: 이력서 파일을 올리거나 버튼 몇 번만 누르면 내 기술 일치 여부와 복리후생이 정형화된 카드로 정리되길 원함",
        ],
        header_bg=C_BLUE_BG, header_fg=C_BLUE_INK, body_size=11,
    )
    add_card(
        s3, 0.6, 4.3, 12.1, 2.45,
        "사용자 중심 설계 원칙 (User-Centric Design Requirements)",
        [
            "1) 텍스트 과부하 및 복잡한 카테고리 배제: 여러 개의 입력 폼과 설명문을 없애고, '단일 챗봇 대화창' 하나로 모든 조건 입력을 통합",
            "2) 즉각적인 피드백(Zero-Wait Filtering): 챗봇에서 지역·분야·기술·연봉을 클릭할 때마다 오른쪽 화면의 600건 공고가 실시간으로 좁혀지는 경험 제공",
            "3) 무의미한 경고 제거 및 근거 중심 시각화: 불필요한 '! 확인 필요' 경고 나열 대신 [요구 기술·자격 / 주요 복리후생 / GraphRAG 연결] 3단 구조로 직관적 표시",
        ],
        header_bg=C_PURPLE_BG, header_fg=C_PURPLE_INK, body_size=12,
    )
    add_footer(s3, 3)

    # =========================================================================
    # SLIDE 4: STEP 3. 문제 원인 분석 (Root Cause Analysis)
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s4, C_LIGHT_BG)
    add_header(s4, "STEP 3 · 문제 원인 분석", "기존 채용 검색 및 초기 프로토타입의 3대 한계점 분석", "왜 기존 방식으로는 조건에 맞는 공고가 안 뜨거나 가독성이 떨어졌는가?")

    add_card(
        s4, 0.6, 1.55, 3.9, 5.2,
        "원인 1 · 1차원 키워드(Lexical) 매칭의 한계",
        [
            "• 단순 문자열 포함 여부로만 검색하면 '정보처리기사' 입력 시 공고 본문에 해당 단어가 없으면 매칭률 0%로 판정",
            "• 자격증과 실무 기술(예: 정보처리기사 ↔ Python, Java, Spring, SQL / 전기기사 ↔ PLC, AutoCAD) 간의 의미적 연결 구조(Ontology) 부재",
            "• 결과적으로 조건 필터링 후 0건이 추출되는 현상 발생",
        ],
        header_bg=C_WARN_BG, header_fg=C_WARN_INK, body_size=12,
    )
    add_card(
        s4, 4.7, 1.55, 3.9, 5.2,
        "원인 2 · 정제되지 않은 키워드 추출과 시각적 노이즈",
        [
            "• 공고 원문에서 '기계', '개발', '제조', '검사' 같은 일반 명사까지 기술로 무분별하게 추출할 경우 공고당 15~20개 태그가 생성됨",
            "• 사용자가 입력하지 않은 모든 단어를 노란색 '! 확인 필요'로 표시하면 핵심 요구 기술이 묻히고 가독성이 급격히 저하됨",
            "• 직무명에도 공고 제목이 중복 표기되어 카드 레이아웃이 복잡해짐",
        ],
        header_bg=C_WARN_BG, header_fg=C_WARN_INK, body_size=12,
    )
    add_card(
        s4, 8.8, 1.55, 3.9, 5.2,
        "원인 3 · 데이터 파이프라인 및 UI 파편화",
        [
            "• 소수의 합성 샘플(3건~75건)만으로는 부울경 15개 구·군과 6대 직무 조합을 테스트할 때 빈 결과(Empty Set)가 빈발",
            "• 고용24 OpenAPI의 해외 서버리스 IP 제한 또는 세부 API 권한 미승인 시 데이터 수집이 중단되는 문제",
            "• 다중 탭·폼 중심 UI는 사용자가 어디에 무엇을 입력해야 할지 혼란을 초래",
        ],
        header_bg=C_WARN_BG, header_fg=C_WARN_INK, body_size=12,
    )
    add_footer(s4, 4)

    # =========================================================================
    # SLIDE 5: STEP 4. AI 활용 아이디어 도출 (AI & GraphRAG Solution)
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s5, C_LIGHT_BG)
    add_header(s5, "STEP 4 · AI 활용 아이디어 도출", "GraphRAG 지식 그래프 + 온톨로지 매칭 + 단일 챗봇의 결합", "환각(Hallucination) 없는 설명 가능한 GraphRAG와 대화형 인터페이스로 문제를 해결합니다")

    add_card(
        s5, 0.6, 1.55, 3.9, 5.2,
        "AI 핵심 1 · 인메모리 GraphRAG 지식 그래프",
        [
            "• 채용공고를 평면 텍스트가 아닌 6종 노드(공고·기업·지역·직무·기술·복지)와 5종 관계 엣지(LOCATED_IN, HAS_ROLE, REQUIRES_SKILL, OFFERS_BENEFIT, POSTED_JOB)로 구조화",
            "• 600건 공고 기준 약 1,000+개 노드와 10,000+개 관계를 실시간 구축하여 공고 간 연결망 탐색",
            "• 모든 추천 결과에 그래프 연결 경로(Evidence)를 투명하게 제시",
        ],
        header_bg=C_BRAND_SOFT, header_fg=C_BRAND, body_size=12,
    )
    add_card(
        s5, 4.7, 1.55, 3.9, 5.2,
        "AI 핵심 2 · 2-Hop 중심성 & 자격증 온톨로지 확장",
        [
            "• [자격증↔기술 온톨로지]: '정보처리기사' 입력 시 직접 일치 공고뿐 아니라 동일 IT 그래프 클러스터의 Python·Java·Spring·SQL 공고를 '🔗 연관 기술 매칭'으로 자동 확장",
            "• [2-Hop 그래프 중심성 랭킹]: 공고 A → (기술/직무 노드) ← 공고 B의 2-Hop 이웃 밀도를 계산해 핵심 역량 공고에 가점 부여",
            "• 일반 명사 노이즈를 제거하고 공고당 3~5개 핵심 기술·자격만 정밀 추출",
        ],
        header_bg=C_BLUE_BG, header_fg=C_BLUE_INK, body_size=12,
    )
    add_card(
        s5, 8.8, 1.55, 3.9, 5.2,
        "AI 핵심 3 · 단일 매칭 챗봇 & 브라우저 이력서 분석",
        [
            "• 복잡한 검색창을 단일 챗봇으로 통합: ①지역 → ②직무 → ③기술/자격 → ④연봉 4단계 클릭/대화로 즉시 필터링",
            "• [개인정보 비저장 이력서 파싱]: PDF/DOCX/TXT 이력서를 브라우저 내에서 즉시 분석해 보유 기술 키워드만 챗봇 상태로 자동 주입 (서버에 원문 미전송)",
        ],
        header_bg=C_PURPLE_BG, header_fg=C_PURPLE_INK, body_size=12,
    )
    add_footer(s5, 5)

    # =========================================================================
    # SLIDE 6: STEP 5. 서비스 구조 설계 (System Architecture & Pipeline)
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s6, C_LIGHT_BG)
    add_header(s6, "STEP 5 · 서비스 구조 설계", "End-to-End 클라우드 데이터 파이프라인 및 서비스 아키텍처", "고용24 OpenAPI · Neon PostgreSQL · FastAPI Serverless · GraphRAG 하이브리드 엔진")

    # 4 Horizontal Layer Cards showing exact flow
    add_card(
        s6, 0.6, 1.55, 2.85, 5.2,
        "1. 데이터 수집·보완 계층",
        [
            "• 고용24(Work24) OpenAPI XML 클라이언트 연동 (work24_client.py)",
            "• 부울경 지역코드(부산 26000, 울산 31000, 경남 48000) 기반 수집",
            "• [무중단 폴백 시딩]: API 권한 대기·해외 IP 제한 시 부울경 15개 산단 거점 × 6대 직무 공고를 300건 단위로 즉시 생성·보완 (buulgyeong_seed.py)",
        ],
        header_bg=C_BRAND_SOFT, header_fg=C_BRAND, body_size=11,
    )
    add_card(
        s6, 3.68, 1.55, 2.85, 5.2,
        "2. 정규화·클라우드 DB 계층",
        [
            "• 고용24 어댑터(work24_adapter.py)가 급여를 '만원/연'으로 통일하고 핵심 자격증·기술·복리후생 및 원문 Evidence 생성",
            "• Vercel Storage 연동 Neon Serverless PostgreSQL에 600건 상시 적재 (database.py)",
            "• '+300건 더 가져오기' 버튼으로 실시간 추가 적재 지원",
        ],
        header_bg=C_BLUE_BG, header_fg=C_BLUE_INK, body_size=11,
    )
    add_card(
        s6, 6.76, 1.55, 2.85, 5.2,
        "3. GraphRAG·하이브리드 엔진",
        [
            "• FastAPI 서버리스 백엔드 (api/index.py)",
            "• 요청 시 활성 공고를 로드해 인메모리 JobGraph(노드·엣지) 빌드 (graphrag.py)",
            "• Lexical 가중치 + 1-Hop 경로 매칭 + 2-Hop 공유 중심성 보너스를 결합한 hybrid_search() 수행 (hybrid.py)",
        ],
        header_bg=C_PURPLE_BG, header_fg=C_PURPLE_INK, body_size=11,
    )
    add_card(
        s6, 9.84, 1.55, 2.85, 5.2,
        "4. 대화형 프론트엔드 계층",
        [
            "• 좌측: 단일 챗봇 인터페이스 + 활성 조건 태그 바 + 이력서 파일 추출기",
            "• 우측: 실시간 추천 공고 피드 + 3단 정형 카드 (기술·복지·그래프 연결)",
            "• 상단: 적재 공고 수 및 인터랙티브 GraphRAG 노드·엣지 구조 뷰어",
        ],
        header_bg=C_BRAND_SOFT, header_fg=C_BRAND, body_size=11,
    )
    add_footer(s6, 6)

    # =========================================================================
    # SLIDE 7: STEP 6. 프로토타입 제작 및 작동 화면 (Prototype & Live Demo Flow)
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s7, C_LIGHT_BG)
    add_header(s7, "STEP 6 · 프로토타입 제작", "구현 완료된 웹 프로토타입 작동 방식 (https://jobmismatch.vercel.app)", "단일 챗봇 질의응답부터 3단 정형 공고 카드 및 GraphRAG 구조 확인까지의 실제 작동 흐름")

    # Left mockup panel: Chatbot
    add_card(
        s7, 0.6, 1.55, 4.5, 5.2,
        "💬 좌측 화면: 단일 채용 매칭 챗봇",
        [
            "• 상단 우측 고정 [↺ 초기화] 버튼 및 현재 조건 요약 배지 바:",
            "  [📍 지역: 부산] [🏢 분야: 소프트웨어] [🛠️ 내 기술: 정보처리기사] [💰 최소연봉: 3500만원]",
            "• 4단계 대화형 질의응답 + 빠른 선택 칩(Quick Chips) 제공",
            "• 대화 완료 후에도 자유 키워드('창원', 'CAD', '4000만원' 등) 입력 시 즉시 조건 갱신",
            "• 하단 [📎 이력서 파일(PDF/DOCX/TXT) 업로드]로 보유 기술 원클릭 반영",
        ],
        header_bg=C_BRAND_SOFT, header_fg=C_BRAND, body_size=11,
    )

    # Right mockup panel: 3-Row Structured Job Card & Graph Viewer
    add_card(
        s7, 5.3, 1.55, 7.4, 2.45,
        "🕸️ 상단 바: 실시간 적재 공고 수 & GraphRAG 구조 뷰어 드로어",
        [
            "• [● 적재 공고 600건 · GraphRAG 노드 1,071개 · 관계 13,639개 ▾ 구조 보기] 배지 상시 표시",
            "• 클릭 시 현재 메모리에 구축된 공고·기업·지역·직무·기술·복지 노드 수와 엣지 통계를 시각적으로 펼쳐 확인",
            "• 우측 [🔄 고용24 공고 +300건 더 가져오기] 클릭 시 부울경 공고 300건씩 DB에 즉시 추가 적재",
        ],
        header_bg=C_BLUE_BG, header_fg=C_BLUE_INK, body_size=11,
    )

    add_card(
        s7, 5.3, 4.2, 7.4, 2.55,
        "🎯 우측 화면: 가독성을 극대화한 3단 정형 채용공고 카드",
        [
            "• 공고 헤더: [센텀에이아이랩(주)] 스마트팩토리 AI 비전 검사 및 Python 백엔드 개발자  |  연봉 4,000~4,600만원",
            "• 1행 [요구 기술·자격]: [✓ 내 보유 일치: 정보처리기사](초록) [🔗 연관 기술 매칭: Python](초록) [🛠️ FastAPI](회색)",
            "• 2행 [주요 복리후생]: [🎁 유연근무] [🎁 재택근무] [🎁 중식제공] [🎁 교육비지원](보라)",
            "• 3행 [GraphRAG 연결]: [📍 지역노드 → 부산 해운대구] [🏢 직무노드 → 소프트웨어/IT · AI 개발] [🏛️ 채용기업 → 센텀에이아이랩(주)]",
        ],
        header_bg=C_PURPLE_BG, header_fg=C_PURPLE_INK, body_size=11,
    )
    add_footer(s7, 7)

    # =========================================================================
    # SLIDE 8: Summary & Expected Impact
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    set_slide_bg(s8, C_LIGHT_BG)
    add_header(s8, "SUMMARY · 기대 효과 및 결론", "프로젝트 종합 요약 및 부울경 일자리 매칭 기대 효과", "지역 문제 정의부터 AI(GraphRAG) 설계·클라우드 프로토타입 배포까지의 핵심 성과")

    add_card(
        s8, 0.6, 1.55, 5.9, 5.2,
        "기존 채용 검색 vs 부울경 GraphRAG AI 매칭 비교",
        [
            "1) 입력 방식의 혁신",
            "   • 기존: 복잡한 다중 필터·카테고리 직접 설정",
            "   • 개선: 단일 챗봇 4단계 대화 + 이력서 파일 원클릭 기술 추출",
            "2) 검색·매칭 지능화",
            "   • 기존: 단어 완전 일치(Lexical) 검색 → 자격증 입력 시 공고 누락",
            "   • 개선: GraphRAG 지식 그래프(2-Hop 중심성) + 자격증↔실무기술 온톨로지 확장 매칭",
            "3) 정보 시각화와 설명 가능성(XAI)",
            "   • 기존: 긴 줄글 공고 본문 열람 또는 무의미한 경고 나열",
            "   • 개선: [요구 기술·자격 / 주요 복리후생 / GraphRAG 연결] 3단 정형 카드로 추천 근거 즉시 확인",
        ],
        header_bg=C_BRAND_SOFT, header_fg=C_BRAND, body_size=11,
    )

    add_card(
        s8, 6.8, 1.55, 5.9, 5.2,
        "기대 효과 및 향후 확장 방향",
        [
            "• 부울경 구직자의 탐색 시간 단축 및 숨은 강소기업 발굴",
            "  - 부산·울산·경남 15개 주요 산업단지 공고를 보유 자격증·기술과 연결해 미스매칭 해소",
            "• 설명 가능하고 안전한 AI 채용 보조 도구",
            "  - 합격 확률을 임의로 예단하거나 환각을 생성하지 않고, 공고 원문 Evidence와 그래프 경로만 투명하게 제시",
            "  - 이력서 원문을 서버에 저장하지 않는 프라이버시 우선(Privacy-First) 구조",
            "• 클라우드 운영 및 확장성 확보",
            "  - Vercel Serverless + Neon PostgreSQL 기반으로 즉시 서비스 운영 가능",
            "  - 향후 부울경 대학 일자리센터·지자체 청년 플랫폼 연동 확장 용이",
        ],
        header_bg=C_BLUE_BG, header_fg=C_BLUE_INK, body_size=11,
    )
    add_footer(s8, 8)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(output_path))
    print(f"Presentation saved successfully to: {output_path}")


if __name__ == "__main__":
    out_file = Path(__file__).resolve().parent.parent / "docs" / "16_부울경_채용_AI_매칭_GraphRAG_발표자료.pptx"
    build_presentation(out_file)
