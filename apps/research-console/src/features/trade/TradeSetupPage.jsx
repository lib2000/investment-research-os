import { useEffect, useMemo, useState } from "react";
import { formatMoney, normalizeCurrency, parseNumberInput } from "../../shared/format/money.js";
import { formatPercent } from "../../shared/format/percent.js";

export function TradeSetupPage({ researchApi, portfolioApi, initialTicker = "PL" }) {
  const [ticker, setTicker] = useState(initialTicker || "PL");
  const [currentPrice, setCurrentPrice] = useState("39.04");
  const [style, setStyle] = useState("swing");
  const [riskTolerance, setRiskTolerance] = useState("보통");
  const [portfolioName, setPortfolioName] = useState("");
  const [portfolioSize, setPortfolioSize] = useState("");
  const [riskPerTradePct, setRiskPerTradePct] = useState("1");
  const [marketStructure, setMarketStructure] = useState("중립 박스권");
  const [autoInjectData, setAutoInjectData] = useState(true);
  const [portfolios, setPortfolios] = useState([]);
  const [status, setStatus] = useState("대기");
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);

  const normalizedTicker = useMemo(() => ticker.trim().toUpperCase(), [ticker]);
  const currency = normalizeCurrency("", normalizedTicker);

  useEffect(() => {
    let ignore = false;
    async function loadPortfolios() {
      try {
        const response = await portfolioApi.list();
        if (ignore) {
          return;
        }
        setPortfolios(response?.portfolios || response?.items || []);
      } catch {
        if (!ignore) {
          setPortfolios([]);
        }
      }
    }
    loadPortfolios();
    return () => {
      ignore = true;
    };
  }, [portfolioApi]);

  useEffect(() => {
    setTicker(String(initialTicker || "PL").trim().toUpperCase());
  }, [initialTicker]);

  function selectPortfolio(name) {
    setPortfolioName(name);
    const selected = portfolios.find((item) => (item.portfolio_name || item.name) === name);
    const value = parseNumberInput(selected?.portfolio_value || selected?.summary?.total_market_value);
    setPortfolioSize(value === null ? "" : String(Math.round(value)));
  }

  async function submitTradeSetup(event) {
    event.preventDefault();
    const price = parseNumberInput(currentPrice);
    const portfolioValue = parseNumberInput(portfolioSize);
    const riskPct = parseNumberInput(riskPerTradePct);

    if (!normalizedTicker) {
      setError("티커를 입력하세요.");
      setStatus("실행 보류");
      return;
    }
    if (price === null || price <= 0) {
      setError("현재가를 입력하세요. 미국 주식은 달러, 한국 주식은 원 기준입니다.");
      setStatus("실행 보류");
      return;
    }
    if (riskPct === null || riskPct <= 0) {
      setError("1회 거래 리스크를 % 숫자로 입력하세요. 예: 1");
      setStatus("실행 보류");
      return;
    }

    setStatus("매매 전략 생성 중");
    setError("");
    setResult(null);
    try {
      const response = await researchApi.runSmartTradeSetup({
        ticker: normalizedTicker,
        currentPrice: price,
        style,
        riskTolerance,
        portfolioSize: portfolioValue,
        riskPerTradePct: riskPct / 100,
        marketStructure: marketStructure || null,
        autoInjectData,
        saveResult: true,
      });
      setResult(response);
      setStatus("전략 생성 완료");
    } catch (nextError) {
      setStatus("전략 생성 실패");
      setError(nextError.message);
    }
  }

  return (
    <section className="panel trade-panel">
      <div className="panel-heading">
        <div>
          <h2>매매전략</h2>
          <p>현재가, 매매 기간, 포트폴리오 규모, 1회 리스크를 기준으로 진입·손절·목표가를 생성합니다.</p>
        </div>
        <strong className="status-pill">{status}</strong>
      </div>

      <form className="trade-form" onSubmit={submitTradeSetup}>
        <div className="trade-form-grid">
          <label>
            티커
            <input value={ticker} onChange={(event) => setTicker(event.target.value)} />
          </label>
          <label>
            현재가 ({currency === "KRW" ? "원" : "$"})
            <input value={currentPrice} onChange={(event) => setCurrentPrice(event.target.value)} />
          </label>
          <label>
            스타일
            <select value={style} onChange={(event) => setStyle(event.target.value)}>
              <option value="scalp">아주 짧게 매매</option>
              <option value="day">하루 안에 매매</option>
              <option value="swing">단기 보유(며칠~몇 주)</option>
              <option value="position">중기 보유(몇 주~몇 달)</option>
            </select>
          </label>
          <label>
            허용 리스크
            <select value={riskTolerance} onChange={(event) => setRiskTolerance(event.target.value)}>
              <option value="낮음">낮음</option>
              <option value="보통">보통</option>
              <option value="높음">높음</option>
            </select>
          </label>
          <label>
            기준 포트폴리오
            <select value={portfolioName} onChange={(event) => selectPortfolio(event.target.value)}>
              <option value="">직접 입력</option>
              {portfolios.map((item) => {
                const name = item.portfolio_name || item.name;
                return (
                  <option key={name} value={name}>
                    {name}
                  </option>
                );
              })}
            </select>
          </label>
          <label>
            포트폴리오 규모 (원)
            <input value={portfolioSize} onChange={(event) => setPortfolioSize(event.target.value)} />
          </label>
          <label>
            1회 거래 리스크 (%)
            <input value={riskPerTradePct} onChange={(event) => setRiskPerTradePct(event.target.value)} />
          </label>
          <label className="wide-field">
            시장 구조
            <input value={marketStructure} onChange={(event) => setMarketStructure(event.target.value)} />
          </label>
        </div>
        <label className="check-row trade-check">
          <input
            type="checkbox"
            checked={autoInjectData}
            onChange={(event) => setAutoInjectData(event.target.checked)}
          />
          시장/재무 데이터 자동 주입
        </label>
        <button type="submit">스마트 매매 전략 생성</button>
      </form>

      {error ? <div className="warning-box">{error}</div> : null}
      {result ? <TradeResult result={result} /> : <TradeGuide />}
    </section>
  );
}

function TradeGuide() {
  return (
    <section className="dashboard-section">
      <div className="info-card">
        <span>입력 단위</span>
        <strong>리스크는 %</strong>
        <p>1회 거래 리스크 1은 포트폴리오의 1%를 뜻하며, 서버에는 0.01로 자동 변환됩니다.</p>
      </div>
    </section>
  );
}

function TradeResult({ result }) {
  const currency = normalizeCurrency("", result.ticker);
  return (
    <div className="trade-result">
      <section className="dashboard-section">
        <h3>전략 요약</h3>
        <div className="dashboard-card-grid">
          <Metric label="티커" value={result.ticker} text={translateStyle(result.style)} />
          <Metric label="현재가" value={formatTradePrice(result.current_price, currency)} text={result.market_structure} />
          <Metric label="세팅 품질" value={result.setup_quality || "미확인"} text={`허용 리스크 ${result.risk_tolerance}`} />
          <Metric
            label="1회 리스크"
            value={formatPercent(result.risk_per_trade_pct, "미확인")}
            text={result.portfolio_size ? `기준 ${formatMoney(result.portfolio_size, "KRW")}` : "포트폴리오 기준 없음"}
          />
        </div>
      </section>

      <section className="dashboard-section two-column">
        <PriceLevelBlock title="진입 구간" levels={result.entry_zone} currency={currency} />
        <PriceLevelBlock title="손절" levels={result.stop_loss ? [result.stop_loss] : []} currency={currency} />
      </section>

      <section className="dashboard-section">
        <h3>목표가</h3>
        <table className="mini-table">
          <thead>
            <tr>
              <th>구분</th>
              <th className="number">가격</th>
              <th className="number">손익비</th>
              <th>조치</th>
            </tr>
          </thead>
          <tbody>
            {(result.targets || []).map((target) => (
              <tr key={target.label}>
                <td>{target.label}</td>
                <td className="number">{formatTradePrice(target.price, currency)}</td>
                <td className="number">{Number(target.risk_reward || 0).toLocaleString("ko-KR", { maximumFractionDigits: 2 })}:1</td>
                <td>{target.action}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="dashboard-section">
        <div className="report-item">
          <strong>포지션 가이드</strong>
          <p>{result.position_sizing_guidance}</p>
          <small>주당 리스크: {formatTradePrice(result.risk_per_share, currency)}</small>
          {result.max_position_value ? <small>권장 최대 포지션: {formatMoney(result.max_position_value, "KRW")}</small> : null}
        </div>
      </section>

      <section className="dashboard-section two-column">
        <ListBlock title="실행 계획" items={result.trade_plan} />
        <ListBlock title="무효화 조건" items={result.invalidation_conditions} />
      </section>
      <section className="dashboard-section two-column">
        <ListBlock title="다음 액션" items={result.next_actions} />
        <ListBlock title="주입 데이터" items={(result.injected_data || []).map((item) => `${item.label || item.source_type}: ${item.value || item.summary || ""}`)} />
      </section>
      {result.storage?.path || result.storage?.relative_path ? (
        <section className="dashboard-section">
          <div className="report-item">
            <strong>저장 데이터</strong>
            <small>{result.storage.relative_path || result.storage.path}</small>
          </div>
        </section>
      ) : null}
    </div>
  );
}

function Metric({ label, value, text }) {
  return (
    <article className="info-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{text}</p>
    </article>
  );
}

function PriceLevelBlock({ title, levels, currency }) {
  const rows = Array.isArray(levels) ? levels : [];
  return (
    <div className="list-block">
      <h3>{title}</h3>
      {rows.length ? (
        <ul>
          {rows.map((item) => (
            <li key={item.label}>
              <strong>{item.label}: {formatTradePrice(item.price, currency)}</strong>
              <br />
              {item.rationale}
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted-text">표시할 가격대가 없습니다.</p>
      )}
    </div>
  );
}

function ListBlock({ title, items }) {
  const list = Array.isArray(items) ? items.filter(Boolean).slice(0, 8) : [];
  return (
    <div className="list-block">
      <h3>{title}</h3>
      {list.length ? (
        <ul>
          {list.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="muted-text">표시할 항목이 없습니다.</p>
      )}
    </div>
  );
}

function formatTradePrice(value, currency) {
  return formatMoney(value, currency, "미확인");
}

function translateStyle(value) {
  const labels = {
    scalp: "아주 짧게 매매",
    day: "하루 안에 매매",
    swing: "단기 보유(며칠~몇 주)",
    position: "중기 보유(몇 주~몇 달)",
  };
  return labels[value] || value || "스타일 미확인";
}
