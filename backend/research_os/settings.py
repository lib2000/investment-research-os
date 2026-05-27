import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y"}


class Settings(BaseModel):
    app_name: str = "Investment Journal API Gateway"
    default_broker: str = "KIWOOM"
    brokerage_api_key: str = Field(default="********")
    brokerage_api_secret: str = Field(default="********")
    kiwoom_base_url: str = "https://api.kiwoom.com"
    kiwoom_mock_base_url: str = "https://mockapi.kiwoom.com"
    kiwoom_use_mock: bool = True
    kiwoom_registered_ip: str = Field(default="********")
    secret_salt: str = Field(default="********")
    dev_user_token: str = Field(default="dev-local-token")
    research_vault_dir: str = "../research_vault"
    data_provider_mode: str = "mock"
    auto_inject_analysis_data: bool = True
    fmp_api_key: str = Field(default="********")
    fmp_base_url: str = "https://financialmodelingprep.com/stable"
    fmp_timeout_seconds: float = 8.0
    kis_app_key: str = Field(default="********")
    kis_app_secret: str = Field(default="********")
    kis_base_url: str = "https://openapi.koreainvestment.com:9443"
    kis_mock_base_url: str = "https://openapivts.koreainvestment.com:29443"
    kis_use_mock: bool = False
    kis_allow_token_issue: bool = False
    kis_access_token: str = Field(default="")
    kis_access_token_file: str = Field(default="")
    kis_token_cache_file: str = "../research_vault/_system/kis_access_token.json"
    kis_timeout_seconds: float = 8.0
    dart_api_key: str = Field(default="")
    dart_base_url: str = "https://opendart.fss.or.kr/api"
    dart_corp_code_cache_file: str = "../research_vault/_system/dart_corp_codes.json"
    dart_timeout_seconds: float = 10.0
    dart_filing_auto_refresh: bool = True
    dart_filing_refresh_hours: float = 6.0
    dart_filing_lookback_days: int = 45
    dart_filing_max_items_per_ticker: int = 20
    financial_datasets_api_key: str = Field(default="")
    financial_datasets_base_url: str = "https://api.financialdatasets.ai"
    financial_datasets_timeout_seconds: float = 10.0
    finnhub_api_key: str = Field(default="")
    finnhub_base_url: str = "https://finnhub.io/api/v1"
    finnhub_timeout_seconds: float = 8.0
    tiingo_api_key: str = Field(default="")
    tiingo_base_url: str = "https://api.tiingo.com"
    tiingo_timeout_seconds: float = 8.0
    alpha_vantage_api_key: str = Field(default="")
    alpha_vantage_base_url: str = "https://www.alphavantage.co/query"
    alpha_vantage_timeout_seconds: float = 10.0
    tavily_api_key: str = Field(default="")
    tavily_base_url: str = "https://api.tavily.com"
    tavily_timeout_seconds: float = 12.0
    tavily_daily_credit_limit: int = 30
    tavily_monthly_credit_limit: int = 900
    brave_api_key: str = Field(default="")
    brave_base_url: str = "https://api.search.brave.com/res/v1"
    brave_timeout_seconds: float = 10.0
    brave_daily_request_limit: int = 30
    brave_monthly_request_limit: int = 900
    provider_usage_file: str = "../research_vault/_system/provider_usage.json"
    naver_finance_enabled: bool = True
    naver_finance_base_url: str = "https://m.stock.naver.com"
    naver_finance_timeout_seconds: float = 6.0
    ticker_registry_auto_refresh: bool = True
    ticker_registry_refresh_hours: float = 24.0
    ticker_registry_timeout_seconds: float = 12.0
    ticker_registry_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36"
    ticker_registry_krx_kind_url: str = "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"
    ticker_registry_nasdaq_listed_url: str = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
    ticker_registry_nasdaq_other_url: str = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
    block_onedrive_paths: bool = True
    live_data_max_age_minutes: float = 30.0
    earnings_calendar_on_demand_refresh: bool = True
    earnings_calendar_auto_refresh: bool = True
    earnings_calendar_refresh_hours: float = 12.0
    shinhan_research_enabled: bool = True
    shinhan_research_auto_refresh: bool = True
    shinhan_research_refresh_hours: float = 24.0
    shinhan_research_base_url: str = "https://www.shinhansec.com"
    shinhan_research_list_url: str = "https://www.shinhansec.com/siw/insights/research/list/view-popup.do"
    shinhan_research_timeout_seconds: float = 12.0
    shinhan_research_max_items: int = 20
    shinhan_research_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36"
    naver_research_enabled: bool = True
    naver_research_auto_refresh: bool = True
    naver_research_refresh_hours: float = 24.0
    naver_research_base_url: str = "https://finance.naver.com"
    naver_research_list_url: str = "https://finance.naver.com/research/"
    naver_research_timeout_seconds: float = 10.0
    naver_research_max_items: int = 40
    naver_research_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36"
    naver_research_pdf_extract_enabled: bool = True
    naver_research_pdf_snippet_max_chars: int = 900
    naver_market_close_auto_journal: bool = True
    naver_market_close_journal_time: str = "08:30"
    kcif_use_login: bool = True
    kcif_username: str = Field(default="")
    kcif_password: str = Field(default="")
    kcif_report_list_url: str = "https://www.kcif.or.kr/annual/reportList"
    kcif_login_proc_url: str = "https://www.kcif.or.kr/webUser/loginProc"
    kcif_timeout_seconds: float = 12.0
    regional_business_sources_enabled: bool = True
    regional_business_sources_auto_refresh: bool = True
    regional_business_sources_refresh_hours: float = 24.0
    regional_business_sources_timeout_seconds: float = 10.0
    regional_business_sources_max_items: int = 40
    regional_business_sources_user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36"
    nps_odcloud_enabled: bool = True
    nps_odcloud_api_key: str = Field(default="")
    nps_odcloud_base_url: str = "https://api.odcloud.kr/api"
    nps_domestic_stock_docs_url: str = "https://infuser.odcloud.kr/oas/docs?namespace=3070507/v1"
    nps_large_holding_docs_url: str = "https://infuser.odcloud.kr/oas/docs?namespace=15106890/v1"
    nps_domestic_stock_api_url: str = "https://api.odcloud.kr/api/3070507/v1/uddi:1eaca842-2152-4546-9144-a6d9d0fa3a19_201709281515"
    nps_large_holding_api_url: str = "https://api.odcloud.kr/api/15106890/v1/uddi:1bcc0415-377e-44fd-9f08-aa1e813a286c"
    nps_odcloud_timeout_seconds: float = 4.0
    nps_odcloud_max_pages: int = 1
    customs_trade_enabled: bool = True
    customs_trade_api_key: str = Field(default="")
    customs_trade_api_url: str = "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList"
    customs_trade_total_api_url: str = "https://apis.data.go.kr/1220000/Newtrade/getNewtradeList"
    customs_trade_total_docs_url: str = "https://www.data.go.kr/data/15102108/openapi.do"
    customs_trade_timeout_seconds: float = 8.0
    customs_trade_max_rows: int = 100
    customs_trade_release_days: str = "1,11,21"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            default_broker=os.getenv("DEFAULT_BROKER", "KIWOOM"),
            brokerage_api_key=os.getenv("KIWOOM_API_KEY", "********"),
            brokerage_api_secret=os.getenv("KIWOOM_API_SECRET", "********"),
            kiwoom_base_url=os.getenv("KIWOOM_BASE_URL", "https://api.kiwoom.com"),
            kiwoom_mock_base_url=os.getenv(
                "KIWOOM_MOCK_BASE_URL", "https://mockapi.kiwoom.com"
            ),
            kiwoom_use_mock=_read_bool("KIWOOM_USE_MOCK", True),
            kiwoom_registered_ip=os.getenv("KIWOOM_REGISTERED_IP", "********"),
            secret_salt=os.getenv("SECRET_SALT", "********"),
            dev_user_token=os.getenv("DEV_USER_TOKEN", "dev-local-token"),
            research_vault_dir=os.getenv("RESEARCH_VAULT_DIR", "../research_vault"),
            data_provider_mode=os.getenv("DATA_PROVIDER_MODE", "mock"),
            auto_inject_analysis_data=_read_bool("AUTO_INJECT_ANALYSIS_DATA", True),
            fmp_api_key=os.getenv("FMP_API_KEY", "********"),
            fmp_base_url=os.getenv(
                "FMP_BASE_URL", "https://financialmodelingprep.com/stable"
            ),
            fmp_timeout_seconds=float(os.getenv("FMP_TIMEOUT_SECONDS", "8")),
            kis_app_key=os.getenv("KIS_APP_KEY", os.getenv("KIS_API_KEY", "********")),
            kis_app_secret=os.getenv(
                "KIS_APP_SECRET", os.getenv("KIS_API_SECRET", "********")
            ),
            kis_base_url=os.getenv(
                "KIS_BASE_URL", "https://openapi.koreainvestment.com:9443"
            ),
            kis_mock_base_url=os.getenv(
                "KIS_MOCK_BASE_URL", "https://openapivts.koreainvestment.com:29443"
            ),
            kis_use_mock=_read_bool("KIS_USE_MOCK", False),
            kis_allow_token_issue=_read_bool("KIS_ALLOW_TOKEN_ISSUE", False),
            kis_access_token=os.getenv("KIS_ACCESS_TOKEN", ""),
            kis_access_token_file=os.getenv("KIS_ACCESS_TOKEN_FILE", ""),
            kis_token_cache_file=os.getenv(
                "KIS_TOKEN_CACHE_FILE", "../research_vault/_system/kis_access_token.json"
            ),
            kis_timeout_seconds=float(os.getenv("KIS_TIMEOUT_SECONDS", "8")),
            dart_api_key=os.getenv("DART_API_KEY", os.getenv("OPENDART_API_KEY", "")),
            dart_base_url=os.getenv("DART_BASE_URL", "https://opendart.fss.or.kr/api"),
            dart_corp_code_cache_file=os.getenv(
                "DART_CORP_CODE_CACHE_FILE",
                "../research_vault/_system/dart_corp_codes.json",
            ),
            dart_timeout_seconds=float(os.getenv("DART_TIMEOUT_SECONDS", "10")),
            dart_filing_auto_refresh=_read_bool("DART_FILING_AUTO_REFRESH", True),
            dart_filing_refresh_hours=float(os.getenv("DART_FILING_REFRESH_HOURS", "6")),
            dart_filing_lookback_days=int(os.getenv("DART_FILING_LOOKBACK_DAYS", "45")),
            dart_filing_max_items_per_ticker=int(
                os.getenv("DART_FILING_MAX_ITEMS_PER_TICKER", "20")
            ),
            financial_datasets_api_key=os.getenv("FINANCIAL_DATASETS_API_KEY", ""),
            financial_datasets_base_url=os.getenv(
                "FINANCIAL_DATASETS_BASE_URL", "https://api.financialdatasets.ai"
            ),
            financial_datasets_timeout_seconds=float(
                os.getenv("FINANCIAL_DATASETS_TIMEOUT_SECONDS", "10")
            ),
            finnhub_api_key=os.getenv("FINNHUB_API_KEY", ""),
            finnhub_base_url=os.getenv("FINNHUB_BASE_URL", "https://finnhub.io/api/v1"),
            finnhub_timeout_seconds=float(os.getenv("FINNHUB_TIMEOUT_SECONDS", "8")),
            tiingo_api_key=os.getenv("TIINGO_API_KEY", ""),
            tiingo_base_url=os.getenv("TIINGO_BASE_URL", "https://api.tiingo.com"),
            tiingo_timeout_seconds=float(os.getenv("TIINGO_TIMEOUT_SECONDS", "8")),
            alpha_vantage_api_key=os.getenv("ALPHA_VANTAGE_API_KEY", ""),
            alpha_vantage_base_url=os.getenv(
                "ALPHA_VANTAGE_BASE_URL", "https://www.alphavantage.co/query"
            ),
            alpha_vantage_timeout_seconds=float(
                os.getenv("ALPHA_VANTAGE_TIMEOUT_SECONDS", "10")
            ),
            tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
            tavily_base_url=os.getenv("TAVILY_BASE_URL", "https://api.tavily.com"),
            tavily_timeout_seconds=float(os.getenv("TAVILY_TIMEOUT_SECONDS", "12")),
            tavily_daily_credit_limit=int(os.getenv("TAVILY_DAILY_CREDIT_LIMIT", "30")),
            tavily_monthly_credit_limit=int(os.getenv("TAVILY_MONTHLY_CREDIT_LIMIT", "900")),
            brave_api_key=os.getenv("BRAVE_API_KEY", ""),
            brave_base_url=os.getenv(
                "BRAVE_BASE_URL", "https://api.search.brave.com/res/v1"
            ),
            brave_timeout_seconds=float(os.getenv("BRAVE_TIMEOUT_SECONDS", "10")),
            brave_daily_request_limit=int(os.getenv("BRAVE_DAILY_REQUEST_LIMIT", "30")),
            brave_monthly_request_limit=int(os.getenv("BRAVE_MONTHLY_REQUEST_LIMIT", "900")),
            provider_usage_file=os.getenv(
                "PROVIDER_USAGE_FILE", "../research_vault/_system/provider_usage.json"
            ),
            naver_finance_enabled=_read_bool("NAVER_FINANCE_ENABLED", True),
            naver_finance_base_url=os.getenv(
                "NAVER_FINANCE_BASE_URL", "https://m.stock.naver.com"
            ),
            naver_finance_timeout_seconds=float(
                os.getenv("NAVER_FINANCE_TIMEOUT_SECONDS", "6")
            ),
            ticker_registry_auto_refresh=_read_bool("TICKER_REGISTRY_AUTO_REFRESH", True),
            ticker_registry_refresh_hours=float(
                os.getenv("TICKER_REGISTRY_REFRESH_HOURS", "24")
            ),
            ticker_registry_timeout_seconds=float(
                os.getenv("TICKER_REGISTRY_TIMEOUT_SECONDS", "12")
            ),
            ticker_registry_user_agent=os.getenv(
                "TICKER_REGISTRY_USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            ),
            ticker_registry_krx_kind_url=os.getenv(
                "TICKER_REGISTRY_KRX_KIND_URL",
                "https://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13",
            ),
            ticker_registry_nasdaq_listed_url=os.getenv(
                "TICKER_REGISTRY_NASDAQ_LISTED_URL",
                "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
            ),
            ticker_registry_nasdaq_other_url=os.getenv(
                "TICKER_REGISTRY_NASDAQ_OTHER_URL",
                "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
            ),
            block_onedrive_paths=_read_bool("BLOCK_ONEDRIVE_PATHS", True),
            live_data_max_age_minutes=float(os.getenv("LIVE_DATA_MAX_AGE_MINUTES", "30")),
            earnings_calendar_on_demand_refresh=_read_bool(
                "EARNINGS_CALENDAR_ON_DEMAND_REFRESH", True
            ),
            earnings_calendar_auto_refresh=_read_bool("EARNINGS_CALENDAR_AUTO_REFRESH", True),
            earnings_calendar_refresh_hours=float(
                os.getenv("EARNINGS_CALENDAR_REFRESH_HOURS", "12")
            ),
            shinhan_research_enabled=_read_bool("SHINHAN_RESEARCH_ENABLED", True),
            shinhan_research_auto_refresh=_read_bool("SHINHAN_RESEARCH_AUTO_REFRESH", True),
            shinhan_research_refresh_hours=float(
                os.getenv("SHINHAN_RESEARCH_REFRESH_HOURS", "24")
            ),
            shinhan_research_base_url=os.getenv(
                "SHINHAN_RESEARCH_BASE_URL", "https://www.shinhansec.com"
            ),
            shinhan_research_list_url=os.getenv(
                "SHINHAN_RESEARCH_LIST_URL",
                "https://www.shinhansec.com/siw/insights/research/list/view-popup.do",
            ),
            shinhan_research_timeout_seconds=float(
                os.getenv("SHINHAN_RESEARCH_TIMEOUT_SECONDS", "12")
            ),
            shinhan_research_max_items=int(os.getenv("SHINHAN_RESEARCH_MAX_ITEMS", "20")),
            shinhan_research_user_agent=os.getenv(
                "SHINHAN_RESEARCH_USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            ),
            naver_research_enabled=_read_bool("NAVER_RESEARCH_ENABLED", True),
            naver_research_auto_refresh=_read_bool("NAVER_RESEARCH_AUTO_REFRESH", True),
            naver_research_refresh_hours=float(
                os.getenv("NAVER_RESEARCH_REFRESH_HOURS", "24")
            ),
            naver_research_base_url=os.getenv(
                "NAVER_RESEARCH_BASE_URL", "https://finance.naver.com"
            ),
            naver_research_list_url=os.getenv(
                "NAVER_RESEARCH_LIST_URL", "https://finance.naver.com/research/"
            ),
            naver_research_timeout_seconds=float(
                os.getenv("NAVER_RESEARCH_TIMEOUT_SECONDS", "10")
            ),
            naver_research_max_items=int(os.getenv("NAVER_RESEARCH_MAX_ITEMS", "40")),
            naver_research_user_agent=os.getenv(
                "NAVER_RESEARCH_USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            ),
            naver_research_pdf_extract_enabled=_read_bool(
                "NAVER_RESEARCH_PDF_EXTRACT_ENABLED", True
            ),
            naver_research_pdf_snippet_max_chars=int(
                os.getenv("NAVER_RESEARCH_PDF_SNIPPET_MAX_CHARS", "900")
            ),
            naver_market_close_auto_journal=_read_bool(
                "NAVER_MARKET_CLOSE_AUTO_JOURNAL", True
            ),
            naver_market_close_journal_time=os.getenv(
                "NAVER_MARKET_CLOSE_JOURNAL_TIME", "08:30"
            ),
            kcif_use_login=_read_bool("KCIF_USE_LOGIN", True),
            kcif_username=os.getenv("KCIF_USERNAME", os.getenv("KCIF_ID", "")),
            kcif_password=os.getenv("KCIF_PASSWORD", ""),
            kcif_report_list_url=os.getenv(
                "KCIF_REPORT_LIST_URL", "https://www.kcif.or.kr/annual/reportList"
            ),
            kcif_login_proc_url=os.getenv(
                "KCIF_LOGIN_PROC_URL", "https://www.kcif.or.kr/webUser/loginProc"
            ),
            kcif_timeout_seconds=float(os.getenv("KCIF_TIMEOUT_SECONDS", "12")),
            regional_business_sources_enabled=_read_bool(
                "REGIONAL_BUSINESS_SOURCES_ENABLED", True
            ),
            regional_business_sources_auto_refresh=_read_bool(
                "REGIONAL_BUSINESS_SOURCES_AUTO_REFRESH", True
            ),
            regional_business_sources_refresh_hours=float(
                os.getenv("REGIONAL_BUSINESS_SOURCES_REFRESH_HOURS", "24")
            ),
            regional_business_sources_timeout_seconds=float(
                os.getenv("REGIONAL_BUSINESS_SOURCES_TIMEOUT_SECONDS", "10")
            ),
            regional_business_sources_max_items=int(
                os.getenv("REGIONAL_BUSINESS_SOURCES_MAX_ITEMS", "40")
            ),
            regional_business_sources_user_agent=os.getenv(
                "REGIONAL_BUSINESS_SOURCES_USER_AGENT",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125 Safari/537.36",
            ),
            nps_odcloud_enabled=_read_bool("NPS_ODCLOUD_ENABLED", True),
            nps_odcloud_api_key=os.getenv(
                "NPS_ODCLOUD_API_KEY",
                os.getenv("PUBLIC_DATA_NPS_API_KEY", ""),
            ),
            nps_odcloud_base_url=os.getenv(
                "NPS_ODCLOUD_BASE_URL", "https://api.odcloud.kr/api"
            ),
            nps_domestic_stock_docs_url=os.getenv(
                "NPS_DOMESTIC_STOCK_DOCS_URL",
                "https://infuser.odcloud.kr/oas/docs?namespace=3070507/v1",
            ),
            nps_large_holding_docs_url=os.getenv(
                "NPS_LARGE_HOLDING_DOCS_URL",
                "https://infuser.odcloud.kr/oas/docs?namespace=15106890/v1",
            ),
            nps_domestic_stock_api_url=os.getenv(
                "NPS_DOMESTIC_STOCK_API_URL",
                "https://api.odcloud.kr/api/3070507/v1/uddi:1eaca842-2152-4546-9144-a6d9d0fa3a19_201709281515",
            ),
            nps_large_holding_api_url=os.getenv(
                "NPS_LARGE_HOLDING_API_URL",
                "https://api.odcloud.kr/api/15106890/v1/uddi:1bcc0415-377e-44fd-9f08-aa1e813a286c",
            ),
            nps_odcloud_timeout_seconds=float(os.getenv("NPS_ODCLOUD_TIMEOUT_SECONDS", "4")),
            nps_odcloud_max_pages=int(os.getenv("NPS_ODCLOUD_MAX_PAGES", "1")),
            customs_trade_enabled=_read_bool("CUSTOMS_TRADE_ENABLED", True),
            customs_trade_api_key=os.getenv(
                "CUSTOMS_TRADE_API_KEY",
                os.getenv(
                    "PUBLIC_DATA_CUSTOMS_API_KEY",
                    os.getenv("PUBLIC_DATA_API_KEY", os.getenv("NPS_ODCLOUD_API_KEY", "")),
                ),
            ),
            customs_trade_api_url=os.getenv(
                "CUSTOMS_TRADE_API_URL",
                "https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList",
            ),
            customs_trade_total_api_url=os.getenv(
                "CUSTOMS_TRADE_TOTAL_API_URL",
                "https://apis.data.go.kr/1220000/Newtrade/getNewtradeList",
            ),
            customs_trade_total_docs_url=os.getenv(
                "CUSTOMS_TRADE_TOTAL_DOCS_URL",
                "https://www.data.go.kr/data/15102108/openapi.do",
            ),
            customs_trade_timeout_seconds=float(os.getenv("CUSTOMS_TRADE_TIMEOUT_SECONDS", "8")),
            customs_trade_max_rows=int(os.getenv("CUSTOMS_TRADE_MAX_ROWS", "100")),
            customs_trade_release_days=os.getenv("CUSTOMS_TRADE_RELEASE_DAYS", "1,11,21"),
        )

    @property
    def kiwoom_api_base_url(self) -> str:
        if self.kiwoom_use_mock:
            return self.kiwoom_mock_base_url
        return self.kiwoom_base_url

    @property
    def kis_api_base_url(self) -> str:
        if self.kis_use_mock:
            return self.kis_mock_base_url
        return self.kis_base_url


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def mask_secret(value: str) -> str:
    if not value or value == "********":
        return "********"
    if len(value) <= 8:
        return "********"
    return f"{value[:4]}****{value[-4:]}"
