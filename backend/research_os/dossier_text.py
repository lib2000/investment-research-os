"""Dossier text cleanup, fingerprinting, and similarity helpers."""

from __future__ import annotations

import hashlib
from pathlib import Path
from re import findall, search, sub


DOSSIER_POSITIVE_TERMS = {
    "상향",
    "개선",
    "강세",
    "호조",
    "성장",
    "수요",
    "수주",
    "확대",
    "마진 개선",
    "가이던스 상향",
    "beat",
    "raise",
    "raised",
    "growth",
    "demand",
    "margin expansion",
    "upside",
}

DOSSIER_NEGATIVE_TERMS = {
    "하향",
    "악화",
    "약세",
    "둔화",
    "하회",
    "약화",
    "하락",
    "적자",
    "못 미쳤",
    "제한적",
    "부진",
    "리스크",
    "경쟁",
    "현금 소진",
    "마진 압박",
    "가이던스 하향",
    "miss",
    "cut",
    "risk",
    "slowdown",
    "downside",
    "cash burn",
}

DOSSIER_FACT_TERMS = {
    "매출",
    "영업이익",
    "순이익",
    "EPS",
    "가이던스",
    "수주",
    "계약",
    "마진",
    "현금",
    "FCF",
    "고객",
    "시장",
    "섹터",
    "정책",
    "금리",
    "revenue",
    "guidance",
    "margin",
    "cash",
    "contract",
    "customer",
}

DOSSIER_ALLOWED_REPORT_TYPES = {
    "collaborative-team-report",
    "institutional-stock-breakdown",
    "earnings-reaction",
    "research-capture",
    "market-close-review",
    "sector-opportunity",
    "compounder-finder",
}

DOSSIER_EXCLUDED_REPORT_TYPES = {
    "dossier-synthesis",
    "rag-query-synthesis",
    "thesis-impact-review",
    "smart-trade-setup",
    "research-checklist",
    "chart-analysis",
    "portfolio-risk-scan",
    "reinforcement-portfolio-optimizer",
    "daily-dossier-brief",
}


def content_fingerprint(text: str | None) -> str:
    normalized = " ".join(str(text or "").lower().split())
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def similarity_tokens(text: str | None) -> set[str]:
    normalized = sub(r"[^0-9a-zA-Z가-힣]+", " ", str(text or "").lower())
    tokens = {
        token
        for token in normalized.split()
        if len(token) >= 2 and token not in {"the", "and", "for", "with", "from", "this", "that"}
    }
    return tokens


def token_jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, len(left | right))


def manifest_similarity_text(entry: dict, text: str | None = None) -> str:
    # source_url/file_name은 exact match에는 유용하지만 유사도 토큰에 넣으면
    # 같은 사이트의 서로 다른 리포트까지 과하게 중복으로 묶일 수 있다.
    body = str(text or "")
    try:
        if body:
            body = " ".join(plain_research_lines(body, limit=40))
    except NameError:
        body = body[:2400]
    return " ".join(
        str(part or "")
        for part in [
            entry.get("title"),
            entry.get("summary"),
            body[:2400],
        ]
    )


def add_unique_text(items: list[str], value: str | None, limit: int = 8) -> None:
    cleaned = " ".join(str(value or "").split())
    if cleaned and cleaned not in items and len(items) < limit:
        items.append(cleaned)


DOSSIER_NOISE_TERMS = {
    "[네이버 금융 리서치 자동 수집]",
    "분류:",
    "기타 /",
    "투자 정보 캡처",
    "분류 근거:",
    "증권사:",
    "종목명:",
    "종목코드:",
    "발행일:",
    "저장 범위:",
    "원문 링크:",
    "pdf 링크:",
    "활용 메모:",
    "source_url",
    "source type",
    "source_type",
    "source_file",
    "source_relative_path",
    "content_hash",
    "attachment",
    "json_relative_path",
    "json_file_name",
    "official_company_profile",
    "DataSourceType.",
    "DataSourceType.EARNINGS_RELEASE",
    "DataSourceType.MARKET_PRICE",
    "DataSourceType.FINANCIAL_STATEMENT",
    "리서치 메모리 / latest_thesis_snapshot",
    "리서치 메모리 / rag_memory_document",
    "latest_thesis_snapshot",
    "rag_memory_document",
    "주입된 데이터 컨텍스트",
    "injected_data",
    "DataSourceType.RESEARCH_MEMORY",
    "DataSourceType.OTHER",
    "저장된 투자 논거가 없어",
    "판단 이유: 이 정보는 신뢰도",
    "새 데이터는 평균 신뢰도",
    "매매전략 탭에서",
    "매매 전략:",
    "포트폴리오 리스크 스캔",
    "기관급 분석",
    "스마트 매매 전략",
    "실적 발표 반응 분석",
    "장기 복리 성장주 발굴",
    "리서치 체크리스트",
    "관점의 핵심 판단",
    "주의 관점:",
    "다음 실적 체크포인트:",
    "직전/최신 실적 메모:",
    "정확한 매출",
    "회사 공시 또는 DART",
    "보강해야",
    "DART/IR 자료",
    "주입 데이터",
    "빠른 정보 저장",
    "재실행",
    "시나리오를 갱신",
    "기준/강세/약세",
    "기준 시나리오의 성장 가정을 하회",
    "이전 가이던스",
    "리스크 예산 초과",
    "포지션 크기를",
    "센티먼트가 개선이면",
    "하는지 확인",
    "방향과 일치하는지",
    "매출 및 수주상황",
    "[첨부 파일]",
    "파일명:",
    "글로벌리더",
    "거래정지 기간 동안",
    "7개 분석 스킬",
    "생성했습니다",
    "실적은 '긍정적 확인'",
    "주가 반응은 미입력",
    "입력되지 않았습니다",
    "보강하세요",
    "다음 실적 전 확인할 KPI",
    "가이던스 평가:",
    "역할:",
    "페르소나:",
    "중점 분석:",
    "체크리스트",
    "보강 필요 입력",
    "표시할 데이터 경고가 없습니다",
    "저장 파일:",
    "저장 데이터:",
    "태그:",
    "tags:",
    "auto_ingested",
    "auto_classified",
    "auto_ticker:",
    "naver_category:",
    "naver_research",
    "가격/리스크 조건을 분리",
    "새 데이터가 들어올 때마다",
    "긍정 관점:",
    "정리:",
    "포지션은 리스크 예산",
    "포트폴리오 리스크 예산",
    "경쟁 우위 훼손",
    "센티먼트가 악화",
    "밸류에이션 범위를 단일 목표가",
    "현재가와 최근 변동성 데이터를",
    "진입 구간, 손절, 목표가를 자동 보정",
    "손익비가",
    "실적 발표 전후에는 포지션 사이즈",
    "장기 복리 후보 여부는",
    "관찰 목록 유지",
    "com/research/company_read",
    "com/research/industry_read",
}


def is_dossier_noise_line(line: str) -> bool:
    cleaned = " ".join(str(line or "").split())
    lowered = cleaned.lower()
    if not cleaned:
        return True
    if cleaned.startswith(("[x]", "[ ]")):
        return True
    if cleaned[0] in {",", ".", ")", "]", "}"}:
        return True
    if cleaned.count(".") >= 8:
        return True
    if cleaned.startswith(("이었", "였", "및 ", "을 ", "를 ", "는 ", "하며", "했고", "화,", "동안 ", "지했다", "(YoY", "악된다", "기의 ")):
        return True
    if len(cleaned) < 24 and not any(ch.isdigit() for ch in cleaned):
        return True
    return any(term.lower() in lowered for term in DOSSIER_NOISE_TERMS)


def is_allowed_dossier_source_entry(entry: dict) -> bool:
    report_type = str(entry.get("type") or "").strip().lower()
    if report_type in DOSSIER_EXCLUDED_REPORT_TYPES:
        return False
    if report_type not in DOSSIER_ALLOWED_REPORT_TYPES:
        return False
    summary = str(entry.get("summary") or "")
    tags = {str(tag).strip().lower() for tag in (entry.get("tags") or []) if str(tag).strip()}
    if {"naver_research", "auto_ingested"} <= tags and len(summary) < 260:
        return False
    return True


def is_research_line_continuation(line: str) -> bool:
    cleaned = str(line or "").strip()
    return bool(
        cleaned
        and (
            cleaned[0] in {",", ".", ")", "]", "}", "%"}
            or cleaned.startswith(
                (
                    "은 ",
                    "는 ",
                    "을 ",
                    "를 ",
                    "이 ",
                    "가 ",
                    "와 ",
                    "과 ",
                    "으로",
                    "로 ",
                    "며 ",
                    "고 ",
                    "다.",
                )
            )
        )
    )


def should_merge_research_lines(previous: str, current: str) -> bool:
    prev = str(previous or "").strip()
    cur = str(current or "").strip()
    if not prev or not cur:
        return False
    if is_research_line_continuation(cur):
        return True
    if prev.endswith(("은", "는", "이", "가", "을", "를", "및", "로", "으로", "영업이익은", "매출액은")):
        return True
    return False


def extract_scenario_clause(line: str, mode: str) -> str:
    cleaned = " ".join(str(line or "").split())
    if mode == "bull" and "강세:" in cleaned:
        clause = cleaned.split("강세:", 1)[1]
        for marker in ("기준:", "약세:"):
            clause = clause.split(marker, 1)[0]
        return clause.strip()
    if mode == "bear" and "약세:" in cleaned:
        return cleaned.split("약세:", 1)[1].strip()
    return cleaned


def clean_dossier_signal(line: str, mode: str = "generic") -> str:
    candidate = extract_scenario_clause(line, mode) if mode in {"bull", "bear"} else " ".join(str(line or "").split())
    candidate = sub(r"^(강세|약세|기준|요약)\s*:\s*", "", candidate).strip()
    candidate = candidate.strip(" -•")
    if not candidate or is_dossier_noise_line(candidate):
        return ""
    return compact_representative_sentence(candidate, 220)


def add_dossier_signal(items: list[str], line: str, mode: str, limit: int) -> None:
    candidate = clean_dossier_signal(line, mode)
    if not candidate:
        return
    if mode == "bull" and "강세:" not in str(line) and line_has_any(candidate, DOSSIER_NEGATIVE_TERMS) and not line_has_negated_bear_context(candidate):
        return
    if mode == "bear" and "약세:" not in str(line) and line_has_any(candidate, DOSSIER_POSITIVE_TERMS) and not line_has_any(candidate, DOSSIER_NEGATIVE_TERMS):
        return
    if mode == "bear" and line_has_negated_bear_context(candidate):
        return
    if len(candidate) < 24 and not any(ch.isdigit() for ch in candidate):
        return
    add_unique_text(items, candidate, limit=limit)


def representative_thesis_line(items: list[str], fallback: str, mode: str = "generic") -> str:
    if not items:
        return fallback

    def score(line: str) -> tuple[int, int, int]:
        cleaned = " ".join(str(line or "").split())
        metric_score = 0
        for terms in (DOSSIER_FACT_TERMS, DOSSIER_POSITIVE_TERMS, DOSSIER_NEGATIVE_TERMS):
            if line_has_any(cleaned, terms):
                metric_score += 1
        completeness = 1 if cleaned.endswith((".", "다.", "입니다.", "습니다.", "요.")) else 0
        return (metric_score, completeness, min(len(cleaned), 180))

    candidates = [item for item in items if not is_dossier_noise_line(item)]
    candidates = [item for item in candidates if len(item) >= 40]
    if not candidates:
        return fallback
    if mode in {"bull", "bear"}:
        marker = "강세:" if mode == "bull" else "약세:"
        scenario_candidates = [
            extract_scenario_clause(item, mode)
            for item in candidates
            if marker in str(item)
        ]
        scenario_candidates = [
            item for item in scenario_candidates if len(item) >= 20 and not is_dossier_noise_line(item)
        ]
        if scenario_candidates:
            return compact_representative_sentence(scenario_candidates[0])
    selected = extract_scenario_clause(sorted(candidates, key=score, reverse=True)[0], mode)
    if is_dossier_noise_line(selected):
        return fallback
    return compact_representative_sentence(selected)


def report_file_sequence(file_name: str) -> int:
    match = search(r"\d{4}-\d{2}-\d{2}-(\d+)\.(?:md|json)$", file_name)
    if match:
        return int(match.group(1))
    return 1 if search(r"\d{4}-\d{2}-\d{2}\.(?:md|json)$", file_name) else 0


def manifest_entry_sort_key(entry: dict) -> tuple[str, int, str]:
    return (
        str(entry.get("date") or ""),
        report_file_sequence(str(entry.get("file_name") or "")),
        str(entry.get("updated_at") or ""),
    )


def read_manifest_entry_text(vault_dir: Path, entry: dict) -> str:
    candidates: list[Path] = []
    relative_path = entry.get("relative_path")
    if relative_path:
        candidates.append(vault_dir.parent / str(relative_path))
    ticker = str(entry.get("ticker") or "").strip()
    file_name = str(entry.get("file_name") or "").strip()
    if ticker and file_name:
        candidates.append(vault_dir / ticker / file_name)
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            if not str(resolved).startswith(str(vault_dir.parent.resolve())):
                continue
            if resolved.exists() and resolved.is_file():
                return resolved.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
    return str(entry.get("summary") or "")


def plain_research_lines(text: str, limit: int = 80) -> list[str]:
    lines: list[str] = []
    raw_lines: list[str] = []
    in_front_matter = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "---":
            in_front_matter = not in_front_matter
            continue
        if in_front_matter:
            continue
        line = sub(r"^[#>*\-\d.\s]+", "", line).strip()
        line = sub(r"\s+", " ", line)
        if len(line) < 2 or line.lower().startswith(("ticker:", "type:", "date:", "module:")):
            continue
        if is_dossier_noise_line(line) and not is_research_line_continuation(line):
            continue
        if raw_lines and should_merge_research_lines(raw_lines[-1], line):
            raw_lines[-1] = f"{raw_lines[-1]} {line}"
        else:
            raw_lines.append(line)

    for line in raw_lines:
        if len(line) < 12 or is_dossier_noise_line(line):
            continue
        if len(line) > 320:
            line = f"{line[:317]}..."
        add_unique_text(lines, line, limit=limit)
    return lines


def line_has_any(text: str, terms: set[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def line_has_negated_bear_context(text: str) -> bool:
    cleaned = " ".join(str(text or "").split())
    compacted = cleaned.replace(" ", "")
    negated_patterns = (
        "둔화 신호로 해석하기는 어렵",
        "둔화 신호로 보기 어렵",
        "훼손이라기보다는",
        "리스크가 제한",
        "우려는 제한",
        "부담은 제한",
        "악화라기보다",
        "리스크 해소",
    )
    compacted_patterns = tuple(pattern.replace(" ", "") for pattern in negated_patterns)
    return any(pattern in cleaned for pattern in negated_patterns) or any(
        pattern in compacted for pattern in compacted_patterns
    )


def compact_representative_sentence(text: str, max_len: int = 180) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= max_len:
        return cleaned
    pieces = [piece.strip() for piece in findall(r"[^.!?。]+[.!?。]?", cleaned) if piece.strip()]
    scored: list[tuple[int, int, str]] = []
    for piece in pieces:
        if is_dossier_noise_line(piece):
            continue
        score = 0
        if line_has_any(piece, DOSSIER_FACT_TERMS):
            score += 2
        if line_has_any(piece, DOSSIER_POSITIVE_TERMS) or line_has_any(piece, DOSSIER_NEGATIVE_TERMS):
            score += 1
        if 35 <= len(piece) <= max_len:
            score += 2
        scored.append((score, min(len(piece), max_len), piece))
    if scored:
        selected = sorted(scored, reverse=True)[0][2]
        if len(selected) <= max_len:
            return selected
    return f"{cleaned[: max_len - 3]}..."


def latest_verified_entries_for_dossier(
    ticker: str,
    vault_dir: Path,
    *,
    read_manifest_fn,
    is_verified_manifest_entry_fn,
) -> tuple[list[dict], list[dict]]:
    entries = [
        entry
        for entry in read_manifest_fn(vault_dir)
        if entry.get("ticker") == ticker
        and is_allowed_dossier_source_entry(entry)
        and is_verified_manifest_entry_fn(entry, ticker)
    ]
    entries.sort(key=manifest_entry_sort_key, reverse=True)
    unique_entries: list[dict] = []
    duplicates: list[dict] = []
    seen: set[str] = set()
    seen_token_sets: list[set[str]] = []
    for entry in entries:
        text = read_manifest_entry_text(vault_dir, entry)
        clean_lines = plain_research_lines(text, limit=12)
        if not clean_lines and is_dossier_noise_line(entry.get("summary")):
            duplicates.append(
                {
                    "file_name": entry.get("file_name"),
                    "type": entry.get("type"),
                    "summary": entry.get("summary"),
                    "reason": "metadata_or_internal_output_only",
                }
            )
            continue
        dedup_key = (
            str(entry.get("source_url") or "").strip()
            or str(entry.get("content_hash") or "").strip()
            or content_fingerprint(f"{entry.get('type')} {entry.get('summary')} {text[:1200]}")
        )
        signature_tokens = similarity_tokens(manifest_similarity_text(entry, text))
        similar_to_seen = any(
            token_jaccard_similarity(signature_tokens, previous_tokens) >= 0.82
            for previous_tokens in seen_token_sets
            if len(signature_tokens) >= 8 and len(previous_tokens) >= 8
        )
        if dedup_key in seen or similar_to_seen:
            duplicates.append(
                {
                    "file_name": entry.get("file_name"),
                    "type": entry.get("type"),
                    "summary": entry.get("summary"),
                    "reason": "exact_match" if dedup_key in seen else "title_body_similarity",
                }
            )
            continue
        seen.add(dedup_key)
        if signature_tokens:
            seen_token_sets.append(signature_tokens)
        unique_entries.append({**entry, "_full_text": text})
    return unique_entries, duplicates


def dedupe_manifest_entries_by_similarity(entries: list[dict], vault_dir: Path, limit: int = 15) -> tuple[list[dict], list[dict]]:
    unique_entries: list[dict] = []
    duplicates: list[dict] = []
    seen_keys: set[str] = set()
    seen_tokens: list[set[str]] = []
    for entry in entries:
        text = read_manifest_entry_text(vault_dir, entry)
        exact_key = (
            str(entry.get("source_url") or "").strip()
            or str(entry.get("content_hash") or "").strip()
            or content_fingerprint(manifest_similarity_text(entry, text))
        )
        tokens = similarity_tokens(manifest_similarity_text(entry, text))
        similar = any(
            token_jaccard_similarity(tokens, previous) >= 0.84
            for previous in seen_tokens
            if len(tokens) >= 8 and len(previous) >= 8
        )
        if exact_key in seen_keys or similar:
            duplicates.append({**entry, "duplicate_reason": "exact_match" if exact_key in seen_keys else "title_body_similarity"})
            continue
        seen_keys.add(exact_key)
        if tokens:
            seen_tokens.append(tokens)
        unique_entries.append(entry)
        if len(unique_entries) >= limit:
            break
    return unique_entries, duplicates


def detect_capture_duplicate(
    *,
    vault_dir: Path,
    ticker: str,
    title: str,
    raw_content: str,
    source_url: str | None = None,
    content_hash: str | None = None,
    max_candidates: int = 120,
    read_manifest_fn,
    summarize_capture_fn,
    special_research_keys: set[str],
) -> dict:
    normalized_ticker = ticker.strip().upper()
    new_text = manifest_similarity_text(
        {
            "title": title,
            "summary": summarize_capture_fn(raw_content),
            "source_url": source_url,
        },
        raw_content,
    )
    new_tokens = similarity_tokens(new_text)
    new_hash = content_hash or content_fingerprint(raw_content)
    candidates = [
        entry
        for entry in sorted(
            [entry for entry in read_manifest_fn(vault_dir) if isinstance(entry, dict)],
            key=manifest_entry_sort_key,
            reverse=True,
        )
        if (entry.get("type") == "research-capture")
        and not is_failed_capture_manifest_entry(entry)
        and (
            str(entry.get("ticker") or "").upper() == normalized_ticker
            or normalized_ticker in special_research_keys
            or str(entry.get("ticker") or "").upper() in special_research_keys
        )
    ][:max_candidates]

    best: dict | None = None
    for entry in candidates:
        reason = None
        similarity = 0.0
        if source_url and entry.get("source_url") == source_url:
            reason = "source_url_exact_match"
            similarity = 1.0
        elif new_hash and entry.get("content_hash") == new_hash:
            reason = "content_hash_exact_match"
            similarity = 1.0
        else:
            existing_text = read_manifest_entry_text(vault_dir, entry)
            existing_tokens = similarity_tokens(manifest_similarity_text(entry, existing_text))
            similarity = token_jaccard_similarity(new_tokens, existing_tokens)
            if len(new_tokens) >= 8 and len(existing_tokens) >= 8 and similarity >= 0.84:
                reason = "title_body_similarity"

        if reason and (best is None or similarity > best.get("similarity", 0)):
            best = {
                "reason": reason,
                "similarity": round(similarity, 4),
                "matched_ticker": entry.get("ticker"),
                "matched_type": entry.get("type"),
                "matched_date": entry.get("date"),
                "matched_file_name": entry.get("file_name"),
                "matched_relative_path": entry.get("relative_path"),
            }

    return {
        "is_duplicate_suspected": best is not None,
        "checked_count": len(candidates),
        "reason": best.get("reason") if best else "no_match",
        "similarity": best.get("similarity") if best else 0.0,
        "matched_ticker": best.get("matched_ticker") if best else None,
        "matched_file_name": best.get("matched_file_name") if best else None,
        "matched_relative_path": best.get("matched_relative_path") if best else None,
    }


def is_failed_capture_manifest_entry(entry: dict) -> bool:
    summary = str(entry.get("summary") or "")
    relative_path = str(entry.get("relative_path") or "")
    source_processing = entry.get("source_url_processing") or {}
    failed_statuses = {"fetch_failed", "invalid", "empty_text"}
    return (
        "WinError 10061" in summary
        or "웹사이트 본문을 추출하지 못했습니다" in summary
        or "winerror-10061" in relative_path.lower()
        or str(source_processing.get("status") or "") in failed_statuses
    )


def capture_quality_status(
    *,
    raw_content: str,
    attachment_info: dict | None = None,
    source_url_processing: dict | None = None,
) -> dict:
    url_status = str((source_url_processing or {}).get("status") or "")
    url_text = str((source_url_processing or {}).get("text") or "")
    attachment_text = str((attachment_info or {}).get("extracted_text") or "")
    text_length = max(len(raw_content or ""), len(url_text), len(attachment_text))
    warnings: list[str] = []
    if url_status in {"fetch_failed", "invalid", "empty_text"}:
        warnings.append("웹사이트 본문 추출 실패")
    attachment_profile = (attachment_info or {}).get("extraction_profile") or {}
    if attachment_profile.get("ocr_status") == "unavailable":
        warnings.append("이미지 OCR 미연결")
    if attachment_info and not attachment_text and not (attachment_info or {}).get("extraction_char_count"):
        warnings.append(
            "첨부 파일 본문 추출 확인 필요"
            if attachment_profile.get("ocr_status") != "unavailable"
            else "이미지 원본은 저장됐지만 OCR 미연결로 본문 분석은 제외"
        )
    if text_length >= 1000 and not warnings:
        status = "정상"
    elif text_length >= 250:
        status = "보강 필요" if warnings else "정상"
    else:
        status = "실패" if warnings else "보강 필요"
    return {
        "status": status,
        "text_length": text_length,
        "warnings": warnings,
        "url_status": url_status or None,
        "readiness": (
            "분석에 바로 활용 가능"
            if status == "정상"
            else "추가 본문/원문 확인 후 활용"
            if status == "보강 필요"
            else "분석 반영 제외 권장"
        ),
    }
