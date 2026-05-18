import base64
import csv
import hashlib
import io
import json
import math
import os
import threading
import zipfile
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from re import DOTALL, IGNORECASE, escape, findall, finditer, fullmatch, search, split, sub
from urllib.parse import urljoin
from xml.etree import ElementTree
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx
from fastapi import Body, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from research_os.brokerage import BrokerageClient, get_default_brokerage_client
from research_os.data_providers import (
    FmpClient,
    OpenDartClient,
    fetch_customs_trade_rows,
    fetch_nps_institutional_context,
    fetch_nps_institutional_signal,
    get_analysis_data_provider,
)
from research_os.export_utils import build_simple_xlsx, collect_result_export_sheets
from research_os.file_extraction import (
    decode_attachment_base64,
    extract_pdf_text,
    extract_uploaded_file_text,
    is_pdf_attachment,
    safe_attachment_file_name,
)
from research_os.kiwoom_auth import KiwoomAuthClient, KiwoomMaskedTokenStatus
from research_os.models import (
    Broker,
    BrokerStatus,
    CapturedResearchItem,
    ChecklistItemStatus,
    CompounderCandidate,
    DashboardMetric,
    DashboardReportSummary,
    DataQualitySummary,
    DataSourceType,
    EarningsMetric,
    EarningsReactionRequest,
    EarningsReactionResponse,
    InjectedDataPoint,
    InvestmentThesis,
    InstitutionalAnalysisRequest,
    InstitutionalAnalysisResponse,
    ConcentrationItem,
    LongTermCompounderRequest,
    LongTermCompounderResponse,
    ResearchChecklistAssessmentResponse,
    ResearchChecklistRequest,
    AutoResearchCaptureRequest,
    ResearchCaptureRequest,
    ResearchCaptureResponse,
    ResearchMemoryContentResponse,
    ResearchManifestResponse,
    ResearchMemoryFile,
    ResearchMemoryListResponse,
    ResearchMemorySupplementRequest,
    ResearchMemoryArchiveRequest,
    PriceLevel,
    SectorCompanyCandidate,
    SectorLeaderCandidate,
    SectorOpportunity,
    SectorPeerComparison,
    SectorOpportunityRequest,
    SectorOpportunityResponse,
    SectorTrendInsight,
    InvestmentThesisListResponse,
    ScenarioSummary,
    SkillContribution,
    SmartTradeSetupRequest,
    SmartTradeSetupResponse,
    TeamAnalysisRequest,
    TeamAnalysisResponse,
    TeamConflict,
    ThesisImpact,
    ThesisImpactFinding,
    ThesisImpactRequest,
    ThesisImpactResponse,
    TradesResponse,
    PortfolioHolding,
    PortfolioImportRequest,
    PortfolioImportResponse,
    PolicyAllocationAdjustment,
    PortfolioSaveRequest,
    PortfolioRiskScanRequest,
    PortfolioRiskScanResponse,
    PortfolioRiskWarning,
    ReinforcementPortfolioOptimizationRequest,
    ReinforcementPortfolioOptimizationResponse,
    PortfolioStoreResponse,
    TradeTarget,
    SavedPortfolio,
    InterestTicker,
    InterestSector,
    InterestListResponse,
    InterestListUpdateRequest,
    MarketCloseEntry,
    MarketCloseHistoryResponse,
    MarketCloseReviewRequest,
    MarketCloseReviewResponse,
    TickerDashboardResponse,
    TickerProfileResponse,
    TickerVerificationResponse,
    WatchItem,
    WatchItemSignal,
)
from research_os.research_memory import (
    ResearchStorageInfo,
    read_manifest,
    resolve_vault_dir,
    save_research_markdown,
    update_manifest,
)
from research_os.rag_memory import (
    backfill_research_memory_documents_from_manifest,
    backfill_thesis_snapshots_from_manifest,
    count_research_memory_documents_by_ticker,
    rag_memory_status,
    read_ticker_thesis_context,
    read_ticker_thesis_snapshot,
    search_all_research_memory_documents,
    search_research_memory_documents,
    upsert_research_memory_document,
    upsert_ticker_thesis_snapshot,
)
from research_os.security import verify_user_token
from research_os.settings import Settings, get_settings, mask_secret
from research_os.web_capture import (
    clean_web_article_text,
    fetch_capture_source_url,
    foreign_text_korean_digest,
    is_unusable_source_url,
    render_source_url_body,
    render_url_only_capture_context,
    translation_language_label,
)


app = FastAPI(title="Investment Journal API Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5501",
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "null",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONSOLE_DIR = Path(__file__).resolve().parents[1] / "mobile_app" / "research_console"
if CONSOLE_DIR.exists():
    app.mount("/console", StaticFiles(directory=CONSOLE_DIR, html=True), name="console")


RESEARCH_CHECKLIST_ITEMS = [
    ("business_model", "비즈니스 모델 이해"),
    ("revenue_drivers", "수익 동력"),
    ("market_size", "시장 규모와 성장성"),
    ("competitive_advantage", "경쟁 우위"),
    ("financial_growth", "매출/이익 성장률"),
    ("margin_quality", "마진 구조"),
    ("cash_flow", "현금흐름과 FCF"),
    ("balance_sheet", "재무 건전성"),
    ("capital_allocation", "자본 배분"),
    ("management_quality", "경영진 평가"),
    ("valuation", "밸류에이션"),
    ("ownership_flow", "수급과 주주 구조"),
    ("industry_cycle", "산업 사이클"),
    ("regulatory_risk", "규제 리스크"),
    ("red_flags", "위험 신호"),
    ("exit_criteria", "투자 철회 기준"),
]


COLLABORATIVE_SKILLS = [
    (
        1,
        "기관급 기업 분석",
        "Goldman Sachs 애널리스트",
        "비즈니스 모델, 수익 동력, 경쟁 우위, 주요 리스크, 강세/기준/약세 논거를 정리합니다.",
    ),
    (
        2,
        "스마트 매매 전략",
        "헤지펀드 포트폴리오 매니저",
        "시장 구조, 진입 구간, 손절, 목표가, 리스크 대비 보상 구조를 설계합니다.",
    ),
    (
        3,
        "실적 반응 분석",
        "Buy-Side 리서치 전문가",
        "실적 발표, 가이던스, 주가 반응, 다음 실적 전 센티먼트 변화를 분석합니다.",
    ),
    (
        4,
        "포트폴리오 리스크 스캔",
        "리스크 관리 전문가",
        "섹터 집중도, 상관관계, 이벤트 리스크, 포트폴리오 취약점을 점검합니다.",
    ),
    (
        5,
        "섹터 기회 발굴",
        "매크로 전략가",
        "금리, AI, 에너지 가격 등 거시 환경에서 수혜 섹터와 상대 매력도를 찾습니다.",
    ),
    (
        6,
        "투자자 리서치 체크리스트",
        "체계적 투자 리서치 전문가",
        "16개 투자 전 체크 항목 기준으로 준비도와 부족한 리서치 영역을 평가합니다.",
    ),
    (
        7,
        "장기 복리 성장주 발굴",
        "Fundsmith/Baillie Gifford 스타일 성장주 투자자",
        "매출 성장, 마진, 경쟁 우위, 확장 가능한 모델을 기준으로 장기 복리 가능성을 봅니다.",
    ),
]


OFFICIAL_TICKER_REGISTRY = {
    "AAPL": {
        "company_name": "Apple Inc.",
        "exchange": "NASDAQ",
        "country": "US",
        "asset_type": "equity",
    },
    "AMZN": {
        "company_name": "Amazon.com, Inc.",
        "exchange": "NASDAQ",
        "country": "US",
        "asset_type": "equity",
    },
    "GOOGL": {
        "company_name": "Alphabet Inc. Class A",
        "exchange": "NASDAQ",
        "country": "US",
        "asset_type": "equity",
    },
    "META": {
        "company_name": "Meta Platforms, Inc.",
        "exchange": "NASDAQ",
        "country": "US",
        "asset_type": "equity",
    },
    "MSFT": {
        "company_name": "Microsoft Corporation",
        "exchange": "NASDAQ",
        "country": "US",
        "asset_type": "equity",
    },
    "NVDA": {
        "company_name": "NVIDIA Corporation",
        "exchange": "NASDAQ",
        "country": "US",
        "asset_type": "equity",
        "sector": "Technology",
        "industry": "Semiconductors",
        "business_context": "AI 가속기, GPU, 네트워킹, 소프트웨어 생태계를 데이터센터와 게임/전문 시각화 시장에 공급하는 반도체 플랫폼 기업",
        "analysis_focus": "AI 데이터센터 수요, GPU 공급, 매출총이익률, 고객 집중도, 경쟁 GPU/ASIC 리스크, 밸류에이션",
        "watch_kpis": [
            "데이터센터 매출 성장률",
            "매출총이익률",
            "GPU 공급/수요 코멘트",
            "주요 클라우드 고객 투자 흐름",
            "차세대 제품 전환 비용",
        ],
    },
    "PL": {
        "company_name": "Planet Labs PBC",
        "exchange": "NYSE",
        "country": "US",
        "asset_type": "equity",
        "sector": "Industrials/Technology",
        "industry": "Earth Observation / Geospatial Data",
        "analysis_focus": "위성 이미지 데이터 수요, 정부·상업 고객 계약, 매출 성장, 매출총이익률, 조정 EBITDA와 현금 소진, 경쟁 리스크",
        "business_context": "지구 관측 위성망에서 수집한 이미지와 분석 데이터를 정부·방위·상업 고객에게 구독/계약 형태로 제공하는 위성 데이터 기업",
        "watch_kpis": [
            "위성 데이터 매출 성장률",
            "정부 고객 계약 수주/갱신",
            "상업 고객 유지율",
            "매출총이익률",
            "조정 EBITDA와 현금 소진",
        ],
        "earnings_dates_by_quarter": {
            "FY2025 Q4": "2025-03-20",
            "Q4 FY2025": "2025-03-20",
            "FY2026 Q1": "2025-06-04",
            "Q1 FY2026": "2025-06-04",
            "FY2026 Q2": "2025-09-08",
            "Q2 FY2026": "2025-09-08",
            "FY2026 Q3": "2025-12-10",
            "Q3 FY2026": "2025-12-10",
            "FY2026 Q4": "2026-03-19",
            "Q4 FY2026": "2026-03-19",
            "FY2027 Q1": "2026-06-03",
            "Q1 FY2027": "2026-06-03",
        },
        "earnings_quarter_sequence": [
            "FY2025 Q4",
            "FY2026 Q1",
            "FY2026 Q2",
            "FY2026 Q3",
            "FY2026 Q4",
            "FY2027 Q1",
        ],
        "latest_reported_quarter": "FY2026 Q4",
        "latest_reported_earnings_date": "2026-03-19",
        "previous_earnings_date": "2025-12-10",
        "next_earnings_date": "2026-06-03",
        "earnings_calendar_source": "Planet IR, MarketBeat, Nasdaq press releases",
        "latest_earnings_profile": {
            "quarter": "FY2026 Q4",
            "earnings_report_date": "2026-03-19",
            "price_reaction": "발표 후 시간외 +22%, 정규장 +8.7%",
            "eps_reported": 0.0,
            "eps_expected": -0.05,
            "revenue_reported": 86.8,
            "revenue_expected": 77.81,
            "guidance_change": "상향",
            "management_tone": (
                "경영진은 Defense & Intelligence 부문 강세, 대형 계약 확대, "
                "Planet Insights Platform 출시와 AI 기반 분석 수요를 강조했습니다."
            ),
            "market_context": (
                "FY2026 Q4 매출과 조정 EBITDA가 시장 예상보다 양호했고, "
                "FY2027 매출 가이던스가 전년 대비 고성장 구간을 제시했습니다."
            ),
            "previous_earnings_summary": (
                "FY2026 Q3 발표 후 회사는 FY2026 Q4 매출 7,600만~8,000만 달러, "
                "비GAAP 매출총이익률 50~52%, 조정 EBITDA 손실 700만~500만 달러, "
                "FY2026 연간 매출 2억 9,700만~3억 100만 달러를 제시했습니다."
            ),
            "next_earnings_guidance": (
                "FY2027 Q1 가이던스: 매출 8,700만~9,100만 달러, 비GAAP 매출총이익률 "
                "49~51%, 조정 EBITDA 손실 600만~300만 달러, 자본지출 1,700만~2,300만 달러. "
                "FY2027 연간 가이던스: 매출 4억 1,500만~4억 4,000만 달러, 비GAAP 매출총이익률 "
                "51~53%, 조정 EBITDA 400만~1,400만 달러, 자본지출 6,500만~7,500만 달러."
            ),
            "key_numbers": {
                "FY2026 Q4 매출": "8,680만 달러",
                "FY2026 연간 매출": "3억 770만 달러",
                "FY2026 Q4 비GAAP 매출총이익률": "54%",
                "FY2026 Q4 조정 EBITDA": "180만 달러",
                "RPO": "8억 5,240만 달러",
                "백로그": "약 9억 달러",
            },
            "source_url": "https://investors.planet.com/news/news-details/2026/Planet-Reports-Financial-Results-for-Fiscal-Fourth-Quarter-and-Full-Year-2026/default.aspx",
        },
        "data_limitations": [
            "실적 캘린더는 로컬 공식 티커 프로필에 저장된 기준값을 우선 사용합니다. 새 발표 일정은 확인 후 업데이트가 필요합니다.",
            "시장/재무 프로바이더가 mock 모드이면 가격과 재무 수치는 실제 투자 판단에 사용할 수 없습니다.",
        ],
    },
    "PLTR": {
        "company_name": "Palantir Technologies Inc.",
        "exchange": "NASDAQ",
        "country": "US",
        "asset_type": "equity",
    },
    "TSLA": {
        "company_name": "Tesla, Inc.",
        "exchange": "NASDAQ",
        "country": "US",
        "asset_type": "equity",
    },
    "XOM": {
        "company_name": "Exxon Mobil Corporation",
        "exchange": "NYSE",
        "country": "US",
        "asset_type": "equity",
    },
    "JNJ": {
        "company_name": "Johnson & Johnson",
        "exchange": "NYSE",
        "country": "US",
        "asset_type": "equity",
    },
    "JOBY": {
        "company_name": "Joby Aviation, Inc.",
        "exchange": "NYSE",
        "country": "US",
        "asset_type": "equity",
        "sector": "Industrials",
        "industry": "Airports & Air Services / Advanced Air Mobility",
        "analysis_focus": "eVTOL 인증 진행, 상용 운항 일정, 현금 소진, 전략적 파트너십, 제조 확장성, 규제 리스크",
        "business_context": "전기 수직이착륙 항공기(eVTOL)를 개발하고 향후 에어택시 서비스를 운영하려는 첨단 항공 모빌리티 기업",
        "watch_kpis": [
            "FAA 인증 단계",
            "상용 운항 개시 일정",
            "현금 보유액과 분기 현금 소진",
            "제조/생산 램프업 진척",
            "Toyota·Delta·Uber 등 전략 파트너십 진행",
        ],
        "data_limitations": [
            "JOBY는 상업화 전/초기 단계 기업이라 전통적 이익 지표보다 인증, 현금 소진, 생산 능력, 파트너십 이정표를 우선 확인해야 합니다.",
        ],
    },
    "ABSI": {
        "company_name": "Absci Corporation",
        "exchange": "NASDAQ",
        "country": "US",
        "asset_type": "equity",
        "sector": "Healthcare",
        "industry": "AI Drug Discovery",
        "business_context": "생성형 AI와 합성생물학을 활용해 항체와 단백질 치료제 후보를 설계하는 바이오 플랫폼 기업",
        "analysis_focus": "플랫폼 검증, 파트너십, 임상 진입, 현금 소진, 기술 이전 가능성",
        "watch_kpis": ["파트너십 계약", "파이프라인 진척", "현금 보유액", "분기 현금 소진", "임상/전임상 데이터"],
    },
    "CHPT": {
        "company_name": "ChargePoint Holdings, Inc.",
        "exchange": "NYSE",
        "country": "US",
        "asset_type": "equity",
        "sector": "Industrials/Technology",
        "industry": "EV Charging Infrastructure",
        "business_context": "전기차 충전 네트워크와 충전 장비, 소프트웨어 서비스를 제공하는 EV 인프라 기업",
        "analysis_focus": "매출 성장, 충전 네트워크 사용률, 매출총이익률, 현금 소진, EV 수요와 보조금 환경",
        "watch_kpis": ["네트워크 충전량", "구독/소프트웨어 매출", "매출총이익률", "현금 소진", "EV 판매 추세"],
    },
    "GOTU": {
        "company_name": "Gaotu Techedu Inc.",
        "exchange": "NYSE",
        "country": "CN",
        "asset_type": "equity",
        "sector": "Consumer Discretionary",
        "industry": "Education Services",
        "business_context": "중국 온라인 교육과 학습 서비스를 제공하는 교육 기술 기업",
        "analysis_focus": "중국 교육 규제, 수강생 성장, 마케팅 효율, 마진 회복, 현금흐름",
        "watch_kpis": ["순매출", "매출총이익률", "영업현금흐름", "마케팅비 효율", "규제 변화"],
    },
    "OTLY": {
        "company_name": "Oatly Group AB",
        "exchange": "NASDAQ",
        "country": "SE",
        "asset_type": "equity",
        "sector": "Consumer Staples",
        "industry": "Plant-based Foods",
        "business_context": "귀리 기반 음료와 식품을 글로벌 시장에 판매하는 식물성 식품 기업",
        "analysis_focus": "매출 성장, 지역별 수요, 매출총이익률, 비용 구조 개선, 브랜드 경쟁력",
        "watch_kpis": ["지역별 매출", "매출총이익률", "EBITDA", "유통 채널 확대", "현금흐름"],
    },
    "RXRX": {
        "company_name": "Recursion Pharmaceuticals, Inc.",
        "exchange": "NASDAQ",
        "country": "US",
        "asset_type": "equity",
        "sector": "Healthcare",
        "industry": "AI Drug Discovery",
        "business_context": "대규모 생물학 데이터와 머신러닝을 활용해 신약 후보를 발굴하는 AI 바이오 플랫폼 기업",
        "analysis_focus": "임상 파이프라인, 플랫폼 파트너십, 데이터 자산, 현금 소진, 빅파마 협업",
        "watch_kpis": ["임상 단계별 진척", "파트너십 수익", "현금 보유액", "분기 현금 소진", "플랫폼 검증 데이터"],
    },
    "OPTT": {
        "company_name": "Ocean Power Technologies, Inc.",
        "exchange": "NYSE American",
        "country": "US",
        "asset_type": "equity",
        "sector": "Energy/Industrials",
        "industry": "Ocean Energy and Maritime Power",
        "business_context": "해양 에너지, 해상 전력·데이터 솔루션과 관련 장비를 개발하는 소형 청정에너지 기업",
        "analysis_focus": "수주, 매출 전환, 현금 소진, 희석 리스크, 해양 방산/에너지 고객 확보",
        "watch_kpis": ["수주잔고", "매출", "현금 보유액", "주식 희석", "주요 고객 계약"],
    },
    "360750": {
        "company_name": "TIGER 미국S&P500 ETF",
        "exchange": "KRX",
        "country": "KR",
        "asset_type": "etf",
        "sector": "ETF",
        "industry": "US Equity / S&P 500",
        "business_context": "S&P 500 지수를 추종해 미국 대형주에 분산 투자하는 국내 상장 ETF",
        "analysis_focus": "미국 대형주 이익 사이클, 달러/원 환율, S&P 500 밸류에이션, 분배금, 환노출",
        "watch_kpis": ["S&P 500 EPS 전망", "미국 10년물 금리", "달러/원", "상위 빅테크 비중", "분배금"],
    },
    "395160": {
        "company_name": "KODEX AI반도체 ETF",
        "exchange": "KRX",
        "country": "KR",
        "asset_type": "etf",
        "sector": "ETF",
        "industry": "Korea AI Semiconductors",
        "business_context": "국내 AI 반도체 밸류체인에 분산 투자하는 국내 상장 ETF",
        "analysis_focus": "메모리/AI 반도체 사이클, GPU·HBM 수요, 국내 반도체 장비·소재 실적, 환율",
        "watch_kpis": ["HBM 수요", "DRAM 가격", "반도체 수출", "상위 보유종목 실적", "외국인 수급"],
    },
    "0117V0": {
        "company_name": "TIGER 코리아AI전력기기TOP3플러스 ETF",
        "exchange": "KRX",
        "country": "KR",
        "asset_type": "etf",
        "sector": "ETF",
        "industry": "Korea AI Power Equipment",
        "business_context": "AI 데이터센터 전력 수요와 전력기기 인프라 확대 수혜 기업에 집중 투자하는 국내 상장 ETF",
        "analysis_focus": "전력기기 수주, 데이터센터 전력 인프라 투자, 상위 3개 종목 집중도, 밸류에이션 부담",
        "watch_kpis": ["전력기기 수주잔고", "변압기 수출", "데이터센터 전력 투자", "상위 3개 종목 비중", "PER/PBR"],
    },
    "033500": {
        "company_name": "동성화인텍",
        "exchange": "KOSDAQ",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Industrials",
        "industry": "LNG Insulation Materials",
        "business_context": "LNG 운반선 보냉재와 초저온 단열재를 공급하는 조선/LNG 밸류체인 기업",
        "analysis_focus": "LNG선 발주, 조선사 수주잔고, 보냉재 납품 마진, 원재료비, 환율",
        "watch_kpis": ["LNG선 발주", "수주잔고", "매출총이익률", "원재료비", "달러/원"],
    },
    "404650": {
        "company_name": "SOL KRX기후변화솔루션 ETF",
        "exchange": "KRX",
        "country": "KR",
        "asset_type": "etf",
        "sector": "ETF",
        "industry": "Climate Change Solutions",
        "business_context": "KRX 기후변화 솔루션 지수를 추종해 저탄소 전환 관련 국내 기업에 투자하는 ETF",
        "analysis_focus": "친환경 정책, 탄소저감 기술, 구성종목 이익 전망, 분배금, 거래 유동성",
        "watch_kpis": ["구성종목 실적", "정책 지원", "분배금", "거래대금", "탄소저감 투자"],
    },
    "414780": {
        "company_name": "TIGER 차이나과창판STAR50(합성) ETF",
        "exchange": "KRX",
        "country": "KR",
        "asset_type": "etf",
        "sector": "ETF",
        "industry": "China STAR 50",
        "business_context": "중국 과창판 STAR 50 지수를 합성 방식으로 추종하는 국내 상장 중국 기술주 ETF",
        "analysis_focus": "중국 기술주 정책, 위안화/원화 환율, 합성 ETF 거래상대방 리스크, 중국 경기",
        "watch_kpis": ["중국 기술주 정책", "위안화", "STAR 50 지수", "거래상대방 리스크", "중국 유동성"],
    },
    "200250": {
        "company_name": "KIWOOM 인도Nifty50(합성) ETF",
        "exchange": "KRX",
        "country": "KR",
        "asset_type": "etf",
        "sector": "ETF",
        "industry": "India Nifty 50",
        "business_context": "인도 Nifty 50 지수를 합성 방식으로 추종하는 국내 상장 인도 대표지수 ETF",
        "analysis_focus": "인도 성장률, 루피/원 환율, Nifty 50 밸류에이션, 합성 ETF 거래상대방 리스크",
        "watch_kpis": ["인도 GDP", "Nifty 50 EPS", "루피 환율", "외국인 수급", "거래상대방 담보비율"],
    },
    "361610": {
        "company_name": "SK아이이테크놀로지",
        "exchange": "KOSPI",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Materials/Technology",
        "industry": "Battery Separator",
        "business_context": "이차전지 분리막을 제조하는 SK그룹 계열 배터리 소재 기업",
        "analysis_focus": "분리막 수요, 전기차 배터리 사이클, 가동률, 고객사 재고조정, 수익성 회복",
        "watch_kpis": ["분리막 출하량", "가동률", "매출총이익률", "EV 배터리 수요", "현금흐름"],
    },
    "003230": {
        "company_name": "삼양식품",
        "exchange": "KOSPI",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Consumer Staples",
        "industry": "Packaged Foods",
        "business_context": "라면과 식품을 제조·판매하며 해외 매출 비중이 높은 한국 식품 기업",
        "analysis_focus": "해외 라면 수요, 수출 성장, 원가율, 환율, 브랜드 확장",
        "watch_kpis": ["해외 매출", "수출 성장률", "매출총이익률", "달러/원", "신제품 판매"],
    },
    "018260": {
        "company_name": "삼성에스디에스",
        "aliases": ["삼성SDS", "SAMSUNG SDS", "삼성에스디에스", "삼성에스디에스주식회사"],
        "exchange": "KOSPI",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Technology",
        "industry": "IT Services",
        "business_context": "삼성그룹 계열 IT 서비스 및 클라우드, 물류 BPO 사업을 영위하는 한국 IT 서비스 기업",
        "analysis_focus": "클라우드 전환, 생성형 AI/데이터센터 수요, 물류 BPO 마진, 그룹사 IT 투자, 배당 정책",
        "watch_kpis": ["클라우드 매출", "IT 서비스 영업이익률", "물류 BPO 매출", "그룹사 투자", "배당성향"],
    },
    "071050": {
        "company_name": "한국금융지주",
        "aliases": ["한국금융지주", "한국금융지주우", "한국투자금융지주", "Korea Investment Holdings"],
        "exchange": "KOSPI",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Financials",
        "industry": "Brokerage and Financial Holding",
        "business_context": "한국투자증권을 핵심 자회사로 둔 금융지주회사로 증권, 자산운용, 저축은행 등 금융 서비스를 영위합니다.",
        "analysis_focus": "증권 브로커리지/IB 실적, 운용손익, 금리와 시장 거래대금, 배당정책, 자본적정성",
        "watch_kpis": ["거래대금", "IB 수수료", "운용손익", "ROE", "배당성향"],
    },
    "189330": {
        "company_name": "씨이랩",
        "aliases": ["씨이랩", "씨아이랩", "XIIlab", "XIILAB", "씨이랩주식회사"],
        "exchange": "KOSDAQ",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Technology",
        "industry": "AI Data Platform",
        "business_context": "AI 영상 데이터 분석과 데이터셋 플랫폼, GPU/AI 인프라 관련 솔루션을 제공하는 국내 AI 소프트웨어 기업",
        "analysis_focus": "AI 데이터 플랫폼 수요, GPU 인프라 사업 전환, 공공·기업 고객 수주, 매출 성장률, 현금흐름과 유상증자 리스크",
        "watch_kpis": ["AI 플랫폼 매출", "신규 수주", "매출총이익률", "현금성 자산", "증자/희석 이벤트"],
    },
    "138080": {
        "company_name": "오이솔루션",
        "aliases": ["OE Solutions", "OESOLUTION", "오이솔루션", "오이솔루션주식회사"],
        "exchange": "KOSDAQ",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Technology",
        "industry": "Optical Communication Equipment",
        "business_context": "광트랜시버와 광통신 부품을 제조·판매하는 국내 통신장비 기업",
        "analysis_focus": "데이터센터/통신망 투자, 광트랜시버 수요, 고객사 발주, 수익성 회복, 재고 사이클",
        "watch_kpis": ["광트랜시버 매출", "수주/출하", "매출총이익률", "통신장비 투자", "재고 회전"],
    },
    "035510": {
        "company_name": "신세계I&C",
        "exchange": "KOSPI",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Technology",
        "industry": "Retail IT Services",
        "business_context": "신세계그룹 유통 IT, 클라우드, 리테일테크 서비스를 제공하는 IT 서비스 기업",
        "analysis_focus": "그룹 IT 투자, 클라우드/리테일테크 매출, 수익성, 신규 솔루션 확장",
        "watch_kpis": ["IT 서비스 매출", "영업이익률", "그룹 투자", "클라우드 매출", "배당"],
    },
    "036890": {
        "company_name": "진성티이씨",
        "exchange": "KOSDAQ",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Industrials",
        "industry": "Construction Machinery Parts",
        "business_context": "건설기계 하부주행체 부품과 산업기계 부품을 공급하는 기계 부품 기업",
        "analysis_focus": "글로벌 건설기계 수요, 고객사 재고, 원재료비, 환율, 수출 마진",
        "watch_kpis": ["건설기계 판매", "수출 매출", "매출총이익률", "원재료비", "달러/원"],
    },
    "089030": {
        "company_name": "테크윙",
        "exchange": "KOSDAQ",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Technology",
        "industry": "Semiconductor Equipment",
        "business_context": "반도체 후공정 테스트 핸들러와 관련 장비를 공급하는 반도체 장비 기업",
        "analysis_focus": "HBM/메모리 후공정 투자, 테스트 장비 수주, 고객사 CAPEX, 마진 회복",
        "watch_kpis": ["수주", "반도체 CAPEX", "HBM 투자", "영업이익률", "고객사 투자 계획"],
    },
    "112610": {
        "company_name": "씨에스윈드",
        "exchange": "KOSPI",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Industrials/Energy",
        "industry": "Wind Power Equipment",
        "business_context": "풍력 타워와 관련 부품을 글로벌 풍력발전 시장에 공급하는 신재생에너지 장비 기업",
        "analysis_focus": "풍력 설치 수요, 미국/유럽 정책, 수주와 마진, 운송비, 환율",
        "watch_kpis": ["풍력 수주", "매출총이익률", "미국 IRA 정책", "운송비", "달러/원"],
    },
    "377300": {
        "company_name": "카카오페이",
        "exchange": "KOSPI",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Financials/Technology",
        "industry": "Fintech Payments",
        "business_context": "간편결제, 금융 플랫폼, 대출·투자·보험 연계 서비스를 제공하는 핀테크 기업",
        "analysis_focus": "거래액, 금융 서비스 전환율, 규제, 수익화, 비용 통제",
        "watch_kpis": ["TPV", "활성 사용자", "금융서비스 매출", "영업손익", "규제 변화"],
    },
    "415640": {
        "company_name": "KB발해인프라",
        "exchange": "KRX",
        "country": "KR",
        "asset_type": "infrastructure_fund",
        "sector": "Infrastructure",
        "industry": "Listed Infrastructure Fund",
        "business_context": "인프라 자산에 투자해 배당과 안정적 현금흐름을 추구하는 국내 상장 인프라 펀드",
        "analysis_focus": "배당 안정성, 기초 인프라 자산 수익, 금리 민감도, 유동성",
        "watch_kpis": ["분배금", "금리", "자산 수익률", "부채비율", "거래대금"],
    },
    "253450": {
        "company_name": "스튜디오드래곤",
        "exchange": "KOSDAQ",
        "country": "KR",
        "asset_type": "equity",
        "sector": "Communication Services",
        "industry": "Media and Content Production",
        "business_context": "드라마와 영상 콘텐츠를 제작·유통하는 한국 대표 콘텐츠 제작사",
        "analysis_focus": "콘텐츠 판매, 글로벌 OTT 수요, 제작비 부담, 방영 편수, 마진 회복",
        "watch_kpis": ["방영 편수", "글로벌 판매", "영업이익률", "제작비", "OTT 계약"],
    },
    "CASH": {
        "company_name": "Cash Position",
        "exchange": "N/A",
        "country": "US",
        "asset_type": "cash",
    },
    "INBOX": {
        "company_name": "Unassigned Research Inbox",
        "exchange": "N/A",
        "country": "GLOBAL",
        "asset_type": "research_inbox",
        "sector": "Research",
        "industry": "Unassigned",
        "business_context": "티커를 자동 식별하지 못한 투자 정보가 임시로 저장되는 리서치 인박스",
        "analysis_focus": "티커 식별, 출처 분류, 투자 논거 연결 여부 확인",
        "watch_kpis": [
            "티커 식별 필요 항목",
            "출처 유형",
            "신뢰도",
            "후속 연결 필요 여부",
        ],
        "data_limitations": [
            "자동 캡처에서 티커를 확정하지 못해 임시 보관함에 저장된 항목입니다. 후속 분석 전 관련 티커로 재분류하세요.",
        ],
    },
    "MACRO": {
        "company_name": "Macro Research",
        "exchange": "N/A",
        "country": "GLOBAL",
        "asset_type": "macro_research",
        "sector": "Macro",
        "industry": "Economic Outlook",
        "business_context": "금리, 물가, 환율, 경기, 유동성, 정책 변화 등 특정 종목이 아닌 거시 투자 환경 리서치",
        "analysis_focus": "금리 경로, 인플레이션, 달러/환율, 경기 사이클, 중앙은행 정책, 자산배분 영향",
        "watch_kpis": ["정책금리", "물가", "고용", "달러", "장단기 금리", "신용 스프레드"],
    },
    "SECTOR": {
        "company_name": "Sector Research",
        "exchange": "N/A",
        "country": "GLOBAL",
        "asset_type": "sector_research",
        "sector": "Cross-sector",
        "industry": "Sector Trends",
        "business_context": "특정 종목보다 산업, 테마, 섹터별 수급과 실적 사이클을 다루는 투자 동향 리서치",
        "analysis_focus": "섹터 상대강도, 이익 전망, 수급, 밸류에이션, 정책/기술 변화 수혜",
        "watch_kpis": ["섹터 EPS 전망", "상대 수익률", "밸류에이션 스프레드", "수급", "주요 테마"],
    },
    "MARKET": {
        "company_name": "Market Strategy Research",
        "exchange": "N/A",
        "country": "GLOBAL",
        "asset_type": "market_research",
        "sector": "Market",
        "industry": "Investment Flows",
        "business_context": "시장 전체 흐름, 투자자 포지셔닝, 자금 흐름, 위험선호 변화를 다루는 리서치",
        "analysis_focus": "자금 흐름, 위험선호, 포지셔닝, 변동성, 시장 폭, 스타일 로테이션",
        "watch_kpis": ["자금 유입/유출", "VIX", "시장 폭", "스타일 로테이션", "신용 스프레드"],
    },
    "POLICY": {
        "company_name": "Policy Research",
        "exchange": "N/A",
        "country": "GLOBAL",
        "asset_type": "policy_research",
        "sector": "Policy",
        "industry": "Government and Regulation",
        "business_context": "정부 정책, 중앙은행 발언, 규제, 관세, 재정 지출, 선거와 지정학 이벤트가 자산시장에 미치는 영향 리서치",
        "analysis_focus": "정책 변화의 방향, 수혜/피해 섹터, 규제 리스크, 재정/통상 정책, 지정학 리스크",
        "watch_kpis": ["정책 발표", "규제 변화", "관세", "재정 지출", "중앙은행 발언", "지정학 이벤트"],
    },
    "RATES": {
        "company_name": "Rates Research",
        "exchange": "N/A",
        "country": "GLOBAL",
        "asset_type": "rates_research",
        "sector": "Rates",
        "industry": "Rates and Inflation",
        "business_context": "정책금리, 국채금리, 물가, 인플레이션 기대, 달러와 신용 스프레드가 투자 환경에 미치는 영향 리서치",
        "analysis_focus": "금리 경로, 장단기 금리, 인플레이션, 달러, 신용 스프레드, 성장주/가치주 민감도",
        "watch_kpis": ["정책금리", "10년물 금리", "2년물 금리", "CPI", "PCE", "달러지수", "신용 스프레드"],
    },
    "FLOWS": {
        "company_name": "Flows Research",
        "exchange": "N/A",
        "country": "GLOBAL",
        "asset_type": "flows_research",
        "sector": "Flows",
        "industry": "Market Flows and Positioning",
        "business_context": "외국인/기관/개인 수급, ETF·펀드 자금 흐름, 포지셔닝, 시장 폭과 로테이션을 다루는 리서치",
        "analysis_focus": "순매수/순매도, ETF 자금 흐름, 투자자 포지셔닝, 시장 폭, 스타일/섹터 로테이션",
        "watch_kpis": ["외국인 순매수", "기관 순매수", "ETF 자금 흐름", "포지셔닝", "시장 폭", "로테이션"],
    },
    "CUSTOMS": {
        "company_name": "Korea Customs Trade Research",
        "exchange": "N/A",
        "country": "KR",
        "asset_type": "macro_research",
        "sector": "Trade",
        "industry": "Exports Imports Inventory",
        "business_context": "관세청 품목·국가별 수출입 실적을 통해 한국 수출주, 섹터 사이클, 원재료·재고 부담을 추적하는 리서치",
        "analysis_focus": "1일·11일·21일 발표 수출입 동향, 품목별 수출입 금액, 국가별 수요, 재고 부담 가능성",
        "watch_kpis": ["수출금액", "수입금액", "무역수지", "수출중량", "수입중량", "품목별 국가 분포"],
    },
}

SPECIAL_RESEARCH_KEYS = {"INBOX", "MACRO", "SECTOR", "MARKET", "MARKET-US", "MARKET-KR", "MARKET-GLOBAL", "POLICY", "RATES", "FLOWS", "CUSTOMS"}


DYNAMIC_TICKER_REGISTRY: dict[str, dict] = {}
TICKER_LOOKUP_DIAGNOSTICS: dict[str, list[dict]] = {}
PORTFOLIO_PRICE_CACHE: dict[str, tuple[float, str | None]] = {}
PORTFOLIO_HISTORY_CACHE: dict[str, list[dict]] = {}


def normalize_ticker(ticker: str) -> str:
    normalized = sub(r"[^A-Za-z0-9._-]+", "-", ticker.strip().upper()).strip("-")
    return normalized or "UNKNOWN"


def dynamic_ticker_cache_path(settings: Settings | None = None) -> Path:
    active_settings = settings or get_settings()
    return resolve_vault_dir(active_settings.research_vault_dir) / "_system" / "ticker_registry_cache.json"


def read_dynamic_ticker_registry(settings: Settings | None = None) -> dict[str, dict]:
    if DYNAMIC_TICKER_REGISTRY:
        return DYNAMIC_TICKER_REGISTRY
    try:
        cache_path = dynamic_ticker_cache_path(settings)
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                DYNAMIC_TICKER_REGISTRY.update(
                    {
                        normalize_ticker(symbol): profile
                        for symbol, profile in payload.items()
                        if isinstance(profile, dict)
                    }
                )
    except Exception:
        return DYNAMIC_TICKER_REGISTRY
    return DYNAMIC_TICKER_REGISTRY


def persist_dynamic_ticker_registry(
    registry: dict[str, dict],
    settings: Settings | None = None,
) -> None:
    cache_path = dynamic_ticker_cache_path(settings)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_dynamic_ticker_profile(
    symbol: str,
    profile: dict,
    settings: Settings | None = None,
) -> None:
    normalized_symbol = normalize_ticker(symbol)
    DYNAMIC_TICKER_REGISTRY[normalized_symbol] = profile
    try:
        existing = read_dynamic_ticker_registry(settings)
        persist_dynamic_ticker_registry(existing, settings)
    except Exception:
        return


def delete_dynamic_ticker_profile(
    symbol: str,
    settings: Settings | None = None,
) -> bool:
    normalized_symbol = normalize_ticker(symbol)
    registry = dict(read_dynamic_ticker_registry(settings))
    deleted = normalized_symbol in registry
    registry.pop(normalized_symbol, None)
    DYNAMIC_TICKER_REGISTRY.clear()
    DYNAMIC_TICKER_REGISTRY.update(registry)
    persist_dynamic_ticker_registry(registry, settings)
    return deleted


def ticker_registry_cache_entries(settings: Settings | None = None) -> list[dict]:
    registry = read_dynamic_ticker_registry(settings)
    entries = []
    for symbol, profile in sorted(registry.items()):
        entries.append(
            {
                "ticker": symbol,
                "company_name": profile.get("company_name", ""),
                "exchange": profile.get("exchange", ""),
                "country": profile.get("country", ""),
                "asset_type": profile.get("asset_type", "equity"),
                "sector": profile.get("sector"),
                "industry": profile.get("industry"),
                "verification_source": profile.get(
                    "verification_source",
                    "dynamic_ticker_cache",
                ),
                "data_limitations": profile.get("data_limitations", []),
            }
        )
    return entries


def exchange_display_name(value: str | None) -> str:
    exchange = str(value or "").upper()
    labels = {
        "NASDAQ": "NASDAQ",
        "NAS": "NASDAQ",
        "NYSE": "NYSE",
        "NYS": "NYSE",
        "AMEX": "NYSE American",
    }
    return labels.get(exchange, value or "UNKNOWN")


def fmp_api_key(settings: Settings) -> str:
    key = settings.fmp_api_key.strip()
    if key.lower().startswith("apikey="):
        return key.split("=", 1)[1].strip()
    return key


def fmp_legacy_base_url(settings: Settings) -> str:
    base_url = settings.fmp_base_url.rstrip("/")
    if base_url.endswith("/stable"):
        return base_url[: -len("/stable")] + "/api/v3"
    return base_url


def provider_error_message(error: Exception, settings: Settings) -> str:
    message = str(error)
    api_key = fmp_api_key(settings)
    if api_key:
        message = message.replace(api_key, "****")
    return message



def earnings_calendar_cache_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "earnings_calendar_cache.json"


def read_earnings_calendar_cache(settings: Settings) -> dict:
    path = earnings_calendar_cache_path(settings)
    if not path.exists():
        return {"entries": {}}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"entries": {}}
    if not isinstance(payload, dict):
        return {"entries": {}}
    payload.setdefault("entries", {})
    return payload


def write_earnings_calendar_cache(settings: Settings, payload: dict) -> None:
    path = earnings_calendar_cache_path(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    cache_text = json.dumps(payload, ensure_ascii=False, indent=2)
    temp_path = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temp_path.write_text(cache_text, encoding="utf-8")
    temp_path.replace(path)


def parse_iso_datetime(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        try:
            parsed = parsed.replace(tzinfo=ZoneInfo("Asia/Seoul"))
        except ZoneInfoNotFoundError:
            parsed = parsed.replace(tzinfo=timezone(timedelta(hours=9)))
    return parsed


def earnings_calendar_entry_has_usable_data(entry: dict | None) -> bool:
    if not isinstance(entry, dict):
        return False
    if entry.get("status") == "success":
        return True
    return bool(
        entry.get("latest_reported_earnings_date")
        or entry.get("next_earnings_date")
        or entry.get("events")
        or entry.get("latest_earnings_profile")
    )


def current_storage_datetime() -> datetime:
    try:
        korea_timezone = ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        korea_timezone = timezone(timedelta(hours=9))
    return datetime.now(korea_timezone)


def earnings_calendar_entry_is_stale(entry: dict | None, settings: Settings) -> bool:
    if not earnings_calendar_entry_has_usable_data(entry):
        return True
    updated_at = parse_iso_datetime(entry.get("updated_at"))
    if not updated_at:
        return True
    max_age = timedelta(minutes=max(float(settings.live_data_max_age_minutes), 1.0))
    return current_storage_datetime() - updated_at > max_age


def parse_iso_date(value: object) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def event_date_value(event: dict) -> date | None:
    return parse_iso_date(
        event.get("date")
        or event.get("earningsDate")
        or event.get("reportDate")
        or event.get("pricedate")
    )


def compact_earnings_event(event: dict) -> dict:
    return {
        "date": str(event.get("date") or event.get("earningsDate") or event.get("reportDate") or "")[:10],
        "symbol": event.get("symbol"),
        "time": event.get("time") or event.get("when") or event.get("hour"),
        "eps": event.get("eps") or event.get("epsActual"),
        "eps_estimated": event.get("epsEstimated") or event.get("epsEstimate"),
        "revenue": event.get("revenue") or event.get("revenueActual"),
        "revenue_estimated": event.get("revenueEstimated") or event.get("revenueEstimate"),
        "fiscal_date_ending": event.get("fiscalDateEnding") or event.get("fiscalDate"),
        "updated_from_date": event.get("updatedFromDate"),
    }


def quarter_for_cached_earnings_date(profile: dict, target_date: str | None) -> str | None:
    parsed = parse_iso_date(target_date)
    if not parsed:
        return None
    calendar = profile.get("earnings_dates_by_quarter") or {}
    if isinstance(calendar, dict):
        best_label = None
        best_gap = 999
        for label, value in calendar.items():
            value_date = parse_iso_date(value)
            if not value_date:
                continue
            gap = abs((value_date - parsed).days)
            if gap < best_gap:
                best_label = str(label)
                best_gap = gap
        if best_label and best_gap <= 45:
            return best_label
    return profile.get("latest_reported_quarter")


def fmp_earnings_calendar_candidates(settings: Settings) -> list[tuple[str, str]]:
    return [
        (settings.fmp_base_url.rstrip("/"), "earnings-calendar"),
        (settings.fmp_base_url.rstrip("/"), "earning-calendar"),
        (fmp_legacy_base_url(settings), "earning_calendar"),
    ]


def fetch_fmp_earnings_calendar_events(ticker: str, settings: Settings) -> tuple[list[dict], str]:
    api_key = fmp_api_key(settings)
    if not api_key or api_key == "********":
        raise RuntimeError("FMP_API_KEY가 설정되지 않았습니다.")
    today = current_storage_date()
    params = {
        "symbol": ticker,
        "from": (today - timedelta(days=730)).isoformat(),
        "to": (today + timedelta(days=365)).isoformat(),
        "apikey": api_key,
    }
    errors: list[str] = []
    for base_url, endpoint in fmp_earnings_calendar_candidates(settings):
        try:
            response = httpx.get(
                f"{base_url}/{endpoint.lstrip('/')}",
                params=params,
                timeout=settings.fmp_timeout_seconds,
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                if isinstance(payload.get("historical"), list):
                    payload = payload["historical"]
                elif isinstance(payload.get("data"), list):
                    payload = payload["data"]
            if not isinstance(payload, list):
                raise RuntimeError("응답 형식이 리스트가 아닙니다.")
            normalized_ticker = normalize_ticker(ticker)
            events = [
                compact_earnings_event(item)
                for item in payload
                if isinstance(item, dict)
                and normalize_ticker(str(item.get("symbol") or ticker)) == normalized_ticker
                and event_date_value(item)
            ]
            if events:
                return sorted(events, key=lambda item: item.get("date") or ""), f"FMP {endpoint}"
            errors.append(f"{endpoint}: 일정 데이터 없음")
        except Exception as exc:
            errors.append(f"{endpoint}: {provider_error_message(exc, settings)}")
    raise RuntimeError("; ".join(errors[-3:]))

def fetch_finnhub_earnings_calendar_events(ticker: str, settings: Settings) -> tuple[list[dict], str]:
    api_key = settings.finnhub_api_key.strip()
    if not api_key or api_key == "********":
        raise RuntimeError("FINNHUB_API_KEY가 설정되지 않았습니다.")
    today = current_storage_date()
    params = {
        "symbol": ticker,
        "from": (today - timedelta(days=730)).isoformat(),
        "to": (today + timedelta(days=365)).isoformat(),
        "token": api_key,
    }
    response = httpx.get(
        f"{settings.finnhub_base_url.rstrip('/')}/calendar/earnings",
        params=params,
        timeout=settings.finnhub_timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    events_payload = payload.get("earningsCalendar") if isinstance(payload, dict) else []
    if not isinstance(events_payload, list):
        raise RuntimeError("Finnhub 응답 형식이 리스트가 아닙니다.")
    normalized_ticker = normalize_ticker(ticker)
    events = [
        compact_earnings_event(item)
        for item in events_payload
        if isinstance(item, dict)
        and normalize_ticker(str(item.get("symbol") or ticker)) == normalized_ticker
        and event_date_value(item)
    ]
    if not events:
        raise RuntimeError("Finnhub 일정 데이터 없음")
    return sorted(events, key=lambda item: item.get("date") or ""), "Finnhub calendar/earnings"


def build_earnings_calendar_cache_entry(ticker: str, settings: Settings) -> dict:
    profile = verified_profile_for_ticker(ticker, settings) or OFFICIAL_TICKER_REGISTRY.get(ticker, {})
    errors: list[str] = []
    try:
        events, source = fetch_fmp_earnings_calendar_events(ticker, settings)
    except Exception as exc:
        errors.append(f"FMP: {provider_error_message(exc, settings)}")
        try:
            events, source = fetch_finnhub_earnings_calendar_events(ticker, settings)
        except Exception as fallback_exc:
            errors.append(f"Finnhub: {provider_error_message(fallback_exc, settings)}")
            raise RuntimeError("; ".join(errors)) from fallback_exc
    today = current_storage_date()
    dated_events = [(event_date_value(event), event) for event in events]
    dated_events = [(event_date, event) for event_date, event in dated_events if event_date]
    past = [(event_date, event) for event_date, event in dated_events if event_date <= today]
    future = [(event_date, event) for event_date, event in dated_events if event_date > today]
    latest = past[-1] if past else None
    previous = past[-2] if len(past) >= 2 else None
    next_event = future[0] if future else None
    latest_event = latest[1] if latest else None
    latest_date = latest[0].isoformat() if latest else None
    latest_quarter = quarter_for_cached_earnings_date(profile, latest_date) if latest_date else None
    return {
        "ticker": ticker,
        "status": "success",
        "updated_at": current_storage_timestamp(),
        "source": source,
        "events": events[-12:],
        "latest_reported_quarter": latest_quarter,
        "latest_reported_earnings_date": latest_date,
        "previous_earnings_date": previous[0].isoformat() if previous else None,
        "next_earnings_date": next_event[0].isoformat() if next_event else None,
        "latest_earnings_profile": {
            "quarter": latest_quarter,
            "earnings_report_date": latest_date,
            "eps_reported": latest_event.get("eps") if latest_event else None,
            "eps_expected": latest_event.get("eps_estimated") if latest_event else None,
            "revenue_reported": latest_event.get("revenue") if latest_event else None,
            "revenue_expected": latest_event.get("revenue_estimated") if latest_event else None,
            "source_url": source,
        } if latest_event else {},
    }


def refresh_earnings_calendar_for_ticker_if_stale(
    ticker: str,
    settings: Settings,
    *,
    force: bool = False,
) -> dict:
    normalized = normalize_ticker(ticker)
    cache = read_earnings_calendar_cache(settings)
    entry = (cache.get("entries") or {}).get(normalized)
    if not force and not settings.earnings_calendar_on_demand_refresh:
        return {"status": "skipped", "ticker": normalized, "reason": "on_demand_disabled"}
    if not force and not earnings_calendar_entry_is_stale(entry, settings):
        return {
            "status": "fresh",
            "ticker": normalized,
            "updated_at": entry.get("updated_at") if isinstance(entry, dict) else None,
        }
    return refresh_earnings_calendar_cache(settings, [normalized])


def merge_cached_earnings_calendar(
    ticker: str,
    profile: dict,
    settings: Settings | None = None,
    *,
    refresh: bool = True,
) -> dict:
    if not settings or not profile:
        return profile
    if refresh and settings.earnings_calendar_on_demand_refresh:
        try:
            refresh_earnings_calendar_for_ticker_if_stale(ticker, settings)
        except Exception:
            pass
    cache = read_earnings_calendar_cache(settings)
    entry = (cache.get("entries") or {}).get(normalize_ticker(ticker))
    if not earnings_calendar_entry_has_usable_data(entry):
        return profile
    enriched = dict(profile)
    for key in [
        "latest_reported_quarter",
        "latest_reported_earnings_date",
        "previous_earnings_date",
        "next_earnings_date",
    ]:
        if entry.get(key):
            enriched[key] = entry[key]
    source = entry.get("source") or "FMP/Finnhub earnings calendar cache"
    enriched["earnings_calendar_source"] = f"{source} · 캐시 갱신 {entry.get('updated_at', '미확인')}"
    limitations = [
        item for item in enriched.get("data_limitations", [])
        if "실적 캘린더는 로컬 공식 티커 프로필" not in str(item)
    ]
    limitations.append(f"실적 캘린더 자동 추적이 적용되었습니다. 출처: {source}.")
    enriched["data_limitations"] = limitations
    cached_profile = entry.get("latest_earnings_profile") or {}
    if isinstance(cached_profile, dict) and cached_profile:
        latest_profile = dict(enriched.get("latest_earnings_profile") or {})
        for key, value in cached_profile.items():
            if value not in (None, ""):
                latest_profile[key] = value
        latest_profile.setdefault("source_url", source)
        enriched["latest_earnings_profile"] = latest_profile
    return enriched


def portfolio_calendar_tickers(settings: Settings) -> list[str]:
    tickers: set[str] = set()
    try:
        store = read_portfolio_store(settings)
        for portfolio in (store.get("portfolios") or {}).values():
            if not isinstance(portfolio, dict):
                continue
            for holding in portfolio.get("holdings") or []:
                if isinstance(holding, dict) and holding.get("ticker"):
                    tickers.add(ensure_verified_ticker(str(holding["ticker"]), settings))
    except Exception:
        pass
    if not tickers:
        tickers.add("PL")
    return sorted(tickers)


def refresh_earnings_calendar_cache(settings: Settings, tickers: list[str] | None = None) -> dict:
    cache = read_earnings_calendar_cache(settings)
    entries = cache.setdefault("entries", {})
    selected_tickers = [normalize_ticker(item) for item in (tickers or portfolio_calendar_tickers(settings))]
    refreshed: list[str] = []
    failed: list[dict] = []
    for ticker in selected_tickers:
        try:
            entry = build_earnings_calendar_cache_entry(ticker, settings)
            entries[ticker] = entry
            refreshed.append(ticker)
        except Exception as exc:
            existing = entries.get(ticker, {}) if isinstance(entries.get(ticker), dict) else {}
            failed_entry = {
                **existing,
                "ticker": ticker,
                "last_refresh_attempt_at": current_storage_timestamp(),
                "last_refresh_error": provider_error_message(exc, settings),
                "refresh_status": "failed",
            }
            if earnings_calendar_entry_has_usable_data(existing):
                failed_entry["status"] = "success"
            else:
                failed_entry["status"] = "failed"
                failed_entry["updated_at"] = current_storage_timestamp()
                failed_entry["error"] = provider_error_message(exc, settings)
            entries[ticker] = failed_entry
            failed.append({"ticker": ticker, "error": provider_error_message(exc, settings)})
    cache["updated_at"] = current_storage_timestamp()
    cache["source"] = "FMP/Finnhub earnings calendar"
    cache_write_warning = None
    try:
        write_earnings_calendar_cache(settings, cache)
    except Exception as exc:
        cache_write_warning = provider_error_message(exc, settings)
    return {
        "status": "success",
        "module": "earnings_calendar_cache",
        "requested_count": len(selected_tickers),
        "refreshed_count": len(refreshed),
        "failed_count": len(failed),
        "refreshed": refreshed,
        "failed": failed,
        "cache_write_warning": cache_write_warning,
        "cache_path": str(earnings_calendar_cache_path(settings)),
    }


_EARNINGS_CALENDAR_SCHEDULER_STARTED = False


def earnings_calendar_scheduler_loop() -> None:
    settings = get_settings()
    interval_seconds = max(settings.earnings_calendar_refresh_hours, 1) * 3600
    while True:
        try:
            refresh_earnings_calendar_cache(settings)
        except Exception:
            pass
        threading.Event().wait(interval_seconds)


def start_earnings_calendar_scheduler() -> None:
    global _EARNINGS_CALENDAR_SCHEDULER_STARTED
    settings = get_settings()
    if _EARNINGS_CALENDAR_SCHEDULER_STARTED or not settings.earnings_calendar_auto_refresh:
        return
    _EARNINGS_CALENDAR_SCHEDULER_STARTED = True
    thread = threading.Thread(
        target=earnings_calendar_scheduler_loop,
        name="earnings-calendar-refresh",
        daemon=True,
    )
    thread.start()


def dart_filing_cache_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "dart_filing_watch_cache.json"


def read_dart_filing_cache(settings: Settings) -> dict:
    return read_json_store(
        dart_filing_cache_path(settings),
        {"updated_at": None, "entries": {}, "last_run": None},
    )


def write_dart_filing_cache(settings: Settings, payload: dict) -> None:
    write_json_store(dart_filing_cache_path(settings), payload)


def recent_dart_cache_entries(cache: dict, ticker: str | None = None, limit: int = 5) -> list[dict]:
    normalized_ticker = normalize_ticker(ticker or "")
    entries = list((cache.get("entries") or {}).values())
    if normalized_ticker:
        entries = [entry for entry in entries if normalize_ticker(entry.get("ticker") or "") == normalized_ticker]
    entries.sort(
        key=lambda entry: (
            str(entry.get("detected_at") or ""),
            str(((entry.get("filing") or {}).get("receipt_date")) or ""),
        ),
        reverse=True,
    )
    return entries[:limit]


def build_dart_filing_signal(ticker: str, settings: Settings) -> dict:
    cache = read_dart_filing_cache(settings)
    normalized_ticker = normalize_ticker(ticker)
    recent_entries = recent_dart_cache_entries(cache, normalized_ticker, limit=3)
    failures = [
        item
        for item in (cache.get("last_failures") or [])
        if normalize_ticker(str((item or {}).get("ticker") or "")) == normalized_ticker
    ]
    latest_entry = recent_entries[0] if recent_entries else {}
    filing = latest_entry.get("filing") or {}
    latest_failure = failures[0] if failures else {}
    important_count = sum(1 for entry in recent_entries if entry.get("importance") == "높음")
    ownership_count = sum(
        1
        for entry in recent_entries
        if any(tag in (entry.get("tags") or []) for tag in ["ownership", "flows"])
    )
    periodic_count = sum(
        1
        for entry in recent_entries
        if any(tag in (entry.get("tags") or []) for tag in ["earnings", "financials"])
    )
    if recent_entries:
        tone = "warning" if important_count else "ok"
        headline = f"{filing.get('report_name') or '공시명 미확인'}"
        signal_bits = []
        if important_count:
            signal_bits.append(f"중요 공시 {important_count}건")
        if periodic_count:
            signal_bits.append(f"정기보고서/재무 {periodic_count}건")
        if ownership_count:
            signal_bits.append(f"지분·수급 {ownership_count}건")
        summary = (
            f"{', '.join(signal_bits)} 감지. {latest_entry.get('action') or '최근 DART 공시를 투자 논거와 리스크에 반영하세요.'}"
            if signal_bits
            else latest_entry.get("action") or "최근 DART 공시가 감지되었습니다."
        )
    elif latest_failure:
        tone = "warning"
        headline = "최근 조회 실패"
        summary = provider_error_message(latest_failure.get("error") or "DART 접속 실패", settings)
    else:
        tone = "neutral"
        headline = "신규 공시 없음"
        summary = "최근 자동 감시 캐시에 이 종목의 신규 DART 공시가 없습니다."
    return {
        "enabled": bool(settings.dart_filing_auto_refresh and settings.dart_api_key),
        "configured": bool(settings.dart_api_key),
        "ticker": normalized_ticker,
        "tone": tone,
        "headline": headline,
        "summary": summary,
        "updated_at": cache.get("updated_at"),
        "last_run": cache.get("last_run"),
        "lookback_days": settings.dart_filing_lookback_days,
        "refresh_hours": settings.dart_filing_refresh_hours,
        "recent_count": len(recent_entries),
        "important_count": important_count,
        "ownership_count": ownership_count,
        "periodic_count": periodic_count,
        "failure_count": len(failures),
        "recent_entries": recent_entries,
        "latest_failure": latest_failure,
    }


def summarize_dart_filing_context(signal: dict | None) -> str:
    if not isinstance(signal, dict) or not signal.get("recent_count"):
        return ""
    entries = signal.get("recent_entries") or []
    snippets: list[str] = []
    for entry in entries[:3]:
        filing = entry.get("filing") or {}
        report_name = filing.get("report_name") or "공시명 미확인"
        receipt_date = filing.get("receipt_date") or "날짜 미확인"
        importance = entry.get("importance") or "보통"
        action = entry.get("action") or "기존 투자 논거와 관련성을 확인하세요."
        snippets.append(f"{receipt_date} {report_name}({importance}) - {action}")
    return " / ".join(snippets)


def dart_cache_needs_ticker_refresh(cache: dict, ticker: str, settings: Settings) -> bool:
    normalized_ticker = normalize_ticker(ticker)
    updated_at = parse_iso_datetime(cache.get("updated_at"))
    if not updated_at:
        return True
    max_age = timedelta(minutes=max(float(settings.live_data_max_age_minutes), 1.0))
    if current_storage_datetime() - updated_at > max_age:
        return True
    return not recent_dart_cache_entries(cache, normalized_ticker, limit=1)


def refresh_dart_filing_for_ticker_if_stale(ticker: str, settings: Settings) -> dict:
    normalized_ticker = normalize_ticker(ticker)
    if not (settings.dart_filing_auto_refresh and settings.dart_api_key):
        return {"status": "skipped", "ticker": normalized_ticker, "reason": "dart_disabled"}
    if not fullmatch(r"\d{6}", normalized_ticker):
        return {"status": "skipped", "ticker": normalized_ticker, "reason": "non_kr_ticker"}
    cache = read_dart_filing_cache(settings)
    if not dart_cache_needs_ticker_refresh(cache, normalized_ticker, settings):
        return {"status": "fresh", "ticker": normalized_ticker, "updated_at": cache.get("updated_at")}
    try:
        return refresh_dart_filing_watch(
            settings,
            [normalized_ticker],
            force=False,
            save_result=False,
        )
    except Exception as exc:
        return {
            "status": "failed",
            "ticker": normalized_ticker,
            "error": provider_error_message(exc, settings),
        }


def dart_periodic_quarter_label(report_name: str, receipt_date: str | None) -> str | None:
    name = str(report_name or "")
    if not any(keyword in name for keyword in ["사업보고서", "반기보고서", "분기보고서"]):
        return None
    period_match = search(r"\((20\d{2})[.\-/년\s]*(0?[369]|1[012])", name)
    report_year = None
    report_month = None
    if period_match:
        report_year = int(period_match.group(1))
        report_month = int(period_match.group(2))
    elif receipt_date and fullmatch(r"\d{8}", receipt_date):
        receipt_year = int(receipt_date[:4])
        if "사업보고서" in name:
            report_year = receipt_year - 1
            report_month = 12
        else:
            report_year = receipt_year
            report_month = 6 if "반기보고서" in name else 3
    if not report_year or not report_month:
        return None
    if "사업보고서" in name or report_month == 12:
        return f"FY{report_year} Annual"
    if "반기보고서" in name or report_month == 6:
        return f"FY{report_year} Q2"
    if report_month == 9:
        return f"FY{report_year} Q3"
    return f"FY{report_year} Q1"


def korean_earnings_neighbor_dates(quarter_label: str | None) -> tuple[str | None, str | None]:
    if not quarter_label:
        return None, None
    match = search(r"FY(\d{4})\s+(Annual|Q[123])", quarter_label)
    if not match:
        return None, None
    year = int(match.group(1))
    period = match.group(2)
    if period == "Annual":
        return date(year, 11, 14).isoformat(), date(year + 1, 5, 15).isoformat()
    if period == "Q1":
        return date(year, 3, 31).isoformat(), date(year, 8, 14).isoformat()
    if period == "Q2":
        return date(year, 5, 15).isoformat(), date(year, 11, 14).isoformat()
    if period == "Q3":
        return date(year, 8, 14).isoformat(), date(year + 1, 3, 31).isoformat()
    return None, None


def merge_dart_latest_earnings_calendar(ticker: str, profile: dict, settings: Settings | None) -> dict:
    if not settings or not profile or profile.get("country") != "KR":
        return profile
    normalized_ticker = normalize_ticker(ticker)
    refresh_dart_filing_for_ticker_if_stale(normalized_ticker, settings)
    signal = build_dart_filing_signal(normalized_ticker, settings)
    entries = []
    for entry in signal.get("recent_entries") or []:
        filing = entry.get("filing") or {}
        report_name = str(filing.get("report_name") or "")
        quarter_label = dart_periodic_quarter_label(report_name, filing.get("receipt_date"))
        receipt_date = str(filing.get("receipt_date") or "")
        if quarter_label and fullmatch(r"\d{8}", receipt_date):
            entries.append((receipt_date, quarter_label, filing))
    if not entries:
        return profile
    receipt_date, quarter_label, filing = sorted(entries, key=lambda item: item[0], reverse=True)[0]
    latest_date = datetime.strptime(receipt_date, "%Y%m%d").date().isoformat()
    current_latest = parse_iso_date(profile.get("latest_reported_earnings_date"))
    if current_latest and parse_iso_date(latest_date) and parse_iso_date(latest_date) < current_latest:
        return profile
    previous_date, next_date = korean_earnings_neighbor_dates(quarter_label)
    enriched = dict(profile)
    enriched["latest_reported_quarter"] = quarter_label
    enriched["latest_reported_earnings_date"] = latest_date
    if previous_date:
        enriched["previous_earnings_date"] = previous_date
    if next_date:
        enriched["next_earnings_date"] = next_date
    source_url = filing.get("source_url") or "https://dart.fss.or.kr/"
    enriched["earnings_calendar_source"] = (
        f"OpenDART 신규 공시 목록 · {filing.get('report_name') or '정기보고서'} "
        f"접수일 {latest_date}"
    )
    latest_profile = dict(enriched.get("latest_earnings_profile") or {})
    latest_profile.update(
        {
            "quarter": quarter_label,
            "earnings_report_date": latest_date,
            "previous_earnings_summary": (
                f"DART에서 {filing.get('report_name') or '정기보고서'} 접수가 확인되어 "
                f"최신 실적 기준을 {quarter_label}로 갱신했습니다."
            ),
            "next_earnings_guidance": (
                "다음 실적 전 확인할 KPI: "
                + ", ".join(str(item) for item in (enriched.get("watch_kpis") or [])[:5])
            ),
            "source_url": source_url,
        }
    )
    enriched["latest_earnings_profile"] = latest_profile
    limitations = [
        item for item in enriched.get("data_limitations", [])
        if "DART 정기보고서 제출 기한 기준" not in str(item)
    ]
    limitations.append("DART 신규 공시 목록으로 최신 실적 기준일을 보정했습니다.")
    enriched["data_limitations"] = limitations
    return enriched


def dart_watch_tickers(settings: Settings) -> list[str]:
    tickers: set[str] = set()
    try:
        store = read_portfolio_store(settings)
        for portfolio in (store.get("portfolios") or {}).values():
            if not isinstance(portfolio, dict):
                continue
            for holding in portfolio.get("holdings") or []:
                ticker = normalize_ticker(str((holding or {}).get("ticker") or ""))
                if fullmatch(r"\d{6}", ticker):
                    tickers.add(ticker)
    except Exception:
        pass
    try:
        interests = read_interest_list(settings)
        for item in interests.get("tickers", []):
            if not isinstance(item, dict):
                continue
            ticker = normalize_ticker(str(item.get("ticker") or ""))
            if fullmatch(r"\d{6}", ticker):
                tickers.add(ticker)
    except Exception:
        pass
    return sorted(tickers)


def dart_filing_importance(report_name: str) -> tuple[str, str, list[str]]:
    name = report_name or ""
    tags = ["dart", "official_filing", "공시"]
    if any(keyword in name for keyword in ["사업보고서", "반기보고서", "분기보고서"]):
        return "높음", "정기보고서: 실적/재무/사업 리스크 업데이트 필요", tags + ["earnings", "financials"]
    if "주요사항보고서" in name:
        return "높음", "주요사항보고서: 투자 판단 변화 가능성이 큰 이벤트", tags + ["event", "risk"]
    if any(keyword in name for keyword in ["대량보유", "임원", "최대주주", "소유상황"]):
        return "중간", "지분/임원/주주 변화: 수급과 지배구조 확인 필요", tags + ["ownership", "flows"]
    if any(keyword in name for keyword in ["증권신고서", "투자설명서", "유상증자", "전환사채"]):
        return "높음", "자금조달/희석 가능성: 밸류에이션과 리스크 재점검 필요", tags + ["financing", "dilution"]
    return "보통", "일반 공시: 기존 투자 논거와 관련성 확인", tags


def dart_filing_cache_key(ticker: str, filing: dict) -> str:
    return f"{normalize_ticker(ticker)}:{filing.get('rcept_no') or ''}"


def render_dart_filing_markdown(ticker: str, filing: dict, importance: str, action: str) -> str:
    company = filing.get("corp_name") or ticker
    report_name = filing.get("report_name") or "공시명 미확인"
    receipt_date = filing.get("receipt_date") or "날짜 미확인"
    source_url = filing.get("source_url") or "https://dart.fss.or.kr/"
    return f"""# DART 신규 공시 감시

티커: {ticker}
회사: {company}
공시명: {report_name}
접수일: {receipt_date}
중요도: {importance}
원문: {source_url}

## 자동 판단
- {action}
- 보유종목/관심종목에 포함된 한국 종목에서 신규 공시가 감지되었습니다.
- 다음 팀 리포트, 리스크 스캔, 실적 분석 실행 시 공식 공시 근거로 함께 활용합니다.

## 확인할 것
- 이번 공시가 매출, 마진, 현금흐름, 지분 구조, 자금조달, 경영 리스크 중 어느 항목을 바꾸는지 확인
- 기존 강세/약세 논거와 충돌하는 내용이 있는지 확인
- 주가 반응과 수급 변화를 다음 거래일에 점검
"""


def save_dart_filing_watch_item(ticker: str, filing: dict, settings: Settings) -> ResearchStorageInfo:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    importance, action, tags = dart_filing_importance(str(filing.get("report_name") or ""))
    markdown = render_dart_filing_markdown(ticker, filing, importance, action)
    receipt_date_text = str(filing.get("receipt_date") or "")
    try:
        report_date = datetime.strptime(receipt_date_text, "%Y%m%d").date()
    except ValueError:
        report_date = date.today()
    payload = {
        "module": "dart_filing_watch",
        "ticker": ticker,
        "filing": filing,
        "importance": importance,
        "action": action,
        "tags": tags,
    }
    summary = f"{filing.get('corp_name') or ticker} DART 신규 공시: {filing.get('report_name') or '공시명 미확인'}"
    storage = save_research_markdown(
        vault_dir=vault_dir,
        ticker=ticker,
        report_type="dart-filing-watch",
        markdown=markdown,
        structured_payload=payload,
        manifest_entry=manifest_with_ticker_verification(
            ticker,
            {
                "module": "dart_filing_watch",
                "summary": summary,
                "source_type": "official_filing",
                "source_url": filing.get("source_url"),
                "confidence": 0.96,
                "importance": importance,
                "tags": tags,
                "rcept_no": filing.get("rcept_no"),
            },
        ),
        report_date=report_date,
        file_suffix=str(filing.get("rcept_no") or ""),
    )
    upsert_research_memory_document(
        vault_dir=vault_dir,
        entry={
            "ticker": ticker,
            "type": "dart-filing-watch",
            "date": report_date.isoformat(),
            "file_name": storage.file_name,
            "relative_path": storage.relative_path,
            "summary": summary,
            "source_type": "official_filing",
            "tags": tags,
        },
        full_text=markdown,
    )
    return storage


def refresh_dart_filing_watch(
    settings: Settings,
    tickers: list[str] | None = None,
    *,
    force: bool = False,
    save_result: bool = True,
) -> dict:
    cache = read_dart_filing_cache(settings)
    entries = cache.setdefault("entries", {})
    selected_tickers = [
        normalize_ticker(item)
        for item in (tickers or dart_watch_tickers(settings))
        if fullmatch(r"\d{6}", normalize_ticker(item))
    ]
    client = OpenDartClient(settings)
    saved: list[dict] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    if not client.is_configured:
        return {
            "status": "skipped",
            "module": "dart_filing_watch",
            "reason": "DART_API_KEY가 없어 DART 신규 공시 자동 감시를 건너뜁니다.",
            "target_count": len(selected_tickers),
            "cache_path": str(dart_filing_cache_path(settings)),
        }

    for ticker in selected_tickers:
        try:
            corp, filings = client.fetch_recent_filings(
                ticker,
                lookback_days=settings.dart_filing_lookback_days,
                page_count=settings.dart_filing_max_items_per_ticker,
            )
            for filing in filings:
                key = dart_filing_cache_key(ticker, filing)
                if key in entries and not force:
                    skipped.append({"ticker": ticker, "rcept_no": filing.get("rcept_no")})
                    continue
                importance, action, tags = dart_filing_importance(str(filing.get("report_name") or ""))
                storage = save_dart_filing_watch_item(ticker, filing, settings) if save_result else None
                entry = {
                    "ticker": ticker,
                    "corp_name": corp.get("corp_name"),
                    "filing": filing,
                    "importance": importance,
                    "action": action,
                    "tags": tags,
                    "detected_at": current_storage_timestamp(),
                    "storage": storage.model_dump(mode="json") if storage else None,
                }
                entries[key] = entry
                saved.append(entry)
        except Exception as exc:
            failed.append({"ticker": ticker, "error": provider_error_message(exc, settings)})

    cache["updated_at"] = current_storage_timestamp()
    cache["last_run"] = current_storage_timestamp()
    cache["target_tickers"] = selected_tickers
    cache["source"] = "OpenDART list.json"
    cache["last_failures"] = failed
    cache["entries"] = dict(list(entries.items())[-800:])
    write_dart_filing_cache(settings, cache)
    return {
        "status": "success" if not failed else "partial_success",
        "module": "dart_filing_watch",
        "target_count": len(selected_tickers),
        "saved_count": len(saved),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "saved": saved,
        "skipped": skipped[:20],
        "failed": failed,
        "cache_path": str(dart_filing_cache_path(settings)),
    }


_DART_FILING_SCHEDULER_STARTED = False


def dart_filing_scheduler_loop() -> None:
    settings = get_settings()
    interval_seconds = max(settings.dart_filing_refresh_hours, 1) * 3600
    while True:
        try:
            refresh_dart_filing_watch(settings)
        except Exception:
            pass
        threading.Event().wait(interval_seconds)


def start_dart_filing_scheduler() -> None:
    global _DART_FILING_SCHEDULER_STARTED
    settings = get_settings()
    if (
        _DART_FILING_SCHEDULER_STARTED
        or not settings.dart_filing_auto_refresh
        or not settings.dart_api_key
    ):
        return
    _DART_FILING_SCHEDULER_STARTED = True
    thread = threading.Thread(
        target=dart_filing_scheduler_loop,
        name="dart-filing-watch-refresh",
        daemon=True,
    )
    thread.start()


def shinhan_research_cache_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "shinhan_research_cache.json"


def read_shinhan_research_cache(settings: Settings) -> dict:
    return read_json_store(
        shinhan_research_cache_path(settings),
        {"updated_at": None, "entries": {}},
    )


def write_shinhan_research_cache(settings: Settings, payload: dict) -> None:
    write_json_store(shinhan_research_cache_path(settings), payload)


def clean_shinhan_research_text(value: str | None) -> str:
    text = sub(r"[\u200b\ufeff]+", "", str(value or ""))
    text = sub(r"\s+", " ", text).strip()
    return text


def shinhan_item_id(item: dict) -> str:
    fingerprint = "|".join(
        clean_shinhan_research_text(item.get(key))
        for key in ["category", "title", "published_at", "url", "pdf_url"]
    )
    return hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:16]


def normalize_shinhan_date(value: str | None) -> str | None:
    text = clean_shinhan_research_text(value)
    if not text:
        return None
    match = search(r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})", text)
    if match:
        year, month, day = match.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"
    match = search(r"(?<!\d)(\d{2})[./-](\d{1,2})[./-](\d{1,2})(?!\d)", text)
    if match:
        year, month, day = match.groups()
        return f"20{year}-{int(month):02d}-{int(day):02d}"
    return None


def infer_shinhan_category(text: str) -> str:
    categories = [
        "오늘의 리서치",
        "투자전략",
        "기업/산업분석",
        "글로벌마켓",
        "ETF",
        "시장지표",
        "신한 속보",
    ]
    for category in categories:
        if category.lower() in text.lower():
            return category
    lower = text.lower()
    if any(keyword in lower for keyword in ["etf", "상장지수"]):
        return "ETF"
    if any(keyword in lower for keyword in ["전략", "매크로", "경제", "금리", "환율", "시장"]):
        return "투자전략"
    if any(keyword in lower for keyword in ["산업", "섹터", "반도체", "바이오", "자동차"]):
        return "기업/산업분석"
    return "오늘의 리서치"


def extract_shinhan_research_items_from_html(html: str, settings: Settings) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    items: list[dict] = []
    base_url = settings.shinhan_research_base_url.rstrip("/") + "/"
    list_url = settings.shinhan_research_list_url

    try:
        from bs4 import BeautifulSoup  # type: ignore
    except Exception:
        BeautifulSoup = None  # type: ignore
        warnings.append("BeautifulSoup을 사용할 수 없어 정규식 기반 예비 파서를 사용했습니다.")

    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup.find_all("a"):
            title = clean_shinhan_research_text(tag.get_text(" "))
            href = clean_shinhan_research_text(tag.get("href"))
            if not title or len(title) < 5:
                continue
            if title in {"오늘의 리서치", "투자전략", "기업/산업분석", "글로벌마켓", "ETF", "시장지표", "신한 속보"}:
                continue
            nearby = clean_shinhan_research_text(
                tag.find_parent().get_text(" ") if tag.find_parent() else title
            )
            combined = f"{nearby} {href}"
            if not any(keyword in combined.lower() for keyword in ["research", "report", "pdf", "insights", "자료", "리서치", "전략", "분석", "시장", "산업", "기업"]):
                continue
            url = urljoin(list_url, href) if href else list_url
            pdf_url = url if ".pdf" in url.lower() else None
            item = {
                "title": title,
                "category": infer_shinhan_category(nearby),
                "published_at": normalize_shinhan_date(nearby),
                "url": url,
                "pdf_url": pdf_url,
                "source": "shinhan_securities",
            }
            item["item_id"] = shinhan_item_id(item)
            items.append(item)

    if not items:
        anchor_pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>'
        for href, raw_title in findall(anchor_pattern, html, flags=0):
            title = clean_shinhan_research_text(sub(r"<[^>]+>", " ", raw_title))
            if len(title) < 5:
                continue
            url = urljoin(base_url, href)
            item = {
                "title": title,
                "category": infer_shinhan_category(title),
                "published_at": normalize_shinhan_date(title),
                "url": url,
                "pdf_url": url if ".pdf" in url.lower() else None,
                "source": "shinhan_securities",
            }
            item["item_id"] = shinhan_item_id(item)
            items.append(item)

    deduped: dict[str, dict] = {}
    for item in items:
        deduped[item["item_id"]] = item
    parsed_items = list(deduped.values())[: max(settings.shinhan_research_max_items, 1)]
    if not parsed_items:
        warnings.append("정적 HTML에서 리서치 항목을 찾지 못했습니다. 신한 페이지가 스크립트로 목록을 늦게 불러오면 전용 API 경로 추가가 필요합니다.")
    return parsed_items, warnings


def shinhan_board_category(board_title: str | None, board_name: str | None = None) -> str:
    title = clean_shinhan_research_text(board_title)
    code = clean_shinhan_research_text(board_name).lower()
    if title:
        return infer_shinhan_category(title)
    if code in {"gieconomy", "gicomment", "giperiodicalbreif", "gibond", "gifuture", "giperiodicalinvest", "fxmarket", "commodity"}:
        return "투자전략"
    if code in {"gicompanyanalyst", "giindustry", "giresearchipo", "konex"}:
        return "기업/산업분석"
    if code in {"china", "foreignstock", "foreignbond", "gistockchart"}:
        return "글로벌마켓"
    if code in {"pbletter", "gifund2", "alternative", "etf"}:
        return "ETF" if code == "etf" else "투자전략"
    if code in {"giperiodicaldaily", "issuecomment", "gigoodpolio", "issuebroker", "gireview,gimovement,stockindex", "shinhannews"}:
        return "시장지표" if "stockindex" in code else "오늘의 리서치"
    return "오늘의 리서치"


def shinhan_api_item_to_research_item(row: dict, settings: Settings) -> dict | None:
    title = clean_shinhan_research_text(row.get("TITLE"))
    if not title:
        return None
    board_name = clean_shinhan_research_text(row.get("BOARD_NAME"))
    board_title = clean_shinhan_research_text(row.get("BOARD_TITLE") or row.get("VARIABLE_FIELD_NAME3"))
    message_id = clean_shinhan_research_text(row.get("MESSAGE_ID") or row.get("DOCID"))
    detail_path = "/siw/board/message/view.file.pop.do"
    url = urljoin(
        settings.shinhan_research_base_url,
        f"{detail_path}?boardName={board_name}&messageId={message_id}" if board_name and message_id else settings.shinhan_research_list_url,
    )
    category = shinhan_board_category(board_title, board_name)
    related_name = clean_shinhan_research_text(row.get("VARIABLE_FIELD_NAME1") or row.get("VARIABLE_FIELD_NAME2"))
    writer = clean_shinhan_research_text(row.get("REGISTER_NICKNAME") or row.get("REGISTER_NICKNAME2"))
    published_at = normalize_shinhan_date(row.get("DATE") or row.get("REG_DT"))
    item = {
        "title": title,
        "category": category,
        "board_name": board_name,
        "board_title": board_title,
        "message_id": message_id,
        "attachment_id": clean_shinhan_research_text(row.get("ATTACHMENT_ID") or row.get("FILE_CONTENT")),
        "display_name": clean_shinhan_research_text(row.get("DISPLAYNAME")),
        "related_name": related_name,
        "writer": writer,
        "published_at": published_at,
        "url": url,
        "pdf_url": url if clean_shinhan_research_text(row.get("EXT")).lower() == "pdf" else None,
        "source": "shinhan_securities",
    }
    item["item_id"] = clean_shinhan_research_text(row.get("DOCID") or row.get("MESSAGE_ID")) or shinhan_item_id(item)
    return item


def fetch_shinhan_research_items_from_api(settings: Settings) -> tuple[list[dict], list[str]]:
    headers = {
        "User-Agent": settings.shinhan_research_user_agent,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.6,en;q=0.5",
        "Referer": settings.shinhan_research_list_url,
        "Origin": settings.shinhan_research_base_url,
        "X-Requested-With": "XMLHttpRequest",
    }
    data = {
        "startCount": 0,
        "listCount": max(settings.shinhan_research_max_items, 1),
        "query": "",
        "searchType": "A",
        "boardCode": "",
    }
    api_url = urljoin(settings.shinhan_research_base_url, "/siw/etc/browse/search05/data.do")
    with httpx.Client(timeout=settings.shinhan_research_timeout_seconds, follow_redirects=True) as client:
        response = client.post(api_url, headers=headers, data=data)
        response.raise_for_status()
        payload = response.json()

    body = payload.get("body") if isinstance(payload, dict) else None
    collection_list = body.get("collectionList") if isinstance(body, dict) else []
    items: list[dict] = []
    for collection in collection_list or []:
        if collection.get("thisCollection") != "researchFinder":
            continue
        for row in collection.get("itemList") or []:
            item = shinhan_api_item_to_research_item(row, settings)
            if item:
                items.append(item)
    if not items:
        return [], ["신한 목록 API 응답에서 researchFinder 항목을 찾지 못했습니다."]
    return items, []


def fetch_shinhan_research_items(settings: Settings) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    try:
        return fetch_shinhan_research_items_from_api(settings)
    except Exception as exc:
        warnings.append(f"신한 목록 API 조회 실패 후 HTML 파서를 사용했습니다: {exc}")

    headers = {
        "User-Agent": settings.shinhan_research_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.6,en;q=0.5",
        "Referer": settings.shinhan_research_base_url,
    }
    with httpx.Client(timeout=settings.shinhan_research_timeout_seconds, follow_redirects=True) as client:
        response = client.get(settings.shinhan_research_list_url, headers=headers)
        response.raise_for_status()
    html_items, html_warnings = extract_shinhan_research_items_from_html(response.text, settings)
    return html_items, warnings + html_warnings


def infer_shinhan_storage_target(item: dict, settings: Settings) -> tuple[str, str, str]:
    title = clean_shinhan_research_text(item.get("title"))
    category = clean_shinhan_research_text(item.get("category"))
    related_name = clean_shinhan_research_text(item.get("related_name"))
    board_title = clean_shinhan_research_text(item.get("board_title"))
    context = "\n".join(
        value
        for value in [
            "신한투자증권 리서치",
            f"카테고리: {category}",
            f"게시판: {board_title}",
            f"관련 종목/자산: {related_name}",
            f"제목: {title}",
        ]
        if value
    )

    us_match = search(r"\(([A-Z]{1,6})\.US\)", f"{related_name} {title}".upper())
    if us_match:
        candidate = us_match.group(1)
        try:
            verified = ensure_verified_ticker(candidate, settings)
            return verified, "shinhan_us_symbol", enum_or_str_value(DataSourceType.ANALYST_REPORT)
        except HTTPException:
            return "MARKET-GLOBAL", "shinhan_unverified_us_symbol", "market_research"

    kr_code_match = search(r"(?<!\d)(\d{6})(?:\.(?:KS|KQ|KR))?(?!\d)", f"{related_name} {title}".upper())
    if kr_code_match:
        code = kr_code_match.group(1)
        try:
            verified = ensure_verified_ticker(code, settings)
            return verified, "shinhan_kr_symbol_code", enum_or_str_value(DataSourceType.ANALYST_REPORT)
        except HTTPException:
            return "SECTOR", "shinhan_unverified_kr_symbol", "sector_research"

    if category == "글로벌마켓":
        key, source_type = infer_non_ticker_research_key(context)
        if key == "INBOX":
            key = "MARKET-GLOBAL"
            source_type = "market_research"
        return key, "shinhan_global_market", source_type

    macro_categories = {"투자전략", "시장지표", "신한 속보", "오늘의 리서치"}
    if category in macro_categories:
        key, source_type = infer_non_ticker_research_key(context)
        if key == "INBOX":
            key = "MARKET-KR"
            source_type = "market_research"
        return key, f"shinhan_{category}", source_type

    if category in {"ETF", "기업/산업분석"}:
        inferred_ticker, source = infer_capture_ticker(context, settings)
        if inferred_ticker not in {"INBOX", "MARKET", "MARKET-KR", "MARKET-US", "MARKET-GLOBAL", "MACRO", "POLICY", "RATES", "FLOWS", "CUSTOMS"}:
            return inferred_ticker, source, enum_or_str_value(DataSourceType.ANALYST_REPORT)
        return "SECTOR", f"shinhan_{category}", "sector_research"

    return "MARKET-KR", "shinhan_research", "market_research"


def build_shinhan_capture_content(item: dict, target: str, source_hint: str) -> str:
    lines = [
        "[신한투자증권 리서치 자동 수집]",
        f"분류: {item.get('category') or '미분류'}",
        f"제목: {item.get('title') or '제목 미확인'}",
        f"게시판: {item.get('board_title') or item.get('category') or '미확인'}",
        f"관련 종목/자산: {item.get('related_name') or '미확인'}",
        f"작성자: {item.get('writer') or '미확인'}",
        f"발행일: {item.get('published_at') or '미확인'}",
        f"저장 범위: {target}",
        f"분류 근거: {source_hint}",
        f"원문 링크: {item.get('url') or '미확인'}",
    ]
    if item.get("pdf_url"):
        lines.append(f"PDF 링크: {item.get('pdf_url')}")
    lines.extend(
        [
            "",
            "활용 지침:",
            "- 이 자료는 신한투자증권 리서치 목록 API에서 자동 수집한 외부 리서치 메타데이터입니다.",
            "- 종목 자료는 기존 투자 논거와 비교하고, 시장/섹터 자료는 시장일지·섹터 발굴·리스크 스캔의 배경 자료로 활용합니다.",
            "- 원문 링크가 있는 경우 최종 투자 판단 전 원문 수치와 발행일을 확인합니다.",
        ]
    )
    return "\n".join(lines)


def save_shinhan_research_item(item: dict, settings: Settings, save_result: bool = True) -> ResearchCaptureResponse:
    target, source_hint, source_type = infer_shinhan_storage_target(item, settings)
    content = build_shinhan_capture_content(item, target, source_hint)
    request = ResearchCaptureRequest(
        ticker=target,
        title=f"신한 리서치 - {item.get('title') or '제목 미확인'}",
        raw_content=content,
        source_type=source_type,
        source_url=item.get("url"),
        as_of=item.get("published_at") or current_storage_date().isoformat(),
        confidence=0.82,
        tags=["shinhan_research", "auto_ingested", f"shinhan_category:{item.get('category') or 'unknown'}"],
        run_thesis_impact=target not in SPECIAL_RESEARCH_KEYS,
        save_result=save_result,
    )
    return save_capture_request(request, settings)


def refresh_shinhan_research_cache(
    settings: Settings,
    limit: int | None = None,
    force: bool = False,
    save_result: bool = True,
) -> dict:
    if not settings.shinhan_research_enabled:
        return {
            "status": "disabled",
            "module": "shinhan_research_ingest",
            "message": "SHINHAN_RESEARCH_ENABLED=false 상태입니다.",
            "cache_path": str(shinhan_research_cache_path(settings)),
        }

    cache = read_shinhan_research_cache(settings)
    entries = cache.get("entries") if isinstance(cache.get("entries"), dict) else {}
    errors: list[str] = []
    warnings: list[str] = []
    try:
        items, parser_warnings = fetch_shinhan_research_items(settings)
        warnings.extend(parser_warnings)
    except Exception as exc:
        errors.append(f"신한 리서치 목록 조회 실패: {exc}")
        return {
            "status": "failed",
            "module": "shinhan_research_ingest",
            "requested_count": 0,
            "saved_count": 0,
            "skipped_count": 0,
            "failed_count": 1,
            "warnings": warnings,
            "errors": errors,
            "cache_path": str(shinhan_research_cache_path(settings)),
        }

    max_items = limit if limit is not None else settings.shinhan_research_max_items
    selected_items = items[: max(int(max_items or 1), 1)]
    saved: list[dict] = []
    skipped: list[dict] = []
    failed: list[dict] = []

    for item in selected_items:
        item_id = item.get("item_id") or shinhan_item_id(item)
        item["item_id"] = item_id
        if item_id in entries and not force:
            skipped.append({"item_id": item_id, "title": item.get("title"), "reason": "already_ingested"})
            continue
        try:
            response = save_shinhan_research_item(item, settings, save_result=save_result)
            entry = {
                **item,
                "ingested_at": current_storage_timestamp(),
                "ticker": response.captured_item.ticker,
                "source_type": enum_or_str_value(response.captured_item.source_type),
                "summary": response.captured_item.summary,
                "storage": response.storage.model_dump(mode="json") if response.storage else None,
            }
            entries[item_id] = entry
            saved.append(entry)
        except Exception as exc:
            failed.append({"item_id": item_id, "title": item.get("title"), "error": str(exc)})

    cache = {
        "updated_at": current_storage_timestamp(),
        "source_url": settings.shinhan_research_list_url,
        "entries": entries,
    }
    write_shinhan_research_cache(settings, cache)
    return {
        "status": "success" if not failed and not errors else "partial_success",
        "module": "shinhan_research_ingest",
        "requested_count": len(selected_items),
        "saved_count": len(saved),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "saved": saved,
        "skipped": skipped,
        "failed": failed,
        "warnings": warnings,
        "errors": errors,
        "cache_path": str(shinhan_research_cache_path(settings)),
    }


_SHINHAN_RESEARCH_SCHEDULER_STARTED = False


def shinhan_research_scheduler_loop() -> None:
    settings = get_settings()
    interval_seconds = max(settings.shinhan_research_refresh_hours, 1) * 3600
    while True:
        try:
            refresh_shinhan_research_cache(settings)
        except Exception:
            pass
        threading.Event().wait(interval_seconds)


def start_shinhan_research_scheduler() -> None:
    global _SHINHAN_RESEARCH_SCHEDULER_STARTED
    settings = get_settings()
    if (
        _SHINHAN_RESEARCH_SCHEDULER_STARTED
        or not settings.shinhan_research_enabled
        or not settings.shinhan_research_auto_refresh
    ):
        return
    _SHINHAN_RESEARCH_SCHEDULER_STARTED = True
    thread = threading.Thread(
        target=shinhan_research_scheduler_loop,
        name="shinhan-research-refresh",
        daemon=True,
    )
    thread.start()



def naver_research_cache_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "naver_research_cache.json"


def read_naver_research_cache(settings: Settings) -> dict:
    return read_json_store(
        naver_research_cache_path(settings),
        {"updated_at": None, "entries": {}},
    )


def write_naver_research_cache(settings: Settings, payload: dict) -> None:
    write_json_store(naver_research_cache_path(settings), payload)


def clean_naver_research_text(value: str | None) -> str:
    return clean_shinhan_research_text(value)


def normalize_naver_research_date(value: str | None) -> str | None:
    return normalize_shinhan_date(value)


def naver_research_categories(settings: Settings) -> list[dict]:
    return [
        {
            "category": "종목분석",
            "scope": "company",
            "url": urljoin(settings.naver_research_base_url, "/research/company_list.naver"),
            "read_marker": "company_read.naver",
        },
        {
            "category": "산업분석",
            "scope": "industry",
            "url": urljoin(settings.naver_research_base_url, "/research/industry_list.naver"),
            "read_marker": "industry_read.naver",
        },
        {
            "category": "시황정보",
            "scope": "market",
            "url": urljoin(settings.naver_research_base_url, "/research/market_info_list.naver"),
            "read_marker": "market_info_read.naver",
        },
        {
            "category": "투자정보",
            "scope": "invest",
            "url": urljoin(settings.naver_research_base_url, "/research/invest_list.naver"),
            "read_marker": "invest_read.naver",
        },
    ]


def naver_research_item_id(item: dict) -> str:
    fingerprint = "|".join(
        clean_naver_research_text(item.get(key))
        for key in ["source", "category", "ticker", "company_name", "title", "published_at", "url", "pdf_url", "nid"]
    )
    return hashlib.sha1(fingerprint.encode("utf-8")).hexdigest()[:16]


def extract_naver_research_nid(href: str | None) -> str:
    match = search(r"(?:\?|&)nid=(\d+)", str(href or ""))
    return match.group(1) if match else ""


def register_naver_korean_ticker(code: str, company_name: str, settings: Settings) -> None:
    normalized_code = clean_naver_research_text(code)
    clean_company = clean_naver_research_text(company_name)
    if not search(r"^\d{6}$", normalized_code) or not clean_company:
        return
    existing = read_dynamic_ticker_registry(settings).get(normalized_code, {})
    profile = {
        **existing,
        "company_name": clean_company,
        "exchange": existing.get("exchange") or "KRX",
        "country": existing.get("country") or "KR",
        "asset_type": existing.get("asset_type") or "equity",
        "sector": existing.get("sector"),
        "industry": existing.get("industry"),
        "business_context": existing.get("business_context")
        or f"{clean_company}의 사업 모델, 실적 추세, 밸류에이션, 업종 내 경쟁 위치, 수급과 리스크를 중심으로 분석",
        "analysis_focus": existing.get("analysis_focus")
        or "사업 모델, 실적 성장, 마진, 현금흐름, 밸류에이션, 업종 리스크, 수급",
        "watch_kpis": existing.get("watch_kpis")
        or ["매출 성장률", "영업이익률", "순이익률", "현금흐름", "가이던스 변화", "기관/외국인 수급"],
        "data_limitations": existing.get("data_limitations")
        or ["네이버 금융 리서치 목록에서 확인한 국내 종목 코드입니다. 상세 회사 전용 KPI는 후속 보강이 필요합니다."],
        "verification_source": "naver_finance_research",
    }
    write_dynamic_ticker_profile(normalized_code, profile, settings)


def naver_research_row_to_item(row, category_info: dict, settings: Settings) -> dict | None:
    marker = str(category_info.get("read_marker") or "")
    title_anchor = row.find("a", href=lambda href: bool(href) and marker in str(href))
    if title_anchor is None:
        return None

    title = clean_naver_research_text(title_anchor.get_text(" "))
    href = clean_naver_research_text(title_anchor.get("href"))
    if not title:
        return None

    detail_url = urljoin(str(category_info.get("url")), href)
    pdf_anchor = row.find("a", href=lambda href: bool(href) and ".pdf" in str(href).lower())
    pdf_url = urljoin(str(category_info.get("url")), clean_naver_research_text(pdf_anchor.get("href"))) if pdf_anchor else None
    stock_anchor = row.find("a", href=lambda href: bool(href) and "/item/main.naver" in str(href) and "code=" in str(href))
    ticker = ""
    company_name = ""
    if stock_anchor is not None:
        stock_href = clean_naver_research_text(stock_anchor.get("href"))
        code_match = search(r"code=(\d{6})", stock_href)
        ticker = code_match.group(1) if code_match else ""
        company_name = clean_naver_research_text(stock_anchor.get("title") or stock_anchor.get_text(" "))
        register_naver_korean_ticker(ticker, company_name, settings)

    cells = [clean_naver_research_text(cell.get_text(" ")) for cell in row.find_all("td")]
    dates = [cell for cell in cells if normalize_naver_research_date(cell)]
    published_at = normalize_naver_research_date(dates[0]) if dates else None
    broker = ""
    if category_info.get("scope") == "company" and len(cells) >= 3:
        broker = cells[2]
    elif len(cells) >= 2:
        broker = cells[1]
    broker = broker if broker and not normalize_naver_research_date(broker) else "미확인"

    item = {
        "source": "naver_finance_research",
        "category": category_info.get("category") or "미분류",
        "scope": category_info.get("scope") or "unknown",
        "title": title,
        "broker": broker,
        "published_at": published_at,
        "url": detail_url,
        "pdf_url": pdf_url,
        "ticker": ticker,
        "company_name": company_name,
        "nid": extract_naver_research_nid(href),
    }
    item["item_id"] = naver_research_item_id(item)
    return item


def fetch_naver_research_page(category_info: dict, settings: Settings) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    try:
        from bs4 import BeautifulSoup  # type: ignore
    except Exception as exc:
        return [], [f"BeautifulSoup을 사용할 수 없어 네이버 리서치 HTML을 파싱하지 못했습니다: {exc}"]

    headers = {
        "User-Agent": settings.naver_research_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.6,en;q=0.5",
        "Referer": settings.naver_research_list_url,
    }
    with httpx.Client(timeout=settings.naver_research_timeout_seconds, follow_redirects=True) as client:
        response = client.get(str(category_info.get("url")), headers=headers)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    items: list[dict] = []
    for row in soup.find_all("tr"):
        item = naver_research_row_to_item(row, category_info, settings)
        if item:
            items.append(item)
    if not items:
        warnings.append(f"네이버 {category_info.get('category')} 목록에서 리서치 항목을 찾지 못했습니다.")
    return items, warnings


def fetch_naver_research_items(settings: Settings) -> tuple[list[dict], list[str]]:
    all_items: list[dict] = []
    warnings: list[str] = []
    for category_info in naver_research_categories(settings):
        try:
            items, page_warnings = fetch_naver_research_page(category_info, settings)
            all_items.extend(items)
            warnings.extend(page_warnings)
        except Exception as exc:
            warnings.append(f"네이버 {category_info.get('category')} 조회 실패: {provider_error_message(exc, settings)}")
    deduped: dict[str, dict] = {}
    for item in all_items:
        deduped[item.get("item_id") or naver_research_item_id(item)] = item
    sorted_items = sorted(
        deduped.values(),
        key=lambda item: str(item.get("published_at") or ""),
        reverse=True,
    )
    return sorted_items[: max(settings.naver_research_max_items, 1)], warnings


def infer_naver_storage_target(item: dict, settings: Settings) -> tuple[str, str, str]:
    ticker = clean_naver_research_text(item.get("ticker"))
    company_name = clean_naver_research_text(item.get("company_name"))
    category = clean_naver_research_text(item.get("category"))
    title = clean_naver_research_text(item.get("title"))
    context = "\n".join(
        value
        for value in [
            "네이버 리서치",
            f"카테고리: {category}",
            f"종목명: {company_name}",
            f"종목코드: {ticker}",
            f"제목: {title}",
        ]
        if value
    )
    if ticker and search(r"^\d{6}$", ticker):
        register_naver_korean_ticker(ticker, company_name or title, settings)
        return ticker, "naver_kr_symbol_code", enum_or_str_value(DataSourceType.ANALYST_REPORT)
    if category == "산업분석":
        key, source_type = infer_non_ticker_research_key(context)
        if key == "INBOX":
            return "SECTOR", "naver_industry_research", "sector_research"
        return key, "naver_industry_research", source_type
    if category in {"시황정보", "투자정보"}:
        key, source_type = infer_non_ticker_research_key(context)
        if key in {"POLICY", "RATES", "FLOWS", "MACRO", "MARKET", "CUSTOMS"}:
            return key, "naver_market_research", source_type
        return "MARKET-KR", "naver_market_research", "market_research"
    key, source_type = infer_non_ticker_research_key(context)
    if key in SPECIAL_RESEARCH_KEYS - {"INBOX"}:
        return key, "naver_research_auto_scope", source_type
    return "MARKET-KR", "naver_research", "market_research"


def build_naver_capture_content(item: dict, target: str, source_hint: str) -> str:
    lines = [
        "[네이버 금융 리서치 자동 수집]",
        f"분류: {item.get('category') or '미분류'}",
        f"제목: {item.get('title') or '제목 미확인'}",
        f"증권사: {item.get('broker') or '미확인'}",
        f"종목명: {item.get('company_name') or '해당 없음'}",
        f"종목코드: {item.get('ticker') or '해당 없음'}",
        f"발행일: {item.get('published_at') or '미확인'}",
        f"저장 범위: {target}",
        f"분류 근거: {source_hint}",
        f"원문 링크: {item.get('url') or '미확인'}",
    ]
    if item.get("pdf_url"):
        lines.append(f"PDF 링크: {item.get('pdf_url')}")
    lines.extend(
        [
            "",
            "활용 지침:",
            "- 이 자료는 네이버 금융 리서치 목록에서 자동 수집한 외부 리서치 메타데이터입니다.",
            "- 종목 리포트는 해당 종목의 기존 투자 논거와 비교하고, 산업/시황/투자정보는 시장일지·섹터 발굴·포트폴리오 리스크 스캔의 배경 자료로 활용합니다.",
            "- 최종 투자 판단 전에는 원문과 PDF의 세부 수치, 목표가, 발행일을 확인합니다.",
        ]
    )
    return "\n".join(lines)


def save_naver_research_item(item: dict, settings: Settings, save_result: bool = True) -> ResearchCaptureResponse:
    target, source_hint, source_type = infer_naver_storage_target(item, settings)
    content = build_naver_capture_content(item, target, source_hint)
    request = ResearchCaptureRequest(
        ticker=target,
        title=f"네이버 리서치 - {item.get('title') or '제목 미확인'}",
        raw_content=content,
        source_type=source_type,
        source_url=item.get("url"),
        as_of=item.get("published_at") or current_storage_date().isoformat(),
        confidence=0.8 if item.get("pdf_url") else 0.74,
        tags=["naver_research", "auto_ingested", f"naver_category:{item.get('category') or 'unknown'}"],
        run_thesis_impact=target not in SPECIAL_RESEARCH_KEYS,
        save_result=save_result,
    )
    return save_capture_request(request, settings)


def refresh_naver_research_cache(
    settings: Settings,
    limit: int | None = None,
    force: bool = False,
    save_result: bool = True,
) -> dict:
    if not settings.naver_research_enabled:
        return {
            "status": "disabled",
            "module": "naver_research_ingest",
            "message": "NAVER_RESEARCH_ENABLED=false 상태입니다.",
            "cache_path": str(naver_research_cache_path(settings)),
        }

    cache = read_naver_research_cache(settings)
    entries = cache.get("entries") if isinstance(cache.get("entries"), dict) else {}
    warnings: list[str] = []
    errors: list[str] = []
    try:
        items, parser_warnings = fetch_naver_research_items(settings)
        warnings.extend(parser_warnings)
    except Exception as exc:
        errors.append(f"네이버 리서치 목록 조회 실패: {provider_error_message(exc, settings)}")
        return {
            "status": "failed",
            "module": "naver_research_ingest",
            "requested_count": 0,
            "saved_count": 0,
            "skipped_count": 0,
            "failed_count": 1,
            "warnings": warnings,
            "errors": errors,
            "cache_path": str(naver_research_cache_path(settings)),
        }

    max_items = limit if limit is not None else settings.naver_research_max_items
    selected_items = items[: max(int(max_items or 1), 1)]
    saved: list[dict] = []
    skipped: list[dict] = []
    failed: list[dict] = []
    for item in selected_items:
        item_id = item.get("item_id") or naver_research_item_id(item)
        item["item_id"] = item_id
        if item_id in entries and not force:
            skipped.append({"item_id": item_id, "title": item.get("title"), "reason": "already_ingested"})
            continue
        try:
            response = save_naver_research_item(item, settings, save_result=save_result)
            entry = {
                **item,
                "ingested_at": current_storage_timestamp(),
                "ticker": response.captured_item.ticker,
                "source_type": enum_or_str_value(response.captured_item.source_type),
                "summary": response.captured_item.summary,
                "storage": response.storage.model_dump(mode="json") if response.storage else None,
            }
            entries[item_id] = entry
            saved.append(entry)
        except Exception as exc:
            failed.append({"item_id": item_id, "title": item.get("title"), "error": str(exc)})

    cache = {
        "updated_at": current_storage_timestamp(),
        "source_url": settings.naver_research_list_url,
        "entries": entries,
    }
    write_naver_research_cache(settings, cache)
    return {
        "status": "success" if not failed and not errors else "partial_success",
        "module": "naver_research_ingest",
        "requested_count": len(selected_items),
        "saved_count": len(saved),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "saved": saved,
        "skipped": skipped,
        "failed": failed,
        "warnings": warnings,
        "errors": errors,
        "cache_path": str(naver_research_cache_path(settings)),
    }


_NAVER_RESEARCH_SCHEDULER_STARTED = False


def naver_research_scheduler_loop() -> None:
    settings = get_settings()
    interval_seconds = max(settings.naver_research_refresh_hours, 1) * 3600
    while True:
        try:
            refresh_naver_research_cache(settings)
        except Exception:
            pass
        threading.Event().wait(interval_seconds)


def start_naver_research_scheduler() -> None:
    global _NAVER_RESEARCH_SCHEDULER_STARTED
    settings = get_settings()
    if (
        _NAVER_RESEARCH_SCHEDULER_STARTED
        or not settings.naver_research_enabled
        or not settings.naver_research_auto_refresh
    ):
        return
    _NAVER_RESEARCH_SCHEDULER_STARTED = True
    thread = threading.Thread(
        target=naver_research_scheduler_loop,
        name="naver-research-refresh",
        daemon=True,
    )
    thread.start()
def remember_ticker_lookup_diagnostics(symbol: str, steps: list[dict]) -> None:
    TICKER_LOOKUP_DIAGNOSTICS[normalize_ticker(symbol)] = steps[-8:]


def normalize_external_ticker_profile(symbol: str, payload: dict) -> dict | None:
    official_symbol = normalize_ticker(str(payload.get("symbol") or symbol))
    if official_symbol != normalize_ticker(symbol):
        return None
    company_name = (
        payload.get("companyName")
        or payload.get("name")
        or payload.get("company_name")
        or ""
    )
    exchange = exchange_display_name(
        payload.get("exchangeShortName")
        or payload.get("exchange")
        or payload.get("stockExchange")
    )
    if not company_name or exchange == "UNKNOWN":
        return None
    sector = payload.get("sector")
    industry = payload.get("industry")
    description = payload.get("description") or payload.get("business_context")
    korean_description = (
        str(description)
        if description and search(r"[가-힣]", str(description))
        else ""
    )
    generic_business_context = (
        f"{company_name}의 사업 모델, 매출 동력, 경쟁 우위, 현금흐름, "
        "밸류에이션과 주요 리스크를 중심으로 분석"
    )
    if sector or industry:
        generic_business_context += f". 참고 섹터/산업: {sector or 'n/a'} / {industry or 'n/a'}"
    return {
        "company_name": str(company_name),
        "exchange": exchange,
        "country": payload.get("country") or "US",
        "asset_type": "equity",
        "sector": sector,
        "industry": industry,
        "business_context": korean_description or generic_business_context,
        "analysis_focus": "사업 모델, 매출 성장, 마진, 현금흐름, 밸류에이션, 주요 리스크",
        "watch_kpis": [
            "매출 성장률",
            "매출총이익률",
            "영업이익률",
            "잉여현금흐름",
            "가이던스 변화",
        ],
        "data_limitations": [
            "이 티커는 로컬 레지스트리에 없어서 외부 데이터 소스로 자동 인증된 프로필입니다. 회사별 전용 KPI와 실적 캘린더는 후속 보강이 필요합니다.",
        ],
        "verification_source": "fmp_company_profile",
    }


def lookup_ticker_profile_from_fmp(
    symbol: str,
    settings: Settings | None = None,
) -> dict | None:
    active_settings = settings or get_settings()
    steps: list[dict] = []
    if not fmp_api_key(active_settings) or fmp_api_key(active_settings) == "********":
        steps.append(
            {
                "source": "fmp",
                "endpoint": "profile",
                "status": "skipped",
                "message": "FMP_API_KEY가 설정되지 않아 외부 티커 인증을 건너뜁니다.",
            }
        )
        remember_ticker_lookup_diagnostics(symbol, steps)
        return None

    try:
        client = FmpClient(active_settings)
        payload = client.get("profile", {"symbol": symbol})
        if isinstance(payload, list) and payload:
            profile = normalize_external_ticker_profile(symbol, payload[0])
            if profile:
                steps.append(
                    {
                        "source": "fmp",
                        "endpoint": "stable/profile",
                        "status": "success",
                        "message": "FMP stable profile에서 회사 프로필을 확인했습니다.",
                    }
                )
                remember_ticker_lookup_diagnostics(symbol, steps)
                return profile
        steps.append(
            {
                "source": "fmp",
                "endpoint": "stable/profile",
                "status": "empty",
                "message": "FMP stable profile 응답에 사용할 수 있는 회사 프로필이 없었습니다.",
            }
        )
    except Exception as error:
        steps.append(
            {
                "source": "fmp",
                "endpoint": "stable/profile",
                "status": "failed",
                "message": provider_error_message(error, active_settings),
            }
        )

    try:
        response = httpx.get(
            f"{fmp_legacy_base_url(active_settings)}/profile/{symbol}",
            params={"apikey": fmp_api_key(active_settings)},
            timeout=active_settings.fmp_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list) and payload:
            profile = normalize_external_ticker_profile(symbol, payload[0])
            if profile:
                steps.append(
                    {
                        "source": "fmp",
                        "endpoint": "api/v3/profile",
                        "status": "success",
                        "message": "FMP legacy profile에서 회사 프로필을 확인했습니다.",
                    }
                )
                remember_ticker_lookup_diagnostics(symbol, steps)
                return profile
        steps.append(
            {
                "source": "fmp",
                "endpoint": "api/v3/profile",
                "status": "empty",
                "message": "FMP legacy profile 응답에 사용할 수 있는 회사 프로필이 없었습니다.",
            }
        )
    except Exception as error:
        steps.append(
            {
                "source": "fmp",
                "endpoint": "api/v3/profile",
                "status": "failed",
                "message": provider_error_message(error, active_settings),
            }
        )
        remember_ticker_lookup_diagnostics(symbol, steps)
        return None
    remember_ticker_lookup_diagnostics(symbol, steps)
    return None


def lookup_ticker_profile_from_kis(
    symbol: str,
    settings: Settings | None = None,
) -> dict | None:
    active_settings = settings or get_settings()
    normalized_symbol = normalize_ticker(symbol)
    steps = list(TICKER_LOOKUP_DIAGNOSTICS.get(normalized_symbol, []))
    if search(r"^\d{6}$", normalized_symbol):
        steps.append(
            {
                "source": "kis",
                "endpoint": "overseas-price",
                "status": "skipped",
                "message": "국내 6자리 종목코드는 KIS 해외주식 티커 인증 대상에서 제외했습니다.",
            }
        )
        remember_ticker_lookup_diagnostics(normalized_symbol, steps)
        return None

    if not (
        active_settings.kis_app_key.strip()
        and active_settings.kis_app_secret.strip()
        and (
            active_settings.kis_access_token.strip()
            or active_settings.kis_access_token_file.strip()
            or active_settings.kis_token_cache_file.strip()
            or active_settings.kis_allow_token_issue
        )
    ):
        steps.append(
            {
                "source": "kis",
                "endpoint": "overseas-price",
                "status": "skipped",
                "message": "KIS 키 또는 접근 토큰 설정이 없어 KIS 티커 인증을 건너뜁니다.",
            }
        )
        remember_ticker_lookup_diagnostics(normalized_symbol, steps)
        return None

    try:
        provider = get_analysis_data_provider(active_settings)
        data_points = provider.market_data_provider.fetch_market_snapshot(normalized_symbol)
        last_price = next(
            (
                point.value
                for point in data_points
                if point.label == "last_price" and point.value and point.value != "n/a"
            ),
            None,
        )
        exchange_code = next(
            (
                point.value
                for point in data_points
                if point.label == "kis_exchange_code" and point.value
            ),
            "",
        )
        warning = next(
            (
                point.value
                for point in data_points
                if point.label == "kis_market_data_provider_warning"
            ),
            "",
        )
        if not last_price:
            steps.append(
                {
                    "source": "kis",
                    "endpoint": "overseas-price",
                    "status": "failed",
                    "message": warning or "KIS 현재가 응답에서 유효한 가격을 찾지 못했습니다.",
                }
            )
            remember_ticker_lookup_diagnostics(normalized_symbol, steps)
            return None

        exchange = exchange_display_name(exchange_code)
        steps.append(
            {
                "source": "kis",
                "endpoint": "overseas-price",
                "status": "success",
                "message": f"KIS 해외주식 현재가로 {normalized_symbol} 거래 가능성을 확인했습니다.",
            }
        )
        remember_ticker_lookup_diagnostics(normalized_symbol, steps)
        return {
            "company_name": f"{normalized_symbol} (KIS 해외주식 공식 티커)",
            "exchange": exchange,
            "country": "US",
            "asset_type": "equity",
            "sector": None,
            "industry": None,
            "business_context": (
                f"{normalized_symbol}은 KIS 해외주식 현재가 조회로 인증된 미국 상장 주식입니다. "
                "회사명, 섹터, 전용 KPI는 FMP 무료 플랜 제한으로 자동 확정하지 않고 "
                "후속 리서치 메모 또는 공식 자료로 보강합니다."
            ),
            "analysis_focus": "사업 모델, 매출 성장, 마진, 현금흐름, 밸류에이션, 주요 리스크",
            "watch_kpis": [
                "매출 성장률",
                "매출총이익률",
                "영업이익률",
                "잉여현금흐름",
                "가이던스 변화",
            ],
            "data_limitations": [
                "KIS 현재가 조회로 티커와 거래소를 인증했지만 회사명/섹터/실적 캘린더는 별도 보강이 필요합니다.",
                "FMP 무료 플랜 제한 때문에 재무제표와 밸류에이션 수치는 합성하지 않습니다.",
            ],
            "verification_source": "kis_overseas_quote",
        }
    except Exception as error:
        steps.append(
            {
                "source": "kis",
                "endpoint": "overseas-price",
                "status": "failed",
                "message": str(error),
            }
        )
        remember_ticker_lookup_diagnostics(normalized_symbol, steps)
        return None


def normalize_company_lookup(value: object) -> str:
    text = str(value or "").upper()
    text = sub(r"[\s\W_]+", "", text)
    for suffix in ["주식회사", "보통주", "ETF", "ETN", "INC", "INCORPORATED", "CORPORATION", "CORP", "PBC", "CLASSA"]:
        text = text.replace(suffix, "")
    return text


def resolve_ticker_symbol_from_alias(
    ticker: str,
    settings: Settings | None = None,
) -> str:
    raw_value = str(ticker or "").strip()
    requested_symbol = normalize_ticker(raw_value)
    registry = {
        **read_dynamic_ticker_registry(settings),
        **OFFICIAL_TICKER_REGISTRY,
    }

    lookup_key = normalize_company_lookup(raw_value)
    has_korean_text = any("\uac00" <= char <= "\ud7a3" for char in raw_value)

    def lookup_alias() -> str | None:
        if not lookup_key:
            return None
        partial_match: str | None = None
        for symbol, profile in registry.items():
            company_name = str(profile.get("company_name") or "")
            aliases = {
                symbol,
                company_name,
                company_name.replace(",", "").replace(".", ""),
                company_name.replace(" ETF", ""),
                company_name.replace("(합성)", ""),
            }
            aliases.update(ticker_aliases(symbol, profile))
            normalized_aliases = {normalize_company_lookup(alias) for alias in aliases if alias}
            if lookup_key in normalized_aliases:
                return symbol
            if has_korean_text and len(lookup_key) >= 3:
                for alias in normalized_aliases:
                    if len(alias) >= 3 and (lookup_key in alias or alias in lookup_key):
                        partial_match = partial_match or symbol
        return partial_match

    if has_korean_text:
        alias_symbol = lookup_alias()
        if alias_symbol:
            return alias_symbol

    if requested_symbol in registry:
        return requested_symbol

    alias_symbol = lookup_alias()
    if alias_symbol:
        return alias_symbol

    return requested_symbol


def verified_profile_for_ticker(
    ticker: str,
    settings: Settings | None = None,
) -> dict | None:
    requested_symbol = resolve_ticker_symbol_from_alias(ticker, settings)
    profile = OFFICIAL_TICKER_REGISTRY.get(requested_symbol)
    if profile:
        return profile

    dynamic_profile = read_dynamic_ticker_registry(settings).get(requested_symbol)
    if dynamic_profile:
        return dynamic_profile

    external_profile = lookup_ticker_profile_from_fmp(requested_symbol, settings)
    if external_profile:
        write_dynamic_ticker_profile(requested_symbol, external_profile, settings)
        return external_profile
    kis_profile = lookup_ticker_profile_from_kis(requested_symbol, settings)
    if kis_profile:
        write_dynamic_ticker_profile(requested_symbol, kis_profile, settings)
        return kis_profile
    return None


def verify_ticker_symbol(
    ticker: str,
    settings: Settings | None = None,
) -> TickerVerificationResponse:
    raw_requested = str(ticker or "").strip()
    requested_symbol = normalize_ticker(raw_requested)
    official_symbol = resolve_ticker_symbol_from_alias(raw_requested, settings)
    profile = verified_profile_for_ticker(official_symbol, settings)
    requested_label = raw_requested if raw_requested and raw_requested != requested_symbol else requested_symbol
    if profile:
        return TickerVerificationResponse(
            requested_symbol=requested_label,
            official_symbol=official_symbol,
            company_name=profile["company_name"],
            exchange=profile["exchange"],
            country=profile["country"],
            asset_type=profile["asset_type"],
            verified=True,
            verification_source=profile.get("verification_source", "local_official_registry"),
            message=(
                f"{requested_label} 공식 티커 인증 완료: "
                f"{profile['company_name']} ({profile['exchange']}) → {official_symbol}"
            ),
        )

    return TickerVerificationResponse(
        status="failed",
        requested_symbol=requested_label,
        official_symbol=official_symbol,
        company_name="",
        exchange="",
        country="",
        asset_type="unknown",
        verified=False,
        verification_source="local_official_registry",
        message=(
            f"{requested_label}는 현재 공식 티커 레지스트리에서 확인되지 않았습니다. "
            "회사명으로 입력했다면 공식 심볼 또는 등록된 회사명을 확인하세요. "
            "FMP/KIS 자동 인증도 실패했을 수 있습니다. 티커 진단에서 API 키/구독 제한과 심볼을 확인하세요."
        ),
    )


def verify_ticker_symbol_local_cached(
    ticker: str,
    settings: Settings | None = None,
) -> TickerVerificationResponse:
    active_settings = settings or get_settings()
    raw_requested = str(ticker or "").strip()
    requested_symbol = normalize_ticker(raw_requested)
    official_symbol = resolve_ticker_symbol_from_alias(raw_requested, active_settings)
    profile = OFFICIAL_TICKER_REGISTRY.get(official_symbol) or read_dynamic_ticker_registry(
        active_settings
    ).get(official_symbol)
    requested_label = raw_requested if raw_requested and raw_requested != requested_symbol else requested_symbol
    if profile:
        return TickerVerificationResponse(
            requested_symbol=requested_label,
            official_symbol=official_symbol,
            company_name=profile["company_name"],
            exchange=profile["exchange"],
            country=profile["country"],
            asset_type=profile["asset_type"],
            verified=True,
            verification_source=profile.get("verification_source", "local_or_dynamic_registry"),
            message=(
                f"{requested_label} 공식 티커 인증 완료: "
                f"{profile['company_name']} ({profile['exchange']}) → {official_symbol}"
            ),
        )
    return TickerVerificationResponse(
        status="failed",
        requested_symbol=requested_label,
        official_symbol=official_symbol,
        company_name="",
        exchange="",
        country="",
        asset_type="unknown",
        verified=False,
        verification_source="local_or_dynamic_registry",
        message=(
            f"{requested_label}는 로컬 공식 레지스트리나 자동 인증 캐시에서 확인되지 않았습니다. "
            "초기 화면에서는 외부 인증을 기다리지 않으므로, 필요하면 티커 진단에서 별도로 확인하세요."
        ),
    )


def diagnose_ticker_symbol(
    ticker: str,
    settings: Settings | None = None,
) -> dict:
    active_settings = settings or get_settings()
    raw_requested = str(ticker or "").strip()
    requested_symbol = normalize_ticker(raw_requested)
    resolved_symbol = resolve_ticker_symbol_from_alias(raw_requested, active_settings)
    local_profile = OFFICIAL_TICKER_REGISTRY.get(resolved_symbol)
    verification = verify_ticker_symbol(raw_requested, active_settings)
    dynamic_profile = read_dynamic_ticker_registry(active_settings).get(resolved_symbol)
    provider_attempts = TICKER_LOOKUP_DIAGNOSTICS.get(resolved_symbol) or TICKER_LOOKUP_DIAGNOSTICS.get(requested_symbol, [])
    if local_profile:
        resolution = "local_official_registry"
    elif verification.verified:
        resolution = verification.verification_source
    elif dynamic_profile:
        resolution = "dynamic_ticker_cache"
    else:
        resolution = "unverified"

    next_steps = []
    if verification.verified:
        next_steps.append("대시보드, 팀 리포트, 매매 전략 등 후속 분석을 바로 실행할 수 있습니다.")
        if resolution != "local_official_registry":
            next_steps.append("회사별 전용 KPI와 실적 캘린더는 리서치 메모로 보강해 정확도를 높이세요.")
    else:
        next_steps.extend(
            [
                "공식 거래소 심볼이 맞는지 확인하세요.",
                "KIS 해외주식 현재가 조회가 가능한 계좌/API 권한인지 확인하세요.",
                "자주 쓰는 티커라면 리서치 메모로 회사명, 섹터, 전용 KPI를 보강하세요.",
            ]
        )

    return {
        "status": "success" if verification.verified else "failed",
        "module": "ticker_diagnostics",
        "ticker": verification.official_symbol if verification.verified else requested_symbol,
        "resolution": resolution,
        "verification": verification.model_dump(mode="json"),
        "checks": [
            {
                "name": "local_official_registry",
                "passed": bool(local_profile),
                "message": "로컬 공식 레지스트리에 등록되어 있습니다."
                if local_profile
                else "로컬 공식 레지스트리에 없습니다.",
            },
            {
                "name": "dynamic_ticker_cache",
                "passed": bool(dynamic_profile),
                "message": "자동 인증 캐시에 저장되어 있습니다."
                if dynamic_profile
                else "자동 인증 캐시에 없습니다.",
            },
            {
                "name": "fmp_company_profile",
                "passed": verification.verification_source == "fmp_company_profile",
                "message": "FMP 회사 프로필로 인증되었습니다."
                if verification.verification_source == "fmp_company_profile"
                else "FMP 회사 프로필 인증 결과는 아래 provider_attempts를 확인하세요.",
            },
            {
                "name": "kis_overseas_quote",
                "passed": verification.verification_source == "kis_overseas_quote",
                "message": "KIS 해외주식 현재가 조회로 공식 티커를 인증했습니다."
                if verification.verification_source == "kis_overseas_quote"
                else "KIS 현재가 인증 결과는 아래 provider_attempts를 확인하세요.",
            },
        ],
        "provider_attempts": provider_attempts,
        "cache_path": str(dynamic_ticker_cache_path(active_settings)),
        "next_steps": next_steps,
    }


def ensure_verified_ticker(ticker: str, settings: Settings | None = None) -> str:
    requested_symbol = normalize_ticker(ticker)
    if requested_symbol in SPECIAL_RESEARCH_KEYS:
        return requested_symbol
    verification = verify_ticker_symbol(ticker, settings)
    if not verification.verified:
        raise HTTPException(status_code=422, detail=verification.message)
    return verification.official_symbol


def local_interest_verification_response(
    ticker_or_company: str,
    settings: Settings | None = None,
) -> tuple[str, TickerVerificationResponse]:
    """관심종목 저장은 외부 API 대기 없이 로컬/캐시 기준으로 먼저 처리합니다."""
    raw_lookup = str(ticker_or_company or "").strip()
    resolved_symbol = resolve_ticker_symbol_from_alias(raw_lookup, settings)
    normalized_symbol = normalize_ticker(resolved_symbol or raw_lookup)
    profile = OFFICIAL_TICKER_REGISTRY.get(normalized_symbol) or read_dynamic_ticker_registry(settings).get(normalized_symbol)
    if profile:
        return normalized_symbol, TickerVerificationResponse(
            status="success",
            requested_symbol=raw_lookup or normalized_symbol,
            official_symbol=normalized_symbol,
            company_name=str(profile.get("company_name") or raw_lookup or normalized_symbol),
            exchange=str(profile.get("exchange") or ""),
            country=str(profile.get("country") or ""),
            asset_type=str(profile.get("asset_type") or "equity"),
            verified=True,
            verification_source=str(profile.get("verification_source") or "local_official_registry"),
            message=f"{profile.get('company_name') or normalized_symbol} 기준으로 관심종목에 저장했습니다.",
        )
    fallback_symbol = normalized_symbol or normalize_ticker(raw_lookup)
    return fallback_symbol, TickerVerificationResponse(
        status="pending",
        requested_symbol=raw_lookup,
        official_symbol=fallback_symbol,
        company_name=raw_lookup or fallback_symbol,
        exchange="",
        country="",
        asset_type="unknown",
        verified=False,
        verification_source="save_first_pending_verification",
        message="먼저 관심종목에 저장했습니다. 외부 API 인증은 이후 티커 진단 또는 데이터 조회 시 보강합니다.",
    )


def ticker_verification_metadata(ticker: str, settings: Settings | None = None) -> dict:
    requested_symbol = normalize_ticker(ticker)
    if requested_symbol in SPECIAL_RESEARCH_KEYS:
        return {
            "requested_symbol": requested_symbol,
            "official_symbol": requested_symbol,
            "company_name": requested_symbol,
            "exchange": "research_scope",
            "country": "global",
            "asset_type": "research_scope",
            "verified": True,
            "verification_source": "special_research_scope",
            "message": f"{requested_symbol}는 종목이 아닌 리서치 저장 범위입니다.",
        }
    return verify_ticker_symbol(ticker, settings).model_dump(mode="json")


def manifest_with_ticker_verification(ticker: str, entry: dict) -> dict:
    return {
        **entry,
        "ticker_verification": ticker_verification_metadata(ticker),
    }


def korean_disclosure_earnings_defaults(today_value: date | None = None) -> dict:
    today = today_value or current_storage_date()
    current_year = today.year
    schedule = [
        (date(current_year, 3, 31), f"FY{current_year - 1} Annual", date(current_year - 1, 11, 14), date(current_year, 5, 15)),
        (date(current_year, 5, 15), f"FY{current_year} Q1", date(current_year, 3, 31), date(current_year, 8, 14)),
        (date(current_year, 8, 14), f"FY{current_year} Q2", date(current_year, 5, 15), date(current_year, 11, 14)),
        (date(current_year, 11, 14), f"FY{current_year} Q3", date(current_year, 8, 14), date(current_year + 1, 3, 31)),
    ]
    latest_due = date(current_year - 1, 11, 14)
    latest_quarter = f"FY{current_year - 1} Q3"
    previous_due = date(current_year - 1, 8, 14)
    next_due = date(current_year, 3, 31)
    for due_date, quarter_label, previous_date, next_date in schedule:
        if today >= due_date:
            latest_due = due_date
            latest_quarter = quarter_label
            previous_due = previous_date
            next_due = next_date
        else:
            next_due = due_date
            break
    return {
        "latest_reported_quarter": latest_quarter,
        "latest_reported_earnings_date": latest_due.isoformat(),
        "previous_earnings_date": previous_due.isoformat(),
        "next_earnings_date": next_due.isoformat(),
        "earnings_calendar_source": "DART 정기보고서 제출 기한 기준 자동 산출",
    }


def with_earnings_calendar_defaults(ticker: str, profile: dict) -> dict:
    if not profile:
        return profile
    enriched = dict(profile)
    if enriched.get("country") == "KR" and not enriched.get("latest_reported_quarter"):
        defaults = korean_disclosure_earnings_defaults()
        for key, value in defaults.items():
            enriched.setdefault(key, value)
        company_name = enriched.get("company_name") or ticker
        watch_kpis = enriched.get("watch_kpis") or ["매출", "영업이익", "마진", "현금흐름"]
        enriched.setdefault(
            "latest_earnings_profile",
            {
                "quarter": defaults["latest_reported_quarter"],
                "earnings_report_date": defaults["latest_reported_earnings_date"],
                "previous_earnings_summary": (
                    f"{company_name}의 최신 공시 가능 기준은 {defaults['latest_reported_quarter']}입니다. "
                    "정확한 매출, 이익, 마진, 주가 반응은 DART/IR 자료나 사용자가 입력한 수치로 보강해야 합니다."
                ),
                "next_earnings_guidance": (
                    "다음 실적 전 확인할 KPI: " + ", ".join(str(item) for item in watch_kpis[:5])
                ),
                "source_url": "https://dart.fss.or.kr/",
            },
        )
    return enriched


def official_ticker_profile(
    ticker: str,
    settings: Settings | None = None,
    *,
    refresh_external: bool = True,
) -> dict:
    profile = verified_profile_for_ticker(ticker, settings) or {}
    profile = with_earnings_calendar_defaults(ticker, profile)
    if refresh_external:
        profile = merge_dart_latest_earnings_calendar(ticker, profile, settings)
    return merge_cached_earnings_calendar(ticker, profile, settings, refresh=refresh_external)

def ticker_company_name(ticker: str) -> str:
    return official_ticker_profile(ticker).get("company_name", ticker)


def ticker_business_context(ticker: str) -> str:
    return official_ticker_profile(ticker).get(
        "business_context",
        "해당 기업의 사업 모델, 매출 동력, 경쟁 우위, 리스크를 중심으로 분석",
    )


def analysis_focus_for_ticker(ticker: str, requested_focus: str | None) -> str:
    legacy_default_focus = "AI 수요, 밸류에이션, 매매 전략, 포트폴리오 리스크"
    if requested_focus and not (
        normalize_ticker(ticker) != "NVDA"
        and requested_focus.strip() == legacy_default_focus
    ):
        return requested_focus
    return official_ticker_profile(ticker).get(
        "analysis_focus",
        "사업 모델, 매출 성장, 마진, 밸류에이션, 주요 리스크",
    )


def ticker_watch_kpis(ticker: str) -> list[str]:
    return official_ticker_profile(ticker).get(
        "watch_kpis",
        ["매출 성장률", "매출총이익률", "영업이익률", "잉여현금흐름", "가이던스 변화"],
    )


def normalize_quarter_label(value: str | None) -> str:
    if not value:
        return ""
    return sub(r"\s+", " ", value.strip().upper())


def ticker_earnings_date_for_quarter(
    ticker: str,
    quarter: str | None,
    settings: Settings | None = None,
    *,
    refresh_external: bool = True,
) -> str | None:
    profile = official_ticker_profile(ticker, settings, refresh_external=refresh_external)
    calendar = profile.get("earnings_dates_by_quarter", {})
    if not isinstance(calendar, dict):
        return None
    normalized_quarter = normalize_quarter_label(quarter)
    normalized_calendar = {
        normalize_quarter_label(key): value for key, value in calendar.items()
    }
    return normalized_calendar.get(normalized_quarter)


def ticker_adjacent_earnings_date(
    ticker: str,
    quarter: str | None,
    direction: int,
    settings: Settings | None = None,
    *,
    refresh_external: bool = True,
) -> str | None:
    profile = official_ticker_profile(ticker, settings, refresh_external=refresh_external)
    sequence = profile.get("earnings_quarter_sequence", [])
    if not isinstance(sequence, list):
        return None
    normalized_quarter = normalize_quarter_label(quarter)
    normalized_sequence = [normalize_quarter_label(item) for item in sequence]
    if normalized_quarter not in normalized_sequence:
        return None
    adjacent_index = normalized_sequence.index(normalized_quarter) + direction
    if adjacent_index < 0 or adjacent_index >= len(sequence):
        return None
    return ticker_earnings_date_for_quarter(
        ticker,
        sequence[adjacent_index],
        settings,
        refresh_external=refresh_external,
    )


def latest_earnings_profile_for_ticker(
    ticker: str,
    settings: Settings | None = None,
    *,
    refresh_external: bool = True,
) -> dict:
    profile = official_ticker_profile(ticker, settings, refresh_external=refresh_external)
    latest_profile = profile.get("latest_earnings_profile", {})
    return latest_profile if isinstance(latest_profile, dict) else {}


def latest_earnings_profile_summary(latest_earnings: dict) -> str:
    quarter = latest_earnings.get("quarter") or "최신 발표 실적"
    report_date = latest_earnings.get("earnings_report_date") or "일정 보강 필요"
    parts = [f"{quarter} 기준일 {report_date}"]

    revenue_reported = latest_earnings.get("revenue_reported")
    revenue_expected = latest_earnings.get("revenue_expected")
    if revenue_reported is not None or revenue_expected is not None:
        revenue_text = f"매출 발표 {revenue_reported if revenue_reported is not None else '미입력'}"
        if revenue_expected is not None:
            revenue_text += f" / 예상 {revenue_expected}"
        parts.append(revenue_text)

    eps_reported = latest_earnings.get("eps_reported")
    eps_expected = latest_earnings.get("eps_expected")
    if eps_reported is not None or eps_expected is not None:
        eps_text = f"EPS 발표 {eps_reported if eps_reported is not None else '미입력'}"
        if eps_expected is not None:
            eps_text += f" / 예상 {eps_expected}"
        parts.append(eps_text)

    price_reaction = latest_earnings.get("price_reaction")
    if price_reaction:
        parts.append(f"주가 반응 {price_reaction}")

    previous_summary = latest_earnings.get("previous_earnings_summary")
    if previous_summary:
        parts.append(f"직전/최신 실적 메모: {previous_summary}")

    next_guidance = latest_earnings.get("next_earnings_guidance")
    if next_guidance:
        parts.append(f"다음 실적 체크포인트: {next_guidance}")

    if len(parts) == 1:
        parts.append("실제 발표 수치, 컨센서스, 주가 반응은 추가 입력 또는 공시 데이터 보강이 필요합니다.")
    return " | ".join(str(part) for part in parts)


def is_latest_earnings_placeholder(ticker: str, quarter: str | None) -> bool:
    normalized_quarter = normalize_quarter_label(quarter)
    normalized_ticker = normalize_ticker(ticker)
    placeholder_values = {
        "",
        "최근 실적 분기 입력",
        f"{normalized_ticker} 최근 실적 분기 입력",
        "최신 실적",
        "최신 발표 실적",
        "가장 최근 발표 실적",
        "LATEST",
        "LATEST REPORTED",
    }
    return normalized_quarter in {normalize_quarter_label(item) for item in placeholder_values}


def request_has_explicit_current_earnings_evidence(request: EarningsReactionRequest) -> bool:
    return (
        bool(request.earnings_report_date)
        or bool(request.price_reaction.strip())
        or request.eps_reported is not None
        or request.eps_expected is not None
        or request.revenue_reported is not None
        or request.revenue_expected is not None
        or bool(request.key_numbers)
        or bool(request.management_tone)
        or bool(request.market_context)
        or request.guidance_change.strip() not in {"", "유지", "중립", "no change", "unchanged"}
    )


def enrich_earnings_request_with_profile_dates(
    ticker: str,
    request: EarningsReactionRequest,
    settings: Settings | None = None,
    *,
    refresh_external: bool = True,
) -> EarningsReactionRequest:
    profile = official_ticker_profile(ticker, settings, refresh_external=refresh_external)
    latest_earnings = profile.get("latest_earnings_profile", {})
    if not isinstance(latest_earnings, dict):
        latest_earnings = latest_earnings_profile_for_ticker(
            ticker,
            settings,
            refresh_external=False,
        )
    updates = {}
    quarter = request.quarter
    latest_reported_quarter = profile.get("latest_reported_quarter")
    should_force_latest = bool(
        latest_reported_quarter
        and not request_has_explicit_current_earnings_evidence(request)
        and normalize_quarter_label(quarter)
        != normalize_quarter_label(latest_reported_quarter)
    )
    if latest_reported_quarter and (
        is_latest_earnings_placeholder(ticker, quarter) or should_force_latest
    ):
        quarter = latest_reported_quarter
        updates["quarter"] = latest_reported_quarter
    if (
        latest_earnings
        and normalize_quarter_label(quarter)
        == normalize_quarter_label(latest_earnings.get("quarter"))
    ):
        for field_name in [
            "price_reaction",
            "previous_earnings_summary",
            "next_earnings_guidance",
            "management_tone",
            "market_context",
            "guidance_change",
        ]:
            current_value = getattr(request, field_name)
            profile_value = latest_earnings.get(field_name)
            if profile_value and (not current_value or str(current_value).strip() in {"유지", "중립"}):
                updates[field_name] = profile_value
        numeric_defaults = {
            "eps_reported": latest_earnings.get("eps_reported"),
            "eps_expected": latest_earnings.get("eps_expected"),
            "revenue_reported": latest_earnings.get("revenue_reported"),
            "revenue_expected": latest_earnings.get("revenue_expected"),
        }
        for field_name, profile_value in numeric_defaults.items():
            if getattr(request, field_name) is None and profile_value is not None:
                updates[field_name] = profile_value
        if not request.key_numbers and latest_earnings.get("key_numbers"):
            updates["key_numbers"] = latest_earnings["key_numbers"]
        if not request.earnings_report_date and latest_earnings.get("earnings_report_date"):
            updates["earnings_report_date"] = latest_earnings["earnings_report_date"]
    if not request.earnings_report_date:
        quarter_date = ticker_earnings_date_for_quarter(
            ticker,
            quarter,
            settings,
            refresh_external=refresh_external,
        )
        if quarter_date:
            updates["earnings_report_date"] = quarter_date
    if not request.previous_earnings_date and profile.get("previous_earnings_date"):
        adjacent_previous_date = ticker_adjacent_earnings_date(
            ticker,
            quarter,
            -1,
            settings,
            refresh_external=refresh_external,
        )
        updates["previous_earnings_date"] = adjacent_previous_date or profile["previous_earnings_date"]
    if not request.next_earnings_date and profile.get("next_earnings_date"):
        adjacent_next_date = ticker_adjacent_earnings_date(
            ticker,
            quarter,
            1,
            settings,
            refresh_external=refresh_external,
        )
        updates["next_earnings_date"] = adjacent_next_date or profile["next_earnings_date"]
    if not updates:
        return request
    return request.model_copy(update=updates)


def injected_data_label_map(injected_data: list[InjectedDataPoint]) -> dict[str, InjectedDataPoint]:
    label_map: dict[str, InjectedDataPoint] = {}
    for point in injected_data:
        label = str(point.label or "").strip()
        if label and label not in label_map:
            label_map[label] = point
    return label_map


def injected_financial_number(
    label_map: dict[str, InjectedDataPoint],
    *labels: str,
) -> float | None:
    for label in labels:
        point = label_map.get(label)
        if not point:
            continue
        value = parse_float_or_none(point.value)
        if value is not None:
            return value
    return None


def enrich_earnings_request_with_injected_financials(
    request: EarningsReactionRequest,
    injected_data: list[InjectedDataPoint],
) -> EarningsReactionRequest:
    """
    실시간/공시 데이터 프로바이더가 가져온 재무 수치를 실적 분석 입력으로 연결합니다.
    컨센서스가 없는 수치는 key_numbers에 남겨 정량 근거로 표시하고, 매출은 발표 수치가
    비어 있을 때 reported 값으로도 사용합니다.
    """
    label_map = injected_data_label_map(injected_data)
    revenue = injected_financial_number(label_map, "dart_revenue", "revenue")
    operating_income = injected_financial_number(
        label_map,
        "dart_operating_income",
        "operating_income",
    )
    net_income = injected_financial_number(label_map, "dart_net_income", "net_income")
    total_assets = injected_financial_number(label_map, "dart_total_assets", "total_assets")

    updates: dict[str, object] = {}
    key_numbers = dict(request.key_numbers or {})
    if revenue is not None:
        if request.revenue_reported is None:
            updates["revenue_reported"] = revenue
        else:
            key_numbers.setdefault("매출", revenue)
    if operating_income is not None:
        key_numbers.setdefault("영업이익", operating_income)
    if net_income not in {None, 0}:
        key_numbers.setdefault("순이익", net_income)
    elif net_income == 0:
        key_numbers.setdefault("순이익", "DART 원천값 0 또는 미매핑, 원문 확인 필요")
    if total_assets is not None:
        key_numbers.setdefault("총자산", total_assets)
    if key_numbers != (request.key_numbers or {}):
        updates["key_numbers"] = key_numbers

    if updates:
        return request.model_copy(update=updates)
    return request


def build_ticker_profile(
    ticker: str,
    settings: Settings | None = None,
    *,
    refresh_external: bool = True,
) -> TickerProfileResponse:
    verification = verify_ticker_symbol(ticker, settings)
    if not verification.verified:
        raise HTTPException(status_code=422, detail=verification.message)
    profile = official_ticker_profile(
        verification.official_symbol,
        settings,
        refresh_external=refresh_external,
    )
    return TickerProfileResponse(
        ticker=verification.official_symbol,
        company_name=verification.company_name,
        exchange=verification.exchange,
        country=verification.country,
        asset_type=verification.asset_type,
        sector=profile.get("sector"),
        industry=profile.get("industry"),
        business_context=profile.get("business_context"),
        analysis_focus=profile.get("analysis_focus"),
        watch_kpis=profile.get("watch_kpis", []),
        data_limitations=profile.get("data_limitations", []),
        latest_reported_quarter=profile.get("latest_reported_quarter"),
        latest_reported_earnings_date=profile.get("latest_reported_earnings_date"),
        previous_earnings_date=profile.get("previous_earnings_date"),
        next_earnings_date=profile.get("next_earnings_date"),
        earnings_calendar_source=profile.get("earnings_calendar_source"),
        latest_earnings_profile=profile.get("latest_earnings_profile", {}),
        verification=verification,
    )


def current_storage_date() -> date:
    try:
        korea_timezone = ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        korea_timezone = timezone(timedelta(hours=9))

    return datetime.now(korea_timezone).date()


def current_storage_timestamp() -> str:
    try:
        korea_timezone = ZoneInfo("Asia/Seoul")
    except ZoneInfoNotFoundError:
        korea_timezone = timezone(timedelta(hours=9))

    return datetime.now(korea_timezone).isoformat(timespec="seconds")


@app.post("/api/v1/export/result-xlsx", dependencies=[Depends(verify_user_token)])
def export_result_xlsx(payload: dict = Body(...)) -> StreamingResponse:
    result_text = str(payload.get("result_text") or "").strip()
    if not result_text or result_text == "대기 중입니다.":
        raise HTTPException(status_code=422, detail="엑셀로 변환할 화면 결과가 없습니다.")

    workbook_bytes = build_simple_xlsx(
        collect_result_export_sheets(payload, generated_at_fallback=current_storage_timestamp())
    )
    timestamp = current_storage_timestamp().replace(":", "").replace("-", "")[:15]
    filename = f"research-os-result-{timestamp}.xlsx"
    return StreamingResponse(
        io.BytesIO(workbook_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def user_state_dir(settings: Settings) -> Path:
    state_dir = resolve_vault_dir(settings.research_vault_dir) / "_system"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def portfolio_store_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "user_portfolios.json"


def interest_list_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "interest_list.json"


def market_close_journal_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "market_close_journal.json"


def latest_daily_brief_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "latest_daily_brief.json"


def news_inbox_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "news_inbox.json"


def research_automation_status_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "research_automation_status.json"


def storage_duplicate_review_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "storage_duplicate_review.json"


def dossier_refresh_queue_status_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "dossier_refresh_queue_status.json"


def backend_health_alert_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "backend_health_alerts.jsonl"


def read_json_store(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return payload if isinstance(payload, dict) else default


def write_json_store(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_jsonl(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False))
        file.write("\n")


def portfolio_store_key(portfolio_name: str) -> str:
    normalized = sub(r"[^\w-]+", "-", portfolio_name.strip().upper()).strip("-_")
    return normalized or "DEFAULT"


def research_memory_store_key(value: str) -> str:
    raw = str(value or "").strip()
    ascii_key = normalize_ticker(raw)
    if ascii_key != "UNKNOWN":
        return ascii_key
    return portfolio_store_key(raw)


def resolve_research_memory_key(value: str, settings: Settings) -> str:
    key = research_memory_store_key(value)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    if key in SPECIAL_RESEARCH_KEYS or (vault_dir / key).exists():
        return key
    return ensure_verified_ticker(key, settings)


def read_portfolio_store(settings: Settings) -> dict:
    return read_json_store(portfolio_store_path(settings), {"portfolios": {}})


def portfolio_name_sort_key(portfolio: SavedPortfolio) -> str:
    return portfolio.portfolio_name.casefold()


def parse_float_or_none(value: object) -> float | None:
    if value is None:
        return None
    try:
        text = str(value).strip().replace(",", "")
        if not text or text.lower() == "n/a":
            return None
        return float(text)
    except (TypeError, ValueError):
        return None


def latest_provider_price(ticker: str, settings: Settings) -> tuple[float | None, str | None]:
    cache_key = normalize_ticker(ticker)
    if cache_key in PORTFOLIO_PRICE_CACHE:
        return PORTFOLIO_PRICE_CACHE[cache_key]
    try:
        data_points = collect_analysis_input_data(
            ticker=ticker,
            provided_data=[],
            auto_inject_data=True,
            settings=settings,
        )
    except Exception:
        return None, None
    for point in data_points:
        if point.label == "last_price":
            price = parse_float_or_none(point.value)
            if price is not None and price > 0:
                source = point.source_url or "data_provider"
                PORTFOLIO_PRICE_CACHE[cache_key] = (price, source)
                return price, source
    return None, None


def infer_holding_fx_rate(holding: PortfolioHolding) -> float:
    if holding.currency.upper() != "USD":
        return 1.0
    if (
        holding.cost_basis
        and holding.quantity
        and holding.average_cost
        and holding.quantity > 0
        and holding.average_cost > 0
    ):
        inferred = holding.cost_basis / (holding.quantity * holding.average_cost)
        if inferred > 0:
            return inferred
    if (
        holding.market_value
        and holding.quantity
        and holding.average_cost
        and holding.quantity > 0
        and holding.average_cost > 0
        and holding.current_price is None
    ):
        inferred = holding.market_value / (holding.quantity * holding.average_cost)
        if inferred > 0:
            return inferred
    return 1.0


def enrich_portfolio_holding(
    holding: PortfolioHolding,
    settings: Settings,
    *,
    refresh_price: bool,
) -> PortfolioHolding:
    price_source = holding.price_source
    current_price = holding.current_price
    currency = (holding.currency or "USD").upper()
    ticker = normalize_ticker(holding.ticker)

    if refresh_price and ticker != "CASH" and currency in {"KRW", "USD"}:
        provider_price, provider_source = latest_provider_price(ticker, settings)
        if provider_price is not None:
            current_price = provider_price
            price_source = provider_source or "data_provider"

    if not refresh_price:
        market_value = holding.market_value
        cost_basis = holding.cost_basis
        unrealized_gain = holding.unrealized_gain
        unrealized_return = holding.unrealized_return
        if unrealized_gain is None and market_value is not None and cost_basis is not None:
            unrealized_gain = market_value - cost_basis
        if (
            unrealized_return is None
            and unrealized_gain is not None
            and cost_basis is not None
            and cost_basis > 0
        ):
            unrealized_return = unrealized_gain / cost_basis
        return holding.model_copy(
            update={
                "ticker": ticker,
                "currency": currency,
                "current_price": round(current_price, 4)
                if current_price is not None
                else None,
                "market_value": round(market_value, 2)
                if market_value is not None
                else None,
                "cost_basis": round(cost_basis, 2)
                if cost_basis is not None
                else None,
                "unrealized_gain": round(unrealized_gain, 2)
                if unrealized_gain is not None
                else None,
                "unrealized_return": round(unrealized_return, 4)
                if unrealized_return is not None
                else None,
                "price_source": price_source,
            }
        )

    fx_rate = infer_holding_fx_rate(holding)
    cost_basis = None
    market_value = holding.market_value
    if holding.quantity is not None and holding.average_cost is not None:
        cost_basis = holding.quantity * holding.average_cost * fx_rate
    if holding.quantity is not None and current_price is not None:
        market_value = holding.quantity * current_price * fx_rate

    unrealized_gain = None
    unrealized_return = None
    if (
        cost_basis is not None
        and cost_basis > 0
        and market_value is not None
        and current_price is not None
    ):
        unrealized_gain = market_value - cost_basis
        unrealized_return = unrealized_gain / cost_basis

    return holding.model_copy(
        update={
            "ticker": ticker,
            "currency": currency,
            "current_price": round(current_price, 4)
            if current_price is not None
            else None,
            "market_value": round(market_value, 2)
            if market_value is not None
            else None,
            "cost_basis": round(cost_basis, 2)
            if cost_basis is not None
            else None,
            "unrealized_gain": round(unrealized_gain, 2)
            if unrealized_gain is not None
            else None,
            "unrealized_return": round(unrealized_return, 4)
            if unrealized_return is not None
            else None,
            "price_source": price_source,
        }
    )


def sort_and_weight_portfolio(
    portfolio: SavedPortfolio,
    settings: Settings,
    *,
    refresh_prices: bool = False,
) -> SavedPortfolio:
    enriched_holdings = [
        enrich_portfolio_holding(holding, settings, refresh_price=refresh_prices)
        for holding in portfolio.holdings
    ]
    total_value = sum(holding.market_value or 0 for holding in enriched_holdings)
    if total_value <= 0:
        total_value = portfolio.portfolio_value or 0

    weighted_holdings = []
    for holding in enriched_holdings:
        weight = (holding.market_value or 0) / total_value if total_value > 0 else holding.weight
        weighted_holdings.append(
            holding.model_copy(
                update={
                    "weight": round(weight, 4) if weight is not None else None,
                }
            )
        )

    weighted_holdings.sort(
        key=lambda holding: (
            holding.market_value or 0,
            holding.ticker,
        ),
        reverse=True,
    )
    return portfolio.model_copy(
        update={
            "holdings": weighted_holdings,
            "portfolio_value": round(total_value, 2) if total_value else portfolio.portfolio_value,
            "holding_count": len(weighted_holdings),
        }
    )


def normalize_saved_portfolio(
    request: PortfolioSaveRequest,
    existing: dict | None,
    settings: Settings,
) -> SavedPortfolio:
    now = current_storage_timestamp()
    portfolio_name = request.portfolio_name.strip() or "default"
    normalized_holdings = []
    for holding in request.holdings:
        ticker = normalize_ticker(holding.ticker)
        if ticker and ticker != "CASH":
            verification = verify_ticker_symbol(ticker, settings)
            if verification.verified:
                ticker = verification.official_symbol
                profile = official_ticker_profile(ticker, settings)
                holding = holding.model_copy(
                    update={
                        "ticker": ticker,
                        "name": holding.name or profile.get("company_name"),
                        "sector": holding.sector
                        if holding.sector and holding.sector != "Unknown"
                        else profile.get("sector", "Unknown"),
                    }
                )
            else:
                holding = holding.model_copy(update={"ticker": ticker})
        else:
            holding = holding.model_copy(update={"ticker": ticker or "CASH"})
        normalized_holdings.append(holding)

    saved = SavedPortfolio(
        portfolio_name=portfolio_name,
        holdings=normalized_holdings,
        portfolio_value=request.portfolio_value,
        max_single_position_weight=request.max_single_position_weight,
        max_sector_weight=request.max_sector_weight,
        max_theme_weight=request.max_theme_weight,
        notes=request.notes,
        holding_count=len(normalized_holdings),
        created_at=(existing or {}).get("created_at", now),
        updated_at=now,
    )
    return sort_and_weight_portfolio(saved, settings, refresh_prices=True)


def portfolio_store_response(
    settings: Settings,
    *,
    active_portfolio: SavedPortfolio | None = None,
) -> PortfolioStoreResponse:
    store = read_portfolio_store(settings)
    records = [
        sort_and_weight_portfolio(
            SavedPortfolio.model_validate(item),
            settings,
            refresh_prices=False,
        )
        for item in store.get("portfolios", {}).values()
    ]
    records.sort(key=portfolio_name_sort_key)
    if active_portfolio is not None:
        active_portfolio = sort_and_weight_portfolio(
            active_portfolio,
            settings,
            refresh_prices=False,
        )
    return PortfolioStoreResponse(
        portfolios=records,
        active_portfolio=active_portfolio,
        storage_path=str(portfolio_store_path(settings)),
    )


def read_interest_list(settings: Settings) -> dict:
    return read_json_store(
        interest_list_path(settings),
        {"tickers": [], "sectors": [], "updated_at": None},
    )


def interest_collection_targets_path(settings: Settings) -> Path:
    return user_state_dir(settings) / "interest_collection_targets.json"


def normalize_interest_list(
    request: InterestListUpdateRequest,
    settings: Settings,
) -> InterestListResponse:
    now = current_storage_timestamp()
    existing = read_interest_list(settings)
    existing_tickers = {
        normalize_ticker(item.get("ticker", "")): item
        for item in existing.get("tickers", [])
        if isinstance(item, dict)
    }
    existing_sectors = {
        str(item.get("name", "")).strip().lower(): item
        for item in existing.get("sectors", [])
        if isinstance(item, dict)
    }

    prepared_tickers: list[tuple[str, InterestTicker, TickerVerificationResponse, dict]] = []
    for item in request.tickers:
        raw_lookup = str(item.ticker or "").strip()
        if not raw_lookup:
            continue
        if item.verification and item.verification.verified and item.verification.official_symbol:
            official_symbol = normalize_ticker(item.verification.official_symbol)
            verification = item.verification
        else:
            official_symbol, verification = local_interest_verification_response(raw_lookup, settings)
        official_symbol = normalize_ticker(official_symbol)
        prior = existing_tickers.get(official_symbol, {})
        prepared_tickers.append((official_symbol, item, verification, prior))

    normalized_tickers = []
    latest_by_ticker: dict[str, tuple[InterestTicker, TickerVerificationResponse, dict]] = {}
    for official_symbol, item, verification, prior in prepared_tickers:
        latest_by_ticker[official_symbol] = (item, verification, prior)
    for official_symbol, (item, verification, prior) in latest_by_ticker.items():
        tags = list(item.tags or [])
        if not verification.verified and "verification_pending" not in tags:
            tags.append("verification_pending")
        normalized_tickers.append(
            InterestTicker(
                ticker=official_symbol,
                priority=item.priority or "medium",
                thesis=item.thesis,
                notes=item.notes,
                tags=tags,
                verification=verification,
                created_at=prior.get("created_at", now),
                updated_at=now,
            )
        )

    latest_sectors: dict[str, InterestSector] = {}
    for item in request.sectors:
        name = item.name.strip()
        if not name:
            continue
        latest_sectors[name.lower()] = item

    normalized_sectors = []
    for item in latest_sectors.values():
        name = item.name.strip()
        prior = existing_sectors.get(name.lower(), {})
        normalized_sectors.append(
            InterestSector(
                name=name,
                region=item.region or "US",
                priority=item.priority or "medium",
                thesis=item.thesis,
                notes=item.notes,
                tags=item.tags,
                created_at=prior.get("created_at", now),
                updated_at=now,
            )
        )

    return InterestListResponse(
        tickers=normalized_tickers,
        sectors=normalized_sectors,
        updated_at=now,
        storage_path=str(interest_list_path(settings)),
    )


def read_market_close_journal(settings: Settings) -> dict:
    return read_json_store(
        market_close_journal_path(settings),
        {"entries": [], "updated_at": None},
    )


def normalize_market_code(value: str | None) -> str:
    text = (value or "US").strip().upper()
    aliases = {
        "미국": "US",
        "USA": "US",
        "UNITED STATES": "US",
        "한국": "KR",
        "KOREA": "KR",
        "KOSPI": "KR",
        "KOSDAQ": "KR",
        "GLOBAL": "GLOBAL",
        "글로벌": "GLOBAL",
    }
    return aliases.get(text, text or "US")


def market_research_key(market: str) -> str:
    return {
        "US": "MARKET-US",
        "KR": "MARKET-KR",
        "GLOBAL": "MARKET-GLOBAL",
    }.get(market, f"MARKET-{market}")


NAVER_KOREA_INDEX_CODES = ("KOSPI", "KOSDAQ")


def fetch_naver_korea_index_snapshot(settings: Settings) -> list[str]:
    if not settings.naver_finance_enabled:
        return []

    base_url = settings.naver_finance_base_url.rstrip("/")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
    }
    snapshot: list[str] = []
    try:
        with httpx.Client(
            timeout=settings.naver_finance_timeout_seconds,
            headers=headers,
            trust_env=False,
        ) as client:
            for code in NAVER_KOREA_INDEX_CODES:
                response = client.get(f"{base_url}/api/index/{code}/basic")
                response.raise_for_status()
                payload = response.json()
                name = payload.get("stockName") or code
                close_price = payload.get("closePrice") or "n/a"
                diff = payload.get("compareToPreviousClosePrice") or "n/a"
                ratio = payload.get("fluctuationsRatio") or "n/a"
                direction = (payload.get("compareToPreviousPrice") or {}).get("text") or "n/a"
                market_status = payload.get("marketStatus") or "n/a"
                traded_at = payload.get("localTradedAt") or current_storage_timestamp()
                sign = "+" if direction == "상승" and not str(diff).startswith("-") else ""
                ratio_sign = "+" if direction == "상승" and not str(ratio).startswith("-") else ""
                snapshot.append(
                    f"{name}: {close_price}p ({sign}{diff}, {ratio_sign}{ratio}%, {direction}, {market_status}, {traded_at})"
                )
    except Exception as exc:
        snapshot.append(
            f"네이버 증권 보조 데이터 경고: KOSPI/KOSDAQ 자동 수집 실패 - {_safe_display_error(exc)}"
        )
    return snapshot


def normalize_kr_stock_code(value: str) -> str:
    text = str(value or "").strip().upper()
    match = search(r"(?<!\d)(\d{6})(?!\d)", text)
    if match:
        return match.group(1)
    return normalize_ticker(text)


def is_naver_domestic_stock_code(value: str) -> bool:
    return bool(search(r"^[0-9A-Z]{6}$", str(value or "").strip().upper()))


def fetch_naver_domestic_stock_basic(ticker: str, settings: Settings) -> dict:
    if not settings.naver_finance_enabled:
        raise HTTPException(status_code=422, detail="NAVER_FINANCE_ENABLED=false 상태입니다.")
    code = normalize_kr_stock_code(ticker)
    if not is_naver_domestic_stock_code(code):
        code = ensure_verified_ticker(ticker, settings)
    if not is_naver_domestic_stock_code(code):
        raise HTTPException(
            status_code=422,
            detail="네이버 국내 차트 분석은 삼양식품 같은 회사명 또는 003230/0117V0 같은 국내 종목코드가 필요합니다.",
        )

    base_url = settings.naver_finance_base_url.rstrip("/")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
    }
    with httpx.Client(
        timeout=settings.naver_finance_timeout_seconds,
        headers=headers,
        trust_env=False,
    ) as client:
        response = client.get(f"{base_url}/api/stock/{code}/basic")
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict) or not payload.get("stockName"):
        raise HTTPException(status_code=502, detail=f"네이버 기본 정보에서 {code} 종목명을 확인하지 못했습니다.")
    register_naver_korean_ticker(code, str(payload.get("stockName") or code), settings)
    return payload


def fetch_naver_domestic_price_history(
    ticker: str,
    settings: Settings,
    page_size: int = 180,
) -> tuple[dict, list[dict]]:
    basic = fetch_naver_domestic_stock_basic(ticker, settings)
    code = normalize_kr_stock_code(ticker)
    if not is_naver_domestic_stock_code(code):
        code = ensure_verified_ticker(ticker, settings)
    base_url = settings.naver_finance_base_url.rstrip("/")
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
    }
    request_page_size = 60
    pages_to_fetch = max(1, math.ceil(max(page_size, request_page_size) / request_page_size))
    payload: list[dict] = []
    with httpx.Client(
        timeout=max(settings.naver_finance_timeout_seconds, 10),
        headers=headers,
        trust_env=False,
    ) as client:
        for page in range(1, pages_to_fetch + 1):
            response = client.get(
                f"{base_url}/api/stock/{code}/price",
                params={"pageSize": request_page_size, "page": page},
            )
            response.raise_for_status()
            page_payload = response.json()
            if not isinstance(page_payload, list):
                raise HTTPException(status_code=502, detail=f"네이버 일별 시세 응답 형식이 예상과 다릅니다: {code}")
            if not page_payload:
                break
            payload.extend(page_payload)
    rows: list[dict] = []
    seen_dates: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            continue
        close_price = parse_float_or_none(item.get("closePrice"))
        open_price = parse_float_or_none(item.get("openPrice"))
        high_price = parse_float_or_none(item.get("highPrice"))
        low_price = parse_float_or_none(item.get("lowPrice"))
        volume = parse_float_or_none(item.get("accumulatedTradingVolume"))
        traded_at = str(item.get("localTradedAt") or "").strip()
        traded_date = traded_at[:10]
        if close_price is None or not traded_date or traded_date in seen_dates:
            continue
        seen_dates.add(traded_date)
        rows.append(
            {
                "date": traded_date,
                "open": open_price or close_price,
                "high": high_price or close_price,
                "low": low_price or close_price,
                "close": close_price,
                "volume": volume or 0.0,
            }
        )
    rows = sorted(rows, key=lambda item: item["date"])
    if len(rows) < 35:
        raise HTTPException(status_code=502, detail=f"차트 분석에 필요한 가격 데이터가 부족합니다: {len(rows)}일")
    return basic, rows


def latest_non_null(values: list[float | None]) -> float | None:
    for value in reversed(values):
        if value is not None:
            return value
    return None


def simple_moving_average(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < period:
            result.append(None)
            continue
        window = values[index + 1 - period : index + 1]
        result.append(sum(window) / period)
    return result


def rolling_std(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = []
    for index in range(len(values)):
        if index + 1 < period:
            result.append(None)
            continue
        window = values[index + 1 - period : index + 1]
        average = sum(window) / period
        variance = sum((value - average) ** 2 for value in window) / period
        result.append(variance ** 0.5)
    return result


def exponential_moving_average(values: list[float], period: int) -> list[float | None]:
    result: list[float | None] = []
    multiplier = 2 / (period + 1)
    ema: float | None = None
    for index, value in enumerate(values):
        if index + 1 < period:
            result.append(None)
            continue
        if ema is None:
            ema = sum(values[index + 1 - period : index + 1]) / period
        else:
            ema = (value - ema) * multiplier + ema
        result.append(ema)
    return result


def calculate_rsi(values: list[float], period: int = 14) -> list[float | None]:
    gains: list[float] = []
    losses: list[float] = []
    result: list[float | None] = [None]
    average_gain: float | None = None
    average_loss: float | None = None
    for index in range(1, len(values)):
        change = values[index] - values[index - 1]
        gain = max(change, 0)
        loss = max(-change, 0)
        gains.append(gain)
        losses.append(loss)
        if index < period:
            result.append(None)
            continue
        if average_gain is None or average_loss is None:
            average_gain = sum(gains[-period:]) / period
            average_loss = sum(losses[-period:]) / period
        else:
            average_gain = (average_gain * (period - 1) + gain) / period
            average_loss = (average_loss * (period - 1) + loss) / period
        if average_loss == 0:
            result.append(100.0)
        else:
            rs = average_gain / average_loss
            result.append(100 - (100 / (1 + rs)))
    return result


def calculate_dmi(rows: list[dict], period: int = 14) -> dict[str, list[float | None]]:
    tr_values: list[float] = []
    plus_dm_values: list[float] = []
    minus_dm_values: list[float] = []
    plus_di: list[float | None] = [None]
    minus_di: list[float | None] = [None]
    dx_values: list[float] = []
    adx: list[float | None] = [None]
    for index in range(1, len(rows)):
        high = float(rows[index]["high"])
        low = float(rows[index]["low"])
        prev_high = float(rows[index - 1]["high"])
        prev_low = float(rows[index - 1]["low"])
        prev_close = float(rows[index - 1]["close"])
        up_move = high - prev_high
        down_move = prev_low - low
        plus_dm = up_move if up_move > down_move and up_move > 0 else 0.0
        minus_dm = down_move if down_move > up_move and down_move > 0 else 0.0
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        plus_dm_values.append(plus_dm)
        minus_dm_values.append(minus_dm)
        tr_values.append(tr)
        if index < period:
            plus_di.append(None)
            minus_di.append(None)
            adx.append(None)
            continue
        tr_sum = sum(tr_values[-period:])
        plus_value = 100 * sum(plus_dm_values[-period:]) / tr_sum if tr_sum else 0.0
        minus_value = 100 * sum(minus_dm_values[-period:]) / tr_sum if tr_sum else 0.0
        plus_di.append(plus_value)
        minus_di.append(minus_value)
        denominator = plus_value + minus_value
        dx = 100 * abs(plus_value - minus_value) / denominator if denominator else 0.0
        dx_values.append(dx)
        if len(dx_values) < period:
            adx.append(None)
        else:
            adx.append(sum(dx_values[-period:]) / period)
    return {"plus_di": plus_di, "minus_di": minus_di, "adx": adx}


def value_trend(values: list[float | None], lookback: int = 5) -> str:
    latest = latest_non_null(values)
    previous_candidates = [value for value in values[:-lookback] if value is not None]
    if latest is None or not previous_candidates:
        return "판단 보류"
    previous = previous_candidates[-1]
    if latest > previous:
        return "상승"
    if latest < previous:
        return "하락"
    return "횡보"


def build_naver_chart_analysis(ticker: str, settings: Settings, save_result: bool = True) -> dict:
    code = normalize_kr_stock_code(ticker)
    if not is_naver_domestic_stock_code(code):
        code = ensure_verified_ticker(ticker, settings)
    basic, rows = fetch_naver_domestic_price_history(code, settings)
    closes = [float(item["close"]) for item in rows]
    highs = [float(item["high"]) for item in rows]
    lows = [float(item["low"]) for item in rows]
    volumes = [float(item["volume"]) for item in rows]

    ma5 = simple_moving_average(closes, 5)
    ma20 = simple_moving_average(closes, 20)
    ma60 = simple_moving_average(closes, 60)
    volume_ma20 = simple_moving_average(volumes, 20)
    std20 = rolling_std(closes, 20)
    upper_band = [
        mean + std * 2 if mean is not None and std is not None else None
        for mean, std in zip(ma20, std20)
    ]
    lower_band = [
        mean - std * 2 if mean is not None and std is not None else None
        for mean, std in zip(ma20, std20)
    ]
    ema12 = exponential_moving_average(closes, 12)
    ema26 = exponential_moving_average(closes, 26)
    macd_line = [
        fast - slow if fast is not None and slow is not None else None
        for fast, slow in zip(ema12, ema26)
    ]
    macd_seed = [value if value is not None else 0.0 for value in macd_line]
    macd_signal = exponential_moving_average(macd_seed, 9)
    macd_histogram = [
        line - signal if line is not None and signal is not None else None
        for line, signal in zip(macd_line, macd_signal)
    ]
    rsi14 = calculate_rsi(closes, 14)
    dmi = calculate_dmi(rows, 14)

    latest = rows[-1]
    latest_close = closes[-1]
    latest_volume = volumes[-1]
    latest_ma5 = latest_non_null(ma5)
    latest_ma20 = latest_non_null(ma20)
    latest_ma60 = latest_non_null(ma60)
    latest_volume_ma20 = latest_non_null(volume_ma20)
    latest_upper = latest_non_null(upper_band)
    latest_lower = latest_non_null(lower_band)
    latest_macd = latest_non_null(macd_line)
    latest_macd_signal = latest_non_null(macd_signal)
    latest_macd_hist = latest_non_null(macd_histogram)
    latest_rsi = latest_non_null(rsi14)
    latest_plus_di = latest_non_null(dmi["plus_di"])
    latest_minus_di = latest_non_null(dmi["minus_di"])
    latest_adx = latest_non_null(dmi["adx"])

    volume_ratio = latest_volume / latest_volume_ma20 if latest_volume_ma20 else None
    band_position = (
        (latest_close - latest_lower) / (latest_upper - latest_lower)
        if latest_upper and latest_lower and latest_upper != latest_lower
        else None
    )
    recent_support = min(lows[-20:])
    recent_resistance = max(highs[-20:])

    trend_score = 0
    signals: list[str] = []
    cautions: list[str] = []
    if latest_ma20 and latest_close > latest_ma20:
        trend_score += 1
        signals.append("종가가 20일 이동평균 위에 있어 단기 추세는 우호적입니다.")
    else:
        cautions.append("종가가 20일 이동평균 아래이거나 20일선 확인이 부족합니다.")
    if latest_ma60 and latest_close > latest_ma60:
        trend_score += 1
        signals.append("종가가 60일 이동평균 위에 있어 중기 추세도 유지되고 있습니다.")
    if latest_macd is not None and latest_macd_signal is not None:
        if latest_macd > latest_macd_signal:
            trend_score += 1
            signals.append("MACD가 시그널선 위에 있어 추세 모멘텀이 살아 있습니다.")
        else:
            cautions.append("MACD가 시그널선 아래라 추세 전환 확인이 더 필요합니다.")
    if latest_plus_di is not None and latest_minus_di is not None:
        if latest_plus_di > latest_minus_di:
            trend_score += 1
            signals.append("DMI상 +DI가 -DI보다 높아 상승 방향성이 우세합니다.")
        else:
            cautions.append("DMI상 -DI가 우세해 하락 압력이 남아 있습니다.")
    if latest_rsi is not None:
        if latest_rsi >= 70:
            cautions.append("RSI 14가 과매수권에 가까워 추격 매수는 신중해야 합니다.")
        elif latest_rsi <= 30:
            cautions.append("RSI 14가 과매도권에 가까워 반등 가능성과 추가 하락 리스크를 함께 봐야 합니다.")
        else:
            signals.append("RSI 14는 극단 구간이 아니라 가격 확인 여지가 있습니다.")
    if band_position is not None:
        if band_position >= 0.85:
            cautions.append("가격이 볼린저 밴드 상단권에 있어 단기 과열 또는 돌파 확인 구간입니다.")
        elif band_position <= 0.15:
            cautions.append("가격이 볼린저 밴드 하단권에 있어 단기 과매도 또는 추세 훼손 구간입니다.")
        else:
            signals.append("볼린저 밴드 기준으로는 극단 과열/과매도 구간은 아닙니다.")
    if volume_ratio is not None:
        if volume_ratio >= 1.5:
            signals.append("거래량이 20일 평균 대비 크게 증가해 가격 움직임의 신뢰도가 높아졌습니다.")
        elif volume_ratio < 0.7:
            cautions.append("거래량이 20일 평균보다 낮아 움직임의 확신은 약합니다.")

    if trend_score >= 4 and latest_rsi is not None and latest_rsi < 75:
        overall_signal = "상승 추세 우위"
        trade_bias = "눌림 매수 또는 돌파 후 지지 확인 전략이 유리합니다."
    elif trend_score <= 1:
        overall_signal = "방어적 관찰"
        trade_bias = "반등 확인 전 신규 진입보다 손절 기준과 지지선 확인을 우선하세요."
    else:
        overall_signal = "중립/확인 필요"
        trade_bias = "지지선 근처 분할 진입과 저항선 돌파 확인을 병행하세요."

    latest_indicators = {
        "date": latest["date"],
        "close": round(latest_close, 4),
        "volume": round(latest_volume, 4),
        "volume_ma20": round(latest_volume_ma20, 4) if latest_volume_ma20 is not None else None,
        "volume_ratio_to_ma20": round(volume_ratio, 3) if volume_ratio is not None else None,
        "ma5": round(latest_ma5, 4) if latest_ma5 is not None else None,
        "ma20": round(latest_ma20, 4) if latest_ma20 is not None else None,
        "ma60": round(latest_ma60, 4) if latest_ma60 is not None else None,
        "ma20_trend": value_trend(ma20),
        "bollinger_upper": round(latest_upper, 4) if latest_upper is not None else None,
        "bollinger_middle": round(latest_ma20, 4) if latest_ma20 is not None else None,
        "bollinger_lower": round(latest_lower, 4) if latest_lower is not None else None,
        "bollinger_position": round(band_position, 3) if band_position is not None else None,
        "macd": round(latest_macd, 4) if latest_macd is not None else None,
        "macd_signal": round(latest_macd_signal, 4) if latest_macd_signal is not None else None,
        "macd_histogram": round(latest_macd_hist, 4) if latest_macd_hist is not None else None,
        "rsi14": round(latest_rsi, 2) if latest_rsi is not None else None,
        "plus_di14": round(latest_plus_di, 2) if latest_plus_di is not None else None,
        "minus_di14": round(latest_minus_di, 2) if latest_minus_di is not None else None,
        "adx14": round(latest_adx, 2) if latest_adx is not None else None,
    }
    analysis = {
        "status": "success",
        "module": "naver_chart_analysis",
        "ticker": code,
        "company_name": basic.get("stockName") or code,
        "exchange": basic.get("stockExchangeName") or "KRX",
        "source": "naver_finance_mobile_price_api",
        "source_url": f"{settings.naver_finance_base_url.rstrip('/')}/api/stock/{code}/price?pageSize=60&page=1",
        "chart_page_url": f"https://stock.naver.com/domestic/stock/{code}/price",
        "as_of": latest["date"],
        "data_points": len(rows),
        "required_indicators": ["거래량", "볼린저 밴드", "이동평균선", "MACD", "RSI 14", "DMI"],
        "latest_indicators": latest_indicators,
        "support_resistance": {
            "recent_20d_support": round(recent_support, 4),
            "recent_20d_resistance": round(recent_resistance, 4),
        },
        "overall_signal": overall_signal,
        "trade_bias": trade_bias,
        "signals": signals[:8],
        "cautions": cautions[:8],
        "next_actions": [
            "매매전략 탭에서 현재가와 함께 차트 분석 결과를 시장 구조 입력에 반영하세요.",
            "볼린저 상단 돌파는 거래량 동반 여부를 확인하고, 상단 근처 추격 매수는 RSI와 MACD를 함께 보세요.",
            "20일선 또는 최근 20일 지지선을 이탈하면 기존 매수 논거와 손절 기준을 다시 점검하세요.",
        ],
        "recent_prices": rows[-30:],
        "saved_to_research_memory": save_result,
    }
    if save_result:
        vault_dir = resolve_vault_dir(settings.research_vault_dir)
        storage_date = current_storage_date()
        storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=code,
            report_type="chart-analysis",
            markdown=render_naver_chart_analysis_markdown(analysis, storage_date),
            structured_payload=analysis,
            manifest_entry=manifest_with_ticker_verification(code, {
                "summary": f"{code} 차트 분석: {overall_signal}, {trade_bias}",
                "company_name": analysis["company_name"],
                "as_of": analysis["as_of"],
                "overall_signal": overall_signal,
                "latest_indicators": latest_indicators,
                "support_resistance": analysis["support_resistance"],
            }),
            report_date=storage_date,
        )
        analysis["storage"] = storage.model_dump(mode="json")
    return analysis


def render_naver_chart_analysis_markdown(analysis: dict, storage_date: date) -> str:
    indicators = analysis.get("latest_indicators") or {}
    support = analysis.get("support_resistance") or {}

    def money(value: object) -> str:
        parsed = parse_float_or_none(value)
        return f"{parsed:,.0f}원" if parsed is not None else "미확인"

    return "\n".join(
        [
            f"# {analysis.get('company_name')}({analysis.get('ticker')}) 네이버 차트 분석",
            "",
            f"- 저장일: {storage_date.isoformat()}",
            f"- 기준일: {analysis.get('as_of')}",
            f"- 데이터 수: {analysis.get('data_points')}개 일봉",
            f"- 출처: {analysis.get('chart_page_url')}",
            "",
            "## 종합 판단",
            f"- 상태: {analysis.get('overall_signal')}",
            f"- 매매 관점: {analysis.get('trade_bias')}",
            f"- 최근 20일 지지선: {money(support.get('recent_20d_support'))}",
            f"- 최근 20일 저항선: {money(support.get('recent_20d_resistance'))}",
            "",
            "## 6개 핵심 보조지표",
            f"- 거래량: {indicators.get('volume'):,.0f}주 / 20일 평균 대비 {indicators.get('volume_ratio_to_ma20') or '미확인'}배",
            f"- 볼린저 밴드: 하단 {money(indicators.get('bollinger_lower'))}, 중심 {money(indicators.get('bollinger_middle'))}, 상단 {money(indicators.get('bollinger_upper'))}",
            f"- 이동평균선: 5일 {money(indicators.get('ma5'))}, 20일 {money(indicators.get('ma20'))}, 60일 {money(indicators.get('ma60'))}, 20일선 방향 {indicators.get('ma20_trend')}",
            f"- MACD: {indicators.get('macd')} / 시그널 {indicators.get('macd_signal')} / 히스토그램 {indicators.get('macd_histogram')}",
            f"- RSI 14: {indicators.get('rsi14')}",
            f"- DMI 14: +DI {indicators.get('plus_di14')} / -DI {indicators.get('minus_di14')} / ADX {indicators.get('adx14')}",
            "",
            "## 긍정 신호",
            *[f"- {item}" for item in analysis.get("signals", [])],
            "",
            "## 주의 신호",
            *[f"- {item}" for item in analysis.get("cautions", [])],
            "",
            "## 다음 행동",
            *[f"- {item}" for item in analysis.get("next_actions", [])],
        ]
    )


def _safe_display_error(error: Exception) -> str:
    text = str(error).strip()
    if len(text) > 180:
        text = text[:177] + "..."
    return text or error.__class__.__name__


def keyword_hits(text: str, keywords: list[str]) -> int:
    upper_text = text.upper()
    return sum(upper_text.count(keyword.upper()) for keyword in keywords)


def clean_market_summary_text(raw_summary: str) -> str:
    cleaned_lines: list[str] = []
    for chunk in (raw_summary or "").replace("\r\n", "\n").split("\n"):
        line = chunk.strip()
        if not line:
            continue
        line = sub(r"([\(（\s])\+([0-9]+(?:\.[0-9]+)?)\s*%", r"\1상승 \2퍼센트", line)
        line = sub(r"([\(（\s])-([0-9]+(?:\.[0-9]+)?)\s*%", r"\1하락 \2퍼센트", line)
        line = sub(r"(?<=\d),(?=\d)", "", line)
        line = sub(r"^[\s\-*•●○■□▪▫◆◇▶▷►▸]+", "", line)
        line = sub(r"[\[\]\(\)（）{}<>〈〉《》■□●○◆◇▶▷►▸▪▫•※*#_`~|^=]+", " ", line)
        line = sub(r"[▲▼△▽↑↓→←↗↘+%]", " ", line)
        line = sub(r"[^0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ\s.,:;!?/·-]", " ", line)
        line = sub(r"[,;:/·]", " ", line)
        line = sub(r"\s+", " ", line).strip(" .!?-")
        if line:
            cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def infer_market_close_sentiment(raw_summary: str) -> tuple[str, str, str]:
    positive = keyword_hits(
        raw_summary,
        [
            "상승",
            "강세",
            "반등",
            "랠리",
            "돌파",
            "위험 선호",
            "매수",
            "완화",
            "실적 호조",
            "상회",
            "rally",
            "rebound",
            "risk-on",
            "beat",
        ],
    )
    negative = keyword_hits(
        raw_summary,
        [
            "하락",
            "약세",
            "급락",
            "매도",
            "조정",
            "위험 회피",
            "금리 상승",
            "인플레이션",
            "부진",
            "하회",
            "selloff",
            "risk-off",
            "miss",
        ],
    )
    risk_hits = keyword_hits(
        raw_summary,
        [
            "변동성",
            "vix",
            "금리 상승",
            "달러 강세",
            "유가 상승",
            "신용",
            "침체",
            "지정학",
            "관세",
            "급락",
            "risk-off",
        ],
    )
    if positive > negative + 1:
        sentiment = "긍정"
    elif negative > positive + 1:
        sentiment = "부정"
    else:
        sentiment = "혼합"

    if risk_hits >= 4 or negative >= positive + 3:
        risk_level = "높음"
    elif risk_hits >= 2 or sentiment == "혼합":
        risk_level = "보통"
    else:
        risk_level = "낮음"

    if sentiment == "긍정" and risk_level != "높음":
        regime = "위험 선호"
    elif sentiment == "부정" and risk_level == "높음":
        regime = "위험 회피"
    elif keyword_hits(raw_summary, ["순환매", "rotation", "섹터 로테이션"]):
        regime = "섹터 순환"
    else:
        regime = "방향성 확인 필요"
    return sentiment, risk_level, regime


def infer_market_tags(raw_summary: str) -> list[str]:
    tag_keywords = {
        "AI": ["AI", "인공지능", "데이터센터", "GPU"],
        "반도체": ["반도체", "semiconductor", "chip"],
        "금리": ["금리", "국채", "yield", "treasury"],
        "환율": ["환율", "달러", "원화", "엔화", "FX"],
        "에너지": ["유가", "원유", "가스", "energy", "oil"],
        "금융": ["은행", "금융", "credit", "bank"],
        "헬스케어": ["헬스케어", "바이오", "제약", "healthcare"],
        "중국": ["중국", "china"],
        "한국 수출": ["수출", "반도체 수출", "무역수지"],
        "정책": ["연준", "FOMC", "한국은행", "BOJ", "정책", "관세"],
    }
    tags = [
        tag
        for tag, keywords in tag_keywords.items()
        if keyword_hits(raw_summary, keywords)
    ]
    return tags or ["시장 전반"]


def summarize_market_lines(raw_summary: str, limit: int = 5) -> list[str]:
    raw_summary = clean_market_summary_text(raw_summary)
    lines = []
    for chunk in raw_summary.replace("\r\n", "\n").split("\n"):
        normalized = chunk.strip(" -•\t")
        if normalized:
            lines.append(normalized)
    if len(lines) < 3:
        lines = [
            item.strip()
            for item in sub(r"([.!?。])", r"\1\n", raw_summary).split("\n")
            if item.strip()
        ]
    return lines[:limit] or ["입력 요약에서 핵심 문장을 추출하지 못했습니다."]


def build_sector_implications(raw_summary: str, tags: list[str]) -> list[str]:
    implications = []
    if "AI" in tags or "반도체" in tags:
        implications.append("AI/반도체 노출은 수요 지속성과 밸류에이션 부담을 함께 점검하세요.")
    if "금리" in tags:
        implications.append("금리 민감 성장주와 금융/방어 섹터의 상대 강도를 비교하세요.")
    if "에너지" in tags:
        implications.append("유가 변동은 에너지·항공·운송·소비재 마진에 반대 방향으로 작용할 수 있습니다.")
    if "환율" in tags:
        implications.append("환율 변화가 수출주, 해외 매출 비중 높은 종목, 원화 자산에 미치는 영향을 점검하세요.")
    if "정책" in tags:
        implications.append("중앙은행·규제·관세 뉴스는 단기 멀티플과 섹터 로테이션을 흔들 수 있습니다.")
    return implications or ["특정 섹터보다 지수 방향성, 시장 폭, 주도주 지속 여부를 우선 확인하세요."]


def market_tag_aliases(tags: list[str]) -> list[str]:
    aliases = {
        "AI": ["AI", "GPU", "데이터센터", "DATACENTER", "DATA CENTER", "TECHNOLOGY", "CLOUD"],
        "반도체": ["반도체", "SEMICONDUCTOR", "CHIP", "GPU", "TECHNOLOGY"],
        "금리": ["금리", "국채", "YIELD", "TREASURY", "BANK", "FINANCIAL"],
        "환율": ["환율", "달러", "FX", "USD", "EXPORT", "수출"],
        "에너지": ["에너지", "ENERGY", "OIL", "GAS", "운송", "항공"],
        "금융": ["금융", "BANK", "FINANCIAL", "CREDIT"],
        "헬스케어": ["헬스케어", "HEALTHCARE", "BIO", "제약"],
        "중국": ["중국", "CHINA", "수출"],
        "한국 수출": ["한국 수출", "수출", "반도체", "EXPORT", "KOREA"],
        "정책": ["정책", "FOMC", "연준", "규제", "관세", "POLICY"],
    }
    terms = set(tags)
    for tag in tags:
        terms.update(aliases.get(tag, []))
    return [term for term in terms if term]


def text_matches_market_tags(value: str, tag_terms: list[str]) -> bool:
    normalized = value.strip().upper()
    if not normalized:
        return False
    for term in tag_terms:
        tag = term.strip().upper()
        if tag and (tag in normalized or normalized in tag):
            return True
    return False


def append_unique(items: list[str], value: str, limit: int = 8) -> None:
    if value and value not in items and len(items) < limit:
        items.append(value)


def build_auto_market_utilization_focus(
    *,
    market: str,
    tags: list[str],
    sentiment: str,
    risk_level: str,
    regime: str,
    settings: Settings,
) -> list[str]:
    focus: list[str] = []
    tag_terms = market_tag_aliases(tags)
    tag_label = ", ".join(tags) or "시장 전반"

    portfolio_store = read_portfolio_store(settings)
    portfolios = [
        SavedPortfolio.model_validate(item)
        for item in portfolio_store.get("portfolios", {}).values()
        if isinstance(item, dict)
    ]
    if portfolios:
        portfolio_names = ", ".join(item.portfolio_name for item in portfolios[:3])
        append_unique(
            focus,
            f"저장 포트폴리오({portfolio_names})의 보유 종목·섹터 노출을 오늘 시장 태그({tag_label})와 자동 대조합니다.",
        )
        matched_exposures: list[str] = []
        for portfolio in portfolios:
            for holding in portfolio.holdings:
                candidates = [
                    holding.ticker,
                    holding.name or "",
                    holding.sector,
                    *holding.theme_tags,
                ]
                if any(text_matches_market_tags(item, tag_terms) for item in candidates):
                    exposure = f"{portfolio.portfolio_name}:{holding.ticker}"
                    if holding.sector and holding.sector != "Unknown":
                        exposure += f"({holding.sector})"
                    append_unique(matched_exposures, exposure, limit=6)
        if matched_exposures:
            append_unique(
                focus,
                "오늘 시장 태그와 겹치는 보유 노출: "
                + ", ".join(matched_exposures)
                + "를 우선 점검합니다.",
            )
        else:
            append_unique(
                focus,
                "직접 겹치는 보유 노출이 없으면 지수·금리·환율 변화가 전체 포트폴리오 베타에 미치는 영향을 우선 확인합니다.",
            )
    else:
        append_unique(
            focus,
            "저장 포트폴리오가 없으므로 장세 판정과 리스크 레벨을 기본 리스크 예산 가이드로 활용합니다.",
        )

    interest_store = read_interest_list(settings)
    interest_tickers = [
        InterestTicker.model_validate(item)
        for item in interest_store.get("tickers", [])
        if isinstance(item, dict)
    ]
    interest_sectors = [
        InterestSector.model_validate(item)
        for item in interest_store.get("sectors", [])
        if isinstance(item, dict)
    ]
    matched_sectors = [
        item.name
        for item in interest_sectors
        if text_matches_market_tags(item.name, tag_terms)
        or any(text_matches_market_tags(tag, tag_terms) for tag in item.tags)
    ]
    matched_tickers = [
        item.ticker
        for item in interest_tickers
        if any(text_matches_market_tags(tag, tag_terms) for tag in item.tags)
        or text_matches_market_tags(item.thesis or "", tag_terms)
        or text_matches_market_tags(item.notes or "", tag_terms)
    ]
    if matched_sectors:
        append_unique(
            focus,
            "관심 섹터 중 오늘 시장 태그와 연결된 영역: "
            + ", ".join(matched_sectors[:5])
            + "를 다음 후보 발굴에 반영합니다.",
        )
    elif interest_sectors:
        append_unique(
            focus,
            "관심 섹터 목록은 유지하되 오늘 태그와 직접 겹치는 섹터가 적어 상대 강도 변화만 관찰합니다.",
        )

    if matched_tickers:
        append_unique(
            focus,
            "관심 종목 중 오늘 이슈와 연결된 종목: "
            + ", ".join(matched_tickers[:8])
            + "의 논거 변화와 다음 장 가격 반응을 우선 확인합니다.",
        )
    elif interest_tickers:
        append_unique(
            focus,
            "관심 종목은 가격보다 오늘 장세가 기존 투자 논거를 강화/약화했는지부터 업데이트합니다.",
        )

    if risk_level == "높음":
        append_unique(
            focus,
            "리스크 레벨이 높아 다음 장 신규 진입보다 기존 노출 축소·손절 기준·현금 비중 점검에 우선순위를 둡니다.",
        )
    elif sentiment == "긍정" and regime == "위험 선호":
        append_unique(
            focus,
            "위험 선호 장세로 분류되어 관심 섹터와 주도주 확산 여부를 다음 매매 후보 필터로 사용합니다.",
        )
    else:
        append_unique(
            focus,
            "방향성이 완전히 확정되지 않았으므로 누적 시장일지의 반복 태그와 다음 장 확인 지표를 함께 비교합니다.",
        )

    if market == "KR":
        append_unique(focus, "한국 시장 기록은 외국인/기관 수급, 원달러 환율, 반도체 대형주 상대 강도를 자동 추적합니다.")
    elif market == "US":
        append_unique(focus, "미국 시장 기록은 10년물 금리, 달러, 나스닥/러셀2000 상대 강도와 연결해 누적합니다.")
    else:
        append_unique(focus, "글로벌 시장 기록은 지역 간 자금 이동과 달러/금리/원자재 변화의 공통 신호로 누적합니다.")
    return focus[:8]


def build_market_interest_implications(
    *,
    raw_summary: str,
    tags: list[str],
    settings: Settings,
) -> list[str]:
    interest_store = read_interest_list(settings)
    interest_tickers = [
        InterestTicker.model_validate(item)
        for item in interest_store.get("tickers", [])
        if isinstance(item, dict)
    ]
    interest_sectors = [
        InterestSector.model_validate(item)
        for item in interest_store.get("sectors", [])
        if isinstance(item, dict)
    ]
    implications: list[str] = []
    tag_terms = market_tag_aliases(tags)
    summary_text = raw_summary.upper()

    for item in interest_tickers[:20]:
        profile_name = ""
        if item.verification and item.verification.company_name:
            profile_name = item.verification.company_name
        candidates = [item.ticker, profile_name, item.thesis or "", item.notes or "", *item.tags]
        direct_match = any(
            candidate and (
                candidate.upper() in summary_text
                or text_matches_market_tags(candidate, tag_terms)
            )
            for candidate in candidates
        )
        if direct_match:
            implications.append(
                f"관심종목 {item.ticker}: 오늘 시장 태그({', '.join(tags)})와 연결됩니다. 다음 장 가격 반응보다 기존 매수 후보 논거가 강화/약화됐는지 먼저 업데이트하세요."
            )

    for item in interest_sectors[:20]:
        candidates = [item.name, item.thesis or "", item.notes or "", *item.tags]
        direct_match = any(
            candidate and (
                candidate.upper() in summary_text
                or text_matches_market_tags(candidate, tag_terms)
            )
            for candidate in candidates
        )
        if direct_match:
            implications.append(
                f"관심섹터 {item.name}: 오늘 시장 태그({', '.join(tags)})와 겹칩니다. 섹터 발굴 후보와 관련 종목의 상대 강도를 다음 관찰 목록에 올리세요."
            )

    if not implications and (interest_tickers or interest_sectors):
        implications.append(
            "현재 관심목록과 오늘 시장 태그의 직접 연결은 약합니다. 관심종목은 개별 촉매가 확인될 때까지 관찰 상태로 유지하세요."
        )
    if not implications:
        implications.append(
            "저장된 관심종목/관심섹터가 없어 시장일지의 관심목록 영향 분석을 건너뜁니다."
        )
    return implications[:10]


def build_market_portfolio_actions(sentiment: str, risk_level: str, regime: str) -> list[str]:
    if risk_level == "높음":
        return [
            "신규 매수는 분할 접근하고 손절/무효화 조건을 먼저 확정하세요.",
            "고집중 포지션과 고베타 성장주 비중이 의도한 리스크 예산 안에 있는지 확인하세요.",
            "다음 장 시작 전 시장 폭, 금리, 환율이 악화되는지 재확인하세요.",
        ]
    if sentiment == "긍정":
        return [
            "주도 섹터가 넓어지는지 확인하면서 기존 강한 논거 종목의 추가 진입 후보를 선별하세요.",
            "급등 추격보다 전일 저항 돌파 후 지지 확인 구간을 우선 관찰하세요.",
        ]
    if regime == "섹터 순환":
        return [
            "기존 주도주와 새로 강해지는 섹터의 상대 강도를 비교해 일부 리밸런싱 후보를 정리하세요.",
            "순환매가 단기 기술적 반등인지 실적/수급 변화인지 분리해서 판단하세요.",
        ]
    return [
        "확신이 낮은 장에서는 현금 비중과 관찰 목록을 유지하고, 다음 촉매 확인 후 행동하세요.",
        "관심 종목은 가격보다 논거 변화와 데이터 확인 여부를 먼저 업데이트하세요.",
    ]


def build_market_next_watch(tags: list[str], market: str) -> list[str]:
    items = ["시장 폭: 상승/하락 종목 수와 주도주 확산 여부"]
    if market == "US":
        items.extend(["미국 10년물 금리와 달러 지수", "나스닥/러셀2000 상대 강도"])
    if market == "KR":
        items.extend(["외국인/기관 수급과 원달러 환율", "코스피 대형주와 코스닥 성장주의 상대 강도"])
    if "AI" in tags or "반도체" in tags:
        items.append("AI/반도체 주도주의 거래대금과 실적 기대 변화")
    if "에너지" in tags:
        items.append("유가와 에너지/운송/소비재 마진 민감도")
    if "정책" in tags:
        items.append("중앙은행 발언, 정책 일정, 규제/관세 뉴스")
    return items


def cumulative_market_patterns(entries: list[MarketCloseEntry], market: str) -> tuple[list[str], str]:
    recent = [entry for entry in entries if entry.market == market][-20:]
    if not recent:
        return ["누적 기록이 아직 부족합니다. 오늘 기록을 기준점으로 저장했습니다."], "첫 기록 또는 초기 축적 단계입니다."

    sentiment_counts = {
        name: sum(1 for entry in recent if entry.sentiment == name)
        for name in ["긍정", "혼합", "부정"]
    }
    risk_counts = {
        name: sum(1 for entry in recent if entry.risk_level == name)
        for name in ["낮음", "보통", "높음"]
    }
    tag_counts: dict[str, int] = {}
    for entry in recent:
        for tag in entry.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda item: item[1], reverse=True)[:5]
    patterns = [
        f"최근 {len(recent)}개 {market} 폐장 기록 기준: 긍정 {sentiment_counts['긍정']}회, 혼합 {sentiment_counts['혼합']}회, 부정 {sentiment_counts['부정']}회입니다.",
        f"리스크 레벨은 낮음 {risk_counts['낮음']}회, 보통 {risk_counts['보통']}회, 높음 {risk_counts['높음']}회로 누적되었습니다.",
    ]
    if top_tags:
        patterns.append(
            "반복 출현 테마: "
            + ", ".join(f"{tag} {count}회" for tag, count in top_tags)
        )
    if risk_counts["높음"] >= 3:
        patterns.append("고위험 장세 기록이 반복되고 있어 신규 포지션은 더 작은 단위로 검증하는 편이 좋습니다.")
    if sentiment_counts["긍정"] >= max(3, sentiment_counts["부정"] + 2):
        patterns.append("긍정 기록이 우세합니다. 다만 과열 신호와 주도주 쏠림을 함께 추적하세요.")
    summary = (
        f"{market} 최근 {len(recent)}회 누적: "
        f"주요 테마 {', '.join(tag for tag, _ in top_tags[:3]) or '미확정'}, "
        f"우세 심리 {max(sentiment_counts, key=sentiment_counts.get)}"
    )
    return patterns, summary


def build_market_close_entry(
    request: MarketCloseReviewRequest,
    settings: Settings,
    attachment_info: dict | None = None,
) -> tuple[MarketCloseEntry, list[MarketCloseEntry], list[str], str]:
    market = normalize_market_code(request.market)
    session_date = request.session_date or current_storage_date().isoformat()
    raw_summary = clean_market_summary_text(request.raw_summary)
    sentiment, risk_level, regime = infer_market_close_sentiment(raw_summary)
    tags = infer_market_tags(raw_summary)
    market_index_snapshot = (
        fetch_naver_korea_index_snapshot(settings) if market == "KR" else []
    )
    key_drivers = summarize_market_lines(raw_summary)
    sector_implications = build_sector_implications(raw_summary, tags)
    auto_utilization_focus = build_auto_market_utilization_focus(
        market=market,
        tags=tags,
        sentiment=sentiment,
        risk_level=risk_level,
        regime=regime,
        settings=settings,
    )
    interest_implications = build_market_interest_implications(
        raw_summary=raw_summary,
        tags=tags,
        settings=settings,
    )
    portfolio_actions = build_market_portfolio_actions(sentiment, risk_level, regime)
    next_session_watch = build_market_next_watch(tags, market)
    now = current_storage_timestamp()
    entry_id = f"{market}-{session_date}"
    entry = MarketCloseEntry(
        entry_id=entry_id,
        market=market,
        session_date=session_date,
        raw_summary=raw_summary,
        sentiment=sentiment,
        risk_level=risk_level,
        regime=regime,
        auto_utilization_focus=auto_utilization_focus,
        interest_implications=interest_implications,
        market_index_snapshot=market_index_snapshot,
        key_drivers=key_drivers,
        sector_implications=sector_implications,
        portfolio_actions=portfolio_actions,
        next_session_watch=next_session_watch,
        tags=tags,
        attachment=attachment_info,
        created_at=now,
        updated_at=now,
    )
    store = read_market_close_journal(settings)
    existing_entries = [
        hydrate_market_close_auto_focus(MarketCloseEntry.model_validate(item), settings)
        for item in store.get("entries", [])
        if isinstance(item, dict)
    ]
    prior_without_same_id = [
        item for item in existing_entries if item.entry_id != entry_id
    ]
    patterns, regime_summary = cumulative_market_patterns(prior_without_same_id + [entry], market)
    return entry, prior_without_same_id, patterns, regime_summary


def hydrate_market_close_auto_focus(
    entry: MarketCloseEntry,
    settings: Settings,
) -> MarketCloseEntry:
    updates: dict[str, object] = {}
    cleaned_summary = clean_market_summary_text(entry.raw_summary)
    if cleaned_summary and cleaned_summary != entry.raw_summary:
        updates["raw_summary"] = cleaned_summary
        updates["key_drivers"] = summarize_market_lines(cleaned_summary)
    if not entry.interest_implications:
        updates["interest_implications"] = build_market_interest_implications(
            raw_summary=cleaned_summary or entry.raw_summary,
            tags=entry.tags,
            settings=settings,
        )
    if entry.market == "KR" and not entry.market_index_snapshot:
        updates["market_index_snapshot"] = fetch_naver_korea_index_snapshot(settings)
    if entry.auto_utilization_focus:
        if updates:
            return entry.model_copy(update=updates)
        return entry
    updates["auto_utilization_focus"] = build_auto_market_utilization_focus(
        market=entry.market,
        tags=entry.tags,
        sentiment=entry.sentiment,
        risk_level=entry.risk_level,
        regime=entry.regime,
        settings=settings,
    )
    return entry.model_copy(update=updates)


def render_market_close_markdown(
    response: MarketCloseReviewResponse,
    storage_date: date,
) -> str:
    entry = response.entry
    return f"""---
ticker: {market_research_key(entry.market)}
type: market-close-review
date: {storage_date.isoformat()}
module: market_close_review
market: {entry.market}
session_date: {entry.session_date}
sentiment: {entry.sentiment}
risk_level: {entry.risk_level}
regime: {entry.regime}
tags: {", ".join(entry.tags)}
---

# {entry.market} 폐장 후 시장 리뷰: {entry.session_date}

## 핵심 평가

- 시장 심리: {entry.sentiment}
- 리스크 레벨: {entry.risk_level}
- 장세 판정: {entry.regime}
- 누적 기록 수: {response.history_count}

## 오늘의 핵심 동인

{chr(10).join(f"- {item}" for item in entry.key_drivers)}

## 네이버 증권 보조 지수

{chr(10).join(f"- {item}" for item in entry.market_index_snapshot) if entry.market_index_snapshot else "- 해당 없음"}

## 섹터/테마 시사점

{chr(10).join(f"- {item}" for item in entry.sector_implications)}

## 시스템 자동 활용 초점

{chr(10).join(f"- {item}" for item in entry.auto_utilization_focus)}

## 관심목록 영향

{chr(10).join(f"- {item}" for item in entry.interest_implications)}

## 포트폴리오 활용

{chr(10).join(f"- {item}" for item in entry.portfolio_actions)}

## 누적 패턴

{chr(10).join(f"- {item}" for item in response.cumulative_patterns)}

## 다음 장 체크포인트

{chr(10).join(f"- {item}" for item in entry.next_session_watch)}

## 첨부 파일

{chr(10).join(f"- {key}: {value}" for key, value in (entry.attachment or {}).items() if key != "extracted_text") if entry.attachment else "- 첨부 파일 없음"}

## 정제된 시장 요약

{entry.raw_summary}
"""


def infer_policy_market_regime(market_state: str, settings: Settings) -> tuple[str, list[str]]:
    text = clean_market_summary_text(market_state)
    if text:
        sentiment, risk_level, regime = infer_market_close_sentiment(text)
        tags = infer_market_tags(text)
        return f"{regime} / 심리 {sentiment} / 리스크 {risk_level}", tags

    store = read_market_close_journal(settings)
    entries = [
        MarketCloseEntry.model_validate(item)
        for item in store.get("entries", [])
        if isinstance(item, dict)
    ]
    if not entries:
        return "누적 시장 상태 부족", []
    latest = sorted(entries, key=lambda item: (item.session_date, item.updated_at or ""), reverse=True)[0]
    return (
        f"{latest.market} 최근 시장일지: {latest.regime} / 심리 {latest.sentiment} / 리스크 {latest.risk_level}",
        latest.tags,
    )


def build_policy_state_features(
    holdings: list[PortfolioHolding],
    regime_summary: str,
    tags: list[str],
) -> list[str]:
    sectors = sorted({holding.sector for holding in holdings if holding.sector and holding.sector != "Unknown"})
    themes = sorted({tag for holding in holdings for tag in holding.theme_tags})
    return [
        f"시장 상태: {regime_summary}",
        f"보유 종목 수: {len(holdings)}",
        f"섹터 노출: {', '.join(sectors[:8]) or '미분류'}",
        f"테마 노출: {', '.join(themes[:10]) or '미분류'}",
        f"시장 태그: {', '.join(tags[:8]) or '없음'}",
        "가격/수익률, 시장일지, 실적 반응, 리스크 스캔 결과를 상태 변수로 누적 학습합니다.",
    ]


def policy_adjustment_for_holding(
    holding: PortfolioHolding,
    *,
    max_position_weight: float,
    risk_profile: str,
    market_tags: list[str],
) -> PolicyAllocationAdjustment:
    weight = float(holding.weight or 0)
    suggested = weight
    action = "유지"
    reasons: list[str] = []
    profile = risk_profile.lower()
    theme_hits = len(set(holding.theme_tags) & set(market_tags))

    if weight > max_position_weight:
        suggested = min(suggested, max_position_weight)
        action = "축소 후보"
        reasons.append(f"현재 비중 {weight:.1%}가 단일 종목 한도 {max_position_weight:.1%}를 초과")
    if holding.unrealized_return is not None and holding.unrealized_return < -0.18:
        suggested = min(suggested, max(weight * 0.75, 0))
        action = "리스크 축소"
        reasons.append(f"미실현 수익률 {holding.unrealized_return:.1%}로 손실 확대 구간")
    if holding.unrealized_return is not None and holding.unrealized_return > 0.25 and profile in {"conservative", "보수", "보수적"}:
        suggested = min(suggested, weight * 0.85)
        action = "일부 이익 보호"
        reasons.append("보수적 위험 성향에서 큰 수익 포지션의 이익 보호 필요")
    if theme_hits and weight < max_position_weight * 0.75 and action == "유지":
        suggested = min(max_position_weight, weight * 1.1 if weight else max_position_weight * 0.25)
        action = "관찰 후 증액 후보"
        reasons.append(f"시장 태그와 보유 테마가 {theme_hits}개 겹침")
    if not reasons:
        reasons.append("현재 정책 기준에서 강한 증액/축소 신호 없음")

    return PolicyAllocationAdjustment(
        ticker=holding.ticker,
        current_weight=round(weight, 4),
        suggested_weight=round(max(suggested, 0), 4),
        action=action,
        rationale="; ".join(reasons),
    )


def render_reinforcement_policy_markdown(
    response: ReinforcementPortfolioOptimizationResponse,
    portfolio_value: float,
    report_date: date,
) -> str:
    adjustments = "\n".join(
        f"- {item.ticker}: {item.action} | 현재 {item.current_weight:.1%} -> 제안 {item.suggested_weight:.1%} | {item.rationale}"
        for item in response.allocation_adjustments
    ) or "- 조정 후보 없음"
    return f"""---
portfolio_name: {response.portfolio_name}
type: reinforcement-portfolio-optimizer
date: {report_date.isoformat()}
objective: {response.objective}
risk_profile: {response.risk_profile}
---

# {response.portfolio_name} 강화학습형 포트폴리오 정책 최적화

- 학습 모드: {response.learning_mode}
- 포트폴리오 총액: {portfolio_value:,.0f}
- 목표 함수: {response.objective}

## 상태 변수

{chr(10).join(f"- {item}" for item in response.state_features)}

## 행동 공간

{chr(10).join(f"- {item}" for item in response.action_space)}

## 보상 함수

{chr(10).join(f"- {item}" for item in response.reward_function)}

## 정책 요약

{response.learned_policy_summary}

## 비중 조정 후보

{adjustments}

## 리스크 가드레일

{chr(10).join(f"- {item}" for item in response.risk_guardrails)}

## 다음 학습 데이터

{chr(10).join(f"- {item}" for item in response.next_training_data_needed)}
"""


def run_reinforcement_portfolio_policy(
    request: ReinforcementPortfolioOptimizationRequest,
    settings: Settings,
) -> ReinforcementPortfolioOptimizationResponse:
    holdings, portfolio_value = normalize_portfolio_holdings(request.holdings, None)
    if not holdings:
        store = read_portfolio_store(settings)
        key = portfolio_store_key(request.portfolio_name)
        saved = store.get("portfolios", {}).get(key)
        if saved:
            saved_portfolio = SavedPortfolio.model_validate(saved)
            holdings, portfolio_value = normalize_portfolio_holdings(
                saved_portfolio.holdings,
                saved_portfolio.portfolio_value,
            )

    regime_summary, market_tags = infer_policy_market_regime(request.market_state, settings)
    state_features = build_policy_state_features(holdings, regime_summary, market_tags)
    action_space = [
        "유지: 기존 비중 유지",
        "관찰 후 증액 후보: 시장 상태와 투자 논거가 강화될 때만 분할 증액",
        "축소 후보: 집중도 또는 손실 확대 위험을 줄이기 위한 비중 축소",
        "리밸런싱: 섹터/테마 쏠림을 낮추고 현금 또는 방어 노출 확보",
        "학습 보류: 데이터 신뢰도 또는 시장 신호가 부족하면 행동하지 않음",
    ]
    reward_function = [
        "위험조정수익률 개선: 수익률 상승보다 변동성·낙폭을 함께 반영",
        "최대낙폭 패널티: 손실 확대 포지션과 고집중 포지션에 음의 보상",
        "논거 일치 보상: 시장일지 태그, 실적 반응, 저장 메모가 같은 방향이면 양의 보상",
        "거래 비용 패널티: 잦은 매매와 근거 없는 회전율을 감점",
        "데이터 품질 패널티: 실제 데이터 부족, 레거시 리포트, 낮은 신뢰도 자료를 감점",
    ]
    allocation_adjustments = [
        policy_adjustment_for_holding(
            holding,
            max_position_weight=request.max_position_weight,
            risk_profile=request.risk_profile,
            market_tags=market_tags,
        )
        for holding in holdings
    ]
    allocation_adjustments.sort(
        key=lambda item: (abs(item.current_weight - item.suggested_weight), item.current_weight),
        reverse=True,
    )
    response = ReinforcementPortfolioOptimizationResponse(
        portfolio_name=request.portfolio_name,
        objective=request.objective,
        risk_profile=request.risk_profile,
        learning_mode="offline_policy_scaffold",
        state_features=state_features,
        action_space=action_space,
        reward_function=reward_function,
        learned_policy_summary=(
            "현재는 실거래 자동 강화학습이 아니라, 누적 시장일지·포트폴리오·실적/뉴스 분석을 "
            "상태/행동/보상 구조로 변환하는 오프라인 정책 학습 준비 단계입니다. 데이터가 쌓이면 "
            "실제 에피소드별 보상 학습으로 확장할 수 있습니다."
        ),
        allocation_adjustments=allocation_adjustments[:20],
        risk_guardrails=[
            f"단일 종목 권장 상한: {request.max_position_weight:.0%}",
            "실거래 자동 집행은 하지 않고, 학습 결과는 후보 행동으로만 표시합니다.",
            "정책 업데이트 전 최신 시장일지, 실적 분석, 포트폴리오 리스크 스캔을 함께 확인합니다.",
            "데이터 공급자가 경고를 반환한 종목은 증액 보상을 제한합니다.",
        ],
        next_training_data_needed=[
            "일별 포트폴리오 평가금액과 현금 비중",
            "시장일지의 심리·리스크·태그와 다음 날 수익률",
            "매매 전략 실행 여부와 실제 진입/청산 결과",
            "실적 발표 전후 주가 반응과 논거 변화",
            "정보입력 메모의 신뢰도와 이후 투자 논거 적중 여부",
        ],
        saved_to_research_memory=request.save_result,
    )
    if request.save_result:
        vault_dir = resolve_vault_dir(settings.research_vault_dir)
        report_date = current_storage_date()
        response.storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=portfolio_store_key(request.portfolio_name),
            report_type="reinforcement-portfolio-optimizer",
            markdown=render_reinforcement_policy_markdown(response, portfolio_value, report_date),
            structured_payload=response.model_dump(mode="json"),
            manifest_entry={
                "summary": f"{request.portfolio_name} 포트폴리오 정책 최적화: {len(response.allocation_adjustments)}개 조정 후보",
                "portfolio_name": request.portfolio_name,
                "objective": request.objective,
                "risk_profile": request.risk_profile,
            },
            report_date=report_date,
        )
    return response


def source_type_value(item: InjectedDataPoint) -> str:
    value = item.source_type
    return value.value if hasattr(value, "value") else str(value)


def enum_or_str_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def translate_source_type_label(value: object) -> str:
    labels = {
        "official_filing": "공식 공시",
        "earnings_release": "실적 발표",
        "ir_presentation": "IR 자료",
        "market_price": "시장 가격",
        "financial_data": "재무 데이터",
        "news": "뉴스",
        "analyst_report": "애널리스트 리포트",
        "user_memo": "직접 메모",
        "macro_research": "거시/경제 전망",
        "sector_research": "섹터/산업 전망",
        "market_research": "전체 시황/투자 동향",
        "research_memory": "리서치 메모리",
        "other": "기타",
    }
    raw_value = enum_or_str_value(value)
    return labels.get(raw_value, raw_value)


def translate_data_label(value: str) -> str:
    labels = {
        "linked_workspace_reports": "연결 가능한 저장 리포트",
        "last_price": "최근 가격",
        "average_volume": "평균 거래량",
        "estimated_volatility": "추정 변동성",
        "market_cap": "시가총액",
        "revenue_growth": "매출 성장률",
        "gross_margin": "매출총이익률",
        "operating_margin": "영업이익률",
        "free_cash_flow_margin": "잉여현금흐름 마진",
        "net_debt_to_ebitda": "순부채/EBITDA",
        "pe_ratio": "PER",
        "eps": "주당순이익",
        "revenue": "매출",
        "guidance": "가이던스",
    }
    return labels.get(value, value)


def translate_trade_style_label(value: str) -> str:
    labels = {
        "scalp": "아주 짧게 매매",
        "day": "하루 안에 매매",
        "swing": "단기 보유(며칠~몇 주)",
        "position": "중기 보유(몇 주~몇 달)",
    }
    return labels.get(value, value)


def sector_research_key(region: str, style: str) -> str:
    style_labels = {
        "성장": "GROWTH",
        "growth": "GROWTH",
        "균형형": "BALANCED",
        "balanced": "BALANCED",
        "가치": "VALUE",
        "value": "VALUE",
        "방어": "DEFENSIVE",
        "defensive": "DEFENSIVE",
    }
    region_key = "KR" if region.upper().startswith(("KR", "KOREA", "한국")) else "US"
    style_key = style_labels.get(style.strip(), normalize_ticker(style))
    return f"SECTOR-{region_key}-{style_key}"


def compounder_research_key(region: str, sector: str, style: str) -> str:
    sector_labels = {
        "전체": "ALL",
        "all": "ALL",
        "기술": "TECH",
        "technology": "TECH",
        "헬스케어": "HEALTHCARE",
        "healthcare": "HEALTHCARE",
        "소비재": "CONSUMER",
        "consumer": "CONSUMER",
        "금융": "FINANCIALS",
        "financials": "FINANCIALS",
        "산업재": "INDUSTRIALS",
        "industrials": "INDUSTRIALS",
    }
    style_labels = {
        "퀄리티 성장": "QUALITY-GROWTH",
        "quality growth": "QUALITY-GROWTH",
        "고성장": "HIGH-GROWTH",
        "high growth": "HIGH-GROWTH",
        "방어 성장": "DEFENSIVE-GROWTH",
        "defensive growth": "DEFENSIVE-GROWTH",
    }
    region_key = "KR" if region.upper().startswith(("KR", "KOREA", "한국")) else "US"
    sector_key = sector_labels.get(sector.strip().lower(), sector_labels.get(sector.strip(), normalize_ticker(sector)))
    style_key = style_labels.get(style.strip().lower(), style_labels.get(style.strip(), normalize_ticker(style)))
    return f"COMPOUNDER-{region_key}-{sector_key}-{style_key}"


def build_checklist_statuses(checked_items: list[str]) -> list[ChecklistItemStatus]:
    checked = {item.strip() for item in checked_items}
    return [
        ChecklistItemStatus(key=key, label=label, completed=key in checked)
        for key, label in RESEARCH_CHECKLIST_ITEMS
    ]


def collect_workspace_context(
    ticker: str,
    vault_dir: Path,
    provided_data: list[InjectedDataPoint],
) -> list[InjectedDataPoint]:
    ticker_dir = vault_dir / ticker
    saved_reports = []
    if ticker_dir.exists():
        saved_reports = sorted(ticker_dir.glob(f"{ticker}-*.md"))

    workspace_context = [
        InjectedDataPoint(
            source_type="research_memory",
            label="linked_workspace_reports",
            value=f"후속 분석에 연결 가능한 저장 리포트 {len(saved_reports)}개",
            as_of=current_storage_date().isoformat(),
            confidence=1.0,
        )
    ]
    try:
        thesis_snapshot = read_ticker_thesis_snapshot(vault_dir, ticker)
    except Exception:
        thesis_snapshot = None
    if thesis_snapshot:
        workspace_context.append(
            InjectedDataPoint(
                source_type=DataSourceType.RESEARCH_MEMORY,
                label="latest_thesis_snapshot",
                value=(
                    f"최신 기준 투자 논거: {thesis_snapshot.get('thesis_summary')} | "
                    f"강세 트리거: {', '.join(thesis_snapshot.get('bull_triggers') or []) or '없음'} | "
                    f"약세 트리거: {', '.join(thesis_snapshot.get('bear_triggers') or []) or '없음'} | "
                    f"무효화 조건: {', '.join(thesis_snapshot.get('invalidation_conditions') or []) or '없음'}"
                ),
                as_of=thesis_snapshot.get("source_date") or current_storage_date().isoformat(),
                source_url=thesis_snapshot.get("source_relative_path"),
                confidence=float(thesis_snapshot.get("confidence") or 0.8),
            )
        )
    try:
        memory_search = search_research_memory_documents(vault_dir, ticker, limit=4)
    except Exception:
        memory_search = {"documents": []}
    for index, document in enumerate(memory_search.get("documents", []), start=1):
        summary = document.get("summary") or document.get("content_excerpt") or ""
        if not summary:
            continue
        workspace_context.append(
            InjectedDataPoint(
                source_type=DataSourceType.RESEARCH_MEMORY,
                label=f"rag_memory_document_{index}",
                value=(
                    f"{document.get('source_date') or '날짜 없음'} "
                    f"{document.get('report_type') or 'research'}: {summary}"
                ),
                as_of=document.get("source_date") or current_storage_date().isoformat(),
                source_url=document.get("source_relative_path"),
                confidence=float(document.get("confidence") or 0.7),
            )
        )
    for scope_key in ["MARKET", "MACRO", "SECTOR", "POLICY", "RATES", "FLOWS", "CUSTOMS"]:
        if ticker.upper() == scope_key:
            continue
        try:
            scope_search = search_research_memory_documents(vault_dir, scope_key, limit=1)
        except Exception:
            scope_search = {"documents": []}
        for document in scope_search.get("documents", [])[:1]:
            summary = document.get("summary") or document.get("content_excerpt") or ""
            if not summary:
                continue
            workspace_context.append(
                InjectedDataPoint(
                    source_type=DataSourceType.RESEARCH_MEMORY,
                    label=f"rag_cross_scope_{scope_key.lower()}",
                    value=(
                        f"{scope_key} 누적 자료 ({document.get('source_date') or '날짜 없음'}): "
                        f"{summary}"
                    ),
                    as_of=document.get("source_date") or current_storage_date().isoformat(),
                    source_url=document.get("source_relative_path"),
                    confidence=float(document.get("confidence") or 0.7),
                )
            )

    return [*provided_data, *workspace_context]


def collect_analysis_input_data(
    *,
    ticker: str,
    provided_data: list[InjectedDataPoint],
    auto_inject_data: bool,
    settings: Settings,
) -> list[InjectedDataPoint]:
    profile_points: list[InjectedDataPoint] = []
    verification = verify_ticker_symbol(ticker, settings)
    profile = None
    if verification.verified:
        profile = build_ticker_profile(ticker, settings, refresh_external=False)
        profile_points.append(
            InjectedDataPoint(
                source_type=DataSourceType.OTHER,
                label="official_company_profile",
                value=(
                    f"{profile.company_name} ({profile.exchange}) | "
                    f"사업 맥락: {profile.business_context or 'n/a'} | "
                    f"핵심 KPI: {', '.join(profile.watch_kpis) or 'n/a'}"
                ),
                as_of=current_storage_date().isoformat(),
                source_url=verification.verification_source,
                confidence=0.95,
            )
        )
        latest_earnings = latest_earnings_profile_for_ticker(
            ticker,
            settings,
            refresh_external=False,
        )
        if latest_earnings:
            profile_points.append(
                InjectedDataPoint(
                    source_type=DataSourceType.EARNINGS_RELEASE,
                    label="official_latest_earnings_profile",
                    value=latest_earnings_profile_summary(latest_earnings),
                    as_of=latest_earnings.get("earnings_report_date"),
                    source_url=latest_earnings.get("source_url"),
                    confidence=0.9,
                )
            )
    if not auto_inject_data or not settings.auto_inject_analysis_data:
        return [*profile_points, *provided_data]

    if not verification.verified:
        return [*profile_points, *provided_data]

    provider = get_analysis_data_provider(settings)
    provider_data = provider.fetch_analysis_context(ticker)
    if verification.verified and profile:
        provider_data.extend(
            fetch_nps_institutional_context(ticker, profile.company_name, settings) or []
        )
    if settings.data_provider_mode == "mock":
        provider_data.append(
            InjectedDataPoint(
                source_type=DataSourceType.OTHER,
                label="data_provider_limitation",
                value="현재 시장/재무 데이터 프로바이더가 mock 모드입니다. 가격과 재무 수치는 실제 투자 판단에 사용하지 마세요.",
                as_of=current_storage_date().isoformat(),
                confidence=0.4,
            )
        )
    return [*profile_points, *provider_data, *provided_data]


def is_archived_research_entry(manifest_entry: dict | None, json_payload: dict | None = None) -> bool:
    payload = json_payload if isinstance(json_payload, dict) else {}
    entry = manifest_entry if isinstance(manifest_entry, dict) else {}
    return bool(
        entry.get("is_deleted")
        or payload.get("is_deleted")
        or str(entry.get("status") or "").lower() == "archived"
        or str(payload.get("status") or "").lower() == "archived"
    )


def list_research_memory_files(
    ticker: str,
    vault_dir: Path,
    include_archived: bool = False,
) -> list[ResearchMemoryFile]:
    ticker_dir = vault_dir / ticker
    if not ticker_dir.exists():
        return []
    manifest_by_file = {
        entry.get("file_name"): entry
        for entry in read_manifest(vault_dir)
        if entry.get("ticker") == ticker and entry.get("file_name")
    }

    files = sorted(
        ticker_dir.glob(f"{ticker}-*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )

    memory_files = [
        build_research_memory_file(file_path, ticker, vault_dir, manifest_by_file.get(file_path.name))
        for file_path in files
    ]
    if include_archived:
        return memory_files
    return [file for file in memory_files if not file.archived and not file.is_deleted]


def build_research_memory_file(
    file_path: Path,
    ticker: str,
    vault_dir: Path,
    manifest_entry: dict | None,
) -> ResearchMemoryFile:
    json_path = file_path.with_suffix(".json")
    json_payload = {}
    if json_path.exists():
        try:
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))
        except Exception:
            json_payload = {}
    captured_item = json_payload.get("captured_item") if isinstance(json_payload, dict) else {}
    if not isinstance(captured_item, dict):
        captured_item = {}
    archived = is_archived_research_entry(manifest_entry, json_payload)
    archive_reason = (
        manifest_entry.get("archive_reason")
        if manifest_entry
        else json_payload.get("archive_reason")
    )
    archived_at = (
        manifest_entry.get("archived_at")
        if manifest_entry
        else json_payload.get("archived_at")
    )
    sidecar_verified = bool(
        ticker in SPECIAL_RESEARCH_KEYS
        and isinstance(json_payload, dict)
        and json_payload.get("status") == "success"
        and normalize_ticker(captured_item.get("ticker") or ticker) == ticker
    )
    verified = bool(
        (manifest_entry and is_verified_manifest_entry(manifest_entry, ticker))
        or sidecar_verified
    )
    status_label = "보관됨" if archived else "저장 메타 확인" if sidecar_verified else "공식 인증" if verified else "레거시/검증 전"
    return ResearchMemoryFile(
        file_name=file_path.name,
        relative_path=file_path.relative_to(vault_dir.parent).as_posix(),
        absolute_path=str(file_path),
        json_file_name=json_path.name if json_path.exists() else None,
        json_relative_path=json_path.relative_to(vault_dir.parent).as_posix()
        if json_path.exists()
        else None,
        modified_at=datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
        report_type=(
            manifest_entry.get("type")
            if manifest_entry
            else "research-capture"
            if json_payload.get("module") == "research_quick_capture"
            else infer_report_type_from_file(file_path.name)
        ),
        summary=(
            manifest_entry.get("summary")
            if manifest_entry
            else captured_item.get("summary") or json_payload.get("summary")
        ),
        verified=verified,
        legacy=not verified,
        status_label=status_label,
        capture_quality=(
            manifest_entry.get("capture_quality")
            if manifest_entry and manifest_entry.get("capture_quality")
            else json_payload.get("capture_quality")
        ),
        attachment=(
            manifest_entry.get("attachment")
            if manifest_entry and manifest_entry.get("attachment")
            else json_payload.get("attachment")
        ),
        archived=archived,
        is_deleted=archived,
        archived_at=archived_at,
        archive_reason=archive_reason,
    )


def read_research_memory_file(
    ticker: str,
    file_name: str,
    vault_dir: Path,
) -> ResearchMemoryContentResponse:
    safe_name = Path(file_name).name
    if safe_name != file_name or not safe_name.endswith(".md"):
        raise HTTPException(status_code=400, detail="읽을 수 없는 파일명입니다.")

    ticker_dir = (vault_dir / ticker).resolve()
    target_path = (ticker_dir / safe_name).resolve()
    if target_path.parent != ticker_dir:
        raise HTTPException(status_code=400, detail="허용되지 않은 파일 경로입니다.")
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="저장된 리포트 파일을 찾을 수 없습니다.")

    json_payload = None
    json_path = target_path.with_suffix(".json")
    if json_path.exists():
        json_payload = json.loads(json_path.read_text(encoding="utf-8"))
    manifest_entry = next(
        (
            entry
            for entry in read_manifest(vault_dir)
            if entry.get("ticker") == ticker and entry.get("file_name") == target_path.name
        ),
        None,
    )
    verified = bool(manifest_entry and is_verified_manifest_entry(manifest_entry, ticker))
    captured_item = (json_payload or {}).get("captured_item", {}) if isinstance(json_payload, dict) else {}
    if not isinstance(captured_item, dict):
        captured_item = {}
    archived = is_archived_research_entry(manifest_entry, json_payload)
    archive_reason = (
        manifest_entry.get("archive_reason")
        if manifest_entry
        else (json_payload or {}).get("archive_reason")
        if isinstance(json_payload, dict)
        else None
    )
    archived_at = (
        manifest_entry.get("archived_at")
        if manifest_entry
        else (json_payload or {}).get("archived_at")
        if isinstance(json_payload, dict)
        else None
    )
    sidecar_verified = bool(
        ticker in SPECIAL_RESEARCH_KEYS
        and isinstance(json_payload, dict)
        and json_payload.get("status") == "success"
        and normalize_ticker(captured_item.get("ticker") or ticker) == ticker
    )
    verified = bool(verified or sidecar_verified)

    status_label = "보관됨" if archived else "저장 메타 확인" if sidecar_verified else "공식 인증" if verified else "레거시/검증 전"
    return ResearchMemoryContentResponse(
        ticker=ticker,
        file_name=target_path.name,
        relative_path=target_path.relative_to(vault_dir.parent).as_posix(),
        content=target_path.read_text(encoding="utf-8"),
        modified_at=datetime.fromtimestamp(target_path.stat().st_mtime).isoformat(),
        json_payload=json_payload,
        report_type=manifest_entry.get("type") if manifest_entry else infer_report_type_from_file(target_path.name),
        summary=(
            manifest_entry.get("summary")
            if manifest_entry
            else (json_payload or {}).get("captured_item", {}).get("summary")
            if isinstance(json_payload, dict)
            else None
        ),
        verified=verified,
        legacy=not verified,
        status_label=status_label,
        capture_quality=(
            manifest_entry.get("capture_quality")
            if manifest_entry and manifest_entry.get("capture_quality")
            else (json_payload or {}).get("capture_quality")
            if isinstance(json_payload, dict)
            else None
        ),
        attachment=(
            manifest_entry.get("attachment")
            if manifest_entry and manifest_entry.get("attachment")
            else (json_payload or {}).get("attachment")
            if isinstance(json_payload, dict)
            else None
        ),
        archived=archived,
        is_deleted=archived,
        archived_at=archived_at,
        archive_reason=archive_reason,
    )


def set_research_memory_archive_status(
    ticker: str,
    file_name: str,
    request: ResearchMemoryArchiveRequest,
    vault_dir: Path,
) -> ResearchMemoryContentResponse:
    safe_name = Path(file_name).name
    if safe_name != file_name or not safe_name.endswith(".md"):
        raise HTTPException(status_code=400, detail="보관 상태를 바꿀 수 없는 파일명입니다.")

    ticker_dir = (vault_dir / ticker).resolve()
    target_path = (ticker_dir / safe_name).resolve()
    if target_path.parent != ticker_dir:
        raise HTTPException(status_code=400, detail="허용되지 않은 파일 경로입니다.")
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="저장된 리포트 파일을 찾을 수 없습니다.")

    now = current_storage_timestamp()
    archived = bool(request.archived)
    reason = (request.reason or "").strip() or (
        "사용자가 저장 데이터 화면에서 보관 처리했습니다."
        if archived
        else "사용자가 저장 데이터 화면에서 보관 해제했습니다."
    )
    json_path = target_path.with_suffix(".json")
    json_payload = {}
    if json_path.exists():
        try:
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            json_payload = {}
    if isinstance(json_payload, dict):
        json_payload["status"] = "archived" if archived else "active"
        json_payload["is_deleted"] = archived
        json_payload["archived_at"] = now if archived else None
        json_payload["archive_reason"] = reason if archived else None
        json_payload["updated_at"] = now
        json_path.write_text(
            json.dumps(json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    manifest_entry = next(
        (
            entry
            for entry in read_manifest(vault_dir)
            if entry.get("ticker") == ticker and entry.get("file_name") == target_path.name
        ),
        None,
    )
    if not manifest_entry:
        manifest_entry = {
            "ticker": ticker,
            "type": infer_report_type_from_file(target_path.name),
            "date": datetime.fromtimestamp(target_path.stat().st_mtime).date().isoformat(),
            "file_name": target_path.name,
            "relative_path": target_path.relative_to(vault_dir.parent).as_posix(),
            "json_file_name": json_path.name if json_path.exists() else None,
            "json_relative_path": json_path.relative_to(vault_dir.parent).as_posix()
            if json_path.exists()
            else None,
            "summary": json_payload.get("summary")
            if isinstance(json_payload, dict)
            else None,
        }
    updated_entry = {**manifest_entry}
    updated_entry["status"] = "archived" if archived else "active"
    updated_entry["is_deleted"] = archived
    updated_entry["archived_at"] = now if archived else None
    updated_entry["archive_reason"] = reason if archived else None
    updated_entry["updated_at"] = now
    tags = list(dict.fromkeys([*(updated_entry.get("tags") or [])]))
    if archived and "archived" not in tags:
        tags.append("archived")
    if not archived:
        tags = [tag for tag in tags if tag != "archived"]
    updated_entry["tags"] = tags
    update_manifest(vault_dir=vault_dir, entry=updated_entry)
    upsert_research_memory_document(
        vault_dir=vault_dir,
        entry=updated_entry,
        full_text=target_path.read_text(encoding="utf-8"),
    )
    return read_research_memory_file(ticker, safe_name, vault_dir)


def supplement_research_memory_file(
    ticker: str,
    file_name: str,
    request: ResearchMemorySupplementRequest,
    vault_dir: Path,
) -> ResearchMemoryContentResponse:
    safe_name = Path(file_name).name
    if safe_name != file_name or not safe_name.endswith(".md"):
        raise HTTPException(status_code=400, detail="수정할 수 없는 파일명입니다.")

    body_text = request.body_text.strip()
    if not body_text:
        raise HTTPException(status_code=422, detail="보강할 본문 텍스트가 비어 있습니다.")

    ticker_dir = (vault_dir / ticker).resolve()
    target_path = (ticker_dir / safe_name).resolve()
    if target_path.parent != ticker_dir:
        raise HTTPException(status_code=400, detail="허용되지 않은 파일 경로입니다.")
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="저장된 리포트 파일을 찾을 수 없습니다.")

    supplemented_at = current_storage_timestamp()
    note = (request.note or "").strip()
    current_content = target_path.read_text(encoding="utf-8")
    supplement_section = [
        "",
        "",
        "## 본문 보강",
        "",
        f"- 보강 일시: {supplemented_at}",
        "- 보강 방식: 사용자 직접 입력",
    ]
    if note:
        supplement_section.append(f"- 메모: {note}")
    supplement_section.extend(["", body_text])
    updated_content = current_content.rstrip() + "\n".join(supplement_section) + "\n"
    target_path.write_text(updated_content, encoding="utf-8")

    supplement_meta = {
        "supplemented_at": supplemented_at,
        "source": "user_body_copy",
        "char_count": len(body_text),
        "note": note or None,
    }
    json_path = target_path.with_suffix(".json")
    json_payload = {}
    if json_path.exists():
        try:
            json_payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            json_payload = {}
    if isinstance(json_payload, dict):
        supplements = json_payload.get("body_supplements")
        if not isinstance(supplements, list):
            supplements = []
        supplements.append(supplement_meta)
        json_payload["body_supplements"] = supplements
        json_payload["body_supplemented_at"] = supplemented_at
        json_payload["raw_content"] = "\n\n".join(
            value
            for value in [
                str(json_payload.get("raw_content") or "").strip(),
                "[사용자 보강 본문]",
                body_text,
            ]
            if value
        )
        capture_quality = json_payload.get("capture_quality")
        if isinstance(capture_quality, dict):
            capture_quality["status"] = "정상"
            capture_quality["body_supplemented"] = True
            capture_quality["supplemented_at"] = supplemented_at
            capture_quality["readiness"] = "사용자 보강 본문으로 분석 활용 가능"
        json_path.write_text(
            json.dumps(json_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    manifest_entry = next(
        (
            entry
            for entry in read_manifest(vault_dir)
            if entry.get("ticker") == ticker and entry.get("file_name") == target_path.name
        ),
        None,
    )
    if manifest_entry:
        updated_entry = {**manifest_entry}
        tags = list(dict.fromkeys([*(updated_entry.get("tags") or []), "body_supplemented"]))
        updated_entry["tags"] = tags
        updated_entry["body_supplemented_at"] = supplemented_at
        updated_entry["body_supplement_count"] = int(updated_entry.get("body_supplement_count") or 0) + 1
        updated_entry["content_hash"] = content_fingerprint(updated_content)
        capture_quality = updated_entry.get("capture_quality")
        if isinstance(capture_quality, dict):
            capture_quality = {**capture_quality}
            capture_quality["status"] = "정상"
            capture_quality["body_supplemented"] = True
            capture_quality["supplemented_at"] = supplemented_at
            capture_quality["readiness"] = "사용자 보강 본문으로 분석 활용 가능"
            updated_entry["capture_quality"] = capture_quality
        update_manifest(vault_dir=vault_dir, entry=updated_entry)
        upsert_research_memory_document(
            vault_dir=vault_dir,
            entry=updated_entry,
            full_text=updated_content,
        )

    return read_research_memory_file(ticker, safe_name, vault_dir)


def latest_manifest_entry(entries: list[dict], *report_types: str) -> dict | None:
    wanted = set(report_types)
    matches = [entry for entry in entries if entry.get("type") in wanted]
    if not matches:
        return None
    return sorted(
        matches,
        key=lambda entry: (
            entry.get("date", ""),
            report_file_sequence(entry.get("file_name", "")),
            entry.get("file_name", ""),
        ),
        reverse=True,
    )[0]


def read_manifest_entry_payload(entry: dict | None, vault_dir: Path) -> dict:
    if not entry:
        return {}
    candidate_paths: list[Path] = []
    json_relative_path = entry.get("json_relative_path")
    if json_relative_path:
        candidate_paths.append((vault_dir.parent / str(json_relative_path)).resolve())
    relative_path = entry.get("relative_path")
    if relative_path:
        candidate_paths.append((vault_dir.parent / str(relative_path)).with_suffix(".json").resolve())
    file_name = entry.get("file_name")
    ticker = entry.get("ticker")
    if file_name and ticker:
        candidate_paths.append((vault_dir / str(ticker) / str(file_name)).with_suffix(".json").resolve())
    for path in candidate_paths:
        try:
            if path.exists() and path.is_file():
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
        except (OSError, json.JSONDecodeError):
            continue
    return {}


def build_latest_dossier_preview(ticker: str, entries: list[dict], vault_dir: Path) -> dict:
    dossier_entry = latest_manifest_entry(entries, "dossier-synthesis")
    if not dossier_entry:
        return {}
    payload = read_manifest_entry_payload(dossier_entry, vault_dir)
    source = payload if payload else dossier_entry
    return {
        "ticker": ticker,
        "company_name": source.get("company_name") or dossier_entry.get("company_name") or ticker_company_name(ticker),
        "date": source.get("date") or dossier_entry.get("date"),
        "file_name": dossier_entry.get("file_name"),
        "relative_path": dossier_entry.get("relative_path"),
        "summary": source.get("thesis_summary") or source.get("summary") or dossier_entry.get("summary"),
        "confidence": source.get("confidence") or dossier_entry.get("source_confidence"),
        "source_count": source.get("source_count") or dossier_entry.get("source_count") or 0,
        "duplicate_count": source.get("duplicate_count") or dossier_entry.get("duplicate_count") or 0,
        "consensus_facts": (source.get("consensus_facts") or [])[:3],
        "bull_thesis": (source.get("bull_thesis") or [])[:3],
        "bear_thesis": (source.get("bear_thesis") or [])[:3],
        "cruxes": (source.get("cruxes") or [])[:3],
        "observables": (source.get("observables") or [])[:4],
    }


def build_document_quality_digest(ticker: str, entries: list[dict], vault_dir: Path) -> dict:
    documents: list[dict] = []
    for entry in entries:
        if entry.get("type") != "research-capture":
            continue
        payload = read_manifest_entry_payload(entry, vault_dir)
        attachment = entry.get("attachment") or payload.get("attachment") or {}
        url_processing = entry.get("source_url_processing") or payload.get("source_url_processing") or {}
        has_file = bool(attachment)
        has_url = bool(url_processing)
        if not (has_file or has_url):
            continue
        profile = attachment.get("extraction_profile") or {}
        warnings = attachment.get("extraction_warnings") or []
        quality = attachment.get("extraction_quality")
        try:
            quality_value = float(quality)
        except (TypeError, ValueError):
            quality_value = 0.0 if has_file else 0.55
        char_count = int(
            attachment.get("extraction_char_count")
            or profile.get("char_count")
            or len(str(payload.get("document_preview") or ""))
            or 0
        )
        if not quality and char_count:
            quality_value = min(0.95, max(0.45, char_count / 6000))
        documents.append(
            {
                "date": entry.get("date"),
                "file_name": attachment.get("file_name") or entry.get("file_name"),
                "title": entry.get("title") or entry.get("summary") or attachment.get("file_name"),
                "document_type": attachment.get("document_type") or ("웹 문서" if has_url else "파일"),
                "quality": round(quality_value, 2) if quality_value else None,
                "char_count": char_count,
                "analysis_readiness": profile.get("analysis_readiness") or ("웹 본문 추출" if has_url else "확인 필요"),
                "next_action": profile.get("next_action") or ("추출 본문으로 자동 분류·태깅 완료" if char_count else "본문 추출 상태를 확인하세요."),
                "warnings": warnings[:3],
                "source_url": url_processing.get("source_url"),
                "relative_path": entry.get("relative_path"),
            }
        )
    documents = sorted(
        documents,
        key=lambda item: (item.get("date") or "", item.get("file_name") or ""),
        reverse=True,
    )[:5]
    if not documents:
        return {}
    usable = [item for item in documents if (item.get("quality") or 0) >= 0.65 or (item.get("char_count") or 0) >= 1000]
    warning_count = sum(len(item.get("warnings") or []) for item in documents)
    latest = documents[0]
    return {
        "ticker": ticker,
        "document_count": len(documents),
        "usable_count": len(usable),
        "warning_count": warning_count,
        "latest": latest,
        "documents": documents,
        "headline": "추출 품질 양호" if usable else "추출 품질 확인 필요",
    }


def build_latest_market_journal_reference(settings: Settings) -> dict:
    store = read_market_close_journal(settings)
    entries = [
        item
        for item in store.get("entries", [])
        if isinstance(item, dict)
    ]
    if not entries:
        return {}
    latest = sorted(
        entries,
        key=lambda item: (item.get("session_date") or "", item.get("updated_at") or item.get("created_at") or ""),
        reverse=True,
    )[0]
    return {
        "market": latest.get("market"),
        "session_date": latest.get("session_date"),
        "sentiment": latest.get("sentiment"),
        "risk_level": latest.get("risk_level"),
        "regime": latest.get("regime"),
        "key_drivers": (latest.get("key_drivers") or [])[:4],
        "sector_implications": (latest.get("sector_implications") or [])[:4],
        "auto_utilization_focus": (latest.get("auto_utilization_focus") or [])[:4],
        "portfolio_actions": (latest.get("portfolio_actions") or [])[:3],
        "next_session_watch": (latest.get("next_session_watch") or [])[:4],
        "tags": (latest.get("tags") or [])[:8],
    }


def latest_manifest_thesis_snapshot(ticker: str, entries: list[dict]) -> dict:
    thesis_entries = [
        entry
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("investment_thesis"), dict)
    ]
    if not thesis_entries:
        return {}
    latest_entry = sorted(
        thesis_entries,
        key=lambda entry: (
            entry.get("date", ""),
            report_file_sequence(entry.get("file_name", "")),
            entry.get("file_name", ""),
        ),
        reverse=True,
    )[0]
    thesis = latest_entry.get("investment_thesis") or {}
    watch_items = [
        item for item in latest_entry.get("watch_items", []) if isinstance(item, dict)
    ]
    valuation = thesis.get("valuation_assumptions") if isinstance(thesis, dict) else {}
    if not isinstance(valuation, dict):
        valuation = {}
    return {
        "ticker": thesis.get("ticker") or ticker,
        "company_name": latest_entry.get("company_name"),
        "thesis_summary": thesis.get("thesis") or latest_entry.get("summary"),
        "bull_triggers": thesis.get("bull_triggers") or [],
        "bear_triggers": thesis.get("bear_triggers") or [],
        "invalidation_conditions": thesis.get("invalidation_conditions") or [],
        "watch_kpis": thesis.get("watch_kpis") or [],
        "watch_items": watch_items,
        "source_report_type": latest_entry.get("type"),
        "source_file_name": latest_entry.get("file_name"),
        "source_relative_path": latest_entry.get("relative_path"),
        "source_date": latest_entry.get("date"),
        "confidence": latest_entry.get("source_confidence") or valuation.get("confidence"),
        "updated_at": latest_entry.get("updated_at") or latest_entry.get("date"),
    }


def report_file_sequence(file_name: str) -> int:
    match = search(r"\d{4}-\d{2}-\d{2}-(\d+)\.(?:md|json)$", file_name)
    if match:
        return int(match.group(1))
    return 1 if search(r"\d{4}-\d{2}-\d{2}\.(?:md|json)$", file_name) else 0


def compact_tooltip_text(value: object, limit: int = 180) -> str:
    if value is None:
        return "근거 요약 없음"
    if isinstance(value, list):
        value = " / ".join(str(item) for item in value[:2])
    elif isinstance(value, dict):
        value = " / ".join(f"{key}: {item}" for key, item in list(value.items())[:3])
    text = sub(r"\s+", " ", str(value)).strip()
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text or "근거 요약 없음"


def dashboard_report_impact_reason(entry: dict) -> str | None:
    if entry.get("type") != "thesis-impact-review":
        return None
    reasons: list[str] = []
    impact = entry.get("overall_impact")
    if impact:
        reasons.append(f"판정: {impact}")
    summary = entry.get("summary")
    if summary:
        reasons.append(f"요약: {compact_tooltip_text(summary, 140)}")
    for finding in (entry.get("findings") or [])[:2]:
        if not isinstance(finding, dict):
            continue
        reference = compact_tooltip_text(finding.get("thesis_reference") or "기존 투자 논거", 70)
        evidence = compact_tooltip_text(
            finding.get("rationale") or finding.get("evidence") or finding.get("signal"),
            150,
        )
        reasons.append(f"근거: {reference} → {evidence}")
    next_actions = [compact_tooltip_text(item, 80) for item in (entry.get("next_actions") or [])[:2]]
    if next_actions:
        reasons.append("다음 조치: " + " / ".join(next_actions))
    return "\n".join(reasons) if reasons else None


def dashboard_report_summary(entry: dict) -> DashboardReportSummary:
    impact_reason = dashboard_report_impact_reason(entry)
    impact_label = entry.get("overall_impact") if entry.get("type") == "thesis-impact-review" else None
    return DashboardReportSummary(
        type=entry.get("type", "unknown"),
        file_name=entry.get("file_name", "unknown.md"),
        relative_path=entry.get("relative_path", ""),
        date=entry.get("date", ""),
        summary=entry.get("summary"),
        impact_label=impact_label,
        impact_reason=impact_reason,
        tooltip=impact_reason,
    )


def infer_report_type_from_file(file_name: str) -> str:
    known_types = [
        "collaborative-team-report",
        "institutional-stock-breakdown",
        "smart-trade-setup",
        "earnings-reaction",
        "research-capture",
        "thesis-impact-review",
        "research-checklist",
        "portfolio-risk-scan",
        "reinforcement-portfolio-optimizer",
        "sector-opportunity",
        "long-term-compounder",
    ]
    for report_type in known_types:
        if report_type in file_name:
            return report_type
    return "saved-report"


def infer_report_date_from_file(file_name: str) -> str:
    match = search(r"\d{4}-\d{2}-\d{2}", file_name)
    if match:
        return match.group(0)
    return ""


def build_dashboard_latest_reports(
    entries: list[dict],
    files: list[ResearchMemoryFile],
) -> list[DashboardReportSummary]:
    summaries = [dashboard_report_summary(entry) for entry in entries]
    seen_paths = {
        summary.relative_path
        for summary in summaries
        if summary.relative_path
    }
    for file in files:
        if file.relative_path in seen_paths:
            continue
        summaries.append(
            DashboardReportSummary(
                type=infer_report_type_from_file(file.file_name),
                file_name=file.file_name,
                relative_path=file.relative_path,
                date=infer_report_date_from_file(file.file_name),
                summary=f"저장된 Markdown 리포트: {file.file_name}",
            )
        )

    return summaries[:6]


def render_dashboard_watch_item(item: object) -> str:
    if isinstance(item, dict):
        metric = item.get("metric", "추적 항목")
        condition = item.get("condition", "조건 확인 필요")
        action = item.get("action", "후속 점검")
        priority = item.get("priority", "medium")
        return f"[{translate_severity_label(priority)}] {metric}: {condition} -> {action}"
    return str(item)


def translate_severity_label(value: object) -> str:
    labels = {
        "high": "높음",
        "medium": "보통",
        "low": "낮음",
    }
    return labels.get(str(value), str(value))


def is_verified_manifest_entry(entry: dict, ticker: str) -> bool:
    verification = entry.get("ticker_verification") or {}
    return (
        verification.get("verified") is True
        and verification.get("official_symbol") == ticker
    )


def build_ticker_dashboard(ticker: str, vault_dir: Path, settings: Settings) -> TickerDashboardResponse:
    ticker_verification = verify_ticker_symbol_local_cached(ticker, settings)
    ticker_profile = build_ticker_profile(
        ticker,
        settings,
        refresh_external=False,
    )
    manifest_entries = read_manifest(vault_dir)
    all_entries = [
        entry
        for entry in manifest_entries
        if entry.get("ticker") == ticker
    ]
    entries = [
        entry
        for entry in all_entries
        if is_verified_manifest_entry(entry, ticker)
    ]
    legacy_entries = [
        entry
        for entry in all_entries
        if not is_verified_manifest_entry(entry, ticker)
    ]
    sorted_entries = sorted(
        entries,
        key=lambda entry: (
            entry.get("date", ""),
            report_file_sequence(entry.get("file_name", "")),
            entry.get("file_name", ""),
        ),
        reverse=True,
    )
    files = list_research_memory_files(ticker, vault_dir)
    legacy_file_count = max(len(files) - len(entries), 0)
    legacy_report_count = max(len(legacy_entries), legacy_file_count)
    data_warnings: list[str] = []
    if legacy_report_count:
        data_warnings.append(
            f"{ticker}에는 공식 티커 인증 도입 전 생성된 레거시 리포트 {legacy_report_count}개가 있습니다. "
            "오염된 가격·가정이 섞일 수 있어 대시보드 기본 분석에서 제외했습니다."
        )
    if settings.data_provider_mode == "mock":
        data_warnings.append(
            "현재 데이터 프로바이더가 모의 데이터 모드입니다. 가격·재무 수치는 실제 데이터가 아니므로 리포트의 정량 판단은 보조용으로만 보세요."
        )
    data_warnings.extend(ticker_profile.data_limitations)
    if ticker_verification.verified and not entries:
        data_warnings.append(
            f"{ticker_verification.company_name} ({ticker_verification.exchange}) 기준으로 "
            "공식 인증 이후 생성된 분석 리포트가 아직 없습니다. 팀 리포트부터 새로 실행하세요."
        )
    report_count_by_type: dict[str, int] = {}
    for entry in entries:
        report_type = entry.get("type", "unknown")
        report_count_by_type[report_type] = report_count_by_type.get(report_type, 0) + 1

    portfolio_store = read_portfolio_store(settings)
    portfolio_policy_keys = {
        portfolio_store_key(item.get("portfolio_name", ""))
        for item in portfolio_store.get("portfolios", {}).values()
        if isinstance(item, dict) and item.get("portfolio_name")
    }
    portfolio_policy_reports = [
        entry
        for entry in manifest_entries
        if entry.get("type") == "reinforcement-portfolio-optimizer"
        and entry.get("ticker") in portfolio_policy_keys
    ]
    latest_policy_report = latest_manifest_entry(
        portfolio_policy_reports,
        "reinforcement-portfolio-optimizer",
    )

    checklist = latest_manifest_entry(entries, "research-checklist")
    team_report = latest_manifest_entry(
        entries,
        "collaborative-team-report",
        "institutional-stock-breakdown",
    )
    capture = latest_manifest_entry(entries, "research-capture")
    trade = latest_manifest_entry(entries, "smart-trade-setup")
    earnings = latest_manifest_entry(entries, "earnings-reaction")
    model_update_note = latest_manifest_entry(entries, "earnings-filing-note")
    try:
        thesis_snapshot = read_ticker_thesis_snapshot(vault_dir, ticker) or {}
    except Exception:
        thesis_snapshot = latest_manifest_thesis_snapshot(ticker, entries)
    latest_thesis_snapshot = {}
    if thesis_snapshot:
        latest_thesis_snapshot = {
            "ticker": thesis_snapshot.get("ticker"),
            "company_name": thesis_snapshot.get("company_name"),
            "thesis_summary": thesis_snapshot.get("thesis_summary"),
            "bull_triggers": (thesis_snapshot.get("bull_triggers") or [])[:4],
            "bear_triggers": (thesis_snapshot.get("bear_triggers") or [])[:4],
            "invalidation_conditions": (
                thesis_snapshot.get("invalidation_conditions") or []
            )[:4],
            "watch_kpis": (thesis_snapshot.get("watch_kpis") or [])[:6],
            "watch_items": (thesis_snapshot.get("watch_items") or [])[:6],
            "source_report_type": thesis_snapshot.get("source_report_type"),
            "source_file_name": thesis_snapshot.get("source_file_name"),
            "source_relative_path": thesis_snapshot.get("source_relative_path"),
            "source_date": thesis_snapshot.get("source_date"),
            "confidence": thesis_snapshot.get("confidence"),
            "updated_at": thesis_snapshot.get("updated_at"),
        }
    latest_earnings_profile = latest_earnings_profile_for_ticker(
        ticker,
        settings,
        refresh_external=False,
    )
    latest_reported_quarter = ticker_profile.latest_reported_quarter
    earnings_aligned = bool(
        earnings
        and latest_reported_quarter
        and normalize_quarter_label(earnings.get("quarter"))
        == normalize_quarter_label(latest_reported_quarter)
    )
    latest_earnings_reference = {
        "official_quarter": latest_reported_quarter,
        "official_earnings_report_date": ticker_profile.latest_reported_earnings_date,
        "previous_earnings_date": ticker_profile.previous_earnings_date,
        "next_earnings_date": ticker_profile.next_earnings_date,
        "source_url": latest_earnings_profile.get("source_url"),
        "saved_report_file": earnings.get("file_name") if earnings else None,
        "saved_report_quarter": earnings.get("quarter") if earnings else None,
        "saved_report_evidence_status": earnings.get("evidence_status") if earnings else None,
        "saved_report_summary": earnings.get("summary") if earnings else None,
        "aligned_with_latest": earnings_aligned,
    }
    nps_signal: dict = {
        "ticker": ticker,
        "company_name": ticker_profile.company_name,
        "warnings": ["대시보드는 빠른 표시를 위해 국민연금 수급을 로컬/캐시 기준으로만 표시합니다. 수급 상세 버튼에서 최신 조회를 실행하세요."],
        "source": "dashboard_fast_path",
    }
    if nps_signal.get("warnings") and (
        nps_signal.get("domestic_match_found") or nps_signal.get("large_holding_events")
    ):
        data_warnings.extend(
            [f"국민연금 데이터 확인: {warning}" for warning in nps_signal.get("warnings", [])[:2]]
        )
    nps_decision_note = nps_signal_decision_note(nps_signal, ticker_profile.company_name)
    if nps_signal_outflow_like(nps_signal):
        data_warnings.append(
            "국민연금 대량보유 보고에서 감소/처분성 표현이 감지되었습니다. 수급 이탈 여부를 별도로 확인하세요."
        )
    dart_filing_signal = build_dart_filing_signal(ticker, settings)
    if dart_filing_signal.get("latest_failure"):
        data_warnings.append(
            f"DART 신규 공시 자동 체크 실패: {dart_filing_signal.get('summary')}"
        )
    elif dart_filing_signal.get("recent_count"):
        recommended_dart = dart_filing_signal.get("summary") or "최근 DART 공시를 확인하세요."
        data_warnings.append(f"DART 신규 공시 확인: {recommended_dart}")

    watch_items: list[str] = []
    for entry in sorted_entries:
        for item in entry.get("watch_items", []) or []:
            watch_items.append(render_dashboard_watch_item(item))
        for item in entry.get("watch_before_next_earnings", []) or []:
            watch_items.append(str(item))
    unique_watch_items = list(dict.fromkeys(watch_items))[:8]

    checklist_rate = checklist.get("completion_rate") if checklist else None
    checklist_readiness = checklist.get("readiness_level") if checklist else None

    recommended_actions: list[str] = []
    if dart_filing_signal.get("recent_count"):
        recommended_actions.append("최근 DART 공시를 팀 리포트와 리스크 스캔에 반영하세요.")
    elif dart_filing_signal.get("latest_failure"):
        recommended_actions.append("DART 자동 체크 연결 실패가 있어 네트워크/방화벽 또는 OpenDART 접속 상태를 확인하세요.")
    if nps_decision_note:
        recommended_actions.append(nps_decision_note)
    if not team_report:
        recommended_actions.append("팀 리포트 또는 기관급 분석으로 기준 투자 논거를 먼저 생성하세요.")
    if not latest_thesis_snapshot:
        recommended_actions.append("저장 데이터 검색 합성으로 최신 투자 논거 스냅샷을 생성하세요.")
    if checklist_rate is None:
        recommended_actions.append("16개 리서치 체크리스트를 작성해 투자 준비도를 수치화하세요.")
    elif float(checklist_rate) < 0.75:
        recommended_actions.append("체크리스트 완료율을 75% 이상으로 보강한 뒤 투자 판단을 업데이트하세요.")
    if not trade:
        recommended_actions.append("매매 전략 모듈에서 진입 구간, 손절, 목표가를 설계하세요.")
    if not earnings:
        recommended_actions.append("최근 실적 발표 반응을 분석해 다음 실적 전 추적 항목을 정리하세요.")
    elif not earnings_aligned:
        recommended_actions.append(
            f"실적 분석을 최신 발표 분기({latest_reported_quarter or '확인 필요'}) 기준으로 다시 실행하세요."
        )
    if earnings and not model_update_note:
        recommended_actions.append("어닝 콜/공시 기반 모델 업데이트 노트를 작성해 실적 분석을 밸류에이션 가정까지 연결하세요.")
    if capture:
        recommended_actions.append("최근 빠른 정보 저장 내용을 기준으로 팀 리포트를 재실행해 논거 변화를 반영하세요.")
    if portfolio_store.get("portfolios") and not latest_policy_report:
        recommended_actions.append("저장된 내 포트폴리오에 강화학습형 정책 최적화를 실행해 비중 조정 후보를 점검하세요.")
    latest_customs_report = latest_manifest_entry(
        [entry for entry in manifest_entries if entry.get("ticker") == "CUSTOMS"],
        "customs-trade-brief",
    )
    latest_customs_trade_reference: dict = {}
    if latest_customs_report:
        latest_customs_trade_reference = {
            "date": latest_customs_report.get("date"),
            "summary": latest_customs_report.get("summary"),
            "relative_path": latest_customs_report.get("relative_path"),
            "sector_implications": (latest_customs_report.get("sector_implications") or [])[:4],
            "release_schedule": latest_customs_report.get("release_schedule")
            or settings.customs_trade_release_days,
            "source": latest_customs_report.get("source") or "관세청 품목별 국가별 수출입실적(GW)",
        }
        recommended_actions.append(
            f"최근 관세청 수출입 자료({latest_customs_trade_reference.get('date') or '날짜 미확인'})를 수출주·재고 부담 점검에 반영하세요."
        )
    latest_daily_brief = read_latest_daily_brief(settings)
    daily_payload = latest_daily_brief.get("payload") if isinstance(latest_daily_brief, dict) else None
    if isinstance(daily_payload, dict):
        daily_date = daily_payload.get("date") or "날짜 미확인"
        if any(item.get("ticker") == ticker for item in daily_payload.get("snapshots", []) if isinstance(item, dict)):
            recommended_actions.append(f"{daily_date} 일일 브리핑에 이 종목 Dossier 스냅샷이 반영되어 있습니다.")
        elif ticker in daily_payload.get("portfolio_tickers", []):
            recommended_actions.append(f"{daily_date} 일일 브리핑 추적 종목에 포함되어 있습니다. 저장 데이터에서 최신 Dossier를 확인하세요.")
    if not recommended_actions:
        recommended_actions.append("새 뉴스나 수치가 들어오면 빠른 정보 저장으로 기존 논거 영향도를 점검하세요.")

    latest_dossier_preview = build_latest_dossier_preview(ticker, entries, vault_dir)
    document_quality_digest = build_document_quality_digest(ticker, entries, vault_dir)
    latest_market_journal_reference = build_latest_market_journal_reference(settings)
    automation_digest = build_research_automation_dashboard_digest(settings)
    priority_items: list[dict] = []
    if data_warnings:
        priority_items.append(
            {
                "label": "데이터 경고",
                "value": data_warnings[0],
                "tone": "warning",
                "action": "데이터 출처와 공식 인증 상태를 먼저 확인하세요.",
            }
        )
    if latest_market_journal_reference:
        priority_items.append(
            {
                "label": "시장일지",
                "value": (
                    f"{latest_market_journal_reference.get('session_date') or '최근'} "
                    f"{latest_market_journal_reference.get('sentiment') or '심리 미확인'} / "
                    f"{latest_market_journal_reference.get('risk_level') or '리스크 미확인'}"
                ),
                "tone": "ok" if latest_market_journal_reference.get("risk_level") in ("낮음", "보통") else "warning",
                "action": (latest_market_journal_reference.get("auto_utilization_focus") or ["시장일지를 종목·섹터 판단에 자동 반영합니다."])[0],
            }
        )
    if latest_customs_trade_reference:
        priority_items.append(
            {
                "label": "수출입 자료",
                "value": latest_customs_trade_reference.get("summary") or "관세청 수출입 자료가 저장되어 있습니다.",
                "tone": "ok",
                "action": "수출주, 재고 부담, 환율 민감 섹터 점검에 반영하세요.",
            }
        )
    if dart_filing_signal:
        priority_items.append(
            {
                "label": "DART 공시",
                "value": dart_filing_signal.get("headline") or "상태 미확인",
                "tone": dart_filing_signal.get("tone") or "neutral",
                "action": dart_filing_signal.get("summary") or "최근 공시 자동 체크 상태를 확인하세요.",
            }
        )
    if latest_dossier_preview:
        priority_items.append(
            {
                "label": "Dossier 합성",
                "value": latest_dossier_preview.get("summary") or "최신 Dossier가 있습니다.",
                "tone": "ok",
                "action": "공통 사실, 강세/약세 논거, 핵심 쟁점 기준으로 리포트를 갱신하세요.",
            }
        )
    if document_quality_digest:
        priority_items.append(
            {
                "label": "파일 추출",
                "value": (
                    f"{document_quality_digest.get('usable_count', 0)}/"
                    f"{document_quality_digest.get('document_count', 0)}개 활용 가능"
                ),
                "tone": "ok" if document_quality_digest.get("usable_count") else "warning",
                "action": (document_quality_digest.get("latest") or {}).get("next_action") or "파일 추출 품질을 확인하세요.",
            }
        )
    priority_items.extend(
        {
            "label": "다음 액션",
            "value": action,
            "tone": "neutral",
            "action": action,
        }
        for action in recommended_actions[:3]
    )
    today_priority_brief = {
        "status": "success",
        "date": current_storage_date().isoformat(),
        "headline": "오늘 확인할 것",
        "item_count": len(priority_items),
        "items": priority_items[:6],
        "automation_tone": automation_digest.get("tone"),
        "automation_headline": automation_digest.get("headline"),
    }

    module_status = [
        DashboardMetric(
            label="기준 리포트",
            value="있음" if team_report else "필요",
            tone="ok" if team_report else "needs_action",
        ),
        DashboardMetric(
            label="체크리스트",
            value=f"{float(checklist_rate) * 100:.0f}% / {checklist_readiness}"
            if checklist_rate is not None
            else "미작성",
            tone="ok"
            if checklist_rate is not None and float(checklist_rate) >= 0.75
            else "warning",
        ),
        DashboardMetric(
            label="매매 전략",
            value="있음" if trade else "필요",
            tone="ok" if trade else "needs_action",
        ),
        DashboardMetric(
            label="실적 분석",
            value="최신 기준" if earnings_aligned else "갱신 필요" if earnings else "필요",
            tone="ok" if earnings_aligned else "warning",
        ),
        DashboardMetric(
            label="모델 업데이트",
            value="노트 있음" if model_update_note else "작성 필요",
            tone="ok" if model_update_note else "warning",
        ),
        DashboardMetric(
            label="최근 캡처",
            value="있음" if capture else "없음",
            tone="ok" if capture else "neutral",
        ),
        DashboardMetric(
            label="투자 논거",
            value="스냅샷 있음" if latest_thesis_snapshot else "합성 필요",
            tone="ok" if latest_thesis_snapshot else "warning",
        ),
        DashboardMetric(
            label="정책 최적화",
            value="있음" if latest_policy_report else "필요",
            tone="ok" if latest_policy_report else "warning",
        ),
        DashboardMetric(
            label="국민연금 수급",
            value=(
                f"{nps_signal_latest_ratio(nps_signal):.2f}%"
                if nps_signal_latest_ratio(nps_signal) is not None
                else "확인됨"
            )
            if nps_signal_matched(nps_signal)
            else "자료 없음",
            tone="warning"
            if nps_signal_outflow_like(nps_signal)
            else "ok"
            if nps_signal_matched(nps_signal)
            else "neutral",
        ),
        DashboardMetric(
            label="DART 공시",
            value=(
                f"신규 {dart_filing_signal.get('recent_count')}건"
                if dart_filing_signal.get("recent_count")
                else "조회 실패"
                if dart_filing_signal.get("latest_failure")
                else "신규 없음"
            ),
            tone=dart_filing_signal.get("tone") or "neutral",
        ),
    ]
    latest_reports = build_dashboard_latest_reports(sorted_entries, [])
    latest_automation_summary = (
        dashboard_report_summary(model_update_note)
        if model_update_note
        else None
    )
    if latest_policy_report:
        latest_reports.append(dashboard_report_summary(latest_policy_report))
        latest_reports = sorted(
            latest_reports,
            key=lambda item: (item.date, report_file_sequence(item.file_name), item.file_name),
            reverse=True,
        )[:6]

    return TickerDashboardResponse(
        ticker=ticker,
        file_count=len(files),
        verified_report_count=len(entries),
        legacy_report_count=legacy_report_count,
        data_warnings=data_warnings,
        ticker_verification=ticker_verification,
        ticker_profile=ticker_profile,
        report_count_by_type=report_count_by_type,
        latest_reports=latest_reports,
        checklist_completion_rate=checklist_rate,
        checklist_readiness=checklist_readiness,
        latest_thesis_summary=latest_thesis_snapshot.get("thesis_summary")
        or (team_report.get("summary") if team_report else None),
        latest_thesis_snapshot=latest_thesis_snapshot,
        latest_capture_summary=capture.get("summary") if capture else None,
        latest_trade_setup_summary=trade.get("summary") if trade else None,
        latest_earnings_summary=earnings.get("summary") if earnings else None,
        latest_automation_summary=latest_automation_summary,
        latest_earnings_reference=latest_earnings_reference,
        nps_institutional_signal=nps_signal,
        dart_filing_signal=dart_filing_signal,
        latest_customs_trade_reference=latest_customs_trade_reference,
        latest_dossier_preview=latest_dossier_preview,
        latest_market_journal_reference=latest_market_journal_reference,
        document_quality_digest=document_quality_digest,
        today_priority_brief=today_priority_brief,
        automation_digest=automation_digest,
        open_watch_items=unique_watch_items,
        recommended_next_actions=recommended_actions[:6],
        module_status=module_status,
    )


def render_institutional_markdown(
    analysis: InstitutionalAnalysisResponse,
    storage_date: date,
) -> str:
    injected_data = "\n".join(
        f"- {translate_source_type_label(item.source_type)} / {translate_data_label(item.label)}: {item.value}"
        for item in analysis.injected_data
    )
    risks = "\n".join(f"- {risk}" for risk in analysis.key_risks)
    actions = "\n".join(f"- {action}" for action in analysis.next_actions)

    return f"""---
ticker: {analysis.ticker}
type: institutional-stock-breakdown
date: {storage_date.isoformat()}
module: {analysis.module.value}
persona: {analysis.persona}
investment_period: {analysis.investment_period}
---

# {analysis.ticker} 기관급 기업 분석

## 핵심 요약

{analysis.executive_summary}

## 주입된 데이터 컨텍스트

{injected_data}

## 강세 시나리오

{analysis.bull_case.thesis}

추적 항목: {", ".join(analysis.bull_case.watch_items)}

## 기준 시나리오

{analysis.base_case.thesis}

추적 항목: {", ".join(analysis.base_case.watch_items)}

## 약세 시나리오

{analysis.bear_case.thesis}

추적 항목: {", ".join(analysis.bear_case.watch_items)}

## 주요 리스크

{risks}

## 다음 액션

{actions}
"""


def render_smart_trade_markdown(
    setup: SmartTradeSetupResponse,
    storage_date: date,
) -> str:
    def trade_price_text(value: float | None) -> str:
        if value is None:
            return "n/a"
        normalized_ticker = normalize_ticker(setup.ticker)
        if normalized_ticker.isdigit() or normalized_ticker.endswith((".KS", ".KQ")):
            return f"{value:,.0f}원"
        return f"${value:,.2f}"

    injected_data = "\n".join(
        f"- {translate_source_type_label(item.source_type)} / {translate_data_label(item.label)}: {item.value}"
        for item in setup.injected_data
    )
    style_label = translate_trade_style_label(setup.style)
    entries = "\n".join(
        f"- {item.label}: {trade_price_text(item.price)} ({item.rationale})"
        for item in setup.entry_zone
    )
    targets = "\n".join(
        f"- {item.label}: {trade_price_text(item.price)}, 예상 보상 {item.reward_pct:.1%}, 손익비 {item.risk_reward:.2f}:1, 조치: {item.action}"
        for item in setup.targets
    )
    trade_plan = "\n".join(f"- {item}" for item in setup.trade_plan)
    invalidation_conditions = "\n".join(
        f"- {item}" for item in setup.invalidation_conditions
    )
    next_actions = "\n".join(f"- {item}" for item in setup.next_actions)

    return f"""---
ticker: {setup.ticker}
type: smart-trade-setup
date: {storage_date.isoformat()}
module: {setup.module.value}
style: {setup.style}
risk_tolerance: {setup.risk_tolerance}
current_price: {setup.current_price}
---

# {setup.ticker} 스마트 매매 전략

## 요약

- 현재가: {trade_price_text(setup.current_price)}
- 스타일: {style_label}
- 허용 리스크: {setup.risk_tolerance}
- 시장 구조: {setup.market_structure}
- 세팅 품질: {setup.setup_quality}
- 1주당 리스크: {trade_price_text(setup.risk_per_share)}
- 포트폴리오 기준 총액: {f'{setup.portfolio_size:,.0f}원' if setup.portfolio_size else '미입력'}
- 포지션 가이드: {setup.position_sizing_guidance}

## 주입된 데이터 컨텍스트

{injected_data}

## 진입 구간

{entries}

## 손절 기준

- {setup.stop_loss.label}: {trade_price_text(setup.stop_loss.price)} ({setup.stop_loss.rationale})

## 목표가

{targets}

## 실행 계획

{trade_plan}

## 무효화 조건

{invalidation_conditions}

## 다음 액션

{next_actions}
"""


def render_earnings_reaction_markdown(
    reaction: EarningsReactionResponse,
    storage_date: date,
) -> str:
    injected_data = "\n".join(
        f"- {translate_source_type_label(item.source_type)} / {translate_data_label(item.label)}: {item.value}"
        for item in reaction.injected_data
    )
    metrics = "\n".join(
        f"- {item.name}: 발표 {item.reported if item.reported is not None else 'n/a'}, 예상 {item.expected if item.expected is not None else 'n/a'}, 서프라이즈 {item.surprise or 'n/a'} - {item.interpretation}"
        for item in reaction.metrics
    )
    previous_takeaways = "\n".join(
        f"- {item}" for item in reaction.previous_earnings_key_takeaways
    )
    watch_items = "\n".join(
        f"- {item}" for item in reaction.watch_before_next_earnings
    )
    missing_inputs = "\n".join(
        f"- {item}" for item in reaction.missing_inputs
    ) or "- 없음"
    thesis_implications = "\n".join(
        f"- {item}" for item in reaction.thesis_implications
    )
    next_actions = "\n".join(f"- {item}" for item in reaction.next_actions)

    return f"""---
ticker: {reaction.ticker}
type: earnings-reaction
date: {storage_date.isoformat()}
module: {reaction.module.value}
persona: {reaction.persona}
quarter: {reaction.quarter}
reaction_type: {reaction.reaction_type}
sentiment_shift: {reaction.sentiment_shift}
---

# {reaction.ticker} 실적 발표 반응 분석

## 핵심 판단

{reaction.headline_assessment}

- 분기: {reaction.quarter}
- 기준 상태: {reaction.earnings_reference_status}
- 공식 최신 발표 분기: {reaction.official_latest_quarter or '미등록'}
- 공식 최신 발표일: {reaction.official_latest_earnings_report_date or '미등록'}
- 캘린더 출처: {reaction.earnings_calendar_source or '미등록'}
- 실적 발표일: {reaction.earnings_report_date or '미입력'}
- 주가 반응: {reaction.price_reaction}
- 반응 유형: {reaction.reaction_type}
- 센티먼트 변화: {reaction.sentiment_shift}
- 가이던스 평가: {reaction.guidance_assessment}
- 증거 상태: {reaction.evidence_status}

## 보강 필요 입력

{missing_inputs}

## 직전 실적 핵심 내용

- 직전 실적일: {reaction.previous_earnings_date or '미입력'}

{previous_takeaways}

## 다음 실적 가이던스

- 다음 실적 예정일: {reaction.next_earnings_date or '미입력'}

{reaction.next_earnings_guidance}

## 주입된 데이터 컨텍스트

{injected_data}

## 주요 수치

{metrics}

## 시장 반응 패턴

{reaction.market_reaction_pattern}

## 다음 실적 전 확인할 항목

{watch_items}

## 투자 논거 영향

{thesis_implications}

## 다음 액션

{next_actions}
"""


def render_sector_opportunity_markdown(
    report: SectorOpportunityResponse,
    storage_date: date,
) -> str:
    injected_data = "\n".join(
        f"- {translate_source_type_label(item.source_type)} / {translate_data_label(item.label)}: {item.value}"
        for item in report.injected_data
    )
    sectors = "\n\n".join(
        "\n".join(
            [
                f"### {index}. {item.sector} ({item.score}/100)",
                f"- 투자 논거: {item.rationale}",
                f"- 매크로 순풍: {', '.join(item.macro_tailwinds) or '없음'}",
                f"- 주요 리스크: {', '.join(item.key_risks) or '없음'}",
                f"- 선호 티커: {', '.join(item.preferred_tickers) or '없음'}",
            ]
        )
        for index, item in enumerate(report.ranked_sectors, start=1)
    )
    companies = "\n\n".join(
        "\n".join(
            [
                f"### {item.ticker} - {item.company_name} ({item.fit_score}/100)",
                f"- 섹터: {item.sector}",
                f"- 투자 논거: {item.thesis}",
                f"- 촉매: {', '.join(item.catalysts) or '없음'}",
                f"- 리스크: {', '.join(item.risks) or '없음'}",
            ]
        )
        for item in report.recommended_companies
    )
    sector_trends = "\n\n".join(
        "\n".join(
            [
                f"### {index}. {item.sector} - {item.trend_label} ({item.flow_score}/100)",
                f"- 시장 흐름: {item.market_flow}",
                f"- 투자 솔루션: {item.investment_solution}",
                f"- 주도주: {', '.join(item.leader_tickers) or '없음'}",
                f"- 근거: {', '.join(item.evidence) or '없음'}",
                f"- 리스크: {', '.join(item.risks) or '없음'}",
                f"- 체크포인트: {', '.join(item.next_checkpoints) or '없음'}",
            ]
        )
        for index, item in enumerate(report.sector_trends, start=1)
    )
    sector_leaders = "\n\n".join(
        "\n".join(
            [
                f"### {index}. {item.company_name} ({item.ticker}) - {item.leader_score}/100",
                f"- 섹터: {item.sector}",
                f"- 출처: {item.source}",
                f"- 투자 논거: {item.thesis}",
                f"- 촉매: {', '.join(item.catalysts) or '없음'}",
                f"- 리스크: {', '.join(item.risks) or '없음'}",
                f"- 다음 확인: {', '.join(item.next_checkpoints) or '없음'}",
            ]
        )
        for index, item in enumerate(report.sector_leaders, start=1)
    )
    industry_overview = "\n".join(f"- {item}" for item in report.industry_overview)
    competitive_landscape = "\n".join(f"- {item}" for item in report.competitive_landscape)
    peer_comparison = "\n".join(
        f"- {item.company_name} ({item.ticker}) / {item.role} / 적합도 {item.fit_score}/100: "
        f"강점 {', '.join(item.strengths) or '없음'} | 리스크 {', '.join(item.risks) or '없음'}"
        for item in report.peer_comparison
    )
    idea_shortlist = "\n".join(
        f"- {item.company_name} ({item.ticker}) / {item.sector} / 적합도 {item.fit_score}/100: {item.thesis}"
        for item in report.idea_shortlist
    )
    analyst_report = "\n\n".join(f"{index}. {item}" for index, item in enumerate(report.analyst_report, start=1))
    watch_items = "\n".join(f"- {item}" for item in report.watch_items)
    risks = "\n".join(f"- {item}" for item in report.key_risks)
    next_actions = "\n".join(f"- {item}" for item in report.next_actions)

    return f"""---
research_key: {report.research_key}
type: sector-opportunity
date: {storage_date.isoformat()}
module: {report.module.value}
persona: {report.persona}
region: {report.region}
style: {report.style}
period: {report.period}
focus_theme: {report.focus_theme or ""}
---

# {report.region} 섹터 기회 발굴

## 매크로 요약

{report.macro_summary}

## 주입된 데이터 컨텍스트

{injected_data}

## 입력 섹터/테마 심층 분석

### 산업 개요

{industry_overview}

### 경쟁 구도

{competitive_landscape}

### 피어 비교

{peer_comparison}

### 아이디어 숏리스트

{idea_shortlist}

## 유망 섹터 순위

{sectors}

## 후보 기업

{companies}

## 산업군별 동향 분석

{sector_trends}

## 섹터 주도주 보드

{sector_leaders}

## 애널리스트 종합 리포트

{analyst_report}

## 배분 관점

{report.allocation_view}

## 확인할 지표

{watch_items}

## 주요 리스크

{risks}

## 다음 액션

{next_actions}
"""


def render_long_term_compounder_markdown(
    report: LongTermCompounderResponse,
    storage_date: date,
) -> str:
    market_cap_unit = (
        "억원"
        if report.region.upper().startswith(("KR", "KOREA")) or "한국" in report.region
        else "백만 달러"
    )

    def market_cap_text(value: float | None) -> str:
        if value is None:
            return "제한 없음"
        return f"{value:,.0f} {market_cap_unit}"

    injected_data = "\n".join(
        f"- {translate_source_type_label(item.source_type)} / {translate_data_label(item.label)}: {item.value}"
        for item in report.injected_data
    )
    candidates = "\n\n".join(
        "\n".join(
            [
                f"### {index}. {item.ticker} - {item.company_name} ({item.compounder_score}/100)",
                f"- 섹터: {item.sector}",
                f"- 시가총액: {market_cap_text(item.market_cap)}",
                f"- 매출 성장률: {item.revenue_growth:.0%}",
                f"- 매출총이익률: {item.gross_margin:.0%}",
                f"- FCF 마진: {item.free_cash_flow_margin:.0%}",
                f"- 경쟁 우위 점수: {item.moat_score}/100",
                f"- 확장성 점수: {item.scalability_score}/100",
                f"- 투자 논거: {item.thesis}",
                f"- 재투자 활주로: {item.reinvestment_runway}",
                f"- 핵심 리스크: {', '.join(item.key_risks) or '없음'}",
                f"- 추적 KPI: {', '.join(item.watch_kpis) or '없음'}",
            ]
        )
        for index, item in enumerate(report.candidates, start=1)
    )
    rejected_reasons = "\n".join(f"- {item}" for item in report.rejected_reasons)
    portfolio_notes = "\n".join(
        f"- {item}" for item in report.portfolio_construction_notes
    )
    next_actions = "\n".join(f"- {item}" for item in report.next_actions)

    return f"""---
research_key: {report.research_key}
type: long-term-compounder
date: {storage_date.isoformat()}
module: {report.module.value}
persona: {report.persona}
region: {report.region}
sector: {report.sector}
style: {report.style}
---

# 장기 복리 성장주 발굴

## 요약

{report.summary}

## 스크리닝 조건

- 기준: {report.screening_criteria}
- 지역: {report.region}
- 섹터: {report.sector}
- 스타일: {report.style}
- 최소 시가총액: {market_cap_text(report.min_market_cap)}
- 최대 시가총액: {market_cap_text(report.max_market_cap)}

## 주입된 데이터 컨텍스트

{injected_data}

## 후보 기업

{candidates}

## 제외/주의 사유

{rejected_reasons}

## 포트폴리오 구성 메모

{portfolio_notes}

## 다음 액션

{next_actions}
"""


def render_checklist_markdown(
    assessment: ResearchChecklistAssessmentResponse,
    storage_date: date,
) -> str:
    completed = "\n".join(
        f"- [x] {item.label} ({item.key})" for item in assessment.completed_items
    )
    missing = "\n".join(
        f"- [ ] {item.label} ({item.key})" for item in assessment.missing_items
    )
    next_steps = "\n".join(f"- {step}" for step in assessment.next_steps)
    injected_data = "\n".join(
        f"- {translate_source_type_label(item.source_type)} / {translate_data_label(item.label)}: {item.value}"
        for item in assessment.injected_data
    )

    return f"""---
ticker: {assessment.ticker}
type: research-checklist
date: {storage_date.isoformat()}
module: {assessment.module.value}
persona: {assessment.persona}
completion_rate: {assessment.completion_rate}
readiness_level: {assessment.readiness_level}
---

# {assessment.ticker} 리서치 체크리스트 평가

## 투자 준비도

{assessment.readiness_summary}

- 완료 항목: {assessment.completed_count}/{assessment.total_count}
- 완료율: {assessment.completion_rate:.0%}
- 준비도 수준: {assessment.readiness_level}

## 주입된 데이터 컨텍스트

{injected_data}

## 완료된 항목

{completed}

## 미완료 항목

{missing}

## 다음 단계

{next_steps}
"""


def build_skill_contributions(
    ticker: str,
    request: TeamAnalysisRequest,
    injected_data: list[InjectedDataPoint],
) -> list[SkillContribution]:
    data_signal = f"주입 데이터 {len(injected_data)}개 사용 가능"
    focus = analysis_focus_for_ticker(ticker, request.focus_area)
    business_context = ticker_business_context(ticker)
    institutional_context = summarize_institutional_flow_context(injected_data)
    institutional_sentence = (
        f" 기관 수급 보조 근거: {institutional_context}."
        if institutional_context
        else ""
    )

    return [
        SkillContribution(
            skill_id=skill_id,
            skill_name=skill_name,
            persona=persona,
            role=role,
            summary=(
                f"{ticker_company_name(ticker)}({ticker})를 {request.investment_period} 관점에서 분석합니다. "
                f"사업 맥락은 {business_context}이며, 중점 영역은 {focus}입니다. {data_signal}.{institutional_sentence}"
            ),
            key_outputs=[
                f"{skill_name} 관점의 핵심 판단",
                "후속 데이터 수집 시 업데이트할 모니터링 포인트",
                "투자 논거가 틀릴 수 있는 조건",
            ],
            confidence=0.7,
        )
        for skill_id, skill_name, persona, role in COLLABORATIVE_SKILLS
    ]


def summarize_institutional_flow_context(injected_data: list[InjectedDataPoint]) -> str:
    nps_items = [
        item
        for item in injected_data
        if str(item.label).startswith("nps_")
    ]
    if not nps_items:
        return ""
    summaries = []
    for item in nps_items[:3]:
        value = str(item.value).strip()
        if len(value) > 180:
            value = f"{value[:180].rstrip()}..."
        summaries.append(value)
    return " / ".join(summaries)


def nps_signal_matched(signal: dict | None) -> bool:
    if not isinstance(signal, dict):
        return False
    return bool(signal.get("domestic_match_found") or signal.get("large_holding_events"))


def nps_signal_latest_ratio(signal: dict | None) -> float | None:
    if not isinstance(signal, dict):
        return None
    events = signal.get("large_holding_events") or []
    candidates = [
        signal.get("holding_ratio"),
        events[0].get("holding_ratio") if events and isinstance(events[0], dict) else None,
    ]
    for value in candidates:
        try:
            if value is not None:
                return float(value)
        except (TypeError, ValueError):
            continue
    return None


def nps_signal_latest_event_date(signal: dict | None) -> str | None:
    if not isinstance(signal, dict):
        return None
    events = signal.get("large_holding_events") or []
    if events and isinstance(events[0], dict):
        return events[0].get("base_date") or events[0].get("보고서 작성기준일")
    return None


def nps_signal_outflow_like(signal: dict | None) -> bool:
    if not isinstance(signal, dict):
        return False
    text = json.dumps(signal.get("large_holding_events") or [], ensure_ascii=False).lower()
    outflow_terms = ["감소", "매도", "처분", "축소", "하락", "decrease", "sell", "sold", "reduced"]
    return any(term in text for term in outflow_terms)


def nps_signal_decision_note(signal: dict | None, company_name: str | None = None) -> str | None:
    if not nps_signal_matched(signal):
        return None
    label = company_name or (signal or {}).get("company_name") or (signal or {}).get("ticker") or "해당 종목"
    ratio = nps_signal_latest_ratio(signal)
    event_date = nps_signal_latest_event_date(signal)
    ratio_text = f" 지분율 {ratio:.2f}%" if ratio is not None else " 보유/대량보유 신호"
    date_text = f", 기준일 {event_date}" if event_date else ""
    if nps_signal_outflow_like(signal):
        return f"{label} 국민연금{ratio_text}{date_text}: 감소/처분성 표현이 있어 추가매수 전 수급 이탈 여부를 우선 점검하세요."
    return f"{label} 국민연금{ratio_text}{date_text}: 기관 수급 보조 근거로 팀 리포트와 리스크 스캔에 함께 반영하세요."


def estimate_data_quality(injected_data: list[InjectedDataPoint]) -> DataQualitySummary:
    user_supplied_data = [
        item for item in injected_data if source_type_value(item) != "research_memory"
    ]
    has_mock_limitation = any(item.label == "data_provider_limitation" for item in user_supplied_data)
    has_provider_warning = any(str(item.label).endswith("_provider_warning") for item in user_supplied_data)
    if not user_supplied_data:
        return DataQualitySummary(
            data_quality="low",
            source_confidence=0.45,
            stale_data_warning=True,
            missing_data=["최신 가격", "최근 재무 데이터", "실적 가이던스"],
        )

    average_confidence = round(
        sum(item.confidence for item in user_supplied_data) / len(user_supplied_data),
        2,
    )
    has_financial_context = any(
        source_type_value(item)
        in {"financial_data", "earnings_release", "official_filing"}
        for item in user_supplied_data
    )
    has_market_context = any(
        source_type_value(item) in {"market_price", "news", "analyst_report"}
        for item in user_supplied_data
    )
    missing_data = []
    if not has_financial_context:
        missing_data.append("최신 재무 또는 실적 데이터")
    if not has_market_context:
        missing_data.append("최신 시장 가격 또는 뉴스 흐름")
    if has_mock_limitation:
        missing_data.append("실제 시장/재무 데이터")
    if has_provider_warning:
        missing_data.append("FMP 실제 데이터 호출 성공 결과")

    quality = "high" if average_confidence >= 0.8 and not missing_data else "medium"
    if has_mock_limitation or has_provider_warning:
        quality = "low"
    return DataQualitySummary(
        data_quality=quality,
        source_confidence=average_confidence,
        stale_data_warning=has_mock_limitation or has_provider_warning,
        missing_data=missing_data,
    )


def build_team_consensus(
    ticker: str,
    injected_data: list[InjectedDataPoint] | None = None,
) -> list[str]:
    company_name = ticker_company_name(ticker)
    business_context = ticker_business_context(ticker)
    consensus = [
        f"{company_name}({ticker}) 분석은 {business_context}이라는 사업 특성과 가격/리스크 조건을 분리해서 판단해야 합니다.",
        "장기 투자 논거가 강해도 단기 매매 전략은 시장 구조와 포트폴리오 노출에 따라 달라져야 합니다.",
        "새 데이터가 들어올 때마다 강세/기준/약세 가정과 무효화 조건을 다시 비교해야 합니다.",
    ]
    institutional_context = summarize_institutional_flow_context(injected_data or [])
    if institutional_context:
        consensus.append(
            f"기관 수급 참고: {institutional_context} 이 데이터는 단독 매수 근거가 아니라 수급 변화 감시와 리스크 경고 보조 근거로 사용합니다."
        )
    return consensus


def build_team_conflicts(ticker: str) -> list[TeamConflict]:
    company_name = ticker_company_name(ticker)
    return [
        TeamConflict(
            topic="기업 퀄리티와 밸류에이션의 충돌",
            positive_view=f"{company_name}({ticker})의 장기 성장성과 경쟁 우위는 프리미엄 밸류에이션을 일부 정당화할 수 있습니다.",
            caution_view="높은 기대가 이미 가격에 반영되어 있으면 장기 성장이 좋아도 기대수익률이 낮아질 수 있습니다.",
            resolution="밸류에이션 범위를 단일 목표가가 아니라 강세/기준/약세 확률 가중 범위로 관리합니다.",
            severity="high",
        ),
        TeamConflict(
            topic="장기 투자 논거와 단기 진입 조건의 충돌",
            positive_view="복리 성장주 관점에서는 긴 보유 기간과 재투자 기회가 중요합니다.",
            caution_view="매매 전략 관점에서는 실적 발표, 변동성, 손절 위치가 좋지 않으면 진입을 늦춰야 합니다.",
            resolution="장기 관심 종목과 실제 진입 시점을 분리하고, 포지션은 리스크 예산 안에서 단계적으로 구성합니다.",
            severity="medium",
        ),
    ]


def trade_style_parameters(style: str, risk_tolerance: str) -> dict[str, float]:
    style_key = style.strip().lower()
    risk_key = risk_tolerance.strip().lower()
    style_defaults = {
        "scalp": {"entry_pullback": 0.006, "deep_pullback": 0.012, "stop": 0.018},
        "day": {"entry_pullback": 0.01, "deep_pullback": 0.02, "stop": 0.03},
        "swing": {"entry_pullback": 0.025, "deep_pullback": 0.045, "stop": 0.065},
        "position": {"entry_pullback": 0.04, "deep_pullback": 0.075, "stop": 0.105},
    }
    risk_adjustments = {
        "낮음": 0.82,
        "low": 0.82,
        "보통": 1.0,
        "medium": 1.0,
        "높음": 1.18,
        "high": 1.18,
    }
    params = style_defaults.get(style_key, style_defaults["swing"]).copy()
    multiplier = risk_adjustments.get(risk_key, 1.0)
    return {key: value * multiplier for key, value in params.items()}


def infer_market_structure(style: str, injected_data: list[InjectedDataPoint]) -> str:
    context = " ".join(f"{item.label} {item.value}" for item in injected_data).lower()
    if any(word in context for word in ["상향", "강세", "positive", "strong", "상회"]):
        return "상승 추세 우위"
    if any(word in context for word in ["하향", "약세", "negative", "weak", "하회"]):
        return "방어적 조정 구간"
    if style.strip().lower() in {"scalp", "day"}:
        return "단기 변동성 중심"
    return "중립 박스권"


def build_smart_trade_setup(
    ticker: str,
    request: SmartTradeSetupRequest,
    injected_data: list[InjectedDataPoint],
) -> SmartTradeSetupResponse:
    def trade_amount_text(value: float | None) -> str:
        if value is None:
            return "n/a"
        normalized_ticker = normalize_ticker(ticker)
        if normalized_ticker.isdigit() or normalized_ticker.endswith((".KS", ".KQ")):
            return f"{value:,.0f}원"
        return f"${value:,.2f}"

    current_price = round(request.current_price, 2)
    params = trade_style_parameters(request.style, request.risk_tolerance)
    market_structure = request.market_structure or infer_market_structure(
        request.style,
        injected_data,
    )
    entry_primary = round(current_price * (1 - params["entry_pullback"]), 2)
    entry_secondary = round(current_price * (1 - params["deep_pullback"]), 2)
    stop_loss = round(current_price * (1 - params["stop"]), 2)
    average_entry = round((entry_primary + entry_secondary) / 2, 2)
    risk_per_share = round(max(average_entry - stop_loss, 0.01), 2)
    target_multiples = [1.5, 2.2, 3.0]
    targets = []
    for index, multiple in enumerate(target_multiples, start=1):
        target_price = round(average_entry + risk_per_share * multiple, 2)
        targets.append(
            TradeTarget(
                label=f"{index}차 목표가",
                price=target_price,
                reward_pct=round((target_price - average_entry) / average_entry, 4),
                risk_reward=round(multiple, 2),
                action=(
                    "일부 이익 실현 및 손절가를 진입가 근처로 상향"
                    if index == 1
                    else "잔여 포지션 축소 또는 추세 지속 여부 재평가"
                ),
            )
        )

    max_position_value = None
    if request.portfolio_size:
        max_risk_amount = request.portfolio_size * request.risk_per_trade_pct
        max_shares = max_risk_amount / risk_per_share
        max_position_value = round(max_shares * average_entry, 2)
        position_sizing_guidance = (
            f"포트폴리오 {request.portfolio_size:,.0f}원 기준 최대 손실 예산은 "
            f"{max_risk_amount:,.0f}원이며, 평균 진입가 기준 포지션 한도는 약 "
            f"{max_position_value:,.0f}원입니다."
        )
    else:
        position_sizing_guidance = (
            f"평균 진입가 {trade_amount_text(average_entry)}와 손절가 {trade_amount_text(stop_loss)} 기준 "
            f"1주당 리스크는 {trade_amount_text(risk_per_share)}입니다. 계좌 총액을 입력하면 포지션 한도를 자동 계산합니다."
        )

    first_target_rr = targets[0].risk_reward if targets else 0
    setup_quality = "우수" if first_target_rr >= 1.5 else "관찰"
    if "방어적" in market_structure and request.risk_tolerance in {"높음", "high"}:
        setup_quality = "주의"

    return SmartTradeSetupResponse(
        ticker=ticker,
        current_price=current_price,
        style=request.style,
        risk_tolerance=request.risk_tolerance,
        market_structure=market_structure,
        entry_zone=[
            PriceLevel(
                label="1차 진입",
                price=entry_primary,
                rationale="현재가 대비 얕은 눌림 구간에서 분할 진입",
            ),
            PriceLevel(
                label="2차 진입",
                price=entry_secondary,
                rationale="변동성 확대 시 평균 단가 개선을 위한 보수적 추가 진입",
            ),
        ],
        stop_loss=PriceLevel(
            label="손절가",
            price=stop_loss,
            rationale="설정한 스타일과 허용 리스크 기준의 투자 논거 무효화 지점",
        ),
        targets=targets,
        risk_per_share=risk_per_share,
        risk_per_trade_pct=request.risk_per_trade_pct,
        max_position_value=max_position_value,
        portfolio_size=request.portfolio_size,
        position_sizing_guidance=position_sizing_guidance,
        setup_quality=setup_quality,
        trade_plan=[
            "1차 진입 후 가격이 2차 진입 구간까지 내려오면 같은 투자 논거가 유지되는지 먼저 확인",
            "1차 목표가 도달 시 일부 이익을 실현하고 손절가를 평균 진입가 근처로 올려 리스크를 줄임",
            "실적 발표, 가이던스 변경, 시장 급락 전에는 신규 진입보다 포지션 크기 조절을 우선",
        ],
        invalidation_conditions=[
            "손절가를 종가 기준으로 이탈",
            "저장된 투자 논거에서 핵심 성장 또는 마진 가정이 약화로 재분류",
            "포트폴리오 리스크 스캔에서 동일 섹터/테마 노출이 한도를 초과",
        ],
        next_actions=[
            "현재가가 1차 진입 구간에 접근하면 최신 뉴스와 실적 메모를 빠른 정보 저장에 추가",
            "진입 전 포트폴리오 리스크 스캔으로 단일 종목과 섹터 한도를 확인",
            "목표가 도달 또는 손절가 이탈 시 매매일지에 실행 근거를 기록",
        ],
        injected_data=injected_data,
        saved_to_research_memory=request.save_result,
    )


def parse_price_reaction_pct(price_reaction: str) -> float | None:
    match = sub(r"[^0-9+\-.]+", "", price_reaction.strip())
    if not match:
        return None
    try:
        return float(match)
    except ValueError:
        return None


def format_surprise(reported: float | None, expected: float | None) -> str | None:
    if reported is None or expected is None:
        return None
    if expected == 0:
        return "예상치 기준 계산 불가"
    surprise = (reported - expected) / abs(expected)
    direction = "상회" if surprise > 0 else "하회" if surprise < 0 else "부합"
    return f"{direction} {abs(surprise):.1%}"


def assess_metric(
    name: str,
    reported: float | None,
    expected: float | None,
    positive_label: str,
    negative_label: str,
) -> EarningsMetric:
    surprise = format_surprise(reported, expected)
    if reported is None or expected is None:
        interpretation = "입력 수치가 부족해 정량 판정은 보류합니다."
    elif reported > expected:
        interpretation = positive_label
    elif reported < expected:
        interpretation = negative_label
    else:
        interpretation = "시장 기대에 대체로 부합했습니다."
    return EarningsMetric(
        name=name,
        reported=reported,
        expected=expected,
        surprise=surprise,
        interpretation=interpretation,
    )


def assess_guidance_change(value: str) -> str:
    text = value.lower()
    if any(word in text for word in ["상향", "raise", "raised", "up", "개선"]):
        return "가이던스가 상향되어 다음 분기 기대치가 높아질 수 있습니다."
    if any(word in text for word in ["하향", "cut", "lower", "down", "악화"]):
        return "가이던스가 하향되어 멀티플과 실적 추정치 압박을 받을 수 있습니다."
    if any(word in text for word in ["혼합", "mixed"]):
        return "가이던스가 혼재되어 시장은 세부 KPI와 경영진 톤을 더 강하게 볼 가능성이 큽니다."
    return "가이던스는 큰 변화가 없거나 중립적으로 해석됩니다."


def build_previous_earnings_takeaways(request: EarningsReactionRequest) -> list[str]:
    if request.previous_earnings_summary:
        takeaways = [
            item.strip(" -•")
            for item in request.previous_earnings_summary.replace(";", "\n").splitlines()
            if item.strip(" -•")
        ]
        return takeaways[:5]

    return [
        "직전 실적 핵심 내용이 입력되지 않았습니다. 매출 성장, 마진, 가이던스, 수요 코멘트를 보강하세요.",
        "이번 실적과 직전 실적의 방향성이 같은지 비교할 수 있도록 다음 분석 전 직전 분기 요약을 저장하세요.",
    ]


def earnings_context_has_user_input(request: EarningsReactionRequest) -> bool:
    text_fields = [
        request.price_reaction,
        request.management_tone or "",
        request.market_context or "",
        request.previous_earnings_summary or "",
        request.next_earnings_guidance or "",
    ]
    numeric_fields = [
        request.eps_reported,
        request.eps_expected,
        request.revenue_reported,
        request.revenue_expected,
    ]
    return (
        any(field.strip() for field in text_fields)
        or request.guidance_change.strip() not in {"", "유지", "중립", "no change", "unchanged"}
        or any(value is not None for value in numeric_fields)
        or bool(request.key_numbers)
    )


def earnings_request_has_current_evidence(request: EarningsReactionRequest) -> bool:
    current_text_fields = [
        request.price_reaction,
        request.management_tone or "",
        request.market_context or "",
    ]
    numeric_fields = [
        request.eps_reported,
        request.eps_expected,
        request.revenue_reported,
        request.revenue_expected,
    ]
    return (
        any(field.strip() for field in current_text_fields)
        or request.guidance_change.strip() not in {"", "유지", "중립", "no change", "unchanged"}
        or any(value is not None for value in numeric_fields)
        or bool(request.key_numbers)
    )


def current_earnings_signal_text(request: EarningsReactionRequest) -> str:
    key_number_text = " ".join(
        f"{key} {value}" for key, value in request.key_numbers.items()
    )
    return " ".join(
        [
            request.price_reaction,
            request.guidance_change,
            request.management_tone or "",
            request.market_context or "",
            key_number_text,
        ]
    )


def build_next_earnings_guidance(
    request: EarningsReactionRequest,
    guidance_assessment: str,
) -> str:
    if request.next_earnings_guidance:
        return request.next_earnings_guidance
    return (
        "다음 실적 가이던스가 입력되지 않았습니다. 다음 분석에서는 회사가 제시한 매출 가이던스, "
        "마진 범위, 핵심 KPI, 현금흐름 또는 비용 항목을 숫자로 입력하세요."
    )


def earnings_missing_inputs(request: EarningsReactionRequest) -> list[str]:
    missing = []
    if not request.earnings_report_date:
        missing.append("실적 발표일")
    if not request.price_reaction.strip():
        missing.append("발표 후 주가 반응")
    if request.eps_reported is None and request.eps_expected is None:
        missing.append("EPS 발표/예상")
    elif request.eps_reported is None:
        missing.append("EPS 발표")
    elif request.eps_expected is None:
        missing.append("EPS 예상")
    if request.revenue_reported is None and request.revenue_expected is None:
        missing.append("매출 발표/예상")
    elif request.revenue_reported is None:
        missing.append("매출 발표")
    elif request.revenue_expected is None:
        missing.append("매출 예상")
    if not request.management_tone:
        missing.append("경영진 톤")
    if not request.market_context:
        missing.append("시장 맥락")
    if not request.previous_earnings_date:
        missing.append("직전 실적일")
    if not request.previous_earnings_summary:
        missing.append("직전 실적 주요 내용")
    if not request.next_earnings_date:
        missing.append("다음 실적 예정일")
    if not request.next_earnings_guidance:
        missing.append("다음 실적 가이던스")
    return missing


def build_earnings_reaction(
    ticker: str,
    request: EarningsReactionRequest,
    injected_data: list[InjectedDataPoint],
    settings: Settings | None = None,
) -> EarningsReactionResponse:
    company_name = ticker_company_name(ticker)
    watch_kpis = ticker_watch_kpis(ticker)
    profile = official_ticker_profile(ticker, settings, refresh_external=False)
    official_latest_quarter = profile.get("latest_reported_quarter")
    official_latest_earnings_report_date = profile.get("latest_reported_earnings_date")
    earnings_calendar_source = profile.get("earnings_calendar_source")
    earnings_reference_status = (
        "공식 최신 발표 실적 기준"
        if official_latest_quarter
        and normalize_quarter_label(request.quarter)
        == normalize_quarter_label(official_latest_quarter)
        else "사용자 지정 또는 비최신 분기 기준"
    )
    has_context_input = earnings_context_has_user_input(request)
    has_current_evidence = earnings_request_has_current_evidence(request)
    missing_inputs = earnings_missing_inputs(request)
    evidence_status = "충분" if not missing_inputs else "부분 보강 필요"
    if not has_current_evidence:
        evidence_status = "데이터 부족"
    metrics = [
        assess_metric(
            "EPS",
            request.eps_reported,
            request.eps_expected,
            "이익이 예상보다 강해 비용 통제 또는 영업 레버리지 신호로 볼 수 있습니다.",
            "이익이 예상보다 약해 마진, 비용, 일회성 요인을 확인해야 합니다.",
        ),
        assess_metric(
            "매출",
            request.revenue_reported,
            request.revenue_expected,
            "매출이 예상보다 강해 수요와 점유율 가정에 긍정적입니다.",
            "매출이 예상보다 약해 수요 둔화 또는 가격 압박 가능성을 점검해야 합니다.",
        ),
    ]
    for key, value in request.key_numbers.items():
        metrics.append(
            EarningsMetric(
                name=str(key),
                reported=value,
                expected=None,
                surprise=None,
                interpretation="추가 핵심 수치입니다. 다음 실적 전 추세 확인 대상으로 남깁니다.",
            )
        )

    reaction_pct = parse_price_reaction_pct(request.price_reaction)
    guidance_assessment = assess_guidance_change(request.guidance_change)
    evidence_text = current_earnings_signal_text(request)
    has_positive = text_has_any(evidence_text, POSITIVE_SIGNAL_WORDS)
    has_negative = text_has_any(evidence_text, NEGATIVE_SIGNAL_WORDS)

    metric_surprises = [
        metric
        for metric in metrics
        if isinstance(metric.reported, (int, float))
        and isinstance(metric.expected, (int, float))
        and metric.reported != metric.expected
    ]
    beat_count = sum(
        1 for metric in metric_surprises if float(metric.reported) > float(metric.expected)
    )
    miss_count = sum(
        1 for metric in metric_surprises if float(metric.reported) < float(metric.expected)
    )

    if beat_count > miss_count and (reaction_pct is None or reaction_pct >= 0):
        reaction_type = "긍정적 확인"
        sentiment_shift = "개선"
    elif miss_count > beat_count and (reaction_pct is None or reaction_pct <= 0):
        reaction_type = "부정적 재평가"
        sentiment_shift = "악화"
    elif beat_count > miss_count and reaction_pct is not None and reaction_pct < 0:
        reaction_type = "좋은 실적에도 매도"
        sentiment_shift = "혼합"
    elif miss_count > beat_count and reaction_pct is not None and reaction_pct > 0:
        reaction_type = "나쁜 실적에도 매수"
        sentiment_shift = "혼합"
    elif has_positive and has_negative:
        reaction_type = "혼재된 반응"
        sentiment_shift = "혼합"
    elif has_positive:
        reaction_type = "긍정적 확인"
        sentiment_shift = "개선"
    elif has_negative:
        reaction_type = "부정적 재평가"
        sentiment_shift = "악화"
    elif not metric_surprises and reaction_pct is not None and reaction_pct >= 2:
        reaction_type = "주가 긍정 반응, 수치 확인 필요"
        sentiment_shift = "개선 후보"
    elif not metric_surprises and reaction_pct is not None and reaction_pct <= -2:
        reaction_type = "주가 부정 반응, 수치 확인 필요"
        sentiment_shift = "악화 후보"
    else:
        reaction_type = "중립적 소화"
        sentiment_shift = "중립"

    if not has_current_evidence:
        reaction_type = "데이터 부족"
        sentiment_shift = "판정 보류"
        missing_reason = (
            "직전 실적 내용이나 다음 실적 가이던스는 참고 컨텍스트로 저장했지만, "
            "현재 분기의 실제 발표 수치, 주가 반응, 경영진 톤, 시장 맥락, 가이던스 변경 중 "
            "판정에 사용할 증거가 부족합니다."
            if has_context_input
            else "실제 발표일, 주가 반응, 주요 수치, 경영진 코멘트 또는 가이던스를 입력해야 합니다."
        )
        headline_assessment = f"{company_name}({ticker}) {request.quarter} 실적 분석은 입력 데이터가 부족해 판정을 보류합니다. {missing_reason}"
    else:
        headline_assessment = (
            f"{company_name}({ticker}) {request.quarter} 실적은 '{reaction_type}'으로 분류됩니다. "
            f"주가 반응은 {request.price_reaction or '미입력'}이며, 가이던스 평가는 '{guidance_assessment}'입니다."
        )
    market_reaction_pattern = (
        "실적 수치와 주가 반응이 같은 방향으로 움직여 시장이 보고서의 핵심 메시지를 비교적 직접 반영했습니다."
    )
    if not has_current_evidence:
        market_reaction_pattern = (
            "실제 실적 수치와 주가 반응이 입력되지 않아 시장 반응 패턴을 판정하지 않았습니다."
        )
    if reaction_type == "좋은 실적에도 매도":
        market_reaction_pattern = (
            "헤드라인 수치는 좋지만 주가가 약했습니다. 이미 높았던 기대, 밸류에이션 부담, 다음 분기 가이던스 세부 항목을 확인해야 합니다."
        )
    elif reaction_type == "나쁜 실적에도 매수":
        market_reaction_pattern = (
            "헤드라인 수치는 약했지만 주가가 올랐습니다. 낮아진 기대치, 비용 개선 신호, 경영진의 다음 분기 톤이 더 중요했을 수 있습니다."
        )
    elif reaction_type == "혼재된 반응":
        market_reaction_pattern = (
            "수치, 가이던스, 경영진 톤이 엇갈려 시장 반응이 단일 방향으로 정리되지 않았습니다."
        )
    elif reaction_type == "주가 긍정 반응, 수치 확인 필요":
        market_reaction_pattern = (
            "주가는 실적 발표 후 긍정적으로 반응했지만, 매출/EPS/회사별 핵심 KPI가 입력되지 않아 반응의 질은 아직 확인이 필요합니다."
        )
    elif reaction_type == "주가 부정 반응, 수치 확인 필요":
        market_reaction_pattern = (
            "주가는 실적 발표 후 부정적으로 반응했지만, 매출/EPS/회사별 핵심 KPI가 입력되지 않아 약세 요인의 원인은 추가 확인이 필요합니다."
        )

    watch_before_next_earnings = [
        f"다음 실적 예정일({request.next_earnings_date or '미입력'}) 전후의 가이던스 업데이트 확인",
        f"{watch_kpis[0]}이 이번 반응을 확인하는지 추적",
        f"{watch_kpis[1] if len(watch_kpis) > 1 else '마진 품질'}이 가이던스 방향과 일치하는지 확인",
        "실적 후 애널리스트 컨센서스와 목표주가 수정 방향 점검",
        "주가가 실적 발표 갭을 유지하거나 되돌리는지 관찰",
    ]
    if has_current_evidence:
        thesis_implications = [
            "센티먼트가 개선이면 강세 시나리오 확률을 높이되 밸류에이션 재평가를 분리합니다.",
            "센티먼트가 악화이면 기존 투자 논거의 무효화 조건과 포지션 크기를 재검토합니다.",
            "혼합 반응이면 다음 실적 전까지 핵심 KPI 두세 개를 watch item으로 고정합니다.",
        ]
        next_actions = [
            "빠른 정보 저장에 실적 콜 핵심 코멘트와 가이던스 숫자를 추가",
            "팀 리포트를 재실행해 강세/기준/약세 시나리오를 갱신",
            "매매 전략 모듈에서 실적 후 변동성 기준의 진입/손절 구간을 다시 산출",
        ]
    else:
        thesis_implications = [
            "현재 분기 실적 판정은 보류합니다. 기존 투자 논거를 강화하거나 약화하는 증거로 사용하지 마세요.",
            "직전 실적 주요 내용과 다음 실적 가이던스는 다음 분석을 위한 체크포인트로만 연결합니다.",
            f"{company_name}({ticker})의 후속 분석은 {', '.join(watch_kpis[:3])} 입력 후 다시 실행하세요.",
        ]
        next_actions = [
            "현재 분기의 실제 실적 발표일, 주가 반응, 매출/EPS 또는 회사 핵심 KPI 수치를 입력",
            "경영진 콜에서 확인한 계약, 고객 유지율, 마진, 현금흐름 관련 코멘트를 빠른 정보 저장에 추가",
            "입력 보강 후 실적 분석을 재실행해 기존 레거시 결과를 대체",
        ]

    return EarningsReactionResponse(
        ticker=ticker,
        quarter=request.quarter,
        official_latest_quarter=official_latest_quarter,
        official_latest_earnings_report_date=official_latest_earnings_report_date,
        earnings_calendar_source=earnings_calendar_source,
        earnings_reference_status=earnings_reference_status,
        earnings_report_date=request.earnings_report_date,
        price_reaction=request.price_reaction,
        previous_earnings_date=request.previous_earnings_date,
        previous_earnings_key_takeaways=build_previous_earnings_takeaways(request),
        next_earnings_date=request.next_earnings_date,
        next_earnings_guidance=build_next_earnings_guidance(request, guidance_assessment),
        reaction_type=reaction_type,
        headline_assessment=headline_assessment,
        sentiment_shift=sentiment_shift,
        guidance_assessment=guidance_assessment,
        evidence_status=evidence_status,
        missing_inputs=missing_inputs,
        metrics=metrics,
        market_reaction_pattern=market_reaction_pattern,
        watch_before_next_earnings=watch_before_next_earnings,
        thesis_implications=thesis_implications,
        next_actions=next_actions,
        injected_data=injected_data,
        saved_to_research_memory=request.save_result,
    )


SECTOR_COMPANY_UNIVERSE = {
    "US": {
        "반도체/AI 인프라": [
            ("NVDA", "NVIDIA", "AI 가속기와 데이터센터 수요의 직접 수혜"),
            ("AVGO", "Broadcom", "AI 네트워킹과 커스텀 반도체 노출"),
            ("AMD", "Advanced Micro Devices", "AI GPU와 서버 CPU 경쟁 구도 개선"),
        ],
        "소프트웨어/클라우드": [
            ("MSFT", "Microsoft", "클라우드와 AI 소프트웨어 배포력"),
            ("GOOGL", "Alphabet", "AI 검색, 클라우드, 광고 회복 노출"),
            ("NOW", "ServiceNow", "기업 자동화 지출의 질 높은 성장"),
        ],
        "에너지": [
            ("XOM", "Exxon Mobil", "유가와 현금흐름 방어력"),
            ("CVX", "Chevron", "배당과 자사주 매입 기반의 가치 노출"),
            ("SLB", "Schlumberger", "업스트림 투자 사이클 수혜"),
        ],
        "헬스케어": [
            ("LLY", "Eli Lilly", "비만/당뇨 치료제 성장성"),
            ("UNH", "UnitedHealth", "방어적 현금흐름과 헬스케어 서비스"),
            ("ISRG", "Intuitive Surgical", "의료기기 플랫폼 확장성"),
        ],
        "금융": [
            ("JPM", "JPMorgan Chase", "자본력과 예대마진 방어"),
            ("BLK", "BlackRock", "시장 회복 시 운용자산 레버리지"),
            ("V", "Visa", "소비 결제망의 높은 마진"),
        ],
        "산업재/전력 인프라": [
            ("GEV", "GE Vernova", "전력망과 발전 설비 투자 수혜"),
            ("ETN", "Eaton", "전력 관리와 데이터센터 전력 수요"),
            ("CAT", "Caterpillar", "인프라와 에너지 투자 사이클"),
        ],
        "필수소비재/방어": [
            ("COST", "Costco", "회원제 기반 방어적 성장"),
            ("PG", "Procter & Gamble", "가격 결정력과 안정적 현금흐름"),
            ("KO", "Coca-Cola", "글로벌 브랜드와 배당 안정성"),
        ],
    },
    "KR": {
        "반도체/AI 인프라": [
            ("005930.KS", "삼성전자", "메모리 회복과 AI 서버 수요 노출"),
            ("000660.KS", "SK하이닉스", "HBM과 AI 메모리 수혜"),
        ],
        "소프트웨어/클라우드": [
            ("035420.KS", "NAVER", "AI 검색과 커머스 플랫폼"),
            ("035720.KS", "카카오", "플랫폼 구조조정과 비용 효율화"),
        ],
        "에너지": [
            ("096770.KS", "SK이노베이션", "정유/배터리 사이클 노출"),
            ("010950.KS", "S-Oil", "정제마진 민감도"),
        ],
        "헬스케어": [
            ("207940.KS", "삼성바이오로직스", "CDMO 장기 수요"),
            ("068270.KS", "셀트리온", "바이오시밀러 포트폴리오"),
        ],
        "금융": [
            ("055550.KS", "신한지주", "주주환원과 금리 민감도"),
            ("105560.KS", "KB금융", "대형 금융지주 자본력"),
        ],
        "산업재/전력 인프라": [
            ("034020.KS", "두산에너빌리티", "전력/원전 인프라 투자"),
            ("267260.KS", "HD현대일렉트릭", "전력기기 수요"),
        ],
        "필수소비재/방어": [
            ("097950.KS", "CJ제일제당", "식품 방어성과 해외 성장"),
            ("271560.KS", "오리온", "브랜드와 해외 매출"),
        ],
    },
}


def sector_score_rules(macro_text: str, style: str) -> dict[str, int]:
    text = macro_text.lower()
    style_text = style.lower()
    scores = {
        "반도체/AI 인프라": 55,
        "소프트웨어/클라우드": 52,
        "에너지": 48,
        "헬스케어": 50,
        "금융": 47,
        "산업재/전력 인프라": 49,
        "필수소비재/방어": 45,
    }
    if any(word in text for word in ["ai", "인공지능", "반도체", "데이터센터", "gpu"]):
        scores["반도체/AI 인프라"] += 28
        scores["소프트웨어/클라우드"] += 18
        scores["산업재/전력 인프라"] += 13
    if any(word in text for word in ["금리 인하", "rate cut", "완화", "유동성"]):
        scores["소프트웨어/클라우드"] += 15
        scores["반도체/AI 인프라"] += 10
        scores["금융"] += 6
    if any(word in text for word in ["금리 상승", "higher rates", "긴축", "인플레이션"]):
        scores["금융"] += 13
        scores["필수소비재/방어"] += 10
        scores["헬스케어"] += 8
        scores["소프트웨어/클라우드"] -= 6
    if any(word in text for word in ["유가", "oil", "energy", "원유", "가스"]):
        scores["에너지"] += 24
        scores["산업재/전력 인프라"] += 6
    if any(word in text for word in ["방어", "침체", "recession", "둔화", "리스크 오프"]):
        scores["헬스케어"] += 17
        scores["필수소비재/방어"] += 16
        scores["에너지"] += 4
    if any(word in text for word in ["전력", "grid", "인프라", "전력망", "원전"]):
        scores["산업재/전력 인프라"] += 22
        scores["반도체/AI 인프라"] += 5

    if "성장" in style_text or "growth" in style_text:
        scores["반도체/AI 인프라"] += 8
        scores["소프트웨어/클라우드"] += 8
    if "가치" in style_text or "value" in style_text:
        scores["에너지"] += 8
        scores["금융"] += 8
    if "방어" in style_text or "defensive" in style_text:
        scores["헬스케어"] += 8
        scores["필수소비재/방어"] += 8

    return {sector: max(0, min(score, 100)) for sector, score in scores.items()}


def sector_theme_score_boosts(theme_text: str) -> dict[str, int]:
    text = (theme_text or "").lower()
    boosts = {sector: 0 for sector in [
        "반도체/AI 인프라",
        "소프트웨어/클라우드",
        "에너지",
        "헬스케어",
        "금융",
        "산업재/전력 인프라",
        "필수소비재/방어",
    ]}
    if any(word in text for word in ["ai", "인공지능", "반도체", "hbm", "gpu", "데이터센터", "데이터 센터"]):
        boosts["반도체/AI 인프라"] += 22
        boosts["소프트웨어/클라우드"] += 10
        boosts["산업재/전력 인프라"] += 7
    if any(word in text for word in ["전력", "전력기기", "변압", "전선", "원전", "grid", "인프라"]):
        boosts["산업재/전력 인프라"] += 24
        boosts["반도체/AI 인프라"] += 5
    if any(word in text for word in ["우주", "위성", "방산", "항공", "로봇", "evtol"]):
        boosts["산업재/전력 인프라"] += 18
        boosts["소프트웨어/클라우드"] += 5
    if any(word in text for word in ["에너지", "lng", "풍력", "태양광", "기후", "오일", "유가", "가스"]):
        boosts["에너지"] += 22
        boosts["산업재/전력 인프라"] += 6
    if any(word in text for word in ["바이오", "헬스", "제약", "cdmo", "신약", "의료"]):
        boosts["헬스케어"] += 24
    if any(word in text for word in ["금융", "은행", "보험", "증권", "핀테크"]):
        boosts["금융"] += 22
    if any(word in text for word in ["식품", "필수소비", "화장품", "소비재", "수출", "브랜드"]):
        boosts["필수소비재/방어"] += 18
    return boosts


def pick_focus_sector(theme_text: str, ranked_sectors: list[SectorOpportunity]) -> str:
    boosts = sector_theme_score_boosts(theme_text)
    if any(boosts.values()):
        return max(boosts.items(), key=lambda item: item[1])[0]
    return ranked_sectors[0].sector if ranked_sectors else "미분류"


def normalize_sector_trend_bucket(raw_sector: str | None, company_name: str = "", ticker: str = "") -> str:
    text = f"{raw_sector or ''} {company_name or ''} {ticker or ''}".lower()
    if any(word in text for word in ["semiconductor", "반도체", "ai반도체", "gpu", "hbm", "memory"]):
        return "반도체/AI 인프라"
    if any(word in text for word in ["software", "cloud", "platform", "internet", "communication services", "소프트웨어", "클라우드", "플랫폼", "naver", "카카오"]):
        return "소프트웨어/클라우드"
    if any(word in text for word in ["health", "bio", "biotech", "pharma", "헬스", "바이오", "제약", "cdmo"]):
        return "헬스케어"
    if any(word in text for word in ["financial", "bank", "insurance", "금융", "은행", "보험", "증권"]):
        return "금융"
    if any(word in text for word in ["energy", "oil", "lng", "gas", "wind", "solar", "에너지", "정유", "가스", "풍력", "기후"]):
        return "에너지"
    if any(word in text for word in ["power", "grid", "industrial", "machinery", "aerospace", "defense", "전력", "전력기기", "인프라", "산업재", "우주", "방산", "조선"]):
        return "산업재/전력 인프라"
    if any(word in text for word in ["consumer staples", "food", "필수소비", "식품", "삼양", "오리온"]):
        return "필수소비재/방어"
    if "etf" in text or "index" in text or "지수" in text:
        return "ETF/지수"
    return raw_sector or "미분류"


def sector_trend_label(score: int) -> str:
    if score >= 78:
        return "강한 주도"
    if score >= 65:
        return "우위"
    if score >= 52:
        return "중립 이상"
    if score >= 42:
        return "관찰"
    return "약세/후순위"


def sector_solution_for_label(sector: str, label: str) -> str:
    if label in {"강한 주도", "우위"}:
        return f"{sector}는 주도 흐름이 확인됩니다. 대표 주도주는 분할 접근하되, 급등 후 추격보다 실적/수급 확인 구간에서 비중을 늘리는 전략이 적합합니다."
    if label == "중립 이상":
        return f"{sector}는 선택적 접근 구간입니다. 섹터 ETF보다 실적 가시성과 가격 모멘텀이 동시에 있는 개별 주도주만 선별하세요."
    if label == "관찰":
        return f"{sector}는 아직 주도권이 뚜렷하지 않습니다. 시장일지와 리포트에서 수급 전환, 실적 상향, 정책 촉매가 반복 확인될 때 후보군을 좁히세요."
    return f"{sector}는 현재 후순위입니다. 신규 매수보다 기존 보유 리스크 관리와 업황 반전 신호 확인이 먼저입니다."


def sector_default_risks(sector: str) -> list[str]:
    risk_map = {
        "반도체/AI 인프라": ["CAPEX 기대 선반영", "수출 규제와 공급망 리스크", "고객사 투자 속도 둔화"],
        "소프트웨어/클라우드": ["금리 상승 시 멀티플 압박", "AI 투자비 증가에 따른 마진 희석"],
        "헬스케어": ["임상/허가 이벤트 변동성", "약가·규제 리스크"],
        "금융": ["순이자마진 둔화", "부동산·신용 비용 확대"],
        "에너지": ["원자재 가격 급락", "정책/환경 규제 리스크"],
        "산업재/전력 인프라": ["수주 지연", "원가 상승과 환율 변동", "정책 예산 집행 지연"],
        "필수소비재/방어": ["원가 상승", "해외 성장 둔화", "밸류에이션 부담"],
        "ETF/지수": ["구성 종목 쏠림", "환율과 지수 밸류에이션 부담"],
    }
    return risk_map.get(sector, ["거시 환경 변화", "실적 가이던스 하향", "수급 공백"])


def sector_default_checkpoints(sector: str) -> list[str]:
    checkpoint_map = {
        "반도체/AI 인프라": ["AI CAPEX 지속 여부", "HBM/GPU 공급 가격", "주요 고객사 주문 변화"],
        "소프트웨어/클라우드": ["ARR/클라우드 성장률", "AI 제품 매출화 속도", "영업마진 방향"],
        "헬스케어": ["임상/허가 일정", "CDMO 수주", "바이오시밀러 가격 경쟁"],
        "금융": ["순이자마진", "대손비용", "주주환원 정책"],
        "에너지": ["유가/LNG 가격", "정제마진", "풍력·신재생 수주"],
        "산업재/전력 인프라": ["수주잔고", "전력망 투자 계획", "원가와 납기"],
        "필수소비재/방어": ["해외 매출 성장", "마진 방어", "브랜드 가격 결정력"],
        "ETF/지수": ["기초 지수 상대강도", "환율", "구성 종목 집중도"],
    }
    return checkpoint_map.get(sector, ["섹터 상대강도", "실적 전망 변화", "기관/외국인 수급"])


def build_sector_trend_analysis(
    request: SectorOpportunityRequest,
    ranked_sectors: list[SectorOpportunity],
    injected_data: list[InjectedDataPoint],
    settings: Settings,
    vault_dir: Path,
) -> tuple[list[SectorTrendInsight], list[SectorLeaderCandidate], list[str]]:
    ranked_score_map = {item.sector: item.score for item in ranked_sectors}
    sector_data: dict[str, dict] = {}
    manifest_entries = read_manifest(vault_dir)

    def bucket_state(sector: str) -> dict:
        return sector_data.setdefault(
            sector,
            {
                "sector": sector,
                "exposure": 0.0,
                "holding_count": 0,
                "interest_count": 0,
                "memory_count": 0,
                "leaders": [],
                "evidence": [],
                "macro_hits": 0,
            },
        )

    for item in injected_data:
        label_text = f"{item.label} {item.value}"
        sector = normalize_sector_trend_bucket(label_text)
        if sector != "미분류":
            state = bucket_state(sector)
            state["macro_hits"] += 1
            state["evidence"].append(f"주입 데이터: {translate_data_label(item.label)}")

    store = read_portfolio_store(settings)
    for payload in store.get("portfolios", {}).values():
        if not isinstance(payload, dict):
            continue
        try:
            portfolio = sort_and_weight_portfolio(
                SavedPortfolio.model_validate(payload),
                settings,
                refresh_prices=False,
            )
        except Exception:
            continue
        for holding in portfolio.holdings:
            ticker = normalize_ticker(holding.ticker)
            if not ticker or ticker == "CASH":
                continue
            profile = official_ticker_profile(ticker, settings)
            company_name = holding.name or profile.get("company_name") or ticker
            sector = normalize_sector_trend_bucket(holding.sector or profile.get("sector"), company_name, ticker)
            state = bucket_state(sector)
            state["holding_count"] += 1
            state["exposure"] += holding.market_value or 0
            memory_count = sum(
                1
                for entry in manifest_entries
                if normalize_ticker(str(entry.get("ticker") or "")) == ticker
            )
            base_score = 45
            base_score += min(18, memory_count * 3)
            base_score += 12 if (holding.unrealized_return or 0) > 0.2 else 6 if (holding.unrealized_return or 0) > 0 else 0
            base_score += min(12, int((holding.weight or 0) * 100))
            leader_score = max(0, min(100, base_score))
            leader = SectorLeaderCandidate(
                ticker=ticker,
                company_name=company_name,
                sector=sector,
                source=f"보유:{portfolio.portfolio_name}",
                leader_score=leader_score,
                current_price=holding.current_price,
                market_value=holding.market_value,
                unrealized_return=holding.unrealized_return,
                research_memory_count=memory_count,
                thesis=(
                    f"{portfolio.portfolio_name} 보유 종목이며, 저장 리포트 {memory_count}건과 "
                    f"현재 손익률 {round((holding.unrealized_return or 0) * 100, 1)}%를 기준으로 섹터 내 주도 후보로 평가했습니다."
                ),
                catalysts=sector_default_checkpoints(sector)[:2],
                risks=sector_default_risks(sector)[:2],
                next_checkpoints=sector_default_checkpoints(sector),
            )
            state["leaders"].append(leader)
            state["memory_count"] += memory_count
            if memory_count:
                state["evidence"].append(f"{company_name}: 저장 리포트 {memory_count}건")

    interests = read_interest_list(settings)
    for item in interests.get("tickers", []):
        if not isinstance(item, dict):
            continue
        ticker = normalize_ticker(item.get("ticker"))
        if not ticker:
            continue
        profile = official_ticker_profile(ticker, settings)
        company_name = item.get("company_name") or profile.get("company_name") or ticker
        sector = normalize_sector_trend_bucket(item.get("sector") or profile.get("sector"), company_name, ticker)
        state = bucket_state(sector)
        state["interest_count"] += 1
        memory_count = sum(
            1
            for entry in manifest_entries
            if normalize_ticker(str(entry.get("ticker") or "")) == ticker
        )
        state["leaders"].append(
            SectorLeaderCandidate(
                ticker=ticker,
                company_name=company_name,
                sector=sector,
                source="관심종목",
                leader_score=max(45, min(85, 48 + memory_count * 4)),
                research_memory_count=memory_count,
                thesis=f"관심종목으로 등록되어 있으며, 저장 자료 {memory_count}건을 통해 추적 근거를 축적 중입니다.",
                catalysts=sector_default_checkpoints(sector)[:2],
                risks=sector_default_risks(sector)[:2],
                next_checkpoints=sector_default_checkpoints(sector),
            )
        )
        state["memory_count"] += memory_count

    region_key = "KR" if request.region.upper().startswith(("KR", "KOREA", "한국")) else "US"
    for sector, candidates in SECTOR_COMPANY_UNIVERSE.get(region_key, {}).items():
        state = bucket_state(sector)
        for ticker, company_name, thesis in candidates[:2]:
            if any(leader.ticker == ticker for leader in state["leaders"]):
                continue
            state["leaders"].append(
                SectorLeaderCandidate(
                    ticker=ticker,
                    company_name=company_name,
                    sector=sector,
                    source="섹터 기본 유니버스",
                    leader_score=max(45, min(86, ranked_score_map.get(sector, 50))),
                    thesis=thesis,
                    catalysts=sector_default_checkpoints(sector)[:2],
                    risks=sector_default_risks(sector)[:2],
                    next_checkpoints=sector_default_checkpoints(sector),
                )
            )

    trends: list[SectorTrendInsight] = []
    all_leaders: list[SectorLeaderCandidate] = []
    for sector, state in sector_data.items():
        base_score = ranked_score_map.get(sector, 45)
        flow_score = base_score
        flow_score += min(10, state["holding_count"] * 2)
        flow_score += min(8, state["interest_count"] * 2)
        flow_score += min(10, state["memory_count"])
        flow_score += min(8, state["macro_hits"] * 2)
        flow_score = max(0, min(100, flow_score))
        deduped_leaders: dict[str, SectorLeaderCandidate] = {}
        for leader in state["leaders"]:
            key = normalize_ticker(leader.ticker)
            existing = deduped_leaders.get(key)
            if existing is None:
                deduped_leaders[key] = leader
                continue
            merged_source = ", ".join(
                dict.fromkeys(
                    [part.strip() for part in f"{existing.source}, {leader.source}".split(",") if part.strip()]
                )
            )
            better = leader if (
                leader.leader_score,
                leader.market_value or 0,
                leader.research_memory_count,
            ) > (
                existing.leader_score,
                existing.market_value or 0,
                existing.research_memory_count,
            ) else existing
            deduped_leaders[key] = better.model_copy(update={"source": merged_source})

        leaders = sorted(
            deduped_leaders.values(),
            key=lambda item: (
                item.leader_score,
                item.market_value or 0,
                item.research_memory_count,
            ),
            reverse=True,
        )[:4]
        label = sector_trend_label(flow_score)
        evidence = list(dict.fromkeys(state["evidence"]))[:5]
        if state["holding_count"]:
            evidence.insert(0, f"보유 종목 {state['holding_count']}개, 평가금액 {round(state['exposure'], 0):,.0f}원 노출")
        if state["interest_count"]:
            evidence.append(f"관심종목 {state['interest_count']}개 연결")
        if not evidence:
            evidence = ["매크로 입력과 기본 섹터 유니버스를 기준으로 평가"]
        trends.append(
            SectorTrendInsight(
                sector=sector,
                flow_score=flow_score,
                trend_label=label,
                market_flow=(
                    f"{sector}는 현재 {label} 흐름입니다. 매크로 점수, 보유/관심 종목 연결, "
                    f"저장 리포트 빈도를 함께 반영했습니다."
                ),
                investment_solution=sector_solution_for_label(sector, label),
                leader_tickers=[leader.ticker for leader in leaders],
                leader_companies=leaders,
                evidence=evidence,
                risks=sector_default_risks(sector),
                next_checkpoints=sector_default_checkpoints(sector),
            )
        )
        all_leaders.extend(leaders)

    trends.sort(key=lambda item: item.flow_score, reverse=True)
    all_leaders.sort(key=lambda item: item.leader_score, reverse=True)
    top_trends = trends[:7]
    top_leaders = all_leaders[:12]
    if top_trends:
        lead = top_trends[0]
        report_sections = [
            f"{request.region} 시장의 {request.period} 섹터 판도는 {lead.sector}가 가장 앞서 있습니다. 점수는 {lead.flow_score}/100이며, {lead.market_flow}",
            "섹터 접근은 지수 전체 매수보다 주도 섹터 안에서 실적·수급·가격 모멘텀이 동시에 확인되는 종목을 선별하는 방식이 적합합니다.",
            "보유 종목이 이미 많은 섹터는 추가 매수보다 리스크 한도와 목표주가 근접도를 먼저 확인하고, 관심섹터는 시장일지와 리포트 누적 신호가 반복될 때 후보를 좁히세요.",
        ]
    else:
        report_sections = [
            "섹터 동향을 판단할 충분한 보유/관심/저장 데이터가 아직 부족합니다.",
            "시장일지와 정보입력에 섹터 전망 자료를 더 저장하면 주도 섹터와 후보 종목 판정이 정교해집니다.",
        ]
    return top_trends, top_leaders, report_sections


def build_sector_theme_deep_dive(
    request: SectorOpportunityRequest,
    ranked_sectors: list[SectorOpportunity],
    recommended_companies: list[SectorCompanyCandidate],
    sector_leaders: list[SectorLeaderCandidate],
) -> tuple[list[str], list[str], list[SectorPeerComparison], list[SectorCompanyCandidate]]:
    focus_theme = (request.focus_theme or "").strip()
    focus_sector = pick_focus_sector(focus_theme, ranked_sectors)
    theme_label = focus_theme or focus_sector
    matched_candidates = [
        item for item in recommended_companies
        if item.sector == focus_sector or theme_label.lower() in f"{item.sector} {item.company_name} {item.thesis}".lower()
    ]
    matched_leaders = [
        item for item in sector_leaders
        if item.sector == focus_sector or theme_label.lower() in f"{item.sector} {item.company_name} {item.thesis}".lower()
    ]
    if not matched_candidates:
        region_key = "KR" if request.region.upper().startswith(("KR", "KOREA", "한국")) else "US"
        for ticker, company_name, thesis in SECTOR_COMPANY_UNIVERSE.get(region_key, {}).get(focus_sector, [])[:4]:
            matched_candidates.append(
                SectorCompanyCandidate(
                    ticker=ticker,
                    company_name=company_name,
                    sector=focus_sector,
                    thesis=thesis,
                    catalysts=sector_default_checkpoints(focus_sector)[:2],
                    risks=sector_default_risks(focus_sector)[:2],
                    fit_score=72,
                )
            )
    scored_sector = next((item for item in ranked_sectors if item.sector == focus_sector), None)
    industry_overview = [
        f"입력 테마 '{theme_label}'는 현재 {focus_sector}로 분류해 분석했습니다. {request.period} 관점에서는 수요 지속성, 실적 가시성, 수급 모멘텀을 함께 확인해야 합니다.",
        f"현재 매크로 입력은 '{request.macro_environment}'입니다. 이 환경에서는 금리, 정책, CAPEX, 원자재 가격 변화가 테마의 밸류에이션과 주문 흐름을 동시에 흔들 수 있습니다.",
        f"섹터 상대 점수는 {scored_sector.score if scored_sector else '미산정'}/100입니다. 점수는 매크로 문구, 스타일, 보유/관심 데이터, 저장 리포트 흐름을 조합해 계산했습니다.",
    ]
    competitive_landscape = [
        "경쟁 구도는 기술/원가/고객 접근성/공급망 안정성/규제 대응력으로 나누어 봐야 합니다.",
        "상위 기업은 수주잔고, 반복 매출, 고객 락인, 제품 전환 비용 중 하나 이상에서 우위를 보여야 합니다.",
        "후발 기업은 성장률이 높더라도 현금 소진, 마진 악화, 단일 고객 의존도가 커지면 테마 노출이 투자 논거로 바로 이어지기 어렵습니다.",
    ]
    peer_pool: list[SectorPeerComparison] = []
    seen: set[str] = set()
    for candidate in matched_candidates:
        ticker = normalize_ticker(candidate.ticker)
        if ticker in seen:
            continue
        seen.add(ticker)
        peer_pool.append(
            SectorPeerComparison(
                ticker=candidate.ticker,
                company_name=candidate.company_name,
                sector=candidate.sector,
                role="핵심 후보",
                strengths=[candidate.thesis, *candidate.catalysts[:1]],
                risks=candidate.risks[:2],
                fit_score=candidate.fit_score,
            )
        )
    for leader in matched_leaders:
        ticker = normalize_ticker(leader.ticker)
        if ticker in seen:
            continue
        seen.add(ticker)
        peer_pool.append(
            SectorPeerComparison(
                ticker=leader.ticker,
                company_name=leader.company_name,
                sector=leader.sector,
                role=leader.source,
                strengths=[leader.thesis, *leader.catalysts[:1]],
                risks=leader.risks[:2],
                fit_score=leader.leader_score,
            )
        )
    peer_pool = sorted(peer_pool, key=lambda item: item.fit_score, reverse=True)[:8]
    idea_shortlist = sorted(matched_candidates, key=lambda item: item.fit_score, reverse=True)[:5]
    return industry_overview, competitive_landscape, peer_pool, idea_shortlist


def build_sector_opportunity_report(
    request: SectorOpportunityRequest,
    injected_data: list[InjectedDataPoint],
    settings: Settings,
    vault_dir: Path,
) -> SectorOpportunityResponse:
    research_key = sector_research_key(request.region, request.style)
    macro_text = " ".join(
        [
            request.macro_environment,
            request.focus_theme or "",
            request.period,
            request.region,
            request.style,
            *[f"{item.label} {item.value}" for item in injected_data],
        ]
    )
    scores = sector_score_rules(macro_text, request.style)
    for sector, boost in sector_theme_score_boosts(request.focus_theme or "").items():
        scores[sector] = max(0, min(100, scores.get(sector, 0) + boost))
    region_key = "KR" if request.region.upper().startswith(("KR", "KOREA", "한국")) else "US"
    universe = SECTOR_COMPANY_UNIVERSE.get(region_key, SECTOR_COMPANY_UNIVERSE["US"])
    ranked_sectors = []
    for sector, score in sorted(scores.items(), key=lambda item: item[1], reverse=True):
        macro_tailwinds = []
        if sector == "반도체/AI 인프라":
            macro_tailwinds = ["AI 투자 사이클", "데이터센터 증설", "고성능 컴퓨팅 수요"]
        elif sector == "소프트웨어/클라우드":
            macro_tailwinds = ["기업 자동화", "클라우드 전환", "금리 완화 시 장기 성장주 재평가"]
        elif sector == "에너지":
            macro_tailwinds = ["유가 민감도", "현금흐름과 주주환원", "공급 제약"]
        elif sector == "헬스케어":
            macro_tailwinds = ["방어적 수요", "혁신 의약품", "경기 둔화 내성"]
        elif sector == "금융":
            macro_tailwinds = ["금리 레벨", "자본시장 회복", "주주환원"]
        elif sector == "산업재/전력 인프라":
            macro_tailwinds = ["전력망 투자", "데이터센터 전력 수요", "인프라 사이클"]
        else:
            macro_tailwinds = ["가격 결정력", "방어적 수요", "현금흐름 안정성"]
        ranked_sectors.append(
            SectorOpportunity(
                sector=sector,
                score=score,
                rationale=(
                    f"{request.macro_environment} 환경에서 {request.period} 동안 "
                    f"{sector}는 상대 점수 {score}/100으로 평가됩니다."
                ),
                macro_tailwinds=macro_tailwinds,
                key_risks=[
                    "기대가 이미 가격에 반영되어 있을 가능성",
                    "금리, 원자재, 실적 가이던스 변화에 따른 로테이션",
                ],
                preferred_tickers=[ticker for ticker, _, _ in universe.get(sector, [])],
            )
        )

    recommended_companies = []
    for sector in ranked_sectors[:3]:
        for ticker, company_name, thesis in universe.get(sector.sector, [])[:2]:
            recommended_companies.append(
                SectorCompanyCandidate(
                    ticker=ticker,
                    company_name=company_name,
                    sector=sector.sector,
                    thesis=thesis,
                    catalysts=sector.macro_tailwinds[:2],
                    risks=sector.key_risks,
                    fit_score=max(0, min(100, sector.score - len(recommended_companies) % 2 * 3)),
                )
            )

    sector_trends, sector_leaders, analyst_report = build_sector_trend_analysis(
        request=request,
        ranked_sectors=ranked_sectors,
        injected_data=injected_data,
        settings=settings,
        vault_dir=vault_dir,
    )
    industry_overview, competitive_landscape, peer_comparison, idea_shortlist = build_sector_theme_deep_dive(
        request=request,
        ranked_sectors=ranked_sectors,
        recommended_companies=recommended_companies,
        sector_leaders=sector_leaders,
    )
    top_sector_names = ", ".join(item.sector for item in ranked_sectors[:3])
    theme_sentence = f" 입력 테마는 '{request.focus_theme}'이며," if request.focus_theme else ""
    macro_summary = (
        f"{request.region} 시장에서 {request.period} 기준 유망 섹터는 {top_sector_names}입니다.{theme_sentence} "
        f"입력한 매크로 환경은 '{request.macro_environment}'이며, 스타일은 {request.style}입니다."
    )
    allocation_view = (
        f"핵심 비중은 1순위 섹터에 두되, 2~3순위 섹터로 촉매와 리스크를 분산하는 구성이 적합합니다. "
        f"개별 종목은 포트폴리오 리스크 스캔의 단일 종목/섹터 한도 안에서만 편입하세요."
    )
    watch_items = [
        "10년물 금리와 실질금리 방향",
        "실적 가이던스 상향/하향 비율",
        "섹터 ETF 상대강도와 자금 유입",
        "유가, 전력 가격, AI CAPEX 관련 뉴스",
    ]
    key_risks = [
        "매크로 내러티브가 빠르게 바뀌면 섹터 로테이션이 반대로 움직일 수 있습니다.",
        "상위 섹터 후보가 기존 포트폴리오와 높은 상관관계를 가질 수 있습니다.",
        "후보 기업은 섹터 매력도와 별도로 밸류에이션과 실적 품질 검증이 필요합니다.",
    ]
    next_actions = [
        "1순위 섹터의 대표 후보에 대해 팀 리포트를 실행",
        "후보 기업을 포트폴리오 리스크 스캔에 넣어 집중도 변화를 확인",
        "매크로 환경이 바뀌면 같은 입력 구조로 섹터 스캔을 재실행",
    ]

    return SectorOpportunityResponse(
        research_key=research_key,
        macro_environment=request.macro_environment,
        period=request.period,
        region=request.region,
        style=request.style,
        focus_theme=request.focus_theme,
        macro_summary=macro_summary,
        industry_overview=industry_overview,
        competitive_landscape=competitive_landscape,
        peer_comparison=peer_comparison,
        idea_shortlist=idea_shortlist,
        ranked_sectors=ranked_sectors[:5],
        recommended_companies=recommended_companies,
        sector_trends=sector_trends,
        sector_leaders=sector_leaders,
        analyst_report=analyst_report,
        allocation_view=allocation_view,
        watch_items=watch_items,
        key_risks=key_risks,
        next_actions=next_actions,
        injected_data=injected_data,
        saved_to_research_memory=request.save_result,
    )


COMPOUNDER_UNIVERSE = [
    {
        "ticker": "MSFT",
        "company_name": "Microsoft",
        "region": "US",
        "sector": "기술",
        "market_cap": 3100000,
        "revenue_growth": 0.15,
        "gross_margin": 0.69,
        "free_cash_flow_margin": 0.30,
        "moat_score": 93,
        "scalability_score": 95,
        "thesis": "클라우드, AI, 오피스 생태계가 높은 전환 비용과 반복 매출을 만듭니다.",
    },
    {
        "ticker": "NVDA",
        "company_name": "NVIDIA",
        "region": "US",
        "sector": "기술",
        "market_cap": 2800000,
        "revenue_growth": 0.42,
        "gross_margin": 0.74,
        "free_cash_flow_margin": 0.36,
        "moat_score": 91,
        "scalability_score": 96,
        "thesis": "AI 가속기 생태계와 소프트웨어 락인이 장기 수요를 뒷받침합니다.",
    },
    {
        "ticker": "GOOGL",
        "company_name": "Alphabet",
        "region": "US",
        "sector": "기술",
        "market_cap": 2100000,
        "revenue_growth": 0.12,
        "gross_margin": 0.57,
        "free_cash_flow_margin": 0.24,
        "moat_score": 88,
        "scalability_score": 90,
        "thesis": "검색, 유튜브, 클라우드, AI 인프라가 현금흐름과 옵션 가치를 함께 제공합니다.",
    },
    {
        "ticker": "META",
        "company_name": "Meta Platforms",
        "region": "US",
        "sector": "기술",
        "market_cap": 1500000,
        "revenue_growth": 0.18,
        "gross_margin": 0.81,
        "free_cash_flow_margin": 0.28,
        "moat_score": 84,
        "scalability_score": 90,
        "thesis": "글로벌 소셜 그래프와 광고 효율성이 높은 영업 레버리지를 만듭니다.",
    },
    {
        "ticker": "LLY",
        "company_name": "Eli Lilly",
        "region": "US",
        "sector": "헬스케어",
        "market_cap": 780000,
        "revenue_growth": 0.24,
        "gross_margin": 0.80,
        "free_cash_flow_margin": 0.18,
        "moat_score": 86,
        "scalability_score": 83,
        "thesis": "비만/당뇨 치료제 포트폴리오가 긴 재투자 활주로를 제공합니다.",
    },
    {
        "ticker": "COST",
        "company_name": "Costco",
        "region": "US",
        "sector": "소비재",
        "market_cap": 420000,
        "revenue_growth": 0.08,
        "gross_margin": 0.13,
        "free_cash_flow_margin": 0.04,
        "moat_score": 87,
        "scalability_score": 78,
        "thesis": "회원제 모델과 낮은 가격 신뢰가 장기 고객 유지율을 높입니다.",
    },
    {
        "ticker": "V",
        "company_name": "Visa",
        "region": "US",
        "sector": "금융",
        "market_cap": 570000,
        "revenue_growth": 0.10,
        "gross_margin": 0.98,
        "free_cash_flow_margin": 0.55,
        "moat_score": 92,
        "scalability_score": 88,
        "thesis": "글로벌 결제 네트워크가 높은 마진과 자본 경량 모델을 유지합니다.",
    },
    {
        "ticker": "ASML",
        "company_name": "ASML Holding",
        "region": "US",
        "sector": "기술",
        "market_cap": 390000,
        "revenue_growth": 0.11,
        "gross_margin": 0.51,
        "free_cash_flow_margin": 0.20,
        "moat_score": 95,
        "scalability_score": 82,
        "thesis": "EUV 노광장비 독점적 지위가 반도체 미세화 사이클의 병목 자산입니다.",
    },
    {
        "ticker": "005930.KS",
        "company_name": "삼성전자",
        "region": "KR",
        "sector": "기술",
        "market_cap": 430000,
        "revenue_growth": 0.08,
        "gross_margin": 0.37,
        "free_cash_flow_margin": 0.12,
        "moat_score": 78,
        "scalability_score": 80,
        "thesis": "메모리, 파운드리, 디바이스 생태계가 사이클 회복 시 복합 레버리지를 만듭니다.",
    },
    {
        "ticker": "000660.KS",
        "company_name": "SK하이닉스",
        "region": "KR",
        "sector": "기술",
        "market_cap": 160000,
        "revenue_growth": 0.26,
        "gross_margin": 0.45,
        "free_cash_flow_margin": 0.10,
        "moat_score": 82,
        "scalability_score": 83,
        "thesis": "HBM 경쟁력이 AI 메모리 수요의 직접 수혜로 이어질 수 있습니다.",
    },
    {
        "ticker": "207940.KS",
        "company_name": "삼성바이오로직스",
        "region": "KR",
        "sector": "헬스케어",
        "market_cap": 65000,
        "revenue_growth": 0.18,
        "gross_margin": 0.43,
        "free_cash_flow_margin": 0.16,
        "moat_score": 84,
        "scalability_score": 79,
        "thesis": "CDMO 생산 역량과 장기 계약 구조가 안정적 성장성을 제공합니다.",
    },
]


def compounder_score(item: dict, criteria: str, style: str) -> int:
    score = 0
    score += min(item["revenue_growth"] / 0.25, 1.0) * 24
    score += min(item["gross_margin"] / 0.70, 1.0) * 18
    score += min(item["free_cash_flow_margin"] / 0.25, 1.0) * 20
    score += item["moat_score"] * 0.16
    score += item["scalability_score"] * 0.14
    text = f"{criteria} {style}".lower()
    if any(word in text for word in ["high growth", "고성장", "매출 성장", "revenue growth"]):
        score += min(item["revenue_growth"] * 16, 6)
    if any(word in text for word in ["margin", "마진", "quality", "퀄리티"]):
        score += min(item["gross_margin"] * 4 + item["free_cash_flow_margin"] * 6, 7)
    if any(word in text for word in ["moat", "경쟁 우위", "durable", "지속"]):
        score += item["moat_score"] * 0.04
    return round(max(0, min(score, 100)))


def passes_market_cap_filter(
    item: dict,
    min_market_cap: float | None,
    max_market_cap: float | None,
) -> bool:
    if min_market_cap is not None and item["market_cap"] < min_market_cap:
        return False
    if max_market_cap is not None and item["market_cap"] > max_market_cap:
        return False
    return True


def build_long_term_compounder_report(
    request: LongTermCompounderRequest,
    injected_data: list[InjectedDataPoint],
) -> LongTermCompounderResponse:
    research_key = compounder_research_key(request.region, request.sector, request.style)
    region_key = "KR" if request.region.upper().startswith(("KR", "KOREA", "한국")) else "US"
    sector_filter = request.sector.strip()
    candidates = []
    rejected_reasons = []

    for item in COMPOUNDER_UNIVERSE:
        if item["region"] != region_key:
            continue
        if sector_filter not in {"전체", "all", "ALL"} and item["sector"] != sector_filter:
            continue
        if not passes_market_cap_filter(
            item,
            request.min_market_cap,
            request.max_market_cap,
        ):
            rejected_reasons.append(
                f"{item['ticker']}는 시가총액 조건에 맞지 않아 제외했습니다."
            )
            continue
        score = compounder_score(item, request.screening_criteria, request.style)
        if score < 68:
            rejected_reasons.append(
                f"{item['ticker']}는 복리 성장 점수 {score}/100으로 기준선 68점을 넘지 못했습니다."
            )
            continue
        candidates.append(
            CompounderCandidate(
                ticker=item["ticker"],
                company_name=item["company_name"],
                sector=item["sector"],
                market_cap=item["market_cap"],
                revenue_growth=item["revenue_growth"],
                gross_margin=item["gross_margin"],
                free_cash_flow_margin=item["free_cash_flow_margin"],
                moat_score=item["moat_score"],
                scalability_score=item["scalability_score"],
                compounder_score=score,
                thesis=item["thesis"],
                reinvestment_runway=(
                    "핵심 시장 침투율, 신제품 확장, 가격 결정력 또는 플랫폼 번들링을 통해 장기 재투자 여지가 있습니다."
                ),
                key_risks=[
                    "높은 밸류에이션이 미래 수익률을 낮출 수 있음",
                    "성장률 둔화 또는 마진 압박이 복리 논거를 약화할 수 있음",
                    "규제, 기술 변화, 경쟁 심화가 경쟁 우위를 훼손할 수 있음",
                ],
                watch_kpis=[
                    "매출 성장률",
                    "매출총이익률",
                    "잉여현금흐름 마진",
                    "재투자 수익률",
                    "고객 유지율 또는 시장 점유율",
                ],
            )
        )

    candidates = sorted(
        candidates,
        key=lambda item: item.compounder_score,
        reverse=True,
    )[:8]
    if not rejected_reasons:
        rejected_reasons = [
            "현재 입력 조건에서는 정량 기준으로 제외된 주요 후보가 없습니다."
        ]
    if candidates:
        top_names = ", ".join(f"{item.ticker}({item.compounder_score}/100)" for item in candidates[:3])
        summary = (
            f"{request.region} {request.sector} 범위에서 {request.style} 기준 장기 복리 후보는 "
            f"{top_names} 순으로 선별되었습니다."
        )
    else:
        summary = (
            "현재 입력 조건을 통과한 복리 성장주 후보가 없습니다. 시가총액 범위나 섹터 조건을 넓혀 다시 실행하세요."
        )
    portfolio_construction_notes = [
        "복리 성장주는 매수 가격보다 보유 기간과 논거 유지 여부가 중요하므로 분할 진입과 정기 점검을 결합하세요.",
        "상위 후보가 같은 섹터에 몰리면 포트폴리오 리스크 스캔으로 상관 노출을 확인하세요.",
        "후보별 팀 리포트와 리서치 체크리스트를 실행해 정량 점수 뒤의 사업 품질을 검증하세요.",
    ]
    next_actions = [
        "1순위 후보에 대해 기관급 분석 또는 7개 스킬 팀 리포트를 실행",
        "실적 발표 전후로 매출 성장률, 마진, FCF 마진이 유지되는지 실적 분석 모듈로 확인",
        "매수 전 체크리스트 완료율을 75% 이상으로 끌어올린 뒤 매매 전략을 설계",
    ]

    return LongTermCompounderResponse(
        research_key=research_key,
        screening_criteria=request.screening_criteria,
        min_market_cap=request.min_market_cap,
        max_market_cap=request.max_market_cap,
        sector=request.sector,
        region=request.region,
        style=request.style,
        summary=summary,
        candidates=candidates,
        rejected_reasons=rejected_reasons[:8],
        portfolio_construction_notes=portfolio_construction_notes,
        next_actions=next_actions,
        injected_data=injected_data,
        saved_to_research_memory=request.save_result,
    )


def build_investment_thesis(
    ticker: str,
    request: TeamAnalysisRequest,
    storage_date: date,
) -> InvestmentThesis:
    focus = analysis_focus_for_ticker(ticker, request.focus_area)
    company_name = ticker_company_name(ticker)
    return InvestmentThesis(
        ticker=ticker,
        thesis=f"{company_name}({ticker})의 투자 논거는 {focus}가 지속적으로 확인되는지에 달려 있습니다.",
        time_horizon=request.investment_period,
        bull_triggers=[
            "성장률 또는 가이던스가 시장 기대를 상회",
            "마진 또는 현금흐름 품질이 유지",
            "섹터 자금 흐름과 밸류에이션 프리미엄이 개선",
        ],
        bear_triggers=[
            "핵심 매출 동력 둔화",
            "마진 압박 또는 경쟁 심화",
            "금리 상승이나 리스크 오프로 멀티플 압축",
        ],
        invalidation_conditions=[
            "핵심 성장 KPI가 2개 분기 연속 약화",
            "경쟁 우위 훼손을 보여주는 가격 인하 또는 점유율 하락 발생",
            "포트폴리오 리스크 예산을 초과할 정도로 상관 노출이 커짐",
        ],
        watch_kpis=ticker_watch_kpis(ticker),
        valuation_assumptions={
            "method": "시나리오 기반 밸류에이션 범위",
            "bear": "성장 둔화와 멀티플 압축",
            "base": "컨센서스 수준 성장과 안정적인 마진",
            "bull": "성장 가속과 프리미엄 멀티플 유지",
        },
        last_updated=storage_date.isoformat(),
    )


def build_watch_items(ticker: str) -> list[WatchItem]:
    watch_kpis = ticker_watch_kpis(ticker)
    return [
        WatchItem(
            ticker=ticker,
            metric=watch_kpis[0],
            condition="기준 시나리오의 성장 가정을 하회",
            action="기준/강세 시나리오를 재검토",
            priority="high",
        ),
        WatchItem(
            ticker=ticker,
            metric=watch_kpis[1] if len(watch_kpis) > 1 else "마진 품질",
            condition="이전 가이던스 또는 경쟁사 추세보다 악화",
            action="밸류에이션 가정을 업데이트",
            priority="high",
        ),
        WatchItem(
            ticker=ticker,
            metric=watch_kpis[2] if len(watch_kpis) > 2 else "포트폴리오 노출",
            condition="섹터 또는 팩터 노출이 리스크 예산 초과",
            action="포지션 크기를 줄이거나 신규 진입을 보류",
            priority="medium",
        ),
    ]


POSITIVE_SIGNAL_WORDS = {
    "above",
    "beat",
    "beats",
    "raise",
    "raised",
    "strong",
    "constructive",
    "accelerate",
    "accelerated",
    "growth",
    "margin expansion",
    "positive",
    "상회",
    "강세",
    "상향",
    "개선",
    "성장",
}


NEGATIVE_SIGNAL_WORDS = {
    "below",
    "miss",
    "misses",
    "cut",
    "lowered",
    "weak",
    "decelerate",
    "decline",
    "pressure",
    "negative",
    "risk",
    "하회",
    "약세",
    "하향",
    "둔화",
    "악화",
    "압박",
}


def text_has_any(text: str, words: set[str]) -> bool:
    lowered = text.lower()
    return any(word.lower() in lowered for word in words)


def translate_impact_label(impact: ThesisImpact) -> str:
    labels = {
        ThesisImpact.STRENGTHENS: "강화",
        ThesisImpact.WEAKENS: "약화",
        ThesisImpact.MIXED: "혼합",
        ThesisImpact.NEUTRAL: "중립",
        ThesisImpact.INSUFFICIENT_DATA: "데이터 부족",
    }
    return labels.get(impact, impact.value)


def translate_quality_label(value: str) -> str:
    labels = {"high": "높음", "medium": "보통", "low": "낮음"}
    return labels.get(value, value)


def translate_priority_label(value: str) -> str:
    labels = {"high": "높음", "medium": "보통", "low": "낮음"}
    return labels.get(value, value)


def translate_severity_label(value: str) -> str:
    labels = {"high": "높음", "medium": "보통", "low": "낮음"}
    return labels.get(value, value)


def extract_manifest_theses_and_watch_items(
    ticker: str,
    vault_dir: Path,
) -> tuple[list[InvestmentThesis], list[WatchItem]]:
    try:
        db_theses, db_watch_items = read_ticker_thesis_context(vault_dir, ticker)
        if db_theses:
            return db_theses, db_watch_items
    except Exception:
        pass

    entries = [
        entry for entry in read_manifest(vault_dir) if entry.get("ticker") == ticker
    ]
    theses = [
        InvestmentThesis(**entry["investment_thesis"])
        for entry in entries
        if entry.get("investment_thesis")
    ]
    watch_items = [
        WatchItem(**watch_item)
        for entry in entries
        for watch_item in entry.get("watch_items", [])
        if isinstance(watch_item, dict)
    ]
    return theses, watch_items


def clamp_confidence(value: float | None) -> float:
    if value is None:
        return 0.7
    return max(0.0, min(1.0, float(value)))


def average_source_confidence(new_data: list[InjectedDataPoint]) -> float:
    if not new_data:
        return 0.0
    return round(
        sum(clamp_confidence(item.confidence) for item in new_data) / len(new_data),
        2,
    )


def confidence_weight_label(confidence: float) -> str:
    if confidence >= 0.85:
        return "높은 가중치"
    if confidence >= 0.7:
        return "보통 이상의 가중치"
    if confidence >= 0.5:
        return "제한적 가중치"
    return "낮은 가중치"


def confidence_prompt_instruction(confidence: float) -> str:
    pct = confidence * 100
    if confidence >= 0.85:
        return (
            f"이 정보는 신뢰도 {pct:.0f}%짜리 정보입니다. 기존 투자 논거와 비교할 때 "
            "상대적으로 높은 가중치를 두고, 강세/약세 시나리오 변화 가능성을 적극 반영하세요."
        )
    if confidence >= 0.7:
        return (
            f"이 정보는 신뢰도 {pct:.0f}%짜리 정보입니다. 기존 투자 논거와 비교할 때 "
            "의미 있는 가중치를 두되, 추가 확인이 필요한 부분은 별도로 표시하세요."
        )
    if confidence >= 0.5:
        return (
            f"이 정보는 신뢰도 {pct:.0f}%짜리 정보입니다. 기존 투자 논거 평가에 반영하되 "
            "결론은 부분 가중치로 제한하고 교차 검증 필요성을 함께 제시하세요."
        )
    return (
        f"이 정보는 신뢰도 {pct:.0f}%짜리 정보입니다. 기존 투자 논거를 바로 바꾸기보다 "
        "관찰 신호로만 취급하고, 결론의 확신도를 낮게 유지하세요."
    )


def format_weighted_evidence(item: InjectedDataPoint) -> str:
    confidence = clamp_confidence(item.confidence)
    return (
        f"[신뢰도 {confidence:.0%} · {confidence_weight_label(confidence)}] "
        f"{item.label}: {item.value}"
    )


def confidence_adjusted_finding_confidence(
    impact: ThesisImpact,
    source_confidence: float,
) -> float:
    if impact == ThesisImpact.INSUFFICIENT_DATA:
        return round(min(0.45, max(0.25, source_confidence * 0.55)), 2)
    if impact == ThesisImpact.NEUTRAL:
        base = 0.52
    elif impact == ThesisImpact.MIXED:
        base = 0.64
    else:
        base = 0.72
    return round(max(0.25, min(0.92, base * (0.55 + source_confidence * 0.55))), 2)


def evaluate_thesis_impact(
    ticker: str,
    new_data: list[InjectedDataPoint],
    theses: list[InvestmentThesis],
    watch_items: list[WatchItem],
) -> ThesisImpactResponse:
    source_confidence = average_source_confidence(new_data)
    prompt_instruction = confidence_prompt_instruction(source_confidence)
    evidence = [format_weighted_evidence(item) for item in new_data]
    combined_text = " ".join(evidence)
    has_positive = text_has_any(combined_text, POSITIVE_SIGNAL_WORDS)
    has_negative = text_has_any(combined_text, NEGATIVE_SIGNAL_WORDS)

    if not new_data or not theses:
        overall_impact = ThesisImpact.INSUFFICIENT_DATA
    elif source_confidence < 0.45:
        overall_impact = ThesisImpact.NEUTRAL
    elif has_positive and has_negative:
        overall_impact = ThesisImpact.MIXED
    elif has_positive:
        overall_impact = ThesisImpact.STRENGTHENS
    elif has_negative:
        overall_impact = ThesisImpact.WEAKENS
    else:
        overall_impact = ThesisImpact.NEUTRAL

    if not theses:
        findings = [
            ThesisImpactFinding(
                impact=ThesisImpact.INSUFFICIENT_DATA,
                thesis_reference="저장된 투자 논거 없음",
                evidence=evidence,
                reasoning=(
                    f"{prompt_instruction} 저장된 투자 논거가 없어 새 정보와 비교할 기준이 부족합니다."
                ),
                confidence=confidence_adjusted_finding_confidence(
                    ThesisImpact.INSUFFICIENT_DATA,
                    source_confidence,
                ),
            )
        ]
    else:
        findings = [
            ThesisImpactFinding(
                impact=overall_impact,
                thesis_reference=thesis.thesis,
                evidence=evidence,
                reasoning=(
                    f"{prompt_instruction} 새 데이터의 긍정/부정 신호를 기존 강세/약세 촉발 조건과 비교했습니다. "
                    f"출처 평균 신뢰도는 {source_confidence:.0%}이며, 이 가중치를 반영해 결론 확신도를 조정했습니다."
                ),
                confidence=confidence_adjusted_finding_confidence(
                    overall_impact,
                    source_confidence,
                ),
            )
            for thesis in theses
        ]

    watch_item_signals = []
    for watch_item in watch_items:
        metric_match = watch_item.metric.lower() in combined_text.lower()
        watch_item_signals.append(
            WatchItemSignal(
                metric=watch_item.metric,
                matched=metric_match,
                signal=(
                    f"'{watch_item.metric}' 관련 새 정보가 감지되었습니다."
                    if metric_match
                    else "직접 매칭된 신호 없음"
                ),
                action=watch_item.action if metric_match else "계속 모니터링",
                priority=watch_item.priority,
            )
        )

    next_actions = [
        "팀 리포트를 재실행해 강세/기준/약세 시나리오를 업데이트",
        "영향도가 약화 또는 혼합이면 무효화 조건과 포지션 사이즈를 재검토",
        "영향도가 강화이면 밸류에이션과 진입 조건을 별도로 업데이트",
    ]
    if source_confidence < 0.7 and new_data:
        next_actions.insert(0, "신뢰도가 제한적인 정보이므로 공식 공시, 실적 자료, 가격 데이터로 교차 검증")
    if overall_impact == ThesisImpact.INSUFFICIENT_DATA:
        next_actions = [
            "먼저 7개 스킬 팀 리포트를 생성해 기준 투자 논거를 저장",
            "공식 실적/재무/가격 데이터를 추가 데이터로 주입",
        ]

    return ThesisImpactResponse(
        ticker=ticker,
        overall_impact=overall_impact,
        summary=(
            f"새 데이터는 평균 신뢰도 {source_confidence:.0%} 가중치를 반영해 "
            f"기존 {ticker} 투자 논거에 대해 '{translate_impact_label(overall_impact)}'로 분류되었습니다."
        ),
        findings=findings,
        watch_item_signals=watch_item_signals,
        next_actions=next_actions,
        source_count=len(new_data),
    )


def render_thesis_impact_markdown(
    impact: ThesisImpactResponse,
    storage_date: date,
) -> str:
    findings = "\n\n".join(
        "\n".join(
            [
                f"### 판단: {item.impact.value}",
                f"- 투자 논거: {item.thesis_reference}",
                f"- 판단 이유: {item.reasoning}",
                f"- 확신도: {item.confidence:.0%}",
                "- 근거:",
                *[f"  - {evidence}" for evidence in item.evidence],
            ]
        )
        for item in impact.findings
    )
    watch_signals = "\n".join(
        f"- {item.metric}: {item.signal} -> {item.action} ({translate_priority_label(item.priority)})"
        for item in impact.watch_item_signals
    )
    next_actions = "\n".join(f"- {item}" for item in impact.next_actions)

    return f"""---
ticker: {impact.ticker}
type: thesis-impact-review
date: {storage_date.isoformat()}
module: {impact.module}
overall_impact: {impact.overall_impact.value}
---

# {impact.ticker} 투자 논거 영향도 분석

## 요약

{impact.summary}

## 판단 근거

{findings}

## 추적 항목 신호

{watch_signals}

## 다음 액션

{next_actions}
"""


def summarize_capture(raw_content: str) -> str:
    compact = " ".join(raw_content.split())
    if len(compact) <= 240:
        return compact
    return f"{compact[:237]}..."


def infer_capture_tags(raw_content: str, provided_tags: list[str]) -> list[str]:
    text = raw_content.lower()
    inferred = set(provided_tags)
    tag_rules = {
        "earnings": {"earnings", "eps", "revenue", "guidance", "실적", "가이던스"},
        "valuation": {"valuation", "multiple", "pe", "ev/ebitda", "밸류에이션"},
        "risk": {"risk", "regulation", "lawsuit", "downside", "리스크", "규제"},
        "growth": {"growth", "demand", "capex", "성장", "수요", "투자"},
        "margin": {"margin", "gross margin", "operating margin", "마진"},
        "macro": {
            "rate",
            "inflation",
            "oil",
            "dollar",
            "fed",
            "fomc",
            "cpi",
            "금리",
            "유가",
            "달러",
            "연준",
            "물가",
            "거시",
        },
        "policy": {
            "policy",
            "regulation",
            "tariff",
            "fiscal",
            "election",
            "sanction",
            "government",
            "central bank",
            "정책",
            "규제",
            "관세",
            "재정",
            "선거",
            "정부",
            "중앙은행",
            "한국은행",
            "지정학",
        },
        "rates": {
            "rate",
            "rates",
            "yield",
            "treasury",
            "bond",
            "duration",
            "cpi",
            "pce",
            "inflation",
            "credit spread",
            "금리",
            "국채",
            "채권",
            "물가",
            "인플레이션",
            "장단기",
            "신용 스프레드",
        },
        "flows": {
            "flows",
            "fund flow",
            "etf flow",
            "positioning",
            "breadth",
            "rotation",
            "net buying",
            "net selling",
            "수급",
            "자금 흐름",
            "순매수",
            "순매도",
            "외국인",
            "기관",
            "개인",
            "포지셔닝",
            "시장 폭",
            "로테이션",
        },
        "sector": {
            "sector",
            "industry",
            "semiconductor",
            "energy",
            "healthcare",
            "섹터",
            "산업",
            "반도체",
            "에너지",
            "헬스케어",
            "테마",
        },
        "market": {
            "market",
            "flows",
            "positioning",
            "breadth",
            "rotation",
            "시장",
            "수급",
            "자금 흐름",
            "포지셔닝",
            "로테이션",
            "투자 동향",
        },
        "ai": {"ai", "artificial intelligence", "gpu", "hbm", "데이터센터", "인공지능", "반도체", "가속기"},
        "energy": {"energy", "oil", "gas", "lng", "power", "grid", "전력", "에너지", "유가", "천연가스", "lng"},
        "space": {"space", "satellite", "launch", "earth observation", "우주", "위성", "발사체", "지구관측"},
        "defense": {"defense", "aerospace", "military", "방산", "국방", "항공우주", "드론"},
        "biotech": {"biotech", "drug", "clinical", "fda", "바이오", "임상", "신약", "허가"},
        "consumer": {"consumer", "brand", "food", "retail", "소비", "브랜드", "식품", "유통"},
        "institution": {"reuters", "bloomberg", "federal reserve", "sec", "정부", "기관", "증권사", "거래소", "공시"},
        "person": {"ceo", "cfo", "chair", "founder", "대표", "회장", "창업자", "경영진"},
    }
    for tag, keywords in tag_rules.items():
        matched = False
        for keyword in keywords:
            keyword_text = str(keyword).lower().strip()
            if not keyword_text:
                continue
            if search(r"[a-z0-9]", keyword_text):
                if search(rf"(?<![a-z0-9]){escape(keyword_text)}(?![a-z0-9])", text):
                    matched = True
                    break
            elif keyword_text in text:
                matched = True
                break
        if matched:
            inferred.add(tag)
    return sorted(inferred)


def infer_capture_source_type(
    raw_content: str,
    file_name: str | None = None,
    allow_non_ticker_scope: bool = False,
) -> str:
    text = f"{file_name or ''} {raw_content}".lower()
    if allow_non_ticker_scope:
        non_ticker_key, non_ticker_source = infer_non_ticker_research_key(raw_content)
        if non_ticker_key in SPECIAL_RESEARCH_KEYS - {"INBOX"}:
            return non_ticker_source
    if any(keyword in text for keyword in ["10-k", "10-q", "sec filing", "annual report", "분기보고서", "사업보고서"]):
        return enum_or_str_value(DataSourceType.OFFICIAL_FILING)
    if any(keyword in text for keyword in ["기사본문", "기자", "news", "press release", "article", "뉴스", "기사", "보도"]):
        return enum_or_str_value(DataSourceType.NEWS)
    if any(keyword in text for keyword in ["earnings", "eps", "guidance", "실적", "가이던스", "컨퍼런스콜"]):
        return enum_or_str_value(DataSourceType.EARNINGS_RELEASE)
    if any(keyword in text for keyword in ["analyst", "initiation", "upgrade", "downgrade", "target price", "애널리스트", "리포트"]):
        return enum_or_str_value(DataSourceType.ANALYST_REPORT)
    if any(keyword in text for keyword in ["revenue", "gross margin", "ebitda", "cash flow", "매출", "마진", "현금흐름"]):
        return enum_or_str_value(DataSourceType.FINANCIAL_DATA)
    return enum_or_str_value(DataSourceType.USER_MEMO)


def infer_capture_confidence(source_type: str, has_file: bool = False) -> float:
    confidence_by_source = {
        enum_or_str_value(DataSourceType.OFFICIAL_FILING): 0.9,
        enum_or_str_value(DataSourceType.EARNINGS_RELEASE): 0.86,
        enum_or_str_value(DataSourceType.ANALYST_REPORT): 0.82,
        enum_or_str_value(DataSourceType.FINANCIAL_DATA): 0.8,
        enum_or_str_value(DataSourceType.NEWS): 0.75,
        enum_or_str_value(DataSourceType.USER_MEMO): 0.7,
        "macro_research": 0.78,
        "sector_research": 0.78,
        "market_research": 0.76,
        "policy_research": 0.78,
        "rates_research": 0.78,
        "flows_research": 0.76,
    }
    base = confidence_by_source.get(source_type, 0.72)
    return min(base + (0.03 if has_file else 0), 0.95)


DOSSIER_POSITIVE_TERMS = {
    "상향",
    "개선",
    "강세",
    "호조",
    "성장",
    "수요",
    "수주",
    "확대",
    "마진 개선",
    "가이던스 상향",
    "beat",
    "raise",
    "raised",
    "growth",
    "demand",
    "margin expansion",
    "upside",
}

DOSSIER_NEGATIVE_TERMS = {
    "하향",
    "악화",
    "약세",
    "둔화",
    "하회",
    "약화",
    "하락",
    "적자",
    "못 미쳤",
    "제한적",
    "부진",
    "리스크",
    "경쟁",
    "현금 소진",
    "마진 압박",
    "가이던스 하향",
    "miss",
    "cut",
    "risk",
    "slowdown",
    "downside",
    "cash burn",
}

DOSSIER_FACT_TERMS = {
    "매출",
    "영업이익",
    "순이익",
    "EPS",
    "가이던스",
    "수주",
    "계약",
    "마진",
    "현금",
    "FCF",
    "고객",
    "시장",
    "섹터",
    "정책",
    "금리",
    "revenue",
    "guidance",
    "margin",
    "cash",
    "contract",
    "customer",
}

DOSSIER_ALLOWED_REPORT_TYPES = {
    "collaborative-team-report",
    "institutional-stock-breakdown",
    "earnings-reaction",
    "research-capture",
    "market-close-review",
    "sector-opportunity",
    "compounder-finder",
}

DOSSIER_EXCLUDED_REPORT_TYPES = {
    "dossier-synthesis",
    "rag-query-synthesis",
    "thesis-impact-review",
    "smart-trade-setup",
    "research-checklist",
    "chart-analysis",
    "portfolio-risk-scan",
    "reinforcement-portfolio-optimizer",
    "daily-dossier-brief",
}


def content_fingerprint(text: str | None) -> str:
    normalized = " ".join(str(text or "").lower().split())
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def similarity_tokens(text: str | None) -> set[str]:
    normalized = sub(r"[^0-9a-zA-Z가-힣]+", " ", str(text or "").lower())
    tokens = {
        token
        for token in normalized.split()
        if len(token) >= 2 and token not in {"the", "and", "for", "with", "from", "this", "that"}
    }
    return tokens


def token_jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, len(left | right))


def manifest_similarity_text(entry: dict, text: str | None = None) -> str:
    # source_url/file_name은 exact match에는 유용하지만 유사도 토큰에 넣으면
    # 같은 사이트의 서로 다른 리포트까지 과하게 중복으로 묶일 수 있다.
    body = str(text or "")
    try:
        if body:
            body = " ".join(plain_research_lines(body, limit=40))
    except NameError:
        body = body[:2400]
    return " ".join(
        str(part or "")
        for part in [
            entry.get("title"),
            entry.get("summary"),
            body[:2400],
        ]
    )


def add_unique_text(items: list[str], value: str | None, limit: int = 8) -> None:
    cleaned = " ".join(str(value or "").split())
    if cleaned and cleaned not in items and len(items) < limit:
        items.append(cleaned)


DOSSIER_NOISE_TERMS = {
    "[네이버 금융 리서치 자동 수집]",
    "분류:",
    "기타 /",
    "투자 정보 캡처",
    "분류 근거:",
    "증권사:",
    "종목명:",
    "종목코드:",
    "발행일:",
    "저장 범위:",
    "원문 링크:",
    "pdf 링크:",
    "활용 메모:",
    "source_url",
    "source type",
    "source_type",
    "source_file",
    "source_relative_path",
    "content_hash",
    "attachment",
    "json_relative_path",
    "json_file_name",
    "official_company_profile",
    "DataSourceType.",
    "DataSourceType.EARNINGS_RELEASE",
    "DataSourceType.MARKET_PRICE",
    "DataSourceType.FINANCIAL_STATEMENT",
    "리서치 메모리 / latest_thesis_snapshot",
    "리서치 메모리 / rag_memory_document",
    "latest_thesis_snapshot",
    "rag_memory_document",
    "주입된 데이터 컨텍스트",
    "injected_data",
    "DataSourceType.RESEARCH_MEMORY",
    "DataSourceType.OTHER",
    "저장된 투자 논거가 없어",
    "판단 이유: 이 정보는 신뢰도",
    "새 데이터는 평균 신뢰도",
    "매매전략 탭에서",
    "매매 전략:",
    "포트폴리오 리스크 스캔",
    "기관급 분석",
    "스마트 매매 전략",
    "실적 발표 반응 분석",
    "장기 복리 성장주 발굴",
    "리서치 체크리스트",
    "관점의 핵심 판단",
    "주의 관점:",
    "다음 실적 체크포인트:",
    "직전/최신 실적 메모:",
    "정확한 매출",
    "회사 공시 또는 DART",
    "보강해야",
    "DART/IR 자료",
    "주입 데이터",
    "빠른 정보 저장",
    "재실행",
    "시나리오를 갱신",
    "기준/강세/약세",
    "기준 시나리오의 성장 가정을 하회",
    "이전 가이던스",
    "리스크 예산 초과",
    "포지션 크기를",
    "센티먼트가 개선이면",
    "하는지 확인",
    "방향과 일치하는지",
    "매출 및 수주상황",
    "[첨부 파일]",
    "파일명:",
    "글로벌리더",
    "거래정지 기간 동안",
    "7개 분석 스킬",
    "생성했습니다",
    "실적은 '긍정적 확인'",
    "주가 반응은 미입력",
    "입력되지 않았습니다",
    "보강하세요",
    "다음 실적 전 확인할 KPI",
    "가이던스 평가:",
    "역할:",
    "페르소나:",
    "중점 분석:",
    "체크리스트",
    "보강 필요 입력",
    "표시할 데이터 경고가 없습니다",
    "저장 파일:",
    "저장 데이터:",
    "태그:",
    "tags:",
    "auto_ingested",
    "auto_classified",
    "auto_ticker:",
    "naver_category:",
    "naver_research",
    "가격/리스크 조건을 분리",
    "새 데이터가 들어올 때마다",
    "긍정 관점:",
    "정리:",
    "포지션은 리스크 예산",
    "포트폴리오 리스크 예산",
    "경쟁 우위 훼손",
    "센티먼트가 악화",
    "밸류에이션 범위를 단일 목표가",
    "현재가와 최근 변동성 데이터를",
    "진입 구간, 손절, 목표가를 자동 보정",
    "손익비가",
    "실적 발표 전후에는 포지션 사이즈",
    "장기 복리 후보 여부는",
    "관찰 목록 유지",
    "com/research/company_read",
    "com/research/industry_read",
}


def is_dossier_noise_line(line: str) -> bool:
    cleaned = " ".join(str(line or "").split())
    lowered = cleaned.lower()
    if not cleaned:
        return True
    if cleaned.startswith(("[x]", "[ ]")):
        return True
    if cleaned[0] in {",", ".", ")", "]", "}"}:
        return True
    if cleaned.count(".") >= 8:
        return True
    if cleaned.startswith(("이었", "였", "및 ", "을 ", "를 ", "는 ", "하며", "했고", "화,", "동안 ", "지했다", "(YoY", "악된다", "기의 ")):
        return True
    if len(cleaned) < 24 and not any(ch.isdigit() for ch in cleaned):
        return True
    return any(term.lower() in lowered for term in DOSSIER_NOISE_TERMS)


def is_allowed_dossier_source_entry(entry: dict) -> bool:
    report_type = str(entry.get("type") or "").strip().lower()
    if report_type in DOSSIER_EXCLUDED_REPORT_TYPES:
        return False
    if report_type not in DOSSIER_ALLOWED_REPORT_TYPES:
        return False
    summary = str(entry.get("summary") or "")
    tags = {str(tag).strip().lower() for tag in (entry.get("tags") or []) if str(tag).strip()}
    if {"naver_research", "auto_ingested"} <= tags and len(summary) < 260:
        return False
    return True


def is_research_line_continuation(line: str) -> bool:
    cleaned = str(line or "").strip()
    return bool(
        cleaned
        and (
            cleaned[0] in {",", ".", ")", "]", "}", "%"}
            or cleaned.startswith(
                (
                    "은 ",
                    "는 ",
                    "을 ",
                    "를 ",
                    "이 ",
                    "가 ",
                    "와 ",
                    "과 ",
                    "으로",
                    "로 ",
                    "며 ",
                    "고 ",
                    "다.",
                )
            )
        )
    )


def should_merge_research_lines(previous: str, current: str) -> bool:
    prev = str(previous or "").strip()
    cur = str(current or "").strip()
    if not prev or not cur:
        return False
    if is_research_line_continuation(cur):
        return True
    if prev.endswith(("은", "는", "이", "가", "을", "를", "및", "로", "으로", "영업이익은", "매출액은")):
        return True
    return False


def extract_scenario_clause(line: str, mode: str) -> str:
    cleaned = " ".join(str(line or "").split())
    if mode == "bull" and "강세:" in cleaned:
        clause = cleaned.split("강세:", 1)[1]
        for marker in ("기준:", "약세:"):
            clause = clause.split(marker, 1)[0]
        return clause.strip()
    if mode == "bear" and "약세:" in cleaned:
        return cleaned.split("약세:", 1)[1].strip()
    return cleaned


def clean_dossier_signal(line: str, mode: str = "generic") -> str:
    candidate = extract_scenario_clause(line, mode) if mode in {"bull", "bear"} else " ".join(str(line or "").split())
    candidate = sub(r"^(강세|약세|기준|요약)\s*:\s*", "", candidate).strip()
    candidate = candidate.strip(" -•")
    if not candidate or is_dossier_noise_line(candidate):
        return ""
    return compact_representative_sentence(candidate, 220)


def add_dossier_signal(items: list[str], line: str, mode: str, limit: int) -> None:
    candidate = clean_dossier_signal(line, mode)
    if not candidate:
        return
    if mode == "bull" and "강세:" not in str(line) and line_has_any(candidate, DOSSIER_NEGATIVE_TERMS) and not line_has_negated_bear_context(candidate):
        return
    if mode == "bear" and "약세:" not in str(line) and line_has_any(candidate, DOSSIER_POSITIVE_TERMS) and not line_has_any(candidate, DOSSIER_NEGATIVE_TERMS):
        return
    if mode == "bear" and line_has_negated_bear_context(candidate):
        return
    if len(candidate) < 24 and not any(ch.isdigit() for ch in candidate):
        return
    add_unique_text(items, candidate, limit=limit)


def representative_thesis_line(items: list[str], fallback: str, mode: str = "generic") -> str:
    if not items:
        return fallback

    def score(line: str) -> tuple[int, int, int]:
        cleaned = " ".join(str(line or "").split())
        metric_score = 0
        for terms in (DOSSIER_FACT_TERMS, DOSSIER_POSITIVE_TERMS, DOSSIER_NEGATIVE_TERMS):
            if line_has_any(cleaned, terms):
                metric_score += 1
        completeness = 1 if cleaned.endswith((".", "다.", "입니다.", "습니다.", "요.")) else 0
        return (metric_score, completeness, min(len(cleaned), 180))

    candidates = [item for item in items if not is_dossier_noise_line(item)]
    candidates = [item for item in candidates if len(item) >= 40]
    if not candidates:
        return fallback
    if mode in {"bull", "bear"}:
        marker = "강세:" if mode == "bull" else "약세:"
        scenario_candidates = [
            extract_scenario_clause(item, mode)
            for item in candidates
            if marker in str(item)
        ]
        scenario_candidates = [
            item for item in scenario_candidates if len(item) >= 20 and not is_dossier_noise_line(item)
        ]
        if scenario_candidates:
            return compact_representative_sentence(scenario_candidates[0])
    selected = extract_scenario_clause(sorted(candidates, key=score, reverse=True)[0], mode)
    if is_dossier_noise_line(selected):
        return fallback
    return compact_representative_sentence(selected)


def manifest_entry_sort_key(entry: dict) -> tuple[str, int, str]:
    return (
        str(entry.get("date") or ""),
        report_file_sequence(str(entry.get("file_name") or "")),
        str(entry.get("updated_at") or ""),
    )


def read_manifest_entry_text(vault_dir: Path, entry: dict) -> str:
    candidates: list[Path] = []
    relative_path = entry.get("relative_path")
    if relative_path:
        candidates.append(vault_dir.parent / str(relative_path))
    ticker = str(entry.get("ticker") or "").strip()
    file_name = str(entry.get("file_name") or "").strip()
    if ticker and file_name:
        candidates.append(vault_dir / ticker / file_name)
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            if not str(resolved).startswith(str(vault_dir.parent.resolve())):
                continue
            if resolved.exists() and resolved.is_file():
                return resolved.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
    return str(entry.get("summary") or "")


def plain_research_lines(text: str, limit: int = 80) -> list[str]:
    lines: list[str] = []
    raw_lines: list[str] = []
    in_front_matter = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "---":
            in_front_matter = not in_front_matter
            continue
        if in_front_matter:
            continue
        line = sub(r"^[#>*\-\d.\s]+", "", line).strip()
        line = sub(r"\s+", " ", line)
        if len(line) < 2 or line.lower().startswith(("ticker:", "type:", "date:", "module:")):
            continue
        if is_dossier_noise_line(line) and not is_research_line_continuation(line):
            continue
        if raw_lines and should_merge_research_lines(raw_lines[-1], line):
            raw_lines[-1] = f"{raw_lines[-1]} {line}"
        else:
            raw_lines.append(line)

    for line in raw_lines:
        if len(line) < 12 or is_dossier_noise_line(line):
            continue
        if len(line) > 320:
            line = f"{line[:317]}..."
        add_unique_text(lines, line, limit=limit)
    return lines


def line_has_any(text: str, terms: set[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def line_has_negated_bear_context(text: str) -> bool:
    cleaned = " ".join(str(text or "").split())
    compacted = cleaned.replace(" ", "")
    negated_patterns = (
        "둔화 신호로 해석하기는 어렵",
        "둔화 신호로 보기 어렵",
        "훼손이라기보다는",
        "리스크가 제한",
        "우려는 제한",
        "부담은 제한",
        "악화라기보다",
        "리스크 해소",
    )
    compacted_patterns = tuple(pattern.replace(" ", "") for pattern in negated_patterns)
    return any(pattern in cleaned for pattern in negated_patterns) or any(
        pattern in compacted for pattern in compacted_patterns
    )


def compact_representative_sentence(text: str, max_len: int = 180) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= max_len:
        return cleaned
    pieces = [piece.strip() for piece in findall(r"[^.!?。]+[.!?。]?", cleaned) if piece.strip()]
    scored: list[tuple[int, int, str]] = []
    for piece in pieces:
        if is_dossier_noise_line(piece):
            continue
        score = 0
        if line_has_any(piece, DOSSIER_FACT_TERMS):
            score += 2
        if line_has_any(piece, DOSSIER_POSITIVE_TERMS) or line_has_any(piece, DOSSIER_NEGATIVE_TERMS):
            score += 1
        if 35 <= len(piece) <= max_len:
            score += 2
        scored.append((score, min(len(piece), max_len), piece))
    if scored:
        selected = sorted(scored, reverse=True)[0][2]
        if len(selected) <= max_len:
            return selected
    return f"{cleaned[: max_len - 3]}..."


def latest_verified_entries_for_dossier(ticker: str, vault_dir: Path) -> tuple[list[dict], list[dict]]:
    entries = [
        entry
        for entry in read_manifest(vault_dir)
        if entry.get("ticker") == ticker
        and is_allowed_dossier_source_entry(entry)
        and is_verified_manifest_entry(entry, ticker)
    ]
    entries.sort(key=manifest_entry_sort_key, reverse=True)
    unique_entries: list[dict] = []
    duplicates: list[dict] = []
    seen: set[str] = set()
    seen_token_sets: list[set[str]] = []
    for entry in entries:
        text = read_manifest_entry_text(vault_dir, entry)
        clean_lines = plain_research_lines(text, limit=12)
        if not clean_lines and is_dossier_noise_line(entry.get("summary")):
            duplicates.append(
                {
                    "file_name": entry.get("file_name"),
                    "type": entry.get("type"),
                    "summary": entry.get("summary"),
                    "reason": "metadata_or_internal_output_only",
                }
            )
            continue
        dedup_key = (
            str(entry.get("source_url") or "").strip()
            or str(entry.get("content_hash") or "").strip()
            or content_fingerprint(f"{entry.get('type')} {entry.get('summary')} {text[:1200]}")
        )
        signature_tokens = similarity_tokens(manifest_similarity_text(entry, text))
        similar_to_seen = any(
            token_jaccard_similarity(signature_tokens, previous_tokens) >= 0.82
            for previous_tokens in seen_token_sets
            if len(signature_tokens) >= 8 and len(previous_tokens) >= 8
        )
        if dedup_key in seen or similar_to_seen:
            duplicates.append(
                {
                    "file_name": entry.get("file_name"),
                    "type": entry.get("type"),
                    "summary": entry.get("summary"),
                    "reason": "exact_match" if dedup_key in seen else "title_body_similarity",
                }
            )
            continue
        seen.add(dedup_key)
        if signature_tokens:
            seen_token_sets.append(signature_tokens)
        unique_entries.append({**entry, "_full_text": text})
    return unique_entries, duplicates


def dedupe_manifest_entries_by_similarity(entries: list[dict], vault_dir: Path, limit: int = 15) -> tuple[list[dict], list[dict]]:
    unique_entries: list[dict] = []
    duplicates: list[dict] = []
    seen_keys: set[str] = set()
    seen_tokens: list[set[str]] = []
    for entry in entries:
        text = read_manifest_entry_text(vault_dir, entry)
        exact_key = (
            str(entry.get("source_url") or "").strip()
            or str(entry.get("content_hash") or "").strip()
            or content_fingerprint(manifest_similarity_text(entry, text))
        )
        tokens = similarity_tokens(manifest_similarity_text(entry, text))
        similar = any(
            token_jaccard_similarity(tokens, previous) >= 0.84
            for previous in seen_tokens
            if len(tokens) >= 8 and len(previous) >= 8
        )
        if exact_key in seen_keys or similar:
            duplicates.append({**entry, "duplicate_reason": "exact_match" if exact_key in seen_keys else "title_body_similarity"})
            continue
        seen_keys.add(exact_key)
        if tokens:
            seen_tokens.append(tokens)
        unique_entries.append(entry)
        if len(unique_entries) >= limit:
            break
    return unique_entries, duplicates


def detect_capture_duplicate(
    *,
    vault_dir: Path,
    ticker: str,
    title: str,
    raw_content: str,
    source_url: str | None = None,
    content_hash: str | None = None,
    max_candidates: int = 120,
) -> dict:
    normalized_ticker = ticker.strip().upper()
    new_text = manifest_similarity_text(
        {
            "title": title,
            "summary": summarize_capture(raw_content),
            "source_url": source_url,
        },
        raw_content,
    )
    new_tokens = similarity_tokens(new_text)
    new_hash = content_hash or content_fingerprint(raw_content)
    candidates = [
        entry
        for entry in sorted(
            [entry for entry in read_manifest(vault_dir) if isinstance(entry, dict)],
            key=manifest_entry_sort_key,
            reverse=True,
        )
        if (entry.get("type") == "research-capture")
        and not is_failed_capture_manifest_entry(entry)
        and (
            str(entry.get("ticker") or "").upper() == normalized_ticker
            or normalized_ticker in SPECIAL_RESEARCH_KEYS
            or str(entry.get("ticker") or "").upper() in SPECIAL_RESEARCH_KEYS
        )
    ][:max_candidates]

    best: dict | None = None
    for entry in candidates:
        reason = None
        similarity = 0.0
        if source_url and entry.get("source_url") == source_url:
            reason = "source_url_exact_match"
            similarity = 1.0
        elif new_hash and entry.get("content_hash") == new_hash:
            reason = "content_hash_exact_match"
            similarity = 1.0
        else:
            existing_text = read_manifest_entry_text(vault_dir, entry)
            existing_tokens = similarity_tokens(manifest_similarity_text(entry, existing_text))
            similarity = token_jaccard_similarity(new_tokens, existing_tokens)
            if len(new_tokens) >= 8 and len(existing_tokens) >= 8 and similarity >= 0.84:
                reason = "title_body_similarity"

        if reason and (best is None or similarity > best.get("similarity", 0)):
            best = {
                "reason": reason,
                "similarity": round(similarity, 4),
                "matched_ticker": entry.get("ticker"),
                "matched_type": entry.get("type"),
                "matched_date": entry.get("date"),
                "matched_file_name": entry.get("file_name"),
                "matched_relative_path": entry.get("relative_path"),
            }

    return {
        "is_duplicate_suspected": best is not None,
        "checked_count": len(candidates),
        "reason": best.get("reason") if best else "no_match",
        "similarity": best.get("similarity") if best else 0.0,
        "matched_ticker": best.get("matched_ticker") if best else None,
        "matched_file_name": best.get("matched_file_name") if best else None,
        "matched_relative_path": best.get("matched_relative_path") if best else None,
    }


def is_failed_capture_manifest_entry(entry: dict) -> bool:
    summary = str(entry.get("summary") or "")
    relative_path = str(entry.get("relative_path") or "")
    source_processing = entry.get("source_url_processing") or {}
    failed_statuses = {"fetch_failed", "invalid", "empty_text"}
    return (
        "WinError 10061" in summary
        or "웹사이트 본문을 추출하지 못했습니다" in summary
        or "winerror-10061" in relative_path.lower()
        or str(source_processing.get("status") or "") in failed_statuses
    )


def capture_quality_status(
    *,
    raw_content: str,
    attachment_info: dict | None = None,
    source_url_processing: dict | None = None,
) -> dict:
    url_status = str((source_url_processing or {}).get("status") or "")
    url_text = str((source_url_processing or {}).get("text") or "")
    attachment_text = str((attachment_info or {}).get("extracted_text") or "")
    text_length = max(len(raw_content or ""), len(url_text), len(attachment_text))
    warnings: list[str] = []
    if url_status in {"fetch_failed", "invalid", "empty_text"}:
        warnings.append("웹사이트 본문 추출 실패")
    if attachment_info and not attachment_text and not (attachment_info or {}).get("extraction_char_count"):
        warnings.append("첨부 파일 본문 추출 확인 필요")
    if text_length >= 1000 and not warnings:
        status = "정상"
    elif text_length >= 250:
        status = "보강 필요" if warnings else "정상"
    else:
        status = "실패" if warnings else "보강 필요"
    return {
        "status": status,
        "text_length": text_length,
        "warnings": warnings,
        "url_status": url_status or None,
        "readiness": (
            "분석에 바로 활용 가능"
            if status == "정상"
            else "추가 본문/원문 확인 후 활용"
            if status == "보강 필요"
            else "분석 반영 제외 권장"
        ),
    }


def compact_manifest_review_entry(entry: dict) -> dict:
    return {
        "ticker": entry.get("ticker"),
        "company_name": entry.get("company_name"),
        "type": entry.get("type"),
        "date": entry.get("date"),
        "title": entry.get("title") or entry.get("file_name") or "제목 없음",
        "summary": compact_representative_sentence(entry.get("summary") or "", 180),
        "file_name": entry.get("file_name"),
        "relative_path": entry.get("relative_path"),
        "source_url": entry.get("source_url"),
    }


def build_storage_duplicate_review(
    settings: Settings,
    *,
    limit: int = 80,
    save_result: bool = True,
) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    manifest_entries = [
        entry
        for entry in read_manifest(vault_dir)
        if isinstance(entry, dict)
        and str(entry.get("type") or "").strip().lower() in DOSSIER_ALLOWED_REPORT_TYPES
    ]
    manifest_entries.sort(key=manifest_entry_sort_key, reverse=True)

    representatives: list[dict] = []
    groups: list[dict] = []
    exact_keys: dict[str, int] = {}
    token_sets: list[set[str]] = []
    checked_count = 0

    for entry in manifest_entries[: max(limit * 10, 200)]:
        text = read_manifest_entry_text(vault_dir, entry)
        if not plain_research_lines(text, limit=3) and is_dossier_noise_line(entry.get("summary")):
            continue
        checked_count += 1
        exact_key = (
            str(entry.get("source_url") or "").strip()
            or str(entry.get("content_hash") or "").strip()
            or content_fingerprint(manifest_similarity_text(entry, text))
        )
        tokens = similarity_tokens(manifest_similarity_text(entry, text))
        match_index: int | None = None
        reason = "no_match"
        similarity = 0.0

        if exact_key and exact_key in exact_keys:
            match_index = exact_keys[exact_key]
            reason = "exact_match"
            similarity = 1.0
        else:
            best: tuple[float, int] | None = None
            for index, previous_tokens in enumerate(token_sets):
                current_ticker = str(entry.get("ticker") or "").upper()
                previous_ticker = str((representatives[index] if index < len(representatives) else {}).get("ticker") or "").upper()
                same_scope = current_ticker == previous_ticker or (
                    current_ticker in SPECIAL_RESEARCH_KEYS and previous_ticker in SPECIAL_RESEARCH_KEYS
                )
                if not same_scope:
                    continue
                if len(tokens) < 8 or len(previous_tokens) < 8:
                    continue
                score = token_jaccard_similarity(tokens, previous_tokens)
                if score >= 0.84 and (best is None or score > best[0]):
                    best = (score, index)
            if best is not None:
                similarity, match_index = best
                reason = "title_body_similarity"

        if match_index is None:
            exact_keys[exact_key] = len(representatives)
            if tokens:
                token_sets.append(tokens)
            else:
                token_sets.append(set())
            representatives.append(entry)
            continue

        while len(groups) <= match_index:
            representative = representatives[len(groups)] if len(groups) < len(representatives) else {}
            groups.append(
                {
                    "group_id": content_fingerprint(
                        f"{representative.get('ticker')} {representative.get('file_name')} {representative.get('source_url')}"
                    )[:16],
                    "ticker": representative.get("ticker"),
                    "company_name": representative.get("company_name"),
                    "representative": compact_manifest_review_entry(representative),
                    "duplicates": [],
                    "duplicate_count": 0,
                    "reasons": {},
                    "recommended_action": "대표 자료 1개만 Dossier 합성에 사용하고, 중복 자료는 복기용 원문으로만 유지합니다.",
                }
            )

        group = groups[match_index]
        group["duplicates"].append(
            {
                **compact_manifest_review_entry(entry),
                "duplicate_reason": reason,
                "similarity": round(similarity, 4),
            }
        )
        group["duplicate_count"] = len(group["duplicates"])
        reasons = group.setdefault("reasons", {})
        reasons[reason] = int(reasons.get(reason) or 0) + 1

    groups = [group for group in groups if group.get("duplicate_count")]
    groups.sort(key=lambda item: int(item.get("duplicate_count") or 0), reverse=True)
    groups = groups[: max(limit, 1)]
    duplicate_entry_count = sum(int(group.get("duplicate_count") or 0) for group in groups)

    ticker_breakdown: dict[str, dict] = {}
    for group in groups:
        key = str(group.get("ticker") or "UNKNOWN")
        item = ticker_breakdown.setdefault(
            key,
            {
                "ticker": key,
                "company_name": group.get("company_name"),
                "duplicate_group_count": 0,
                "duplicate_entry_count": 0,
            },
        )
        item["duplicate_group_count"] += 1
        item["duplicate_entry_count"] += int(group.get("duplicate_count") or 0)

    payload = {
        "status": "success",
        "module": "storage_duplicate_review",
        "as_of": current_storage_timestamp(),
        "checked_count": checked_count,
        "unique_representative_count": len(representatives),
        "duplicate_group_count": len(groups),
        "duplicate_entry_count": duplicate_entry_count,
        "groups": groups,
        "ticker_breakdown": sorted(
            ticker_breakdown.values(),
            key=lambda item: (int(item.get("duplicate_entry_count") or 0), int(item.get("duplicate_group_count") or 0)),
            reverse=True,
        )[:20],
        "next_actions": [
            "중복 의심이 많은 종목부터 Dossier 재합성을 실행해 최신 투자 논거를 다시 고정하세요.",
            "source_url/content_hash 일치 자료는 사실상 같은 자료로 보고 대표 자료만 의사결정에 반영하세요.",
            "제목·본문 유사 자료는 원문이 다른 업데이트일 수 있으므로 요약 차이가 있는지 우선 확인하세요.",
        ],
    }
    if save_result:
        write_json_store(storage_duplicate_review_path(settings), payload)
        payload["storage"] = {
            "relative_path": str(storage_duplicate_review_path(settings).relative_to(vault_dir.parent)).replace("\\", "/")
        }
    return payload


def build_dossier_payload(ticker: str, vault_dir: Path) -> dict:
    storage_date = current_storage_date()
    company_name = ticker_company_name(ticker)
    entries, duplicates = latest_verified_entries_for_dossier(ticker, vault_dir)
    profile_focus = analysis_focus_for_ticker(ticker, None)
    watch_kpis = ticker_watch_kpis(ticker)
    consensus_facts: list[str] = []
    bull_thesis: list[str] = []
    bear_thesis: list[str] = []
    latest_changes: list[dict] = []
    confidence_values: list[float] = []
    tags: set[str] = set()

    for entry in entries[:30]:
        summary = str(entry.get("summary") or "")
        text = str(entry.get("_full_text") or summary)
        lines = [
            line
            for line in [summary, *plain_research_lines(text, limit=40)]
            if not is_dossier_noise_line(line)
        ]
        for tag in entry.get("tags") or []:
            tags.add(str(tag))
        confidence_values.append(clamp_confidence(entry.get("confidence") or entry.get("source_confidence")))
        latest_changes.append(
            {
                "date": entry.get("date"),
                "type": entry.get("type"),
                "file_name": entry.get("file_name"),
                "summary": summary,
                "confidence": entry.get("confidence") or entry.get("source_confidence"),
            }
        )
        for line in lines:
            has_bull_marker = "강세:" in line
            has_bear_marker = "약세:" in line
            if line_has_any(line, DOSSIER_FACT_TERMS) and not (has_bull_marker or has_bear_marker):
                fact = clean_dossier_signal(line, "generic")
                if fact:
                    add_unique_text(consensus_facts, fact, limit=8)
            if has_bull_marker or (line_has_any(line, DOSSIER_POSITIVE_TERMS) and not has_bear_marker):
                add_dossier_signal(bull_thesis, line, "bull", limit=6)
            if has_bear_marker or (line_has_any(line, DOSSIER_NEGATIVE_TERMS) and not has_bull_marker):
                add_dossier_signal(bear_thesis, line, "bear", limit=6)

    if not consensus_facts:
        for entry in entries[:6]:
            add_unique_text(consensus_facts, entry.get("summary"), limit=6)
    if not bull_thesis:
        add_unique_text(
            bull_thesis,
            f"{company_name}의 강세 논거는 {profile_focus}가 실제 수치와 신규 자료에서 반복 확인되는 경우입니다.",
        )
    if not bear_thesis:
        add_unique_text(
            bear_thesis,
            f"{company_name}의 약세 논거는 핵심 KPI 둔화, 마진 훼손, 경쟁 심화 또는 투자 심리 악화가 동시에 나타나는 경우입니다.",
        )

    cruxes = [
        f"{watch_kpis[0] if watch_kpis else '핵심 성장 KPI'}가 다음 데이터에서 개선 추세를 유지하는가?",
        "현재 밸류에이션이 성장률, 마진, 현금흐름 품질을 과도하게 선반영하고 있지 않은가?",
        "최근 입력 자료의 강세/약세 신호 중 실제 숫자로 확인 가능한 항목은 무엇인가?",
    ]
    observables = [
        f"{metric}: 다음 실적/공시/뉴스에서 방향성 확인"
        for metric in watch_kpis[:5]
    ]
    if not observables:
        observables = [
            "매출 성장률: 다음 실적에서 추세 확인",
            "마진 품질: 비용 구조와 가격 결정력 확인",
            "현금흐름: 투자 확대와 현금 소진 균형 확인",
        ]

    confidence = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else 0.65
    bull_summary = representative_thesis_line(
        bull_thesis,
        f"{company_name}의 강세 논거는 {profile_focus}가 실제 수치와 신규 자료에서 반복 확인되는 경우입니다.",
        mode="bull",
    )
    bear_summary = representative_thesis_line(
        bear_thesis,
        f"{company_name}의 약세 논거는 핵심 KPI 둔화, 마진 훼손, 경쟁 심화 또는 투자 심리 악화가 동시에 나타나는 경우입니다.",
        mode="bear",
    )
    thesis_summary = (
        f"{company_name}({ticker})의 최신 Dossier는 {len(entries)}개 고유 저장 자료를 바탕으로 "
        f"{profile_focus}를 핵심 투자 논거로 추적합니다. "
        f"강세는 {bull_summary} / 약세는 {bear_summary}입니다."
    )
    invalidation_conditions = [
        "핵심 성장 KPI가 2개 분기 연속 약화",
        "기존 강세 논거를 뒷받침하던 수요·마진·현금흐름 지표가 동시에 후퇴",
        "새 자료의 부정 신호가 반복 입력되고 신뢰도 가중 평균이 70% 이상으로 상승",
    ]

    return {
        "ticker": ticker,
        "company_name": company_name,
        "date": storage_date.isoformat(),
        "source_count": len(entries),
        "duplicate_count": len(duplicates),
        "confidence": confidence,
        "tags": sorted(tags),
        "thesis_summary": thesis_summary,
        "consensus_facts": consensus_facts,
        "bull_thesis": bull_thesis,
        "bear_thesis": bear_thesis,
        "cruxes": cruxes,
        "observables": observables,
        "invalidation_conditions": invalidation_conditions,
        "latest_changes": latest_changes[:10],
        "duplicates": duplicates[:10],
    }


def render_dossier_markdown(payload: dict) -> str:
    def bullet(items: list[str] | list[dict], empty: str = "표시할 항목이 없습니다.") -> str:
        if not items:
            return f"- {empty}"
        lines = []
        for item in items:
            if isinstance(item, dict):
                lines.append(
                    f"- {item.get('date') or '날짜 미확인'} · {item.get('type') or '자료'} · "
                    f"{item.get('summary') or item.get('file_name') or '요약 없음'}"
                )
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)

    return f"""---
ticker: {payload["ticker"]}
type: dossier-synthesis
date: {payload["date"]}
module: research_dossier_synthesis
---

# {payload["company_name"]}({payload["ticker"]}) Dossier 합성 보고서

## 요약

{payload["thesis_summary"]}

- 고유 자료: {payload["source_count"]}개
- 중복 제외: {payload["duplicate_count"]}개
- 합성 신뢰도: {payload["confidence"]:.0%}
- 태그: {", ".join(payload["tags"]) or "없음"}

## 합의된 사실

{bullet(payload["consensus_facts"])}

## 강세 논거

{bullet(payload["bull_thesis"])}

## 약세 논거

{bullet(payload["bear_thesis"])}

## 핵심 쟁점

{bullet(payload["cruxes"])}

## 관찰 가능한 트리거

{bullet(payload["observables"])}

## 무효화 조건

{bullet(payload["invalidation_conditions"])}

## 최근 변화

{bullet(payload["latest_changes"])}
"""


def synthesize_and_save_dossier(
    ticker: str,
    settings: Settings,
    *,
    save_result: bool = True,
) -> dict:
    normalized_ticker = ensure_verified_ticker(ticker, settings)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    payload = build_dossier_payload(normalized_ticker, vault_dir)
    storage = None
    if save_result:
        markdown = render_dossier_markdown(payload)
        storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=normalized_ticker,
            report_type="dossier-synthesis",
            markdown=markdown,
            structured_payload=payload,
            manifest_entry=manifest_with_ticker_verification(normalized_ticker, {
                "summary": payload["thesis_summary"],
                "company_name": payload["company_name"],
                "source_count": payload["source_count"],
                "duplicate_count": payload["duplicate_count"],
                "source_confidence": payload["confidence"],
                "tags": payload["tags"],
                "investment_thesis": {
                    "ticker": normalized_ticker,
                    "thesis": payload["thesis_summary"],
                    "time_horizon": "상시 업데이트",
                    "bull_triggers": payload["bull_thesis"],
                    "bear_triggers": payload["bear_thesis"],
                    "invalidation_conditions": payload["invalidation_conditions"],
                    "watch_kpis": ticker_watch_kpis(normalized_ticker),
                    "valuation_assumptions": {
                        "method": "저장 자료 기반 Dossier 합성",
                        "confidence": payload["confidence"],
                    },
                    "last_updated": payload["date"],
                },
                "watch_items": [
                    {
                        "ticker": normalized_ticker,
                        "metric": item.split(":")[0],
                        "condition": item,
                        "action": "다음 정보 입력/시장일지/실적 분석에서 자동 대조",
                        "priority": "medium",
                    }
                    for item in payload["observables"][:5]
                ],
            }),
            report_date=current_storage_date(),
        )
        payload["storage"] = storage.model_dump(mode="json")
        thesis = InvestmentThesis(
            ticker=normalized_ticker,
            thesis=payload["thesis_summary"],
            time_horizon="상시 업데이트",
            bull_triggers=payload["bull_thesis"],
            bear_triggers=payload["bear_thesis"],
            invalidation_conditions=payload["invalidation_conditions"],
            watch_kpis=ticker_watch_kpis(normalized_ticker),
            valuation_assumptions={
                "method": "저장 자료 기반 Dossier 합성",
                "confidence": payload["confidence"],
            },
            last_updated=payload["date"],
        )
        watch_items = [
            WatchItem(
                ticker=normalized_ticker,
                metric=item.split(":")[0],
                condition=item,
                action="다음 정보 입력/시장일지/실적 분석에서 자동 대조",
                priority="medium",
            )
            for item in payload["observables"][:5]
        ]
        upsert_ticker_thesis_snapshot(
            vault_dir=vault_dir,
            ticker=normalized_ticker,
            company_name=payload["company_name"],
            investment_thesis=thesis,
            watch_items=watch_items,
            source_entry={
                "type": "dossier-synthesis",
                "date": payload["date"],
                "file_name": storage.file_name if storage else None,
                "relative_path": storage.relative_path if storage else None,
            },
            confidence=payload["confidence"],
        )
    return {"status": "success", "module": "dossier_synthesis", **payload}


def dossier_candidate_tickers(settings: Settings, limit: int = 30) -> list[str]:
    tickers: set[str] = set()
    for ticker in portfolio_calendar_tickers(settings):
        if ticker and ticker not in SPECIAL_RESEARCH_KEYS and ticker != "CASH":
            tickers.add(normalize_ticker(ticker))
    try:
        interest_payload = read_interest_list(settings)
        for item in interest_payload.get("tickers", []):
            if isinstance(item, dict) and item.get("ticker"):
                tickers.add(ensure_verified_ticker(str(item["ticker"]), settings))
    except Exception:
        pass
    try:
        vault_dir = resolve_vault_dir(settings.research_vault_dir)
        for entry in read_manifest(vault_dir):
            ticker = normalize_ticker(str(entry.get("ticker") or ""))
            if ticker and ticker not in SPECIAL_RESEARCH_KEYS and ticker != "UNKNOWN":
                tickers.add(ticker)
    except Exception:
        pass
    return sorted(tickers)[: max(1, min(limit, 100))]


def dossier_refresh_candidates_from_duplicate_review(settings: Settings, limit: int = 8) -> list[dict]:
    review = read_json_store(storage_duplicate_review_path(settings), {})
    if not review:
        review = build_storage_duplicate_review(settings, limit=max(limit * 3, 20), save_result=False)
    candidates: list[dict] = []
    seen: set[str] = set()
    for item in review.get("ticker_breakdown") or []:
        ticker = normalize_ticker(str(item.get("ticker") or ""))
        if (
            not ticker
            or ticker in seen
            or ticker in SPECIAL_RESEARCH_KEYS
            or ticker in {"UNKNOWN", "CASH"}
        ):
            continue
        seen.add(ticker)
        candidates.append(
            {
                "ticker": ticker,
                "company_name": item.get("company_name") or ticker_company_name(ticker),
                "duplicate_group_count": int(item.get("duplicate_group_count") or 0),
                "duplicate_entry_count": int(item.get("duplicate_entry_count") or 0),
                "reason": "중복 리뷰에서 대표 자료 재합성이 필요한 종목으로 선별됨",
            }
        )
        if len(candidates) >= max(limit, 1):
            break
    return candidates


def run_deduped_dossier_refresh_queue(
    settings: Settings,
    *,
    limit: int = 8,
    save_result: bool = True,
) -> dict:
    candidates = dossier_refresh_candidates_from_duplicate_review(settings, limit=limit)
    refreshed: list[dict] = []
    failed: list[dict] = []
    skipped: list[dict] = []

    for candidate in candidates:
        ticker = candidate["ticker"]
        try:
            preview = synthesize_and_save_dossier(ticker, settings, save_result=False)
            if int(preview.get("source_count") or 0) <= 0:
                skipped.append(
                    {
                        **candidate,
                        "reason": "Dossier에 사용할 검증된 고유 자료가 없어 저장을 건너뜀",
                    }
                )
                continue
            result = synthesize_and_save_dossier(ticker, settings, save_result=save_result)
            refreshed.append(
                {
                    "ticker": ticker,
                    "company_name": result.get("company_name") or candidate.get("company_name"),
                    "source_count": result.get("source_count"),
                    "duplicate_count": result.get("duplicate_count"),
                    "confidence": result.get("confidence"),
                    "storage": result.get("storage"),
                    "reason": candidate.get("reason"),
                }
            )
        except Exception as exc:
            message = provider_error_message(exc, settings)
            if "공식 티커" in message or "확인되지 않았습니다" in message:
                skipped.append({**candidate, "reason": message})
            else:
                failed.append({**candidate, "error": message})

    payload = {
        "status": "success" if not failed else "partial",
        "module": "deduped_dossier_refresh_queue",
        "as_of": current_storage_timestamp(),
        "candidate_count": len(candidates),
        "refreshed_count": len(refreshed),
        "failed_count": len(failed),
        "skipped_count": len(skipped),
        "candidates": candidates,
        "refreshed": refreshed,
        "failed": failed,
        "skipped": skipped,
        "next_actions": [
            "갱신된 Dossier의 강세/약세 논거가 대시보드 최신 투자 논거에 반영됐는지 확인하세요.",
            "실패 또는 스킵 종목은 티커 인증 상태와 원천 저장 자료 품질을 먼저 점검하세요.",
            "중복 리뷰가 새로 생성되면 이 큐를 다시 실행해 대표 자료 기준을 갱신하세요.",
        ],
    }
    if save_result:
        write_json_store(dossier_refresh_queue_status_path(settings), payload)
        status = read_json_store(research_automation_status_path(settings), {})
        if isinstance(status, dict):
            status["last_deduped_dossier_refresh"] = {
                "updated_at": payload["as_of"],
                "candidate_count": payload["candidate_count"],
                "refreshed_count": payload["refreshed_count"],
                "failed_count": payload["failed_count"],
                "skipped_count": payload["skipped_count"],
            }
            write_json_store(research_automation_status_path(settings), status)
    return payload


def _portfolio_thesis_date_age_days(source_date: object) -> int | None:
    if not source_date:
        return None
    try:
        parsed = date.fromisoformat(str(source_date)[:10])
    except ValueError:
        return None
    return (current_storage_date() - parsed).days


def build_daily_portfolio_thesis_overview(settings: Settings, vault_dir: Path) -> dict:
    response = portfolio_store_response(settings)
    by_ticker: dict[str, dict] = {}
    for portfolio in response.portfolios:
        for holding in portfolio.holdings:
            ticker = normalize_ticker(holding.ticker)
            if not ticker or ticker == "UNKNOWN":
                continue
            record = by_ticker.setdefault(
                ticker,
                {
                    "ticker": ticker,
                    "company_name": holding.name or ticker,
                    "market_value": 0.0,
                    "portfolios": [],
                },
            )
            if holding.name and record["company_name"] == ticker:
                record["company_name"] = holding.name
            if holding.market_value is not None:
                record["market_value"] += float(holding.market_value)
            if portfolio.portfolio_name not in record["portfolios"]:
                record["portfolios"].append(portfolio.portfolio_name)

    items: list[dict] = []
    for ticker, record in by_ticker.items():
        verification = verify_ticker_symbol(ticker, settings)
        official_symbol = normalize_ticker(verification.official_symbol or ticker)
        company_name = verification.company_name or record["company_name"] or official_symbol
        try:
            snapshot = read_ticker_thesis_snapshot(vault_dir, official_symbol)
        except Exception:
            snapshot = None
        age_days = _portfolio_thesis_date_age_days((snapshot or {}).get("source_date"))
        confidence = (snapshot or {}).get("confidence")
        try:
            confidence_value = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            confidence_value = None
        bear_triggers = (snapshot or {}).get("bear_triggers") or []
        status = "정상"
        action = "새 자료가 들어오면 기존 논거와 비교하세요."
        priority_score = 0
        if not verification.verified:
            status = "티커 인증 필요"
            action = "회사명 또는 공식 티커를 확인해 등록하세요."
            priority_score += 70
        elif not snapshot:
            status = "논거 스냅샷 필요"
            action = "Dossier 또는 저장 데이터 검색 합성을 실행하세요."
            priority_score += 60
        else:
            if age_days is not None and age_days > 14:
                status = "논거 갱신 필요"
                action = "최근 시장일지·뉴스·실적 자료를 반영해 합성을 다시 실행하세요."
                priority_score += 35
            if confidence_value is not None and confidence_value < 0.7:
                status = "신뢰도 보강 필요"
                action = "원문 수치와 공시 자료를 보강해 신뢰도를 높이세요."
                priority_score += 25
            if bear_triggers:
                priority_score += min(20, len(bear_triggers) * 5)
        priority_score += min(30, int((record.get("market_value") or 0) / 1_000_000))
        items.append(
            {
                "ticker": official_symbol,
                "company_name": company_name,
                "market_value": record.get("market_value") or 0,
                "portfolios": record["portfolios"],
                "verified": verification.verified,
                "snapshot_connected": bool(snapshot),
                "snapshot_date": (snapshot or {}).get("source_date"),
                "snapshot_age_days": age_days,
                "confidence": confidence_value,
                "summary": (snapshot or {}).get("thesis_summary") or "",
                "bull_triggers": ((snapshot or {}).get("bull_triggers") or [])[:2],
                "bear_triggers": bear_triggers[:2],
                "watch_kpis": ((snapshot or {}).get("watch_kpis") or ticker_watch_kpis(official_symbol))[:5],
                "status": status,
                "recommended_action": action,
                "priority_score": priority_score,
            }
        )
    items.sort(key=lambda item: (item["priority_score"], item["market_value"]), reverse=True)
    connected_count = sum(1 for item in items if item["snapshot_connected"])
    verified_count = sum(1 for item in items if item["verified"])
    high_priority = [
        item
        for item in items
        if item["status"] != "정상" or item.get("bear_triggers")
    ][:8]
    return {
        "portfolio_count": len(response.portfolios),
        "holding_count": len(items),
        "verified_count": verified_count,
        "snapshot_connected_count": connected_count,
        "coverage_rate": connected_count / len(items) if items else 0.0,
        "items": items[:20],
        "priority_reviews": high_priority,
    }


def build_daily_brief_payload(settings: Settings) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    manifest_entries = sorted(
        [
            entry
            for entry in read_manifest(vault_dir)
            if isinstance(entry, dict)
            and entry.get("type") not in {"daily-dossier-brief"}
        ],
        key=manifest_entry_sort_key,
        reverse=True,
    )
    tickers = dossier_candidate_tickers(settings, limit=50)
    snapshots: list[dict] = []
    for ticker in tickers:
        try:
            snapshot = read_ticker_thesis_snapshot(vault_dir, ticker)
            if snapshot:
                snapshots.append(
                    {
                        "ticker": ticker,
                        "company_name": snapshot.get("company_name") or ticker_company_name(ticker),
                        "summary": snapshot.get("thesis_summary"),
                        "confidence": snapshot.get("confidence"),
                        "updated_at": snapshot.get("updated_at"),
                    }
                )
        except Exception:
            continue
    unique_recent_entries, duplicate_recent_entries = dedupe_manifest_entries_by_similarity(
        manifest_entries,
        vault_dir,
        limit=15,
    )
    recent_entries = [
        {
            "ticker": entry.get("ticker"),
            "type": entry.get("type"),
            "date": entry.get("date"),
            "summary": entry.get("summary"),
            "confidence": entry.get("confidence") or entry.get("source_confidence"),
        }
        for entry in unique_recent_entries
    ]
    unique_market_entries, duplicate_market_entries = dedupe_manifest_entries_by_similarity(
        [
            entry
            for entry in manifest_entries
            if entry.get("ticker") in {"MARKET", "MARKET-KR", "MARKET-US", "MARKET-GLOBAL", "MACRO", "CUSTOMS"}
            and entry.get("type") not in {"daily-dossier-brief", "rag-query-synthesis"}
        ],
        vault_dir,
        limit=5,
    )
    market_entries = [
        entry
        for entry in unique_market_entries
    ]
    portfolio_overview = build_daily_portfolio_thesis_overview(settings, vault_dir)
    interest_automation = build_interest_automation_board(settings, save_result=False)
    customs_trade_reference = build_daily_customs_trade_reference(settings)
    return {
        "date": current_storage_date().isoformat(),
        "generated_at": current_storage_timestamp(),
        "portfolio_tickers": tickers,
        "snapshot_count": len(snapshots),
        "portfolio_snapshot_count": portfolio_overview["snapshot_connected_count"],
        "portfolio_holding_count": portfolio_overview["holding_count"],
        "recent_entry_count": len(recent_entries),
        "duplicate_recent_entry_count": len(duplicate_recent_entries),
        "duplicate_market_entry_count": len(duplicate_market_entries),
        "market_entries": market_entries,
        "customs_trade_reference": customs_trade_reference,
        "portfolio_overview": portfolio_overview,
        "interest_automation": interest_automation,
        "snapshots": snapshots,
        "recent_entries": recent_entries,
        "next_actions": [
            "우선 점검 종목은 포트폴리오 비중, 논거 공백, 낮은 신뢰도, 약세 논거를 함께 반영해 자동 선별됩니다.",
            "신규 입력 자료가 있는 종목은 Dossier 합성 보고서의 강세/약세 논거 변화를 먼저 확인하세요.",
            "시장일지·거시 자료는 보유 종목의 섹터 노출과 자동 대조해 다음 매매 후보 필터로 사용하세요.",
            "신뢰도 낮은 자료는 투자 결론보다 관찰 항목으로만 반영하고, 원문·공시·수치 확인 후 가중치를 높이세요.",
        ],
    }


def render_daily_brief_markdown(payload: dict) -> str:
    def entry_lines(entries: list[dict], empty: str) -> str:
        if not entries:
            return f"- {empty}"
        lines = []
        for entry in entries:
            label = entry.get("ticker") or entry.get("company_name") or "대상 미확인"
            confidence = entry.get("confidence")
            confidence_text = f" · 신뢰도 {float(confidence):.0%}" if confidence is not None else ""
            lines.append(
                f"- {entry.get('date') or entry.get('updated_at') or '날짜 미확인'} · "
                f"{label} · {entry.get('type') or 'snapshot'}{confidence_text}: "
                f"{entry.get('summary') or '요약 없음'}"
            )
        return "\n".join(lines)

    def portfolio_priority_lines(entries: list[dict]) -> str:
        if not entries:
            return "- 우선 점검 종목이 없습니다."
        lines = []
        for entry in entries:
            confidence = entry.get("confidence")
            confidence_text = f" · 신뢰도 {float(confidence):.0%}" if confidence is not None else ""
            bear_text = (
                f" · 약세: {', '.join(entry.get('bear_triggers') or [])}"
                if entry.get("bear_triggers")
                else ""
            )
            kpi_text = ", ".join(entry.get("watch_kpis") or []) or "KPI 미정"
            lines.append(
                f"- {entry.get('company_name') or entry.get('ticker')}({entry.get('ticker')}) · "
                f"{entry.get('status') or '상태 미확인'}{confidence_text}: "
                f"{entry.get('recommended_action') or '후속 점검'} "
                f"확인 KPI: {kpi_text}{bear_text}"
            )
        return "\n".join(lines)

    def interest_target_lines(payload: dict) -> str:
        targets = (payload.get("ticker_targets") or [])[:8]
        sectors = (payload.get("sector_targets") or [])[:5]
        lines: list[str] = []
        for entry in targets:
            lines.append(
                f"- {entry.get('company_name') or entry.get('ticker')}({entry.get('ticker')}) · "
                f"저장 자료 {entry.get('recent_document_count', 0)}개 · "
                f"RAG {entry.get('rag_document_count', 0)}개 · "
                f"검색 예시: {', '.join((entry.get('rag_query_examples') or [])[:2]) or '없음'}"
            )
        for entry in sectors:
            lines.append(
                f"- {entry.get('name')} · {entry.get('region') or 'GLOBAL'} · "
                f"저장 자료 {entry.get('recent_document_count', 0)}개 · "
                f"검색 예시: {', '.join((entry.get('rag_query_examples') or [])[:2]) or '없음'}"
            )
        return "\n".join(lines) if lines else "- 관심목록 수집 대상이 없습니다."

    portfolio_overview = payload.get("portfolio_overview") or {}
    interest_automation = payload.get("interest_automation") or {}
    customs_reference = payload.get("customs_trade_reference") or {}
    customs_lines = []
    if customs_reference:
        customs_lines.extend(customs_reference.get("key_takeaways") or [])
        customs_lines.extend(customs_reference.get("sector_implications") or [])
        if customs_reference.get("warnings"):
            customs_lines.extend([f"경고: {item}" for item in customs_reference.get("warnings", [])])

    return f"""---
ticker: MARKET
type: daily-dossier-brief
date: {payload["date"]}
module: research_automation_daily_brief
---

# 일일 리서치 브리핑

## 시스템 상태

- 생성 시각: {payload["generated_at"]}
- 연결 종목: {len(payload["portfolio_tickers"])}개
- 최신 Dossier 스냅샷: {payload["snapshot_count"]}개
- 포트폴리오 논거 연결: {portfolio_overview.get("snapshot_connected_count", 0)}/{portfolio_overview.get("holding_count", 0)}개
- 최근 저장 자료 반영: {payload["recent_entry_count"]}개

## 시장/거시 입력

{entry_lines(payload["market_entries"], "최근 시장일지 또는 거시 자료가 없습니다.")}

## 관세청 수출입/재고 참고자료

{chr(10).join(f"- {item}" for item in customs_lines) if customs_lines else "- 오늘은 관세청 1일/11일/21일 자동 점검일이 아니거나 표시할 자료가 없습니다."}

## 종목별 최신 논거

{entry_lines(payload["snapshots"], "아직 Dossier 스냅샷이 없습니다.")}

## 포트폴리오 우선 점검

{portfolio_priority_lines((portfolio_overview.get("priority_reviews") or [])[:8])}

## 관심목록 자동 수집 대상

{interest_target_lines(interest_automation)}

## 최근 저장 자료

{entry_lines(payload["recent_entries"], "최근 저장 자료가 없습니다.")}

## 다음 액션

{chr(10).join(f"- {item}" for item in payload["next_actions"])}
"""


def save_daily_brief(payload: dict, settings: Settings) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    markdown = render_daily_brief_markdown(payload)
    storage = save_research_markdown(
        vault_dir=vault_dir,
        ticker="MARKET",
        report_type="daily-dossier-brief",
        markdown=markdown,
        structured_payload=payload,
        manifest_entry=manifest_with_ticker_verification("MARKET", {
            "summary": f"{payload['date']} 일일 리서치 브리핑: {payload['snapshot_count']}개 Dossier 스냅샷 반영",
            "source_confidence": 0.78,
            "tags": ["daily_brief", "dossier", "automation", "market"],
        }),
        report_date=current_storage_date(),
    )
    payload["storage"] = storage.model_dump(mode="json")
    write_json_store(
        latest_daily_brief_path(settings),
        {
            "updated_at": current_storage_timestamp(),
            "payload": payload,
            "storage": payload["storage"],
        },
    )
    return payload


def read_latest_daily_brief(settings: Settings) -> dict:
    return read_json_store(latest_daily_brief_path(settings), {})


def safe_rag_memory_status(vault_dir: Path) -> dict:
    try:
        return rag_memory_status(vault_dir)
    except Exception as exc:
        return {
            "document_count": 0,
            "snapshot_count": 0,
            "warning": f"RAG 색인 상태 확인 실패: {exc}",
        }


def build_research_automation_feature_status(settings: Settings) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    manifest_entries = read_manifest(vault_dir)
    rag_status_payload = safe_rag_memory_status(vault_dir)
    news_payload = read_news_inbox(settings)
    news_items = [
        item for item in news_payload.get("items", []) if isinstance(item, dict)
    ]
    news_unpromoted_count = sum(1 for item in news_items if not item.get("promoted"))
    news_quality_issue_count = sum(
        1
        for item in news_items
        if (item.get("capture_quality") or {}).get("status") not in {None, "정상"}
    )
    latest_brief = read_latest_daily_brief(settings)
    last_run = read_json_store(research_automation_status_path(settings), {})
    duplicate_review = read_json_store(storage_duplicate_review_path(settings), {})
    refresh_queue = read_json_store(dossier_refresh_queue_status_path(settings), {})
    latest_interest_targets = read_json_store(interest_collection_targets_path(settings), {})
    interest_payload = latest_interest_targets.get("payload") if isinstance(latest_interest_targets, dict) else {}
    if not isinstance(interest_payload, dict):
        interest_payload = {}
    latest_brief_payload = latest_brief.get("payload") if isinstance(latest_brief, dict) else {}
    if not isinstance(latest_brief_payload, dict):
        latest_brief_payload = {}
    source_tags = {
        tag
        for entry in manifest_entries
        for tag in (entry.get("tags") or [])
        if isinstance(tag, str)
    }
    duplicate_count = (
        sum(1 for entry in manifest_entries if entry.get("duplicate_reason"))
        + int(latest_brief_payload.get("duplicate_recent_entry_count") or 0)
        + int(latest_brief_payload.get("duplicate_market_entry_count") or 0)
    )
    if isinstance(duplicate_review, dict):
        duplicate_count = max(duplicate_count, int(duplicate_review.get("duplicate_entry_count") or 0))
    dossier_count = sum(1 for entry in manifest_entries if entry.get("type") == "dossier-synthesis")
    daily_brief_count = sum(1 for entry in manifest_entries if entry.get("type") == "daily-dossier-brief")
    rag_document_count = rag_status_payload.get("document_count")
    if not rag_document_count and isinstance(last_run, dict):
        rag_document_count = last_run.get("rag_updated_count")
    rag_snapshot_count = rag_status_payload.get("snapshot_count")
    if not rag_snapshot_count and isinstance(last_run, dict):
        rag_snapshot_count = last_run.get("rag_ticker_count")
    payload = {
        "status": "success",
        "module": "research_automation_feature_status",
        "as_of": current_storage_timestamp(),
        "features": [
            {
                "name": "Pulls",
                "status": "active",
                "detail": "신한/네이버 리서치, 웹사이트 입력, 파일 입력, 시장일지, 보유/관심 종목 후보를 수집 흐름에 연결했습니다.",
                "interest_target_count": interest_payload.get("target_count", 0),
            },
            {
                "name": "De-dupes",
                "status": "active",
                "detail": "source_url/content_hash exact match와 제목·본문 토큰 유사도 기반 중복 제거를 Dossier/일일 브리핑에 적용했습니다.",
                "duplicate_count": duplicate_count,
            },
            {
                "name": "Embeds",
                "status": "active",
                "detail": "SQLite RAG 메모리 색인으로 티커, 태그, 요약, 본문 검색을 지원합니다.",
                "document_count": rag_document_count,
                "snapshot_count": rag_snapshot_count,
            },
            {
                "name": "Tags",
                "status": "active",
                "detail": "종목/섹터/테마/리스크/실적/수급/금리/기관/인물/AI/에너지/우주/방산/바이오/소비재 태그를 자동 부여합니다.",
                "tag_count": len(source_tags),
            },
            {
                "name": "Syntheses",
                "status": "active",
                "detail": "7개 스킬의 리포트와 저장 자료를 Dossier 합성 보고서로 통합합니다.",
                "dossier_count": dossier_count,
            },
            {
                "name": "Consensus facts",
                "status": "active",
                "detail": "여러 자료에서 반복 등장하는 매출, 마진, 현금흐름, 계약, 정책, 시장 사실을 합의된 사실로 추출합니다.",
            },
            {
                "name": "Bull thesis",
                "status": "active",
                "detail": "성장, 수요, 마진, 수주, 가이던스 상향 등 긍정 신호를 강세 논거로 정리합니다.",
            },
            {
                "name": "Bear thesis",
                "status": "active",
                "detail": "둔화, 리스크, 마진 압박, 규제, 현금 소진 등 부정 신호를 약세 논거로 정리하되 부정 문맥은 제외합니다.",
            },
            {
                "name": "Cruxes",
                "status": "active",
                "detail": "투자 판단을 좌우할 핵심 KPI, 밸류에이션, 신규 자료 검증 질문을 생성합니다.",
            },
            {
                "name": "Observables",
                "status": "active",
                "detail": "다음 실적/공시/뉴스에서 확인할 KPI와 이벤트를 추적 항목으로 저장합니다.",
            },
            {
                "name": "Delivers",
                "status": "active",
                "detail": "일일 브리핑을 저장 데이터에 적재하고 최신 브리핑 상태를 대시보드 추천 액션에서 참조합니다.",
                "daily_brief_count": daily_brief_count,
                "latest_daily_brief_date": latest_brief_payload.get("date"),
            },
        ],
        "last_run": last_run,
        "duplicate_review": duplicate_review if isinstance(duplicate_review, dict) else {},
        "dossier_refresh_queue": refresh_queue if isinstance(refresh_queue, dict) else {},
    }
    try:
        payload["dashboard_digest"] = build_research_automation_dashboard_digest(settings)
    except Exception as exc:
        payload["dashboard_digest"] = {
            "status": "warning",
            "headline": "자동화 요약 확인 필요",
            "error": provider_error_message(exc, settings),
        }
    return payload


def build_research_automation_dashboard_digest(settings: Settings) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    latest_targets = read_json_store(interest_collection_targets_path(settings), {})
    board = latest_targets.get("payload") if isinstance(latest_targets, dict) else {}
    if not isinstance(board, dict) or not board:
        try:
            board = build_interest_automation_board(settings, save_result=False)
        except Exception as exc:
            board = {"status": "warning", "error": provider_error_message(exc, settings)}

    status = read_json_store(research_automation_status_path(settings), {})
    duplicate_review = read_json_store(storage_duplicate_review_path(settings), {})
    refresh_queue = read_json_store(dossier_refresh_queue_status_path(settings), {})
    latest_brief = read_latest_daily_brief(settings)
    brief_payload = latest_brief.get("payload") if isinstance(latest_brief, dict) else {}
    if not isinstance(brief_payload, dict):
        brief_payload = {}
    rag_status_payload = safe_rag_memory_status(vault_dir)

    targets = [
        *[item for item in board.get("ticker_targets", []) if isinstance(item, dict)],
        *[item for item in board.get("sector_targets", []) if isinstance(item, dict)],
    ]
    priority_targets = sorted(
        targets,
        key=lambda item: (
            {"high": 3, "medium": 2, "low": 1}.get(str(item.get("priority")), 2),
            int(item.get("recent_document_count") or 0),
            int(item.get("rag_document_count") or 0),
        ),
        reverse=True,
    )[:5]
    duplicate_count = max(
        int(board.get("duplicate_suspected_count") or 0),
        int(duplicate_review.get("duplicate_entry_count") or 0) if isinstance(duplicate_review, dict) else 0,
    )
    failed_count = int(status.get("failed_count") or 0)
    target_count = int(board.get("target_count") or 0)
    dossier_count = int(status.get("dossier_count") or 0)
    target_rag_count = sum(int(item.get("rag_document_count") or 0) for item in targets)
    rag_document_count = max(
        int(rag_status_payload.get("document_count") or 0),
        int(status.get("rag_updated_count") or 0),
        target_rag_count,
    )
    news_payload = build_news_inbox_payload(settings, limit=10)
    news_items = news_payload.get("items") if isinstance(news_payload, dict) else []
    if not isinstance(news_items, list):
        news_items = []
    news_unpromoted_count = int(news_payload.get("unpromoted_count") or 0) if isinstance(news_payload, dict) else 0
    news_quality_issue_count = (
        int(news_payload.get("quality_issue_count") or 0) if isinstance(news_payload, dict) else 0
    )
    daily_brief_date = status.get("daily_brief_date") or brief_payload.get("date")

    tone = "ok"
    headline = "자동화 정상"
    if failed_count or duplicate_count or news_quality_issue_count:
        tone = "warning"
        headline = "확인 필요"
    if not target_count or not daily_brief_date:
        tone = "needs_action"
        headline = "업데이트 필요"

    next_actions = []
    if not target_count:
        next_actions.append("포트폴리오나 관심목록을 저장해 자동 수집 대상을 먼저 구성하세요.")
    if not daily_brief_date:
        next_actions.append("오늘 리서치 업데이트를 실행해 일일 브리핑을 생성하세요.")
    if duplicate_count:
        next_actions.append(f"중복 의심 자료 {duplicate_count}개를 Dossier 합성에서 묶어 확인하세요.")
    if failed_count:
        next_actions.append(f"자동화 실패 {failed_count}건의 API/소스 상태를 점검하세요.")
    if news_unpromoted_count:
        next_actions.append(f"뉴스 인박스 미승격 자료 {news_unpromoted_count}개를 논거/시장일지 반영 여부로 분류하세요.")
    if news_quality_issue_count:
        next_actions.append(f"뉴스 본문 추출 품질 경고 {news_quality_issue_count}개를 원문 링크나 본문 붙여넣기로 보강하세요.")
    if not next_actions:
        next_actions.append("보유·관심 대상의 새 자료를 수집하고 Dossier/일일 브리핑에 반영할 준비가 되어 있습니다.")

    return {
        "status": "success",
        "module": "research_automation_dashboard_digest",
        "tone": tone,
        "headline": headline,
        "as_of": current_storage_timestamp(),
        "target_count": target_count,
        "ticker_target_count": int(board.get("ticker_target_count") or 0),
        "sector_target_count": int(board.get("sector_target_count") or 0),
        "portfolio_linked_count": int(board.get("portfolio_linked_count") or 0),
        "rag_connected_count": int(board.get("rag_connected_count") or 0),
        "rag_document_count": rag_document_count,
        "duplicate_suspected_count": duplicate_count,
        "duplicate_group_count": int(duplicate_review.get("duplicate_group_count") or 0)
        if isinstance(duplicate_review, dict)
        else 0,
        "last_deduped_dossier_refresh": refresh_queue
        if isinstance(refresh_queue, dict) and refresh_queue
        else status.get("last_deduped_dossier_refresh"),
        "dossier_count": dossier_count,
        "failed_count": failed_count,
        "daily_brief_date": daily_brief_date,
        "news_inbox_count": len(news_items),
        "news_unpromoted_count": news_unpromoted_count,
        "news_quality_issue_count": news_quality_issue_count,
        "last_run_at": status.get("updated_at"),
        "priority_targets": [
            {
                "label": item.get("company_name") or item.get("name") or item.get("ticker") or "대상 미확인",
                "key": item.get("ticker") or item.get("name") or "",
                "source": item.get("source") or item.get("scope") or "interest",
                "priority": item.get("priority") or "medium",
                "recent_document_count": item.get("recent_document_count") or 0,
                "rag_document_count": item.get("rag_document_count") or 0,
                "duplicate_suspected_count": item.get("duplicate_suspected_count") or 0,
                "next_action": item.get("next_action"),
            }
            for item in priority_targets
        ],
        "next_actions": next_actions[:5],
        "automation_steps": board.get("automation_steps") or [
            "Pulls: 보유·관심 대상의 뉴스, 공시, 리포트, 시장일지를 수집합니다.",
            "De-dupes: 중복 기사와 리포트를 제목·본문 유사도로 묶습니다.",
            "Embeds/Tags: 저장 데이터를 RAG 색인과 자동 태그에 연결합니다.",
            "Syntheses/Delivers: Dossier와 일일 브리핑으로 합성해 대시보드에 반영합니다.",
        ],
    }


def run_research_automation_pipeline(
    settings: Settings,
    *,
    limit: int = 30,
    save_result: bool = True,
) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    source_results: list[dict] = []
    for name, refresh_func in [
        ("shinhan_research", refresh_shinhan_research_cache),
        ("naver_research", refresh_naver_research_cache),
    ]:
        try:
            source_results.append(
                {
                    "source": name,
                    "result": refresh_func(settings, limit=5, force=False, save_result=save_result),
                }
            )
        except Exception as exc:
            source_results.append({"source": name, "status": "failed", "error": str(exc)})

    rag_backfill = backfill_research_memory_documents_from_manifest(vault_dir)
    dossier_results: list[dict] = []
    failed: list[dict] = []
    for ticker in dossier_candidate_tickers(settings, limit=limit):
        try:
            dossier = synthesize_and_save_dossier(ticker, settings, save_result=save_result)
            dossier_results.append(
                {
                    "ticker": ticker,
                    "source_count": dossier.get("source_count"),
                    "duplicate_count": dossier.get("duplicate_count"),
                    "confidence": dossier.get("confidence"),
                    "storage": dossier.get("storage"),
                }
            )
        except Exception as exc:
            failed.append({"ticker": ticker, "error": str(exc)})

    daily_payload = build_daily_brief_payload(settings)
    daily_brief = save_daily_brief(daily_payload, settings) if save_result else daily_payload
    interest_board = build_interest_automation_board(settings, save_result=save_result)
    automation_digest = build_research_automation_dashboard_digest(settings)
    result = {
        "status": "success",
        "module": "research_automation_pipeline",
        "ran_at": current_storage_timestamp(),
        "source_results": source_results,
        "rag_backfill": {
            "updated_count": rag_backfill.get("updated_count"),
            "ticker_count": len(rag_backfill.get("tickers", [])),
        },
        "dossier_count": len(dossier_results),
        "dossiers": dossier_results,
        "failed": failed,
        "daily_brief": daily_brief,
        "interest_board": {
            "target_count": interest_board.get("target_count"),
            "ticker_target_count": interest_board.get("ticker_target_count"),
            "sector_target_count": interest_board.get("sector_target_count"),
            "portfolio_linked_count": interest_board.get("portfolio_linked_count"),
            "rag_connected_count": interest_board.get("rag_connected_count"),
            "thesis_connected_count": interest_board.get("thesis_connected_count"),
            "duplicate_suspected_count": interest_board.get("duplicate_suspected_count"),
            "automation_steps": interest_board.get("automation_steps"),
            "next_actions": interest_board.get("next_actions"),
        },
        "automation_digest": automation_digest,
        "news_inbox": build_news_inbox_payload(settings, limit=10),
    }
    result["automation_digest"].update(
        {
            "dossier_count": result["dossier_count"],
            "failed_count": len(failed),
            "daily_brief_date": daily_brief.get("date") if isinstance(daily_brief, dict) else None,
            "last_run_at": result["ran_at"],
        }
    )
    write_json_store(
        research_automation_status_path(settings),
        {
            "updated_at": result["ran_at"],
            "dossier_count": result["dossier_count"],
            "failed_count": len(failed),
            "rag_updated_count": result["rag_backfill"]["updated_count"],
            "rag_ticker_count": result["rag_backfill"]["ticker_count"],
            "daily_brief_date": daily_brief.get("date") if isinstance(daily_brief, dict) else None,
            "pull_target_count": interest_board.get("target_count"),
            "duplicate_suspected_count": interest_board.get("duplicate_suspected_count"),
            "rag_connected_count": interest_board.get("rag_connected_count"),
            "save_result": save_result,
            "news_inbox_count": result["news_inbox"].get("count"),
            "news_unpromoted_count": result["news_inbox"].get("unpromoted_count"),
        },
    )
    return result


def read_news_inbox(settings: Settings) -> dict:
    payload = read_json_store(news_inbox_path(settings), {"items": [], "updated_at": None})
    if not isinstance(payload, dict):
        return {"items": [], "updated_at": None}
    items = payload.get("items")
    if not isinstance(items, list):
        payload["items"] = []
    return payload


def write_news_inbox(settings: Settings, payload: dict) -> None:
    payload["updated_at"] = current_storage_timestamp()
    write_json_store(news_inbox_path(settings), payload)


def find_news_inbox_item(items: list[dict], item_id: str) -> dict | None:
    return next((entry for entry in items if str(entry.get("id") or "") == item_id), None)


def news_item_fingerprint(title: str, raw_content: str, source_url: str | None = None) -> str:
    if source_url:
        return content_fingerprint(f"url::{source_url.strip().lower()}")
    return content_fingerprint("\n".join([title.strip().lower(), raw_content.strip()]))


def news_scope_label(scope: str) -> str:
    return {
        "INBOX": "일반 뉴스",
        "MACRO": "거시/경제",
        "SECTOR": "섹터/산업",
        "MARKET": "시장 흐름",
        "POLICY": "정책/규제",
        "RATES": "금리/환율",
        "FLOWS": "수급/자금 흐름",
    }.get(scope, scope)


def build_news_inbox_payload(settings: Settings, limit: int = 30) -> dict:
    payload = read_news_inbox(settings)
    items = [
        item
        for item in payload.get("items", [])
        if isinstance(item, dict)
    ]
    items = sorted(
        items,
        key=lambda item: item.get("created_at") or item.get("updated_at") or "",
        reverse=True,
    )
    return {
        "status": "success",
        "module": "news_inbox_list",
        "updated_at": payload.get("updated_at"),
        "count": len(items),
        "unpromoted_count": sum(1 for item in items if not item.get("promoted")),
        "quality_issue_count": sum(
            1
            for item in items
            if (item.get("capture_quality") or {}).get("status") not in {None, "정상"}
        ),
        "items": items[: max(1, min(int(limit or 30), 100))],
    }


def update_news_inbox_item_action(item: dict, action: str) -> dict:
    now = current_storage_timestamp()
    normalized_action = str(action or "").strip().lower()
    if normalized_action in {"hold", "보류"}:
        item["review_status"] = "보류"
        item["held_at"] = now
        item["updated_at"] = now
        message = "뉴스를 보류 상태로 표시했습니다."
    elif normalized_action in {"restore", "pending", "대기"}:
        item["review_status"] = "대기"
        item["updated_at"] = now
        message = "뉴스를 대기 상태로 되돌렸습니다."
    elif normalized_action in {"market_journal", "market", "시장일지"}:
        item["scope"] = "MARKET"
        item["scope_label"] = news_scope_label("MARKET")
        item["review_status"] = "시장일지 후보"
        item["market_journal_candidate"] = True
        item["updated_at"] = now
        tags = sorted(set([*(item.get("tags") or []), "market_journal_candidate"]))
        item["tags"] = tags
        message = "뉴스를 시장일지 반영 후보로 표시했습니다."
    else:
        raise HTTPException(status_code=422, detail="지원하지 않는 뉴스 처리 액션입니다.")
    return {
        "status": "success",
        "module": "news_inbox_action",
        "action": normalized_action,
        "message": message,
        "item": item,
    }


def infer_market_from_news_item(item: dict) -> str:
    scope = str(item.get("scope") or "").upper()
    text = " ".join(
        str(value or "")
        for value in [
            item.get("title"),
            item.get("summary"),
            item.get("raw_content"),
            " ".join(item.get("tags") or []),
        ]
    ).upper()
    text_without_translation_markers = text.replace("한국어", "")
    if "KOSPI" in text_without_translation_markers or "KOSDAQ" in text_without_translation_markers or any(
        keyword in text
        for keyword in ["한국 증시", "한국 시장", "국내", "코스피", "코스닥", "원화", "관세청", "수출입", "국내 증시"]
    ):
        return "KR"
    if any(
        keyword in text
        for keyword in ["NASDAQ", "S&P", "NYSE", "DOW", "미국", "연준", "FOMC", "달러"]
    ):
        return "US"
    if scope in {"MARKET-KR", "KR"}:
        return "KR"
    if scope in {"MARKET-US", "US"}:
        return "US"
    return "GLOBAL"


def market_journal_existing_summary(
    settings: Settings,
    market: str,
    session_date: str,
) -> str:
    payload = read_market_close_journal(settings)
    for raw_entry in payload.get("entries", []):
        if not isinstance(raw_entry, dict):
            continue
        if raw_entry.get("market") == market and raw_entry.get("session_date") == session_date:
            return str(raw_entry.get("raw_summary") or "").strip()
    return ""


def save_news_item_to_market_journal(
    item: dict,
    settings: Settings,
) -> MarketCloseReviewResponse:
    market = infer_market_from_news_item(item)
    session_date = current_storage_date().isoformat()
    report_date = current_storage_date()
    title = compact_interest_text(item.get("title") or "뉴스 인박스 자료", 90)
    source_url = str(item.get("source_url") or "").strip()
    summary = str(item.get("raw_content") or item.get("summary") or "").strip()
    existing_summary = market_journal_existing_summary(settings, market, session_date)
    source_line = f"출처: {source_url}" if source_url else "출처: 뉴스 인박스"
    news_block = "\n".join(
        value
        for value in [
            f"[뉴스 인박스 반영] {title}",
            source_line,
            summary,
        ]
        if value
    )
    combined_summary = "\n\n".join(
        value for value in [existing_summary, news_block] if value
    )

    cleaned_summary = clean_market_summary_text(combined_summary)
    sentiment, risk_level, regime = infer_market_close_sentiment(cleaned_summary)
    tags = sorted(set([*infer_market_tags(cleaned_summary), "news_inbox_market_journal"]))
    auto_utilization_focus = build_auto_market_utilization_focus(
        market=market,
        tags=tags,
        sentiment=sentiment,
        risk_level=risk_level,
        regime=regime,
        settings=settings,
    )
    interest_implications = build_market_interest_implications(
        raw_summary=cleaned_summary,
        tags=tags,
        settings=settings,
    )
    now = current_storage_timestamp()
    entry = MarketCloseEntry(
        entry_id=f"{market}-{session_date}",
        market=market,
        session_date=session_date,
        raw_summary=cleaned_summary,
        sentiment=sentiment,
        risk_level=risk_level,
        regime=regime,
        auto_utilization_focus=auto_utilization_focus,
        interest_implications=interest_implications,
        market_index_snapshot=[],
        key_drivers=summarize_market_lines(cleaned_summary),
        sector_implications=build_sector_implications(cleaned_summary, tags),
        portfolio_actions=build_market_portfolio_actions(sentiment, risk_level, regime),
        next_session_watch=build_market_next_watch(tags, market),
        tags=tags,
        attachment=None,
        created_at=now,
        updated_at=now,
    )
    store = read_market_close_journal(settings)
    existing_entries = [
        MarketCloseEntry.model_validate(raw_entry)
        for raw_entry in store.get("entries", [])
        if isinstance(raw_entry, dict)
    ]
    prior_entries = [existing for existing in existing_entries if existing.entry_id != entry.entry_id]
    all_entries = prior_entries + [entry]
    all_entries.sort(key=lambda entry_item: (entry_item.session_date, entry_item.market, entry_item.entry_id))
    patterns, regime_summary = cumulative_market_patterns(all_entries, market)
    response = MarketCloseReviewResponse(
        entry=entry,
        history_count=len([entry_item for entry_item in all_entries if entry_item.market == market]),
        cumulative_patterns=patterns,
        recent_regime_summary=regime_summary,
        storage_path=str(market_close_journal_path(settings)),
        saved_to_research_memory=True,
        attachment=None,
        source_url_processing=None,
        capture_quality=capture_quality_status(raw_content=cleaned_summary),
    )
    write_json_store(
        market_close_journal_path(settings),
        {
            "entries": [entry_item.model_dump(mode="json") for entry_item in all_entries],
            "updated_at": current_storage_timestamp(),
        },
    )
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    response.storage = save_research_markdown(
        vault_dir=vault_dir,
        ticker=market_research_key(entry.market),
        report_type="market-close-review",
        markdown=render_market_close_markdown(response, report_date),
        structured_payload={
            "status": response.status,
            "module": response.module,
            "entry": entry.model_dump(mode="json"),
            "history_count": response.history_count,
            "cumulative_patterns": response.cumulative_patterns,
            "recent_regime_summary": response.recent_regime_summary,
            "source": "news_inbox",
        },
        manifest_entry={
            "summary": f"{entry.market} {entry.session_date} 뉴스 반영 시장일지: {entry.regime}, 심리 {entry.sentiment}, 리스크 {entry.risk_level}",
            "market": entry.market,
            "session_date": entry.session_date,
            "sentiment": entry.sentiment,
            "risk_level": entry.risk_level,
            "regime": entry.regime,
            "tags": entry.tags,
            "source": "news_inbox",
            "source_title": title,
            "auto_utilization_focus": entry.auto_utilization_focus,
            "interest_implications": entry.interest_implications,
        },
        report_date=report_date,
        file_suffix="news-inbox",
    )
    return response


def build_news_item_from_payload(payload: dict, settings: Settings) -> dict:
    raw_content = str(payload.get("raw_content") or payload.get("rawContent") or "").strip()
    source_url = str(payload.get("source_url") or payload.get("sourceUrl") or "").strip()
    url_info = fetch_capture_source_url(source_url) if source_url else {}
    url_body_context = render_source_url_body(url_info)
    url_title_context = (
        f"웹사이트 제목: {url_info.get('title')}"
        if source_url and url_info.get("title")
        else ""
    )
    if (
        source_url
        and is_unusable_source_url(url_info)
        and not raw_content
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "뉴스 URL 본문을 추출하지 못했습니다. "
                f"{url_info.get('note') or '본문 텍스트를 직접 붙여넣으세요.'}"
            ),
        )
    combined_content = "\n\n".join(
        value for value in [raw_content, url_title_context, url_body_context] if value
    )
    if not combined_content.strip():
        raise HTTPException(status_code=422, detail="저장할 뉴스 본문 또는 웹사이트 주소가 비어 있습니다.")
    inferred_scope, scope_reason = infer_capture_ticker(combined_content, settings)
    source_type = infer_capture_source_type(combined_content, None)
    if enum_or_str_value(source_type) != "news":
        source_type = DataSourceType.NEWS
    title = (
        str(payload.get("title") or "").strip()
        or str(url_info.get("title") or "").strip()
        or infer_capture_title(combined_content, None)
    )
    source_url_for_storage = (
        url_info.get("final_url")
        or url_info.get("source_url")
        or source_url
        or None
    )
    tags = infer_capture_tags(
        combined_content,
        ["news_inbox", "auto_classified", f"auto_scope:{scope_reason}"],
    )
    if source_url:
        tags.extend(["url_input", "web_capture"])
    quality_status = capture_quality_status(
        raw_content=combined_content,
        attachment_info=None,
        source_url_processing=url_info if source_url else None,
    )
    fingerprint = news_item_fingerprint(title, combined_content, source_url_for_storage)
    now = current_storage_timestamp()
    return {
        "id": fingerprint[:16],
        "fingerprint": fingerprint,
        "title": title,
        "scope": inferred_scope,
        "scope_label": news_scope_label(inferred_scope),
        "scope_reason": scope_reason,
        "source_type": "news",
        "source_url": source_url_for_storage,
        "raw_content": combined_content,
        "summary": summarize_capture(combined_content),
        "confidence": float(payload.get("confidence") or 0.78),
        "tags": sorted(set(tags)),
        "capture_quality": quality_status,
        "source_url_processing": url_info if source_url else None,
        "input_preview": capture_preview_text(
            "\n".join(value for value in [raw_content, f"웹사이트 주소: {source_url}" if source_url else ""] if value)
        ),
        "document_preview": capture_preview_text(url_info.get("text") or url_info.get("note")),
        "created_at": now,
        "updated_at": now,
        "promoted": False,
        "promoted_storage": None,
    }


@app.get(
    "/api/v1/news/inbox",
    dependencies=[Depends(verify_user_token)],
)
def get_news_inbox(
    limit: int = 30,
    settings: Settings = Depends(get_settings),
) -> dict:
    return build_news_inbox_payload(settings, limit=limit)


@app.post(
    "/api/v1/news/inbox/ingest",
    dependencies=[Depends(verify_user_token)],
)
def ingest_news_inbox(
    payload: dict = Body(...),
    settings: Settings = Depends(get_settings),
) -> dict:
    inbox = read_news_inbox(settings)
    items = [item for item in inbox.get("items", []) if isinstance(item, dict)]
    item = build_news_item_from_payload(payload, settings)
    duplicate = next(
        (
            existing
            for existing in items
            if existing.get("fingerprint") == item["fingerprint"]
            or (
                item.get("source_url")
                and existing.get("source_url")
                and str(existing.get("source_url")).lower() == str(item.get("source_url")).lower()
            )
        ),
        None,
    )
    if duplicate:
        duplicate["updated_at"] = current_storage_timestamp()
        duplicate["duplicate_seen_count"] = int(duplicate.get("duplicate_seen_count") or 1) + 1
        duplicate["last_duplicate_summary"] = item["summary"]
        saved_item = duplicate
        is_duplicate = True
    else:
        items.insert(0, item)
        saved_item = item
        is_duplicate = False
    inbox["items"] = items[:500]
    write_news_inbox(settings, inbox)
    return {
        "status": "success",
        "module": "news_inbox",
        "item": saved_item,
        "duplicate_check": {
            "is_duplicate_suspected": is_duplicate,
            "reason": "같은 URL 또는 같은 본문 지문이 뉴스 인박스에 이미 있습니다." if is_duplicate else "신규 뉴스로 저장했습니다.",
        },
        "count": len(inbox["items"]),
        "unpromoted_count": sum(1 for entry in inbox["items"] if not entry.get("promoted")),
        "next_actions": [
            "관련 종목이나 섹터가 맞는지 확인하세요.",
            "투자 논거에 반영할 자료라면 뉴스 인박스에서 저장 데이터로 승격하세요.",
            "시장 전체 자료라면 시장일지 또는 일일 브리핑 합성에 활용하세요.",
        ],
    }


@app.post(
    "/api/v1/news/inbox/promote",
    dependencies=[Depends(verify_user_token)],
)
def promote_news_inbox_item(
    payload: dict = Body(...),
    settings: Settings = Depends(get_settings),
) -> dict:
    item_id = str(payload.get("id") or payload.get("item_id") or "").strip()
    if not item_id:
        raise HTTPException(status_code=422, detail="승격할 뉴스 ID가 비어 있습니다.")
    inbox = read_news_inbox(settings)
    items = [item for item in inbox.get("items", []) if isinstance(item, dict)]
    item = find_news_inbox_item(items, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="뉴스 인박스에서 해당 항목을 찾지 못했습니다.")
    scope = str(item.get("scope") or "INBOX").upper()
    short_title = compact_interest_text(item.get("title") or "뉴스 인박스 자료", 70)
    title = prefix_capture_title(short_title, scope, item.get("scope_reason") or "news_inbox")
    request = ResearchCaptureRequest(
        ticker=scope,
        title=title,
        raw_content=str(item.get("raw_content") or item.get("summary") or ""),
        source_type=DataSourceType.NEWS,
        source_url=item.get("source_url"),
        confidence=float(item.get("confidence") or 0.78),
        tags=sorted(set([*(item.get("tags") or []), "news_inbox_promoted"])),
        run_thesis_impact=scope not in SPECIAL_RESEARCH_KEYS,
        save_result=True,
    )
    response = save_capture_request(
        request,
        settings,
        source_url_processing=item.get("source_url_processing"),
        input_preview_override=item.get("input_preview"),
        document_preview_override=item.get("document_preview"),
    )
    item["promoted"] = True
    item["promoted_at"] = current_storage_timestamp()
    item["promoted_storage"] = (
        response.storage.model_dump(mode="json")
        if hasattr(response.storage, "model_dump")
        else response.storage
    ) if response.storage else None
    write_news_inbox(settings, {"items": items})
    return {
        "status": "success",
        "module": "news_promotion",
        "item": item,
        "capture": response.model_dump(mode="json"),
        "message": "뉴스를 저장 데이터/RAG 메모리로 승격했습니다.",
    }


@app.post(
    "/api/v1/news/inbox/action",
    dependencies=[Depends(verify_user_token)],
)
def update_news_inbox_action(
    payload: dict = Body(...),
    settings: Settings = Depends(get_settings),
) -> dict:
    item_id = str(payload.get("id") or payload.get("item_id") or "").strip()
    action = str(payload.get("action") or "").strip()
    if not item_id:
        raise HTTPException(status_code=422, detail="처리할 뉴스 ID가 비어 있습니다.")
    if not action:
        raise HTTPException(status_code=422, detail="뉴스 처리 액션이 비어 있습니다.")
    inbox = read_news_inbox(settings)
    items = [item for item in inbox.get("items", []) if isinstance(item, dict)]
    if action.strip().lower() in {"delete", "삭제"}:
        next_items = [entry for entry in items if str(entry.get("id") or "") != item_id]
        if len(next_items) == len(items):
            raise HTTPException(status_code=404, detail="뉴스 인박스에서 해당 항목을 찾지 못했습니다.")
        write_news_inbox(settings, {"items": next_items})
        return {
            "status": "success",
            "module": "news_inbox_action",
            "action": "delete",
            "message": "뉴스를 인박스에서 삭제했습니다.",
            "item_id": item_id,
            "count": len(next_items),
        }
    item = find_news_inbox_item(items, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="뉴스 인박스에서 해당 항목을 찾지 못했습니다.")
    result = update_news_inbox_item_action(item, action)
    if str(action or "").strip().lower() in {"market_journal", "market", "시장일지"}:
        journal_response = save_news_item_to_market_journal(item, settings)
        item["market_journal_promoted"] = True
        item["market_journal_promoted_at"] = current_storage_timestamp()
        item["market_journal_storage"] = (
            journal_response.storage.model_dump(mode="json")
            if journal_response.storage and hasattr(journal_response.storage, "model_dump")
            else journal_response.storage
        )
        item["market_journal_entry"] = journal_response.entry.model_dump(mode="json")
        item["review_status"] = "시장일지 반영 완료"
        result["message"] = "뉴스를 시장일지에 실제 반영하고 저장했습니다."
        result["market_journal"] = journal_response.model_dump(mode="json")
        result["item"] = item
    write_news_inbox(settings, {"items": items})
    result["count"] = len(items)
    return result


def compact_interest_text(value: object, max_length: int = 180) -> str:
    text = sub(r"\s+", " ", str(value or "")).strip()
    return text[:max_length].rstrip() + ("..." if len(text) > max_length else "")


def target_keyword_candidates(*values: object) -> list[str]:
    keywords: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, list):
            iterable = value
        else:
            iterable = [value]
        for item in iterable:
            text = str(item or "").strip()
            if not text:
                continue
            for piece in [text, *[part.strip() for part in text.replace("/", ",").split(",")]]:
                if len(piece) < 2:
                    continue
                key = piece.lower()
                if key not in seen:
                    seen.add(key)
                    keywords.append(piece)
    return keywords[:12]


def manifest_entries_matching_keywords(entries: list[dict], keywords: list[str], limit: int = 30) -> list[dict]:
    normalized_keywords = [keyword.lower() for keyword in keywords if keyword]
    matched: list[dict] = []
    for entry in entries:
        haystack = " ".join(
            str(entry.get(field) or "")
            for field in ["ticker", "title", "summary", "source_url", "type"]
        ).lower()
        tags = " ".join(str(tag or "") for tag in (entry.get("tags") or [])).lower()
        if any(keyword in haystack or keyword in tags for keyword in normalized_keywords):
            matched.append(entry)
        if len(matched) >= limit:
            break
    return matched


def market_journal_matches_for_keywords(settings: Settings, keywords: list[str], limit: int = 5) -> list[dict]:
    payload = read_market_close_journal(settings)
    normalized_keywords = [keyword.lower() for keyword in keywords if keyword]
    results: list[dict] = []
    for item in sorted(
        [entry for entry in payload.get("entries", []) if isinstance(entry, dict)],
        key=lambda entry: (entry.get("session_date") or "", entry.get("updated_at") or ""),
        reverse=True,
    ):
        text = " ".join(
            [
                str(item.get("raw_summary") or ""),
                " ".join(str(value or "") for value in item.get("key_drivers", []) or []),
                " ".join(str(value or "") for value in item.get("sector_implications", []) or []),
                " ".join(str(value or "") for value in item.get("interest_implications", []) or []),
                " ".join(str(value or "") for value in item.get("tags", []) or []),
            ]
        ).lower()
        if any(keyword in text for keyword in normalized_keywords):
            results.append(
                {
                    "market": item.get("market"),
                    "session_date": item.get("session_date"),
                    "sentiment": item.get("sentiment"),
                    "risk_level": item.get("risk_level"),
                    "summary": compact_interest_text(item.get("raw_summary"), 220),
                }
            )
        if len(results) >= limit:
            break
    return results


def interest_ticker_target(
    item: dict,
    *,
    settings: Settings,
    manifest_entries: list[dict],
    rag_counts: dict[str, int],
    source_label: str,
) -> dict:
    raw_symbol = str(item.get("ticker") or "").strip()
    verification = verify_ticker_symbol_local_cached(raw_symbol, settings)
    ticker = normalize_ticker(verification.official_symbol or raw_symbol)
    profile = official_ticker_profile(ticker, settings, refresh_external=False) if verification.verified else {}
    company_name = (
        verification.company_name
        or item.get("company_name")
        or item.get("companyName")
        or profile.get("company_name")
        or ticker
    )
    tags = [str(tag) for tag in (item.get("tags") or []) if str(tag).strip()]
    keywords = target_keyword_candidates(
        ticker,
        company_name,
        profile.get("sector"),
        profile.get("industry"),
        profile.get("business_context"),
        item.get("thesis"),
        item.get("notes"),
        tags,
    )
    target_entries = [
        entry
        for entry in manifest_entries
        if normalize_ticker(str(entry.get("ticker") or "")) == ticker
    ]
    if not target_entries:
        target_entries = manifest_entries_matching_keywords(manifest_entries, keywords, limit=30)
    unique_entries, duplicate_entries = dedupe_manifest_entries_by_similarity(
        target_entries,
        resolve_vault_dir(settings.research_vault_dir),
        limit=20,
    )
    rag_count = rag_counts.get(ticker) or 0
    snapshot = None
    try:
        snapshot = read_ticker_thesis_snapshot(resolve_vault_dir(settings.research_vault_dir), ticker)
    except Exception:
        snapshot = None
    return {
        "scope": "ticker",
        "source": source_label,
        "ticker": ticker,
        "company_name": company_name,
        "priority": item.get("priority") or "medium",
        "verified": verification.verified,
        "exchange": verification.exchange,
        "country": verification.country,
        "sector": profile.get("sector") or "미분류",
        "keywords": keywords,
        "tags": sorted(set([*tags, profile.get("sector") or "", profile.get("industry") or ""]))[:12],
        "collection_sources": [
            "신한/네이버 리서치",
            "DART/Finnhub/Tiingo/KIS 데이터",
            "정보입력 URL·파일",
            "시장일지",
        ],
        "rag_query_examples": [
            f"{company_name} 최근 악재",
            f"{company_name} 강세 논거",
            f"{company_name} 실적 수급",
            f"{company_name} 리스크와 밸류에이션",
        ],
        "recent_document_count": len(target_entries),
        "unique_document_count": len(unique_entries),
        "duplicate_suspected_count": len(duplicate_entries),
        "rag_document_count": rag_count,
        "thesis_snapshot_connected": bool(snapshot),
        "market_journal_matches": market_journal_matches_for_keywords(settings, keywords),
        "next_action": (
            "Dossier/팀 리포트 갱신으로 최신 투자 논거를 합성하세요."
            if rag_count or target_entries
            else "관련 뉴스·리포트·시장일지를 먼저 정보입력 또는 자동수집으로 적재하세요."
        ),
    }


def interest_sector_target(
    item: dict,
    *,
    settings: Settings,
    manifest_entries: list[dict],
) -> dict:
    name = str(item.get("name") or "").strip()
    tags = [str(tag) for tag in (item.get("tags") or []) if str(tag).strip()]
    keywords = target_keyword_candidates(
        name,
        item.get("region"),
        item.get("thesis"),
        item.get("notes"),
        tags,
    )
    target_entries = manifest_entries_matching_keywords(manifest_entries, keywords, limit=40)
    unique_entries, duplicate_entries = dedupe_manifest_entries_by_similarity(
        target_entries,
        resolve_vault_dir(settings.research_vault_dir),
        limit=20,
    )
    return {
        "scope": "sector",
        "source": "interest_sector",
        "name": name,
        "region": item.get("region") or "GLOBAL",
        "priority": item.get("priority") or "medium",
        "keywords": keywords,
        "tags": sorted(set([*tags, name]))[:12],
        "collection_sources": [
            "신한/네이버 산업 리포트",
            "Tavily/Brave 웹 검색",
            "시장일지",
            "정보입력 URL·파일",
        ],
        "rag_query_examples": [
            f"{name} 수혜 종목",
            f"{name} 최근 리스크",
            f"{name} 정책과 수급",
            f"{name} 장기 성장 논거",
        ],
        "recent_document_count": len(target_entries),
        "unique_document_count": len(unique_entries),
        "duplicate_suspected_count": len(duplicate_entries),
        "market_journal_matches": market_journal_matches_for_keywords(settings, keywords),
        "next_action": "시장일지와 저장 데이터를 함께 검색해 섹터 강세/약세 논거를 재합성하세요.",
    }


def build_interest_automation_board(settings: Settings, *, save_result: bool = True) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    manifest_entries = sorted(
        [entry for entry in read_manifest(vault_dir) if isinstance(entry, dict)],
        key=manifest_entry_sort_key,
        reverse=True,
    )
    interest_payload = read_interest_list(settings)
    portfolio_payload = portfolio_store_response(settings)
    portfolio_items: dict[str, dict] = {}
    for portfolio in portfolio_payload.portfolios:
        for holding in portfolio.holdings:
            ticker = normalize_ticker(holding.ticker)
            if not ticker or ticker in {"UNKNOWN", "CASH"}:
                continue
            portfolio_items.setdefault(
                ticker,
                {
                    "ticker": ticker,
                    "company_name": holding.name,
                    "priority": "high" if (holding.market_value or 0) > 0 else "medium",
                    "thesis": "보유 포트폴리오 종목으로 자동 수집 대상",
                    "tags": holding.theme_tags,
                },
            )

    interest_ticker_items = [
        item for item in interest_payload.get("tickers", []) if isinstance(item, dict)
    ]
    explicit_symbols = {normalize_ticker(str(item.get("ticker") or "")) for item in interest_ticker_items}
    merged_ticker_items = [
        {**item, "_source_label": "interest_ticker"} for item in interest_ticker_items
    ]
    for ticker, item in portfolio_items.items():
        if ticker not in explicit_symbols:
            merged_ticker_items.append({**item, "_source_label": "portfolio_holding"})

    rag_counts = count_research_memory_documents_by_ticker(
        vault_dir,
        [normalize_ticker(str(item.get("ticker") or "")) for item in merged_ticker_items],
    )
    ticker_targets = [
        interest_ticker_target(
            item,
            settings=settings,
            manifest_entries=manifest_entries,
            rag_counts=rag_counts,
            source_label=item.get("_source_label") or "interest_ticker",
        )
        for item in merged_ticker_items
        if item.get("ticker")
    ]
    sector_targets = [
        interest_sector_target(item, settings=settings, manifest_entries=manifest_entries)
        for item in interest_payload.get("sectors", [])
        if isinstance(item, dict) and item.get("name")
    ]
    unique_recent, duplicate_recent = dedupe_manifest_entries_by_similarity(
        manifest_entries,
        vault_dir,
        limit=40,
    )
    all_queries = []
    for target in [*ticker_targets, *sector_targets]:
        for query in target.get("rag_query_examples", []):
            if query not in all_queries:
                all_queries.append(query)
    payload = {
        "status": "success",
        "module": "interest_automation_board",
        "as_of": current_storage_timestamp(),
        "target_count": len(ticker_targets) + len(sector_targets),
        "ticker_target_count": len(ticker_targets),
        "sector_target_count": len(sector_targets),
        "portfolio_linked_count": sum(1 for item in ticker_targets if item.get("source") == "portfolio_holding"),
        "rag_connected_count": sum(1 for item in ticker_targets if item.get("rag_document_count", 0) > 0),
        "thesis_connected_count": sum(1 for item in ticker_targets if item.get("thesis_snapshot_connected")),
        "duplicate_suspected_count": len(duplicate_recent),
        "recent_unique_document_count": len(unique_recent),
        "ticker_targets": sorted(
            ticker_targets,
            key=lambda item: (
                {"high": 2, "medium": 1, "low": 0}.get(str(item.get("priority")), 1),
                item.get("recent_document_count", 0),
                item.get("rag_document_count", 0),
            ),
            reverse=True,
        ),
        "sector_targets": sorted(
            sector_targets,
            key=lambda item: (
                {"high": 2, "medium": 1, "low": 0}.get(str(item.get("priority")), 1),
                item.get("recent_document_count", 0),
            ),
            reverse=True,
        ),
        "rag_search_prompts": all_queries[:30],
        "automation_steps": [
            "Pulls: 보유종목·관심종목·관심섹터 키워드로 뉴스/공시/리포트/시장일지 후보를 수집합니다.",
            "De-dupes: source_url, content_hash, 제목·본문 유사도로 중복 자료를 묶습니다.",
            "Embeds: 저장 데이터는 RAG 색인으로 들어가 자연어 검색과 재합성에 사용됩니다.",
            "Tags: 종목, 섹터, 테마, 실적, 수급, 금리, 정책, 리스크 태그를 자동 부여합니다.",
            "Syntheses/Delivers: 검색 결과와 Dossier를 합성해 일일 브리핑·대시보드·시장일지에 반영합니다.",
        ],
        "next_actions": [
            "관심목록을 저장한 뒤 자동화 보드를 다시 생성하면 새 수집 대상이 즉시 반영됩니다.",
            "RAG 검색어 예시를 저장 데이터 화면에서 실행하면 강세/약세/핵심 쟁점 합성 보고서로 이어집니다.",
            "시장일지에 같은 키워드가 들어오면 관심섹터와 관심종목의 확인 포인트로 자동 연결됩니다.",
        ],
    }
    if save_result:
        write_json_store(
            interest_collection_targets_path(settings),
            {
                "updated_at": payload["as_of"],
                "payload": payload,
            },
        )
        payload["storage_path"] = str(interest_collection_targets_path(settings))
    return payload


def render_source_url_context(url_info: dict | None) -> str:
    if not url_info:
        return ""
    lines = [
        "[웹사이트 입력]",
        f"원본 URL: {url_info.get('source_url') or '미입력'}",
        f"최종 URL: {url_info.get('final_url') or url_info.get('source_url') or '미확인'}",
        f"처리 상태: {url_info.get('status') or 'unknown'}",
        f"처리 메모: {url_info.get('note') or '없음'}",
    ]
    if url_info.get("title"):
        lines.append(f"웹페이지 제목: {url_info['title']}")
    if url_info.get("language"):
        lines.append(f"원문 언어: {translation_language_label(str(url_info.get('language') or 'unknown'))}")
    if url_info.get("translation_status"):
        lines.append(
            f"한국어 변환: {url_info.get('translation_status')} - {url_info.get('translation_note') or '메모 없음'}"
        )
    if url_info.get("content_type"):
        lines.append(f"콘텐츠 유형: {url_info['content_type']}")
    if url_info.get("text"):
        lines.extend(["", "[웹사이트 본문 추출]", url_info["text"][:30000]])
    return "\n".join(lines)


@app.post(
    "/api/v1/source-url/preview",
    dependencies=[Depends(verify_user_token)],
)
def preview_source_url_body(
    payload: dict = Body(default_factory=dict),
) -> dict:
    """
    정보입력/시장일지에서 저장 전에 웹사이트 본문 추출 품질만 확인합니다.
    저장 데이터나 RAG 색인은 만들지 않습니다.
    """
    source_url = str(payload.get("source_url") or payload.get("sourceUrl") or "").strip()
    if not source_url:
        raise HTTPException(status_code=422, detail="미리보기할 웹사이트 주소를 입력하세요.")
    url_info = fetch_capture_source_url(source_url)
    text = str(url_info.get("text") or "").strip()
    original_text = str(url_info.get("original_text") or "").strip()
    preview = clean_web_article_text(text)[:12000]
    original_preview = clean_web_article_text(original_text)[:12000] if original_text else ""
    return {
        "status": "success",
        "module": "source_url_preview",
        "source_url_processing": url_info,
        "source_url": source_url,
        "final_url": url_info.get("final_url") or source_url,
        "title": url_info.get("title") or "",
        "original_title": url_info.get("original_title") or "",
        "language": url_info.get("language") or "unknown",
        "translation_status": url_info.get("translation_status") or "unknown",
        "translation_note": url_info.get("translation_note") or "",
        "content_type": url_info.get("content_type") or "unknown",
        "preview": preview,
        "analysis_preview": preview,
        "original_preview": original_preview,
        "text_length": len(preview),
        "note": url_info.get("note") or "",
    }


def infer_capture_title(raw_content: str, file_name: str | None = None) -> str:
    first_line = next((line.strip() for line in raw_content.splitlines() if line.strip()), "")
    if file_name:
        stem = Path(file_name).stem.strip() or "자동 캡처"
        return stem[:80]
    if first_line:
        return first_line[:80]
    return "자동 캡처"


def prefix_capture_title(title: str, ticker: str, inference: str) -> str:
    labels = {
        "MACRO": "거시 전망",
        "SECTOR": "섹터 전망",
        "MARKET": "전체 시황",
        "POLICY": "정책/규제 전망",
        "RATES": "금리/물가 전망",
        "FLOWS": "수급/자금 흐름",
        "INBOX": "미분류 자료",
    }
    label = labels.get(ticker)
    if not label:
        return title
    cleaned_title = title.strip() or "자동 캡처"
    if cleaned_title.startswith(label):
        return cleaned_title[:80]
    return f"{label}: {cleaned_title}"[:80]


def ticker_aliases(symbol: str, profile: dict) -> set[str]:
    aliases = {symbol.upper()}
    aliases.update(str(alias).upper() for alias in profile.get("aliases", []) if str(alias).strip())
    company_name = str(profile.get("company_name") or "")
    if company_name:
        aliases.add(company_name.upper())
        aliases.add(company_name.replace(",", "").replace(".", "").upper())
        for suffix in [" INC", " INCORPORATED", " CORPORATION", " CORP", " PBC", " CLASS A"]:
            cleaned = company_name.upper().replace(".", "").replace(",", "")
            if suffix in cleaned:
                aliases.add(cleaned.replace(suffix, "").strip())
    return {alias for alias in aliases if len(alias) >= 2}


def alias_matches_research_text(alias: str, raw_text: str) -> bool:
    normalized_alias = alias.strip().upper()
    if not normalized_alias:
        return False
    escaped_alias = escape(normalized_alias)
    if any("\uac00" <= char <= "\ud7a3" for char in normalized_alias):
        if len(normalized_alias) <= 3:
            return bool(
                search(
                    rf"(?<![\uac00-\ud7a3A-Z0-9]){escaped_alias}(?![\uac00-\ud7a3A-Z0-9])",
                    raw_text,
                )
            )
        return normalized_alias in raw_text
    if len(normalized_alias) <= 3:
        return bool(search(rf"(?<![A-Z0-9]){escaped_alias}(?![A-Z0-9])", raw_text))
    if search(rf"(?<![A-Z0-9]){escaped_alias}(?![A-Z0-9])", raw_text):
        return True
    return False


def infer_non_ticker_research_key(raw_content: str) -> tuple[str, str]:
    text = raw_content.lower()
    keyword_groups = {
        "POLICY": {
            "source_type": "policy_research",
            "keywords": {
                "policy",
                "regulation",
                "regulatory",
                "tariff",
                "fiscal",
                "subsidy",
                "election",
                "sanction",
                "government",
                "white house",
                "congress",
                "central bank",
                "정책",
                "규제",
                "관세",
                "재정",
                "보조금",
                "선거",
                "정부",
                "의회",
                "중앙은행",
                "한국은행",
                "연준 발언",
                "지정학",
                "제재",
            },
        },
        "RATES": {
            "source_type": "rates_research",
            "keywords": {
                "rates",
                "rate cut",
                "rate hike",
                "yield",
                "treasury",
                "bond",
                "duration",
                "inflation",
                "cpi",
                "ppi",
                "pce",
                "dollar",
                "credit spread",
                "금리",
                "금리 인하",
                "금리 인상",
                "국채",
                "채권",
                "물가",
                "인플레이션",
                "달러",
                "환율",
                "장단기 금리",
                "신용 스프레드",
            },
        },
        "FLOWS": {
            "source_type": "flows_research",
            "keywords": {
                "flows",
                "fund flow",
                "etf flow",
                "positioning",
                "breadth",
                "rotation",
                "risk appetite",
                "net buying",
                "net selling",
                "foreign buying",
                "institutional buying",
                "수급",
                "자금 흐름",
                "펀드 플로우",
                "순매수",
                "순매도",
                "외국인",
                "기관",
                "개인",
                "포지셔닝",
                "시장 폭",
                "로테이션",
                "위험선호",
            },
        },
        "MACRO": {
            "source_type": "macro_research",
            "keywords": {
                "macro",
                "economy",
                "economic outlook",
                "fed",
                "fomc",
                "inflation",
                "cpi",
                "ppi",
                "rates",
                "rate cut",
                "yield",
                "treasury",
                "dollar",
                "currency",
                "recession",
                "gdp",
                "employment",
                "payroll",
                "금리",
                "물가",
                "인플레이션",
                "환율",
                "달러",
                "경기",
                "중앙은행",
                "연준",
                "한국은행",
                "고용",
                "경제 전망",
                "거시",
                "통화정책",
                "재정정책",
                "국채",
                "장단기 금리",
            },
        },
        "SECTOR": {
            "source_type": "sector_research",
            "keywords": {
                "sector",
                "industry",
                "semiconductor",
                "software",
                "cloud",
                "energy",
                "healthcare",
                "drug discovery",
                "drug design",
                "therapeutic",
                "pipeline",
                "clinical",
                "financials",
                "consumer",
                "ai capex",
                "infrastructure",
                "utilities",
                "defense",
                "aerospace",
                "biotech",
                "materials",
                "섹터",
                "산업",
                "업종",
                "반도체",
                "소프트웨어",
                "클라우드",
                "에너지",
                "헬스케어",
                "바이오",
                "신약",
                "신약개발",
                "신약 설계",
                "치료제",
                "파이프라인",
                "임상",
                "금융",
                "소비재",
                "인프라",
                "방산",
                "항공우주",
                "유틸리티",
                "소재",
                "테마",
                "ai 투자",
                "데이터센터",
            },
        },
        "MARKET": {
            "source_type": "market_research",
            "keywords": {
                "market",
                "equity market",
                "flows",
                "fund flow",
                "positioning",
                "risk appetite",
                "breadth",
                "volatility",
                "vix",
                "rotation",
                "liquidity",
                "sentiment",
                "시장",
                "증시",
                "수급",
                "자금 흐름",
                "펀드 플로우",
                "포지셔닝",
                "위험선호",
                "위험 회피",
                "변동성",
                "시장 폭",
                "로테이션",
                "투자 동향",
                "유동성",
                "투자심리",
                "리스크온",
                "리스크오프",
            },
        },
    }
    scores = {}
    for key, config in keyword_groups.items():
        scores[key] = sum(1 for keyword in config["keywords"] if keyword in text)
    if scores.get("RATES", 0) and scores.get("MACRO", 0):
        scores["RATES"] += 1
    if scores.get("FLOWS", 0) and scores.get("MARKET", 0):
        scores["FLOWS"] += 1
    if scores.get("POLICY", 0) and scores.get("MACRO", 0):
        scores["POLICY"] += 1
    best_key, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score > 0:
        return best_key, str(keyword_groups[best_key]["source_type"])
    return "INBOX", "unassigned_inbox"


def infer_capture_ticker(raw_content: str, settings: Settings | None = None) -> tuple[str, str]:
    active_settings = settings or get_settings()
    upper_text = raw_content.upper()
    special_research_keys = {"CASH", *SPECIAL_RESEARCH_KEYS}
    explicit = search(r"(?:TICKER|SYMBOL|티커|심볼)\s*[:=]\s*\$?([A-Z0-9._-]{1,10})", upper_text)
    if explicit:
        candidate = normalize_ticker(explicit.group(1))
        if verify_ticker_symbol(candidate, active_settings).verified:
            return candidate, "explicit_symbol"

    registry = {
        **OFFICIAL_TICKER_REGISTRY,
        **read_dynamic_ticker_registry(active_settings),
    }
    symbol_hits = []
    for symbol in registry:
        if symbol in special_research_keys:
            continue
        if search(rf"(?<![A-Z0-9])\$?{escape(symbol)}(?![A-Z0-9])", upper_text):
            symbol_hits.append(symbol)
    if len(symbol_hits) == 1:
        return symbol_hits[0], "symbol_match"

    alias_hits = []
    for symbol, profile in registry.items():
        if symbol in special_research_keys:
            continue
        aliases = ticker_aliases(symbol, profile) - {symbol.upper()}
        if any(alias_matches_research_text(alias, upper_text) for alias in aliases):
            alias_hits.append(symbol)
    unique_alias_hits = sorted(set(alias_hits))
    if len(unique_alias_hits) == 1:
        return unique_alias_hits[0], "company_alias_match"

    return infer_non_ticker_research_key(raw_content)


def render_research_capture_markdown(
    captured_item: CapturedResearchItem,
    raw_content: str,
    storage_date: date,
    attachment_info: dict | None = None,
) -> str:
    tags = ", ".join(captured_item.tags) or "none"
    attachment_section = ""
    if attachment_info:
        attachment_section = f"""
## 첨부 파일

- 파일명: {attachment_info.get("file_name") or "n/a"}
- MIME: {attachment_info.get("mime_type") or "n/a"}
- 크기: {attachment_info.get("size") or 0} bytes
- 저장 경로: {attachment_info.get("relative_path") or "n/a"}
- 텍스트 추출: {attachment_info.get("text_extraction") or "n/a"}
"""
    return f"""---
ticker: {captured_item.ticker}
type: research-capture
date: {storage_date.isoformat()}
module: research_quick_capture
source_type: {enum_or_str_value(captured_item.source_type)}
confidence: {captured_item.confidence}
tags: {tags}
---

# {captured_item.ticker} 투자 정보 캡처: {captured_item.title}

## 요약

{captured_item.summary}

## 출처

- 유형: {enum_or_str_value(captured_item.source_type)}
- URL: {captured_item.source_url or "n/a"}
- 기준 시점: {captured_item.as_of or storage_date.isoformat()}
- 신뢰도: {captured_item.confidence:.0%}
- 태그: {tags}
{attachment_section}

## 원문

{raw_content}
"""


def save_capture_attachment(
    vault_dir: Path,
    ticker: str,
    storage_date: date,
    request: AutoResearchCaptureRequest,
) -> dict | None:
    file_bytes = decode_attachment_base64(request.file_content_base64)
    if file_bytes is None:
        return None

    safe_ticker = normalize_ticker(ticker)
    attachments_dir = vault_dir / safe_ticker / "_attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%H%M%S")
    safe_name = safe_attachment_file_name(request.file_name)
    attachment_path = attachments_dir / f"{safe_ticker}-research-attachment-{storage_date.isoformat()}-{timestamp}-{safe_name}"
    attachment_path.write_bytes(file_bytes)

    extraction = extract_uploaded_file_text(
        file_bytes,
        request.file_name,
        request.file_mime_type,
        source_path=attachment_path,
    )
    extracted_text = extraction.get("extracted_text") or ""
    extraction_note = extraction.get("text_extraction") or (
        "본문 텍스트 추출 포함"
        if request.raw_content.strip()
        else "원본 첨부만 저장됨"
    )

    relative_path = attachment_path.relative_to(vault_dir).as_posix()
    return {
        "file_name": request.file_name or safe_name,
        "mime_type": request.file_mime_type or "application/octet-stream",
        "size": len(file_bytes),
        "declared_size": request.file_size,
        "relative_path": relative_path,
        "text_extraction": extraction_note,
        "extracted_text": extracted_text,
        "document_type": extraction.get("document_type"),
        "extraction_quality": extraction.get("extraction_quality"),
        "extraction_char_count": extraction.get("extraction_char_count"),
        "extraction_preview": extraction.get("extraction_preview"),
        "extraction_warnings": extraction.get("extraction_warnings") or [],
        "extraction_profile": extraction.get("extraction_profile") or {},
    }


def render_attachment_context(request: AutoResearchCaptureRequest, attachment_info: dict | None) -> str:
    if not attachment_info:
        return ""
    lines = [
        "[첨부 파일]",
        f"파일명: {attachment_info.get('file_name') or request.file_name or 'n/a'}",
        f"MIME: {attachment_info.get('mime_type') or request.file_mime_type or 'n/a'}",
        f"크기: {attachment_info.get('size') or request.file_size or 0} bytes",
        f"저장 경로: {attachment_info.get('relative_path') or 'n/a'}",
        f"문서 유형: {attachment_info.get('document_type') or 'n/a'}",
        f"추출 품질: {attachment_info.get('extraction_quality') or 'n/a'}",
        f"텍스트 추출: {attachment_info.get('text_extraction') or '원본 첨부만 저장됨'}",
    ]
    extraction_profile = attachment_info.get("extraction_profile") or {}
    if extraction_profile:
        lines.extend(
            [
                f"분석 활용도: {extraction_profile.get('analysis_readiness') or 'n/a'}",
                f"추출 구조: 본문 {extraction_profile.get('char_count') or 0}자, 줄 {extraction_profile.get('line_count') or 0}개, 숫자 토큰 {extraction_profile.get('numeric_token_count') or 0}개",
                f"권장 조치: {extraction_profile.get('next_action') or 'n/a'}",
            ]
        )
    for warning in attachment_info.get("extraction_warnings") or []:
        lines.append(f"추출 경고: {warning}")
    extracted_text = (attachment_info.get("extracted_text") or "").strip()
    if extracted_text:
        lines.extend(["", "[첨부 본문 추출]", extracted_text])
    return "\n".join(lines)


def capture_preview_text(value: str | None, max_chars: int = 4000) -> str | None:
    text = (value or "").strip()
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars].rstrip()}\n\n[미리보기는 앞부분 {max_chars:,}자만 표시합니다. 전체 원문은 저장 데이터에 보관했습니다.]"


def normalize_portfolio_holdings(
    holdings: list[PortfolioHolding],
    portfolio_value: float | None,
) -> tuple[list[PortfolioHolding], float]:
    normalized_holdings = []
    inferred_values = []

    for holding in holdings:
        market_value = holding.market_value
        if market_value is None and holding.quantity is not None and holding.current_price is not None:
            market_value = holding.quantity * holding.current_price
        if market_value is None and holding.weight is not None and portfolio_value is not None:
            market_value = holding.weight * portfolio_value
        if market_value is None:
            market_value = 0

        inferred_values.append(market_value)
        official_ticker = ensure_verified_ticker(holding.ticker)
        normalized_holdings.append(
            holding.model_copy(
                update={
                    "ticker": official_ticker,
                    "market_value": market_value,
                }
            )
        )

    total_value = portfolio_value if portfolio_value is not None else sum(inferred_values)
    if total_value <= 0:
        total_value = 1

    weighted_holdings = []
    for holding in normalized_holdings:
        weight = holding.weight
        if weight is None:
            weight = (holding.market_value or 0) / total_value
        weighted_holdings.append(holding.model_copy(update={"weight": weight}))

    return weighted_holdings, total_value


def aggregate_concentration(
    holdings: list[PortfolioHolding],
    key_getter,
) -> list[ConcentrationItem]:
    totals: dict[str, dict[str, float]] = {}
    for holding in holdings:
        keys = key_getter(holding)
        if isinstance(keys, str):
            keys = [keys]
        if not keys:
            keys = ["Unknown"]
        for key in keys:
            bucket = totals.setdefault(key or "Unknown", {"weight": 0, "market_value": 0})
            bucket["weight"] += holding.weight or 0
            bucket["market_value"] += holding.market_value or 0

    return [
        ConcentrationItem(
            name=name,
            weight=round(values["weight"], 4),
            market_value=round(values["market_value"], 2),
        )
        for name, values in sorted(
            totals.items(),
            key=lambda item: item[1]["weight"],
            reverse=True,
        )
    ]


def build_portfolio_warnings(
    *,
    holdings: list[PortfolioHolding],
    sector_concentration: list[ConcentrationItem],
    theme_concentration: list[ConcentrationItem],
    request: PortfolioRiskScanRequest,
    top_five_weight: float,
    settings: Settings,
) -> list[PortfolioRiskWarning]:
    warnings = []
    for holding in holdings:
        if (holding.weight or 0) > request.max_single_position_weight:
            warnings.append(
                PortfolioRiskWarning(
                    type="single_position",
                    severity="high",
                    message=f"{holding.ticker} 비중이 {holding.weight:.0%}로 단일 종목 한도 {request.max_single_position_weight:.0%}를 초과했습니다.",
                    action="추가 매수 전 포지션 크기, 일부 축소 계획, 투자 논거 확신도를 재검토하세요.",
                )
            )

    for sector in sector_concentration:
        if sector.weight > request.max_sector_weight:
            warnings.append(
                PortfolioRiskWarning(
                    type="sector_concentration",
                    severity="high",
                    message=f"{sector.name} 섹터 비중이 {sector.weight:.0%}로 섹터 한도 {request.max_sector_weight:.0%}를 초과했습니다.",
                    action="다른 섹터 비중을 줄이기 전에는 상관성이 높은 종목 추가를 피하세요.",
                )
            )

    for theme in theme_concentration:
        if theme.weight > request.max_theme_weight:
            warnings.append(
                PortfolioRiskWarning(
                    type="theme_concentration",
                    severity="medium",
                    message=f"{theme.name} 테마 비중이 {theme.weight:.0%}로 테마 한도 {request.max_theme_weight:.0%}를 초과했습니다.",
                    action="보유 종목들이 같은 촉매, 밸류에이션 리스크, 거시 민감도를 공유하는지 점검하세요.",
                )
            )

    if top_five_weight > 0.75:
        warnings.append(
            PortfolioRiskWarning(
                type="top_five_concentration",
                severity="medium",
                message=f"상위 5개 보유 종목이 포트폴리오의 {top_five_weight:.0%}를 차지합니다.",
                action="집중도를 더 높이기 전에 상위 종목 동반 하락 시나리오를 점검하세요.",
            )
        )

    nps_alerts = build_nps_portfolio_flow_warnings(holdings, settings)
    warnings.extend(nps_alerts)

    if not warnings:
        warnings.append(
            PortfolioRiskWarning(
                type="portfolio_structure",
                severity="low",
                message="현재 입력 기준으로 집중도 한도를 초과한 항목은 없습니다.",
                action="상관관계, 실적 일정, 유동성은 계속 점검하세요.",
            )
        )

    return warnings


def build_nps_portfolio_flow_warnings(
    holdings: list[PortfolioHolding],
    settings: Settings,
) -> list[PortfolioRiskWarning]:
    alerts: list[PortfolioRiskWarning] = []
    if not settings.nps_odcloud_enabled or not settings.nps_odcloud_api_key:
        return alerts
    cache: dict[str, dict] = {}
    for holding in holdings:
        ticker = normalize_ticker(holding.ticker)
        if not ticker or ticker in cache:
            continue
        try:
            verification = verify_ticker_symbol(ticker, settings)
            company_name = verification.company_name if verification.verified else None
            signal = fetch_nps_institutional_signal(ticker, company_name, settings)
            cache[ticker] = signal
        except Exception:
            cache[ticker] = {}
            continue
        events = signal.get("large_holding_events") or []
        if not events:
            continue
        raw_text = json.dumps(events, ensure_ascii=False).lower()
        outflow_terms = ["감소", "매도", "처분", "축소", "하락", "decrease", "sell", "sold", "reduced"]
        outflow_like = any(term in raw_text for term in outflow_terms)
        ratio_text = ""
        latest_ratio = events[0].get("holding_ratio") if isinstance(events[0], dict) else None
        if latest_ratio is not None:
            ratio_text = f" 최근 보고 지분율 {latest_ratio:.2f}%."
        alerts.append(
            PortfolioRiskWarning(
                type="nps_institutional_flow",
                severity="high" if outflow_like else "medium",
                message=(
                    f"{holding.ticker}에서 국민연금 대량보유 보고 이벤트가 확인되었습니다."
                    f"{ratio_text} {'감소/처분성 문구가 감지되어 수급 이탈 가능성을 우선 점검해야 합니다.' if outflow_like else '증감 방향은 원문 확인이 필요합니다.'}"
                ),
                action="포트폴리오 추가매수 전 국민연금 보고내역의 증감 방향, 보고 기준일, 동일 섹터 동반 매도 여부를 확인하세요.",
            )
        )
    return alerts


def calculate_portfolio_risk_score(warnings: list[PortfolioRiskWarning]) -> int:
    score = 25
    severity_points = {"low": 5, "medium": 15, "high": 25}
    for warning in warnings:
        score += severity_points.get(warning.severity, 10)
    return min(score, 100)


def render_portfolio_risk_markdown(
    scan: PortfolioRiskScanResponse,
    storage_date: date,
) -> str:
    holdings = "\n".join(
        f"- {item.ticker}: 비중 {item.weight:.1%}, 섹터 {item.sector}, 평가금액 {item.market_value:.2f}"
        for item in scan.holdings
    )
    sectors = "\n".join(
        f"- {item.name}: 비중 {item.weight:.1%}, 평가금액 {item.market_value:.2f}"
        for item in scan.sector_concentration
    )
    themes = "\n".join(
        f"- {item.name}: 비중 {item.weight:.1%}, 평가금액 {item.market_value:.2f}"
        for item in scan.theme_concentration
    )
    warnings = "\n".join(
        f"- [{translate_severity_label(item.severity)}] {item.message} 조치: {item.action}"
        for item in scan.warnings
    )
    next_actions = "\n".join(f"- {item}" for item in scan.next_actions)

    return f"""---
portfolio_name: {scan.portfolio_name}
type: portfolio-risk-scan
date: {storage_date.isoformat()}
module: {scan.module.value}
risk_score: {scan.risk_score}
---

# {scan.portfolio_name} 포트폴리오 리스크 스캔

## 요약

- 포트폴리오 총액: {scan.portfolio_value:.2f}
- 리스크 점수: {scan.risk_score}/100
- 상위 5개 비중: {scan.top_five_weight:.1%}

## 보유 종목

{holdings}

## 섹터 집중도

{sectors}

## 테마 집중도

{themes}

## 경고

{warnings}

## 다음 액션

{next_actions}
"""


def render_team_analysis_markdown(
    report: TeamAnalysisResponse,
    storage_date: date,
) -> str:
    injected_data = "\n".join(
        f"- {item.source_type} / {item.label}: {item.value}"
        for item in report.injected_data
    )
    contributions = "\n\n".join(
        "\n".join(
            [
                f"### {item.skill_id}. {item.skill_name}",
                f"- 페르소나: {item.persona}",
                f"- 역할: {item.role}",
                f"- 요약: {item.summary}",
                "- 핵심 산출물:",
                *[f"  - {output}" for output in item.key_outputs],
                f"- 확신도: {item.confidence:.0%}",
            ]
        )
        for item in report.team_contributions
    )
    scenarios = "\n".join(f"- {item}" for item in report.scenario_map)
    consensus = "\n".join(f"- {item}" for item in report.consensus)
    conflicts = "\n\n".join(
        "\n".join(
            [
                f"### {item.topic}",
                f"- 긍정 관점: {item.positive_view}",
                f"- 주의 관점: {item.caution_view}",
                f"- 정리: {item.resolution}",
                f"- 심각도: {translate_severity_label(item.severity)}",
            ]
        )
        for item in report.conflicts
    )
    trade_plan = "\n".join(f"- {item}" for item in report.trade_plan)
    compounder_notes = "\n".join(f"- {item}" for item in report.compounder_notes)
    invalidation_conditions = "\n".join(
        f"- {item}" for item in report.invalidation_conditions
    )
    watch_items = "\n".join(
        f"- {item.metric}: {item.condition}이면 {item.action} ({translate_priority_label(item.priority)})"
        for item in report.watch_items
    )
    next_actions = "\n".join(f"- {item}" for item in report.next_actions)

    return f"""---
ticker: {report.ticker}
type: collaborative-team-report
date: {storage_date.isoformat()}
module: {report.module}
investment_period: {report.investment_period}
region: {report.region}
style: {report.style}
---

# {report.ticker} 7개 스킬 협업 분석 보고서

## 핵심 요약

{report.executive_summary}

## 주입된 데이터 컨텍스트

{injected_data}

## 스킬별 기여

{contributions}

## 데이터 품질

- 품질: {translate_quality_label(report.data_quality.data_quality)}
- 출처 신뢰도: {report.data_quality.source_confidence:.0%}
- 오래된 데이터 경고: {report.data_quality.stale_data_warning}
- 부족한 데이터: {", ".join(report.data_quality.missing_data) or "없음"}

## 통합 판단

{report.synthesized_view}

## 합의된 관점

{consensus}

## 충돌/주의점

{conflicts}

## 투자 논거

{report.investment_thesis.thesis}

## 시나리오 맵

{scenarios}

## 매매 전략

{trade_plan}

## 장기 복리 관점

{compounder_notes}

## 무효화 조건

{invalidation_conditions}

## 추적 항목

{watch_items}

## 다음 액션

{next_actions}
"""


@app.get("/")
def read_root() -> dict:
    return {"message": "매매일지 백엔드 서버가 정상 작동 중입니다."}


@app.get("/api/v1/config/safety")
def read_safety_config(settings: Settings = Depends(get_settings)) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return {
        "brokerage_api_key": mask_secret(settings.brokerage_api_key),
        "brokerage_api_secret": mask_secret(settings.brokerage_api_secret),
        "kiwoom_base_url": settings.kiwoom_base_url,
        "kiwoom_mock_base_url": settings.kiwoom_mock_base_url,
        "kiwoom_use_mock": settings.kiwoom_use_mock,
        "kiwoom_registered_ip": mask_secret(settings.kiwoom_registered_ip),
        "secret_salt": mask_secret(settings.secret_salt),
        "research_vault_dir": settings.research_vault_dir,
        "resolved_research_vault_dir": str(vault_dir),
        "block_onedrive_paths": settings.block_onedrive_paths,
        "onedrive_excluded": "onedrive" not in str(vault_dir).lower(),
        "live_data_max_age_minutes": settings.live_data_max_age_minutes,
        "earnings_calendar_on_demand_refresh": settings.earnings_calendar_on_demand_refresh,
        "data_provider_mode": settings.data_provider_mode,
        "auto_inject_analysis_data": settings.auto_inject_analysis_data,
        "fmp_api_key": mask_secret(settings.fmp_api_key),
        "fmp_base_url": settings.fmp_base_url,
        "fmp_timeout_seconds": settings.fmp_timeout_seconds,
        "dart_api_key": mask_secret(settings.dart_api_key),
        "dart_base_url": settings.dart_base_url,
        "financial_datasets_api_key": mask_secret(settings.financial_datasets_api_key),
        "finnhub_api_key": mask_secret(settings.finnhub_api_key),
        "tiingo_api_key": mask_secret(settings.tiingo_api_key),
        "alpha_vantage_api_key": mask_secret(settings.alpha_vantage_api_key),
        "tavily_api_key": mask_secret(settings.tavily_api_key),
        "brave_api_key": mask_secret(settings.brave_api_key),
        "naver_finance_enabled": settings.naver_finance_enabled,
        "naver_finance_base_url": settings.naver_finance_base_url,
        "naver_finance_timeout_seconds": settings.naver_finance_timeout_seconds,
        "nps_odcloud_enabled": settings.nps_odcloud_enabled,
        "nps_odcloud_api_key": mask_secret(settings.nps_odcloud_api_key),
        "nps_odcloud_base_url": settings.nps_odcloud_base_url,
        "nps_domestic_stock_docs_url": settings.nps_domestic_stock_docs_url,
        "nps_large_holding_docs_url": settings.nps_large_holding_docs_url,
        "nps_domestic_stock_api_url": settings.nps_domestic_stock_api_url,
        "nps_large_holding_api_url": settings.nps_large_holding_api_url,
        "customs_trade_enabled": settings.customs_trade_enabled,
        "customs_trade_api_key": mask_secret(settings.customs_trade_api_key),
        "customs_trade_api_url": settings.customs_trade_api_url,
        "customs_trade_release_days": settings.customs_trade_release_days,
        "secrets_are_masked": True,
    }


@app.get("/api/v1/data-providers/status")
def read_data_provider_status(settings: Settings = Depends(get_settings)) -> dict:
    provider = get_analysis_data_provider(settings)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return {
        "status": "success",
        "mode": settings.data_provider_mode,
        "auto_inject_analysis_data": settings.auto_inject_analysis_data,
        "live_data_max_age_minutes": settings.live_data_max_age_minutes,
        "earnings_calendar_on_demand_refresh": settings.earnings_calendar_on_demand_refresh,
        "resolved_research_vault_dir": str(vault_dir),
        "onedrive_excluded": "onedrive" not in str(vault_dir).lower(),
        "providers": provider.status(),
    }


CUSTOMS_STRATEGIC_ITEMS = [
    {
        "item_code": "190230",
        "label": "라면/가공식품",
        "linked_sectors": ["음식료", "수출소비재"],
        "watch_reason": "삼양식품 등 음식료 수출주의 수요 강도와 재고 부담을 점검",
    },
    {
        "item_code": "8542",
        "label": "반도체",
        "linked_sectors": ["반도체", "AI 인프라"],
        "watch_reason": "반도체 수출 회복, 재고 조정, AI 서버 수요 흐름을 점검",
    },
    {
        "item_code": "8504",
        "label": "변압기/전력기기",
        "linked_sectors": ["전력기기", "전력망"],
        "watch_reason": "전력 인프라 수출과 전력기기 피어 밸류에이션 근거를 점검",
    },
    {
        "item_code": "850760",
        "label": "리튬이온 배터리",
        "linked_sectors": ["2차전지", "기후변화"],
        "watch_reason": "배터리 수출 둔화/회복과 원재료·재고 부담을 점검",
    },
]


def yymm_add_months(yymm: str, months: int) -> str:
    year = int(yymm[:4])
    month = int(yymm[4:6]) + months
    while month <= 0:
        month += 12
        year -= 1
    while month > 12:
        month -= 12
        year += 1
    return f"{year:04d}{month:02d}"


def customs_default_period(today: date | None = None) -> tuple[str, str, str]:
    selected = today or current_storage_date()
    current_yymm = f"{selected.year:04d}{selected.month:02d}"
    end_yymm = current_yymm if selected.day >= 11 else yymm_add_months(current_yymm, -1)
    start_yymm = yymm_add_months(end_yymm, -2)
    release_cycle = "1일 확정/전월 점검" if selected.day < 11 else "11일·21일 잠정 수출입 동향 점검"
    return start_yymm, end_yymm, release_cycle


def safe_customs_number(value: object) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def aggregate_customs_trade_rows(rows: list[dict], theme: dict) -> dict:
    export_value = sum(safe_customs_number(row.get("export_value_usd")) for row in rows)
    import_value = sum(safe_customs_number(row.get("import_value_usd")) for row in rows)
    export_weight = sum(safe_customs_number(row.get("export_weight")) for row in rows)
    import_weight = sum(safe_customs_number(row.get("import_weight")) for row in rows)
    balance = export_value - import_value
    top_countries = []
    country_buckets: dict[str, dict] = {}
    for row in rows:
        country = row.get("country_name") or row.get("country_code") or "국가 미상"
        bucket = country_buckets.setdefault(
            country,
            {"country": country, "export_value_usd": 0.0, "import_value_usd": 0.0},
        )
        bucket["export_value_usd"] += safe_customs_number(row.get("export_value_usd"))
        bucket["import_value_usd"] += safe_customs_number(row.get("import_value_usd"))
    top_countries = sorted(
        country_buckets.values(),
        key=lambda item: item["export_value_usd"] + item["import_value_usd"],
        reverse=True,
    )[:5]
    if export_value > import_value * 1.2:
        signal = "수출 우위"
        inventory_signal = "재고 부담 낮음 또는 해외 수요 우위 가능성"
    elif import_value > export_value * 1.2:
        signal = "수입/재고 부담 우위"
        inventory_signal = "원재료·재고 축적 또는 내수/생산 투입 부담 확인 필요"
    else:
        signal = "균형"
        inventory_signal = "수출입 균형권. 가격/재고 지표와 함께 재확인"
    return {
        "item_code": theme["item_code"],
        "label": theme["label"],
        "linked_sectors": theme["linked_sectors"],
        "watch_reason": theme["watch_reason"],
        "row_count": len(rows),
        "export_value_usd": export_value,
        "import_value_usd": import_value,
        "trade_balance_usd": balance,
        "export_weight": export_weight,
        "import_weight": import_weight,
        "signal": signal,
        "inventory_signal": inventory_signal,
        "top_countries": top_countries,
    }


def build_customs_trade_snapshot(
    *,
    settings: Settings,
    start_yymm: str | None = None,
    end_yymm: str | None = None,
    item_code: str = "",
    country_code: str = "",
) -> dict:
    default_start, default_end, release_cycle = customs_default_period()
    start_yymm = sub(r"\D", "", start_yymm or default_start)[:6]
    end_yymm = sub(r"\D", "", end_yymm or default_end)[:6]
    if len(start_yymm) != 6 or len(end_yymm) != 6:
        raise HTTPException(status_code=422, detail="start_yymm/end_yymm은 YYYYMM 형식이어야 합니다.")

    themes = [
        theme
        for theme in CUSTOMS_STRATEGIC_ITEMS
        if not item_code or theme["item_code"].startswith(str(item_code).strip())
    ]
    if item_code and not themes:
        themes = [
            {
                "item_code": str(item_code).strip(),
                "label": f"HS {str(item_code).strip()}",
                "linked_sectors": ["사용자 지정 품목"],
                "watch_reason": "사용자 지정 품목의 수출입 흐름을 점검",
            }
        ]
    warnings: list[str] = []
    aggregates: list[dict] = []
    source_urls: list[str] = []
    raw_rows: list[dict] = []
    for theme in themes:
        fetched = fetch_customs_trade_rows(
            settings,
            start_yymm=start_yymm,
            end_yymm=end_yymm,
            item_code=theme["item_code"],
            country_code=country_code,
        )
        warnings.extend(fetched.get("warnings") or [])
        if fetched.get("source_url") and fetched["source_url"] not in source_urls:
            source_urls.append(fetched["source_url"])
        rows = fetched.get("rows") or []
        raw_rows.extend(rows[:20])
        aggregates.append(aggregate_customs_trade_rows(rows, theme))

    aggregates.sort(
        key=lambda item: abs(float(item.get("trade_balance_usd") or 0)),
        reverse=True,
    )
    key_takeaways = []
    for item in aggregates:
        if item["row_count"]:
            key_takeaways.append(
                f"{item['label']}은 {item['signal']} 신호입니다. "
                f"{item['inventory_signal']}."
            )
        else:
            key_takeaways.append(
                f"{item['label']}은 이번 조회 조건에서 표시 가능한 행이 없습니다. HS코드/기간/국가 조건을 재확인하세요."
            )
    sector_implications = [
        f"{item['label']} 관련 섹터({', '.join(item['linked_sectors'])})는 {item['signal']} 신호를 보조 지표로 반영합니다."
        for item in aggregates
    ]
    return {
        "status": "success",
        "module": "korea_customs_trade_snapshot",
        "source": "관세청 품목별 국가별 수출입실적(GW)",
        "release_schedule": "매월 1일, 11일, 21일 발표 자료를 우선 확인",
        "release_cycle": release_cycle,
        "start_yymm": start_yymm,
        "end_yymm": end_yymm,
        "item_code": item_code,
        "country_code": country_code,
        "source_urls": source_urls,
        "warnings": list(dict.fromkeys(warnings))[:5],
        "aggregates": aggregates,
        "raw_rows_preview": raw_rows[:20],
        "key_takeaways": key_takeaways,
        "sector_implications": sector_implications,
        "portfolio_usage": [
            "수출 비중이 큰 보유 종목은 해당 품목의 수출 우위/둔화를 투자 논거 가중치에 반영합니다.",
            "수입이 수출보다 빠르게 늘면 원재료·재고 부담 가능성을 리스크 스캔에 보조 신호로 반영합니다.",
            "시장일지와 일일 브리핑은 이 데이터를 섹터 흐름·재고 사이클 체크포인트로 자동 참조합니다.",
        ],
        "generated_at": current_storage_timestamp(),
    }


def render_customs_trade_markdown(snapshot: dict, storage_date: date) -> str:
    aggregate_lines = []
    for item in snapshot.get("aggregates", []):
        aggregate_lines.append(
            f"- {item['label']}({item['item_code']}): {item['signal']} / "
            f"수출 ${item['export_value_usd']:,.0f}, 수입 ${item['import_value_usd']:,.0f}, "
            f"무역수지 ${item['trade_balance_usd']:,.0f} / {item['inventory_signal']}"
        )
    return f"""---
ticker: CUSTOMS
type: customs-trade-brief
date: {storage_date.isoformat()}
module: korea_customs_trade_snapshot
source: korea_customs_service_public_data
period: {snapshot.get('start_yymm')}~{snapshot.get('end_yymm')}
---

# 관세청 수출입 동향 투자 참고자료: {snapshot.get('start_yymm')}~{snapshot.get('end_yymm')}

## 발표 주기

- {snapshot.get('release_schedule')}
- 현재 반영 기준: {snapshot.get('release_cycle')}

## 핵심 신호

{chr(10).join(f"- {item}" for item in snapshot.get("key_takeaways", []))}

## 품목별 요약

{chr(10).join(aggregate_lines) if aggregate_lines else "- 표시할 품목 데이터가 없습니다."}

## 섹터 시사점

{chr(10).join(f"- {item}" for item in snapshot.get("sector_implications", []))}

## 포트폴리오 활용

{chr(10).join(f"- {item}" for item in snapshot.get("portfolio_usage", []))}

## 데이터 경고

{chr(10).join(f"- {item}" for item in snapshot.get("warnings", [])) if snapshot.get("warnings") else "- 표시할 경고 없음"}
"""


def save_customs_trade_snapshot(snapshot: dict, settings: Settings) -> dict:
    storage_date = current_storage_date()
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    markdown = render_customs_trade_markdown(snapshot, storage_date)
    storage = save_research_markdown(
        vault_dir=vault_dir,
        ticker="CUSTOMS",
        report_type="customs-trade-brief",
        markdown=markdown,
        structured_payload=snapshot,
        manifest_entry={
            "summary": (
                f"관세청 수출입 동향 {snapshot.get('start_yymm')}~{snapshot.get('end_yymm')}: "
                f"{'; '.join(snapshot.get('key_takeaways', [])[:2]) or '요약 없음'}"
            ),
            "source": snapshot.get("source"),
            "source_confidence": 0.88 if not snapshot.get("warnings") else 0.72,
            "tags": ["customs", "trade", "exports", "imports", "inventory", "macro", "sector"],
            "sector_implications": snapshot.get("sector_implications", []),
            "release_schedule": snapshot.get("release_schedule"),
        },
        report_date=storage_date,
        file_suffix=f"{snapshot.get('start_yymm')}-{snapshot.get('end_yymm')}",
    )
    rag_document = upsert_saved_workflow_rag_document(
        vault_dir=vault_dir,
        storage=storage,
        storage_key="CUSTOMS",
        report_type="customs-trade-brief",
        summary=(
            f"관세청 수출입 동향 {snapshot.get('start_yymm')}~{snapshot.get('end_yymm')}: "
            f"{'; '.join(snapshot.get('key_takeaways', [])[:2]) or '요약 없음'}"
        ),
        markdown=markdown,
        tags=["customs", "exports", "imports", "inventory", "macro", "sector"],
        source_confidence=0.88 if not snapshot.get("warnings") else 0.72,
        metadata={
            "source": snapshot.get("source"),
            "source_urls": snapshot.get("source_urls"),
            "release_schedule": snapshot.get("release_schedule"),
            "sector_implications": snapshot.get("sector_implications"),
        },
    )
    return {**snapshot, "storage": storage, "rag_document": rag_document}


def should_check_customs_trade_today(settings: Settings, selected_date: date | None = None) -> bool:
    today = selected_date or current_storage_date()
    try:
        release_days = {
            int(value.strip())
            for value in str(settings.customs_trade_release_days or "1,11,21").split(",")
            if value.strip()
        }
    except ValueError:
        release_days = {1, 11, 21}
    return today.day in release_days


def build_daily_customs_trade_reference(settings: Settings) -> dict | None:
    if not should_check_customs_trade_today(settings):
        return None
    try:
        snapshot = build_customs_trade_snapshot(settings=settings)
    except Exception as exc:
        return {
            "status": "warning",
            "summary": f"관세청 수출입 동향 자동 확인 실패: {provider_error_message(exc, settings)}",
            "release_schedule": settings.customs_trade_release_days,
            "key_takeaways": [],
            "warnings": [provider_error_message(exc, settings)],
        }
    return {
        "status": "success",
        "source": snapshot.get("source"),
        "period": f"{snapshot.get('start_yymm')}~{snapshot.get('end_yymm')}",
        "release_cycle": snapshot.get("release_cycle"),
        "key_takeaways": snapshot.get("key_takeaways", [])[:4],
        "sector_implications": snapshot.get("sector_implications", [])[:4],
        "warnings": snapshot.get("warnings", [])[:3],
    }


@app.get(
    "/api/v1/macro/customs-trade/latest",
    dependencies=[Depends(verify_user_token)],
)
def read_latest_customs_trade_snapshot(
    start_yymm: str | None = Query(default=None),
    end_yymm: str | None = Query(default=None),
    item_code: str = Query(default=""),
    country_code: str = Query(default=""),
    save_result: bool = Query(default=True),
    settings: Settings = Depends(get_settings),
) -> dict:
    snapshot = build_customs_trade_snapshot(
        settings=settings,
        start_yymm=start_yymm,
        end_yymm=end_yymm,
        item_code=item_code,
        country_code=country_code,
    )
    if save_result:
        return save_customs_trade_snapshot(snapshot, settings)
    return snapshot

@app.post(
    "/api/v1/alerts/backend-health",
    dependencies=[Depends(verify_user_token)],
)
def record_backend_health_alert(
    payload: dict | None = Body(default=None),
    settings: Settings = Depends(get_settings),
) -> dict:
    payload = payload if isinstance(payload, dict) else {}
    now = current_storage_timestamp()
    alert = {
        "status": "recorded",
        "module": "backend_health_alert",
        "alert_type": str(payload.get("alert_type") or "backend_status_warning"),
        "severity": str(payload.get("severity") or "warning"),
        "source": str(payload.get("source") or "research_console"),
        "message": str(payload.get("message") or "백엔드 상태 확인 경고가 기록되었습니다."),
        "api_base": str(payload.get("api_base") or ""),
        "client_timestamp": payload.get("client_timestamp"),
        "server_timestamp": now,
    }
    append_jsonl(backend_health_alert_path(settings), alert)
    push_ready = bool(
        os.getenv("EXPO_PUSH_TOKEN")
        or os.getenv("FCM_SERVER_KEY")
        or os.getenv("FCM_SERVICE_ACCOUNT_JSON")
    )
    alert["mobile_push_ready"] = push_ready
    alert["mobile_push_status"] = "push_config_detected" if push_ready else "push_key_not_configured"
    alert["next_step"] = "EXPO_PUSH_TOKEN 또는 FCM 설정을 연결하면 동일 이벤트를 모바일 푸시로 전달할 수 있습니다."
    return alert

@app.get(
    "/api/v1/data-providers/snapshot/{ticker}",
    dependencies=[Depends(verify_user_token)],
)
def read_data_provider_snapshot(
    ticker: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    official_ticker = ensure_verified_ticker(ticker)
    live_refresh = refresh_earnings_calendar_for_ticker_if_stale(official_ticker, settings)
    provider = get_analysis_data_provider(settings)
    injected_data = collect_analysis_input_data(
        ticker=official_ticker,
        provided_data=[],
        auto_inject_data=True,
        settings=settings,
    )
    return {
        "status": "success",
        "module": "data_provider_snapshot",
        "ticker": official_ticker,
        "provider_mode": settings.data_provider_mode,
        "live_refresh": live_refresh,
        "auto_inject_analysis_data": settings.auto_inject_analysis_data,
        "providers": provider.status(),
        "data_points": [item.model_dump(mode="json") for item in injected_data],
    }


@app.get(
    "/api/v1/institutional-flow/nps/{ticker}",
    dependencies=[Depends(verify_user_token)],
)
def read_nps_institutional_flow(
    ticker: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    공공데이터포털 국민연금 국내주식 투자정보와 대량보유 보고내역을
    티커/회사명 기준으로 정규화해 반환합니다.
    """
    official_ticker = ensure_verified_ticker(ticker)
    profile = build_ticker_profile(official_ticker, settings)
    signal = fetch_nps_institutional_signal(
        official_ticker,
        profile.company_name,
        settings,
    )
    return {
        "status": "success",
        "module": "nps_institutional_flow",
        "ticker": official_ticker,
        "company_name": profile.company_name,
        "signal": signal,
        "data_points": [
            item.model_dump(mode="json")
            for item in fetch_nps_institutional_context(
                official_ticker,
                profile.company_name,
                settings,
            )
        ],
    }


@app.get(
    "/api/v1/portfolios/{portfolio_name}/institutional-flow/nps",
    dependencies=[Depends(verify_user_token)],
)
def read_portfolio_nps_institutional_flow(
    portfolio_name: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    저장된 포트폴리오의 국내 보유 종목을 국민연금 보유/대량보유 데이터와 일괄 매칭합니다.
    ETF나 해외주식처럼 공공데이터포털 보유주식 레코드와 직접 맞지 않는 항목은 건너뜁니다.
    """
    store = read_portfolio_store(settings)
    portfolio_payload = store.get("portfolios", {}).get(portfolio_store_key(portfolio_name))
    if not portfolio_payload:
        raise HTTPException(status_code=404, detail=f"{portfolio_name} 포트폴리오를 찾을 수 없습니다.")
    portfolio = SavedPortfolio.model_validate(portfolio_payload)
    signals: list[dict] = []
    matched_count = 0
    warning_count = 0
    total_market_value = float(portfolio.portfolio_value or 0)
    seen: set[str] = set()
    for holding in portfolio.holdings:
        ticker = normalize_ticker(holding.ticker)
        if ticker in seen:
            continue
        seen.add(ticker)
        if not fullmatch(r"\d{6}", ticker):
            continue
        signal = fetch_nps_institutional_signal(ticker, holding.name, settings)
        events = signal.get("large_holding_events") or []
        matched = bool(signal.get("domestic_match_found") or events)
        if matched:
            matched_count += 1
        if signal.get("warnings"):
            warning_count += len(signal.get("warnings") or [])
        latest_event = events[0] if events else {}
        latest_ratio = signal.get("holding_ratio")
        if latest_ratio is None and isinstance(latest_event, dict):
            latest_ratio = latest_event.get("holding_ratio")
        signals.append(
            {
                "ticker": ticker,
                "holding_name": holding.name,
                "market_value": holding.market_value,
                "portfolio_weight": (
                    round(float(holding.market_value or 0) / total_market_value, 6)
                    if total_market_value > 0
                    else holding.weight
                ),
                "matched": matched,
                "domestic_match_found": signal.get("domestic_match_found"),
                "latest_holding_ratio": latest_ratio,
                "latest_event_date": latest_event.get("base_date") if isinstance(latest_event, dict) else None,
                "large_holding_event_count": len(events),
                "warnings": signal.get("warnings") or [],
                "signal": signal,
            }
        )
    signals.sort(
        key=lambda item: (
            not item.get("matched"),
            -(float(item.get("market_value") or 0)),
            item.get("ticker") or "",
        )
    )
    matched_signals = [item for item in signals if item.get("matched")]
    ratio_chart = sorted(
        [
            {
                "ticker": item.get("ticker"),
                "holding_name": item.get("holding_name"),
                "nps_holding_ratio": item.get("latest_holding_ratio"),
                "portfolio_weight": item.get("portfolio_weight"),
                "market_value": item.get("market_value"),
                "latest_event_date": item.get("latest_event_date"),
                "large_holding_event_count": item.get("large_holding_event_count") or 0,
            }
            for item in matched_signals
            if item.get("latest_holding_ratio") is not None
        ],
        key=lambda item: float(item.get("nps_holding_ratio") or 0),
        reverse=True,
    )
    exposure_chart = sorted(
        [
            {
                "ticker": item.get("ticker"),
                "holding_name": item.get("holding_name"),
                "nps_holding_ratio": item.get("latest_holding_ratio"),
                "portfolio_weight": item.get("portfolio_weight"),
                "market_value": item.get("market_value"),
                "latest_event_date": item.get("latest_event_date"),
            }
            for item in matched_signals
        ],
        key=lambda item: float(item.get("portfolio_weight") or 0),
        reverse=True,
    )
    institutional_flow_alerts: list[dict] = []
    outflow_terms = ["감소", "매도", "처분", "축소", "하락", "decrease", "sell", "sold", "reduced"]
    for item in matched_signals:
        signal = item.get("signal") or {}
        events = signal.get("large_holding_events") or []
        event_text = json.dumps(events[:3], ensure_ascii=False).lower()
        outflow_like = any(term in event_text for term in outflow_terms)
        if outflow_like or len(events) >= 2:
            institutional_flow_alerts.append(
                {
                    "ticker": item.get("ticker"),
                    "holding_name": item.get("holding_name"),
                    "severity": "high" if outflow_like else "medium",
                    "latest_event_date": item.get("latest_event_date"),
                    "event_count": len(events),
                    "reason": (
                        "최근 국민연금 대량보유 보고에 감소/처분성 표현이 감지되었습니다."
                        if outflow_like
                        else "대량보유 보고 이벤트가 반복 확인되어 수급 변화 복기가 필요합니다."
                    ),
                    "action": "추가 매수 전 보고 기준일, 증감 방향, 동일 섹터 동반 매도 여부를 확인하세요.",
                }
            )
    research_assist_notes = []
    if ratio_chart:
        top = ratio_chart[0]
        research_assist_notes.append(
            f"{top.get('holding_name') or top.get('ticker')}은 국민연금 지분율 {float(top.get('nps_holding_ratio') or 0):.2f}%로 포트폴리오 내 기관 수급 확인 우선순위가 높습니다."
        )
    if institutional_flow_alerts:
        alert = institutional_flow_alerts[0]
        research_assist_notes.append(
            f"{alert.get('holding_name') or alert.get('ticker')}은 {alert.get('reason')} 리서치 리포트 작성 시 수급 리스크 단락에 반영하세요."
        )
    if not research_assist_notes:
        research_assist_notes.append(
            "현재 매칭 기준에서는 국민연금 대형 수급 이탈 신호가 뚜렷하지 않습니다. 추후 공공데이터 업데이트 시 다시 점검하세요."
        )
    return {
        "status": "success",
        "module": "portfolio_nps_institutional_flow",
        "portfolio_name": portfolio.portfolio_name,
        "holding_count": portfolio.holding_count or len(portfolio.holdings),
        "checked_count": len(signals),
        "matched_count": matched_count,
        "warning_count": warning_count,
        "signals": signals,
        "visualization": {
            "ratio_chart": ratio_chart[:12],
            "portfolio_exposure_chart": exposure_chart[:12],
        },
        "institutional_flow_alerts": institutional_flow_alerts[:12],
        "research_assist_notes": research_assist_notes,
        "next_actions": [
            "국민연금 지분율이 높은 종목은 팀 리포트의 기관 수급 근거에 반영하세요.",
            "대량보유 보고 이벤트가 반복되거나 감소성 문구가 있는 종목은 리스크 스캔에서 수급 이탈 후보로 추적하세요.",
            "ETF와 해외주식은 공공데이터포털 국민연금 개별 국내주식 자료와 직접 매칭되지 않을 수 있습니다.",
        ],
        "summary": (
            f"{portfolio.portfolio_name} 포트폴리오 국내 보유 {len(signals)}개 중 "
            f"{matched_count}개에서 국민연금 보유/대량보유 신호가 확인되었습니다."
        ),
    }


@app.get(
    "/api/v1/tickers/verify/{ticker}",
    response_model=TickerVerificationResponse,
    dependencies=[Depends(verify_user_token)],
)
def verify_ticker(
    ticker: str,
    fast: bool = False,
    settings: Settings = Depends(get_settings),
) -> TickerVerificationResponse:
    """
    입력 티커가 공식 티커 레지스트리에 있는지 확인합니다.
    모든 티커 기반 분석은 이 인증 결과의 official_symbol을 기준으로 실행합니다.
    """
    if fast:
        return verify_ticker_symbol_local_cached(ticker, settings)
    return verify_ticker_symbol(ticker, settings)


@app.get(
    "/api/v1/tickers/profile/{ticker}",
    response_model=TickerProfileResponse,
    dependencies=[Depends(verify_user_token)],
)
def get_ticker_profile(
    ticker: str,
    refresh_external: bool = True,
    settings: Settings = Depends(get_settings),
) -> TickerProfileResponse:
    """
    공식 티커 인증 결과와 회사별 분석 초점, 핵심 KPI, 데이터 한계를 함께 반환합니다.
    """
    if refresh_external:
        normalized_ticker = ensure_verified_ticker(ticker, settings)
    else:
        verification = verify_ticker_symbol_local_cached(ticker, settings)
        if not verification.verified:
            raise HTTPException(status_code=422, detail=verification.message)
        normalized_ticker = verification.official_symbol
    return build_ticker_profile(
        normalized_ticker,
        settings,
        refresh_external=refresh_external,
    )



@app.get(
    "/api/v1/earnings-calendar/status",
    dependencies=[Depends(verify_user_token)],
)
def get_earnings_calendar_status(settings: Settings = Depends(get_settings)) -> dict:
    cache = read_earnings_calendar_cache(settings)
    entries = cache.get("entries") or {}
    return {
        "status": "success",
        "module": "earnings_calendar_cache",
        "auto_refresh": settings.earnings_calendar_auto_refresh,
        "refresh_hours": settings.earnings_calendar_refresh_hours,
        "updated_at": cache.get("updated_at"),
        "cache_path": str(earnings_calendar_cache_path(settings)),
        "entry_count": len(entries),
        "entries": entries,
    }


@app.post(
    "/api/v1/earnings-calendar/refresh",
    dependencies=[Depends(verify_user_token)],
)
def refresh_earnings_calendar(
    ticker: str | None = None,
    settings: Settings = Depends(get_settings),
) -> dict:
    tickers = [ensure_verified_ticker(ticker, settings)] if ticker else None
    return refresh_earnings_calendar_cache(settings, tickers)


@app.get(
    "/api/v1/shinhan-research/status",
    dependencies=[Depends(verify_user_token)],
)
def get_shinhan_research_status(settings: Settings = Depends(get_settings)) -> dict:
    cache = read_shinhan_research_cache(settings)
    entries = cache.get("entries") if isinstance(cache.get("entries"), dict) else {}
    recent_entries = sorted(
        entries.values(),
        key=lambda item: str(item.get("ingested_at") or item.get("published_at") or ""),
        reverse=True,
    )[:20]
    return {
        "status": "success",
        "module": "shinhan_research_ingest",
        "enabled": settings.shinhan_research_enabled,
        "auto_refresh": settings.shinhan_research_auto_refresh,
        "refresh_hours": settings.shinhan_research_refresh_hours,
        "source_url": settings.shinhan_research_list_url,
        "updated_at": cache.get("updated_at"),
        "entry_count": len(entries),
        "recent_entries": recent_entries,
        "cache_path": str(shinhan_research_cache_path(settings)),
    }


@app.post(
    "/api/v1/shinhan-research/refresh",
    dependencies=[Depends(verify_user_token)],
)
def refresh_shinhan_research(
    limit: int | None = None,
    force: bool = False,
    save_result: bool = True,
    settings: Settings = Depends(get_settings),
) -> dict:
    return refresh_shinhan_research_cache(
        settings,
        limit=limit,
        force=force,
        save_result=save_result,
    )



@app.get(
    "/api/v1/naver-research/status",
    dependencies=[Depends(verify_user_token)],
)
def get_naver_research_status(settings: Settings = Depends(get_settings)) -> dict:
    cache = read_naver_research_cache(settings)
    entries = cache.get("entries") if isinstance(cache.get("entries"), dict) else {}
    recent_entries = sorted(
        entries.values(),
        key=lambda item: str(item.get("ingested_at") or item.get("published_at") or ""),
        reverse=True,
    )[:20]
    return {
        "status": "success",
        "module": "naver_research_ingest",
        "enabled": settings.naver_research_enabled,
        "auto_refresh": settings.naver_research_auto_refresh,
        "refresh_hours": settings.naver_research_refresh_hours,
        "source_url": settings.naver_research_list_url,
        "updated_at": cache.get("updated_at"),
        "entry_count": len(entries),
        "recent_entries": recent_entries,
        "cache_path": str(naver_research_cache_path(settings)),
    }


@app.post(
    "/api/v1/naver-research/refresh",
    dependencies=[Depends(verify_user_token)],
)
def refresh_naver_research(
    limit: int | None = None,
    force: bool = False,
    save_result: bool = True,
    settings: Settings = Depends(get_settings),
) -> dict:
    return refresh_naver_research_cache(
        settings,
        limit=limit,
        force=force,
        save_result=save_result,
    )
@app.get(
    "/api/v1/tickers/diagnose/{ticker}",
    dependencies=[Depends(verify_user_token)],
)
def diagnose_ticker(
    ticker: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    티커 인증 실패/성공 경로를 로컬 레지스트리, 자동 캐시, FMP 조회 단계별로 진단합니다.
    """
    return diagnose_ticker_symbol(ticker, settings)


@app.get(
    "/api/v1/tickers/cache",
    dependencies=[Depends(verify_user_token)],
)
def list_ticker_cache(settings: Settings = Depends(get_settings)) -> dict:
    """
    FMP 등 외부 데이터로 자동 인증되어 로컬 캐시에 저장된 티커 목록을 반환합니다.
    로컬 공식 레지스트리에 없는 티커도 한 번 인증되면 다음 분석부터 재사용됩니다.
    """
    entries = ticker_registry_cache_entries(settings)
    return {
        "status": "success",
        "module": "ticker_registry_cache",
        "local_registry_count": len(OFFICIAL_TICKER_REGISTRY),
        "cache_count": len(entries),
        "cache_path": str(dynamic_ticker_cache_path(settings)),
        "entries": entries,
    }


@app.delete(
    "/api/v1/tickers/cache/{ticker}",
    dependencies=[Depends(verify_user_token)],
)
def remove_ticker_cache_entry(
    ticker: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    자동 인증 캐시에서 특정 티커를 삭제합니다.
    로컬 공식 레지스트리 항목은 삭제하지 않습니다.
    """
    normalized_ticker = normalize_ticker(ticker)
    deleted = delete_dynamic_ticker_profile(normalized_ticker, settings)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"{normalized_ticker}는 자동 인증 캐시에 없습니다.",
        )
    entries = ticker_registry_cache_entries(settings)
    return {
        "status": "success",
        "module": "ticker_registry_cache",
        "deleted_ticker": normalized_ticker,
        "cache_count": len(entries),
        "entries": entries,
    }


@app.get("/api/v1/brokerage/status", response_model=BrokerStatus)
def read_brokerage_status(settings: Settings = Depends(get_settings)) -> BrokerStatus:
    return BrokerStatus(
        default_broker=Broker(settings.default_broker),
        first_integration_target=Broker.KIWOOM,
        adapters_ready=[Broker.KIWOOM],
        message="첫 증권사 연동 대상은 키움증권입니다. 한국투자증권은 후속 Adapter로 추가합니다.",
    )


@app.post(
    "/api/v1/brokerage/kiwoom/token-test",
    response_model=KiwoomMaskedTokenStatus,
    dependencies=[Depends(verify_user_token)],
)
def test_kiwoom_token_issue(
    settings: Settings = Depends(get_settings),
) -> KiwoomMaskedTokenStatus:
    """
    키움 OAuth 접근 토큰 발급을 테스트합니다.

    보안상 실제 token 원문은 반환하지 않고 마스킹된 값만 반환합니다.
    """
    return KiwoomAuthClient(settings).issue_masked_token_status()


@app.get(
    "/api/v1/trades",
    response_model=TradesResponse,
    dependencies=[Depends(verify_user_token)],
)
def get_recent_trades(
    brokerage_client: BrokerageClient = Depends(get_default_brokerage_client),
) -> TradesResponse:
    """
    증권사 API와 통신하여 최근 매매 내역을 가져오는 엔드포인트입니다.

    현재는 모바일 개발과 API 계약 검증을 위한 Mock 데이터를 반환합니다.
    첫 실제 연동 대상은 키움증권 Adapter입니다.
    """
    return TradesResponse(data=brokerage_client.fetch_recent_trades())


@app.get(
    "/api/v1/dashboard/{ticker}",
    response_model=TickerDashboardResponse,
    dependencies=[Depends(verify_user_token)],
)
def get_ticker_dashboard(
    ticker: str,
    settings: Settings = Depends(get_settings),
) -> TickerDashboardResponse:
    """
    티커 하나를 기준으로 저장된 리서치, 체크리스트 상태, 최근 캡처,
    매매/실적 분석 준비도와 다음 추천 작업을 한 화면에 묶어 반환합니다.
    """
    normalized_ticker = ensure_verified_ticker(ticker)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return build_ticker_dashboard(normalized_ticker, vault_dir, settings)


@app.get(
    "/api/v1/research-memory/{ticker}",
    response_model=ResearchMemoryListResponse,
    dependencies=[Depends(verify_user_token)],
)
def get_research_memory_files(
    ticker: str,
    include_archived: bool = Query(False),
    settings: Settings = Depends(get_settings),
) -> ResearchMemoryListResponse:
    """
    동일 워크스페이스에 자동 적재된 티커별 Markdown 리서치 파일 목록을 반환합니다.
    후속 분석 화면은 이 목록을 불러와 이전 분석 맥락을 연결할 수 있습니다.
    """
    normalized_ticker = resolve_research_memory_key(ticker, settings)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    visible_files = list_research_memory_files(normalized_ticker, vault_dir, include_archived=False)
    all_files = list_research_memory_files(normalized_ticker, vault_dir, include_archived=True)
    files = all_files if include_archived else visible_files
    manifest_entries = [
        entry
        for entry in read_manifest(vault_dir)
        if entry.get("ticker") == normalized_ticker
        and (include_archived or not is_archived_research_entry(entry))
    ]
    legacy_file_count = sum(1 for file in files if file.legacy)
    archived_file_count = sum(1 for file in all_files if file.archived or file.is_deleted)
    data_warnings = []
    if legacy_file_count:
        data_warnings.append(
            f"{normalized_ticker} 저장 파일 중 공식 티커 인증 도입 전 생성된 레거시 파일 {legacy_file_count}개가 있습니다. "
            "파일 본문은 열 수 있지만 투자 판단에는 새로 생성한 공식 인증 리포트를 우선 사용하세요."
        )
    if archived_file_count and not include_archived:
        data_warnings.append(
            f"{normalized_ticker} 저장 파일 중 보관 처리된 문서 {archived_file_count}개는 기본 목록에서 숨겨졌습니다. "
            "필요하면 보관 문서 포함 옵션으로 다시 확인하거나 복원하세요."
        )

    return ResearchMemoryListResponse(
        ticker=normalized_ticker,
        files=files,
        manifest_entries=manifest_entries,
        verified_file_count=sum(1 for file in files if file.verified),
        legacy_file_count=legacy_file_count,
        archived_file_count=archived_file_count,
        include_archived=include_archived,
        data_warnings=data_warnings,
    )


@app.get(
    "/api/v1/research-memory",
    response_model=ResearchManifestResponse,
    dependencies=[Depends(verify_user_token)],
)
def get_research_manifest(
    settings: Settings = Depends(get_settings),
) -> ResearchManifestResponse:
    """
    전체 리서치 메모리 manifest를 반환합니다.
    대시보드, 최근 분석 목록, 후속 분석 라우팅에 사용합니다.
    """
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return ResearchManifestResponse(entries=read_manifest(vault_dir))


@app.get(
    "/api/v1/rag/status",
    dependencies=[Depends(verify_user_token)],
)
def get_rag_memory_status(
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    티커별 최신 투자 논거 스냅샷 DB 상태를 반환합니다.
    빠른 정보 저장/논거 영향도 분석은 이 DB를 우선 조회한 뒤 manifest로 보완합니다.
    """
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return rag_memory_status(vault_dir)


@app.post(
    "/api/v1/rag/thesis-snapshot/backfill",
    dependencies=[Depends(verify_user_token)],
)
def backfill_rag_thesis_snapshots(
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    기존 manifest에 저장된 최신 팀 리포트 투자 논거를 RAG 스냅샷 DB로 이관합니다.
    """
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return backfill_thesis_snapshots_from_manifest(vault_dir)


@app.post(
    "/api/v1/rag/memory/backfill",
    dependencies=[Depends(verify_user_token)],
)
def backfill_rag_memory_documents(
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    기존 manifest의 모든 저장 보고서/메모를 검색 가능한 RAG 문서 색인으로 이관합니다.
    티커 없는 거시/섹터/시장 메모도 manifest 키 기준으로 색인합니다.
    """
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return backfill_research_memory_documents_from_manifest(vault_dir)


def _rag_synthesis_unique(values: list[str], limit: int = 8) -> list[str]:
    seen: set[str] = set()
    selected: list[str] = []
    for value in values:
        cleaned = " ".join(str(value or "").split())
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        selected.append(cleaned)
        if len(selected) >= limit:
            break
    return selected


def _rag_clean_text(value: str) -> str:
    cleaned = str(value or "")
    cleaned = sub(r"---.*?---", " ", cleaned, flags=DOTALL)
    cleaned = sub(r"이 문장은 중복 감지와 RAG 즉시 색인 테스트용이다[:：]?.*?(?=(?:[.!?。]|$))", " ", cleaned)
    cleaned = sub(r"자동화 검증 메모[:：]?", " ", cleaned)
    cleaned = sub(r"처리:\s*PDF 파일은 서버에서 본문 텍스트 추출을 시도하고,? 원본 PDF도 함께 저장합니다\.?", " ", cleaned)
    cleaned = sub(r"처리:\s*파일은 서버에서 본문 텍스트 추출을 시도하고,? 원본 PDF도 함께 저장합니다\.?", " ", cleaned)
    cleaned = sub(r"강세는\s+강세는", "강세는", cleaned)
    cleaned = sub(r"약세는\s+약세는", "약세는", cleaned)
    cleaned = sub(r"#+\s*", " ", cleaned)
    cleaned = sub(r"\b(md|pdf|json)\b\s*", " ", cleaned, flags=IGNORECASE)
    cleaned = sub(r"\b(OTHER|OFFICIAL_FILING|RESEARCH_MEMORY)\s*/\s*[^:]+:\s*", " ", cleaned)
    cleaned = sub(r"\bDataSourceType\.[A-Za-z_]+", " ", cleaned)
    cleaned = sub(r"\[첨부 파일\]\s*", " ", cleaned)
    cleaned = sub(r"파일명:\s*[^.。!?\\n\\r]{1,120}", " ", cleaned)
    cleaned = sub(r"MIME:\s*[^\\n\\r]+", " ", cleaned)
    cleaned = sub(r"크기:\s*\d+\s*bytes", " ", cleaned)
    cleaned = sub(r"저장 경로:\s*\\S+", " ", cleaned)
    cleaned = sub(r"tags:\s*[^\\n\\r]+", " ", cleaned, flags=IGNORECASE)
    cleaned = sub(r"\s+", " ", cleaned).strip(" -·")
    return cleaned


def _rag_should_skip_sentence(value: str) -> bool:
    lowered = str(value or "").casefold()
    skip_terms = [
        "테스트용",
        "rag 즉시 색인 테스트",
        "중복 감지",
        "syntax",
        "placeholder",
        "본문 텍스트 추출",
        "원본 pdf",
        "저장 경로",
        "mime:",
        "파일명:",
        "직접 매칭된 신호 없음",
        "계속 모니터링",
        "추적 항목 신호",
        "판단 근거 판단:",
        "확신도:",
        "latest_thesis_snapshot",
        "주입된 데이터 컨텍스트",
        "리서치 메모리 /",
        "연결 가능한 저장 리포트",
        "매매 전략:",
        "손절",
        "목표가",
        "분할 진입",
    ]
    return any(term in lowered for term in skip_terms)


def _rag_document_text(document: dict) -> str:
    summary = _rag_clean_text(str(document.get("summary") or ""))
    excerpt = _rag_clean_text(str(document.get("content_excerpt") or ""))
    title = _rag_clean_text(str(document.get("title") or document.get("source_file_name") or ""))
    pieces = [summary, excerpt if len(summary) < 90 else "", title if not summary else ""]
    return " ".join(piece for piece in pieces if piece)


def _rag_select_synthesis_documents(documents: list[dict]) -> list[dict]:
    excluded_report_types = {
        "rag-query-synthesis",
        "smart-trade-setup",
        "research-checklist",
        "chart-analysis",
        "portfolio-risk-scan",
        "reinforcement-portfolio-optimizer",
        "thesis-impact-review",
    }
    source_documents = [
        document
        for document in documents
        if str(document.get("report_type") or "").strip().lower()
        not in excluded_report_types
    ]
    if source_documents:
        documents = source_documents
    full_matches = [
        document
        for document in documents
        if str(document.get("match_strength") or "").strip() in {"완전", "전체"}
    ]
    if len(full_matches) < 2:
        return documents
    focus_tickers = {
        str(document.get("ticker") or "").upper()
        for document in full_matches
        if str(document.get("ticker") or "").upper() not in {"", "GENERAL", "MARKET", "SEARCH"}
    }
    if not focus_tickers:
        return full_matches
    selected: list[dict] = []
    seen: set[str] = set()
    for document in documents:
        ticker = str(document.get("ticker") or "").upper()
        report_type = str(document.get("report_type") or "").lower()
        if ticker not in focus_tickers:
            continue
        if report_type == "rag-query-synthesis":
            continue
        key = str(document.get("document_id") or document.get("source_relative_path") or document.get("source_file_name"))
        if key in seen:
            continue
        seen.add(key)
        selected.append(document)
    return selected or full_matches


def _rag_extract_lines(documents: list[dict], query_terms: list[str]) -> list[str]:
    lines: list[str] = []
    for document in documents:
        text = _rag_document_text(document)
        for part in findall(r"[^.!?\n\r。]+[.!?。]?", text):
            cleaned = _rag_clean_text(" ".join(part.split()))
            if len(cleaned) < 12:
                continue
            if _rag_should_skip_sentence(cleaned):
                continue
            if query_terms and not any(term in cleaned.casefold() for term in query_terms):
                continue
            ticker = document.get("ticker") or "범위 미확인"
            lines.append(f"{ticker}: {compact_representative_sentence(cleaned, 180)}")
    return _rag_synthesis_unique(lines, 10)


def _rag_filter_theme_lines(
    documents: list[dict],
    keywords: list[str],
    *,
    limit: int = 6,
    query_terms: list[str] | None = None,
) -> list[str]:
    selected: list[str] = []
    lowered_keywords = [keyword.casefold() for keyword in keywords]
    for document in documents:
        text = _rag_document_text(document)
        if _rag_should_skip_sentence(text):
            continue
        for part in findall(r"[^.!?\n\r。]+[.!?。]?", text):
            cleaned = _rag_clean_text(part)
            if len(cleaned) < 12 or _rag_should_skip_sentence(cleaned):
                continue
            lowered = cleaned.casefold()
            if not any(keyword in lowered for keyword in lowered_keywords):
                continue
            if query_terms and not any(term in lowered for term in query_terms):
                continue
            selected.append(
                f"{document.get('ticker') or '범위 미확인'}: "
                f"{compact_representative_sentence(cleaned, 190)}"
            )
    return _rag_synthesis_unique(selected, limit)


def _rag_synthesis_storage_key(documents: list[dict]) -> str:
    tickers = [
        str(document.get("ticker") or "").upper()
        for document in documents
        if str(document.get("ticker") or "").upper() not in {"", "GENERAL", "MARKET", "SEARCH"}
    ]
    unique_tickers = sorted(set(tickers))
    if len(unique_tickers) == 1:
        return unique_tickers[0]
    if not unique_tickers:
        return "MARKET"
    return "SEARCH"


def build_rag_query_synthesis_payload(
    *,
    query: str,
    search_result: dict,
) -> dict:
    candidate_documents = [
        document
        for document in list(search_result.get("documents") or [])
        if str(document.get("report_type") or "").lower() != "rag-query-synthesis"
    ]
    documents = _rag_select_synthesis_documents(candidate_documents)
    query_terms = [
        term.casefold()
        for term in findall(r"[A-Za-z0-9가-힣]{2,}", query)
    ][:8]
    tickers = sorted(
        {
            str(document.get("ticker") or "GENERAL").upper()
            for document in documents
            if str(document.get("ticker") or "GENERAL").upper() not in {"UNKNOWN"}
        }
    )
    tags = _rag_synthesis_unique(
        [
            str(tag)
            for document in documents
            for tag in (document.get("tags") or [])
            if str(tag).strip()
        ],
        14,
    )
    confidence_values = [
        float(document.get("source_confidence") or document.get("confidence") or 0.7)
        for document in documents
    ]
    confidence = (
        sum(confidence_values) / len(confidence_values)
        if confidence_values
        else 0.0
    )
    consensus_facts = _rag_extract_lines(documents, query_terms)
    if len(consensus_facts) < 3:
        consensus_facts = _rag_synthesis_unique(
            [
                f"{document.get('ticker') or '범위 미확인'}: "
                f"{compact_representative_sentence(_rag_clean_text(_rag_document_text(document)), 180)}"
                for document in documents[:8]
            ],
            8,
        )
    bull_thesis = _rag_filter_theme_lines(
        documents,
        ["성장", "수요", "매출", "마진", "개선", "강세", "상회", "수출", "계약", "positive", "bull"],
        query_terms=query_terms,
    )
    bear_thesis = _rag_filter_theme_lines(
        documents,
        ["리스크", "둔화", "압박", "하락", "약세", "비용", "경쟁", "감소", "불확실", "risk", "bear"],
        query_terms=query_terms,
    )
    cruxes = _rag_synthesis_unique(
        [
            f"{query} 판단을 좌우하는 쟁점: {compact_representative_sentence(_rag_document_text(document), 160)}"
            for document in documents[:6]
            if not _rag_should_skip_sentence(_rag_document_text(document))
            and any(term in _rag_document_text(document).casefold() for term in query_terms)
        ],
        6,
    )
    observable_keywords = [
        "매출",
        "수출",
        "마진",
        "환율",
        "수요",
        "실적",
        "가이던스",
        "수급",
        "가격",
        "금리",
        "계약",
        "리스크",
    ]
    observables = _rag_synthesis_unique(
        [
            f"{keyword} 변화 추적"
            for keyword in observable_keywords
            if any(keyword in _rag_document_text(document) for document in documents)
        ],
        8,
    )
    next_actions = [
        "가장 관련도 높은 문서를 열어 원문 수치와 날짜를 확인하세요.",
        "공통 사실과 반대 논거가 충돌하는 지점을 팀 리포트 또는 매매 전략에 반영하세요.",
        "관찰 가능한 KPI가 새로 들어오면 같은 검색어로 합성을 다시 실행해 변화만 비교하세요.",
    ]
    summary = (
        f"'{query}' 검색 후보 {len(candidate_documents)}개 중 관련도가 높은 {len(documents)}개를 합성했습니다. "
        f"주요 범위는 {', '.join(tickers[:6]) if tickers else '시장/섹터 자료'}이며, "
        f"공통 사실과 강세/약세 논거를 분리해 후속 투자 판단에 사용할 수 있습니다."
    )
    source_documents = [
        {
            "ticker": document.get("ticker") or "GENERAL",
            "title": document.get("title") or document.get("source_file_name"),
            "report_type": document.get("report_type"),
            "source_file_name": document.get("source_file_name"),
            "source_relative_path": document.get("source_relative_path"),
            "source_date": document.get("source_date"),
            "quality_score": document.get("quality_score"),
            "relevance_score": document.get("relevance_score"),
            "match_strength": document.get("match_strength"),
            "summary": _rag_clean_text(document.get("summary") or document.get("content_excerpt") or ""),
        }
        for document in documents
    ]
    return {
        "query": query,
        "date": current_storage_date().isoformat(),
        "source_count": len(documents),
        "candidate_count": len(candidate_documents),
        "grouped_count": min(int(search_result.get("grouped_count") or len(documents)), len(documents)),
        "tickers": tickers,
        "tags": tags,
        "confidence": max(0.0, min(confidence, 1.0)),
        "summary": summary,
        "consensus_facts": consensus_facts,
        "bull_thesis": bull_thesis,
        "bear_thesis": bear_thesis,
        "cruxes": cruxes,
        "observables": observables or ["다음 자료 입력 때 확인할 KPI를 자동 추출할 수 있도록 관련 수치가 포함된 메모를 추가하세요."],
        "next_actions": next_actions,
        "source_documents": source_documents,
    }


def render_rag_query_synthesis_markdown(payload: dict) -> str:
    def bullet(items: list[str], empty: str = "표시할 항목이 없습니다.") -> str:
        if not items:
            return f"- {empty}"
        return "\n".join(f"- {item}" for item in items)

    source_lines = [
        f"- {item.get('ticker') or 'GENERAL'} · {item.get('source_date') or '날짜 없음'} · "
        f"{item.get('report_type') or '자료'} · {item.get('title') or item.get('source_file_name') or '제목 없음'}"
        for item in payload.get("source_documents", [])[:15]
    ]
    return f"""---
ticker: {_rag_synthesis_storage_key(payload.get("source_documents", []))}
type: rag-query-synthesis
date: {payload["date"]}
module: rag_query_synthesis
query: {payload["query"]}
---

# 저장 데이터 검색 합성 보고서

## 검색어

{payload["query"]}

## 요약

{payload["summary"]}

- 원천 문서: {payload["source_count"]}개
- 검색 후보: {payload.get("candidate_count", payload["source_count"])}개
- 중복 묶음 반영 후: {payload["grouped_count"]}개
- 합성 신뢰도: {payload["confidence"]:.0%}
- 관련 범위: {", ".join(payload["tickers"]) or "시장/섹터"}
- 태그: {", ".join(payload["tags"]) or "없음"}

## 합의된 사실

{bullet(payload["consensus_facts"])}

## 강세 논거

{bullet(payload["bull_thesis"])}

## 약세 논거

{bullet(payload["bear_thesis"])}

## 핵심 쟁점

{bullet(payload["cruxes"])}

## 앞으로 확인할 관찰 지표

{bullet(payload["observables"])}

## 다음 액션

{bullet(payload["next_actions"])}

## 사용한 저장 데이터

{chr(10).join(source_lines) if source_lines else "- 사용한 저장 데이터가 없습니다."}
"""


def build_rag_query_synthesis_thesis(
    ticker: str,
    payload: dict,
) -> tuple[InvestmentThesis, list[WatchItem]]:
    thesis = InvestmentThesis(
        ticker=ticker,
        thesis=payload["summary"],
        time_horizon="저장 데이터 검색 합성 기반 상시 업데이트",
        bull_triggers=payload.get("bull_thesis", [])[:8],
        bear_triggers=payload.get("bear_thesis", [])[:8],
        invalidation_conditions=payload.get("cruxes", [])[:8],
        watch_kpis=ticker_watch_kpis(ticker),
        valuation_assumptions={
            "method": "저장 데이터 검색 합성",
            "query": payload.get("query"),
            "confidence": payload.get("confidence"),
            "source_count": payload.get("source_count"),
            "candidate_count": payload.get("candidate_count"),
        },
        last_updated=payload.get("date"),
    )
    watch_items = [
        WatchItem(
            ticker=ticker,
            metric=str(item).split(":")[0].replace(" 변화 추적", "").strip() or "관찰 지표",
            condition=str(item),
            action="정보 입력, 시장일지, 실적 분석에서 새 자료가 들어오면 같은 검색어로 재합성",
            priority="medium",
        )
        for item in payload.get("observables", [])[:6]
    ]
    return thesis, watch_items


@app.post(
    "/api/v1/rag/memory/synthesize",
    dependencies=[Depends(verify_user_token)],
)
def synthesize_rag_memory_search_results(
    request: dict = Body(...),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    전체 저장 데이터 검색 결과를 투자 판단용 보고서로 합성합니다.
    Dossier가 종목 중심이라면 이 엔드포인트는 검색어/주제 중심입니다.
    """
    query = str(request.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=422, detail="검색어를 입력해야 합성할 수 있습니다.")
    limit = max(1, min(int(request.get("limit") or 12), 50))
    include_low_quality = bool(request.get("include_low_quality", False))
    save_result = bool(request.get("save_result", True))
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    search_result = search_all_research_memory_documents(
        vault_dir,
        query=query,
        limit=limit,
        include_low_quality=include_low_quality,
    )
    payload = build_rag_query_synthesis_payload(
        query=query,
        search_result=search_result,
    )
    storage = None
    rag_document = None
    thesis_snapshot = None
    if save_result:
        storage_key = _rag_synthesis_storage_key(payload["source_documents"])
        thesis = None
        watch_items: list[WatchItem] = []
        manifest_extra = {
            "summary": payload["summary"],
            "query": query,
            "source_count": payload["source_count"],
            "candidate_count": payload["candidate_count"],
            "grouped_count": payload["grouped_count"],
            "source_confidence": payload["confidence"],
            "tags": ["rag_query_synthesis", "search", "synthesis", *payload["tags"][:10]],
            "tickers": payload["tickers"],
            "consensus_facts": payload["consensus_facts"],
            "bull_thesis": payload["bull_thesis"],
            "bear_thesis": payload["bear_thesis"],
            "cruxes": payload["cruxes"],
            "observables": payload["observables"],
        }
        if storage_key not in {"SEARCH", "MARKET", "GENERAL", "UNKNOWN"}:
            thesis, watch_items = build_rag_query_synthesis_thesis(storage_key, payload)
            manifest_extra["investment_thesis"] = thesis.model_dump(mode="json")
            manifest_extra["watch_items"] = [
                item.model_dump(mode="json") for item in watch_items
            ]
        storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=storage_key,
            report_type="rag-query-synthesis",
            markdown=render_rag_query_synthesis_markdown(payload),
            structured_payload=payload,
            manifest_entry=manifest_extra,
            report_date=current_storage_date(),
            file_suffix=query,
        )
        if storage:
            saved_entry = next(
                (
                    entry
                    for entry in read_manifest(vault_dir)
                    if entry.get("file_name") == storage.file_name
                    and str(entry.get("ticker") or "").upper() == storage_key
                ),
                None,
            )
            if saved_entry:
                rag_document = upsert_research_memory_document(
                    vault_dir=vault_dir,
                    entry=saved_entry,
                )
        if thesis is not None and storage is not None:
            thesis_snapshot = upsert_ticker_thesis_snapshot(
                vault_dir=vault_dir,
                ticker=storage_key,
                company_name=ticker_company_name(storage_key),
                investment_thesis=thesis,
                watch_items=watch_items,
                source_entry={
                    "type": "rag-query-synthesis",
                    "date": payload["date"],
                    "file_name": storage.file_name,
                    "relative_path": storage.relative_path,
                },
                confidence=payload["confidence"],
            )

    return {
        "status": "success",
        "module": "rag_query_synthesis",
        "query": query,
        "payload": payload,
        "storage": storage.model_dump(mode="json") if storage else None,
        "rag_document": rag_document,
        "thesis_snapshot": thesis_snapshot,
    }


@app.get(
    "/api/v1/rag/memory/search",
    dependencies=[Depends(verify_user_token)],
)
def search_all_rag_memory_documents(
    query: str,
    limit: int = 12,
    include_low_quality: bool = False,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    전체 저장 데이터/RAG 색인을 자연어로 검색합니다.
    티커를 모를 때도 회사명, 섹터, 테마, 리스크, KPI 키워드로 관련 자료를 찾습니다.
    """
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return search_all_research_memory_documents(
        vault_dir,
        query=query,
        limit=limit,
        include_low_quality=include_low_quality,
    )


@app.get(
    "/api/v1/rag/memory/search/{key}",
    dependencies=[Depends(verify_user_token)],
)
def search_rag_memory_documents(
    key: str,
    query: str | None = None,
    limit: int = 5,
    include_low_quality: bool = False,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    티커 또는 일반 리서치 키의 저장 문서를 RAG 색인에서 검색합니다.
    공식 티커 인증 실패가 저장된 거시/섹터 자료 검색을 막지 않도록 키 정규화만 적용합니다.
    """
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return search_research_memory_documents(
        vault_dir,
        normalize_ticker(key),
        query=query,
        limit=limit,
        include_low_quality=include_low_quality,
    )


@app.get(
    "/api/v1/rag/thesis-snapshot/{ticker}",
    dependencies=[Depends(verify_user_token)],
)
def get_rag_thesis_snapshot(
    ticker: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    특정 티커의 최신 투자 논거 스냅샷을 반환합니다.
    """
    normalized_ticker = ensure_verified_ticker(ticker)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    snapshot = read_ticker_thesis_snapshot(vault_dir, normalized_ticker)
    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail=f"{normalized_ticker}의 RAG 투자 논거 스냅샷이 아직 없습니다.",
        )
    return {"status": "success", "ticker": normalized_ticker, "snapshot": snapshot}


@app.get(
    "/api/v1/dart/filings/status",
    dependencies=[Depends(verify_user_token)],
)
def get_dart_filing_watch_status(
    settings: Settings = Depends(get_settings),
) -> dict:
    cache = read_dart_filing_cache(settings)
    entries = cache.get("entries") if isinstance(cache, dict) else {}
    recent_entries = sorted(
        [
            item
            for item in (entries or {}).values()
            if isinstance(item, dict)
        ],
        key=lambda item: str(item.get("detected_at") or ""),
        reverse=True,
    )[:20]
    return {
        "status": "success",
        "module": "dart_filing_watch_status",
        "enabled": bool(settings.dart_filing_auto_refresh and settings.dart_api_key),
        "configured": bool(settings.dart_api_key),
        "refresh_hours": settings.dart_filing_refresh_hours,
        "lookback_days": settings.dart_filing_lookback_days,
        "target_tickers": dart_watch_tickers(settings),
        "updated_at": cache.get("updated_at"),
        "entry_count": len(entries or {}),
        "recent_entries": recent_entries,
        "last_failures": (cache.get("last_failures") or [])[:10],
        "cache_path": str(dart_filing_cache_path(settings)),
    }


@app.post(
    "/api/v1/dart/filings/refresh",
    dependencies=[Depends(verify_user_token)],
)
def run_dart_filing_watch_refresh(
    request: dict = Body(default_factory=dict),
    settings: Settings = Depends(get_settings),
) -> dict:
    tickers = request.get("tickers") if isinstance(request, dict) else None
    if isinstance(tickers, str):
        tickers = [item.strip() for item in tickers.split(",") if item.strip()]
    if not isinstance(tickers, list):
        tickers = None
    force = bool((request or {}).get("force", False))
    save_result = bool((request or {}).get("save_result", True))
    return refresh_dart_filing_watch(
        settings,
        tickers=[str(item) for item in tickers] if tickers else None,
        force=force,
        save_result=save_result,
    )


@app.post(
    "/api/v1/dossier/{ticker}/synthesize",
    dependencies=[Depends(verify_user_token)],
)
def run_dossier_synthesis(
    ticker: str,
    save_result: bool = True,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    저장된 리포트, 정보입력, 논거 영향도 분석을 중복 제거한 뒤 종목별 Dossier를 합성합니다.
    결과는 RAG 투자 논거 스냅샷 DB에도 반영되어 후속 분석이 최신 논거를 바로 사용합니다.
    """
    return synthesize_and_save_dossier(ticker, settings, save_result=save_result)


@app.get(
    "/api/v1/dossier/{ticker}",
    dependencies=[Depends(verify_user_token)],
)
def preview_dossier_synthesis(
    ticker: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    저장하지 않고 현재 저장 자료 기준의 Dossier 합성 결과를 미리 봅니다.
    """
    return synthesize_and_save_dossier(ticker, settings, save_result=False)


@app.post(
    "/api/v1/research-automation/run",
    dependencies=[Depends(verify_user_token)],
)
def run_research_automation(
    limit: int = 30,
    save_result: bool = True,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Mont Blanc식 로컬 우선 리서치 파이프라인을 실행합니다.
    외부 리서치 캐시 갱신, RAG 문서 색인, 종목별 Dossier 합성, 일일 브리핑 생성을 순서대로 수행합니다.
    """
    return run_research_automation_pipeline(
        settings,
        limit=limit,
        save_result=save_result,
    )


@app.get(
    "/api/v1/research-automation/status",
    dependencies=[Depends(verify_user_token)],
)
def get_research_automation_feature_status(
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    Pulls, De-dupes, Embeds, Tags, Syntheses, Delivers 등 자동 리서치 파이프라인의
    현재 적용 상태와 마지막 실행 상태를 반환합니다.
    """
    return build_research_automation_feature_status(settings)


@app.post(
    "/api/v1/research-automation/dedupes/review",
    dependencies=[Depends(verify_user_token)],
)
def run_storage_duplicate_review(
    limit: int = 80,
    save_result: bool = True,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    저장 데이터 전체를 훑어 대표 자료와 중복 의심 자료를 묶은 리뷰를 생성합니다.
    원본 파일은 삭제하지 않고, Dossier/RAG에서 어떤 자료를 대표로 볼지 판단하는 보조 데이터만 저장합니다.
    """
    return build_storage_duplicate_review(settings, limit=limit, save_result=save_result)


@app.post(
    "/api/v1/research-automation/dedupes/refresh-dossiers",
    dependencies=[Depends(verify_user_token)],
)
def run_deduped_dossier_refresh(
    limit: int = 8,
    save_result: bool = True,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    중복 리뷰에서 우선순위가 높은 종목을 골라 Dossier를 다시 합성합니다.
    같은 자료가 반복 저장된 종목의 최신 투자 논거 스냅샷을 대표 자료 기준으로 갱신합니다.
    """
    return run_deduped_dossier_refresh_queue(
        settings,
        limit=limit,
        save_result=save_result,
    )


@app.get(
    "/api/v1/research-automation/dedupes/review",
    dependencies=[Depends(verify_user_token)],
)
def get_storage_duplicate_review(
    settings: Settings = Depends(get_settings),
) -> dict:
    payload = read_json_store(storage_duplicate_review_path(settings), {})
    if payload:
        return payload
    return build_storage_duplicate_review(settings, save_result=False)


@app.get(
    "/api/v1/daily-briefing",
    dependencies=[Depends(verify_user_token)],
)
def get_daily_research_briefing(
    save_result: bool = False,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    보유/관심 종목의 Dossier 스냅샷과 최근 시장·종목 자료를 묶어 일일 브리핑을 생성합니다.
    """
    payload = build_daily_brief_payload(settings)
    if save_result:
        payload = save_daily_brief(payload, settings)
    return {"status": "success", "module": "daily_research_briefing", **payload}


@app.get(
    "/api/v1/research-memory/{ticker}/files/{file_name}",
    response_model=ResearchMemoryContentResponse,
    dependencies=[Depends(verify_user_token)],
)
def get_research_memory_file_content(
    ticker: str,
    file_name: str,
    settings: Settings = Depends(get_settings),
) -> ResearchMemoryContentResponse:
    """
    리서치 메모리 화면에서 선택한 Markdown 리포트의 본문을 반환합니다.
    파일명만 허용해 같은 티커 폴더 밖의 파일은 읽지 않습니다.
    """
    normalized_ticker = resolve_research_memory_key(ticker, settings)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return read_research_memory_file(normalized_ticker, file_name, vault_dir)


@app.patch(
    "/api/v1/research-memory/{ticker}/files/{file_name}/body-supplement",
    response_model=ResearchMemoryContentResponse,
    dependencies=[Depends(verify_user_token)],
)
def patch_research_memory_file_body(
    ticker: str,
    file_name: str,
    request: ResearchMemorySupplementRequest,
    settings: Settings = Depends(get_settings),
) -> ResearchMemoryContentResponse:
    """
    본문 추출이 제한된 URL-only 저장 자료에 사용자가 복사한 원문을 보강합니다.
    원본 파일은 삭제하거나 재작성하지 않고 별도 보강 섹션을 추가합니다.
    """
    normalized_ticker = resolve_research_memory_key(ticker, settings)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return supplement_research_memory_file(normalized_ticker, file_name, request, vault_dir)


@app.patch(
    "/api/v1/research-memory/{ticker}/files/{file_name}/archive",
    response_model=ResearchMemoryContentResponse,
    dependencies=[Depends(verify_user_token)],
)
def patch_research_memory_file_archive_status(
    ticker: str,
    file_name: str,
    request: ResearchMemoryArchiveRequest,
    settings: Settings = Depends(get_settings),
) -> ResearchMemoryContentResponse:
    """
    저장 리포트를 삭제하지 않고 보관/복원 상태만 바꿉니다.
    파일은 그대로 두고 manifest와 JSON sidecar에 status/is_deleted 플래그를 기록합니다.
    """
    normalized_ticker = resolve_research_memory_key(ticker, settings)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    return set_research_memory_archive_status(normalized_ticker, file_name, request, vault_dir)


@app.get(
    "/api/v1/research-memory/{ticker}/theses",
    response_model=InvestmentThesisListResponse,
    dependencies=[Depends(verify_user_token)],
)
def get_investment_theses(
    ticker: str,
    settings: Settings = Depends(get_settings),
) -> InvestmentThesisListResponse:
    """
    RAG 스냅샷 DB에서 티커별 최신 투자 논거와 watch item을 우선 추출합니다.
    새 뉴스나 데이터가 들어왔을 때 기존 논거와 비교하는 기반 API입니다.
    """
    normalized_ticker = ensure_verified_ticker(ticker)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    theses, watch_items = extract_manifest_theses_and_watch_items(
        normalized_ticker,
        vault_dir,
    )

    return InvestmentThesisListResponse(
        ticker=normalized_ticker,
        theses=theses,
        watch_items=watch_items,
    )


@app.post(
    "/api/v1/research-memory/thesis-impact/run",
    response_model=ThesisImpactResponse,
    dependencies=[Depends(verify_user_token)],
)
def run_thesis_impact_review(
    request: ThesisImpactRequest,
    settings: Settings = Depends(get_settings),
) -> ThesisImpactResponse:
    """
    새 뉴스, 실시간 데이터, 사용자 메모가 기존 투자 논거를 강화/약화/무관하게 만드는지 평가합니다.
    결과는 thesis-impact-review 리포트로 자동 저장되어 다음 후속 분석의 입력이 됩니다.
    """
    ticker = ensure_verified_ticker(request.ticker)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    theses, watch_items = extract_manifest_theses_and_watch_items(ticker, vault_dir)
    impact = evaluate_thesis_impact(ticker, request.new_data, theses, watch_items)
    impact.saved_to_research_memory = request.save_result

    if request.save_result:
        storage_date = current_storage_date()
        impact.storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=ticker,
            report_type="thesis-impact-review",
            markdown=render_thesis_impact_markdown(impact, storage_date),
            structured_payload=impact.model_dump(mode="json"),
            manifest_entry=manifest_with_ticker_verification(ticker, {
                "summary": impact.summary,
                "overall_impact": impact.overall_impact.value,
                "source_count": impact.source_count,
                "findings": [item.model_dump(mode="json") for item in impact.findings],
                "watch_item_signals": [
                    item.model_dump(mode="json") for item in impact.watch_item_signals
                ],
                "next_actions": impact.next_actions,
            }),
            report_date=storage_date,
        )

    return impact


@app.post(
    "/api/v1/research-memory/capture",
    response_model=ResearchCaptureResponse,
    dependencies=[Depends(verify_user_token)],
)
def capture_research_item(
    request: ResearchCaptureRequest,
    settings: Settings = Depends(get_settings),
) -> ResearchCaptureResponse:
    """
    사용자가 수집한 뉴스, 메모, 리포트 요약, 숫자 데이터를 즉시 저장합니다.
    옵션이 켜져 있으면 저장된 투자 논거에 대한 영향도 분석도 바로 실행합니다.
    """
    return save_capture_request(request, settings)


def save_capture_request(
    request: ResearchCaptureRequest,
    settings: Settings,
    attachment_info: dict | None = None,
    source_url_processing: dict | None = None,
    input_preview_override: str | None = None,
    document_preview_override: str | None = None,
) -> ResearchCaptureResponse:
    ticker = ensure_verified_ticker(request.ticker, settings)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    storage_date = current_storage_date()
    tags = infer_capture_tags(request.raw_content, request.tags)
    raw_content_hash = content_fingerprint(request.raw_content)
    duplicate_check = detect_capture_duplicate(
        vault_dir=vault_dir,
        ticker=ticker,
        title=request.title,
        raw_content=request.raw_content,
        source_url=request.source_url,
        content_hash=raw_content_hash,
    )
    captured_item = CapturedResearchItem(
        ticker=ticker,
        title=request.title,
        summary=summarize_capture(request.raw_content),
        source_type=request.source_type,
        source_url=request.source_url,
        as_of=request.as_of,
        confidence=request.confidence,
        tags=tags,
    )

    linked_impact = None
    if request.run_thesis_impact:
        impact_data = [
            InjectedDataPoint(
                source_type=request.source_type,
                label=request.title,
                value=request.raw_content,
                as_of=request.as_of,
                source_url=request.source_url,
                confidence=request.confidence,
            )
        ]
        theses, watch_items = extract_manifest_theses_and_watch_items(ticker, vault_dir)
        linked_impact = evaluate_thesis_impact(ticker, impact_data, theses, watch_items)
        linked_impact.saved_to_research_memory = request.save_result

    quality_status = capture_quality_status(
        raw_content=request.raw_content,
        attachment_info=attachment_info,
        source_url_processing=source_url_processing,
    )

    response = ResearchCaptureResponse(
        captured_item=captured_item,
        linked_impact=linked_impact,
        saved_to_research_memory=request.save_result,
        attachment=attachment_info,
        source_url_processing=source_url_processing,
        capture_quality=quality_status,
        duplicate_check=duplicate_check,
        input_preview=capture_preview_text(
            request.raw_content if input_preview_override is None else input_preview_override
        ),
        document_preview=capture_preview_text(
            (attachment_info or {}).get("extracted_text")
            if document_preview_override is None
            else document_preview_override
        ),
    )

    if request.save_result:
        manifest_extra = {
            "summary": captured_item.summary,
            "source_type": enum_or_str_value(captured_item.source_type),
            "source_url": captured_item.source_url,
            "confidence": captured_item.confidence,
            "tags": captured_item.tags,
            "attachment": attachment_info,
            "source_url_processing": source_url_processing,
            "capture_quality": quality_status,
            "capture_quality_status": quality_status["status"],
            "content_hash": raw_content_hash,
            "duplicate_check": duplicate_check,
            "linked_impact": linked_impact.model_dump(mode="json")
            if linked_impact
            else None,
        }
        if duplicate_check.get("is_duplicate_suspected"):
            manifest_extra["duplicate_reason"] = duplicate_check.get("reason")
            manifest_extra["duplicate_of"] = duplicate_check.get("matched_relative_path")
        response.storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=ticker,
            report_type="research-capture",
            markdown=render_research_capture_markdown(
                captured_item,
                request.raw_content,
                storage_date,
                attachment_info,
            ),
            structured_payload={
                **response.model_dump(mode="json"),
                "raw_content": request.raw_content,
                "attachment": attachment_info,
            },
            manifest_entry=manifest_with_ticker_verification(ticker, manifest_extra),
            report_date=storage_date,
            file_suffix=request.title,
        )
        if response.storage:
            saved_entry = next(
                (
                    entry
                    for entry in read_manifest(vault_dir)
                    if entry.get("file_name") == response.storage.file_name
                    and str(entry.get("ticker") or "").upper() == ticker
                ),
                None,
            )
            if saved_entry:
                response.rag_document = upsert_research_memory_document(
                    vault_dir=vault_dir,
                    entry=saved_entry,
                )

        if linked_impact is not None:
            linked_impact.storage = save_research_markdown(
                vault_dir=vault_dir,
                ticker=ticker,
                report_type="thesis-impact-review",
                markdown=render_thesis_impact_markdown(linked_impact, storage_date),
                structured_payload=linked_impact.model_dump(mode="json"),
                manifest_entry=manifest_with_ticker_verification(ticker, {
                    "summary": linked_impact.summary,
                    "overall_impact": linked_impact.overall_impact.value,
                    "source_count": linked_impact.source_count,
                    "findings": [
                        item.model_dump(mode="json")
                        for item in linked_impact.findings
                    ],
                    "watch_item_signals": [
                        item.model_dump(mode="json")
                        for item in linked_impact.watch_item_signals
                    ],
                    "next_actions": linked_impact.next_actions,
                    "linked_capture_file": response.storage.file_name
                    if response.storage
                    else None,
                }),
                report_date=storage_date,
            )

        if ticker not in SPECIAL_RESEARCH_KEYS:
            try:
                synthesize_and_save_dossier(ticker, settings, save_result=True)
            except Exception as exc:
                append_jsonl(
                    user_state_dir(settings) / "dossier_refresh_errors.jsonl",
                    {
                        "ticker": ticker,
                        "at": current_storage_timestamp(),
                        "source": "research_capture",
                        "error": str(exc),
                    },
                )

    return response


@app.post(
    "/api/v1/research-memory/auto-capture",
    response_model=ResearchCaptureResponse,
    dependencies=[Depends(verify_user_token)],
)
def auto_capture_research_item(
    request: AutoResearchCaptureRequest,
    settings: Settings = Depends(get_settings),
) -> ResearchCaptureResponse:
    """
    텍스트/파일 내용을 받아 티커, 제목, 출처 유형, 신뢰도를 자동 추론한 뒤 저장합니다.
    티커를 확정하지 못하면 INBOX에 저장해 후속 재분류가 가능하도록 보존합니다.
    """
    raw_content = (request.raw_content or "").strip()
    original_user_raw_content = raw_content
    source_url = (request.source_url or "").strip()
    raw_translation_info = (
        foreign_text_korean_digest(raw_content, "")
        if raw_content
        else {"status": "empty", "text": "", "language": "unknown", "note": ""}
    )
    if raw_translation_info.get("status") == "local_digest" and raw_translation_info.get("text"):
        raw_content = str(raw_translation_info["text"]).strip()
    url_info = fetch_capture_source_url(source_url) if source_url else {}
    url_body_context = render_source_url_body(url_info)
    url_title_context = (
        f"웹사이트 제목: {url_info.get('title')}"
        if source_url and url_info.get("title")
        else ""
    )
    original_input_preview = "\n".join(
        value
        for value in [
            raw_content,
            f"웹사이트 주소: {source_url}" if source_url else "",
        ]
        if value
    )
    if original_user_raw_content != raw_content:
        original_input_preview = "\n\n".join(
            value
            for value in [
                original_user_raw_content,
                "[한국어 분석용 변환본]",
                raw_content,
                f"웹사이트 주소: {source_url}" if source_url else "",
            ]
            if value
        )
    if not raw_content and not request.file_content_base64 and not source_url:
        raise HTTPException(
            status_code=422,
            detail="저장할 텍스트, 웹사이트 주소 또는 파일 내용이 비어 있습니다.",
        )
    url_text_unavailable = (
        source_url
        and is_unusable_source_url(url_info)
        and not raw_content
        and not request.file_content_base64
    )
    if url_text_unavailable:
        raw_content = render_url_only_capture_context(source_url, url_info)
        original_input_preview = raw_content

    inference_content = "\n\n".join(
        value for value in [raw_content, url_title_context, url_body_context] if value
    )
    if request.file_name:
        inference_content = "\n".join(
            value for value in [inference_content, f"첨부 파일명: {request.file_name}"] if value
        )
    if is_pdf_attachment(request.file_name, request.file_mime_type) and request.file_content_base64:
        pdf_bytes = decode_attachment_base64(request.file_content_base64)
        if pdf_bytes:
            pdf_text, pdf_note = extract_pdf_text(pdf_bytes)
            pdf_inference_context = "\n".join(
                value
                for value in [
                    f"첨부 PDF 텍스트 추출 상태: {pdf_note}",
                    f"첨부 PDF 본문:\n{pdf_text[:20000]}" if pdf_text else "",
                ]
                if value
            )
            inference_content = "\n\n".join(
                value for value in [inference_content, pdf_inference_context] if value
            )

    inferred_ticker, ticker_inference = infer_capture_ticker(inference_content, settings)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    attachment_info = (
        save_capture_attachment(
            vault_dir,
            inferred_ticker,
            current_storage_date(),
            request,
        )
        if request.save_result
        else None
    )
    attachment_context = render_attachment_context(request, attachment_info)
    if attachment_context and attachment_context not in raw_content:
        raw_content = "\n\n".join(value for value in [raw_content, attachment_context] if value)
    if url_body_context and url_body_context not in raw_content:
        raw_content = "\n\n".join(value for value in [raw_content, url_body_context] if value)
    source_type = (
        ticker_inference
        if inferred_ticker in SPECIAL_RESEARCH_KEYS - {"INBOX"}
        else infer_capture_source_type(raw_content, request.file_name)
    )
    tags = [f"auto_ticker:{ticker_inference}", "auto_classified"]
    if inferred_ticker in SPECIAL_RESEARCH_KEYS:
        tags.append(f"research_scope:{inferred_ticker.lower()}")
    tags = infer_capture_tags(raw_content, tags)
    if request.file_name:
        tags.append("file_input")
    if source_url:
        tags.append("url_input")
        tags.append("web_capture")
    if url_text_unavailable:
        tags.append("url_text_unavailable")
        tags.append("needs_body_copy")
    if raw_translation_info.get("status") == "local_digest":
        tags.append("foreign_text_converted")
    inferred_title = (
        (url_info.get("title") or "").strip()
        if source_url and not request.file_name
        else ""
    ) or infer_capture_title(raw_content, request.file_name)
    title = prefix_capture_title(inferred_title, inferred_ticker, ticker_inference)
    source_url_for_storage = (
        url_info.get("final_url")
        or url_info.get("source_url")
        or source_url
        or None
    )
    auto_request = ResearchCaptureRequest(
        ticker=inferred_ticker,
        title=title,
        raw_content=raw_content,
        source_type=source_type,
        source_url=source_url_for_storage,
        confidence=infer_capture_confidence(
            source_type,
            bool(request.file_name) or bool(url_info.get("text")),
        ),
        tags=tags,
        run_thesis_impact=request.run_thesis_impact
        and inferred_ticker not in SPECIAL_RESEARCH_KEYS,
        save_result=request.save_result,
    )
    response = save_capture_request(
        auto_request,
        settings,
        attachment_info=attachment_info,
        source_url_processing=url_info if source_url else None,
        input_preview_override=original_input_preview,
        document_preview_override=(
            (attachment_info or {}).get("extracted_text")
            or url_info.get("text")
            or (render_url_only_capture_context(source_url, url_info) if url_text_unavailable else "")
            or url_info.get("note")
        ),
    )
    response.captured_item.tags = sorted(set(response.captured_item.tags + tags))
    if inferred_ticker == "INBOX":
        response.captured_item.summary = (
            f"[티커 미확정: INBOX 저장] {response.captured_item.summary}"
        )
    elif inferred_ticker in SPECIAL_RESEARCH_KEYS - {"INBOX"}:
        response.captured_item.summary = (
            f"[{inferred_ticker} 자동 분류] {response.captured_item.summary}"
        )
    return response


PORTFOLIO_IMPORT_HEADERS = {
    "ticker": {"ticker", "symbol", "종목", "종목코드", "티커", "코드"},
    "name": {"name", "company", "company_name", "종목명", "회사명", "이름"},
    "quantity": {"quantity", "qty", "shares", "수량", "보유수량", "주식수"},
    "average_cost": {"average_cost", "avg_cost", "avg price", "평단", "평균단가", "매입가"},
    "current_price": {"current_price", "price", "last", "현재가", "가격"},
    "market_value": {"market_value", "value", "amount", "평가금액", "평가액", "금액"},
    "weight": {"weight", "비중", "비율"},
    "sector": {"sector", "섹터", "업종"},
    "theme_tags": {"theme_tags", "tags", "tag", "테마", "태그"},
}


def normalize_import_header(value: str) -> str:
    cleaned = sub(r"[\s_\-()/%]+", "", str(value or "").strip().lower())
    for target, aliases in PORTFOLIO_IMPORT_HEADERS.items():
        if cleaned in {sub(r"[\s_\-()/%]+", "", alias.lower()) for alias in aliases}:
            return target
    return cleaned


def parse_import_number(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    is_percent = "%" in text
    cleaned = sub(r"[^0-9.\-]+", "", text)
    if cleaned in {"", "-", "."}:
        return None
    try:
        number = float(cleaned)
    except ValueError:
        return None
    if is_percent:
        return number / 100
    return number


def portfolio_holding_from_row(row: dict[str, object]) -> PortfolioHolding | None:
    normalized = {normalize_import_header(key): value for key, value in row.items()}
    ticker = normalize_ticker(str(normalized.get("ticker") or normalized.get("symbol") or ""))
    if not ticker or ticker == "UNKNOWN":
        return None
    quantity = parse_import_number(normalized.get("quantity"))
    current_price = parse_import_number(normalized.get("current_price"))
    market_value = parse_import_number(normalized.get("market_value"))
    if market_value is None and quantity is not None and current_price is not None:
        market_value = quantity * current_price
    if ticker == "CASH" and market_value is None:
        market_value = current_price or parse_import_number(normalized.get("average_cost"))
    tags = [
        tag.strip()
        for tag in str(normalized.get("theme_tags") or "").replace(";", ",").split(",")
        if tag.strip()
    ]
    return PortfolioHolding(
        ticker=ticker,
        name=str(normalized.get("name") or "").strip() or None,
        quantity=quantity,
        average_cost=parse_import_number(normalized.get("average_cost")),
        current_price=current_price,
        market_value=market_value,
        weight=parse_import_number(normalized.get("weight")),
        sector=str(normalized.get("sector") or "Unknown").strip() or "Unknown",
        theme_tags=tags,
        currency="USD" if ticker != "CASH" else "USD",
    )


def parse_portfolio_delimited_text(text: str) -> tuple[list[PortfolioHolding], int, list[str]]:
    warnings: list[str] = []
    rows = [line for line in text.splitlines() if line.strip()]
    if not rows:
        return [], 0, ["파일에서 읽을 수 있는 행이 없습니다."]
    sample = "\n".join(rows[:8])
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        reader = csv.DictReader(io.StringIO("\n".join(rows)), dialect=dialect)
    except csv.Error:
        delimiter = "\t" if "\t" in sample else ","
        reader = csv.DictReader(io.StringIO("\n".join(rows)), delimiter=delimiter)
    holdings = [holding for record in reader if (holding := portfolio_holding_from_row(record))]
    if not holdings:
        warnings.append("헤더 기반 표를 찾지 못했습니다. 첫 행에 티커, 수량, 현재가, 평가금액 같은 열 이름을 넣어주세요.")
    return holdings, max(0, len(rows) - 1), warnings


def parse_portfolio_json_text(text: str) -> tuple[list[PortfolioHolding], int, list[str]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return [], 0, ["JSON 파일 형식을 읽지 못했습니다."]
    records = payload.get("holdings") if isinstance(payload, dict) else payload
    if not isinstance(records, list):
        return [], 0, ["JSON은 보유 종목 배열이거나 holdings 배열을 포함해야 합니다."]
    holdings = [
        holding
        for record in records
        if isinstance(record, dict) and (holding := portfolio_holding_from_row(record))
    ]
    warnings = [] if holdings else ["JSON에서 보유 종목을 인식하지 못했습니다."]
    return holdings, len(records), warnings


def parse_xlsx_shared_strings(zip_file: zipfile.ZipFile) -> list[str]:
    try:
        xml_bytes = zip_file.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ElementTree.fromstring(xml_bytes)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values = []
    for item in root.findall("x:si", namespace):
        texts = [node.text or "" for node in item.findall(".//x:t", namespace)]
        values.append("".join(texts))
    return values


def xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    cell_type = cell.attrib.get("t")
    value_node = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
    if value_node is None or value_node.text is None:
        inline = cell.find(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
        return inline.text if inline is not None and inline.text else ""
    value = value_node.text
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return ""
    return value


def xlsx_column_index(cell_ref: str) -> int:
    letters = "".join(char for char in cell_ref.upper() if char.isalpha())
    index = 0
    for char in letters:
        index = index * 26 + (ord(char) - ord("A") + 1)
    return max(index - 1, 0)


def parse_portfolio_xlsx(content: bytes) -> tuple[list[PortfolioHolding], int, list[str]]:
    warnings: list[str] = []
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as workbook:
            shared_strings = parse_xlsx_shared_strings(workbook)
            sheet_names = [
                name
                for name in workbook.namelist()
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            ]
            if not sheet_names:
                return [], 0, ["엑셀 파일에서 워크시트를 찾지 못했습니다."]
            sheet_xml = workbook.read(sorted(sheet_names)[0])
    except zipfile.BadZipFile:
        return [], 0, ["지원하지 않는 엑셀 형식입니다. .xlsx 또는 CSV로 다시 저장해 주세요."]
    root = ElementTree.fromstring(sheet_xml)
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    table_rows: list[list[str]] = []
    for row in root.findall(".//x:sheetData/x:row", namespace):
        values_by_column: dict[int, str] = {}
        for cell in row.findall("x:c", namespace):
            values_by_column[xlsx_column_index(cell.attrib.get("r", ""))] = xlsx_cell_value(
                cell,
                shared_strings,
            )
        max_column = max(values_by_column.keys(), default=-1)
        values = [values_by_column.get(index, "") for index in range(max_column + 1)]
        if any(str(value).strip() for value in values):
            table_rows.append(values)
    if len(table_rows) < 2:
        return [], len(table_rows), ["엑셀 파일에 헤더와 보유 종목 행이 필요합니다."]
    headers = [normalize_import_header(value) for value in table_rows[0]]
    holdings = []
    for values in table_rows[1:]:
        record = {headers[index]: value for index, value in enumerate(values) if index < len(headers)}
        holding = portfolio_holding_from_row(record)
        if holding:
            holdings.append(holding)
    if not holdings:
        warnings.append("엑셀에서 보유 종목을 인식하지 못했습니다. 첫 행에 티커/수량/평가금액 등의 열 이름을 넣어주세요.")
    return holdings, len(table_rows) - 1, warnings


@app.post(
    "/api/v1/portfolios/import-file",
    response_model=PortfolioImportResponse,
    dependencies=[Depends(verify_user_token)],
)
def import_portfolio_file(request: PortfolioImportRequest) -> PortfolioImportResponse:
    file_name = request.file_name.strip() or "portfolio"
    suffix = Path(file_name).suffix.lower()
    try:
        content = base64.b64decode(request.content_base64)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="파일 내용을 읽지 못했습니다.") from exc

    warnings: list[str] = []
    if suffix in {".xlsx"}:
        holdings, raw_rows, warnings = parse_portfolio_xlsx(content)
    elif suffix in {".xls"}:
        holdings, raw_rows, warnings = [], 0, ["구형 .xls는 직접 파싱하지 않습니다. .xlsx 또는 CSV로 저장해 불러오세요."]
    elif suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}:
        holdings, raw_rows, warnings = [], 0, ["사진 파일은 업로드 인식은 가능하지만 OCR 엔진이 아직 연결되지 않았습니다. 사진 속 표를 텍스트/CSV로 변환해 붙여넣거나 업로드하세요."]
    elif suffix == ".json":
        text = content.decode("utf-8-sig", errors="ignore")
        holdings, raw_rows, warnings = parse_portfolio_json_text(text)
    else:
        text = content.decode("utf-8-sig", errors="ignore")
        holdings, raw_rows, warnings = parse_portfolio_delimited_text(text)

    return PortfolioImportResponse(
        file_name=file_name,
        imported_holdings=holdings,
        raw_rows=raw_rows,
        warnings=warnings,
    )


@app.post(
    "/api/v1/portfolios/{portfolio_name}",
    response_model=PortfolioStoreResponse,
    dependencies=[Depends(verify_user_token)],
)
def save_portfolio(
    portfolio_name: str,
    request: PortfolioSaveRequest,
    settings: Settings = Depends(get_settings),
) -> PortfolioStoreResponse:
    store = read_portfolio_store(settings)
    key = portfolio_store_key(portfolio_name)
    request = request.model_copy(update={"portfolio_name": portfolio_name})
    saved = normalize_saved_portfolio(
        request,
        store.get("portfolios", {}).get(key),
        settings,
    )
    store.setdefault("portfolios", {})[key] = saved.model_dump(mode="json")
    write_json_store(portfolio_store_path(settings), store)
    return portfolio_store_response(settings, active_portfolio=saved)


@app.get(
    "/api/v1/portfolios",
    response_model=PortfolioStoreResponse,
    dependencies=[Depends(verify_user_token)],
)
def list_portfolios(
    settings: Settings = Depends(get_settings),
) -> PortfolioStoreResponse:
    return portfolio_store_response(settings)


@app.get(
    "/api/v1/portfolios/connectivity",
    dependencies=[Depends(verify_user_token)],
)
def check_portfolio_connectivity(
    settings: Settings = Depends(get_settings),
) -> dict:
    response = portfolio_store_response(settings)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    manifest_entries = read_manifest(vault_dir)
    by_ticker: dict[str, dict] = {}
    for portfolio in response.portfolios:
        for holding in portfolio.holdings:
            ticker = normalize_ticker(holding.ticker)
            if not ticker or ticker == "UNKNOWN":
                continue
            record = by_ticker.setdefault(
                ticker,
                {
                    "ticker": ticker,
                    "holding_name": holding.name,
                    "portfolios": [],
                    "stored_current_price": holding.current_price,
                    "stored_price_source": holding.price_source,
                    "currency": holding.currency,
                    "market_value": holding.market_value,
                    "missing_fields": [],
                },
            )
            if portfolio.portfolio_name not in record["portfolios"]:
                record["portfolios"].append(portfolio.portfolio_name)
            if record.get("stored_current_price") is None and holding.current_price is not None:
                record["stored_current_price"] = holding.current_price
                record["stored_price_source"] = holding.price_source
            if record.get("market_value") is None and holding.market_value is not None:
                record["market_value"] = holding.market_value

    items = []
    rag_document_counts = count_research_memory_documents_by_ticker(vault_dir, list(by_ticker.keys()))
    for ticker, record in sorted(by_ticker.items()):
        verification = verify_ticker_symbol(ticker, settings)
        profile = official_ticker_profile(verification.official_symbol, settings) if verification.verified else {}
        official_symbol = normalize_ticker(verification.official_symbol or ticker)
        memory_count = sum(
            1
            for entry in manifest_entries
            if normalize_ticker(str(entry.get("ticker") or "")) in {ticker, official_symbol}
        )
        try:
            thesis_snapshot = read_ticker_thesis_snapshot(vault_dir, official_symbol)
        except Exception:
            thesis_snapshot = None
        rag_document_count = rag_document_counts.get(official_symbol) or rag_document_counts.get(ticker) or 0
        missing_fields: list[str] = []
        if not verification.verified:
            missing_fields.append("공식 티커 인증")
        if record.get("stored_current_price") is None:
            missing_fields.append("저장 현재가")
        if not profile.get("sector"):
            missing_fields.append("섹터")
        if not profile.get("business_context"):
            missing_fields.append("사업 맥락")
        if memory_count < 1:
            missing_fields.append("저장 리포트")
        if not thesis_snapshot:
            missing_fields.append("투자 논거 스냅샷")
        if rag_document_count < 1:
            missing_fields.append("RAG 검색 문서")

        connected = verification.verified and not missing_fields
        items.append(
            {
                "ticker": ticker,
                "official_symbol": verification.official_symbol,
                "connected": connected,
                "verified": verification.verified,
                "company_name": verification.company_name or record.get("holding_name") or ticker,
                "exchange": verification.exchange,
                "country": verification.country,
                "asset_type": verification.asset_type,
                "sector": profile.get("sector") or "미분류",
                "industry": profile.get("industry") or "",
                "business_context": profile.get("business_context") or "",
                "analysis_focus": profile.get("analysis_focus") or "",
                "watch_kpis": profile.get("watch_kpis", []),
                "portfolios": record["portfolios"],
                "stored_current_price": record.get("stored_current_price"),
                "stored_price_source": record.get("stored_price_source"),
                "currency": record.get("currency"),
                "market_value": record.get("market_value"),
                "research_memory_count": memory_count,
                "thesis_snapshot_connected": bool(thesis_snapshot),
                "thesis_snapshot_date": (thesis_snapshot or {}).get("source_date") if thesis_snapshot else None,
                "rag_document_count": rag_document_count,
                "rag_connected": rag_document_count > 0,
                "missing_fields": missing_fields,
                "message": (
                    "시스템 연결 완료"
                    if connected
                    else f"보강 필요: {', '.join(missing_fields)}"
                ),
            }
        )

    connected_count = sum(1 for item in items if item["connected"])
    verified_count = sum(1 for item in items if item["verified"])
    rag_connected_count = sum(1 for item in items if item["rag_connected"])
    thesis_snapshot_count = sum(1 for item in items if item["thesis_snapshot_connected"])
    return {
        "status": "success",
        "module": "portfolio_connectivity",
        "portfolio_count": len(response.portfolios),
        "holding_count": len(items),
        "verified_count": verified_count,
        "connected_count": connected_count,
        "rag_connected_count": rag_connected_count,
        "thesis_snapshot_count": thesis_snapshot_count,
        "summary": (
            f"저장 포트폴리오 {len(response.portfolios)}개에서 고유 종목 {len(items)}개를 점검했습니다. "
            f"공식 티커 인증 {verified_count}/{len(items)}, RAG 검색 연결 {rag_connected_count}/{len(items)}, "
            f"투자 논거 스냅샷 {thesis_snapshot_count}/{len(items)}, 시스템 연결 {connected_count}/{len(items)}입니다."
        ),
        "items": items,
    }


@app.get(
    "/api/v1/portfolios/analysis-status",
    dependencies=[Depends(verify_user_token)],
)
def check_portfolio_analysis_status(
    settings: Settings = Depends(get_settings),
) -> dict:
    response = portfolio_store_response(settings)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    manifest_entries = read_manifest(vault_dir)
    by_ticker: dict[str, dict] = {}
    for portfolio in response.portfolios:
        for holding in portfolio.holdings:
            ticker = normalize_ticker(holding.ticker)
            if not ticker or ticker == "UNKNOWN":
                continue
            record = by_ticker.setdefault(
                ticker,
                {
                    "ticker": ticker,
                    "holding_name": holding.name,
                    "portfolios": [],
                    "market_value": holding.market_value,
                },
            )
            if portfolio.portfolio_name not in record["portfolios"]:
                record["portfolios"].append(portfolio.portfolio_name)
            if record.get("market_value") is None and holding.market_value is not None:
                record["market_value"] = holding.market_value

    required_modules = [
        ("team_report", "기준 리포트"),
        ("trade_setup", "매매 전략"),
        ("earnings_reaction", "실적 분석"),
        ("model_update_note", "모델 업데이트 노트"),
        ("checklist", "체크리스트"),
        ("recent_capture", "최근 정보 입력"),
    ]
    items = []
    for ticker, record in sorted(by_ticker.items()):
        verification = verify_ticker_symbol(ticker, settings)
        official_symbol = verification.official_symbol
        ticker_entries = [
            entry
            for entry in manifest_entries
            if entry.get("ticker") == official_symbol
            and is_verified_manifest_entry(entry, official_symbol)
        ]
        sorted_entries = sorted(
            ticker_entries,
            key=lambda entry: (
                entry.get("date", ""),
                report_file_sequence(entry.get("file_name", "")),
                entry.get("file_name", ""),
            ),
            reverse=True,
        )
        team_report = latest_manifest_entry(
            ticker_entries,
            "collaborative-team-report",
            "institutional-stock-breakdown",
        )
        trade_setup = latest_manifest_entry(ticker_entries, "smart-trade-setup")
        earnings_reaction = latest_manifest_entry(ticker_entries, "earnings-reaction")
        model_update_note = latest_manifest_entry(ticker_entries, "earnings-filing-note")
        checklist = latest_manifest_entry(ticker_entries, "research-checklist")
        recent_capture = latest_manifest_entry(ticker_entries, "research-capture")
        module_state = {
            "team_report": bool(team_report),
            "trade_setup": bool(trade_setup),
            "earnings_reaction": bool(earnings_reaction),
            "model_update_note": bool(model_update_note),
            "checklist": bool(checklist),
            "recent_capture": bool(recent_capture),
        }
        completed_count = sum(1 for value in module_state.values() if value)
        missing_labels = [
            label for key, label in required_modules if not module_state.get(key)
        ]
        if not verification.verified:
            next_action = "공식 티커 인증을 먼저 보강하세요."
        elif not team_report:
            next_action = "팀 리포트로 기준 투자 논거를 먼저 생성하세요."
        elif not trade_setup:
            next_action = "매매 전략에서 진입 구간, 손절, 목표가를 설계하세요."
        elif not earnings_reaction:
            next_action = "최근 실적 반응을 연결해 다음 실적 전 추적 항목을 정리하세요."
        elif not model_update_note:
            next_action = "보고 자동화에서 어닝 콜/공시 기반 모델 업데이트 노트를 작성하세요."
        elif not checklist:
            next_action = "16개 리서치 체크리스트로 투자 준비도를 수치화하세요."
        elif not recent_capture:
            next_action = "뉴스/리포트/메모를 정보 입력에 저장해 논거 변화를 추적하세요."
        else:
            next_action = "핵심 분석이 모두 연결되어 있습니다. 새 데이터 유입 시 갱신만 하면 됩니다."

        items.append(
            {
                "ticker": ticker,
                "official_symbol": official_symbol,
                "verified": verification.verified,
                "company_name": verification.company_name or record.get("holding_name") or ticker,
                "portfolios": record["portfolios"],
                "market_value": record.get("market_value"),
                "module_state": module_state,
                "completed_count": completed_count,
                "required_count": len(required_modules),
                "completion_rate": completed_count / len(required_modules),
                "missing_modules": missing_labels,
                "latest_report_date": sorted_entries[0].get("date") if sorted_entries else None,
                "latest_report_summary": sorted_entries[0].get("summary") if sorted_entries else None,
                "latest_files": [
                    {
                        "type": entry.get("type"),
                        "file_name": entry.get("file_name"),
                        "date": entry.get("date"),
                        "summary": entry.get("summary"),
                    }
                    for entry in sorted_entries[:3]
                ],
                "next_action": next_action,
            }
        )

    average_completion = (
        sum(item["completion_rate"] for item in items) / len(items)
        if items
        else 0
    )
    ready_count = sum(1 for item in items if item["completion_rate"] >= 1)
    needs_team_report = sum(
        1 for item in items if not item["module_state"]["team_report"]
    )
    return {
        "status": "success",
        "module": "portfolio_analysis_status",
        "portfolio_count": len(response.portfolios),
        "holding_count": len(items),
        "ready_count": ready_count,
        "average_completion": average_completion,
        "needs_team_report_count": needs_team_report,
        "summary": (
            f"저장 포트폴리오 {len(response.portfolios)}개, 고유 보유 종목 {len(items)}개 기준 "
            f"분석 준비 완료 {ready_count}개, 평균 완료율 {average_completion:.0%}입니다."
        ),
        "items": sorted(
            items,
            key=lambda item: (item["completion_rate"], item.get("market_value") or 0),
        ),
    }


@app.get(
    "/api/v1/portfolios/team-report-queue",
    dependencies=[Depends(verify_user_token)],
)
def get_portfolio_team_report_queue(
    settings: Settings = Depends(get_settings),
) -> dict:
    response = portfolio_store_response(settings)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    manifest_entries = read_manifest(vault_dir)
    by_ticker: dict[str, dict] = {}
    for portfolio in response.portfolios:
        for holding in portfolio.holdings:
            ticker = normalize_ticker(holding.ticker)
            if not ticker or ticker == "UNKNOWN" or ticker == "CASH":
                continue
            record = by_ticker.setdefault(
                ticker,
                {
                    "ticker": ticker,
                    "holding_name": holding.name,
                    "portfolios": [],
                    "market_value": holding.market_value or 0,
                    "weight": holding.weight,
                },
            )
            if portfolio.portfolio_name not in record["portfolios"]:
                record["portfolios"].append(portfolio.portfolio_name)
            if (holding.market_value or 0) > (record.get("market_value") or 0):
                record["market_value"] = holding.market_value or 0
                record["weight"] = holding.weight

    queue = []
    already_ready = []
    blocked = []
    for ticker, record in by_ticker.items():
        verification = verify_ticker_symbol_local_cached(ticker, settings)
        if not verification.verified:
            blocked.append(
                {
                    "ticker": ticker,
                    "reason": "공식 티커 인증 실패",
                    "message": verification.message,
                    "portfolios": record["portfolios"],
                }
            )
            continue
        official_symbol = verification.official_symbol
        profile = OFFICIAL_TICKER_REGISTRY.get(official_symbol) or read_dynamic_ticker_registry(
            settings
        ).get(official_symbol) or {}
        ticker_entries = [
            entry
            for entry in manifest_entries
            if entry.get("ticker") == official_symbol
            and is_verified_manifest_entry(entry, official_symbol)
        ]
        team_report = latest_manifest_entry(
            ticker_entries,
            "collaborative-team-report",
            "institutional-stock-breakdown",
        )
        item = {
            "ticker": ticker,
            "official_symbol": official_symbol,
            "company_name": verification.company_name or record.get("holding_name") or ticker,
            "portfolios": record["portfolios"],
            "market_value": record.get("market_value") or 0,
            "weight": record.get("weight"),
            "sector": profile.get("sector") or "미분류",
            "analysis_focus": profile.get("analysis_focus")
            or "사업 모델, 매출 성장, 마진, 밸류에이션, 주요 리스크",
            "investment_period": "3년",
            "region": "한국" if verification.country == "KR" else "US",
            "style": "균형형",
            "watch_kpis": profile.get("watch_kpis", []),
            "business_context": profile.get("business_context") or "",
        }
        if team_report:
            already_ready.append(
                {
                    **item,
                    "latest_team_report_file": team_report.get("file_name"),
                    "latest_team_report_date": team_report.get("date"),
                    "latest_team_report_summary": team_report.get("summary"),
                }
            )
        else:
            queue.append(
                {
                    **item,
                    "reason": "공식 인증 기준 리포트가 아직 없습니다.",
                    "recommended_action": (
                        f"{official_symbol} 팀 리포트를 먼저 실행해 기준 투자 논거를 생성하세요."
                    ),
                }
            )

    queue.sort(key=lambda item: item.get("market_value") or 0, reverse=True)
    already_ready.sort(key=lambda item: item.get("market_value") or 0, reverse=True)
    return {
        "status": "success",
        "module": "portfolio_team_report_queue",
        "portfolio_count": len(response.portfolios),
        "queue_count": len(queue),
        "ready_count": len(already_ready),
        "blocked_count": len(blocked),
        "summary": (
            f"고유 보유 종목 {len(by_ticker)}개 중 기준 리포트 생성 필요 {len(queue)}개, "
            f"이미 준비 {len(already_ready)}개, 인증 보류 {len(blocked)}개입니다."
        ),
        "queue": queue,
        "already_ready": already_ready,
        "blocked": blocked,
    }


def target_price_currency(symbol: str | None, unit: str | None, holding_currency: str) -> str:
    unit_text = str(unit or "").upper()
    symbol_text = str(symbol or "")
    if "$" in symbol_text or "USD" in unit_text or "달러" in unit_text:
        return "USD"
    if "₩" in symbol_text or "KRW" in unit_text or "원" in unit_text:
        return "KRW"
    normalized_currency = (holding_currency or "KRW").upper()
    return normalized_currency if normalized_currency in {"USD", "KRW"} else "KRW"


def is_plausible_target_price(value: float, currency: str) -> bool:
    if value <= 0:
        return False
    if currency == "KRW":
        return 100 <= value <= 5_000_000
    if currency == "USD":
        return 0.01 <= value <= 5_000
    return True


def target_price_numeric_value(raw_value: object, unit: str | None) -> float | None:
    value = parse_float_or_none(raw_value)
    if value is None:
        return None
    unit_text = str(unit or "").upper()
    if "만원" in str(unit or ""):
        return value * 10000
    if unit_text in {"BN", "B"}:
        return None
    return value


def is_probable_year_or_metadata_number(
    raw_value: object,
    symbol: str | None,
    unit: str | None,
    context: str,
    ticker_context: str | None = None,
) -> bool:
    raw_text = str(raw_value or "").strip().replace(",", "")
    unit_text = str(unit or "").strip()
    symbol_text = str(symbol or "").strip()
    context_text = context.lower()
    metadata_blockers = [
        "mime",
        "bytes",
        "파일명",
        "파일 이름",
        "파일 크기",
        "크기:",
        "pdf 링크",
        "원문 링크",
        "nid=",
        "page=",
        "종목코드",
        "발행일",
        "저장 범위",
        "분류 근거",
        "as of",
        "quarter 20",
        "fy20",
        "fiscal",
        "financial results",
    ]
    if any(blocker in context_text for blocker in metadata_blockers):
        return True
    if not unit_text and not symbol_text and raw_text.isdigit() and len(raw_text) == 4:
        year_value = int(raw_text)
        if 1900 <= year_value <= 2100:
            return True
    normalized_ticker_context = normalize_ticker(ticker_context or "")
    if raw_text.isdigit() and fullmatch(r"\d{6}", normalized_ticker_context):
        try:
            if int(raw_text) == int(normalized_ticker_context):
                return True
        except ValueError:
            pass
    return False


def filter_target_price_outliers(values: list[float]) -> list[float]:
    if len(values) < 4:
        return values
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    median = (
        sorted_values[midpoint]
        if len(sorted_values) % 2
        else (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2
    )
    if median <= 0:
        return values
    filtered = [value for value in values if median * 0.35 <= value <= median * 2.8]
    return filtered if len(filtered) >= 2 else values


def target_price_result(
    value: float,
    currency: str,
    memory_file,
    source_label: str,
    confidence: float,
) -> dict | None:
    if not is_plausible_target_price(value, currency):
        return None
    return {
        "target_price": round(value, 4),
        "target_price_currency": currency,
        "target_price_source_file": memory_file.file_name,
        "target_price_source_type": source_label,
        "target_price_confidence": round(confidence, 2),
    }


def parse_structured_trade_target_from_json(memory_file, holding_currency: str) -> dict | None:
    json_path = Path(memory_file.absolute_path).with_suffix(".json")
    if not json_path.exists():
        return None
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8", errors="ignore"))
    except (OSError, json.JSONDecodeError):
        return None
    targets = payload.get("targets")
    if not isinstance(targets, list):
        return None
    for target in targets:
        if not isinstance(target, dict):
            continue
        value = parse_float_or_none(target.get("price"))
        if value is None:
            continue
        result = target_price_result(
            value=value,
            currency=(holding_currency or "KRW").upper(),
            memory_file=memory_file,
            source_label="smart-trade-setup:구조화 목표가",
            confidence=0.9,
        )
        if result:
            return result
    return None


def parse_explicit_analyst_target_from_text(
    text: str,
    memory_file,
    holding_currency: str,
) -> dict | None:
    patterns = [
        r"(목표\s*주가|목표\s*가격|목표가|target\s*price|TP)\s*(?:를|은|는|로|까지)?\s*[:：]?\s*(\$|₩)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(만원|원|달러|USD|KRW)?",
        r"(이에\s*목표\s*주가)\s*(\$|₩)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(만원|원|달러|USD|KRW)?",
    ]
    for pattern in patterns:
        for match in finditer(pattern, text, flags=0):
            prefix = text[max(0, match.start() - 12):match.start()]
            if "직전" in prefix or "기존" in prefix:
                continue
            label, symbol, raw_value, unit = match.groups()
            value = target_price_numeric_value(raw_value, unit)
            if value is None:
                continue
            currency = target_price_currency(symbol, unit, holding_currency)
            result = target_price_result(
                value=value,
                currency=currency,
                memory_file=memory_file,
                source_label=f"{memory_file.report_type}:명시 목표주가",
                confidence=0.85 if "target" in label.lower() or "목표" in label else 0.8,
            )
            if result:
                return result
    return None


def parse_tactical_trade_target_from_text(
    text: str,
    memory_file,
    holding_currency: str,
) -> dict | None:
    pattern = r"(?:1차|2차|3차)\s*목표가?\s*[:：]?\s*(\$|₩)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(만원|원|달러|USD|KRW)?"
    for symbol, raw_value, unit in findall(pattern, text, flags=0):
        value = target_price_numeric_value(raw_value, unit)
        if value is None:
            continue
        currency = target_price_currency(symbol, unit, holding_currency)
        result = target_price_result(
            value=value,
            currency=currency,
            memory_file=memory_file,
            source_label=f"{memory_file.report_type}:전술 목표가",
            confidence=0.75,
        )
        if result:
            return result
    return None


def target_price_context_source_type(text: str) -> tuple[str, float]:
    normalized = text.lower()
    if any(keyword in text for keyword in ["컨센서스", "평균 목표", "증권사 평균", "시장 평균"]):
        return "증권사 컨센서스 목표주가", 0.95
    if any(keyword in text for keyword in ["증권사", "투자의견", "리포트", "목표주가", "목표가"]):
        return "증권사 리포트 목표주가", 0.88
    if "target price" in normalized or "analyst" in normalized:
        return "애널리스트 목표주가", 0.86
    return "저장 리포트 목표주가", 0.78


def extract_target_price_observations_from_text(
    text: str,
    memory_file: ResearchMemoryFile,
    holding_currency: str,
    ticker_context: str | None = None,
) -> list[dict]:
    patterns = [
        r"(컨센서스|평균\s*목표\s*주가|증권사\s*평균|목표\s*주가|목표\s*가격|목표가|target\s*price|TP)[^。\n\r]{0,45}?(\$|₩)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(만원|원|달러|USD|KRW)?",
        r"(\$|₩)?\s*([0-9][0-9,]*(?:\.\d+)?)\s*(만원|원|달러|USD|KRW)?\s*(?:으로|까지|로)?\s*(목표\s*주가|목표가|target\s*price)",
    ]
    observations: list[dict] = []
    seen: set[tuple[str, float, str]] = set()
    for pattern_index, pattern in enumerate(patterns):
        for match in finditer(pattern, text, flags=IGNORECASE):
            if pattern_index == 0:
                _label, symbol, raw_value, unit = match.groups()
            else:
                symbol, raw_value, unit, _label = match.groups()
            value = target_price_numeric_value(raw_value, unit)
            currency = target_price_currency(symbol, unit, holding_currency)
            context = text[max(0, match.start() - 90): min(len(text), match.end() + 90)]
            if (
                value is None
                or not is_plausible_target_price(value, currency)
                or is_probable_year_or_metadata_number(
                    raw_value,
                    symbol,
                    unit,
                    context,
                    ticker_context=ticker_context,
                )
            ):
                continue
            if any(blocker in context for blocker in ["현재가", "종가", "시가총액", "매출", "영업이익"]):
                if "목표" not in context and "target" not in context.lower():
                    continue
            key = (memory_file.file_name, round(value, 4), currency)
            if key in seen:
                continue
            seen.add(key)
            source_type, confidence = target_price_context_source_type(context)
            observations.append(
                {
                    "target_price": round(value, 4),
                    "target_price_currency": currency,
                    "source_file": memory_file.file_name,
                    "source_type": source_type,
                    "source_report_type": memory_file.report_type,
                    "source_date": infer_report_date_from_file(memory_file.file_name),
                    "modified_at": memory_file.modified_at,
                    "confidence": confidence,
                    "context": " ".join(context.split())[:240],
                }
            )
    return observations


def build_target_price_consensus_from_memory(
    ticker: str,
    vault_dir: Path,
    holding_currency: str,
    *,
    limit_files: int = 40,
) -> dict | None:
    normalized_ticker = normalize_ticker(ticker)
    observations: list[dict] = []
    allowed_report_types = {"research-capture", "thesis-impact-review", "dossier-synthesis"}
    for memory_file in list_research_memory_files(normalized_ticker, vault_dir)[:limit_files]:
        if memory_file.report_type not in allowed_report_types:
            continue
        try:
            text = Path(memory_file.absolute_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        observations.extend(
            extract_target_price_observations_from_text(
                text,
                memory_file,
                holding_currency,
                ticker_context=normalized_ticker,
            )
        )
    observations = [
        item
        for item in observations
        if item.get("target_price_currency") == (holding_currency or "KRW").upper()
    ]
    if not observations:
        return None
    observations.sort(
        key=lambda item: (
            item.get("source_date") or "",
            item.get("confidence") or 0,
            item.get("modified_at") or "",
        ),
        reverse=True,
    )
    recent = observations[:12]
    values = [float(item["target_price"]) for item in recent if item.get("target_price")]
    if not values:
        return None
    values = filter_target_price_outliers(values)
    sorted_values = sorted(values)
    midpoint = len(sorted_values) // 2
    median = (
        sorted_values[midpoint]
        if len(sorted_values) % 2
        else (sorted_values[midpoint - 1] + sorted_values[midpoint]) / 2
    )
    consensus_value = sum(values) / len(values)
    return {
        "target_price": round(consensus_value, 4),
        "target_price_currency": (holding_currency or "KRW").upper(),
        "target_price_median": round(median, 4),
        "target_price_high": round(max(values), 4),
        "target_price_low": round(min(values), 4),
        "source_count": len(recent),
        "observation_count": len(observations),
        "source_type": "저장 증권사 리포트 컨센서스",
        "confidence": round(sum(float(item.get("confidence") or 0.75) for item in recent) / len(recent), 2),
        "latest_source_file": recent[0].get("source_file"),
        "latest_source_date": recent[0].get("source_date"),
        "latest_context": recent[0].get("context"),
        "observations": recent,
    }


def parse_latest_target_price_from_memory(
    ticker: str,
    vault_dir: Path,
    holding_currency: str,
) -> dict | None:
    """
    최근 저장 리포트에서 목표가/Target Price 숫자를 찾아 지능형 테이블 계산에 사용합니다.
    애매한 체크리스트 주입 문구는 제외하고, 명시적 증권사 목표주가를 우선한 뒤
    구조화된 스마트 매매전략 목표가를 보조값으로 사용합니다.
    """
    normalized_ticker = normalize_ticker(ticker)
    memory_files = list_research_memory_files(normalized_ticker, vault_dir)[:30]
    explicit_source_types = {"research-capture", "thesis-impact-review"}
    trade_source_types = {"smart-trade-setup"}

    for memory_file in memory_files:
        if memory_file.report_type not in explicit_source_types:
            continue
        try:
            text = Path(memory_file.absolute_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        result = parse_explicit_analyst_target_from_text(text, memory_file, holding_currency)
        if result:
            return result

    for memory_file in memory_files:
        if memory_file.report_type not in trade_source_types:
            continue
        result = parse_structured_trade_target_from_json(memory_file, holding_currency)
        if result:
            return result

    for memory_file in memory_files:
        if memory_file.report_type not in trade_source_types:
            continue
        try:
            text = Path(memory_file.absolute_path).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        result = parse_tactical_trade_target_from_text(text, memory_file, holding_currency)
        if result:
            return result
    return None


def fetch_52_week_high_for_holding(
    ticker: str,
    settings: Settings,
) -> dict:
    code = normalize_kr_stock_code(ticker)
    if not is_naver_domestic_stock_code(code):
        try:
            code = ensure_verified_ticker(ticker, settings)
        except HTTPException as exc:
            return {
                "week52_high": None,
                "week52_high_as_of": None,
                "week52_high_source": None,
                "week52_status": f"티커 인증 실패: {exc.detail}",
            }
    if not is_naver_domestic_stock_code(code):
        return {
            "week52_high": None,
            "week52_high_as_of": None,
            "week52_high_source": None,
            "week52_status": "네이버 국내 종목코드가 아니라 52주 최고가 자동 계산을 보류했습니다.",
        }
    try:
        _, rows = fetch_naver_domestic_price_history(code, settings, page_size=260)
    except Exception as exc:
        return {
            "week52_high": None,
            "week52_high_as_of": None,
            "week52_high_source": None,
            "week52_status": f"네이버 52주 데이터 조회 실패: {exc}",
        }
    if not rows:
        return {
            "week52_high": None,
            "week52_high_as_of": None,
            "week52_high_source": None,
            "week52_status": "52주 가격 데이터가 없습니다.",
        }
    high_row = max(rows, key=lambda item: item.get("high") or item.get("close") or 0)
    high_value = parse_float_or_none(high_row.get("high")) or parse_float_or_none(high_row.get("close"))
    return {
        "week52_high": round(high_value, 4) if high_value else None,
        "week52_high_as_of": high_row.get("date"),
        "week52_high_source": "naver_finance_mobile_price_api",
        "week52_status": "계산 완료" if high_value else "52주 최고가 계산 실패",
    }


PORTFOLIO_PERFORMANCE_PERIODS = [
    ("1w", "최근 1주일", 7),
    ("1m", "최근 1개월", 30),
    ("6m", "최근 6개월", 182),
    ("1y", "최근 1년", 365),
]


def portfolio_history_rows_for_ticker(
    ticker: str,
    settings: Settings,
    page_size: int = 280,
) -> tuple[str, list[dict]]:
    code = normalize_kr_stock_code(ticker)
    if not is_naver_domestic_stock_code(code):
        try:
            code = ensure_verified_ticker(ticker, settings)
        except HTTPException as exc:
            raise ValueError(f"티커 인증 실패: {exc.detail}") from exc
    if not is_naver_domestic_stock_code(code):
        raise ValueError("국내 가격 히스토리 지원 대상이 아닙니다.")
    cache_key = f"{code}:{page_size}"
    if cache_key not in PORTFOLIO_HISTORY_CACHE:
        _, rows = fetch_naver_domestic_price_history(code, settings, page_size=page_size)
        PORTFOLIO_HISTORY_CACHE[cache_key] = rows
    return code, PORTFOLIO_HISTORY_CACHE[cache_key]


def historical_close_on_or_before(rows: list[dict], target_date: date) -> tuple[float | None, str | None]:
    target = target_date.isoformat()
    for row in reversed(rows):
        row_date = str(row.get("date") or "")
        close = parse_float_or_none(row.get("close"))
        if row_date and row_date <= target and close is not None and close > 0:
            return close, row_date
    return None, None


def portfolio_holding_current_value(
    holding: PortfolioHolding,
    current_price: float | None,
    *,
    prefer_market_value: bool = True,
) -> float | None:
    if prefer_market_value and holding.market_value is not None and holding.market_value > 0:
        return holding.market_value
    if holding.quantity is None or holding.quantity <= 0 or current_price is None:
        return None
    return holding.quantity * current_price * infer_holding_fx_rate(holding)


def build_portfolio_performance(portfolio_name: str, settings: Settings) -> dict:
    store = read_portfolio_store(settings)
    key = portfolio_store_key(portfolio_name)
    payload = store.get("portfolios", {}).get(key)
    if not payload:
        raise HTTPException(status_code=404, detail=f"{portfolio_name} 포트폴리오를 찾을 수 없습니다.")

    portfolio = sort_and_weight_portfolio(
        SavedPortfolio.model_validate(payload),
        settings,
        refresh_prices=False,
    )
    as_of = current_storage_date()
    period_accumulators = {
        key: {
            "key": key,
            "label": label,
            "days": days,
            "target_date": None,
            "price_as_of": None,
            "target_dates": [],
            "price_as_of_dates": [],
            "current_value": 0.0,
            "base_value": 0.0,
            "net_profit": 0.0,
            "return_rate": None,
            "included_count": 0,
            "covered_market_value": 0.0,
            "top_gainers": [],
            "top_losers": [],
        }
        for key, label, days in PORTFOLIO_PERFORMANCE_PERIODS
    }
    holding_rows: list[dict] = []
    skipped: list[dict] = []
    current_portfolio_value = 0.0
    current_cost_basis = 0.0
    current_unrealized_gain = 0.0
    price_as_of_dates: list[str] = []

    for holding in portfolio.holdings:
        ticker = normalize_ticker(holding.ticker)
        if not ticker:
            continue
        current_value_for_total = holding.market_value or 0.0
        current_portfolio_value += current_value_for_total
        current_cost_basis += holding.cost_basis or 0.0
        current_unrealized_gain += holding.unrealized_gain or 0.0

        if ticker == "CASH":
            current_value = current_value_for_total
            for period in period_accumulators.values():
                period["current_value"] += current_value
                period["base_value"] += current_value
                period["included_count"] += 1
                period["covered_market_value"] += current_value
            holding_rows.append({
                "ticker": ticker,
                "name": holding.name or "현금",
                "currency": holding.currency,
                "current_value": round(current_value, 2),
                "status": "현금은 기간 수익률 0%로 반영했습니다.",
                "periods": {
                    key: {
                        "base_price": None,
                        "base_date": period["target_date"],
                        "current_price": None,
                        "current_value": round(current_value, 2),
                        "base_value": round(current_value, 2),
                        "net_profit": 0.0,
                        "return_rate": 0.0,
                    }
                    for key, period in period_accumulators.items()
                },
            })
            continue

        try:
            official_symbol, history_rows = portfolio_history_rows_for_ticker(ticker, settings)
        except Exception as exc:
            skipped.append({
                "ticker": ticker,
                "name": holding.name,
                "market_value": round(current_value_for_total, 2) if current_value_for_total else None,
                "reason": str(exc),
            })
            continue

        latest_history_close = parse_float_or_none(history_rows[-1].get("close")) if history_rows else None
        latest_history_date_text = str(history_rows[-1].get("date") or "") if history_rows else ""
        try:
            latest_history_date = date.fromisoformat(latest_history_date_text)
        except ValueError:
            latest_history_date = as_of
        if latest_history_date_text:
            price_as_of_dates.append(latest_history_date_text)
        current_price = latest_history_close or holding.current_price
        current_value = portfolio_holding_current_value(
            holding,
            current_price,
            prefer_market_value=False,
        )
        if current_value is None or current_value <= 0 or holding.quantity is None or holding.quantity <= 0:
            skipped.append({
                "ticker": ticker,
                "name": holding.name,
                "market_value": round(current_value_for_total, 2) if current_value_for_total else None,
                "reason": "수량 또는 현재 평가금액이 없어 기간 수익을 계산하지 못했습니다.",
            })
            continue

        fx_rate = infer_holding_fx_rate(holding)
        row_periods: dict[str, dict] = {}
        for period_key, period_label, days in PORTFOLIO_PERFORMANCE_PERIODS:
            target_date = latest_history_date - timedelta(days=days)
            base_price, base_date = historical_close_on_or_before(history_rows, target_date)
            if base_price is None:
                row_periods[period_key] = {
                    "base_price": None,
                    "base_date": None,
                    "current_price": round(current_price, 4) if current_price else None,
                    "current_value": round(current_value, 2),
                    "base_value": None,
                    "net_profit": None,
                    "return_rate": None,
                    "status": "해당 기간의 과거 종가가 부족합니다.",
                }
                continue
            base_value = holding.quantity * base_price * fx_rate
            net_profit = current_value - base_value
            return_rate = net_profit / base_value if base_value > 0 else None
            period = period_accumulators[period_key]
            period["target_dates"].append(target_date.isoformat())
            period["price_as_of_dates"].append(latest_history_date_text)
            period["current_value"] += current_value
            period["base_value"] += base_value
            period["net_profit"] += net_profit
            period["included_count"] += 1
            period["covered_market_value"] += current_value
            contribution = {
                "ticker": ticker,
                "name": holding.name,
                "net_profit": round(net_profit, 2),
                "return_rate": round(return_rate, 4) if return_rate is not None else None,
                "current_value": round(current_value, 2),
                "base_value": round(base_value, 2),
            }
            period["top_gainers"].append(contribution)
            period["top_losers"].append(contribution)
            row_periods[period_key] = {
                "label": period_label,
                "base_price": round(base_price, 4),
                "base_date": base_date,
                "current_price": round(current_price, 4) if current_price else None,
                "current_value": round(current_value, 2),
                "base_value": round(base_value, 2),
                "net_profit": round(net_profit, 2),
                "return_rate": round(return_rate, 4) if return_rate is not None else None,
            }

        holding_rows.append({
            "ticker": ticker,
            "official_symbol": official_symbol,
            "name": holding.name,
            "currency": holding.currency,
            "quantity": holding.quantity,
            "current_price": round(current_price, 4) if current_price else None,
            "current_value": round(current_value, 2),
            "price_source": "naver_finance_mobile_price_api",
            "periods": row_periods,
        })

    periods = []
    for key, label, days in PORTFOLIO_PERFORMANCE_PERIODS:
        period = period_accumulators[key]
        base_value = period["base_value"]
        return_rate = period["net_profit"] / base_value if base_value > 0 else None
        period["current_value"] = round(period["current_value"], 2)
        period["base_value"] = round(period["base_value"], 2)
        period["net_profit"] = round(period["net_profit"], 2)
        period["return_rate"] = round(return_rate, 4) if return_rate is not None else None
        target_dates = sorted(date_text for date_text in period.pop("target_dates", []) if date_text)
        price_as_of_period_dates = sorted(date_text for date_text in period.pop("price_as_of_dates", []) if date_text)
        period["target_date"] = target_dates[-1] if target_dates else None
        period["price_as_of"] = price_as_of_period_dates[-1] if price_as_of_period_dates else None
        period["coverage_rate"] = (
            round(period["covered_market_value"] / current_portfolio_value, 4)
            if current_portfolio_value > 0
            else None
        )
        period["top_gainers"] = sorted(
            period["top_gainers"],
            key=lambda item: item.get("net_profit") or 0,
            reverse=True,
        )[:3]
        period["top_losers"] = sorted(
            period["top_losers"],
            key=lambda item: item.get("net_profit") or 0,
        )[:3]
        periods.append(period)

    current_unrealized_return = (
        current_unrealized_gain / current_cost_basis
        if current_cost_basis > 0
        else None
    )
    return {
        "status": "success",
        "module": "portfolio_performance_comparison",
        "portfolio_name": portfolio.portfolio_name,
        "as_of": current_storage_timestamp(),
        "price_data_as_of": sorted(price_as_of_dates)[-1] if price_as_of_dates else None,
        "method": "현재 저장 수량과 가격 히스토리의 최신 종가를 기준으로, 기간별 과거 종가 대비 평가금액 차이를 계산했습니다.",
        "portfolio_value": round(current_portfolio_value or portfolio.portfolio_value or 0, 2),
        "current_unrealized_gain": round(current_unrealized_gain, 2),
        "current_unrealized_return": round(current_unrealized_return, 4)
        if current_unrealized_return is not None
        else None,
        "periods": periods,
        "holdings": holding_rows,
        "skipped_holdings": skipped,
        "coverage_note": "국내 가격 히스토리가 확인된 종목과 현금만 기간 수익률에 반영했습니다. 해외 종목은 현재 저장 손익에는 포함되지만 기간별 가격 비교에서는 제외될 수 있습니다.",
    }


def build_portfolio_intelligent_table(portfolio_name: str, settings: Settings) -> dict:
    store = read_portfolio_store(settings)
    key = portfolio_store_key(portfolio_name)
    payload = store.get("portfolios", {}).get(key)
    if not payload:
        raise HTTPException(status_code=404, detail=f"{portfolio_name} 포트폴리오를 찾을 수 없습니다.")

    portfolio = sort_and_weight_portfolio(
        SavedPortfolio.model_validate(payload),
        settings,
        refresh_prices=True,
    )
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    portfolio_tickers = [
        normalize_ticker(holding.ticker)
        for holding in portfolio.holdings
        if normalize_ticker(holding.ticker) and normalize_ticker(holding.ticker) != "CASH"
    ]
    rag_document_counts = count_research_memory_documents_by_ticker(vault_dir, portfolio_tickers)
    manifest_entries = read_manifest(vault_dir)
    rows: list[dict] = []
    warnings: list[str] = []
    for holding in portfolio.holdings:
        ticker = normalize_ticker(holding.ticker)
        if not ticker or ticker == "CASH":
            continue
        profile = official_ticker_profile(ticker, settings)
        verification = verify_ticker_symbol(ticker, settings)
        official_symbol = normalize_ticker(verification.official_symbol or ticker)
        company_name = (
            verification.company_name
            or profile.get("company_name")
            or holding.name
            or ticker
        )
        week52 = fetch_52_week_high_for_holding(ticker, settings)
        week52_high = week52.get("week52_high")
        current_price = holding.current_price
        week52_proximity = (
            current_price / week52_high
            if current_price is not None and week52_high and week52_high > 0
            else None
        )
        week52_gap = (
            (current_price - week52_high) / week52_high
            if current_price is not None and week52_high and week52_high > 0
            else None
        )
        target = parse_latest_target_price_from_memory(ticker, vault_dir, holding.currency)
        target_price = target.get("target_price") if target else None
        target_currency = target.get("target_price_currency") if target else None
        same_target_currency = target_currency == (holding.currency or "KRW").upper()
        target_proximity = (
            current_price / target_price
            if same_target_currency
            and current_price is not None
            and target_price
            and target_price > 0
            else None
        )
        target_upside = (
            (target_price - current_price) / current_price
            if same_target_currency
            and current_price is not None
            and current_price > 0
            and target_price
            else None
        )
        if week52_high is None:
            warnings.append(f"{company_name}: 52주 최고가 {week52.get('week52_status')}")
        if target_price is None:
            warnings.append(f"{company_name}: 저장 리포트에서 목표주가를 찾지 못했습니다.")
        memory_count = sum(
            1
            for entry in manifest_entries
            if normalize_ticker(str(entry.get("ticker") or "")) in {ticker, official_symbol}
        )
        try:
            thesis_snapshot = read_ticker_thesis_snapshot(vault_dir, official_symbol)
        except Exception:
            thesis_snapshot = None
        rag_document_count = rag_document_counts.get(official_symbol) or rag_document_counts.get(ticker) or 0
        readiness_score = 0
        readiness_score += 20 if verification.verified else 0
        readiness_score += 20 if current_price is not None else 0
        readiness_score += 20 if memory_count > 0 else 0
        readiness_score += 20 if thesis_snapshot else 0
        readiness_score += 10 if target_price is not None else 0
        readiness_score += 10 if week52_high is not None else 0
        if not verification.verified:
            next_action = "공식 티커 인증을 먼저 보강"
        elif current_price is None:
            next_action = "현재가 자동 입력 상태 확인"
        elif not thesis_snapshot:
            next_action = "팀 리포트로 기준 투자 논거 생성"
        elif memory_count < 3:
            next_action = "정보입력에 뉴스·리포트 추가 저장"
        elif target_price is None:
            next_action = "매매전략에서 목표가·손절가 보강"
        elif week52_high is None:
            next_action = "차트분석으로 52주 위치 확인"
        elif target_upside is not None and target_upside <= 0.05:
            next_action = "목표가 근접: 일부 이익실현 또는 목표 재점검"
        elif week52_proximity is not None and week52_proximity >= 0.95:
            next_action = "52주 고점권: 추격매수보다 변동성 확인"
        else:
            next_action = "새 자료 유입 시 논거 변화만 갱신"
        rows.append(
            {
                "ticker": ticker,
                "official_symbol": verification.official_symbol,
                "company_name": company_name,
                "verified": verification.verified,
                "country": verification.country or profile.get("country"),
                "exchange": verification.exchange,
                "sector": profile.get("sector") or holding.sector or "미분류",
                "currency": (holding.currency or "KRW").upper(),
                "quantity": holding.quantity,
                "average_cost": holding.average_cost,
                "current_price": current_price,
                "market_value": holding.market_value,
                "cost_basis": holding.cost_basis,
                "unrealized_gain": holding.unrealized_gain,
                "unrealized_return": holding.unrealized_return,
                "weight": holding.weight,
                "price_source": holding.price_source,
                "week52_high": week52_high,
                "week52_high_as_of": week52.get("week52_high_as_of"),
                "week52_high_source": week52.get("week52_high_source"),
                "week52_high_proximity": round(week52_proximity, 4)
                if week52_proximity is not None
                else None,
                "week52_high_gap": round(week52_gap, 4)
                if week52_gap is not None
                else None,
                "week52_status": week52.get("week52_status"),
                "target_price": target_price,
                "target_price_currency": target_currency,
                "target_price_source_file": target.get("target_price_source_file") if target else None,
                "target_price_source_type": target.get("target_price_source_type") if target else None,
                "target_price_proximity": round(target_proximity, 4)
                if target_proximity is not None
                else None,
                "target_upside": round(target_upside, 4) if target_upside is not None else None,
                "target_status": (
                    "계산 완료"
                    if target_proximity is not None
                    else "목표주가 미등록"
                    if target_price is None
                    else "목표주가 통화가 현재가 통화와 달라 근접도 계산 보류"
                ),
                "research_memory_count": memory_count,
                "rag_document_count": rag_document_count,
                "rag_connected": rag_document_count > 0,
                "thesis_snapshot_connected": bool(thesis_snapshot),
                "thesis_snapshot_date": (thesis_snapshot or {}).get("source_date") if thesis_snapshot else None,
                "thesis_summary": (thesis_snapshot or {}).get("thesis_summary") if thesis_snapshot else "",
                "data_readiness_score": round(readiness_score / 100, 4),
                "next_action": next_action,
            }
        )

    rows.sort(key=lambda item: item.get("market_value") or 0, reverse=True)
    top_market_value = rows[:8]
    top_return = sorted(
        rows,
        key=lambda item: item.get("unrealized_return")
        if item.get("unrealized_return") is not None
        else -999,
        reverse=True,
    )[:8]
    return {
        "status": "success",
        "module": "portfolio_intelligent_table",
        "portfolio_name": portfolio.portfolio_name,
        "as_of": current_storage_timestamp(),
        "portfolio_value": portfolio.portfolio_value,
        "holding_count": len(rows),
        "summary": (
            f"{portfolio.portfolio_name} 포트폴리오 {len(rows)}개 종목에 대해 "
            "현재가, 손익, 52주 최고가 근접도, 목표주가 근접도, RAG/투자 논거 준비도를 서버에서 계산했습니다."
        ),
        "warnings": warnings[:20],
        "holdings": rows,
        "charts": {
            "market_value_top": top_market_value,
            "return_top": top_return,
        },
    }


def target_consensus_universe(
    settings: Settings,
    portfolio_name: str | None,
    include_interests: bool,
) -> list[dict]:
    store = read_portfolio_store(settings)
    portfolios_payload = store.get("portfolios", {})
    selected_payloads: list[dict] = []
    if portfolio_name and portfolio_name != "__all__":
        payload = portfolios_payload.get(portfolio_store_key(portfolio_name))
        if payload:
            selected_payloads.append(payload)
    else:
        selected_payloads = [
            payload for payload in portfolios_payload.values() if isinstance(payload, dict)
        ]

    by_ticker: dict[str, dict] = {}
    for payload in selected_payloads:
        try:
            portfolio = sort_and_weight_portfolio(
                SavedPortfolio.model_validate(payload),
                settings,
                refresh_prices=False,
            )
        except Exception:
            continue
        for holding in portfolio.holdings:
            ticker = normalize_ticker(holding.ticker)
            if not ticker or ticker == "CASH":
                continue
            try:
                verification = verify_ticker_symbol(ticker, settings)
                official_symbol = normalize_ticker(verification.official_symbol or ticker)
            except HTTPException:
                verification = None
                official_symbol = ticker
            profile = official_ticker_profile(official_symbol, settings)
            currency = (holding.currency or ("KRW" if profile.get("country") == "KR" else "USD")).upper()
            row = by_ticker.setdefault(
                official_symbol,
                {
                    "ticker": official_symbol,
                    "company_name": (
                        (verification.company_name if verification else None)
                        or profile.get("company_name")
                        or holding.name
                        or official_symbol
                    ),
                    "currency": currency,
                    "sources": [],
                    "portfolio_names": [],
                    "interest": False,
                    "market_value": 0,
                    "quantity": 0,
                    "current_price": None,
                    "price_source": None,
                },
            )
            if portfolio.portfolio_name not in row["portfolio_names"]:
                row["portfolio_names"].append(portfolio.portfolio_name)
            row["sources"].append(f"보유:{portfolio.portfolio_name}")
            row["market_value"] = round((row.get("market_value") or 0) + (holding.market_value or 0), 2)
            row["quantity"] = round((row.get("quantity") or 0) + (holding.quantity or 0), 4)
            if holding.current_price is not None:
                row["current_price"] = holding.current_price
                row["price_source"] = holding.price_source

    if include_interests:
        for item in read_interest_list(settings).get("tickers", []):
            if not isinstance(item, dict):
                continue
            ticker = normalize_ticker(item.get("ticker"))
            if not ticker:
                continue
            try:
                verification = verify_ticker_symbol(ticker, settings)
                official_symbol = normalize_ticker(verification.official_symbol or ticker)
            except HTTPException:
                verification = None
                official_symbol = ticker
            profile = official_ticker_profile(official_symbol, settings)
            currency = "KRW" if profile.get("country") == "KR" or fullmatch(r"\d{6}", official_symbol) else "USD"
            row = by_ticker.setdefault(
                official_symbol,
                {
                    "ticker": official_symbol,
                    "company_name": (
                        (verification.company_name if verification else None)
                        or profile.get("company_name")
                        or official_symbol
                    ),
                    "currency": currency,
                    "sources": [],
                    "portfolio_names": [],
                    "interest": True,
                    "market_value": 0,
                    "quantity": 0,
                    "current_price": None,
                    "price_source": None,
                },
            )
            row["interest"] = True
            row["sources"].append("관심종목")
    return list(by_ticker.values())


def build_target_consensus_scan(
    settings: Settings,
    *,
    portfolio_name: str | None = None,
    include_interests: bool = True,
) -> dict:
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    universe = target_consensus_universe(settings, portfolio_name, include_interests)
    rows: list[dict] = []
    warnings: list[str] = []
    for item in universe:
        ticker = normalize_ticker(item.get("ticker"))
        currency = (item.get("currency") or "KRW").upper()
        current_price = parse_float_or_none(item.get("current_price"))
        price_source = item.get("price_source")
        consensus = build_target_price_consensus_from_memory(ticker, vault_dir, currency)
        if current_price is None and consensus is not None:
            provider_price, provider_source = latest_provider_price(ticker, settings)
            current_price = provider_price
            price_source = provider_source
        target_price = consensus.get("target_price") if consensus else None
        target_upside = (
            (target_price - current_price) / current_price
            if target_price is not None
            and current_price is not None
            and current_price > 0
            else None
        )
        if current_price is None:
            warnings.append(f"{item.get('company_name') or ticker}: 현재가를 찾지 못했습니다.")
        if consensus is None:
            warnings.append(f"{item.get('company_name') or ticker}: 저장 데이터에서 증권사 목표주가를 찾지 못했습니다.")
        if target_upside is None:
            signal = "계산 보류"
        elif target_upside >= 0.35:
            signal = "강한 저평가 후보"
        elif target_upside >= 0.2:
            signal = "저평가 후보"
        elif target_upside >= 0.05:
            signal = "중립 이상"
        elif target_upside >= 0:
            signal = "목표가 근접"
        else:
            signal = "목표가 초과"
        rows.append(
            {
                "ticker": ticker,
                "company_name": item.get("company_name") or ticker,
                "currency": currency,
                "current_price": round(current_price, 4) if current_price is not None else None,
                "price_source": price_source,
                "consensus_target_price": target_price,
                "consensus_target_currency": consensus.get("target_price_currency") if consensus else currency,
                "consensus_target_median": consensus.get("target_price_median") if consensus else None,
                "consensus_target_high": consensus.get("target_price_high") if consensus else None,
                "consensus_target_low": consensus.get("target_price_low") if consensus else None,
                "target_upside": round(target_upside, 4) if target_upside is not None else None,
                "target_gap": round((target_price - current_price), 4)
                if target_price is not None and current_price is not None
                else None,
                "source_count": consensus.get("source_count") if consensus else 0,
                "observation_count": consensus.get("observation_count") if consensus else 0,
                "confidence": consensus.get("confidence") if consensus else None,
                "latest_source_file": consensus.get("latest_source_file") if consensus else None,
                "latest_source_date": consensus.get("latest_source_date") if consensus else None,
                "latest_context": consensus.get("latest_context") if consensus else None,
                "valuation_signal": signal,
                "market_value": item.get("market_value") or 0,
                "quantity": item.get("quantity") or 0,
                "portfolio_names": item.get("portfolio_names") or [],
                "interest": bool(item.get("interest")),
                "source_scope": ", ".join(dict.fromkeys(item.get("sources") or [])),
            }
        )
    rows.sort(
        key=lambda row: (
            row.get("target_upside") is not None,
            row.get("target_upside") if row.get("target_upside") is not None else -999,
            row.get("source_count") or 0,
        ),
        reverse=True,
    )
    calculable = [row for row in rows if row.get("target_upside") is not None]
    best = calculable[0] if calculable else None
    return {
        "status": "success",
        "module": "target_consensus_scanner",
        "as_of": current_storage_timestamp(),
        "portfolio_name": portfolio_name or "__all__",
        "include_interests": include_interests,
        "universe_count": len(universe),
        "calculated_count": len(calculable),
        "best_undervalued": best,
        "summary": (
            f"{len(universe)}개 보유/관심 종목 중 {len(calculable)}개에서 현재가와 "
            "증권사 목표주가를 동시에 비교했습니다."
            + (f" 가장 저평가 후보는 {best.get('company_name')}({best.get('ticker')})입니다." if best else "")
        ),
        "warnings": warnings[:30],
        "rows": rows,
    }


@app.get(
    "/api/v1/valuation/target-consensus-scan",
    dependencies=[Depends(verify_user_token)],
)
def get_target_consensus_scan(
    portfolio_name: str | None = None,
    include_interests: bool = True,
    settings: Settings = Depends(get_settings),
) -> dict:
    return build_target_consensus_scan(
        settings,
        portfolio_name=portfolio_name,
        include_interests=include_interests,
    )


@app.get(
    "/api/v1/portfolios/{portfolio_name}/intelligent-table",
    dependencies=[Depends(verify_user_token)],
)
def get_portfolio_intelligent_table(
    portfolio_name: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    return build_portfolio_intelligent_table(portfolio_name, settings)


@app.get(
    "/api/v1/portfolios/{portfolio_name}/performance",
    dependencies=[Depends(verify_user_token)],
)
def get_portfolio_performance(
    portfolio_name: str,
    settings: Settings = Depends(get_settings),
) -> dict:
    return build_portfolio_performance(portfolio_name, settings)


@app.get(
    "/api/v1/portfolios/{portfolio_name}",
    response_model=PortfolioStoreResponse,
    dependencies=[Depends(verify_user_token)],
)
def get_portfolio(
    portfolio_name: str,
    settings: Settings = Depends(get_settings),
) -> PortfolioStoreResponse:
    store = read_portfolio_store(settings)
    key = portfolio_store_key(portfolio_name)
    payload = store.get("portfolios", {}).get(key)
    if not payload:
        raise HTTPException(status_code=404, detail=f"{portfolio_name} 포트폴리오를 찾을 수 없습니다.")
    return portfolio_store_response(
        settings,
        active_portfolio=SavedPortfolio.model_validate(payload),
    )


@app.delete(
    "/api/v1/portfolios/{portfolio_name}",
    response_model=PortfolioStoreResponse,
    dependencies=[Depends(verify_user_token)],
)
def delete_portfolio(
    portfolio_name: str,
    settings: Settings = Depends(get_settings),
) -> PortfolioStoreResponse:
    store = read_portfolio_store(settings)
    key = portfolio_store_key(portfolio_name)
    if key not in store.get("portfolios", {}):
        raise HTTPException(status_code=404, detail=f"{portfolio_name} 포트폴리오를 찾을 수 없습니다.")
    del store["portfolios"][key]
    write_json_store(portfolio_store_path(settings), store)
    return portfolio_store_response(settings)


@app.get(
    "/api/v1/interests",
    response_model=InterestListResponse,
    dependencies=[Depends(verify_user_token)],
)
def get_interests(
    settings: Settings = Depends(get_settings),
) -> InterestListResponse:
    payload = read_interest_list(settings)
    return normalize_interest_list(
        InterestListUpdateRequest(
            tickers=[InterestTicker.model_validate(item) for item in payload.get("tickers", [])],
            sectors=[InterestSector.model_validate(item) for item in payload.get("sectors", [])],
        ),
        settings,
    )


@app.put(
    "/api/v1/interests",
    response_model=InterestListResponse,
    dependencies=[Depends(verify_user_token)],
)
def save_interests(
    request: InterestListUpdateRequest,
    settings: Settings = Depends(get_settings),
) -> InterestListResponse:
    response = normalize_interest_list(request, settings)
    write_json_store(
        interest_list_path(settings),
        {
            "tickers": [item.model_dump(mode="json") for item in response.tickers],
            "sectors": [item.model_dump(mode="json") for item in response.sectors],
            "updated_at": response.updated_at,
        },
    )
    return response


@app.post(
    "/api/v1/interests/tickers",
    response_model=InterestListResponse,
    dependencies=[Depends(verify_user_token)],
)
def add_interest_ticker(
    request: dict = Body(default_factory=dict),
    settings: Settings = Depends(get_settings),
) -> InterestListResponse:
    raw_request = dict(request or {})
    ticker_value = str(
        raw_request.get("ticker")
        or raw_request.get("query")
        or raw_request.get("name")
        or raw_request.get("company")
        or ""
    ).strip()
    if not ticker_value:
        raise HTTPException(status_code=422, detail="관심종목으로 추가할 티커 또는 회사명을 입력하세요.")
    raw_request["ticker"] = ticker_value
    if "notes" not in raw_request and "note" in raw_request:
        raw_request["notes"] = raw_request.get("note")
    request_item = InterestTicker.model_validate(raw_request)
    payload = read_interest_list(settings)
    existing_tickers = [
        InterestTicker.model_validate(item)
        for item in payload.get("tickers", [])
        if isinstance(item, dict)
    ]
    existing_sectors = [
        InterestSector.model_validate(item)
        for item in payload.get("sectors", [])
        if isinstance(item, dict)
    ]
    response = normalize_interest_list(
        InterestListUpdateRequest(
            tickers=[*existing_tickers, request_item],
            sectors=existing_sectors,
        ),
        settings,
    )
    write_json_store(
        interest_list_path(settings),
        {
            "tickers": [item.model_dump(mode="json") for item in response.tickers],
            "sectors": [item.model_dump(mode="json") for item in response.sectors],
            "updated_at": response.updated_at,
        },
    )
    return response


@app.post(
    "/api/v1/interests/sectors",
    response_model=InterestListResponse,
    dependencies=[Depends(verify_user_token)],
)
def add_interest_sector(
    request: dict = Body(default_factory=dict),
    settings: Settings = Depends(get_settings),
) -> InterestListResponse:
    raw_request = dict(request or {})
    sector_name = str(
        raw_request.get("name")
        or raw_request.get("query")
        or raw_request.get("sector")
        or raw_request.get("theme")
        or ""
    ).strip()
    if not sector_name:
        raise HTTPException(status_code=422, detail="관심섹터 또는 테마명을 입력하세요.")
    raw_request["name"] = sector_name
    if "notes" not in raw_request and "note" in raw_request:
        raw_request["notes"] = raw_request.get("note")
    request_item = InterestSector.model_validate(raw_request)
    payload = read_interest_list(settings)
    existing_tickers = [
        InterestTicker.model_validate(item)
        for item in payload.get("tickers", [])
        if isinstance(item, dict)
    ]
    existing_sectors = [
        InterestSector.model_validate(item)
        for item in payload.get("sectors", [])
        if isinstance(item, dict)
    ]
    response = normalize_interest_list(
        InterestListUpdateRequest(
            tickers=existing_tickers,
            sectors=[*existing_sectors, request_item],
        ),
        settings,
    )
    write_json_store(
        interest_list_path(settings),
        {
            "tickers": [item.model_dump(mode="json") for item in response.tickers],
            "sectors": [item.model_dump(mode="json") for item in response.sectors],
            "updated_at": response.updated_at,
        },
    )
    return response


@app.get(
    "/api/v1/interests/automation-board",
    dependencies=[Depends(verify_user_token)],
)
def get_interest_automation_board(
    save_result: bool = True,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    관심종목, 보유종목, 관심섹터를 기준으로 자동 수집 대상, 중복 제거 상태,
    RAG 검색어, 시장일지 연결 포인트를 한 번에 생성합니다.
    """
    return build_interest_automation_board(settings, save_result=save_result)


@app.get(
    "/api/v1/market-data/naver/korea-indices",
    dependencies=[Depends(verify_user_token)],
)
def read_naver_korea_indices(
    settings: Settings = Depends(get_settings),
) -> dict:
    return {
        "status": "success",
        "module": "naver_korea_indices",
        "source": "naver_finance_mobile",
        "enabled": settings.naver_finance_enabled,
        "indices": fetch_naver_korea_index_snapshot(settings),
    }


@app.get(
    "/api/v1/market-close-journal",
    response_model=MarketCloseHistoryResponse,
    dependencies=[Depends(verify_user_token)],
)
def get_market_close_journal(
    market: str = "ALL",
    settings: Settings = Depends(get_settings),
) -> MarketCloseHistoryResponse:
    requested_market = normalize_market_code(market) if market != "ALL" else "ALL"
    payload = read_market_close_journal(settings)
    entries = [
        hydrate_market_close_auto_focus(MarketCloseEntry.model_validate(item), settings)
        for item in payload.get("entries", [])
        if isinstance(item, dict)
    ]
    if requested_market != "ALL":
        entries = [entry for entry in entries if entry.market == requested_market]
    entries.sort(key=lambda item: (item.session_date, item.updated_at or ""), reverse=True)
    return MarketCloseHistoryResponse(
        market=requested_market,
        entries=entries,
        storage_path=str(market_close_journal_path(settings)),
    )


@app.post(
    "/api/v1/market-close-journal/review",
    response_model=MarketCloseReviewResponse,
    dependencies=[Depends(verify_user_token)],
)
def save_market_close_review(
    request: MarketCloseReviewRequest,
    settings: Settings = Depends(get_settings),
) -> MarketCloseReviewResponse:
    source_url = (request.source_url or "").strip()
    url_info = fetch_capture_source_url(source_url) if source_url else {}
    url_body = render_source_url_body(url_info)
    if (
        source_url
        and is_unusable_source_url(url_info)
        and not str(request.raw_summary or "").strip()
        and not request.file_content_base64
    ):
        raise HTTPException(
            status_code=422,
            detail=(
                "시장일지 웹사이트 본문을 추출하지 못했습니다. "
                f"{url_info.get('note') or '시장 요약을 직접 붙여넣거나 파일을 첨부하세요.'}"
            ),
        )
    combined_summary_for_check = "\n\n".join(
        value for value in [request.raw_summary, url_body] if str(value or "").strip()
    )
    has_text = bool(clean_market_summary_text(combined_summary_for_check))
    has_file = bool(request.file_content_base64)
    if not has_text and not has_file:
        raise HTTPException(
            status_code=422,
            detail="폐장 후 시장 요약, 웹사이트 주소를 입력하거나 파일을 선택하세요.",
        )

    market = normalize_market_code(request.market)
    session_date = request.session_date or current_storage_date().isoformat()
    try:
        report_date = date.fromisoformat(session_date)
    except ValueError:
        report_date = current_storage_date()
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    attachment_request = AutoResearchCaptureRequest(
        raw_content=combined_summary_for_check,
        source_url=source_url or None,
        file_name=request.file_name,
        file_mime_type=request.file_mime_type,
        file_size=request.file_size,
        file_content_base64=request.file_content_base64,
        run_thesis_impact=False,
        save_result=request.save_result,
    )
    attachment_info = save_capture_attachment(
        vault_dir=vault_dir,
        ticker=market_research_key(market),
        storage_date=report_date,
        request=attachment_request,
    )
    attachment_context = render_attachment_context(attachment_request, attachment_info)
    raw_summary = "\n\n--- 첨부 파일 내용 ---\n\n".join(
        value
        for value in [combined_summary_for_check, attachment_context]
        if str(value or "").strip()
    )
    enriched_request = request.model_copy(
        update={
            "market": market,
            "session_date": session_date,
            "raw_summary": raw_summary,
        }
    )

    entry, prior_entries, patterns, regime_summary = build_market_close_entry(
        enriched_request,
        settings,
        attachment_info=attachment_info,
    )
    all_entries = prior_entries + [entry]
    all_entries.sort(key=lambda item: (item.session_date, item.market, item.entry_id))
    response = MarketCloseReviewResponse(
        entry=entry,
        history_count=len([item for item in all_entries if item.market == entry.market]),
        cumulative_patterns=patterns,
        recent_regime_summary=regime_summary,
        storage_path=str(market_close_journal_path(settings)),
        saved_to_research_memory=request.save_result,
        attachment=attachment_info,
        source_url_processing=url_info if source_url else None,
        capture_quality=capture_quality_status(
            raw_content=raw_summary,
            attachment_info=attachment_info,
            source_url_processing=url_info if source_url else None,
        ),
    )

    write_json_store(
        market_close_journal_path(settings),
        {
            "entries": [item.model_dump(mode="json") for item in all_entries],
            "updated_at": current_storage_timestamp(),
        },
    )

    if request.save_result:
        response.storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=market_research_key(entry.market),
            report_type="market-close-review",
            markdown=render_market_close_markdown(response, report_date),
            structured_payload=response.model_dump(mode="json"),
            manifest_entry={
                "summary": f"{entry.market} {entry.session_date} 폐장 리뷰: {entry.regime}, 심리 {entry.sentiment}, 리스크 {entry.risk_level}",
                "market": entry.market,
                "session_date": entry.session_date,
                "sentiment": entry.sentiment,
                "risk_level": entry.risk_level,
                "regime": entry.regime,
                "tags": entry.tags,
                "auto_utilization_focus": entry.auto_utilization_focus,
                "interest_implications": entry.interest_implications,
            },
            report_date=report_date,
        )

    return response


@app.post(
    "/api/v1/portfolio/reinforcement-optimizer",
    response_model=ReinforcementPortfolioOptimizationResponse,
    dependencies=[Depends(verify_user_token)],
)
def run_reinforcement_portfolio_optimizer(
    request: ReinforcementPortfolioOptimizationRequest,
    settings: Settings = Depends(get_settings),
) -> ReinforcementPortfolioOptimizationResponse:
    """
    누적 시장일지, 저장 포트폴리오, 실적/뉴스 분석 결과를 상태·행동·보상 구조로 변환해
    강화학습형 포트폴리오 최적화 정책 후보를 생성합니다.
    """
    return run_reinforcement_portfolio_policy(request, settings)


@app.post(
    "/api/v1/portfolio/risk-scan",
    response_model=PortfolioRiskScanResponse,
    dependencies=[Depends(verify_user_token)],
)
def run_portfolio_risk_scan(
    request: PortfolioRiskScanRequest,
    settings: Settings = Depends(get_settings),
) -> PortfolioRiskScanResponse:
    """
    보유 종목 비중, 섹터, 테마 태그를 기반으로 포트폴리오 집중도와 리스크 경고를 생성합니다.
    결과는 research_vault에 Markdown/JSON/manifest로 저장됩니다.
    """
    holdings, portfolio_value = normalize_portfolio_holdings(
        request.holdings,
        request.portfolio_value,
    )
    if not holdings:
        store = read_portfolio_store(settings)
        key = portfolio_store_key(request.portfolio_name)
        saved = store.get("portfolios", {}).get(key)
        if saved:
            saved_portfolio = SavedPortfolio.model_validate(saved)
            holdings, portfolio_value = normalize_portfolio_holdings(
                saved_portfolio.holdings,
                saved_portfolio.portfolio_value,
            )

    single_position_concentration = aggregate_concentration(
        holdings,
        lambda holding: holding.ticker,
    )
    sector_concentration = aggregate_concentration(
        holdings,
        lambda holding: holding.sector,
    )
    theme_concentration = aggregate_concentration(
        holdings,
        lambda holding: holding.theme_tags or ["Untagged"],
    )
    top_five_weight = round(
        sum((holding.weight or 0) for holding in sorted(holdings, key=lambda item: item.weight or 0, reverse=True)[:5]),
        4,
    )
    warnings = build_portfolio_warnings(
        holdings=holdings,
        sector_concentration=sector_concentration,
        theme_concentration=theme_concentration,
        request=request,
        top_five_weight=top_five_weight,
        settings=settings,
    )
    dart_watch_alerts = [
        f"{holding.ticker}: {signal.get('summary')}"
        for holding in holdings
        for signal in [build_dart_filing_signal(holding.ticker, settings)]
        if signal.get("recent_count") and signal.get("important_count")
    ][:3]
    risk_score = calculate_portfolio_risk_score(warnings)
    has_nps_flow_warning = any(item.type == "nps_institutional_flow" for item in warnings)
    next_actions = [
        "집중도가 높은 상위 보유 종목은 7개 스킬 팀 리포트를 실행하세요.",
        "이미 한도를 초과한 섹터나 테마에는 추가 노출을 신중히 제한하세요.",
        "고집중 종목을 추가 매수하기 전 thesis-impact-review로 최신 논거 변화를 확인하세요.",
    ]
    if dart_watch_alerts:
        next_actions.insert(
            0,
            "DART 중요 공시 감지: " + " / ".join(dart_watch_alerts),
        )
    if has_nps_flow_warning:
        next_actions.insert(
            0,
            "국민연금 대량보유/보유비중이 확인된 종목은 추가매수 전 보고 기준일, 증감 방향, 동일 섹터 동반 매도 여부를 확인하세요.",
        )
    if risk_score < 45:
        next_actions = [
            *(
                ["국민연금 대량보유 신호가 있는 종목은 수급 변화 방향을 계속 추적하세요."]
                if has_nps_flow_warning
                else []
            ),
            "현재 분산 원칙을 유지하고 주요 추적 항목을 계속 모니터링하세요.",
            "큰 가격 변동, 실적 발표, 포트폴리오 변경 후 리스크 스캔을 다시 실행하세요.",
        ]

    scan = PortfolioRiskScanResponse(
        portfolio_name=request.portfolio_name,
        portfolio_value=round(portfolio_value, 2),
        holdings=holdings,
        single_position_concentration=single_position_concentration,
        sector_concentration=sector_concentration,
        theme_concentration=theme_concentration,
        top_five_weight=top_five_weight,
        risk_score=risk_score,
        warnings=warnings,
        next_actions=next_actions,
        saved_to_research_memory=request.save_result,
    )

    if request.save_result:
        storage_date = current_storage_date()
        vault_dir = resolve_vault_dir(settings.research_vault_dir)
        portfolio_key = normalize_ticker(request.portfolio_name)
        scan.storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=portfolio_key,
            report_type="portfolio-risk-scan",
            markdown=render_portfolio_risk_markdown(scan, storage_date),
            structured_payload=scan.model_dump(mode="json"),
            manifest_entry={
                "summary": f"{request.portfolio_name} 리스크 점수 {risk_score}/100, 상위 5개 비중 {top_five_weight:.0%}",
                "portfolio_value": round(portfolio_value, 2),
                "risk_score": risk_score,
                "top_five_weight": top_five_weight,
                "sector_concentration": [
                    item.model_dump(mode="json") for item in sector_concentration
                ],
                "theme_concentration": [
                    item.model_dump(mode="json") for item in theme_concentration
                ],
                "warnings": [item.model_dump(mode="json") for item in warnings],
            },
            report_date=storage_date,
        )

    return scan


@app.post(
    "/api/v1/analysis/modules/institutional-stock-breakdown/run",
    response_model=InstitutionalAnalysisResponse,
    dependencies=[Depends(verify_user_token)],
)
def run_institutional_stock_breakdown(
    request: InstitutionalAnalysisRequest,
    settings: Settings = Depends(get_settings),
) -> InstitutionalAnalysisResponse:
    """
    티커 입력 후 실행 버튼을 눌렀을 때 모듈 1로 자동 이동하고 즉시 분석을 시작하는 API입니다.

    현재는 화면 연동과 데이터 계약 검증을 위한 구조화된 Mock 분석을 반환합니다.
    이후 재무 데이터, 저장된 리서치 메모, LLM 분석 엔진을 연결해 같은 응답 모델로 교체합니다.
    """
    ticker = ensure_verified_ticker(request.ticker)
    focus = analysis_focus_for_ticker(ticker, request.focus_area)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    analysis_input_data = collect_analysis_input_data(
        ticker=ticker,
        provided_data=request.realtime_data,
        auto_inject_data=request.auto_inject_data,
        settings=settings,
    )
    injected_data = collect_workspace_context(ticker, vault_dir, analysis_input_data)
    dart_context = summarize_dart_filing_context(build_dart_filing_signal(ticker, settings))
    dart_risk = f"최근 DART 공시 확인: {dart_context}" if dart_context else None

    analysis = InstitutionalAnalysisResponse(
        ticker=ticker,
        investment_period=request.investment_period,
        focus_area=focus,
        executive_summary=(
            f"{ticker_company_name(ticker)}({ticker})에 대한 기관급 분석을 시작했습니다. "
            f"투자 기간은 {request.investment_period}이며, 중점 분석은 {focus}입니다."
        ),
        bull_case=ScenarioSummary(
            title="강세 시나리오",
            thesis="핵심 성장 동력이 예상보다 오래 지속되고 마진 방어력이 확인될 경우 멀티플 프리미엄이 유지될 수 있습니다.",
            watch_items=["매출 성장률", "영업마진", "신규 수요 지표", "상향된 가이던스"],
        ),
        base_case=ScenarioSummary(
            title="기준 시나리오",
            thesis="현재 시장 기대에 부합하는 성장과 수익성을 유지하면 주가는 실적 확인 구간마다 재평가될 수 있습니다.",
            watch_items=["컨센서스 변화", "현금흐름", "경쟁사 실적", "밸류에이션 밴드"],
        ),
        bear_case=ScenarioSummary(
            title="약세 시나리오",
            thesis="성장 둔화, 가격 경쟁, 규제 또는 밸류에이션 압축이 발생하면 투자 논거가 약화될 수 있습니다.",
            watch_items=["가이던스 하향", "마진 압박", "재고 증가", "규제 뉴스"],
        ),
        key_risks=[
            "높은 밸류에이션이 실적 둔화에 민감하게 반응할 수 있음",
            "경쟁 심화 또는 기술 변화로 기존 경쟁 우위가 약해질 수 있음",
            "거시 환경 변화가 할인율과 섹터 선호도에 영향을 줄 수 있음",
            *([dart_risk] if dart_risk else []),
        ],
        next_actions=[
            *(
                ["최근 DART 공시 내용을 사업/재무/수급 리스크 단락에 반영"]
                if dart_context
                else []
            ),
            "최근 실적 발표와 컨센서스 변화를 연결해 Base Case 가정을 보정",
            "저장된 리서치 메모 중 해당 티커 관련 긍정/부정 근거를 병합",
            "매매 전략 모듈에서 진입 구간과 무효화 조건을 별도로 설계",
        ],
        injected_data=injected_data,
        saved_to_research_memory=request.save_result,
    )

    if request.save_result:
        storage_date = current_storage_date()
        analysis.storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=ticker,
            report_type="institutional-stock-breakdown",
            markdown=render_institutional_markdown(analysis, storage_date),
            structured_payload=analysis.model_dump(mode="json"),
            manifest_entry=manifest_with_ticker_verification(ticker, {
                "summary": analysis.executive_summary,
                "source_count": len(analysis.injected_data),
                "key_risks": analysis.key_risks,
                "watch_items": analysis.bull_case.watch_items
                + analysis.base_case.watch_items
                + analysis.bear_case.watch_items,
            }),
            report_date=storage_date,
        )

    return analysis


@app.post(
    "/api/v1/analysis/modules/naver-chart/run",
    dependencies=[Depends(verify_user_token)],
)
def run_naver_chart_analysis(
    ticker: str | None = None,
    save_result: bool = True,
    payload: dict | None = Body(default=None),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    네이버 증권 국내 종목 일별 시세를 수집해 거래량, 볼린저 밴드, 이동평균선,
    MACD, RSI 14, DMI 14를 계산하고 저장 가능한 차트 분석으로 반환합니다.
    """
    body = payload if isinstance(payload, dict) else {}
    requested_ticker = str(ticker or body.get("ticker") or "").strip()
    requested_save_result = body.get("save_result", body.get("saveResult", save_result))
    if isinstance(requested_save_result, str):
        requested_save_result = requested_save_result.strip().lower() not in {"0", "false", "no", "off"}
    if not requested_ticker:
        raise HTTPException(status_code=422, detail="차트 분석할 국내 종목명 또는 종목코드를 입력하세요.")
    return build_naver_chart_analysis(
        requested_ticker,
        settings,
        save_result=bool(requested_save_result),
    )


@app.post(
    "/api/v1/analysis/modules/smart-trade-setup/run",
    response_model=SmartTradeSetupResponse,
    dependencies=[Depends(verify_user_token)],
)
def run_smart_trade_setup(
    request: SmartTradeSetupRequest,
    settings: Settings = Depends(get_settings),
) -> SmartTradeSetupResponse:
    """
    특정 종목의 현재가, 매매 스타일, 허용 리스크를 바탕으로 구조화된 매매 계획을 생성합니다.
    진입 구간, 손절가, 목표가, 손익비, 포지션 리스크 가이드를 저장 가능한 형태로 반환합니다.
    """
    ticker = ensure_verified_ticker(request.ticker)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    analysis_input_data = collect_analysis_input_data(
        ticker=ticker,
        provided_data=request.realtime_data,
        auto_inject_data=request.auto_inject_data,
        settings=settings,
    )
    injected_data = collect_workspace_context(ticker, vault_dir, analysis_input_data)
    setup = build_smart_trade_setup(ticker, request, injected_data)

    if request.save_result:
        storage_date = current_storage_date()
        setup.storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=ticker,
            report_type="smart-trade-setup",
            markdown=render_smart_trade_markdown(setup, storage_date),
            structured_payload=setup.model_dump(mode="json"),
            manifest_entry=manifest_with_ticker_verification(ticker, {
                "summary": (
                    f"{ticker} 매매 전략: 1차 진입 {setup.entry_zone[0].price:.2f}, "
                    f"손절 {setup.stop_loss.price:.2f}, 1차 목표 {setup.targets[0].price:.2f}"
                ),
                "current_price": setup.current_price,
                "style": setup.style,
                "risk_tolerance": setup.risk_tolerance,
                "market_structure": setup.market_structure,
                "setup_quality": setup.setup_quality,
                "entry_zone": [item.model_dump(mode="json") for item in setup.entry_zone],
                "stop_loss": setup.stop_loss.model_dump(mode="json"),
                "targets": [item.model_dump(mode="json") for item in setup.targets],
                "risk_per_share": setup.risk_per_share,
            }),
            report_date=storage_date,
        )

    return setup


@app.post(
    "/api/v1/analysis/modules/earnings-reaction/run",
    response_model=EarningsReactionResponse,
    dependencies=[Depends(verify_user_token)],
)
def run_earnings_reaction_analyzer(
    request: EarningsReactionRequest,
    settings: Settings = Depends(get_settings),
) -> EarningsReactionResponse:
    """
    실적 수치, 주가 반응, 가이던스 변경, 경영진 톤을 종합해 실적 발표 이후 시장 반응을 분석합니다.
    결과는 다음 실적 전 추적 항목과 투자 논거 영향까지 포함해 research_vault에 저장됩니다.
    """
    ticker = ensure_verified_ticker(request.ticker)
    request = enrich_earnings_request_with_profile_dates(
        ticker,
        request,
        settings,
        refresh_external=False,
    )
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    analysis_input_data = collect_analysis_input_data(
        ticker=ticker,
        provided_data=request.realtime_data,
        auto_inject_data=request.auto_inject_data,
        settings=settings,
    )
    request = enrich_earnings_request_with_injected_financials(request, analysis_input_data)
    injected_data = collect_workspace_context(ticker, vault_dir, analysis_input_data)
    reaction = build_earnings_reaction(ticker, request, injected_data, settings)

    if request.save_result:
        storage_date = current_storage_date()
        reaction.storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=ticker,
            report_type="earnings-reaction",
            markdown=render_earnings_reaction_markdown(reaction, storage_date),
            structured_payload=reaction.model_dump(mode="json"),
            manifest_entry=manifest_with_ticker_verification(ticker, {
                "summary": reaction.headline_assessment,
                "quarter": reaction.quarter,
                "official_latest_quarter": reaction.official_latest_quarter,
                "official_latest_earnings_report_date": reaction.official_latest_earnings_report_date,
                "earnings_calendar_source": reaction.earnings_calendar_source,
                "earnings_reference_status": reaction.earnings_reference_status,
                "earnings_report_date": reaction.earnings_report_date,
                "previous_earnings_date": reaction.previous_earnings_date,
                "previous_earnings_key_takeaways": reaction.previous_earnings_key_takeaways,
                "next_earnings_date": reaction.next_earnings_date,
                "next_earnings_guidance": reaction.next_earnings_guidance,
                "price_reaction": reaction.price_reaction,
                "reaction_type": reaction.reaction_type,
                "sentiment_shift": reaction.sentiment_shift,
                "guidance_assessment": reaction.guidance_assessment,
                "evidence_status": reaction.evidence_status,
                "missing_inputs": reaction.missing_inputs,
                "watch_before_next_earnings": reaction.watch_before_next_earnings,
                "thesis_implications": reaction.thesis_implications,
            }),
            report_date=storage_date,
        )

    return reaction


def workflow_material_excerpt(value: str | None, limit: int = 900) -> str:
    compact = " ".join((value or "").split())
    if not compact:
        return "입력 자료 없음"
    return compact if len(compact) <= limit else f"{compact[:limit - 3]}..."


def prepare_workflow_attachment(
    *,
    vault_dir: Path,
    storage_key: str,
    payload: dict,
    storage_date: date,
) -> dict | None:
    file_bytes = decode_attachment_base64(payload.get("file_content_base64"))
    if file_bytes is None:
        return None
    safe_key = normalize_ticker(storage_key) or "WORKFLOW"
    attachments_dir = vault_dir / safe_key / "_attachments"
    attachments_dir.mkdir(parents=True, exist_ok=True)
    safe_name = safe_attachment_file_name(payload.get("file_name"))
    timestamp = datetime.now().strftime("%H%M%S")
    attachment_path = attachments_dir / f"{safe_key}-workflow-attachment-{storage_date.isoformat()}-{timestamp}-{safe_name}"
    attachment_path.write_bytes(file_bytes)
    extraction = extract_uploaded_file_text(
        file_bytes,
        payload.get("file_name"),
        payload.get("file_mime_type"),
        source_path=attachment_path,
    )
    return {
        "file_name": payload.get("file_name") or safe_name,
        "mime_type": payload.get("file_mime_type") or "application/octet-stream",
        "size": len(file_bytes),
        "relative_path": attachment_path.relative_to(vault_dir).as_posix(),
        "text_extraction": extraction.get("text_extraction"),
        "extracted_text": extraction.get("extracted_text") or "",
        "document_type": extraction.get("document_type"),
        "extraction_quality": extraction.get("extraction_quality"),
        "extraction_char_count": extraction.get("extraction_char_count"),
        "extraction_preview": extraction.get("extraction_preview"),
        "extraction_warnings": extraction.get("extraction_warnings") or [],
        "extraction_profile": extraction.get("extraction_profile") or {},
    }


def upsert_saved_workflow_rag_document(
    *,
    vault_dir: Path,
    storage: ResearchStorageInfo,
    storage_key: str,
    report_type: str,
    summary: str,
    markdown: str,
    tags: list[str] | None = None,
    source_confidence: float = 0.85,
    metadata: dict | None = None,
) -> dict:
    entry = {
        "ticker": normalize_ticker(storage_key) or "GENERAL",
        "type": report_type,
        "date": current_storage_date().isoformat(),
        "file_name": storage.file_name,
        "relative_path": storage.relative_path,
        "json_file_name": storage.json_file_name,
        "json_relative_path": storage.json_relative_path,
        "summary": summary,
        "title": storage.file_name,
        "source_confidence": source_confidence,
        "tags": tags or [],
        **(metadata or {}),
    }
    return upsert_research_memory_document(
        vault_dir=vault_dir,
        entry=entry,
        full_text=markdown,
    )


def infer_model_update_items(material_text: str) -> list[dict]:
    text = material_text.lower()
    rules = [
        ("매출", ["revenue", "sales", "매출", "수요", "주문"], "매출 성장률과 다음 분기 가이던스 가정을 재점검"),
        ("마진", ["margin", "gross margin", "operating margin", "마진", "원가"], "매출총이익률/영업이익률 가정 업데이트"),
        ("CAPEX", ["capex", "투자", "설비", "데이터센터", "전력"], "CAPEX와 감가상각, 관련 수혜/부담 항목 반영"),
        ("현금흐름", ["cash flow", "fcf", "현금흐름", "현금 소진", "free cash"], "FCF, 운전자본, 현금 소진 속도 업데이트"),
        ("가이던스", ["guidance", "outlook", "가이던스", "전망"], "회사 가이던스와 컨센서스 차이를 모델에 반영"),
        ("리스크", ["risk", "lawsuit", "regulation", "리스크", "규제", "소송"], "할인율, 목표 멀티플, 약세 시나리오 확률 조정"),
    ]
    updates = []
    for label, keywords, action in rules:
        matched = [keyword for keyword in keywords if keyword in text]
        if matched:
            updates.append({
                "item": label,
                "signal": ", ".join(matched[:4]),
                "model_action": action,
                "status": "업데이트 필요",
            })
    if not updates:
        updates.append({
            "item": "핵심 가정",
            "signal": "명시적 수치 신호 부족",
            "model_action": "어닝 콜/공시 원문에서 매출, 마진, 현금흐름, 가이던스 수치를 보강",
            "status": "보강 필요",
        })
    return updates


def render_file_processing_markdown(file_processing: dict | None) -> str:
    if not file_processing:
        return "- 첨부 파일 없음"
    profile = file_processing.get("extraction_profile") or {}
    lines = [
        f"- 파일명: {file_processing.get('file_name')}",
        f"- 문서 유형: {file_processing.get('document_type') or '미확인'}",
        f"- 저장 경로: {file_processing.get('relative_path')}",
        f"- 추출 상태: {file_processing.get('text_extraction')}",
        f"- 추출 품질: {file_processing.get('extraction_quality') or '미평가'}",
        f"- 추출 본문 길이: {file_processing.get('extraction_char_count') or 0}자",
    ]
    if profile:
        lines.extend(
            [
                f"- 분석 활용도: {profile.get('analysis_readiness') or '미평가'}",
                f"- 구조 신호: 줄 {profile.get('line_count') or 0}개, 숫자 토큰 {profile.get('numeric_token_count') or 0}개, 표형 줄 {profile.get('table_like_line_count') or 0}개",
                f"- 권장 조치: {profile.get('next_action') or '미평가'}",
            ]
        )
        if profile.get("image_size") or profile.get("ocr_available") is not None:
            ocr_state = "사용 가능" if profile.get("ocr_available") else "사용 불가"
            lines.append(f"- 이미지/OCR: {profile.get('image_size') or '크기 미확인'} · OCR {ocr_state}")
        if profile.get("ocr_language"):
            lines.append(f"- OCR 언어: {profile.get('ocr_language')}")
    lines.extend(
        f"- 추출 경고: {warning}"
        for warning in (file_processing.get("extraction_warnings") or [])
    )
    return "\n".join(lines)


def render_earnings_filing_note_markdown(response: dict, storage_date: date) -> str:
    model_updates = "\n".join(
        f"- {item['item']}: {item['model_action']} (근거: {item['signal']})"
        for item in response.get("model_updates", [])
    )
    file_processing = response.get("file_processing") or {}
    file_section = render_file_processing_markdown(file_processing)
    note_sections = "\n\n".join(f"## {section['title']}\n\n{section['body']}" for section in response.get("note_draft", []))
    open_questions = "\n".join(f"- {item}" for item in response.get("open_questions", []))
    next_actions = "\n".join(f"- {item}" for item in response.get("next_actions", []))
    return f"""---
ticker: {response.get('ticker')}
type: earnings-filing-note
date: {storage_date.isoformat()}
module: earnings_filing_note
persona: Buy-Side 모델 업데이트 애널리스트
---

# {response.get('company_name')}({response.get('ticker')}) 어닝 콜/공시 기반 노트 초안

## 모델 업데이트 항목

{model_updates}

## 첨부 파일 처리

{file_section}

{note_sections}

## 미확인 질문

{open_questions}

## 다음 액션

{next_actions}
"""


def build_earnings_filing_note_response(payload: dict, settings: Settings) -> dict:
    requested_ticker = str(payload.get("ticker") or "").strip()
    ticker = resolve_ticker_symbol_from_alias(requested_ticker, settings)
    profile = OFFICIAL_TICKER_REGISTRY.get(ticker) or read_dynamic_ticker_registry(settings).get(ticker)
    if not profile:
        raise HTTPException(
            status_code=422,
            detail=f"{requested_ticker or '미입력'}는 로컬/캐시 티커 레지스트리에서 확인되지 않았습니다. 먼저 대시보드 티커 진단이나 정보 입력으로 등록하세요.",
        )
    company_name = profile.get("company_name") or ticker
    earnings_call = str(payload.get("earnings_call") or payload.get("earnings_call_text") or "")
    filing_material = str(payload.get("filing_material") or payload.get("filing_text") or "")
    model_notes = str(payload.get("model_notes") or "")
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    attachment_info = prepare_workflow_attachment(
        vault_dir=vault_dir,
        storage_key=ticker,
        payload=payload,
        storage_date=current_storage_date(),
    )
    profile_points = [
        InjectedDataPoint(
            source_type=DataSourceType.OTHER,
            label="official_company_profile",
            value=(
                f"{company_name} | 사업 맥락: {profile.get('business_context') or 'n/a'} | "
                f"핵심 KPI: {', '.join(profile.get('watch_kpis') or []) or 'n/a'}"
            ),
            as_of=current_storage_date().isoformat(),
            source_url="official_ticker_registry",
            confidence=0.95,
        )
    ]
    ticker_dir = vault_dir / ticker
    saved_report_count = len(list(ticker_dir.glob(f"{ticker}-*.md"))) if ticker_dir.exists() else 0
    injected_data = [
        *profile_points,
        InjectedDataPoint(
            source_type=DataSourceType.RESEARCH_MEMORY,
            label="linked_workspace_reports",
            value=f"모델 업데이트 전 참고 가능한 저장 리포트 {saved_report_count}개",
            as_of=current_storage_date().isoformat(),
            confidence=1.0,
        ),
    ]
    material_text = "\n".join([
        earnings_call,
        filing_material,
        model_notes,
        attachment_info.get("extracted_text", "") if attachment_info else "",
        *[f"{item.label}: {item.value}" for item in injected_data[:8]],
    ])
    model_updates = infer_model_update_items(material_text)
    evidence_summary = workflow_material_excerpt(material_text, 1200)
    note_draft = [
        {
            "title": "핵심 요약",
            "body": f"{company_name}의 최신 어닝 콜/공시 자료를 기준으로 모델 업데이트가 필요한 항목은 {', '.join(item['item'] for item in model_updates)}입니다.",
        },
        {
            "title": "투자 논거 변화",
            "body": "기존 투자 논거는 숫자 업데이트 전까지 유지하되, 가이던스·마진·현금흐름 신호가 기존 강세/기준/약세 시나리오 중 어느 쪽을 강화하는지 재분류해야 합니다.",
        },
        {
            "title": "근거 메모",
            "body": evidence_summary,
        },
    ]
    open_questions = [
        "회사 가이던스가 컨센서스 대비 상향/하향인지 확인",
        "매출 성장률과 마진 변화가 일회성인지 구조적인지 확인",
        "현금흐름, CAPEX, 재고/운전자본 변화가 밸류에이션에 미치는 영향 확인",
    ]
    next_actions = [
        "모델의 매출, 마진, FCF, 목표 멀티플 입력값 업데이트",
        "업데이트된 모델 결과를 팀 리포트와 매매 전략에 재연결",
        "다음 실적 전 확인할 KPI를 체크리스트 또는 저장 데이터에 반영",
    ]
    return {
        "status": "success",
        "module": "earnings_filing_note",
        "ticker": ticker,
        "company_name": company_name,
        "model_updates": model_updates,
        "note_draft": note_draft,
        "open_questions": open_questions,
        "next_actions": next_actions,
        "file_processing": {
            key: value for key, value in (attachment_info or {}).items() if key != "extracted_text"
        },
        "injected_data": [item.model_dump(mode="json") for item in injected_data],
    }


def render_lp_report_staging_markdown(response: dict, storage_date: date) -> str:
    valuation = "\n".join(f"- {item}" for item in response.get("valuation_template_output", []))
    valuation_rows = "\n".join(
        f"| {item.get('line_item')} | {item.get('input_status')} | {item.get('model_action')} | {item.get('lp_note')} |"
        for item in response.get("valuation_template_rows", [])
    )
    staging = "\n".join(f"- {item}" for item in response.get("staging_checklist", []))
    risks = "\n".join(f"- {item}" for item in response.get("lp_risk_flags", []))
    draft = "\n\n".join(f"## {section['title']}\n\n{section['body']}" for section in response.get("lp_report_draft", []))
    file_processing = response.get("file_processing") or {}
    file_section = render_file_processing_markdown(file_processing)
    return f"""---
type: lp-report-staging
date: {storage_date.isoformat()}
module: gp_lp_staging
fund_name: {response.get('fund_name')}
---

# {response.get('fund_name')} LP 보고 스테이징

## GP 패키지 요약

{response.get('gp_package_summary')}

## 밸류에이션 템플릿 결과

{valuation}

| 항목 | 입력 상태 | 모델 액션 | LP 보고 메모 |
| --- | --- | --- | --- |
{valuation_rows}

## 첨부 파일 처리

{file_section}

{draft}

## LP 보고 전 리스크 플래그

{risks}

## 스테이징 체크리스트

{staging}
"""


def build_gp_lp_staging_response(payload: dict, settings: Settings) -> dict:
    fund_name = str(payload.get("fund_name") or "GP 패키지").strip()
    package_text = str(payload.get("gp_package") or payload.get("gp_package_text") or "")
    valuation_method = str(payload.get("valuation_method") or "멀티플/DCF 혼합").strip()
    base_case = str(payload.get("base_case") or "기준 시나리오").strip()
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    storage_key = normalize_ticker(fund_name) or "LP-REPORT"
    attachment_info = prepare_workflow_attachment(
        vault_dir=vault_dir,
        storage_key=storage_key,
        payload=payload,
        storage_date=current_storage_date(),
    )
    if attachment_info and attachment_info.get("extracted_text"):
        package_text = "\n".join([package_text, attachment_info.get("extracted_text", "")]).strip()
    package_summary = summarize_capture(package_text) if package_text else "입력된 GP 패키지 본문이 없어 스테이징 틀만 생성했습니다."
    lower_text = package_text.lower()
    valuation_template_output = [
        f"사용 템플릿: {valuation_method}",
        f"기준 시나리오: {base_case}",
        "NAV/공정가치, 매출 성장률, EBITDA/FCF, 할인율 또는 목표 멀티플 입력값을 LP 보고 전 확정해야 합니다.",
        "전분기 대비 변동이 큰 자산은 GP 코멘트, 거래 사례, 외부 평가 근거를 별도 첨부하세요.",
    ]
    if any(word in lower_text for word in ["down round", "write-down", "손상", "감액", "하락"]):
        valuation_template_output.append("감액 신호가 있어 약세 시나리오와 손상 근거 확인이 필요합니다.")
    if any(word in lower_text for word in ["exit", "ipo", "m&a", "상장", "매각"]):
        valuation_template_output.append("엑시트 이벤트가 언급되어 회수 시점과 할인율 민감도 표를 추가하세요.")
    valuation_template_rows = [
        {
            "line_item": "NAV/공정가치",
            "input_status": "확인 필요",
            "model_action": "전분기 NAV와 이번 평가가치 차이를 입력",
            "lp_note": "평가 기준일과 통화 단위를 명확히 표시",
        },
        {
            "line_item": "매출 성장률",
            "input_status": "GP 본문/파일에서 추출",
            "model_action": "전년 대비 및 전분기 대비 성장률 분리",
            "lp_note": "성장률 둔화/가속의 원인을 한 줄로 설명",
        },
        {
            "line_item": "EBITDA/FCF",
            "input_status": "보강 필요",
            "model_action": "수익성 개선과 현금 소진 속도 확인",
            "lp_note": "손익과 현금흐름 방향이 다르면 별도 리스크로 표기",
        },
        {
            "line_item": "할인율/목표 멀티플",
            "input_status": valuation_method,
            "model_action": "피어 멀티플 또는 DCF 할인율을 전분기와 비교",
            "lp_note": "평가 방법이 바뀐 경우 LP 질문 대비",
        },
        {
            "line_item": "엑시트/펀딩 이벤트",
            "input_status": "이벤트 여부 확인",
            "model_action": "IPO, M&A, 다운라운드 가능성 반영",
            "lp_note": "회수 가능성과 감액 가능성을 분리해 설명",
        },
    ]
    lp_report_draft = [
        {
            "title": "LP 보고 초안 요약",
            "body": f"{fund_name}의 GP 패키지를 기준으로 {valuation_method} 템플릿을 실행할 준비가 되었습니다. 핵심은 평가가치 변동, 실현/미실현 손익, 주요 포트폴리오 이벤트를 LP가 바로 이해할 수 있게 정리하는 것입니다.",
        },
        {
            "title": "포트폴리오 업데이트",
            "body": "주요 자산별 매출/마진/현금흐름/KPI 변화와 밸류에이션 변동 원인을 한 줄씩 연결하세요. 변동 폭이 큰 자산은 GP 원문 근거를 각주 또는 부록으로 붙입니다.",
        },
        {
            "title": "본문 근거",
            "body": workflow_material_excerpt(package_text, 1000),
        },
    ]
    lp_risk_flags = [
        "GP 제공 수치와 내부 밸류에이션 입력값의 기준일 불일치 가능성",
        "평가 방법 변경 또는 비교 멀티플 변경 시 LP 질문 가능성",
        "현금 소진, 추가 펀딩 필요, 엑시트 지연 자산은 별도 설명 필요",
    ]
    staging_checklist = [
        "GP 패키지 원문, 보유 비중, 평가 기준일 확인",
        "밸류에이션 템플릿 입력값과 전분기 입력값 비교",
        "LP 보고용 요약표, 주요 변동 사유, 리스크 플래그 확정",
        "최종 보고 전 수치 단위, 통화, 기준일, 소수점 표기 검수",
    ]
    return {
        "status": "success",
        "module": "gp_lp_staging",
        "fund_name": fund_name,
        "gp_package_summary": package_summary,
        "valuation_method": valuation_method,
        "valuation_template_output": valuation_template_output,
        "valuation_template_rows": valuation_template_rows,
        "lp_report_draft": lp_report_draft,
        "lp_risk_flags": lp_risk_flags,
        "staging_checklist": staging_checklist,
        "file_processing": {
            key: value for key, value in (attachment_info or {}).items() if key != "extracted_text"
        },
    }


@app.post(
    "/api/v1/workflows/earnings-filing-note",
    dependencies=[Depends(verify_user_token)],
)
def run_earnings_filing_note_workflow(
    payload: dict = Body(...),
    settings: Settings = Depends(get_settings),
) -> dict:
    response = build_earnings_filing_note_response(payload, settings)
    if payload.get("save_result", True):
        storage_date = current_storage_date()
        vault_dir = resolve_vault_dir(settings.research_vault_dir)
        markdown = render_earnings_filing_note_markdown(response, storage_date)
        storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=response["ticker"],
            report_type="earnings-filing-note",
            markdown=markdown,
            structured_payload=response,
            manifest_entry={
                "summary": f"{response['company_name']} 어닝 콜/공시 기반 모델 업데이트 노트 초안",
                "model_updates": response["model_updates"],
                "open_questions": response["open_questions"],
                "source_confidence": 0.88,
                "tags": ["earnings", "filing", "model_update", "valuation", "rag_connected"],
                "ticker_verification": {
                    "official_symbol": response["ticker"],
                    "company_name": response["company_name"],
                    "verified": True,
                    "verification_source": "local_or_dynamic_registry",
                },
            },
            report_date=storage_date,
        )
        response["storage"] = storage
        response["rag_document"] = upsert_saved_workflow_rag_document(
            vault_dir=vault_dir,
            storage=storage,
            storage_key=response["ticker"],
            report_type="earnings-filing-note",
            summary=f"{response['company_name']} 어닝 콜/공시 기반 모델 업데이트 노트 초안",
            markdown=markdown,
            tags=["earnings", "filing", "model_update", "valuation", "workflow"],
            source_confidence=0.88,
            metadata={
                "ticker_verification": {
                    "official_symbol": response["ticker"],
                    "company_name": response["company_name"],
                    "verified": True,
                    "verification_source": "local_or_dynamic_registry",
                },
                "model_updates": response["model_updates"],
                "open_questions": response["open_questions"],
            },
        )
    return response


@app.post(
    "/api/v1/workflows/gp-lp-staging",
    dependencies=[Depends(verify_user_token)],
)
def run_gp_lp_staging_workflow(
    payload: dict = Body(...),
    settings: Settings = Depends(get_settings),
) -> dict:
    response = build_gp_lp_staging_response(payload, settings)
    if payload.get("save_result", True):
        storage_date = current_storage_date()
        vault_dir = resolve_vault_dir(settings.research_vault_dir)
        storage_key = normalize_ticker(response["fund_name"]) or "LP-REPORT"
        markdown = render_lp_report_staging_markdown(response, storage_date)
        storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=storage_key,
            report_type="lp-report-staging",
            markdown=markdown,
            structured_payload=response,
            manifest_entry={
                "summary": f"{response['fund_name']} LP 보고 스테이징",
                "fund_name": response["fund_name"],
                "valuation_method": response["valuation_method"],
                "lp_risk_flags": response["lp_risk_flags"],
                "source_confidence": 0.82,
                "tags": ["gp_package", "lp_report", "valuation_template", "workflow", "rag_connected"],
            },
            report_date=storage_date,
        )
        response["storage"] = storage
        response["rag_document"] = upsert_saved_workflow_rag_document(
            vault_dir=vault_dir,
            storage=storage,
            storage_key=storage_key,
            report_type="lp-report-staging",
            summary=f"{response['fund_name']} LP 보고 스테이징",
            markdown=markdown,
            tags=["gp_package", "lp_report", "valuation_template", "workflow"],
            source_confidence=0.82,
            metadata={
                "fund_name": response["fund_name"],
                "valuation_method": response["valuation_method"],
                "lp_risk_flags": response["lp_risk_flags"],
            },
        )
    return response


@app.post(
    "/api/v1/analysis/modules/sector-opportunity/run",
    dependencies=[Depends(verify_user_token)],
)
def run_sector_opportunity_finder(
    request: SectorOpportunityRequest,
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    금리, AI, 에너지 가격, 경기 국면 같은 매크로 입력을 바탕으로
    향후 기간 동안 상대적으로 유리한 섹터와 후보 기업을 제안합니다.
    """
    research_key = sector_research_key(request.region, request.style)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    macro_input = InjectedDataPoint(
        source_type="user_memo",
        label="macro_environment",
        value=request.macro_environment,
        as_of=current_storage_date().isoformat(),
        confidence=0.8,
    )
    analysis_input_data = [macro_input, *request.realtime_data]
    injected_data = analysis_input_data
    report = build_sector_opportunity_report(request, injected_data, settings, vault_dir)

    if request.save_result:
        storage_date = current_storage_date()
        report.storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=research_key,
            report_type="sector-opportunity",
            markdown=render_sector_opportunity_markdown(report, storage_date),
            structured_payload=report.model_dump(mode="json"),
            manifest_entry={
                "summary": report.macro_summary,
                "period": report.period,
                "region": report.region,
                "style": report.style,
                "top_sectors": [
                    item.model_dump(mode="json") for item in report.ranked_sectors[:3]
                ],
                "recommended_companies": [
                    item.model_dump(mode="json")
                    for item in report.recommended_companies
                ],
                "sector_trends": [
                    item.model_dump(mode="json") for item in report.sector_trends
                ],
                "sector_leaders": [
                    item.model_dump(mode="json") for item in report.sector_leaders[:10]
                ],
                "analyst_report": report.analyst_report,
                "watch_items": report.watch_items,
                "key_risks": report.key_risks,
            },
            report_date=storage_date,
        )

    return report.model_dump(mode="json")


@app.post(
    "/api/v1/analysis/modules/long-term-compounder/run",
    response_model=LongTermCompounderResponse,
    dependencies=[Depends(verify_user_token)],
)
def run_long_term_compounder_finder(
    request: LongTermCompounderRequest,
    settings: Settings = Depends(get_settings),
) -> LongTermCompounderResponse:
    """
    매출 성장, 마진, 경쟁 우위, 확장성, 시가총액 조건을 기준으로
    장기 복리 성장주 후보를 선별합니다.
    """
    research_key = compounder_research_key(request.region, request.sector, request.style)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    criteria_input = InjectedDataPoint(
        source_type="user_memo",
        label="screening_criteria",
        value=request.screening_criteria,
        as_of=current_storage_date().isoformat(),
        confidence=0.85,
    )
    analysis_input_data = collect_analysis_input_data(
        ticker=research_key,
        provided_data=[criteria_input, *request.realtime_data],
        auto_inject_data=request.auto_inject_data,
        settings=settings,
    )
    injected_data = collect_workspace_context(research_key, vault_dir, analysis_input_data)
    report = build_long_term_compounder_report(request, injected_data)

    if request.save_result:
        storage_date = current_storage_date()
        report.storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=research_key,
            report_type="long-term-compounder",
            markdown=render_long_term_compounder_markdown(report, storage_date),
            structured_payload=report.model_dump(mode="json"),
            manifest_entry={
                "summary": report.summary,
                "screening_criteria": report.screening_criteria,
                "region": report.region,
                "sector": report.sector,
                "style": report.style,
                "min_market_cap": report.min_market_cap,
                "max_market_cap": report.max_market_cap,
                "candidates": [
                    item.model_dump(mode="json") for item in report.candidates
                ],
                "next_actions": report.next_actions,
            },
            report_date=storage_date,
        )

    return report


@app.post(
    "/api/v1/analysis/team-report/run",
    response_model=TeamAnalysisResponse,
    dependencies=[Depends(verify_user_token)],
)
def run_collaborative_team_report(
    request: TeamAnalysisRequest,
    settings: Settings = Depends(get_settings),
) -> TeamAnalysisResponse:
    """
    7개 분석 스킬이 하나의 팀처럼 협업해 종목별 종합 분석 보고서를 생성합니다.

    현재는 오케스트레이션 계약과 저장 구조를 위한 구조화된 Mock 리포트입니다.
    이후 뉴스/데이터 수집기, 밸류에이션 엔진, 매매 전략 엔진, 복리 성장주 스크리너를
    각 스킬 contribution 생성 단계에 연결합니다.
    """
    ticker = ensure_verified_ticker(request.ticker)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    analysis_input_data = collect_analysis_input_data(
        ticker=ticker,
        provided_data=request.realtime_data,
        auto_inject_data=request.auto_inject_data,
        settings=settings,
    )
    injected_data = collect_workspace_context(ticker, vault_dir, analysis_input_data)
    contributions = build_skill_contributions(ticker, request, injected_data)
    institutional_context = summarize_institutional_flow_context(injected_data)
    dart_context = summarize_dart_filing_context(build_dart_filing_signal(ticker, settings))
    institutional_clause = (
        f" 기관 수급은 {institutional_context}를 보조 근거로 함께 검토합니다."
        if institutional_context
        else ""
    )
    dart_clause = (
        f" DART 신규 공시는 {dart_context}를 공식 근거로 함께 반영합니다."
        if dart_context
        else ""
    )
    focus = analysis_focus_for_ticker(ticker, request.focus_area)
    storage_date = current_storage_date()
    investment_thesis = build_investment_thesis(ticker, request, storage_date)
    watch_items = build_watch_items(ticker)
    conflicts = build_team_conflicts(ticker)

    report = TeamAnalysisResponse(
        ticker=ticker,
        investment_period=request.investment_period,
        region=request.region,
        style=request.style,
        focus_area=focus,
        executive_summary=(
            f"{ticker_company_name(ticker)}({ticker})에 대해 7개 분석 스킬이 협업하는 종합 투자 리포트를 생성했습니다. "
            f"핵심 초점은 {focus}이며, 투자 기간은 {request.investment_period}입니다."
        ),
        team_contributions=contributions,
        data_quality=estimate_data_quality(injected_data),
        synthesized_view=(
            "기관급 기업 분석, 실적 반응, 섹터 환경, 포트폴리오 리스크, 매매 전략, "
            "체크리스트 준비도, 장기 복리 가능성을 하나의 투자 논거로 통합합니다."
            f"{institutional_clause}{dart_clause}"
        ),
        consensus=build_team_consensus(ticker, injected_data),
        conflicts=conflicts,
        investment_thesis=investment_thesis,
        scenario_map=[
            "강세: 성장 동력과 섹터 수급이 동시에 강화되고 밸류에이션 프리미엄이 유지되는 경우",
            "기준: 실적과 가이던스가 컨센서스에 부합하며 주가가 기존 밸류에이션 밴드 안에서 움직이는 경우",
            "약세: 성장률 둔화, 마진 압박, 거시 할인율 상승, 기관 수급 이탈 또는 이벤트 리스크가 동시에 부각되는 경우",
        ],
        trade_plan=[
            "현재가와 최근 변동성 데이터를 주입하면 진입 구간, 손절, 목표가를 자동 보정",
            "손익비가 2:1 미만이면 신규 진입보다 관찰 목록 유지",
            "실적 발표 전후에는 포지션 사이즈를 축소하거나 시나리오별 대응 조건을 분리",
        ]
        if request.include_trade_setup
        else ["매매 전략 섹션은 요청에서 제외되었습니다."],
        compounder_notes=[
            "장기 복리 후보 여부는 매출 성장, 마진 품질, ROIC, 재투자 기회, 경쟁 우위 지속성으로 판단",
            "높은 밸류에이션은 장기 복리 논거를 부정하지 않지만 기대수익률의 출발점을 낮출 수 있음",
            "반복 매출, 가격 결정력, 낮은 자본집약도 여부를 후속 데이터로 확인",
        ]
        if request.include_compounder_screen
        else ["복리 성장주 스크리닝 섹션은 요청에서 제외되었습니다."],
        invalidation_conditions=investment_thesis.invalidation_conditions,
        watch_items=watch_items,
        next_actions=[
            *(
                ["국민연금/기관 수급 자료를 수급 보조 근거와 리스크 경고 단락에 반영하세요."]
                if institutional_context
                else []
            ),
            *(
                ["최근 DART 공시를 기준으로 강세/약세 논거와 무효화 조건을 업데이트하세요."]
                if dart_context
                else []
            ),
            "실시간 가격, 최근 실적 수치, 뉴스 요약을 추가 데이터로 주입해 리포트 업데이트",
            "저장된 이전 Markdown 분석과 새 보고서를 비교해 투자 논거 변화 추적",
            "체크리스트 미완료 항목을 우선 보강한 뒤 밸류에이션 범위를 재산정",
        ],
        injected_data=injected_data,
        saved_to_research_memory=request.save_result,
    )

    if request.save_result:
        report.storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=ticker,
            report_type="collaborative-team-report",
            markdown=render_team_analysis_markdown(report, storage_date),
            structured_payload=report.model_dump(mode="json"),
            manifest_entry=manifest_with_ticker_verification(ticker, {
                "summary": report.executive_summary,
                "data_quality": report.data_quality.data_quality,
                "source_confidence": report.data_quality.source_confidence,
                "source_count": len(report.injected_data),
                "consensus": report.consensus,
                "conflicts": [item.model_dump(mode="json") for item in report.conflicts],
                "investment_thesis": report.investment_thesis.model_dump(mode="json"),
                "watch_items": [item.model_dump(mode="json") for item in report.watch_items],
                "invalidation_conditions": report.invalidation_conditions,
            }),
            report_date=storage_date,
        )
        upsert_ticker_thesis_snapshot(
            vault_dir=vault_dir,
            ticker=ticker,
            company_name=ticker_company_name(ticker),
            investment_thesis=report.investment_thesis,
            watch_items=report.watch_items,
            source_entry={
                "type": "collaborative-team-report",
                "date": storage_date.isoformat(),
                "file_name": report.storage.file_name if report.storage else None,
                "relative_path": report.storage.relative_path
                if report.storage
                else None,
            },
            confidence=report.data_quality.source_confidence,
        )
        try:
            synthesize_and_save_dossier(ticker, settings, save_result=True)
        except Exception as exc:
            append_jsonl(
                user_state_dir(settings) / "dossier_refresh_errors.jsonl",
                {
                    "ticker": ticker,
                    "at": current_storage_timestamp(),
                    "source": "team_report",
                    "error": str(exc),
                },
            )

    return report


@app.post(
    "/api/v1/research/checklist/assess",
    response_model=ResearchChecklistAssessmentResponse,
    dependencies=[Depends(verify_user_token)],
)
def assess_research_checklist(
    request: ResearchChecklistRequest,
    settings: Settings = Depends(get_settings),
) -> ResearchChecklistAssessmentResponse:
    """
    16개 리서치 체크리스트의 체크 현황을 바탕으로 투자 준비도를 평가합니다.

    모바일 화면에서는 체크박스 변경 시 로컬 완료율 진행바를 즉시 갱신하고,
    사용자가 '완성된 항목 분석' 버튼을 누를 때 이 API를 호출합니다.
    """
    ticker = ensure_verified_ticker(request.ticker)
    vault_dir = resolve_vault_dir(settings.research_vault_dir)
    injected_data = collect_workspace_context(ticker, vault_dir, request.realtime_data)
    statuses = build_checklist_statuses(request.checked_items)
    completed_items = [item for item in statuses if item.completed]
    missing_items = [item for item in statuses if not item.completed]
    total_count = len(statuses)
    completed_count = len(completed_items)
    completion_rate = round(completed_count / total_count, 4)

    if completion_rate >= 0.85:
        readiness_level = "높음"
        readiness_summary = "투자 판단을 위한 핵심 리서치가 대부분 완료되었습니다. 이제 시나리오별 가격 범위와 무효화 조건을 정교화할 단계입니다."
    elif completion_rate >= 0.55:
        readiness_level = "보통"
        readiness_summary = "기본 리서치는 진행됐지만, 빠진 항목이 아직 투자 논거의 약점을 만들 수 있습니다."
    else:
        readiness_level = "낮음"
        readiness_summary = "아직 투자 판단보다 리서치 보강이 우선입니다. 사업, 재무, 리스크 항목을 먼저 채워야 합니다."

    next_steps = [
        f"{item.label} 항목을 보강"
        for item in missing_items[:3]
    ]
    if not next_steps:
        next_steps = [
            "강세/기준/약세 시나리오의 핵심 가정을 숫자로 정리",
            "매수 전 무효화 조건과 손절 기준을 확정",
            "다음 실적 발표 전 확인할 KPI를 알림으로 등록",
        ]

    assessment = ResearchChecklistAssessmentResponse(
        ticker=ticker,
        completed_count=completed_count,
        total_count=total_count,
        completion_rate=completion_rate,
        readiness_level=readiness_level,
        readiness_summary=readiness_summary,
        completed_items=completed_items,
        missing_items=missing_items,
        next_steps=next_steps,
        injected_data=injected_data,
        saved_to_research_memory=request.save_result,
    )

    if request.save_result:
        storage_date = current_storage_date()
        assessment.storage = save_research_markdown(
            vault_dir=vault_dir,
            ticker=ticker,
            report_type="research-checklist",
            markdown=render_checklist_markdown(assessment, storage_date),
            structured_payload=assessment.model_dump(mode="json"),
            manifest_entry=manifest_with_ticker_verification(ticker, {
                "summary": assessment.readiness_summary,
                "completion_rate": assessment.completion_rate,
                "readiness_level": assessment.readiness_level,
                "source_count": len(assessment.injected_data),
                "next_steps": assessment.next_steps,
            }),
            report_date=storage_date,
        )

    return assessment




@app.on_event("startup")
def start_background_schedulers() -> None:
    start_earnings_calendar_scheduler()
    start_dart_filing_scheduler()
    start_shinhan_research_scheduler()
    start_naver_research_scheduler()
