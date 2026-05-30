"""Static contract checks for the classic research console HTML/JS."""

from __future__ import annotations

import argparse
import re
from html.parser import HTMLParser
from pathlib import Path

REQUIRED_IDS = {
    "actionFeedback",
    "dashboardForm",
    "dailyRecommendationsQuickButton",
    "dailyRecommendationsStatusQuickButton",
    "dailyRecommendationsButton",
    "dailyRecommendationsStatusButton",
    "dailyRecommendationCards",
    "portfolioLoadButton",
    "portfolioKiwoomSyncButton",
    "portfolioPerformanceButton",
    "portfolioConsensusScanButton",
    "llmPromptForm",
    "copyLlmPromptButton",
    "llmResultForm",
    "llmStorageStatusButton",
    "researchAutomationStatusButton",
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
    "ragBackfillButton",
    "ocrReprocessButton",
    "storageCleanupButton",
    "dedupedDossierRefreshButton",
    "manifestButton",
    "tickerCacheButton",
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
        self.buttons: list[tuple[str | None, str | None, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        element_id = attr.get("id")
        if element_id:
            self.ids.append(element_id)
        if tag == "section" and element_id:
            self.sections.add(element_id)
        if tag == "button":
            self.buttons.append((element_id, attr.get("data-tab"), attr.get("data-workflow-action")))
            if attr.get("data-tab"):
                self.tab_targets.add(attr["data-tab"] or "")


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
    missing_tabs = sorted(REQUIRED_TABS - parser_obj.sections)
    tab_without_section = sorted(parser_obj.tab_targets - parser_obj.sections)
    section_without_tab = sorted((REQUIRED_TABS & parser_obj.sections) - parser_obj.tab_targets)
    missing_css_snippets = sorted(
        name for name, snippet in REQUIRED_CSS_SNIPPETS.items() if snippet not in css
    )

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
    if missing_tabs:
        errors.append("필수 섹션 누락: " + ", ".join(missing_tabs))
    if tab_without_section:
        errors.append("탭 대상 섹션 누락: " + ", ".join(tab_without_section))
    if section_without_tab:
        errors.append("섹션 탭 누락: " + ", ".join(section_without_tab))
    if missing_css_snippets:
        errors.append("메뉴/버튼 레이아웃 CSS 계약 누락: " + ", ".join(missing_css_snippets))

    print(f"HTML id 수: {len(ids)}개")
    print(f"JS 참조 id 수: {len(referenced_ids)}개")
    print(f"탭 섹션: {len(parser_obj.sections & REQUIRED_TABS)}/{len(REQUIRED_TABS)}개")
    print(f"버튼 수: {len(parser_obj.buttons)}개")
    print(f"피드백 필수 버튼: {len(REQUIRED_FEEDBACK_BUTTON_IDS - set(missing_feedback_buttons) - set(feedback_without_handler))}/{len(REQUIRED_FEEDBACK_BUTTON_IDS)}개")
    print(f"메뉴/버튼 레이아웃 CSS: {len(REQUIRED_CSS_SNIPPETS) - len(missing_css_snippets)}/{len(REQUIRED_CSS_SNIPPETS)}개")
    if errors:
        for error in errors:
            print(f"오류: {error}")
        return 1 if args.strict else 0
    print("클래식 콘솔 정적 계약 정상")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
