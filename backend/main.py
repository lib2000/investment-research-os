import csv
import io
import time
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from email.parser import BytesParser
from email.policy import default as email_default_policy

import httpx
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response

from app.application_models import (
    CorporateActionCreateRequest,
    CorporateActionResponse,
    FxRateCreateRequest,
    FxRateResponse,
    JournalDraftsResponse,
    JournalAnalyticsResponse,
    JournalEntriesResponse,
    JournalEntryCreateRequest,
    JournalEntryResponse,
    ManualTransactionCreateRequest,
    ManualTransactionsImportResponse,
    ManualTransactionResponse,
    ManualTransactionsResponse,
    HistoricalSyncDayResult,
    HistoricalSyncJobResponse,
    HistoricalSyncResponse,
    JournalSourceTradesResponse,
    LatestSyncResponse,
    PortfolioResponse,
    SyncRunResponse,
)
from app.backup import backup_database, backup_database_if_due, list_database_backups
from app.brokerage import BrokerageClient, get_default_brokerage_client
from app.database import (
    cancel_history_sync_job,
    clear_imported_sync_records,
    count_journal_drafts,
    count_journal_entries,
    count_manual_transactions,
    create_manual_transaction,
    delete_journal_entry,
    delete_manual_transaction,
    fail_sync_run,
    fail_history_sync_job,
    finish_cancelled_history_sync_job,
    finish_history_sync_job,
    finish_sync_run,
    create_or_update_journal_entry,
    get_history_sync_job,
    get_latest_history_sync_job,
    get_latest_sync_run,
    get_journal_analytics,
    get_resumable_history_sync_job,
    init_db,
    list_journal_entries,
    list_journal_drafts,
    list_manual_transactions,
    mark_history_sync_job_day_started,
    mark_history_sync_job_page_checkpoint,
    mark_history_sync_job_retry,
    pause_stale_history_sync_jobs,
    start_history_sync_job,
    start_sync_run,
    update_history_sync_job_progress,
    upsert_corporate_action,
    upsert_fx_rate,
)
from app.kiwoom_account import KiwoomAccountClient, KiwoomMaskedAccountsStatus
from app.kiwoom_auth import KiwoomAuthClient, KiwoomMaskedTokenStatus
from app.kiwoom_balance import KiwoomBalanceClient, KiwoomBalanceStatus
from app.kiwoom_order_execution import (
    KiwoomOrderExecutionClient,
    KiwoomOrderExecutionStatus,
)
from app.kiwoom_trade_journal import (
    KiwoomTradeJournalClient,
    KiwoomTradeJournalStatus,
)
from app.models import Broker, BrokerStatus, TradesResponse
from app.security import verify_user_token
from app.settings import Settings, get_settings, mask_secret


MAX_HISTORICAL_SYNC_DAYS = 366


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db(settings)
    pause_stale_history_sync_jobs(settings)
    backup_database_if_due(settings, reason="startup")
    yield


app = FastAPI(title="Investment Journal API Gateway", lifespan=lifespan)


class AppError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        self.code = code
        self.message = message
        self.status = status


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )


@app.exception_handler(HTTPException)
async def http_error_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "요청 값 형식이 올바르지 않습니다.",
                "details": exc.errors(),
            },
        },
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "서버 처리 중 오류가 발생했습니다.",
            },
        },
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8082",
        "http://localhost:8082",
        "http://127.0.0.1:8081",
        "http://localhost:8081",
    ],
    allow_origin_regex=(
        r"^https?://("
        r"localhost|127\.0\.0\.1|"
        r"10\.\d+\.\d+\.\d+|"
        r"172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+|"
        r"192\.168\.\d+\.\d+"
        r"):\d+$"
    ),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root() -> dict:
    return {"message": "매매일지 백엔드 서버가 정상 작동 중입니다."}


@app.get("/api/v1/config/safety")
def read_safety_config(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "brokerage_api_key": mask_secret(settings.brokerage_api_key),
        "brokerage_api_secret": mask_secret(settings.brokerage_api_secret),
        "kiwoom_base_url": settings.kiwoom_base_url,
        "kiwoom_mock_base_url": settings.kiwoom_mock_base_url,
        "kiwoom_use_mock": settings.kiwoom_use_mock,
        "kiwoom_registered_ip": mask_secret(settings.kiwoom_registered_ip),
        "secret_salt": mask_secret(settings.secret_salt),
        "sqlite_encryption_configured": bool(settings.sqlite_encryption_key),
        "sqlite_wal_enabled": settings.sqlite_enable_wal,
        "sqlite_busy_timeout_ms": settings.sqlite_busy_timeout_ms,
        "sqlite_restrict_file_permissions": settings.sqlite_restrict_file_permissions,
        "db_backup_on_startup": settings.db_backup_on_startup,
        "db_backup_dir": settings.db_backup_dir,
        "db_backup_retention_days": settings.db_backup_retention_days,
        "db_backup_interval_hours": settings.db_backup_interval_hours,
        "secrets_are_masked": True,
    }


@app.get(
    "/api/v1/admin/backups",
    dependencies=[Depends(verify_user_token)],
)
def read_database_backups(settings: Settings = Depends(get_settings)) -> dict:
    return list_database_backups(settings)


@app.post(
    "/api/v1/admin/backups",
    dependencies=[Depends(verify_user_token)],
)
def create_database_backup(settings: Settings = Depends(get_settings)) -> dict:
    return backup_database(settings, reason="manual")


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


@app.post(
    "/api/v1/brokerage/kiwoom/accounts-test",
    response_model=KiwoomMaskedAccountsStatus,
    dependencies=[Depends(verify_user_token)],
)
def test_kiwoom_account_lookup(
    settings: Settings = Depends(get_settings),
) -> KiwoomMaskedAccountsStatus:
    """
    키움 계좌번호조회(ka00001)를 테스트합니다.

    보안상 실제 계좌번호 원문은 반환하지 않고 마스킹된 값만 반환합니다.
    """
    return KiwoomAccountClient(settings).fetch_masked_accounts_status()


@app.post(
    "/api/v1/brokerage/kiwoom/balance-test",
    response_model=KiwoomBalanceStatus,
    dependencies=[Depends(verify_user_token)],
)
def test_kiwoom_balance_lookup(
    settings: Settings = Depends(get_settings),
) -> KiwoomBalanceStatus:
    """
    키움 계좌평가잔고내역요청(kt00018)을 테스트합니다.

    보유 종목 화면의 기본 데이터 소스로 사용합니다.
    """
    return KiwoomBalanceClient(settings).fetch_balance_status()


@app.post(
    "/api/v1/brokerage/kiwoom/trade-journal-test",
    response_model=KiwoomTradeJournalStatus,
    dependencies=[Depends(verify_user_token)],
)
def test_kiwoom_trade_journal_lookup(
    settings: Settings = Depends(get_settings),
) -> KiwoomTradeJournalStatus:
    """
    키움 당일매매일지요청(ka10170)을 테스트합니다.

    매매일지 자동 생성의 1차 원천 데이터로 사용합니다.
    """
    return KiwoomTradeJournalClient(settings).fetch_today_trade_journal_status()


@app.post(
    "/api/v1/brokerage/kiwoom/order-executions-test",
    response_model=KiwoomOrderExecutionStatus,
    dependencies=[Depends(verify_user_token)],
)
def test_kiwoom_order_executions_lookup(
    settings: Settings = Depends(get_settings),
) -> KiwoomOrderExecutionStatus:
    """
    키움 계좌별주문체결내역상세요청(kt00007)을 테스트합니다.

    매매일지의 원천 체결 단위 데이터로 사용합니다.
    """
    return KiwoomOrderExecutionClient(settings).fetch_order_execution_status()


@app.get(
    "/api/v1/portfolio",
    response_model=PortfolioResponse,
    dependencies=[Depends(verify_user_token)],
)
def read_portfolio(
    settings: Settings = Depends(get_settings),
) -> PortfolioResponse:
    """
    모바일 포트폴리오 화면에서 사용하는 현재 잔고/보유종목 API입니다.
    """
    balance = KiwoomBalanceClient(settings).fetch_balance_status()
    return PortfolioResponse(
        broker="KIWOOM",
        synced_from="kt00018",
        summary=balance.summary,
        holdings_count=balance.holdings_count,
        holdings=balance.holdings,
        has_next=balance.has_next,
        return_code=balance.return_code,
        return_msg=balance.return_msg,
    )


@app.get(
    "/api/v1/journal/source-trades",
    response_model=JournalSourceTradesResponse,
    dependencies=[Depends(verify_user_token)],
)
def read_journal_source_trades(
    base_date: str = Query(default="", description="YYYYMMDD. 비우면 금일 조회"),
    order_date: str = Query(default="", description="YYYYMMDD. 비우면 금일 조회"),
    settings: Settings = Depends(get_settings),
) -> JournalSourceTradesResponse:
    """
    매매일지 자동 생성에 사용할 원천 거래 데이터 API입니다.

    ka10170은 당일 매매 요약, kt00007은 주문/체결 상세를 제공합니다.
    """
    trade_journal = KiwoomTradeJournalClient(settings).fetch_today_trade_journal_status(
        base_date=base_date
    )
    order_executions = KiwoomOrderExecutionClient(settings).fetch_order_execution_status(
        order_date=order_date
    )
    needs_review_count = max(
        trade_journal.items_count,
        order_executions.executions_count,
    )
    return JournalSourceTradesResponse(
        broker="KIWOOM",
        synced_from=["ka10170", "kt00007"],
        base_date=base_date or "TODAY",
        trade_summary=trade_journal.summary,
        trade_journal_items_count=trade_journal.items_count,
        trade_journal_items=trade_journal.items,
        order_executions_count=order_executions.executions_count,
        order_executions=order_executions.executions,
        needs_review_count=needs_review_count,
        has_next=trade_journal.has_next or order_executions.has_next,
        return_code=trade_journal.return_code,
        return_msg=trade_journal.return_msg,
    )


def _fetch_journal_source_trades_for_date(
    settings: Settings,
    target_date: str,
    job_id: int | None = None,
) -> JournalSourceTradesResponse:
    def checkpoint(api_id: str, page_no: int, cursor: str) -> None:
        if job_id is None:
            return
        mark_history_sync_job_page_checkpoint(
            settings=settings,
            job_id=job_id,
            target_date=target_date,
            api_id=api_id,
            page_no=page_no,
            cursor=cursor,
        )

    trade_journal = KiwoomTradeJournalClient(settings).fetch_today_trade_journal_status(
        base_date=target_date,
        page_checkpoint=checkpoint,
    )
    if settings.history_sync_request_delay_seconds > 0:
        time.sleep(settings.history_sync_request_delay_seconds)
    order_executions = KiwoomOrderExecutionClient(settings).fetch_order_execution_status(
        order_date=target_date,
        page_checkpoint=checkpoint,
    )
    needs_review_count = max(
        trade_journal.items_count,
        order_executions.executions_count,
    )
    return JournalSourceTradesResponse(
        broker="KIWOOM",
        synced_from=["ka10170", "kt00007"],
        base_date=target_date,
        trade_summary=trade_journal.summary,
        trade_journal_items_count=trade_journal.items_count,
        trade_journal_items=trade_journal.items,
        order_executions_count=order_executions.executions_count,
        order_executions=order_executions.executions,
        needs_review_count=needs_review_count,
        has_next=trade_journal.has_next or order_executions.has_next,
        return_code=trade_journal.return_code,
        return_msg=trade_journal.return_msg,
    )


@app.post(
    "/api/v1/sync/kiwoom",
    response_model=SyncRunResponse,
    dependencies=[Depends(verify_user_token)],
)
def sync_kiwoom_data(
    settings: Settings = Depends(get_settings),
) -> SyncRunResponse:
    """
    키움 포트폴리오와 매매일지 원천 데이터를 조회해 로컬 DB에 저장합니다.
    """
    init_db(settings)
    sync_run_id = start_sync_run(settings, broker="KIWOOM")
    try:
        portfolio = read_portfolio(settings=settings)
        today = datetime.now().strftime("%Y%m%d")
        journal = read_journal_source_trades(
            base_date=today,
            order_date=today,
            settings=settings,
        )
        finish_sync_run(settings, sync_run_id, portfolio, journal)
    except Exception as exc:
        fail_sync_run(settings, sync_run_id, str(exc))
        raise

    return SyncRunResponse(
        status="success",
        sync_run_id=sync_run_id,
        broker="KIWOOM",
        portfolio_holdings_count=portfolio.holdings_count,
        journal_items_count=journal.trade_journal_items_count,
        order_executions_count=journal.order_executions_count,
        needs_review_count=journal.needs_review_count,
    )


@app.post(
    "/api/v1/sync/kiwoom/history",
    response_model=HistoricalSyncResponse,
    dependencies=[Depends(verify_user_token)],
)
def sync_kiwoom_history(
    start_date: str = Query(description="YYYYMMDD 또는 YYYY-MM-DD"),
    end_date: str = Query(description="YYYYMMDD 또는 YYYY-MM-DD"),
    settings: Settings = Depends(get_settings),
) -> HistoricalSyncResponse:
    """
    지정한 날짜 범위의 키움 과거 거래 이력을 조회해 로컬 DB 초안으로 저장합니다.

    API 호출량과 응답 시간을 통제하기 위해 한 번에 최대 1년 단위로 허용합니다.
    """
    init_db(settings)
    start = _parse_sync_date(start_date)
    end = _parse_sync_date(end_date)
    if start > end:
        raise HTTPException(status_code=400, detail="start_date는 end_date보다 늦을 수 없습니다.")

    dates = _date_range(start, end)
    if len(dates) > MAX_HISTORICAL_SYNC_DAYS:
        raise HTTPException(status_code=400, detail="과거 동기화는 한 번에 최대 1년까지만 가능합니다.")

    portfolio = read_portfolio(settings=settings)
    results: list[HistoricalSyncDayResult] = []
    for target in dates:
        target_date = target.strftime("%Y%m%d")
        if results and settings.history_sync_rate_limit_seconds > 0:
            time.sleep(settings.history_sync_rate_limit_seconds)
        sync_run_id = start_sync_run(settings, broker="KIWOOM")
        try:
            journal = _fetch_journal_source_trades_for_date(settings, target_date)
            finish_sync_run(settings, sync_run_id, portfolio, journal)
        except Exception as exc:
            fail_sync_run(settings, sync_run_id, str(exc))
            raise

        results.append(
            HistoricalSyncDayResult(
                date=target_date,
                sync_run_id=sync_run_id,
                journal_items_count=journal.trade_journal_items_count,
                order_executions_count=journal.order_executions_count,
                needs_review_count=journal.needs_review_count,
                has_next=journal.has_next,
            )
        )

    return HistoricalSyncResponse(
        status="success",
        broker="KIWOOM",
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
        days_requested=len(dates),
        days_synced=len(results),
        total_journal_items_count=sum(item.journal_items_count for item in results),
        total_order_executions_count=sum(
            item.order_executions_count for item in results
        ),
        total_needs_review_count=sum(item.needs_review_count for item in results),
        results=results,
    )


@app.post(
    "/api/v1/sync/kiwoom/history/start",
    response_model=HistoricalSyncJobResponse,
    dependencies=[Depends(verify_user_token)],
)
def start_kiwoom_history_sync(
    background_tasks: BackgroundTasks,
    start_date: str = Query(description="YYYYMMDD 또는 YYYY-MM-DD"),
    end_date: str = Query(description="YYYYMMDD 또는 YYYY-MM-DD"),
    settings: Settings = Depends(get_settings),
) -> HistoricalSyncJobResponse:
    """
    과거 거래 이력 동기화를 백그라운드 작업으로 시작합니다.

    화면은 이 API의 job id로 진행 상태를 조회합니다.
    """
    init_db(settings)
    start = _parse_sync_date(start_date)
    end = _parse_sync_date(end_date)
    if start > end:
        raise HTTPException(status_code=400, detail="start_date는 end_date보다 늦을 수 없습니다.")

    dates = _date_range(start, end)
    if len(dates) > MAX_HISTORICAL_SYNC_DAYS:
        raise HTTPException(status_code=400, detail="과거 동기화는 한 번에 최대 1년까지만 가능합니다.")

    resume_from_job = get_resumable_history_sync_job(
        settings=settings,
        broker="KIWOOM",
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
    )
    resume_from_job_id = None
    if resume_from_job and resume_from_job.get("next_date"):
        resume_start = _parse_sync_date(str(resume_from_job["next_date"]))
        if start <= resume_start <= end:
            dates = [target for target in dates if target >= resume_start]
            resume_from_job_id = int(resume_from_job["id"])

    job = start_history_sync_job(
        settings=settings,
        broker="KIWOOM",
        start_date=start.strftime("%Y%m%d"),
        end_date=end.strftime("%Y%m%d"),
        total_days=len(dates),
        resume_from_job_id=resume_from_job_id,
    )
    background_tasks.add_task(_run_kiwoom_history_sync_job, settings, int(job["id"]), dates)
    return HistoricalSyncJobResponse(status="accepted", job=job)


@app.get(
    "/api/v1/sync/kiwoom/history/latest",
    response_model=HistoricalSyncJobResponse,
    dependencies=[Depends(verify_user_token)],
)
def read_latest_kiwoom_history_sync(
    settings: Settings = Depends(get_settings),
) -> HistoricalSyncJobResponse:
    return HistoricalSyncJobResponse(
        status="success",
        job=get_latest_history_sync_job(settings) or {},
    )


@app.get(
    "/api/v1/sync/kiwoom/history/jobs/{job_id}",
    response_model=HistoricalSyncJobResponse,
    dependencies=[Depends(verify_user_token)],
)
def read_kiwoom_history_sync_job(
    job_id: int,
    settings: Settings = Depends(get_settings),
) -> HistoricalSyncJobResponse:
    job = get_history_sync_job(settings, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="과거 거래 동기화 작업을 찾을 수 없습니다.")
    return HistoricalSyncJobResponse(status="success", job=job)


@app.post(
    "/api/v1/sync/kiwoom/history/jobs/{job_id}/cancel",
    response_model=HistoricalSyncJobResponse,
    dependencies=[Depends(verify_user_token)],
)
def cancel_kiwoom_history_sync_job(
    job_id: int,
    settings: Settings = Depends(get_settings),
) -> HistoricalSyncJobResponse:
    job = cancel_history_sync_job(settings, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="과거 거래 동기화 작업을 찾을 수 없습니다.")
    return HistoricalSyncJobResponse(status="success", job=job)


@app.delete(
    "/api/v1/sync/kiwoom/history/records",
    dependencies=[Depends(verify_user_token)],
)
def clear_kiwoom_history_records(
    confirm: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        result = clear_imported_sync_records(settings, confirm=confirm)
    except ValueError as exc:
        raise AppError("HISTORY_SYNC_ACTIVE", str(exc), 409) from exc
    return {"status": "success", **result}


@app.get(
    "/api/v1/sync/latest",
    response_model=LatestSyncResponse,
    dependencies=[Depends(verify_user_token)],
)
def read_latest_sync(
    settings: Settings = Depends(get_settings),
) -> LatestSyncResponse:
    return LatestSyncResponse(sync_run=get_latest_sync_run(settings))


@app.get(
    "/api/v1/journal/drafts",
    response_model=JournalDraftsResponse,
    dependencies=[Depends(verify_user_token)],
)
def read_journal_drafts(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    include_completed: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
) -> JournalDraftsResponse:
    offset = _pagination_offset(page, page_size)
    total = count_journal_drafts(settings, include_completed=include_completed)
    drafts = list_journal_drafts(
        settings,
        limit=page_size,
        offset=offset,
        include_completed=include_completed,
    )
    return JournalDraftsResponse(
        drafts_count=len(drafts),
        drafts=drafts,
        **_pagination_payload(total=total, page=page, page_size=page_size),
    )


@app.post(
    "/api/v1/journal/entries",
    response_model=JournalEntryResponse,
    dependencies=[Depends(verify_user_token)],
)
def upsert_journal_entry(
    payload: JournalEntryCreateRequest,
    settings: Settings = Depends(get_settings),
) -> JournalEntryResponse:
    init_db(settings)
    try:
        entry = create_or_update_journal_entry(
            settings=settings,
            draft_id=payload.draft_id,
            strategy_name=payload.strategy_name,
            setup_tags=payload.setup_tags,
            entry_reason=payload.entry_reason,
            exit_reason=payload.exit_reason,
            rule_followed=payload.rule_followed,
            good_points=payload.good_points,
            improvement_points=payload.improvement_points,
            memo=payload.memo,
            manual_profit_loss_amount=payload.manual_profit_loss_amount,
            manual_profit_rate=payload.manual_profit_rate,
            manual_buy_amount=payload.manual_buy_amount,
            manual_sell_amount=payload.manual_sell_amount,
            planned_entry_price=payload.planned_entry_price,
            actual_entry_price=payload.actual_entry_price,
            stop_loss_price=payload.stop_loss_price,
            target_price=payload.target_price,
            exit_price=payload.exit_price,
            planned_risk_amount=payload.planned_risk_amount,
            realized_r_multiple=payload.realized_r_multiple,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return JournalEntryResponse(entry=entry)


@app.get(
    "/api/v1/journal/entries",
    response_model=JournalEntriesResponse,
    dependencies=[Depends(verify_user_token)],
)
def read_journal_entries(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    ticker: str = Query(default="", description="종목코드 일부 또는 전체"),
    strategy_name: str = Query(default="", description="전략명 일부 또는 전체"),
    setup_tag: str = Query(default="", description="셋업 태그 일부 또는 전체"),
    result: str = Query(
        default="",
        description="profit, loss, breakeven, unknown 중 하나",
    ),
    rule_status: str = Query(
        default="",
        description="followed, broken, unknown 중 하나",
    ),
    search: str = Query(default="", description="종목명, 근거, 메모, 태그 검색어"),
    settings: Settings = Depends(get_settings),
) -> JournalEntriesResponse:
    offset = _pagination_offset(page, page_size)
    total = count_journal_entries(
        settings=settings,
        ticker=ticker,
        strategy_name=strategy_name,
        setup_tag=setup_tag,
        result=result,
        rule_status=rule_status,
        search=search,
    )
    entries = list_journal_entries(
        settings=settings,
        limit=page_size,
        offset=offset,
        ticker=ticker,
        strategy_name=strategy_name,
        setup_tag=setup_tag,
        result=result,
        rule_status=rule_status,
        search=search,
    )
    return JournalEntriesResponse(
        entries_count=len(entries),
        entries=entries,
        **_pagination_payload(total=total, page=page, page_size=page_size),
    )


@app.get(
    "/api/v1/manual-transactions",
    response_model=ManualTransactionsResponse,
    dependencies=[Depends(verify_user_token)],
)
def read_manual_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    settings: Settings = Depends(get_settings),
) -> ManualTransactionsResponse:
    offset = _pagination_offset(page, page_size)
    total = count_manual_transactions(settings)
    transactions = list_manual_transactions(settings, limit=page_size, offset=offset)
    return ManualTransactionsResponse(
        transactions_count=len(transactions),
        transactions=transactions,
        **_pagination_payload(total=total, page=page, page_size=page_size),
    )


@app.post(
    "/api/v1/manual-transactions",
    response_model=ManualTransactionResponse,
    dependencies=[Depends(verify_user_token)],
)
def add_manual_transaction(
    payload: ManualTransactionCreateRequest,
    settings: Settings = Depends(get_settings),
) -> ManualTransactionResponse:
    init_db(settings)
    transaction = create_manual_transaction(
        settings=settings,
        trade_date=_normalize_manual_trade_date(payload.trade_date),
        broker=payload.broker,
        account_name=payload.account_name,
        transaction_type=payload.transaction_type,
        ticker=payload.ticker,
        name=payload.name,
        quantity=payload.quantity,
        price=payload.price,
        buy_amount=payload.buy_amount,
        sell_amount=payload.sell_amount,
        profit_loss_amount=payload.profit_loss_amount,
        dividend_amount=payload.dividend_amount,
        tax_amount=payload.tax_amount,
        commission_amount=payload.commission_amount,
        currency=payload.currency,
        fx_rate_krw=payload.fx_rate_krw,
        split_adjustment_ratio=payload.split_adjustment_ratio,
        adjustment_note=payload.adjustment_note,
        memo=payload.memo,
    )
    return ManualTransactionResponse(transaction=transaction)


@app.post(
    "/api/v1/manual-transactions/import.csv",
    response_model=ManualTransactionsImportResponse,
    dependencies=[Depends(verify_user_token)],
)
async def import_manual_transactions_csv(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> ManualTransactionsImportResponse:
    init_db(settings)
    file_name, csv_bytes = await _extract_csv_upload(request)
    parsed_rows = _parse_manual_transaction_csv(csv_bytes)
    transactions = []
    errors = []
    skipped_count = 0

    for row_number, row in parsed_rows:
        if _is_blank_csv_row(row):
            skipped_count += 1
            continue
        try:
            payload = _manual_transaction_payload_from_csv_row(row)
            transaction = create_manual_transaction(settings=settings, **payload)
            transactions.append(transaction)
        except ValueError as exc:
            errors.append({"row": row_number, "message": str(exc)})

    return ManualTransactionsImportResponse(
        file_name=file_name,
        total_rows=len(parsed_rows),
        imported_count=len(transactions),
        failed_count=len(errors),
        skipped_count=skipped_count,
        transactions=transactions[:50],
        errors=errors,
    )


@app.get(
    "/api/v1/manual-transactions/import.csv/template",
    dependencies=[Depends(verify_user_token)],
)
def download_manual_transactions_csv_template() -> Response:
    csv_text = _manual_transactions_csv_template()
    return Response(
        content=csv_text.encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="manual-transactions-template.csv"',
        },
    )


@app.post(
    "/api/v1/reference/fx-rates",
    response_model=FxRateResponse,
    dependencies=[Depends(verify_user_token)],
)
def save_fx_rate(
    payload: FxRateCreateRequest,
    settings: Settings = Depends(get_settings),
) -> FxRateResponse:
    init_db(settings)
    fx_rate = upsert_fx_rate(
        settings=settings,
        currency=payload.currency,
        rate_date=_normalize_manual_trade_date(payload.rate_date),
        fx_rate_krw=payload.fx_rate_krw,
        source=payload.source,
    )
    return FxRateResponse(fx_rate=fx_rate)


@app.post(
    "/api/v1/reference/corporate-actions",
    response_model=CorporateActionResponse,
    dependencies=[Depends(verify_user_token)],
)
def save_corporate_action(
    payload: CorporateActionCreateRequest,
    settings: Settings = Depends(get_settings),
) -> CorporateActionResponse:
    init_db(settings)
    corporate_action = upsert_corporate_action(
        settings=settings,
        ticker=payload.ticker,
        action_type=payload.action_type,
        effective_date=_normalize_manual_trade_date(payload.effective_date),
        adjustment_ratio=payload.adjustment_ratio,
        source=payload.source,
        memo=payload.memo,
    )
    return CorporateActionResponse(corporate_action=corporate_action)


@app.delete(
    "/api/v1/manual-transactions/{transaction_id}",
    dependencies=[Depends(verify_user_token)],
)
def remove_manual_transaction(
    transaction_id: int,
    settings: Settings = Depends(get_settings),
) -> dict:
    try:
        deleted = delete_manual_transaction(settings, transaction_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "success", **deleted}


@app.get(
    "/api/v1/journal/entries/export.csv",
    dependencies=[Depends(verify_user_token)],
)
def export_journal_entries_csv(
    ticker: str = Query(default="", description="종목코드 일부 또는 전체"),
    strategy_name: str = Query(default="", description="전략명 일부 또는 전체"),
    setup_tag: str = Query(default="", description="셋업 태그 일부 또는 전체"),
    result: str = Query(default="", description="profit, loss, breakeven, unknown 중 하나"),
    rule_status: str = Query(default="", description="followed, broken, unknown 중 하나"),
    search: str = Query(default="", description="종목명, 근거, 메모, 태그 검색어"),
    settings: Settings = Depends(get_settings),
) -> Response:
    entries = list_journal_entries(
        settings=settings,
        limit=1000,
        ticker=ticker,
        strategy_name=strategy_name,
        setup_tag=setup_tag,
        result=result,
        rule_status=rule_status,
        search=search,
    )
    csv_text = _journal_entries_to_csv(entries)
    return Response(
        content="\ufeff" + csv_text,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="investment-journal-entries.csv"'
        },
    )


@app.delete(
    "/api/v1/journal/entries/{entry_id}",
    dependencies=[Depends(verify_user_token)],
)
def remove_journal_entry(
    entry_id: int,
    settings: Settings = Depends(get_settings),
) -> dict:
    init_db(settings)
    try:
        deleted = delete_journal_entry(settings, entry_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "success", **deleted}


@app.get(
    "/api/v1/journal/analytics",
    response_model=JournalAnalyticsResponse,
    dependencies=[Depends(verify_user_token)],
)
def read_journal_analytics(
    start_date: str | None = Query(default=None, description="YYYYMMDD 또는 YYYY-MM-DD"),
    end_date: str | None = Query(default=None, description="YYYYMMDD 또는 YYYY-MM-DD"),
    settings: Settings = Depends(get_settings),
) -> JournalAnalyticsResponse:
    parsed_start = _parse_optional_filter_date(start_date, "start_date")
    parsed_end = _parse_optional_filter_date(end_date, "end_date")
    if parsed_start and parsed_end and parsed_start > parsed_end:
        raise HTTPException(status_code=400, detail="start_date는 end_date보다 늦을 수 없습니다.")
    return JournalAnalyticsResponse(
        **get_journal_analytics(
            settings,
            start_date=parsed_start.isoformat() if parsed_start else None,
            end_date=parsed_end.isoformat() if parsed_end else None,
        )
    )


@app.get(
    "/api/v1/analytics/journal",
    dependencies=[Depends(verify_user_token)],
)
def redirect_legacy_journal_analytics() -> RedirectResponse:
    return RedirectResponse("/api/v1/journal/analytics", status_code=301)


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


def _parse_sync_date(value: str) -> date:
    normalized = value.strip().replace("-", "")
    try:
        return datetime.strptime(normalized, "%Y%m%d").date()
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="날짜는 YYYYMMDD 또는 YYYY-MM-DD 형식이어야 합니다.",
        ) from exc


def _parse_optional_filter_date(value: str | None, field_name: str) -> date | None:
    if value is None or not value.strip():
        return None
    try:
        return _parse_sync_date(value)
    except HTTPException as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=f"{field_name}는 YYYYMMDD 또는 YYYY-MM-DD 형식이어야 합니다.",
        ) from exc


def _normalize_manual_trade_date(value: str) -> str:
    return _parse_sync_date(value).strftime("%Y-%m-%d")


def _manual_transactions_csv_template() -> str:
    rows = [
        [
            "거래일",
            "증권사",
            "계좌",
            "유형",
            "종목코드",
            "종목명",
            "수량",
            "가격",
            "매수금액",
            "매도금액",
            "매매손익",
            "배당",
            "세금",
            "수수료",
            "통화",
            "환율",
            "분할보정비율",
            "보정메모",
            "메모",
        ],
        [
            "2026-05-22",
            "타증권",
            "기타",
            "trade",
            "005930",
            "삼성전자",
            "1",
            "80000",
            "80000",
            "",
            "0",
            "0",
            "0",
            "0",
            "KRW",
            "",
            "1",
            "",
            "예시 행은 삭제 후 사용",
        ],
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(rows)
    return buffer.getvalue()


async def _extract_csv_upload(request: Request) -> tuple[str, bytes]:
    content_type = request.headers.get("content-type", "")
    body = await request.body()
    if not body:
        raise AppError("CSV_EMPTY", "CSV 파일 내용이 비어 있습니다.", 400)

    if content_type.startswith("multipart/form-data"):
        header = (
            f"Content-Type: {content_type}\r\n"
            "MIME-Version: 1.0\r\n"
            "\r\n"
        ).encode("utf-8")
        message = BytesParser(policy=email_default_policy).parsebytes(header + body)
        if not message.is_multipart():
            raise AppError("CSV_MULTIPART_INVALID", "multipart/form-data 형식이 올바르지 않습니다.", 400)
        for part in message.iter_parts():
            disposition = part.get("Content-Disposition", "")
            field_name = part.get_param("name", header="content-disposition")
            if "filename=" in disposition or field_name in {"file", "csv", "upload"}:
                file_name = part.get_filename() or "manual-transactions.csv"
                payload = part.get_payload(decode=True) or b""
                if not payload:
                    raise AppError("CSV_EMPTY", "CSV 파일 내용이 비어 있습니다.", 400)
                return file_name, payload
        raise AppError("CSV_FILE_MISSING", "업로드 요청에서 CSV 파일 필드를 찾을 수 없습니다.", 400)

    if content_type.startswith("text/csv") or content_type.startswith("application/csv"):
        return "manual-transactions.csv", body

    raise AppError(
        "CSV_CONTENT_TYPE_INVALID",
        "CSV 가져오기는 multipart/form-data 또는 text/csv 요청만 지원합니다.",
        415,
    )


def _parse_manual_transaction_csv(csv_bytes: bytes) -> list[tuple[int, dict]]:
    text = _decode_csv_text(csv_bytes)
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise AppError("CSV_HEADER_MISSING", "CSV 첫 줄에 헤더가 필요합니다.", 400)
    return [(index, row) for index, row in enumerate(reader, start=2)]


def _decode_csv_text(csv_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "cp949", "euc-kr"):
        try:
            return csv_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise AppError("CSV_ENCODING_UNSUPPORTED", "CSV 인코딩은 UTF-8 또는 CP949만 지원합니다.", 400)


def _manual_transaction_payload_from_csv_row(row: dict) -> dict:
    normalized = {
        _normalize_csv_header(key): (value or "").strip()
        for key, value in row.items()
        if key is not None
    }

    trade_date = _csv_value(normalized, "trade_date")
    if not trade_date:
        raise ValueError("거래일은 필수입니다.")

    return {
        "trade_date": _normalize_manual_trade_date(trade_date),
        "broker": _csv_value(normalized, "broker") or "CSV",
        "account_name": _csv_value(normalized, "account_name") or "기타",
        "transaction_type": _normalize_csv_transaction_type(
            _csv_value(normalized, "transaction_type") or "trade"
        ),
        "ticker": _csv_value(normalized, "ticker"),
        "name": _csv_value(normalized, "name"),
        "quantity": _parse_optional_float(_csv_value(normalized, "quantity")),
        "price": _parse_optional_float(_csv_value(normalized, "price")),
        "buy_amount": _parse_optional_int(_csv_value(normalized, "buy_amount")),
        "sell_amount": _parse_optional_int(_csv_value(normalized, "sell_amount")),
        "profit_loss_amount": _parse_optional_int(_csv_value(normalized, "profit_loss_amount")),
        "dividend_amount": _parse_optional_int(_csv_value(normalized, "dividend_amount")),
        "tax_amount": _parse_optional_int(_csv_value(normalized, "tax_amount")),
        "commission_amount": _parse_optional_int(_csv_value(normalized, "commission_amount")),
        "currency": (_csv_value(normalized, "currency") or "KRW").upper(),
        "fx_rate_krw": _parse_optional_float(_csv_value(normalized, "fx_rate_krw")),
        "split_adjustment_ratio": _parse_optional_float(
            _csv_value(normalized, "split_adjustment_ratio")
        )
        or 1.0,
        "adjustment_note": _csv_value(normalized, "adjustment_note"),
        "memo": _csv_value(normalized, "memo"),
    }


def _normalize_csv_header(value: str) -> str:
    key = "".join(str(value).strip().lower().replace("\ufeff", "").split())
    aliases = {
        "거래일": "trade_date",
        "일자": "trade_date",
        "date": "trade_date",
        "tradedate": "trade_date",
        "증권사": "broker",
        "broker": "broker",
        "계좌": "account_name",
        "계좌명": "account_name",
        "account": "account_name",
        "accountname": "account_name",
        "유형": "transaction_type",
        "거래유형": "transaction_type",
        "type": "transaction_type",
        "transactiontype": "transaction_type",
        "종목코드": "ticker",
        "티커": "ticker",
        "ticker": "ticker",
        "symbol": "ticker",
        "code": "ticker",
        "종목명": "name",
        "name": "name",
        "수량": "quantity",
        "quantity": "quantity",
        "qty": "quantity",
        "가격": "price",
        "단가": "price",
        "price": "price",
        "매수금액": "buy_amount",
        "buyamount": "buy_amount",
        "매도금액": "sell_amount",
        "sellamount": "sell_amount",
        "매매손익": "profit_loss_amount",
        "손익": "profit_loss_amount",
        "실현손익": "profit_loss_amount",
        "pnl": "profit_loss_amount",
        "profitloss": "profit_loss_amount",
        "profitlossamount": "profit_loss_amount",
        "배당": "dividend_amount",
        "dividend": "dividend_amount",
        "세금": "tax_amount",
        "tax": "tax_amount",
        "수수료": "commission_amount",
        "commission": "commission_amount",
        "fee": "commission_amount",
        "통화": "currency",
        "currency": "currency",
        "환율": "fx_rate_krw",
        "fxrate": "fx_rate_krw",
        "fxratekrw": "fx_rate_krw",
        "분할보정비율": "split_adjustment_ratio",
        "보정비율": "split_adjustment_ratio",
        "splitadjustmentratio": "split_adjustment_ratio",
        "보정메모": "adjustment_note",
        "권리락메모": "adjustment_note",
        "adjustmentnote": "adjustment_note",
        "메모": "memo",
        "memo": "memo",
    }
    return aliases.get(key, key)


def _csv_value(row: dict, key: str) -> str:
    return str(row.get(key) or "").strip()


def _is_blank_csv_row(row: dict) -> bool:
    return not any(str(value or "").strip() for value in row.values())


def _normalize_csv_transaction_type(value: str) -> str:
    key = value.strip().lower()
    aliases = {
        "매매손익": "trade",
        "매매": "trade",
        "trade": "trade",
        "매수": "buy",
        "buy": "buy",
        "매도": "sell",
        "sell": "sell",
        "배당": "dividend",
        "dividend": "dividend",
        "세금": "tax",
        "tax": "tax",
        "수수료": "fee",
        "fee": "fee",
    }
    return aliases.get(key, key or "trade")


def _parse_optional_int(value: str) -> int | None:
    parsed = _parse_optional_float(value)
    if parsed is None:
        return None
    return int(round(parsed))


def _parse_optional_float(value: str) -> float | None:
    cleaned = value.strip()
    if not cleaned or cleaned in {"-", "--"}:
        return None
    is_negative = cleaned.startswith("(") and cleaned.endswith(")")
    cleaned = (
        cleaned.replace(",", "")
        .replace("원", "")
        .replace("$", "")
        .replace("%", "")
        .replace("(", "")
        .replace(")", "")
        .strip()
    )
    if not cleaned:
        return None
    try:
        number = float(cleaned)
    except ValueError as exc:
        raise ValueError(f"숫자 형식이 올바르지 않습니다: {value}") from exc
    return -number if is_negative else number


def _pagination_offset(page: int, page_size: int) -> int:
    return (page - 1) * page_size


def _pagination_payload(total: int, page: int, page_size: int) -> dict:
    total_pages = (total + page_size - 1) // page_size if total else 0
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_previous": page > 1 and total_pages > 0,
    }


def _date_range(start: date, end: date) -> list[date]:
    days = (end - start).days
    return [start + timedelta(days=offset) for offset in range(days + 1)]


def _run_kiwoom_history_sync_job(
    settings: Settings,
    job_id: int,
    dates: list[date],
) -> None:
    try:
        portfolio = read_portfolio(settings=settings)
        for index, target in enumerate(dates):
            if _history_sync_cancel_requested(settings, job_id):
                finish_cancelled_history_sync_job(settings, job_id)
                return

            target_date = target.strftime("%Y%m%d")
            next_date = dates[index + 1].strftime("%Y%m%d") if index + 1 < len(dates) else None
            if index > 0 and not _sleep_with_history_cancel_check(
                settings,
                job_id,
                settings.history_sync_rate_limit_seconds,
            ):
                finish_cancelled_history_sync_job(settings, job_id)
                return
            mark_history_sync_job_day_started(settings, job_id, target_date)
            sync_run_id = start_sync_run(settings, broker="KIWOOM")
            try:
                journal = _fetch_journal_source_trades_for_date_with_retry(
                    settings=settings,
                    job_id=job_id,
                    target_date=target_date,
                )
                finish_sync_run(settings, sync_run_id, portfolio, journal)
                update_history_sync_job_progress(
                    settings=settings,
                    job_id=job_id,
                    journal_items_count=journal.trade_journal_items_count,
                    order_executions_count=journal.order_executions_count,
                    needs_review_count=journal.needs_review_count,
                    completed_date=target_date,
                    next_date=next_date,
                )
                if _history_sync_cancel_requested(settings, job_id):
                    finish_cancelled_history_sync_job(settings, job_id)
                    return
                if next_date and not _sleep_with_history_cancel_check(
                    settings,
                    job_id,
                    settings.history_sync_min_delay_seconds,
                ):
                    finish_cancelled_history_sync_job(settings, job_id)
                    return
            except Exception as exc:
                fail_sync_run(settings, sync_run_id, str(exc))
                raise
        finish_history_sync_job(settings, job_id)
    except Exception as exc:
        fail_history_sync_job(settings, job_id, str(exc))


def _fetch_journal_source_trades_for_date_with_retry(
    settings: Settings,
    job_id: int,
    target_date: str,
) -> JournalSourceTradesResponse:
    max_retries = max(int(settings.history_sync_max_retries), 1)
    for attempt in range(1, max_retries + 1):
        try:
            return _fetch_journal_source_trades_for_date(
                settings=settings,
                target_date=target_date,
                job_id=job_id,
            )
        except Exception as exc:
            if attempt >= max_retries:
                raise

            backoff_seconds = max(
                _history_sync_backoff_seconds(settings, attempt),
                _history_sync_retry_after_seconds(exc),
            )
            mark_history_sync_job_retry(
                settings=settings,
                job_id=job_id,
                target_date=target_date,
                retry_count=attempt,
                backoff_seconds=backoff_seconds,
                error_message=_history_sync_retry_message(exc, attempt, max_retries),
            )
            if not _sleep_with_history_cancel_check(settings, job_id, backoff_seconds):
                raise RuntimeError("과거 거래 동기화가 사용자 요청으로 중단되었습니다.")

    raise RuntimeError("과거 거래 동기화 재시도 한도를 초과했습니다.")


def _history_sync_backoff_seconds(settings: Settings, attempt: int) -> float:
    initial = max(float(settings.history_sync_backoff_initial_seconds), 0)
    multiplier = max(float(settings.history_sync_backoff_multiplier), 1)
    max_seconds = max(float(settings.history_sync_backoff_max_seconds), initial)
    return min(initial * (multiplier ** max(attempt - 1, 0)), max_seconds)


def _history_sync_retry_message(exc: Exception, attempt: int, max_retries: int) -> str:
    reason = str(exc)
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        reason = f"HTTP {status_code}"
        retry_after = exc.response.headers.get("retry-after")
        if retry_after:
            reason = f"{reason}, retry-after={retry_after}"
    return f"재시도 {attempt}/{max_retries - 1}: {reason}"


def _history_sync_retry_after_seconds(exc: Exception) -> float:
    if not isinstance(exc, httpx.HTTPStatusError):
        return 0.0
    retry_after = exc.response.headers.get("retry-after")
    if not retry_after:
        return 0.0
    try:
        return max(float(retry_after), 0.0)
    except ValueError:
        return 0.0


def _sleep_with_history_cancel_check(
    settings: Settings,
    job_id: int,
    seconds: float,
) -> bool:
    if seconds <= 0:
        return not _history_sync_cancel_requested(settings, job_id)

    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if _history_sync_cancel_requested(settings, job_id):
            return False
        time.sleep(min(0.5, max(deadline - time.monotonic(), 0)))
    return not _history_sync_cancel_requested(settings, job_id)


def _history_sync_cancel_requested(settings: Settings, job_id: int) -> bool:
    job = get_history_sync_job(settings, job_id)
    return bool(job and job.get("status") == "cancel_requested")


def _journal_entries_to_csv(entries: list[dict]) -> str:
    output = io.StringIO()
    fieldnames = [
        "id",
        "draft_id",
        "broker",
        "ticker",
        "name",
        "strategy_name",
        "setup_tags",
        "rule_followed",
        "manual_profit_loss_amount",
        "manual_profit_rate",
        "manual_buy_amount",
        "manual_sell_amount",
        "planned_entry_price",
        "actual_entry_price",
        "stop_loss_price",
        "target_price",
        "exit_price",
        "planned_risk_amount",
        "realized_r_multiple",
        "entry_reason",
        "exit_reason",
        "good_points",
        "improvement_points",
        "memo",
        "created_at",
        "updated_at",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for entry in entries:
        row = {field: entry.get(field) for field in fieldnames}
        row["setup_tags"] = ", ".join(entry.get("setup_tags", []))
        writer.writerow(row)
    return output.getvalue()
