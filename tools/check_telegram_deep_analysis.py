"""Render and safely dry-run the Telegram deep-analysis channel report."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from research_os.settings import Settings  # noqa: E402
from research_os.telegram_brief_delivery import execute_telegram_delivery  # noqa: E402
from research_os.telegram_deep_analysis import (  # noqa: E402
    build_telegram_deep_analysis,
    build_telegram_deep_analysis_payload,
)
from research_os.telegram_favorite_posts import (  # noqa: E402
    TelegramFavoritePopularPost,
    TelegramFavoritePostsRuntime,
    collect_telegram_favorite_popular_posts,
    parse_telegram_favorite_channels_json,
)
from research_os.telegram_market_journal import TelegramMarketPost, fetch_telegram_public_channel_posts  # noqa: E402


ENV_TEMPLATE = """# Telegram deep-analysis report. Keep this ignored, never commit tokens.
TELEGRAM_FAVORITE_CHANNELS_JSON=[{\"username\":\"example_channel\",\"label\":\"Example\",\"max_posts\":30}]
TELEGRAM_DEEP_ANALYSIS_ENABLED=false
TELEGRAM_DEEP_ANALYSIS_TIME=23:08
TELEGRAM_DEEP_ANALYSIS_TOP_N=10
TELEGRAM_DEEP_ANALYSIS_CHAT_ID=
TELEGRAM_DEEP_ANALYSIS_ENTITY_ALIASES_JSON=[]
TELEGRAM_BOT_TOKEN=
"""


def read_env_file(path: Path | None) -> dict[str, str]:
    if not path:
        return {}
    if not path.exists():
        raise SystemExit(f"env file not found: {path}")
    values: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def env_bool(values: dict[str, str], name: str, default: bool = False) -> bool:
    return str(values.get(name, os.getenv(name, str(default)))).strip().lower() in {"1", "true", "yes", "y"}


def env_str(values: dict[str, str], name: str, default: str = "") -> str:
    return str(values.get(name, os.getenv(name, default))).strip()


def sample_posts() -> list[TelegramFavoritePopularPost]:
    return [
        TelegramFavoritePopularPost("aether", "에테르 리서치", "aether/1", "1", "https://t.me/aether/1", "삼성전자 AI 메모리 수요 개선", "삼성전자와 AI 반도체 수요가 개선되고 실적 상향 기대가 확대", "2026-08-29T13:00:00+09:00", 7311, 7311, 185),
        TelegramFavoritePopularPost("usstocks", "미국 주식 인사이더", "usstocks/2", "2", "https://t.me/usstocks/2", "NVIDIA 실적 발표와 데이터센터 성장", "NVIDIA 데이터센터 매출 성장, 다만 금리와 밸류에이션 리스크 확인 필요", "2026-08-29T13:04:00+09:00", 5624, 5624, 25),
        TelegramFavoritePopularPost("macro", "매크로 노트", "macro/3", "3", "https://t.me/macro/3", "금리 불확실성으로 시장 관망", "금리 인하 지연 우려로 기술주 주가 하락 가능성과 리스크를 점검", "2026-08-29T13:06:00+09:00", 2659, 2659, 55),
    ]


def build_runtime() -> TelegramFavoritePostsRuntime:
    return TelegramFavoritePostsRuntime(
        current_storage_date=lambda: datetime.now().date(),
        current_storage_timestamp=lambda: datetime.now().astimezone().isoformat(timespec="seconds"),
        current_storage_datetime=lambda: datetime.now().astimezone(),
        read_json_store=lambda _path, default: default,
        write_json_store=lambda _path, _payload: None,
        read_news_inbox=lambda _settings: {"items": []},
        write_news_inbox=lambda _settings, _payload: None,
        content_fingerprint=lambda value: str(value or ""),
        provider_error_message=lambda exc, _settings: str(exc),
        telegram_favorite_posts_state_path=lambda _settings: PROJECT_ROOT / "tmp" / "telegram_deep_analysis_check_state.json",
        fetch_telegram_public_channel_posts=fetch_telegram_public_channel_posts,
    )


def build_settings(values: dict[str, str]) -> Settings:
    return Settings(
        research_vault_dir=str(PROJECT_ROOT / ".test-tmp" / "telegram-deep-analysis-vault"),
        telegram_favorite_channels_json=env_str(values, "TELEGRAM_FAVORITE_CHANNELS_JSON"),
        telegram_favorite_posts_timeout_seconds=float(env_str(values, "TELEGRAM_FAVORITE_POSTS_TIMEOUT_SECONDS", "10")),
        telegram_favorite_posts_user_agent=env_str(values, "TELEGRAM_FAVORITE_POSTS_USER_AGENT", Settings().telegram_favorite_posts_user_agent),
        telegram_deep_analysis_enabled=env_bool(values, "TELEGRAM_DEEP_ANALYSIS_ENABLED"),
        telegram_deep_analysis_top_n=int(env_str(values, "TELEGRAM_DEEP_ANALYSIS_TOP_N", "10")),
        telegram_deep_analysis_chat_id=env_str(values, "TELEGRAM_DEEP_ANALYSIS_CHAT_ID", env_str(values, "TELEGRAM_CHAT_ID")),
        telegram_deep_analysis_entity_aliases_json=env_str(values, "TELEGRAM_DEEP_ANALYSIS_ENTITY_ALIASES_JSON"),
        telegram_brief_delivery_enabled=env_bool(values, "TELEGRAM_BRIEF_DELIVERY_ENABLED"),
        telegram_brief_delivery_dry_run=env_bool(values, "TELEGRAM_BRIEF_DELIVERY_DRY_RUN", True),
        telegram_bot_token=env_str(values, "TELEGRAM_BOT_TOKEN"),
    )


def load_holding_aliases(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Build aliases from the current persisted holdings, without copying them to .env."""
    if not path.exists():
        return [], [f"보유 종목 파일을 찾을 수 없습니다: {path}"]
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [], [f"보유 종목 파일을 읽을 수 없습니다: {exc}"]
    portfolios = payload.get("portfolios") if isinstance(payload, dict) else None
    if not isinstance(portfolios, dict):
        return [], ["보유 종목 파일에 portfolios 객체가 없습니다."]
    aliases: list[dict[str, str]] = []
    seen: set[str] = set()
    for portfolio in portfolios.values():
        holdings = portfolio.get("holdings") if isinstance(portfolio, dict) else None
        if not isinstance(holdings, list):
            continue
        for holding in holdings:
            if not isinstance(holding, dict):
                continue
            name = str(holding.get("name") or "").strip()
            ticker = str(holding.get("ticker") or "").strip()
            if not name or len(name) < 2 or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            aliases.append({"alias": name, "label": name, "ticker": ticker})
    return aliases, []


def merge_aliases_json(raw_value: str, holding_aliases: list[dict[str, str]]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    entries: list[object] = []
    text = str(raw_value or "").strip()
    if text:
        try:
            parsed = json.loads(text)
            entries = parsed.get("entities", []) if isinstance(parsed, dict) else parsed
            if not isinstance(entries, list):
                warnings.append("사용자 별칭 JSON은 배열 또는 entities 배열이어야 하므로 보유 종목 별칭만 사용합니다.")
                entries = []
        except json.JSONDecodeError as exc:
            warnings.append(f"사용자 별칭 JSON 파싱 실패: {exc.msg}; 보유 종목 별칭만 사용합니다.")
    return json.dumps([*entries, *holding_aliases], ensure_ascii=False), warnings


def redact(value):
    if isinstance(value, dict):
        return {key: ("configured" if key == "chat_id" and item else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def console_print(value: object) -> None:
    """Write Korean output as UTF-8 even when Windows starts Python as cp949."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, OSError, ValueError):
        # Keep the command usable for redirected or non-standard stdout streams.
        pass
    print(str(value))


def main() -> int:
    parser = argparse.ArgumentParser(description="Telegram 심층 분석 리포트를 안전한 dry-run으로 생성합니다.")
    parser.add_argument("--env-file", type=Path, help="ignored env 파일")
    parser.add_argument("--sample", action="store_true", help="샘플 게시글로 렌더링을 검증합니다.")
    parser.add_argument("--live-fetch", action="store_true", help="설정된 공개 t.me/s 채널을 조회합니다.")
    parser.add_argument("--submit", action="store_true", help="명시적으로 실제 채널 전송을 허용합니다.")
    parser.add_argument(
        "--portfolio-file",
        type=Path,
        default=PROJECT_ROOT / "research_vault" / "_system" / "user_portfolios.json",
        help="현재 보유 종목 별칭을 읽을 JSON 파일",
    )
    parser.add_argument("--output-json", type=Path, help="분석 결과 JSON 저장 경로")
    parser.add_argument("--write-env-template", type=Path, help="덮어쓰지 않는 env 템플릿 생성")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.write_env_template:
        output = args.write_env_template if args.write_env_template.is_absolute() else PROJECT_ROOT / args.write_env_template
        if output.exists():
            raise SystemExit(f"refusing to overwrite existing file: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(ENV_TEMPLATE, encoding="utf-8")
        print(f"created env template: {output}")
        return 0
    values = read_env_file(args.env_file)
    settings = build_settings(values)
    channels, channel_warnings = parse_telegram_favorite_channels_json(settings.telegram_favorite_channels_json)
    portfolio_path = args.portfolio_file if args.portfolio_file.is_absolute() else PROJECT_ROOT / args.portfolio_file
    holding_aliases, holding_warnings = load_holding_aliases(portfolio_path)
    merged_aliases_json, alias_warnings = merge_aliases_json(
        settings.telegram_deep_analysis_entity_aliases_json,
        holding_aliases,
    )
    if args.sample:
        posts, warnings = sample_posts(), []
    elif args.live_fetch:
        posts, warnings = collect_telegram_favorite_popular_posts(build_runtime(), settings, limit=0)
    else:
        posts, warnings = [], ["--sample 또는 --live-fetch를 지정하세요. 실제 전송은 --submit도 필요합니다."]
    analysis = build_telegram_deep_analysis(
        posts,
        configured_channel_count=None if args.sample else len(channels),
        entity_aliases_json=merged_aliases_json,
        top_n=settings.telegram_deep_analysis_top_n,
    )
    payload = build_telegram_deep_analysis_payload(analysis, chat_id=settings.telegram_deep_analysis_chat_id)
    submit_blockers = []
    if args.submit:
        if not settings.telegram_deep_analysis_enabled:
            submit_blockers.append("TELEGRAM_DEEP_ANALYSIS_ENABLED=true가 필요합니다.")
        if not settings.telegram_brief_delivery_enabled:
            submit_blockers.append("TELEGRAM_BRIEF_DELIVERY_ENABLED=true가 필요합니다.")
        if settings.telegram_brief_delivery_dry_run:
            submit_blockers.append("TELEGRAM_BRIEF_DELIVERY_DRY_RUN=false가 필요합니다.")
        if not settings.telegram_deep_analysis_chat_id:
            submit_blockers.append("TELEGRAM_DEEP_ANALYSIS_CHAT_ID가 필요합니다.")
        if not settings.telegram_bot_token:
            submit_blockers.append("TELEGRAM_BOT_TOKEN 또는 MARKET_SIGNAL_GRAPH_TELEGRAM_BOT_TOKEN이 필요합니다.")
    delivery = execute_telegram_delivery(
        payload,
        enabled=settings.telegram_brief_delivery_enabled and args.submit and not submit_blockers,
        dry_run=not args.submit or bool(submit_blockers) or settings.telegram_brief_delivery_dry_run,
        bot_token=settings.telegram_bot_token,
    )
    result = {
        "status": "success" if posts and not submit_blockers else "needs_configuration" if submit_blockers or not posts else "success",
        "design": analysis["design"],
        "channel_count": len(channels),
        "post_count": len(posts),
        "holding_alias_count": len(holding_aliases),
        "analysis": analysis,
        "delivery": delivery,
        "submit_blockers": submit_blockers,
        "warnings": [*channel_warnings, *holding_warnings, *alias_warnings, *warnings],
    }
    if args.output_json:
        output = args.output_json if args.output_json.is_absolute() else PROJECT_ROOT / args.output_json
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(redact(result), ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        console_print(json.dumps(redact(result), ensure_ascii=False, indent=2))
    else:
        console_print(payload["text"])
        console_print(f"\n[delivery] {delivery.get('planned_send_count')}건 계획 / dry_run={delivery.get('dry_run')}")
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
