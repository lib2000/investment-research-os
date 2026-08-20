"""Safe, optional Kronos forecasting adapter for research and backtesting.

Kronos is intentionally kept outside the live recommendation and brokerage
paths.  This module owns the small integration boundary needed for staged
experiments: OHLCV validation, lazy model loading, output sanitisation, and
leakage-safe walk-forward evaluation.

The Kronos package is not a dependency of Research OS.  Install it in a
separate numerical environment only when running an experiment.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite, log
from typing import Any, Callable, Iterable, Mapping, Sequence


REQUIRED_COLUMNS = ("open", "high", "low", "close")
OPTIONAL_COLUMNS = ("volume", "amount")
DEFAULT_MODEL_ID = "NeoQuasar/Kronos-small"
DEFAULT_TOKENIZER_ID = "NeoQuasar/Kronos-Tokenizer-base"
DEFAULT_MAX_CONTEXT = 512


class KronosAdapterError(ValueError):
    """Raised when input or model output cannot be safely evaluated."""


class KronosDependencyError(RuntimeError):
    """Raised when the optional Kronos runtime is not installed."""


@dataclass(frozen=True)
class ModelBenchmarkGate:
    """Human-review gate for promoting a numerical model beyond research."""

    model_id: str
    mean_improvement_vs_baseline_pct: float
    strict_failures: int
    output_repairs: int
    observations: int
    min_improvement_pct: float = 0.0
    max_repair_rate: float = 0.0

    @property
    def repair_rate(self) -> float:
        if self.observations <= 0:
            return 1.0
        return self.output_repairs / self.observations

    @property
    def eligible_for_human_review(self) -> bool:
        return (
            self.mean_improvement_vs_baseline_pct >= self.min_improvement_pct
            and self.strict_failures == 0
            and self.repair_rate <= self.max_repair_rate
        )

    @property
    def decision(self) -> str:
        return "human_review" if self.eligible_for_human_review else "hold_research_only"

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "mean_improvement_vs_baseline_pct": self.mean_improvement_vs_baseline_pct,
            "strict_failures": self.strict_failures,
            "output_repairs": self.output_repairs,
            "observations": self.observations,
            "repair_rate": self.repair_rate,
            "min_improvement_pct": self.min_improvement_pct,
            "max_repair_rate": self.max_repair_rate,
            "eligible_for_human_review": self.eligible_for_human_review,
            "decision": self.decision,
        }


def evaluate_model_benchmark_gate(
    *,
    model_id: str,
    mean_improvement_vs_baseline_pct: float,
    strict_failures: int,
    output_repairs: int,
    observations: int,
    min_improvement_pct: float = 0.0,
    max_repair_rate: float = 0.0,
) -> ModelBenchmarkGate:
    """Return a non-promoting-by-default decision record for a model run."""

    if strict_failures < 0 or output_repairs < 0 or observations < 0:
        raise KronosAdapterError("benchmark counts cannot be negative")
    if observations == 0 and output_repairs:
        raise KronosAdapterError("output repairs require observations")
    if max_repair_rate < 0 or min_improvement_pct < 0:
        raise KronosAdapterError("benchmark thresholds cannot be negative")
    return ModelBenchmarkGate(
        model_id=model_id,
        mean_improvement_vs_baseline_pct=float(mean_improvement_vs_baseline_pct),
        strict_failures=int(strict_failures),
        output_repairs=int(output_repairs),
        observations=int(observations),
        min_improvement_pct=float(min_improvement_pct),
        max_repair_rate=float(max_repair_rate),
    )


@dataclass(frozen=True)
class KronosForecast:
    """A validated forecast plus evidence-oriented diagnostics."""

    rows: list[dict[str, Any]]
    model_id: str
    diagnostics: dict[str, Any]


@dataclass(frozen=True)
class WalkForwardMetrics:
    """Aggregate metrics for a chronological, non-shuffled evaluation."""

    windows: int
    observations: int
    forecast_mae: float | None
    naive_mae: float | None
    improvement_vs_naive_pct: float | None
    direction_accuracy: float | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "windows": self.windows,
            "observations": self.observations,
            "forecast_mae": self.forecast_mae,
            "naive_mae": self.naive_mae,
            "improvement_vs_naive_pct": self.improvement_vs_naive_pct,
            "direction_accuracy": self.direction_accuracy,
        }


def _records_from_frame(frame: Any) -> list[dict[str, Any]]:
    """Convert a DataFrame-like object or row iterable to plain records."""

    if frame is None:
        return []
    if hasattr(frame, "to_dict"):
        try:
            records = frame.to_dict(orient="records")
        except TypeError:
            records = frame.to_dict("records")
        index = getattr(frame, "index", None)
        index_values = list(index) if index is not None else []
        # A default RangeIndex is row numbering, not market time.  Treating it
        # as a timestamp would silently make a timestamp-less frame look valid.
        default_index = index_values == list(range(len(records)))
        result: list[dict[str, Any]] = []
        for position, raw in enumerate(records):
            row = dict(raw) if isinstance(raw, Mapping) else {}
            if "timestamp" not in row and not default_index and position < len(index_values):
                row["timestamp"] = index_values[position]
            result.append(row)
        return result
    if isinstance(frame, Mapping):
        return [dict(frame)]
    try:
        return [dict(row) for row in frame]
    except (TypeError, ValueError) as exc:
        raise KronosAdapterError("OHLCV data must be a DataFrame or row mappings") from exc


def _finite_number(value: Any, *, field: str, row_number: int) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise KronosAdapterError(f"{field} at row {row_number} is not numeric") from exc
    if not isfinite(number):
        raise KronosAdapterError(f"{field} at row {row_number} is not finite")
    return number


def _timestamp_key(value: Any) -> str:
    """Return a stable, comparable representation without changing the source value."""

    return str(value)


def validate_ohlcv_rows(rows: Sequence[Mapping[str, Any]], *, require_timestamps: bool = False) -> list[dict[str, Any]]:
    """Validate and normalise OHLCV rows before handing them to a model."""

    if not rows:
        raise KronosAdapterError("at least one OHLCV row is required")
    normalised: list[dict[str, Any]] = []
    timestamp_keys: list[str] = []
    for row_number, source in enumerate(rows):
        row = dict(source)
        missing = [column for column in REQUIRED_COLUMNS if column not in row]
        if missing:
            raise KronosAdapterError(f"row {row_number} is missing required columns: {', '.join(missing)}")
        for column in REQUIRED_COLUMNS:
            row[column] = _finite_number(row[column], field=column, row_number=row_number)
        if row["high"] < max(row["open"], row["close"]):
            raise KronosAdapterError(f"high is below open/close at row {row_number}")
        if row["low"] > min(row["open"], row["close"]):
            raise KronosAdapterError(f"low is above open/close at row {row_number}")
        for column in OPTIONAL_COLUMNS:
            if column in row and row[column] is not None:
                row[column] = _finite_number(row[column], field=column, row_number=row_number)
                if row[column] < 0:
                    raise KronosAdapterError(f"{column} is negative at row {row_number}")
        if "timestamp" in row and row["timestamp"] is not None:
            timestamp_keys.append(_timestamp_key(row["timestamp"]))
        elif require_timestamps:
            raise KronosAdapterError(f"timestamp is required at row {row_number}")
        normalised.append(row)
    if timestamp_keys and len(timestamp_keys) == len(normalised):
        if any(left >= right for left, right in zip(timestamp_keys, timestamp_keys[1:])):
            raise KronosAdapterError("timestamps must be strictly increasing")
    return normalised


def _sequence_values(value: Any) -> list[Any]:
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    try:
        return list(value)
    except TypeError:
        return [value]


def _optional_pandas_frame(rows: list[dict[str, Any]], original: Any = None) -> Any:
    """Build the DataFrame expected by Kronos without making pandas mandatory."""

    model_columns = [*REQUIRED_COLUMNS, *OPTIONAL_COLUMNS]
    if original is not None and hasattr(original, "columns") and hasattr(original, "iloc"):
        available = [column for column in model_columns if column in original.columns]
        return original.loc[:, available]
    try:
        import pandas as pd  # type: ignore
    except ImportError:
        return rows
    return pd.DataFrame(
        [{column: row[column] for column in model_columns if column in row} for row in rows]
    )


def _optional_pandas_series(values: Sequence[Any]) -> Any:
    try:
        import pandas as pd  # type: ignore
    except ImportError:
        return list(values)
    series = pd.Series(list(values))
    # Kronos derives calendar features through ``Series.dt``.  Keep the
    # original values when they are not date-like, but make ISO date strings
    # usable by the real predictor instead of failing deep inside the model.
    try:
        return pd.to_datetime(series, errors="raise")
    except (TypeError, ValueError):
        return series


def _trim_history(history: Any, rows: list[dict[str, Any]], max_context: int) -> tuple[Any, list[dict[str, Any]], int]:
    if len(rows) <= max_context:
        return history, rows, 0
    trimmed_rows = rows[-max_context:]
    if hasattr(history, "iloc"):
        return history.iloc[-max_context:], trimmed_rows, len(rows) - max_context
    return _optional_pandas_frame(trimmed_rows), trimmed_rows, len(rows) - max_context


def _validate_future_timestamps(y_timestamp: Sequence[Any], pred_len: int) -> list[Any]:
    values = _sequence_values(y_timestamp)
    if len(values) != pred_len:
        raise KronosAdapterError(f"y_timestamp length {len(values)} does not match pred_len {pred_len}")
    if any(left >= right for left, right in zip(map(_timestamp_key, values), map(_timestamp_key, values[1:]))):
        raise KronosAdapterError("future timestamps must be strictly increasing")
    return values


def sanitise_forecast_rows(
    forecast: Any,
    y_timestamp: Sequence[Any],
    *,
    pred_len: int,
    strict: bool = False,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Validate model output and repair known K-line violations.

    Kronos issue #130 documents negative volume samples.  Non-strict mode
    clips only the mechanically safe violations and records every repair;
    strict mode fails so an evaluator can exclude the window instead.
    """

    rows = _records_from_frame(forecast)
    if len(rows) != pred_len:
        raise KronosAdapterError(f"model returned {len(rows)} rows; expected {pred_len}")
    timestamps = _validate_future_timestamps(y_timestamp, pred_len)
    repaired: list[str] = []
    result: list[dict[str, Any]] = []
    for row_number, source in enumerate(rows):
        row = dict(source)
        missing = [column for column in REQUIRED_COLUMNS if column not in row]
        if missing:
            raise KronosAdapterError(f"forecast row {row_number} is missing: {', '.join(missing)}")
        for column in REQUIRED_COLUMNS:
            row[column] = _finite_number(row[column], field=column, row_number=row_number)
        high_floor = max(row["open"], row["close"])
        low_ceiling = min(row["open"], row["close"])
        if row["high"] < high_floor:
            if strict:
                raise KronosAdapterError(f"forecast high is below open/close at row {row_number}")
            row["high"] = high_floor
            repaired.append(f"high[{row_number}]")
        if row["low"] > low_ceiling:
            if strict:
                raise KronosAdapterError(f"forecast low is above open/close at row {row_number}")
            row["low"] = low_ceiling
            repaired.append(f"low[{row_number}]")
        for column in OPTIONAL_COLUMNS:
            if column not in row or row[column] is None:
                continue
            row[column] = _finite_number(row[column], field=column, row_number=row_number)
            if row[column] < 0:
                if strict:
                    raise KronosAdapterError(f"forecast {column} is negative at row {row_number}")
                row[column] = 0.0
                repaired.append(f"{column}[{row_number}]")
        row["timestamp"] = timestamps[row_number]
        result.append(row)
    return result, repaired


class KronosForecastAdapter:
    """Adapter around ``KronosPredictor`` with no live-system side effects."""

    def __init__(
        self,
        predictor: Any,
        *,
        model_id: str = DEFAULT_MODEL_ID,
        max_context: int = DEFAULT_MAX_CONTEXT,
        deployment_mode: str = "research_only",
    ) -> None:
        if predictor is None or not callable(getattr(predictor, "predict", None)):
            raise KronosAdapterError("predictor must expose a predict method")
        if max_context < 1:
            raise KronosAdapterError("max_context must be positive")
        if deployment_mode != "research_only":
            raise KronosAdapterError("Kronos is restricted to research_only mode")
        self.predictor = predictor
        self.model_id = model_id
        self.max_context = max_context
        self.deployment_mode = deployment_mode

    def predict(
        self,
        history: Any,
        *,
        y_timestamp: Sequence[Any],
        pred_len: int,
        x_timestamp: Sequence[Any] | None = None,
        temperature: float = 1.0,
        top_p: float = 0.9,
        sample_count: int = 1,
        strict: bool = False,
    ) -> KronosForecast:
        if pred_len < 1:
            raise KronosAdapterError("pred_len must be positive")
        if not 0 < top_p <= 1:
            raise KronosAdapterError("top_p must be in (0, 1]")
        if temperature <= 0:
            raise KronosAdapterError("temperature must be positive")
        if sample_count < 1:
            raise KronosAdapterError("sample_count must be positive")

        source_rows = _records_from_frame(history)
        trimmed_history, rows, trimmed_count = _trim_history(history, source_rows, self.max_context)
        rows = validate_ohlcv_rows(rows, require_timestamps=False)
        explicit_x_timestamp = _sequence_values(x_timestamp)
        if explicit_x_timestamp:
            if len(explicit_x_timestamp) != len(source_rows):
                raise KronosAdapterError("x_timestamp length must match history length")
            explicit_x_timestamp = explicit_x_timestamp[-len(rows) :]
        else:
            explicit_x_timestamp = [row.get("timestamp") for row in rows]
            if any(value is None for value in explicit_x_timestamp):
                raise KronosAdapterError("x_timestamp is required when history has no timestamp column")

        future_timestamps = _validate_future_timestamps(y_timestamp, pred_len)
        model_input = _optional_pandas_frame(rows, trimmed_history if hasattr(trimmed_history, "columns") else None)
        raw_forecast = self.predictor.predict(
            df=model_input,
            x_timestamp=_optional_pandas_series(explicit_x_timestamp),
            y_timestamp=_optional_pandas_series(future_timestamps),
            pred_len=pred_len,
            T=temperature,
            top_p=top_p,
            sample_count=sample_count,
        )
        forecast_rows, repaired = sanitise_forecast_rows(
            raw_forecast,
            future_timestamps,
            pred_len=pred_len,
            strict=strict,
        )
        diagnostics = {
            "model_id": self.model_id,
            "context_limit": self.max_context,
            "input_rows": len(source_rows),
            "context_rows": len(rows),
            "context_rows_trimmed": trimmed_count,
            "pred_len": pred_len,
            "sample_count": sample_count,
            "output_repairs": repaired,
            "output_repair_count": len(repaired),
            "live_trading": False,
            "deployment_mode": self.deployment_mode,
        }
        return KronosForecast(rows=forecast_rows, model_id=self.model_id, diagnostics=diagnostics)


def load_kronos_predictor(
    *,
    model_id: str = DEFAULT_MODEL_ID,
    tokenizer_id: str = DEFAULT_TOKENIZER_ID,
    device: str | None = None,
    max_context: int = DEFAULT_MAX_CONTEXT,
) -> Any:
    """Load Kronos lazily so the core Research OS does not depend on torch."""

    try:
        from model import Kronos, KronosPredictor, KronosTokenizer  # type: ignore
    except ImportError as exc:
        raise KronosDependencyError(
            "Kronos is optional; install its requirements and expose its model.py on PYTHONPATH"
        ) from exc
    try:
        tokenizer = KronosTokenizer.from_pretrained(tokenizer_id)
        model = Kronos.from_pretrained(model_id)
        kwargs: dict[str, Any] = {"max_context": max_context}
        if device:
            kwargs["device"] = device
        return KronosPredictor(model, tokenizer, **kwargs)
    except Exception as exc:  # model download/config errors need one clear boundary
        raise KronosDependencyError(f"Kronos model loading failed: {exc}") from exc


def iter_walk_forward_windows(
    rows: Sequence[Mapping[str, Any]],
    *,
    lookback: int,
    horizon: int,
    step: int | None = None,
) -> Iterable[tuple[list[dict[str, Any]], list[dict[str, Any]]]]:
    """Yield chronological history/future pairs without future leakage."""

    if lookback < 1 or horizon < 1:
        raise KronosAdapterError("lookback and horizon must be positive")
    if step is None:
        step = horizon
    if step < 1:
        raise KronosAdapterError("step must be positive")
    normalised = validate_ohlcv_rows(rows, require_timestamps=False)
    cursor = lookback
    while cursor + horizon <= len(normalised):
        yield normalised[cursor - lookback : cursor], normalised[cursor : cursor + horizon]
        cursor += step


def evaluate_walk_forward(
    rows: Sequence[Mapping[str, Any]],
    forecaster: Callable[[list[dict[str, Any]], list[Any]], Sequence[Mapping[str, Any]]],
    *,
    lookback: int,
    horizon: int,
    step: int | None = None,
    strict: bool = True,
) -> WalkForwardMetrics:
    """Evaluate a forecaster against a last-close baseline.

    This deliberately reports forecast quality, not a tradable return.  A
    later strategy stage must add portfolio constraints, fees, slippage, and
    market-impact assumptions before any investment decision is considered.
    """

    forecast_errors: list[float] = []
    naive_errors: list[float] = []
    directions: list[bool] = []
    windows = 0
    for history, future in iter_walk_forward_windows(rows, lookback=lookback, horizon=horizon, step=step):
        timestamps = [row.get("timestamp") for row in future]
        if any(value is None for value in timestamps):
            raise KronosAdapterError("walk-forward evaluation requires future timestamps")
        predicted = forecaster(history, timestamps)
        forecast_rows, _ = sanitise_forecast_rows(predicted, timestamps, pred_len=horizon, strict=strict)
        last_close = history[-1]["close"]
        for actual, forecast in zip(future, forecast_rows):
            forecast_errors.append(abs(forecast["close"] - actual["close"]))
            naive_errors.append(abs(last_close - actual["close"]))
        directions.append(
            (forecast_rows[0]["close"] - last_close >= 0)
            == (future[0]["close"] - last_close >= 0)
        )
        windows += 1
    if not windows:
        return WalkForwardMetrics(0, 0, None, None, None, None)
    forecast_mae = sum(forecast_errors) / len(forecast_errors)
    naive_mae = sum(naive_errors) / len(naive_errors)
    improvement = ((naive_mae - forecast_mae) / naive_mae * 100) if naive_mae else None
    return WalkForwardMetrics(
        windows=windows,
        observations=len(forecast_errors),
        forecast_mae=forecast_mae,
        naive_mae=naive_mae,
        improvement_vs_naive_pct=improvement,
        direction_accuracy=sum(directions) / len(directions) if directions else None,
    )


def log_return_drift_forecast(
    history: Sequence[Mapping[str, Any]],
    timestamps: Sequence[Any],
) -> list[dict[str, Any]]:
    """Build a deterministic price baseline from mean historical log return.

    This is a benchmark only.  It is intentionally simple and does not model
    costs, corporate actions, liquidity, or portfolio constraints.
    """

    rows = validate_ohlcv_rows(history, require_timestamps=False)
    closes = [row["close"] for row in rows]
    if len(closes) < 2:
        raise KronosAdapterError("at least two closes are required for log-return drift")
    returns = [log(current / previous) for previous, current in zip(closes, closes[1:]) if previous > 0 and current > 0]
    if not returns:
        raise KronosAdapterError("positive closes are required for log-return drift")
    mean_return = sum(returns) / len(returns)
    previous_close = closes[-1]
    result: list[dict[str, Any]] = []
    for step, timestamp in enumerate(_sequence_values(timestamps), start=1):
        close = previous_close * exp(mean_return * step)
        result.append(
            {
                "timestamp": timestamp,
                "open": previous_close,
                "high": max(previous_close, close),
                "low": min(previous_close, close),
                "close": close,
                "volume": 0.0,
            }
        )
    return result
