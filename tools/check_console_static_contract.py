"""Static contract checks for the classic research console HTML/JS."""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path

REQUIRED_IDS = {
    "actionFeedback",
    "dashboardForm",
    "dailyRecommendationsQuickButton",
    "dailyRecommendationsStatusQuickButton",
    "recentWeeklyEvidenceSynthesisButton",
    "dailyRecommendationsButton",
    "dailyRecommendationsStatusButton",
    "dailyRecommendationCards",
    "investmentCalendarRefreshButton",
    "investmentCalendarMonthly",
    "investmentCalendarWeekly",
    "portfolioLoadButton",
    "portfolioKiwoomSyncButton",
    "portfolioPerformanceButton",
    "portfolioConsensusScanButton",
    "llmPromptForm",
    "copyLlmPromptButton",
    "llmResultForm",
    "llmStorageStatusButton",
    "researchAutomationStatusButton",
    "codeKnowledgeGraphButton",
    "openClawStatus",
    "output",
    "outputStatus",
}

REQUIRED_FEEDBACK_BUTTON_IDS = {
    "statusButton",
    "dailyRecommendationsQuickButton",
    "dailyRecommendationsStatusQuickButton",
    "dailyRecommendationsButton",
    "dailyRecommendationsStatusButton",
    "copyLlmPromptButton",
    "llmStorageStatusButton",
    "kcifReportsWatchButton",
    "kcifReportsRefreshButton",
    "regionalBusinessSourcesWatchButton",
    "regionalBusinessSourcesRefreshButton",
    "newsInboxButton",
    "newsPromoteLatestButton",
    "customsTradeSnapshotButton",
    "marketCloseHistoryButton",
    "portfolioLoadButton",
    "portfolioKiwoomSyncButton",
    "portfolioKiwoomApplyButton",
    "portfolioKiwoomCancelButton",
    "portfolioSyncHistoryButton",
    "portfolioConnectivityButton",
    "portfolioNpsFlowButton",
    "portfolioNpsAllocationButton",
    "portfolioNpsRebalanceButton",
    "portfolioAnalysisStatusButton",
    "portfolioTeamQueueButton",
    "portfolioRunTopTeamButton",
    "portfolioPerformanceButton",
    "portfolioQuickRiskButton",
    "portfolioSaveButton",
    "portfolioDeleteButton",
    "portfolioOptimizeButton",
    "portfolioImportPickButton",
    "portfolioImportButton",
    "recalculatePortfolioButton",
    "addCashButton",
    "addHoldingButton",
    "portfolioApplyExecutionButton",
    "portfolioSmartRefreshButton",
    "portfolioConsensusScanButton",
    "interestsLoadButton",
    "interestAutomationButton",
    "addInterestTickerButton",
    "addInterestSectorButton",
    "ragNaturalSearchButton",
    "ragSynthesisButton",
    "ragSearchButton",
    "dossierButton",
    "todayResearchUpdateButton",
    "dailyBriefButton",
    "researchAutomationButton",
    "researchAutomationStatusButton",
    "codeKnowledgeGraphButton",
    "ragBackfillButton",
    "ocrReprocessButton",
    "storageCleanupButton",
    "dedupedDossierRefreshButton",
    "manifestButton",
    "tickerCacheButton",
    "publicIrSecFirecrawlDryRunButton",
    "investmentCalendarRefreshButton",
}

FEEDBACK_TOKENS = (
    "registerActionClick",
    "startOutputLoading",
    "showActionFeedback",
    "showActionAccepted",
    "setOutput",
    "attachButtonActionFeedback",
)

REQUIRED_CSS_SNIPPETS = {
    "responsive_tabs": "grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));",
    "tab_wrapping": ".tab {",
    "tab_white_space": "white-space: normal;",
    "tab_word_break": "word-break: keep-all;",
    "tab_overflow_wrap": "overflow-wrap: anywhere;",
    "dashboard_command_width": "grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));",
    "dashboard_button_width": ".dashboard-command-bar button",
    "dashboard_button_min_width": "min-width: 150px;",
    "daily_recommendation_date_groups": ".daily-recommendation-date-groups",
    "daily_recommendation_progress_grid": ".daily-recommendation-progress-grid",
    "daily_recommendation_timeline_steps": ".daily-recommendation-timeline-steps",
    "daily_recommendation_evidence": ".daily-recommendation-evidence",
    "daily_recommendation_citation": "daily-recommendation-citation",
    "daily_recommendation_rank_card": ".daily-recommendation-rank-card",
    "daily_recommendation_rank_trigger": ".daily-recommendation-rank-trigger",
    "daily_recommendation_rank_badge": ".daily-recommendation-rank-badge",
    "daily_recommendation_rank_card_open_state": ".daily-recommendation-rank-card.is-detail-open",
    "daily_recommendation_rank_metrics": ".daily-recommendation-rank-metrics",
    "daily_recommendation_market_section": ".daily-recommendation-market-section",
    "daily_recommendation_market_head": ".daily-recommendation-market-head",
    "daily_recommendation_market_grid": ".daily-recommendation-market-grid",
    "daily_recommendation_us_market_style": ".daily-recommendation-market-section.market-us",
    "daily_recommendation_compact_signal_auto_fit": "grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));",
    "daily_recommendation_mobile_signal_auto_fit": "grid-template-columns: repeat(auto-fit, minmax(136px, 1fr));",
    "daily_recommendation_reason_keep_all": ".daily-recommendation-primary-reasons",
    "daily_recommendation_top_panel": ".daily-recommendation-top-panel",
    "daily_recommendation_top_head": ".daily-recommendation-top-head",
    "daily_recommendation_top_button": ".daily-recommendation-top-head button",
    "daily_recommendation_top_rank": ".daily-recommendation-top-rank",
    "daily_recommendation_investment_profile": ".daily-recommendation-investment-profile",
    "daily_recommendation_investment_profile_badge": "em.investment-profile",
    "openclaw_status_card": ".openclaw-status-card",
    "openclaw_status_metrics": ".openclaw-status-metrics",
    "interest_region_group": ".interest-region-group",
    "interest_region_grid": ".interest-region-grid",
    "interest_region_badge": ".interest-summary-meta b.interest-region",
    "interest_name_only_summary": "grid-template-columns: minmax(0, 1fr) auto;",
    "investment_calendar_grid": ".investment-calendar-grid",
    "investment_calendar_weekly": ".investment-calendar-weekly",
}

REQUIRED_JS_SNIPPETS = {
    "daily_recommendation_result_title": "오늘의 추천 결과",
    "daily_recommendation_rank_layout_text": "한국/미국 1~3위 추천 후보를 카드로 정렬했습니다",
    "daily_recommendation_market_group_helper": "dailyRecommendationMarketGroups",
    "daily_recommendation_market_header_text": "추천 1~3위",
    "daily_recommendation_market_label_usage": "dailyRecommendationMarketLabel(group.market)",
    "daily_recommendation_market_grid_class": "daily-recommendation-market-grid",
    "daily_recommendation_dashboard_top": "${renderDailyRecommendationHomeTopPanel()}",
    "daily_recommendation_top_panel_class": "daily-recommendation-top-panel",
    "daily_recommendation_top_panel_schedule": "매일 08:00 자동 실행",
    "daily_recommendation_top_panel_status_button": "상태 보기",
    "openclaw_status_fetch": "fetchOpenClawStatus",
    "openclaw_status_card_render": "renderOpenClawStatusCard",
    "openclaw_status_label": "openClawStatusLabel",
    "daily_recommendation_top_panel_status_text": "매일 ${schedule} 자동 실행",
    "daily_recommendation_rank_card_class": "daily-recommendation-rank-card",
    "daily_recommendation_rank_trigger": "daily-recommendation-rank-trigger",
    "daily_recommendation_rank_trigger_toggle": 'data-daily-recommendation-toggle="detail"',
    "daily_recommendation_dashboard_open": "openDailyRecommendationDetailFromDashboard",
    "daily_recommendation_dashboard_open_attr": "data-daily-recommendation-open",
    "daily_recommendation_card_interactions": "initializeDailyRecommendationCardInteractions",
    "daily_recommendation_card_toggle": "toggleDailyRecommendationCardDetail",
    "daily_recommendation_card_detail_label": "추천 상세 보기",
    "daily_recommendation_daily_list": "일자별 추천 목록",
    "daily_recommendation_progress_graph": "경과 그래프",
    "daily_recommendation_short_label_helper": "dailyRecommendationMilestoneShortLabel",
    "daily_recommendation_tone_helper": "dailyRecommendationMilestoneTone",
    "daily_recommendation_weekly_evidence_helper": "dailyRecommendationWeeklyEvidenceRows",
    "daily_recommendation_weekly_impact_helper": "dailyRecommendationWeeklyImpactRows",
    "daily_recommendation_exposure_helper": "dailyRecommendationExposureSummary",
    "daily_recommendation_investment_profile_helper": "dailyRecommendationInvestmentProfileSummary",
    "daily_recommendation_investment_profile_line": "투자 방향 반영:",
    "daily_recommendation_investment_profile_badge_text": "투자 방향:",
    "daily_recommendation_investment_profile_text_output": "투자 방향: ${investmentProfile.labelText}",
    "daily_recommendation_exposure_line": "추천 연결:",
    "recent_weekly_recommendation_impact_helper": "recommendationImpactForItem",
    "recent_weekly_impact_summary": "추천 영향 요약",
    "recent_weekly_priority_summary": "우선 확인 요약",
    "recent_weekly_ir_sec_automation_hint": "IR/SEC 자동 활용",
    "recent_weekly_windows_verify_hint": "verify_research_console.ps1",
    "recent_weekly_today_impact_section": "오늘 추천 영향 요약",
    "recent_weekly_target_impact_section": "종목별 추천 영향",
    "recent_weekly_target_impact_helper": "recentWeeklyImpactByTargetLines",
    "recent_weekly_impact_decision": "영향 판정",
    "daily_recommendation_evidence_rows_helper": "dailyRecommendationEvidenceRows",
    "daily_recommendation_citation_rows_helper": "dailyRecommendationCitationRows",
    "daily_recommendation_citation_label": "근거 문서",
    "portfolio_store_freshness_summary": "portfolioStoreFreshnessSummary",
    "portfolio_store_stale_warning": "갱신 권고",
    "code_knowledge_readiness_output": "운영 준비도",
    "code_knowledge_signal_output": "운영 주의 신호",
    "investment_calendar_renderer": "renderInvestmentCalendar",
    "recent_weekly_usage_status_helper": "usageStatusForItem",
    "recent_weekly_status_legend": "상태 기준",
    "recent_weekly_status_recommendation": "추천 반영",
    "recent_weekly_status_reference": "참고만",
    "recent_weekly_status_body_needed": "본문 보강 필요",
    "recent_weekly_status_latest_recommendation_evidence": "오늘 추천 근거",
    "recent_weekly_recommendation_link_summary": "추천 근거 연결",
    "interest_region_group_renderer": "renderInterestRowsByRegion",
    "interest_region_summary_kr": "한국 종목",
    "interest_region_summary_us": "미국 종목",
    "interest_region_label_helper": "interestRegionLabel",
    "recent_weekly_recommendation_linked_section": "추천 근거 연결 자료",
    "recent_weekly_latest_recommendation_linked_section": "오늘 추천 근거 연결 자료",
    "recent_weekly_historical_recommendation_linked_section": "추천 이력 근거 연결 자료",
    "recent_weekly_latest_recommendation_linked_count": "오늘 추천 직접 연결",
    "recent_weekly_recommendation_link_badge": "추천근거 최신",
    "recent_weekly_navigation_hint": "탐색",
    "recent_weekly_rag_query_hint": "RAG 검색어",
    "recent_weekly_next_action_hint": "다음 행동",
    "recent_weekly_action_helper": "actionForItem",
    "recent_weekly_evidence_synthesis_flow": "runRecentWeeklyEvidenceSynthesisFlow",
    "recent_weekly_evidence_synthesis_query": "최근 1주 추천 근거 연결 자료 요약",
    "recent_weekly_evidence_synthesis_title": "추천 근거 요약",
    "recent_weekly_evidence_synthesis_rag_status": "추천 근거 RAG 합성",
    "recent_weekly_evidence_synthesis_storage": "저장된 합성 보고서",
    "telegram_market_close_task_status_api": "fetchTelegramMarketCloseTaskStatus",
    "telegram_market_close_system_check": "텔레그램 미국 시장일지 자동 반영",
    "telegram_market_close_storage_line": "미국 시장일지 저장",
    "telegram_market_close_section_count": "포함 섹션",
    "public_ir_sec_firecrawl_readiness": "Firecrawl IR 보조 수집",
    "public_ir_sec_firecrawl_hosted_api": "Hosted API:",
    "public_ir_sec_firecrawl_dry_run_sample": "Dry-run 샘플:",
    "public_ir_sec_firecrawl_dry_run_button": "Firecrawl IR hosted dry-run",
    "public_ir_sec_firecrawl_dry_run_api": "runPublicIrSecFirecrawlDryRun",
}

REQUIRED_WORKFLOW_ACTIONS = {
    "capture",
    "chart",
    "dart-refresh",
    "dashboard-refresh",
    "diagnose-ticker",
    "earnings",
    "interest-automation",
    "marketData",
    "memory",
    "news",
    "portfolio",
    "refresh-data",
    "reportAutomation",
    "run-team",
    "storage-quality",
    "system-check",
    "team",
    "today-research-update",
}


REQUIRED_LIVE_REGIONS = {
    "actionFeedback": "assertive",
    "dailyRecommendationCards": "polite",
}

REQUIRED_TABS = {
    "dashboard",
    "team",
    "trade",
    "chart",
    "earnings",
    "macro",
    "sector",
    "compounder",
    "capture",
    "news",
    "llmBridge",
    "reportAutomation",
    "marketClose",
    "investmentCalendar",
    "portfolio",
    "interests",
    "checklist",
    "memory",
}


class ConsoleHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.sections: set[str] = set()
        self.tab_targets: set[str] = set()
        self.buttons: list[dict[str, str | None]] = []
        self.workflow_actions: set[str] = set()
        self.attrs_by_id: dict[str, dict[str, str | None]] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        element_id = attr.get("id")
        if element_id:
            self.ids.append(element_id)
            self.attrs_by_id[element_id] = attr
        if tag == "section" and element_id:
            self.sections.add(element_id)
        if tag == "button":
            workflow_action = attr.get("data-workflow-action")
            self.buttons.append({"id": element_id, "data_tab": attr.get("data-tab"), "workflow_action": workflow_action, "type": attr.get("type")})
            if attr.get("data-tab"):
                self.tab_targets.add(attr["data-tab"] or "")
            if workflow_action:
                self.workflow_actions.add(workflow_action)


def project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "mobile_app" / "research_console" / "index.html").exists() and (
            candidate / "mobile_app" / "research_console" / "console.js"
        ).exists():
            return candidate
    raise SystemExit("InvestmentJournalApp 프로젝트 루트를 찾지 못했습니다.")


def selector_ids(js_text: str) -> set[str]:
    ids: set[str] = set()
    patterns = [
        r"querySelector\(\s*['\"]#([A-Za-z0-9_-]+)['\"]\s*\)",
        r"getElementById\(\s*['\"]([A-Za-z0-9_-]+)['\"]\s*\)",
    ]
    for pattern in patterns:
        ids.update(re.findall(pattern, js_text))
    return ids


def workflow_actions_in_js_templates(js_text: str) -> set[str]:
    return set(re.findall(r"data-workflow-action=['\"]([^'\"]+)['\"]", js_text))


def js_button_tags(js_text: str) -> list[str]:
    return re.findall(r"<button\b[^>]*>", js_text, flags=re.IGNORECASE)


def button_label(button: dict[str, str | None]) -> str:
    return button.get("id") or button.get("data_tab") or button.get("workflow_action") or "button"


def handled_workflow_actions(js_text: str) -> set[str]:
    actions = set(re.findall(r"action\s*===\s*['\"]([^'\"]+)['\"]", js_text))
    match = re.search(r"const\s+actionToTab\s*=\s*\{(?P<body>.*?)\n\s*\};", js_text, re.S)
    if match:
        actions.update(
            re.findall(r"^\s*['\"]?([A-Za-z0-9_-]+)['\"]?\s*:", match.group("body"), re.M)
        )
    return actions


def button_has_feedback(js_text: str, button_id: str) -> bool:
    positions = [match.start() for match in re.finditer(re.escape(button_id), js_text)]
    for position in positions:
        context = js_text[max(0, position - 900): position + 1400]
        if any(token in context for token in FEEDBACK_TOKENS):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="클래식 콘솔 HTML/JS 정적 계약을 점검합니다.")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true", help="점검 결과를 JSON으로 출력합니다.")
    args = parser.parse_args()

    root = project_root(Path.cwd())
    html_path = root / "mobile_app" / "research_console" / "index.html"
    js_path = root / "mobile_app" / "research_console" / "console.js"
    css_path = root / "mobile_app" / "research_console" / "styles.css"
    parser_obj = ConsoleHtmlParser()
    html = html_path.read_text(encoding="utf-8")
    js = js_path.read_text(encoding="utf-8")
    css = css_path.read_text(encoding="utf-8")
    parser_obj.feed(html)

    ids = set(parser_obj.ids)
    duplicate_ids = sorted({element_id for element_id in parser_obj.ids if parser_obj.ids.count(element_id) > 1})
    referenced_ids = selector_ids(js)
    missing_referenced = sorted(referenced_ids - ids)
    missing_required = sorted(REQUIRED_IDS - ids)
    missing_feedback_buttons = sorted(REQUIRED_FEEDBACK_BUTTON_IDS - ids)
    feedback_without_handler = sorted(
        button_id
        for button_id in REQUIRED_FEEDBACK_BUTTON_IDS & ids
        if not button_has_feedback(js, button_id)
    )
    workflow_actions = parser_obj.workflow_actions | workflow_actions_in_js_templates(js)
    handled_actions = handled_workflow_actions(js)
    missing_required_workflow_actions = sorted(REQUIRED_WORKFLOW_ACTIONS - workflow_actions)
    workflow_actions_without_handler = sorted(workflow_actions - handled_actions)
    missing_tabs = sorted(REQUIRED_TABS - parser_obj.sections)
    tab_without_section = sorted(parser_obj.tab_targets - parser_obj.sections)
    section_without_tab = sorted((REQUIRED_TABS & parser_obj.sections) - parser_obj.tab_targets)
    missing_css_snippets = sorted(
        name for name, snippet in REQUIRED_CSS_SNIPPETS.items() if snippet not in css
    )
    missing_js_snippets = sorted(
        name for name, snippet in REQUIRED_JS_SNIPPETS.items() if snippet not in js
    )
    missing_live_regions = sorted(
        f"{element_id} aria-live={expected}"
        for element_id, expected in REQUIRED_LIVE_REGIONS.items()
        if parser_obj.attrs_by_id.get(element_id, {}).get("aria-live") != expected
    )
    html_buttons_missing_type = sorted(
        button_label(button)
        for button in parser_obj.buttons
        if not str(button.get("type") or "").strip()
    )
    html_buttons_invalid_type = sorted(
        f"{button_label(button)}:{button.get('type')}"
        for button in parser_obj.buttons
        if str(button.get("type") or "").strip().lower() not in {"button", "submit", "reset"}
    )
    js_buttons = js_button_tags(js)
    js_buttons_missing_type = sorted(button for button in js_buttons if "type=" not in button.lower())

    errors: list[str] = []
    if duplicate_ids:
        errors.append("중복 id: " + ", ".join(duplicate_ids))
    if missing_referenced:
        errors.append("JS selector 대상 누락: " + ", ".join(missing_referenced[:20]))
    if missing_required:
        errors.append("필수 UI id 누락: " + ", ".join(missing_required))
    if missing_feedback_buttons:
        errors.append("피드백 필수 버튼 id 누락: " + ", ".join(missing_feedback_buttons))
    if feedback_without_handler:
        errors.append("즉시 피드백/로딩 연결 누락 버튼: " + ", ".join(feedback_without_handler))
    if missing_required_workflow_actions:
        errors.append("필수 워크플로우 버튼 누락: " + ", ".join(missing_required_workflow_actions))
    if workflow_actions_without_handler:
        errors.append("워크플로우 핸들러 누락: " + ", ".join(workflow_actions_without_handler))
    if missing_tabs:
        errors.append("필수 섹션 누락: " + ", ".join(missing_tabs))
    if tab_without_section:
        errors.append("탭 대상 섹션 누락: " + ", ".join(tab_without_section))
    if section_without_tab:
        errors.append("섹션 탭 누락: " + ", ".join(section_without_tab))
    if missing_css_snippets:
        errors.append("메뉴/버튼 레이아웃 CSS 계약 누락: " + ", ".join(missing_css_snippets))
    if missing_js_snippets:
        errors.append("추천 결과 UI JS 계약 누락: " + ", ".join(missing_js_snippets))
    if missing_live_regions:
        errors.append("실시간 피드백 aria-live 계약 누락: " + ", ".join(missing_live_regions))
    if html_buttons_missing_type:
        errors.append("HTML 버튼 type 속성 누락: " + ", ".join(html_buttons_missing_type))
    if html_buttons_invalid_type:
        errors.append("HTML 버튼 type 값 확인 필요: " + ", ".join(html_buttons_invalid_type))
    if js_buttons_missing_type:
        errors.append("JS 템플릿 버튼 type 속성 누락: " + ", ".join(js_buttons_missing_type[:20]))

    result = {
        "status": "error" if errors else "ok",
        "project_root": str(root),
        "html_id_count": len(ids),
        "js_referenced_id_count": len(referenced_ids),
        "tab_section_count": len(parser_obj.sections & REQUIRED_TABS),
        "required_tab_count": len(REQUIRED_TABS),
        "button_count": len(parser_obj.buttons),
        "feedback_button_ok_count": len(REQUIRED_FEEDBACK_BUTTON_IDS - set(missing_feedback_buttons) - set(feedback_without_handler)),
        "required_feedback_button_count": len(REQUIRED_FEEDBACK_BUTTON_IDS),
        "workflow_action_ok_count": len(workflow_actions - set(workflow_actions_without_handler)),
        "workflow_action_count": len(workflow_actions),
        "css_contract_ok_count": len(REQUIRED_CSS_SNIPPETS) - len(missing_css_snippets),
        "css_contract_count": len(REQUIRED_CSS_SNIPPETS),
        "js_contract_ok_count": len(REQUIRED_JS_SNIPPETS) - len(missing_js_snippets),
        "js_contract_count": len(REQUIRED_JS_SNIPPETS),
        "live_region_ok_count": len(REQUIRED_LIVE_REGIONS) - len(missing_live_regions),
        "live_region_count": len(REQUIRED_LIVE_REGIONS),
        "html_button_type_ok_count": len(parser_obj.buttons) - len(html_buttons_missing_type) - len(html_buttons_invalid_type),
        "js_button_type_ok_count": len(js_buttons) - len(js_buttons_missing_type),
        "js_button_count": len(js_buttons),
        "errors": errors,
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if args.strict and errors else 0

    print(f"HTML id 수: {len(ids)}개")
    print(f"JS 참조 id 수: {len(referenced_ids)}개")
    print(f"탭 섹션: {len(parser_obj.sections & REQUIRED_TABS)}/{len(REQUIRED_TABS)}개")
    print(f"버튼 수: {len(parser_obj.buttons)}개")
    print(f"피드백 필수 버튼: {len(REQUIRED_FEEDBACK_BUTTON_IDS - set(missing_feedback_buttons) - set(feedback_without_handler))}/{len(REQUIRED_FEEDBACK_BUTTON_IDS)}개")
    print(f"워크플로우 버튼: {len(workflow_actions - set(workflow_actions_without_handler))}/{len(workflow_actions)}개")
    print(f"메뉴/버튼 레이아웃 CSS: {len(REQUIRED_CSS_SNIPPETS) - len(missing_css_snippets)}/{len(REQUIRED_CSS_SNIPPETS)}개")
    print(f"추천 결과 UI JS: {len(REQUIRED_JS_SNIPPETS) - len(missing_js_snippets)}/{len(REQUIRED_JS_SNIPPETS)}개")
    print(f"실시간 피드백 영역: {len(REQUIRED_LIVE_REGIONS) - len(missing_live_regions)}/{len(REQUIRED_LIVE_REGIONS)}개")
    print(f"HTML 버튼 타입: {len(parser_obj.buttons) - len(html_buttons_missing_type) - len(html_buttons_invalid_type)}/{len(parser_obj.buttons)}개")
    print(f"JS 템플릿 버튼 타입: {len(js_buttons) - len(js_buttons_missing_type)}/{len(js_buttons)}개")
    if errors:
        for error in errors:
            print(f"오류: {error}")
        return 1 if args.strict else 0
    print("클래식 콘솔 정적 계약 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
