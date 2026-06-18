"""HTTP fetch helpers for URL capture."""

from __future__ import annotations

from urllib.parse import urlparse
import urllib.request

import httpx


def capture_url_headers(cleaned_url: str) -> dict[str, str]:
    parsed = urlparse(cleaned_url)
    origin = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else cleaned_url
    host = (parsed.hostname or "").lower()
    if host.endswith("sec.gov"):
        return {
            "User-Agent": "investment-research-os/1.0 contact lib2000@gmail.com",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ko-KR;q=0.8,ko;q=0.7",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Referer": "https://www.sec.gov/",
        }
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36 InvestmentResearchOS/1.0"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf,text/plain,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": origin,
    }


def fetch_sec_url_with_urllib(cleaned_url: str, headers: dict[str, str], attempts: list[str]) -> httpx.Response | None:
    parsed = urlparse(cleaned_url)
    host = (parsed.hostname or "").lower()
    if not host.endswith("sec.gov"):
        return None
    try:
        request = urllib.request.Request(cleaned_url, headers=headers)
        with urllib.request.urlopen(request, timeout=18.0) as source:
            status_code = int(getattr(source, "status", 0) or source.getcode() or 200)
            final_url = source.geturl() or cleaned_url
            content = source.read(4_000_000)
            response_headers = dict(source.headers.items())
        attempts.append(f"sec_urllib: success {status_code}")
        return httpx.Response(
            status_code=status_code,
            headers=response_headers,
            content=content,
            request=httpx.Request("GET", final_url, headers=headers),
        )
    except Exception as error:
        attempts.append(f"sec_urllib: {error}")
        return None


def fetch_url_with_retry(cleaned_url: str) -> tuple[httpx.Response | None, list[str]]:
    attempts: list[str] = []
    headers = capture_url_headers(cleaned_url)
    for trust_env in [False, True]:
        mode = "direct" if not trust_env else "system_proxy"
        try:
            with httpx.Client(
                follow_redirects=True,
                timeout=httpx.Timeout(18.0, connect=8.0),
                headers=headers,
                trust_env=trust_env,
            ) as client:
                response = client.get(cleaned_url)
                response.raise_for_status()
                attempts.append(f"{mode}: success {response.status_code}")
                return response, attempts
        except Exception as error:
            attempts.append(f"{mode}: {error}")
    sec_response = fetch_sec_url_with_urllib(cleaned_url, headers, attempts)
    if sec_response is not None:
        return sec_response, attempts
    return None, attempts
