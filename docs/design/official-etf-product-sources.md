# Official ETF Product Sources

- Status: implemented
- Updated: 2026-08-30
- Scope: portfolio research freshness only

## Objective

Keep ETF holdings separate from operating-company earnings.  The daily public-source
watch reads each ETF's official KRX KIND product overview so research can verify the
product code, underlying index, manager, fee, and product structure without inventing
an earnings calendar or converting a price quote into a research document.

## Source and trust boundary

1. The source starts at `https://kind.krx.co.kr/disclosure/etfisudetail.do`.
2. The collector reads the public KRX product summary, obtains the ISIN, and requests
   the public product-detail GET URL.
3. The returned KRX ticker must exactly match the configured holding ticker.  A
   mismatch is a failed source, never saved evidence.
4. Portfolio ticker binding is allowed only for HTTPS URLs on the exact
   `kind.krx.co.kr` host with source type `krx_etf_product`.
5. The evidence is labelled `KRX 공식 ETF 상품개요(일일 확인)`.  It is a checked
   product snapshot, not an issuer earnings release, trading signal, or automatic
   human-review completion.

## Automation behavior

The existing public-source scheduler fetches the configured KRX ETF sources together
with company IR and SEC sources.  It stores a URL-based official-source record only
when the product page is successfully bound to its configured ticker.  It does not
create an investment recommendation, order, report, strategy, or review decision.

## Verification

`tests/test_official_source_extensions.py` validates the source list, KRX detail URL
flow, exact ticker match, and KRX-host allowlist.  Live verification must check the
saved source result and the portfolio research batch after the backend refresh.
