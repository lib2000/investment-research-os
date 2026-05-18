from pydantic import BaseModel, Field

from app.kiwoom_balance import KiwoomBalanceSummary, KiwoomHolding
from app.kiwoom_order_execution import KiwoomOrderExecution
from app.kiwoom_trade_journal import (
    KiwoomTradeJournalItem,
    KiwoomTradeJournalSummary,
)


class PortfolioResponse(BaseModel):
    status: str = "success"
    broker: str
    synced_from: str
    summary: KiwoomBalanceSummary
    holdings_count: int
    holdings: list[KiwoomHolding]
    has_next: bool = False
    return_code: int | None = None
    return_msg: str | None = None


class JournalSourceTradesResponse(BaseModel):
    status: str = "success"
    broker: str
    synced_from: list[str]
    base_date: str
    trade_summary: KiwoomTradeJournalSummary
    trade_journal_items_count: int
    trade_journal_items: list[KiwoomTradeJournalItem]
    order_executions_count: int
    order_executions: list[KiwoomOrderExecution]
    needs_review_count: int
    has_next: bool = False
    return_code: int | None = None
    return_msg: str | None = None


class SyncRunResponse(BaseModel):
    status: str
    sync_run_id: int
    broker: str
    portfolio_holdings_count: int
    journal_items_count: int
    order_executions_count: int
    needs_review_count: int


class HistoricalSyncDayResult(BaseModel):
    date: str
    sync_run_id: int
    journal_items_count: int
    order_executions_count: int
    needs_review_count: int
    has_next: bool = False


class HistoricalSyncResponse(BaseModel):
    status: str
    broker: str
    start_date: str
    end_date: str
    days_requested: int
    days_synced: int
    total_journal_items_count: int
    total_order_executions_count: int
    total_needs_review_count: int
    results: list[HistoricalSyncDayResult]


class HistoricalSyncJobResponse(BaseModel):
    status: str
    job: dict


class LatestSyncResponse(BaseModel):
    status: str = "success"
    sync_run: dict | None


class JournalDraftsResponse(BaseModel):
    status: str = "success"
    drafts_count: int
    drafts: list[dict]
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 0
    has_next: bool = False
    has_previous: bool = False


class JournalEntryCreateRequest(BaseModel):
    draft_id: int
    strategy_name: str = ""
    setup_tags: list[str] = Field(default_factory=list)
    entry_reason: str = ""
    exit_reason: str = ""
    rule_followed: bool | None = None
    good_points: str = ""
    improvement_points: str = ""
    memo: str = ""
    manual_profit_loss_amount: int | None = None
    manual_profit_rate: float | None = None
    manual_buy_amount: int | None = None
    manual_sell_amount: int | None = None
    planned_entry_price: float | None = None
    actual_entry_price: float | None = None
    stop_loss_price: float | None = None
    target_price: float | None = None
    exit_price: float | None = None
    planned_risk_amount: int | None = None
    realized_r_multiple: float | None = None


class JournalEntryResponse(BaseModel):
    status: str = "success"
    entry: dict


class JournalEntriesResponse(BaseModel):
    status: str = "success"
    entries_count: int
    entries: list[dict]
    total: int = 0
    page: int = 1
    page_size: int = 50
    total_pages: int = 0
    has_next: bool = False
    has_previous: bool = False


class ManualTransactionCreateRequest(BaseModel):
    trade_date: str
    broker: str = "MANUAL"
    account_name: str = "기타"
    transaction_type: str = "trade"
    ticker: str = ""
    name: str = ""
    quantity: float | None = None
    price: float | None = None
    buy_amount: int | None = None
    sell_amount: int | None = None
    profit_loss_amount: int | None = None
    dividend_amount: int | None = None
    tax_amount: int | None = None
    commission_amount: int | None = None
    currency: str = "KRW"
    fx_rate_krw: float | None = None
    split_adjustment_ratio: float = 1.0
    adjustment_note: str = ""
    memo: str = ""


class ManualTransactionResponse(BaseModel):
    status: str = "success"
    transaction: dict


class ManualTransactionsResponse(BaseModel):
    status: str = "success"
    transactions_count: int
    transactions: list[dict]
    total: int = 0
    page: int = 1
    page_size: int = 100
    total_pages: int = 0
    has_next: bool = False
    has_previous: bool = False


class ManualTransactionsImportResponse(BaseModel):
    status: str = "success"
    file_name: str
    total_rows: int
    imported_count: int
    failed_count: int
    skipped_count: int
    transactions: list[dict]
    errors: list[dict]


class FxRateCreateRequest(BaseModel):
    currency: str
    rate_date: str
    fx_rate_krw: float
    source: str = "manual"


class FxRateResponse(BaseModel):
    status: str = "success"
    fx_rate: dict


class CorporateActionCreateRequest(BaseModel):
    ticker: str
    action_type: str = "split"
    effective_date: str
    adjustment_ratio: float
    source: str = "manual"
    memo: str = ""


class CorporateActionResponse(BaseModel):
    status: str = "success"
    corporate_action: dict


class JournalAnalyticsResponse(BaseModel):
    status: str = "success"
    filter_start_date: str | None = None
    filter_end_date: str | None = None
    total_entries: int
    completed_drafts: int
    pending_drafts: int
    rule_followed_count: int
    rule_broken_count: int
    rule_unknown_count: int
    rule_follow_rate: float | None
    top_tickers: list[dict]
    realized_profit_loss_total: int
    gross_profit_total: int
    gross_loss_total: int
    profit_factor: float | None
    expectancy_per_trade: float | None
    planned_risk_amount_total: int
    total_r_multiple: float
    average_r_multiple: float | None
    best_r_multiple: float | None
    worst_r_multiple: float | None
    positive_r_count: int
    negative_r_count: int
    r_win_rate: float | None
    planned_price_entry_count: int
    stop_loss_defined_count: int
    target_defined_count: int
    average_entry_slippage_amount: float | None
    average_entry_slippage_rate: float | None
    average_planned_reward_risk_ratio: float | None
    average_profit_loss: float | None
    average_profit_rate: float | None
    win_count: int
    loss_count: int
    breakeven_count: int
    win_rate: float | None
    rule_followed_profit_loss_total: int
    rule_broken_profit_loss_total: int
    rule_unknown_profit_loss_total: int
    best_entry: dict | None
    worst_entry: dict | None
    strategy_performance: list[dict]
    setup_tag_performance: list[dict]
    cumulative_profit_curve: list[dict]
    max_drawdown_amount: int
    max_drawdown_rate: float | None
    monthly_performance: list[dict]
    annual_profit: list[dict]
    quarterly_profit: list[dict]
    monthly_profit: list[dict]
    profit_trend: list[dict]
    ticker_allocation: list[dict]
    type_allocation: list[dict]
    account_allocation: list[dict]
    dividend_total: int
    dividend_by_year: list[dict]
    tax_total: int
    tax_by_year: list[dict]
    commission_total: int
    commission_by_year: list[dict]
    currency_breakdown: list[dict]
    fx_unconverted_count: int
    corporate_action_adjusted_count: int
    duplicate_manual_transactions_count: int
    manual_transactions_count: int
    current_win_streak: int
    current_loss_streak: int
    longest_win_streak: int
    longest_loss_streak: int
    total_buy_amount: int
    total_sell_amount: int
    latest_entry_at: str | None = None
