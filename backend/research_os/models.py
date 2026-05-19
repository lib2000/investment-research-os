from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from research_os.research_memory import ResearchStorageInfo


class Broker(str, Enum):
    KIWOOM = "KIWOOM"
    KIS = "KIS"


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    ETC = "ETC"


class NormalizedTrade(BaseModel):
    trade_id: str
    broker: Broker
    market: str
    ticker: str
    name: str
    side: TradeSide
    order_type: OrderType = OrderType.ETC
    trade_date: str
    trade_time: str
    price: float
    quantity: float
    gross_amount: float
    fee: float = 0
    tax: float = 0
    currency: str = "KRW"
    source_order_id: Optional[str] = None
    source_execution_id: Optional[str] = None
    raw_hash: Optional[str] = None
    strategy: Optional[str] = None
    journal_required: bool = True


class TradesResponse(BaseModel):
    status: str = "success"
    data: List[NormalizedTrade]


class BrokerStatus(BaseModel):
    default_broker: Broker
    first_integration_target: Broker
    adapters_ready: List[Broker]
    message: str


class TickerVerificationResponse(BaseModel):
    status: str = "success"
    requested_symbol: str
    official_symbol: str
    company_name: str
    exchange: str
    country: str = "US"
    asset_type: str = "equity"
    verified: bool
    verification_source: str
    message: str


class TickerProfileResponse(BaseModel):
    status: str = "success"
    ticker: str
    company_name: str
    exchange: str
    country: str = "US"
    asset_type: str = "equity"
    sector: Optional[str] = None
    industry: Optional[str] = None
    business_context: Optional[str] = None
    analysis_focus: Optional[str] = None
    watch_kpis: List[str] = Field(default_factory=list)
    data_limitations: List[str] = Field(default_factory=list)
    latest_reported_quarter: Optional[str] = None
    latest_reported_earnings_date: Optional[str] = None
    previous_earnings_date: Optional[str] = None
    next_earnings_date: Optional[str] = None
    earnings_calendar_source: Optional[str] = None
    latest_earnings_profile: dict = Field(default_factory=dict)
    verification: TickerVerificationResponse


class AnalysisModule(str, Enum):
    INSTITUTIONAL_STOCK_BREAKDOWN = "institutional_stock_breakdown"
    SMART_TRADE_SETUP = "smart_trade_setup"
    EARNINGS_REACTION = "earnings_reaction"
    PORTFOLIO_RISK_SCAN = "portfolio_risk_scan"
    SECTOR_OPPORTUNITY = "sector_opportunity"
    INVESTOR_RESEARCH_CHECKLIST = "investor_research_checklist"
    LONG_TERM_COMPOUNDER = "long_term_compounder"
    REINFORCEMENT_PORTFOLIO_OPTIMIZER = "reinforcement_portfolio_optimizer"


class DataSourceType(str, Enum):
    OFFICIAL_FILING = "official_filing"
    EARNINGS_RELEASE = "earnings_release"
    IR_PRESENTATION = "ir_presentation"
    MARKET_PRICE = "market_price"
    FINANCIAL_DATA = "financial_data"
    NEWS = "news"
    ANALYST_REPORT = "analyst_report"
    USER_MEMO = "user_memo"
    RESEARCH_MEMORY = "research_memory"
    OTHER = "other"


class InjectedDataPoint(BaseModel):
    source_type: DataSourceType | str
    label: str
    value: str
    as_of: Optional[str] = None
    source_url: Optional[str] = None
    confidence: float = 1.0


class DataQualitySummary(BaseModel):
    data_quality: str
    source_confidence: float
    stale_data_warning: bool = False
    missing_data: List[str] = Field(default_factory=list)


class WatchItem(BaseModel):
    ticker: str
    metric: str
    condition: str
    action: str
    priority: str = "medium"


class InvestmentThesis(BaseModel):
    ticker: str
    thesis: str
    time_horizon: str
    bull_triggers: List[str] = Field(default_factory=list)
    bear_triggers: List[str] = Field(default_factory=list)
    invalidation_conditions: List[str] = Field(default_factory=list)
    watch_kpis: List[str] = Field(default_factory=list)
    valuation_assumptions: dict = Field(default_factory=dict)
    last_updated: str


class TeamConflict(BaseModel):
    topic: str
    positive_view: str
    caution_view: str
    resolution: str
    severity: str = "medium"


class InstitutionalAnalysisRequest(BaseModel):
    ticker: str
    investment_period: str = "3 years"
    focus_area: Optional[str] = None
    auto_run: bool = True
    auto_inject_data: bool = True
    realtime_data: List[InjectedDataPoint] = Field(default_factory=list)
    save_result: bool = True


class ScenarioSummary(BaseModel):
    title: str
    thesis: str
    watch_items: List[str]


class PriceLevel(BaseModel):
    label: str
    price: float
    rationale: str


class TradeTarget(BaseModel):
    label: str
    price: float
    reward_pct: float
    risk_reward: float
    action: str


class SmartTradeSetupRequest(BaseModel):
    ticker: str
    current_price: float
    style: str = "swing"
    risk_tolerance: str = "보통"
    portfolio_size: Optional[float] = None
    risk_per_trade_pct: float = 0.01
    market_structure: Optional[str] = None
    auto_inject_data: bool = True
    realtime_data: List[InjectedDataPoint] = Field(default_factory=list)
    save_result: bool = True


class SmartTradeSetupResponse(BaseModel):
    status: str = "success"
    module: AnalysisModule = AnalysisModule.SMART_TRADE_SETUP
    persona: str = "헤지펀드 포트폴리오 매니저"
    ticker: str
    current_price: float
    style: str
    risk_tolerance: str
    market_structure: str
    entry_zone: List[PriceLevel]
    stop_loss: PriceLevel
    targets: List[TradeTarget]
    risk_per_share: float
    risk_per_trade_pct: float
    max_position_value: Optional[float] = None
    portfolio_size: Optional[float] = None
    position_sizing_guidance: str
    setup_quality: str
    trade_plan: List[str]
    invalidation_conditions: List[str]
    next_actions: List[str]
    injected_data: List[InjectedDataPoint] = Field(default_factory=list)
    saved_to_research_memory: bool = True
    storage: Optional[ResearchStorageInfo] = None


class EarningsMetric(BaseModel):
    name: str
    reported: Optional[float | str] = None
    expected: Optional[float | str] = None
    surprise: Optional[str] = None
    interpretation: str


class EarningsReactionRequest(BaseModel):
    ticker: str
    quarter: str
    official_latest_quarter: Optional[str] = None
    official_latest_earnings_report_date: Optional[str] = None
    earnings_calendar_source: Optional[str] = None
    earnings_reference_status: str = "확인 필요"
    earnings_report_date: Optional[str] = None
    price_reaction: str = ""
    previous_earnings_date: Optional[str] = None
    previous_earnings_summary: Optional[str] = None
    next_earnings_date: Optional[str] = None
    next_earnings_guidance: Optional[str] = None
    eps_reported: Optional[float] = None
    eps_expected: Optional[float] = None
    revenue_reported: Optional[float] = None
    revenue_expected: Optional[float] = None
    guidance_change: str = "유지"
    key_numbers: dict = Field(default_factory=dict)
    management_tone: Optional[str] = None
    market_context: Optional[str] = None
    auto_inject_data: bool = True
    realtime_data: List[InjectedDataPoint] = Field(default_factory=list)
    save_result: bool = True


class EarningsReactionResponse(BaseModel):
    status: str = "success"
    module: AnalysisModule = AnalysisModule.EARNINGS_REACTION
    persona: str = "Buy-Side 리서치 전문가"
    ticker: str
    quarter: str
    official_latest_quarter: Optional[str] = None
    official_latest_earnings_report_date: Optional[str] = None
    earnings_calendar_source: Optional[str] = None
    earnings_reference_status: str = "확인 필요"
    earnings_report_date: Optional[str] = None
    price_reaction: str
    previous_earnings_date: Optional[str] = None
    previous_earnings_key_takeaways: List[str] = Field(default_factory=list)
    next_earnings_date: Optional[str] = None
    next_earnings_guidance: str
    reaction_type: str
    headline_assessment: str
    sentiment_shift: str
    guidance_assessment: str
    evidence_status: str = "확인 필요"
    missing_inputs: List[str] = Field(default_factory=list)
    metrics: List[EarningsMetric] = Field(default_factory=list)
    market_reaction_pattern: str
    watch_before_next_earnings: List[str] = Field(default_factory=list)
    thesis_implications: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    injected_data: List[InjectedDataPoint] = Field(default_factory=list)
    saved_to_research_memory: bool = True
    storage: Optional[ResearchStorageInfo] = None


class SectorOpportunity(BaseModel):
    sector: str
    score: int
    rationale: str
    macro_tailwinds: List[str] = Field(default_factory=list)
    key_risks: List[str] = Field(default_factory=list)
    preferred_tickers: List[str] = Field(default_factory=list)


class SectorCompanyCandidate(BaseModel):
    ticker: str
    company_name: str
    sector: str
    thesis: str
    catalysts: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    fit_score: int


class SectorPeerComparison(BaseModel):
    ticker: str
    company_name: str
    sector: str
    role: str
    strengths: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    fit_score: int


class SectorLeaderCandidate(BaseModel):
    ticker: str
    company_name: str
    sector: str
    source: str = "system"
    leader_score: int
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    unrealized_return: Optional[float] = None
    target_upside: Optional[float] = None
    research_memory_count: int = 0
    thesis: str
    catalysts: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    next_checkpoints: List[str] = Field(default_factory=list)


class SectorTrendInsight(BaseModel):
    sector: str
    flow_score: int
    trend_label: str
    market_flow: str
    investment_solution: str
    leader_tickers: List[str] = Field(default_factory=list)
    leader_companies: List[SectorLeaderCandidate] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    next_checkpoints: List[str] = Field(default_factory=list)


class SectorOpportunityRequest(BaseModel):
    macro_environment: str
    period: str = "6개월"
    region: str = "US"
    style: str = "균형형"
    focus_theme: Optional[str] = None
    auto_inject_data: bool = True
    realtime_data: List[InjectedDataPoint] = Field(default_factory=list)
    save_result: bool = True


class SectorOpportunityResponse(BaseModel):
    status: str = "success"
    module: AnalysisModule = AnalysisModule.SECTOR_OPPORTUNITY
    persona: str = "매크로 전략가"
    research_key: str
    macro_environment: str
    period: str
    region: str
    style: str
    focus_theme: Optional[str] = None
    macro_summary: str
    industry_overview: List[str] = Field(default_factory=list)
    competitive_landscape: List[str] = Field(default_factory=list)
    peer_comparison: List[SectorPeerComparison] = Field(default_factory=list)
    idea_shortlist: List[SectorCompanyCandidate] = Field(default_factory=list)
    ranked_sectors: List[SectorOpportunity] = Field(default_factory=list)
    recommended_companies: List[SectorCompanyCandidate] = Field(default_factory=list)
    sector_trends: List[SectorTrendInsight] = Field(default_factory=list)
    sector_leaders: List[SectorLeaderCandidate] = Field(default_factory=list)
    analyst_report: List[str] = Field(default_factory=list)
    allocation_view: str
    watch_items: List[str] = Field(default_factory=list)
    key_risks: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    injected_data: List[InjectedDataPoint] = Field(default_factory=list)
    saved_to_research_memory: bool = True
    storage: Optional[ResearchStorageInfo] = None


class CompounderCandidate(BaseModel):
    ticker: str
    company_name: str
    sector: str
    market_cap: float
    revenue_growth: float
    gross_margin: float
    free_cash_flow_margin: float
    moat_score: int
    scalability_score: int
    compounder_score: int
    thesis: str
    reinvestment_runway: str
    key_risks: List[str] = Field(default_factory=list)
    watch_kpis: List[str] = Field(default_factory=list)


class LongTermCompounderRequest(BaseModel):
    screening_criteria: str
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    sector: str = "전체"
    region: str = "US"
    style: str = "퀄리티 성장"
    auto_inject_data: bool = True
    realtime_data: List[InjectedDataPoint] = Field(default_factory=list)
    save_result: bool = True


class LongTermCompounderResponse(BaseModel):
    status: str = "success"
    module: AnalysisModule = AnalysisModule.LONG_TERM_COMPOUNDER
    persona: str = "Fundsmith/Baillie Gifford 스타일 성장주 투자자"
    research_key: str
    screening_criteria: str
    min_market_cap: Optional[float] = None
    max_market_cap: Optional[float] = None
    sector: str
    region: str
    style: str
    summary: str
    candidates: List[CompounderCandidate] = Field(default_factory=list)
    rejected_reasons: List[str] = Field(default_factory=list)
    portfolio_construction_notes: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    injected_data: List[InjectedDataPoint] = Field(default_factory=list)
    saved_to_research_memory: bool = True
    storage: Optional[ResearchStorageInfo] = None


class InstitutionalAnalysisResponse(BaseModel):
    status: str = "success"
    module: AnalysisModule = AnalysisModule.INSTITUTIONAL_STOCK_BREAKDOWN
    persona: str = "Goldman Sachs analyst"
    ticker: str
    investment_period: str
    focus_area: Optional[str] = None
    executive_summary: str
    bull_case: ScenarioSummary
    base_case: ScenarioSummary
    bear_case: ScenarioSummary
    key_risks: List[str]
    next_actions: List[str]
    injected_data: List[InjectedDataPoint] = Field(default_factory=list)
    saved_to_research_memory: bool = True
    storage: Optional[ResearchStorageInfo] = None


class ChecklistItemStatus(BaseModel):
    key: str
    label: str
    completed: bool


class ResearchChecklistRequest(BaseModel):
    ticker: str
    checked_items: List[str]
    notes: Optional[str] = None
    realtime_data: List[InjectedDataPoint] = Field(default_factory=list)
    save_result: bool = True


class ResearchChecklistAssessmentResponse(BaseModel):
    status: str = "success"
    module: AnalysisModule = AnalysisModule.INVESTOR_RESEARCH_CHECKLIST
    persona: str = "체계적 투자 리서치 전문가"
    ticker: str
    completed_count: int
    total_count: int
    completion_rate: float
    readiness_level: str
    readiness_summary: str
    completed_items: List[ChecklistItemStatus]
    missing_items: List[ChecklistItemStatus]
    next_steps: List[str]
    injected_data: List[InjectedDataPoint] = Field(default_factory=list)
    saved_to_research_memory: bool = True
    storage: Optional[ResearchStorageInfo] = None


class ResearchMemoryFile(BaseModel):
    file_name: str
    relative_path: str
    absolute_path: str
    json_file_name: Optional[str] = None
    json_relative_path: Optional[str] = None
    modified_at: str
    report_type: Optional[str] = None
    summary: Optional[str] = None
    verified: bool = False
    legacy: bool = True
    status_label: str = "레거시"
    tags: List[str] = Field(default_factory=list)
    source_url_processing: Optional[dict] = None
    capture_quality: Optional[dict] = None
    data_quality_status: Optional[str] = None
    needs_body_copy: bool = False
    url_text_unavailable: bool = False
    attachment: Optional[dict] = None
    archived: bool = False
    is_deleted: bool = False
    archived_at: Optional[str] = None
    archive_reason: Optional[str] = None


class ResearchMemoryListResponse(BaseModel):
    status: str = "success"
    ticker: str
    files: List[ResearchMemoryFile]
    manifest_entries: List[dict] = Field(default_factory=list)
    verified_file_count: int = 0
    legacy_file_count: int = 0
    archived_file_count: int = 0
    include_archived: bool = False
    legacy_policy: Optional[dict] = None
    data_warnings: List[str] = Field(default_factory=list)


class ResearchMemoryContentResponse(BaseModel):
    status: str = "success"
    ticker: str
    file_name: str
    relative_path: str
    content: str
    modified_at: str
    json_payload: Optional[dict] = None
    report_type: Optional[str] = None
    summary: Optional[str] = None
    verified: bool = False
    legacy: bool = True
    status_label: str = "레거시"
    tags: List[str] = Field(default_factory=list)
    source_url_processing: Optional[dict] = None
    capture_quality: Optional[dict] = None
    data_quality_status: Optional[str] = None
    needs_body_copy: bool = False
    url_text_unavailable: bool = False
    attachment: Optional[dict] = None
    archived: bool = False
    is_deleted: bool = False
    archived_at: Optional[str] = None
    archive_reason: Optional[str] = None


class ResearchManifestResponse(BaseModel):
    status: str = "success"
    entries: List[dict] = Field(default_factory=list)


class DashboardReportSummary(BaseModel):
    type: str
    file_name: str
    relative_path: str
    date: str
    summary: Optional[str] = None
    impact_label: Optional[str] = None
    impact_reason: Optional[str] = None
    tooltip: Optional[str] = None


class DashboardMetric(BaseModel):
    label: str
    value: str
    tone: str = "neutral"


class TickerDashboardResponse(BaseModel):
    status: str = "success"
    module: str = "ticker_dashboard"
    ticker: str
    file_count: int
    verified_report_count: int = 0
    legacy_report_count: int = 0
    data_warnings: List[str] = Field(default_factory=list)
    ticker_verification: Optional[TickerVerificationResponse] = None
    ticker_profile: Optional[TickerProfileResponse] = None
    report_count_by_type: dict[str, int] = Field(default_factory=dict)
    latest_reports: List[DashboardReportSummary] = Field(default_factory=list)
    checklist_completion_rate: Optional[float] = None
    checklist_readiness: Optional[str] = None
    latest_thesis_summary: Optional[str] = None
    latest_capture_summary: Optional[str] = None
    latest_trade_setup_summary: Optional[str] = None
    latest_earnings_summary: Optional[str] = None
    latest_automation_summary: Optional[DashboardReportSummary] = None
    latest_thesis_snapshot: dict = Field(default_factory=dict)
    latest_earnings_reference: dict = Field(default_factory=dict)
    nps_institutional_signal: dict = Field(default_factory=dict)
    dart_filing_signal: dict = Field(default_factory=dict)
    latest_customs_trade_reference: dict = Field(default_factory=dict)
    latest_dossier_preview: dict = Field(default_factory=dict)
    latest_market_journal_reference: dict = Field(default_factory=dict)
    document_quality_digest: dict = Field(default_factory=dict)
    today_priority_brief: dict = Field(default_factory=dict)
    automation_digest: dict = Field(default_factory=dict)
    open_watch_items: List[str] = Field(default_factory=list)
    recommended_next_actions: List[str] = Field(default_factory=list)
    module_status: List[DashboardMetric] = Field(default_factory=list)


class InvestmentThesisListResponse(BaseModel):
    status: str = "success"
    ticker: str
    theses: List[InvestmentThesis] = Field(default_factory=list)
    watch_items: List[WatchItem] = Field(default_factory=list)


class ThesisImpact(str, Enum):
    STRENGTHENS = "강화"
    WEAKENS = "약화"
    MIXED = "혼합"
    NEUTRAL = "중립"
    INSUFFICIENT_DATA = "데이터 부족"


class ThesisImpactRequest(BaseModel):
    ticker: str
    new_data: List[InjectedDataPoint]
    user_question: Optional[str] = None
    save_result: bool = True


class ThesisImpactFinding(BaseModel):
    impact: ThesisImpact
    thesis_reference: str
    evidence: List[str] = Field(default_factory=list)
    reasoning: str
    confidence: float


class WatchItemSignal(BaseModel):
    metric: str
    matched: bool
    signal: str
    action: str
    priority: str


class ThesisImpactResponse(BaseModel):
    status: str = "success"
    module: str = "thesis_impact_analyzer"
    ticker: str
    overall_impact: ThesisImpact
    summary: str
    findings: List[ThesisImpactFinding] = Field(default_factory=list)
    watch_item_signals: List[WatchItemSignal] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    source_count: int
    saved_to_research_memory: bool = True
    storage: Optional[ResearchStorageInfo] = None


class ResearchCaptureRequest(BaseModel):
    ticker: str
    title: str
    raw_content: str
    source_type: DataSourceType | str = DataSourceType.USER_MEMO
    source_url: Optional[str] = None
    as_of: Optional[str] = None
    confidence: float = 0.8
    tags: List[str] = Field(default_factory=list)
    run_thesis_impact: bool = True
    save_result: bool = True


class ResearchMemorySupplementRequest(BaseModel):
    body_text: str = Field(..., min_length=1, max_length=200000)
    note: Optional[str] = None


class ResearchMemoryArchiveRequest(BaseModel):
    archived: bool = True
    reason: Optional[str] = None


class AutoResearchCaptureRequest(BaseModel):
    raw_content: str
    source_url: Optional[str] = None
    file_name: Optional[str] = None
    file_mime_type: Optional[str] = None
    file_size: Optional[int] = None
    file_content_base64: Optional[str] = None
    run_thesis_impact: bool = True
    save_result: bool = True


class CapturedResearchItem(BaseModel):
    ticker: str
    title: str
    summary: str
    source_type: DataSourceType | str
    source_url: Optional[str] = None
    as_of: Optional[str] = None
    confidence: float
    tags: List[str] = Field(default_factory=list)


class ResearchCaptureResponse(BaseModel):
    status: str = "success"
    module: str = "research_quick_capture"
    captured_item: CapturedResearchItem
    linked_impact: Optional[ThesisImpactResponse] = None
    saved_to_research_memory: bool = True
    storage: Optional[ResearchStorageInfo] = None
    attachment: Optional[dict] = None
    source_url_processing: Optional[dict] = None
    capture_quality: Optional[dict] = None
    input_preview: Optional[str] = None
    document_preview: Optional[str] = None
    duplicate_check: Optional[dict] = None
    rag_document: Optional[dict] = None


class PortfolioHolding(BaseModel):
    ticker: str
    name: Optional[str] = None
    quantity: Optional[float] = None
    average_cost: Optional[float] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    cost_basis: Optional[float] = None
    unrealized_gain: Optional[float] = None
    unrealized_return: Optional[float] = None
    price_source: Optional[str] = None
    price_refresh_status: Optional[str] = None
    price_checked_at: Optional[str] = None
    weight: Optional[float] = None
    sector: str = "Unknown"
    theme_tags: List[str] = Field(default_factory=list)
    currency: str = "USD"


class PortfolioRiskScanRequest(BaseModel):
    portfolio_name: str = "default"
    holdings: List[PortfolioHolding] = Field(default_factory=list)
    portfolio_value: Optional[float] = None
    max_single_position_weight: float = 0.2
    max_sector_weight: float = 0.35
    max_theme_weight: float = 0.4
    save_result: bool = True


class PortfolioSaveRequest(BaseModel):
    portfolio_name: str = "default"
    holdings: List[PortfolioHolding] = Field(default_factory=list)
    portfolio_value: Optional[float] = None
    max_single_position_weight: float = 0.2
    max_sector_weight: float = 0.35
    max_theme_weight: float = 0.4
    notes: Optional[str] = None


class SavedPortfolio(BaseModel):
    portfolio_name: str
    holdings: List[PortfolioHolding] = Field(default_factory=list)
    portfolio_value: Optional[float] = None
    max_single_position_weight: float = 0.2
    max_sector_weight: float = 0.35
    max_theme_weight: float = 0.4
    notes: Optional[str] = None
    holding_count: int = 0
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class PortfolioStoreResponse(BaseModel):
    status: str = "success"
    module: str = "portfolio_store"
    portfolios: List[SavedPortfolio] = Field(default_factory=list)
    active_portfolio: Optional[SavedPortfolio] = None
    storage_path: Optional[str] = None


class PolicyAllocationAdjustment(BaseModel):
    ticker: str
    current_weight: float
    suggested_weight: float
    action: str
    rationale: str


class ReinforcementPortfolioOptimizationRequest(BaseModel):
    portfolio_name: str = "default"
    holdings: List[PortfolioHolding] = Field(default_factory=list)
    market_state: str = ""
    objective: str = "risk_adjusted_return"
    risk_profile: str = "balanced"
    learning_horizon_days: int = 90
    max_position_weight: float = 0.2
    save_result: bool = True


class ReinforcementPortfolioOptimizationResponse(BaseModel):
    status: str = "success"
    module: AnalysisModule = AnalysisModule.REINFORCEMENT_PORTFOLIO_OPTIMIZER
    portfolio_name: str
    objective: str
    risk_profile: str
    learning_mode: str
    state_features: List[str] = Field(default_factory=list)
    action_space: List[str] = Field(default_factory=list)
    reward_function: List[str] = Field(default_factory=list)
    learned_policy_summary: str
    allocation_adjustments: List[PolicyAllocationAdjustment] = Field(default_factory=list)
    risk_guardrails: List[str] = Field(default_factory=list)
    next_training_data_needed: List[str] = Field(default_factory=list)
    saved_to_research_memory: bool = True
    storage: Optional[ResearchStorageInfo] = None


class PortfolioImportRequest(BaseModel):
    file_name: str
    content_base64: str


class PortfolioImportResponse(BaseModel):
    status: str = "success"
    module: str = "portfolio_import"
    file_name: str
    imported_holdings: List[PortfolioHolding] = Field(default_factory=list)
    raw_rows: int = 0
    warnings: List[str] = Field(default_factory=list)


class InterestTicker(BaseModel):
    ticker: str
    priority: str = "medium"
    thesis: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    verification: Optional[TickerVerificationResponse] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class InterestSector(BaseModel):
    name: str
    region: str = "US"
    priority: str = "medium"
    thesis: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    attachment: Optional[dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class InterestListUpdateRequest(BaseModel):
    tickers: List[InterestTicker] = Field(default_factory=list)
    sectors: List[InterestSector] = Field(default_factory=list)


class InterestListResponse(BaseModel):
    status: str = "success"
    module: str = "interest_list"
    tickers: List[InterestTicker] = Field(default_factory=list)
    sectors: List[InterestSector] = Field(default_factory=list)
    updated_at: Optional[str] = None
    storage_path: Optional[str] = None


class MarketCloseReviewRequest(BaseModel):
    market: str = "US"
    session_date: Optional[str] = None
    raw_summary: str = ""
    source_url: Optional[str] = None
    file_name: Optional[str] = None
    file_mime_type: Optional[str] = None
    file_size: Optional[int] = None
    file_content_base64: Optional[str] = None
    save_result: bool = True


class MarketCloseEntry(BaseModel):
    entry_id: str
    market: str
    session_date: str
    raw_summary: str
    sentiment: str
    risk_level: str
    regime: str
    auto_utilization_focus: List[str] = Field(default_factory=list)
    interest_implications: List[str] = Field(default_factory=list)
    market_index_snapshot: List[str] = Field(default_factory=list)
    key_drivers: List[str] = Field(default_factory=list)
    sector_implications: List[str] = Field(default_factory=list)
    portfolio_actions: List[str] = Field(default_factory=list)
    next_session_watch: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    attachment: Optional[dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class MarketCloseReviewResponse(BaseModel):
    status: str = "success"
    module: str = "market_close_review"
    entry: MarketCloseEntry
    history_count: int = 0
    cumulative_patterns: List[str] = Field(default_factory=list)
    recent_regime_summary: str
    storage_path: Optional[str] = None
    saved_to_research_memory: bool = True
    storage: Optional[ResearchStorageInfo] = None
    attachment: Optional[dict] = None
    source_url_processing: Optional[dict] = None
    capture_quality: Optional[dict] = None


class MarketCloseHistoryResponse(BaseModel):
    status: str = "success"
    module: str = "market_close_history"
    market: str = "ALL"
    entries: List[MarketCloseEntry] = Field(default_factory=list)
    storage_path: Optional[str] = None


class ConcentrationItem(BaseModel):
    name: str
    weight: float
    market_value: float


class PortfolioRiskWarning(BaseModel):
    type: str
    severity: str
    message: str
    action: str


class PortfolioRiskScanResponse(BaseModel):
    status: str = "success"
    module: AnalysisModule = AnalysisModule.PORTFOLIO_RISK_SCAN
    portfolio_name: str
    portfolio_value: float
    holdings: List[PortfolioHolding]
    single_position_concentration: List[ConcentrationItem]
    sector_concentration: List[ConcentrationItem]
    theme_concentration: List[ConcentrationItem]
    top_five_weight: float
    risk_score: int
    warnings: List[PortfolioRiskWarning] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)
    saved_to_research_memory: bool = True
    storage: Optional[ResearchStorageInfo] = None


class TeamAnalysisRequest(BaseModel):
    ticker: str
    investment_period: str = "3 years"
    region: str = "US"
    style: str = "balanced"
    focus_area: Optional[str] = None
    include_trade_setup: bool = True
    include_compounder_screen: bool = True
    auto_inject_data: bool = True
    realtime_data: List[InjectedDataPoint] = Field(default_factory=list)
    save_result: bool = True


class SkillContribution(BaseModel):
    skill_id: int
    skill_name: str
    persona: str
    role: str
    summary: str
    key_outputs: List[str]
    confidence: float


class TeamAnalysisResponse(BaseModel):
    status: str = "success"
    module: str = "collaborative_research_team"
    ticker: str
    investment_period: str
    region: str
    style: str
    focus_area: Optional[str] = None
    executive_summary: str
    team_contributions: List[SkillContribution]
    data_quality: DataQualitySummary
    synthesized_view: str
    consensus: List[str]
    conflicts: List[TeamConflict]
    investment_thesis: InvestmentThesis
    scenario_map: List[str]
    trade_plan: List[str]
    compounder_notes: List[str]
    invalidation_conditions: List[str]
    watch_items: List[WatchItem]
    next_actions: List[str]
    injected_data: List[InjectedDataPoint] = Field(default_factory=list)
    saved_to_research_memory: bool = True
    storage: Optional[ResearchStorageInfo] = None
