# Investment Research OS Design Contract

## Product character
- Treat the console as an evidence-first analyst workstation, not a trading promotion page.
- Keep research, strategy design, simulation, and live execution visibly separated.
- Show data freshness, source quality, loading, empty, and error states near the affected result.

## Visual language
- Preserve the existing warm neutral console, compact cards, restrained blue actions, and tabular numeric presentation.
- Use Korean market color conventions consistently: rise/profit red, fall/loss blue, neutral gray.
- Prefer clear section labels and stable information density over decorative effects.

## Integrated tools
- Research OS remains the primary entry point for portfolio, family holdings, news, earnings, and recommendations.
- Strategy Builder and Backtester appear as analysis workbenches with their own explicit service status and URL.
- Never make an analysis or simulation control look like a live-order control.

## Responsive and accessibility
- At narrow widths, cards become a single column and actions wrap without horizontal overflow.
- Korean labels wrap by word or phrase, never one character per line.
- Interactive controls retain visible focus and a practical touch target.

## Verification
- Check the console at desktop and 390x844 mobile widths.
- Verify the integrated tool links, service-down guidance, loading/empty/error states, and existing console static contract.
