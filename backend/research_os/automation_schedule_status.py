"""External source schedule status helpers for automation dashboards."""

from __future__ import annotations


def build_external_source_schedule_status(runtime, settings) -> list[dict]:
    kcif_watch = runtime.read_kcif_reports_watch(settings)
    regional_watch = runtime.read_regional_business_sources_watch(settings)
    policy_watch = runtime.read_policy_sources_watch(settings)
    company_ir_watch = runtime.read_company_ir_sources_watch(settings)
    naver_cache = runtime.read_naver_research_cache(settings)
    shinhan_cache = runtime.read_shinhan_research_cache(settings)
    dart_cache = runtime.read_dart_filing_cache(settings)
    dart_daily = runtime.dart_daily_check_status(dart_cache, settings)
    dart_related_count = (
        int(dart_daily.get("checked_count") or 0)
        or int(dart_daily.get("current_target_count") or dart_daily.get("target_count") or 0)
        or (len(dart_cache.get("items") or []) if isinstance(dart_cache, dict) else 0)
        or (len(dart_cache.get("entries") or {}) if isinstance(dart_cache, dict) else 0)
    )
    return [
        {
            "key": "kcif_reports_watch",
            "label": "KCIF 매크로 보고서",
            "enabled": True,
            "auto_refresh": settings.regional_business_sources_auto_refresh,
            "refresh_hours": settings.regional_business_sources_refresh_hours,
            "last_checked_at": kcif_watch.get("updated_at") if isinstance(kcif_watch, dict) else None,
            "due": runtime.should_refresh_kcif_cache(kcif_watch),
            "related_count": len(kcif_watch.get("related_reports") or []) if isinstance(kcif_watch, dict) else 0,
            "source_status": kcif_watch.get("source_status") if isinstance(kcif_watch, dict) else "not_checked",
            "policy": "metadata_and_derived_signals_only",
        },
        {
            "key": "regional_business_sources_watch",
            "label": "EMERiCs/CSF/KIEP 지역·매크로 자료",
            "enabled": settings.regional_business_sources_enabled,
            "auto_refresh": settings.regional_business_sources_auto_refresh,
            "refresh_hours": settings.regional_business_sources_refresh_hours,
            "last_checked_at": regional_watch.get("updated_at") if isinstance(regional_watch, dict) else None,
            "due": runtime.should_refresh_regional_business_cache(regional_watch),
            "related_count": len(regional_watch.get("related_items") or []) if isinstance(regional_watch, dict) else 0,
            "source_status": regional_watch.get("source_status") if isinstance(regional_watch, dict) else "not_checked",
            "policy": "metadata_and_derived_signals_only",
        },
        {
            "key": "policy_sources_watch",
            "label": "공식 정책·법령·규제 자료",
            "enabled": settings.policy_sources_enabled,
            "auto_refresh": settings.policy_sources_auto_refresh,
            "refresh_hours": settings.policy_sources_refresh_hours,
            "last_checked_at": policy_watch.get("updated_at") if isinstance(policy_watch, dict) else None,
            "due": runtime.should_refresh_policy_sources_cache(
                policy_watch,
                refresh_hours=settings.policy_sources_refresh_hours,
            ),
            "related_count": len(policy_watch.get("related_items") or []) if isinstance(policy_watch, dict) else 0,
            "source_status": policy_watch.get("source_status") if isinstance(policy_watch, dict) else "not_checked",
            "policy": "official_policy_metadata_only",
        },
        {
            "key": "company_ir_sources_watch",
            "label": "Joby IR 보도자료",
            "enabled": settings.company_ir_sources_enabled,
            "auto_refresh": settings.company_ir_sources_auto_refresh,
            "refresh_hours": settings.company_ir_sources_refresh_hours,
            "last_checked_at": company_ir_watch.get("updated_at") if isinstance(company_ir_watch, dict) else None,
            "due": runtime.should_refresh_company_ir_cache(
                company_ir_watch,
                refresh_hours=settings.company_ir_sources_refresh_hours,
            ),
            "related_count": len(company_ir_watch.get("related_items") or []) if isinstance(company_ir_watch, dict) else 0,
            "source_status": company_ir_watch.get("source_status") if isinstance(company_ir_watch, dict) else "not_checked",
            "policy": "public_company_ir_capture_and_rag",
        },
        {
            "key": "naver_research",
            "label": "네이버 금융 리서치/시황",
            "enabled": settings.naver_research_enabled,
            "auto_refresh": settings.naver_research_auto_refresh,
            "refresh_hours": settings.naver_research_refresh_hours,
            "last_checked_at": naver_cache.get("updated_at") if isinstance(naver_cache, dict) else None,
            "due": not isinstance(naver_cache, dict) or not naver_cache.get("updated_at"),
            "related_count": len(naver_cache.get("entries") or {}) if isinstance(naver_cache, dict) else 0,
            "source_status": naver_cache.get("status") if isinstance(naver_cache, dict) else "not_checked",
            "policy": "metadata_and_pdf_snippets_only",
        },
        {
            "key": "shinhan_research",
            "label": "신한 리서치",
            "enabled": settings.shinhan_research_enabled,
            "auto_refresh": settings.shinhan_research_auto_refresh,
            "refresh_hours": settings.shinhan_research_refresh_hours,
            "last_checked_at": shinhan_cache.get("updated_at") if isinstance(shinhan_cache, dict) else None,
            "due": not isinstance(shinhan_cache, dict) or not shinhan_cache.get("updated_at"),
            "related_count": len(shinhan_cache.get("entries") or {}) if isinstance(shinhan_cache, dict) else 0,
            "source_status": shinhan_cache.get("status") if isinstance(shinhan_cache, dict) else "not_checked",
            "policy": "metadata_and_derived_signals_only",
        },
        {
            "key": "dart_filing_watch",
            "label": "DART 보유·관심 공시",
            "enabled": bool(settings.dart_api_key),
            "auto_refresh": settings.dart_filing_auto_refresh,
            "refresh_hours": settings.dart_filing_refresh_hours,
            "last_checked_at": dart_cache.get("updated_at") if isinstance(dart_cache, dict) else None,
            "due": bool(dart_daily.get("due")),
            "related_count": dart_related_count,
            "source_status": dart_cache.get("status") if isinstance(dart_cache, dict) else "not_checked",
            "policy": "official_filings_metadata_and_links",
        },
    ]
