from __future__ import annotations


def automation_board_targets(board: dict) -> list[dict]:
    return [
        *[item for item in board.get("ticker_targets", []) if isinstance(item, dict)],
        *[item for item in board.get("sector_targets", []) if isinstance(item, dict)],
    ]


def select_priority_targets(targets: list[dict]) -> list[dict]:
    return sorted(
        targets,
        key=lambda item: (
            {"high": 3, "medium": 2, "low": 1}.get(str(item.get("priority")), 2),
            int(item.get("recent_document_count") or 0),
            int(item.get("rag_document_count") or 0),
        ),
        reverse=True,
    )[:5]


def project_priority_targets(priority_targets: list[dict]) -> list[dict]:
    return [
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
    ]


def build_source_quality_dashboard(
    *,
    dart_daily: dict,
    news_quality_issue_count: int,
    news_items: list[dict],
    status: dict,
    kcif_due: bool,
    kcif_related_count: int,
    kcif_watch: dict,
    regional_sources_due: bool,
    regional_sources_related_count: int,
    regional_sources_watch: dict,
    telegram_favorite_state: dict | None = None,
    telegram_favorite_enabled: bool = False,
    telegram_favorite_channel_count: int = 0,
    telegram_favorite_due: bool = False,
) -> list[dict]:
    telegram_state = telegram_favorite_state if isinstance(telegram_favorite_state, dict) else {}
    telegram_status = str(telegram_state.get("status") or "not_checked")
    telegram_warnings = telegram_state.get("warnings") if isinstance(telegram_state.get("warnings"), list) else []
    if not telegram_favorite_enabled:
        telegram_display_status = "꺼짐"
    elif telegram_status == "error" or telegram_warnings:
        telegram_display_status = "주의"
    elif telegram_favorite_due:
        telegram_display_status = "점검 필요"
    elif telegram_status in {"success", "ok"}:
        telegram_display_status = "정상"
    elif telegram_status == "not_found":
        telegram_display_status = "확인 완료"
    else:
        telegram_display_status = "미점검"
    telegram_candidate_count = int(telegram_state.get("candidate_count") or 0)
    telegram_saved_count = int(telegram_state.get("saved_count") or 0)
    return [
        {
            "source": "DART 공시",
            "status": "점검 필요" if dart_daily.get("due") else ("주의" if dart_daily.get("failure_count") else "정상"),
            "copyright_policy": "공시 원문/메타데이터 저장",
            "duplicate_guard": "공시번호 기준 중복 제외",
            "related_count": int(dart_daily.get("target_count") or dart_daily.get("coverage_count") or 0),
            "last_checked_at": dart_daily.get("last_checked_at") or dart_daily.get("checked_at"),
            "detail": dart_daily.get("summary") or f"실패 {dart_daily.get('failure_count') or 0}건",
        },
        {
            "source": "네이버 리서치/시장일지",
            "status": "주의" if news_quality_issue_count else "정상",
            "copyright_policy": "저작권 안전 요약/메타데이터 중심",
            "duplicate_guard": "source_url/content_hash/제목 유사도 중복 제외",
            "related_count": len(news_items),
            "last_checked_at": status.get("naver_research_checked_at") or status.get("updated_at"),
            "detail": f"뉴스 인박스 {len(news_items)}개 · 품질 확인 {news_quality_issue_count}개",
        },
        {
            "source": "KIEP/KCIF 매크로",
            "status": "점검 필요" if kcif_due else "정상",
            "copyright_policy": "제목·발행일·링크·요약 메타데이터 활용",
            "duplicate_guard": "보고서 URL/제목 기준 중복 제외",
            "related_count": kcif_related_count,
            "last_checked_at": kcif_watch.get("updated_at") if isinstance(kcif_watch, dict) else None,
            "detail": "매크로 보고서 일일 점검",
        },
        {
            "source": "EMERiCs/CSF/지역자료",
            "status": "점검 필요" if regional_sources_due else "정상",
            "copyright_policy": "제목·링크·발행기관·요약 메타데이터 활용",
            "duplicate_guard": "URL/제목 기준 중복 제외",
            "related_count": regional_sources_related_count,
            "last_checked_at": regional_sources_watch.get("updated_at")
            if isinstance(regional_sources_watch, dict)
            else None,
            "detail": "지역·중국·신흥국 리스크 소스 일일 점검",
        },
        {
            "source": "텔레그램 즐겨찾기 인기글",
            "status": telegram_display_status,
            "copyright_policy": "공개 t.me preview의 제목·링크·조회수·짧은 메모만 활용",
            "duplicate_guard": "게시글 URL/지문 기준 뉴스 인박스 중복 제외",
            "related_count": telegram_candidate_count,
            "last_checked_at": telegram_state.get("last_attempt_at") or telegram_state.get("last_run_at"),
            "detail": (
                f"채널 {telegram_favorite_channel_count}개 · 후보 {telegram_candidate_count}개 · "
                f"신규 {telegram_saved_count}개"
            ),
        },
    ]


def automation_tone(
    *,
    failed_count: int,
    news_quality_issue_count: int,
    target_count: int,
    daily_brief_date: object,
) -> tuple[str, str]:
    tone = "ok"
    headline = "자동화 정상"
    if failed_count or news_quality_issue_count:
        tone = "warning"
        headline = "확인 필요"
    if not target_count or not daily_brief_date:
        tone = "needs_action"
        headline = "업데이트 필요"
    return tone, headline


def _short_title(value: object, *, limit: int = 70) -> str:
    title = str(value or "").strip()
    if len(title) <= limit:
        return title
    return f"{title[: limit - 1]}..."


def _watch_item_action(
    watch: dict | None,
    *,
    item_keys: tuple[str, ...],
    source_label: str,
    fallback_count: int,
    fallback: str,
) -> str:
    if not isinstance(watch, dict):
        return fallback
    item = None
    for key in item_keys:
        rows = watch.get(key)
        if isinstance(rows, list) and rows:
            item = next((row for row in rows if isinstance(row, dict)), None)
            if item:
                break
    if not item:
        return fallback

    title = _short_title(item.get("title")) or "상위 자료"
    themes = [str(theme).strip() for theme in (item.get("matched_themes") or []) if str(theme).strip()]
    theme_text = ", ".join(themes[:3]) if themes else "매크로/지역 리스크"
    target_matches = item.get("target_matches") or item.get("matched_targets") or []
    target_count = len(target_matches) if isinstance(target_matches, list) else 0
    target_suffix = f" · 보유/관심 연결 {target_count}개" if target_count else ""
    count_suffix = f" (관련 {fallback_count}개)" if fallback_count else ""
    return f"{source_label} 최우선 `{title}`를 {theme_text} 관점의 시장일지/리스크 메모에 반영하세요{target_suffix}{count_suffix}."


def build_dashboard_next_actions(
    *,
    target_count: int,
    daily_brief_date: object,
    duplicate_count: int,
    failed_count: int,
    news_unpromoted_count: int,
    news_actionable_unpromoted_count: int | None,
    news_quality_issue_count: int,
    kcif_due: bool,
    kcif_related_count: int,
    regional_sources_due: bool,
    regional_sources_related_count: int,
    dart_daily: dict,
    daily_recommendations_due: bool,
    daily_recommendations: dict,
    kcif_watch: dict | None = None,
    regional_sources_watch: dict | None = None,
    duplicate_refresh_candidate_count: int | None = None,
    news_duplicate_priority_group_count: int = 0,
    news_duplicate_priority_entry_count: int = 0,
    telegram_favorite_count: int = 0,
    telegram_favorite_top_posts: list[dict] | None = None,
    telegram_favorite_due: bool = False,
) -> list[str]:
    next_actions = []
    if not target_count:
        next_actions.append("포트폴리오나 관심목록을 저장해 자동 수집 대상을 먼저 구성하세요.")
    if not daily_brief_date:
        next_actions.append("오늘 리서치 업데이트를 실행해 일일 브리핑을 생성하세요.")
    if duplicate_count and duplicate_refresh_candidate_count == 0:
        next_actions.append(
            f"중복 의심 자료 {duplicate_count}개는 대표 자료 정책으로 Dossier/추천 근거에서 제외됐고, 재합성 후보는 없습니다."
        )
    elif duplicate_count:
        next_actions.append(f"중복 의심 자료 {duplicate_count}개를 Dossier 합성에서 묶어 확인하세요.")
    if failed_count:
        next_actions.append(f"자동화 실패 {failed_count}건의 API/소스 상태를 점검하세요.")
    if news_duplicate_priority_group_count and news_duplicate_priority_entry_count:
        next_actions.append(
            f"뉴스 우선 분류 중복 후보 {news_duplicate_priority_group_count}묶음/"
            f"{news_duplicate_priority_entry_count}개를 먼저 보류·통합하세요."
        )
    if news_unpromoted_count:
        if news_actionable_unpromoted_count and news_actionable_unpromoted_count < news_unpromoted_count:
            next_actions.append(
                f"뉴스 인박스 우선 분류 {news_actionable_unpromoted_count}개를 먼저 확인하세요"
                f"(전체 미승격 {news_unpromoted_count}개)."
            )
        else:
            next_actions.append(f"뉴스 인박스 미승격 자료 {news_unpromoted_count}개를 논거/시장일지 반영 여부로 분류하세요.")
    if news_quality_issue_count:
        next_actions.append(f"뉴스 본문 추출 품질 경고 {news_quality_issue_count}개를 원문 링크나 본문 붙여넣기로 보강하세요.")
    if kcif_due:
        next_actions.append("KCIF 매크로 보고서 목록 일일 점검이 필요합니다.")
    elif kcif_related_count:
        next_actions.append(
            _watch_item_action(
                kcif_watch,
                item_keys=("related_reports", "reports"),
                source_label="KCIF",
                fallback_count=kcif_related_count,
                fallback=f"KCIF 관련 매크로 보고서 {kcif_related_count}개를 시장일지/보유종목 리스크 메모와 연결하세요.",
            )
        )
    if regional_sources_due:
        next_actions.append("EMERiCs/CSF/KIEP 지역·매크로 자료 일일 점검이 필요합니다.")
    elif regional_sources_related_count:
        next_actions.append(
            _watch_item_action(
                regional_sources_watch,
                item_keys=("related_items", "items"),
                source_label="EMERiCs/CSF/KIEP",
                fallback_count=regional_sources_related_count,
                fallback=(
                    f"EMERiCs/CSF/KIEP 관련 자료 {regional_sources_related_count}개를 "
                    "시장일지/보유종목 리스크 메모와 연결하세요."
                ),
            )
        )
    if telegram_favorite_due:
        next_actions.append("텔레그램 즐겨찾기 인기글 22:00 자동 수집 상태를 확인하세요.")
    elif telegram_favorite_count:
        top_posts = telegram_favorite_top_posts if isinstance(telegram_favorite_top_posts, list) else []
        first_post = next((post for post in top_posts if isinstance(post, dict)), {})
        title = _short_title(first_post.get("title"), limit=60) if first_post else "상위 인기글"
        channel = first_post.get("channel_label") or first_post.get("channel_username") or "텔레그램"
        next_actions.append(
            f"텔레그램 인기글 {telegram_favorite_count}개 중 `{channel} · {title}`를 시장 심리/뉴스 반영 후보로 확인하세요."
        )
    if dart_daily.get("due"):
        next_actions.append("보유·관심 종목 DART 신규 공시 일일 점검이 필요합니다.")
    elif dart_daily.get("failure_count"):
        next_actions.append(f"DART 공시 점검 실패 {dart_daily.get('failure_count')}개 종목을 확인하세요.")
    if daily_recommendations_due:
        next_actions.append("오늘의 한국/미국 추천 후보 1~3위 생성과 사후 추적 저장이 필요합니다.")
    elif daily_recommendations.get("latest_recommendation_date"):
        next_actions.append(
            f"{daily_recommendations.get('latest_recommendation_date')} 한국/미국 추천 후보 1~3위가 별도 항목에 저장되어 있습니다."
        )
    if not next_actions:
        next_actions.append("보유·관심 대상의 새 자료를 수집하고 Dossier/일일 브리핑에 반영할 준비가 되어 있습니다.")
    return next_actions
