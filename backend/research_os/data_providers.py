import research_os.provider_usage as provider_usage
from research_os.analysis_data_provider import (
    AnalysisDataProvider,
    get_analysis_data_provider,
)
from research_os.data_provider_utils import (
    _first_value,
)
from research_os.customs_data_provider import (
    CUSTOMS_DEFAULT_COUNTRY_CODES,
    KoreaCustomsTradeClient,
    fetch_customs_total_trend_status,
    fetch_customs_trade_rows,
    is_valid_customs_trade_row,
    normalize_customs_trade_row,
)
from research_os.nps_data_provider import (
    NpsOdcloudClient,
    fetch_nps_institutional_context,
    fetch_nps_institutional_signal,
    nps_signal_to_data_points,
)
from research_os.kis_data_provider import (
    KIS_US_EXCHANGE_BY_TICKER,
    _kis_candidate_exchange_codes,
)


def _resolve_backend_relative_path(path_value: str):
    return provider_usage.resolve_backend_relative_path(path_value)


def _consume_external_provider_quota(
    *,
    provider_name: str,
    usage_file: str,
    daily_limit: int,
    monthly_limit: int,
    units: int = 1,
    unit_label: str = "requests",
) -> tuple[bool, str]:
    return provider_usage.consume_external_provider_quota(
        provider_name=provider_name,
        usage_file=usage_file,
        daily_limit=daily_limit,
        monthly_limit=monthly_limit,
        units=units,
        unit_label=unit_label,
    )
