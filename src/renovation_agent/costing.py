from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from .planner import RenovationPlan

DEFAULT_RATES_PATH = Path(__file__).parent / "data" / "default_rates.json"
DATA_DIR = Path(__file__).parent / "data"

RATE_PRESETS: dict[str, Path] = {
    "default": DATA_DIR / "default_rates.json",
    "india-metro": DATA_DIR / "rates_india_metro.json",
    "india-tier2": DATA_DIR / "rates_india_tier2.json",
    "us-standard": DATA_DIR / "rates_us_standard.json",
}


def list_rate_presets() -> list[str]:
    return sorted(RATE_PRESETS.keys())


class RatesError(ValueError):
    pass


@dataclass
class CostLine:
    item: str
    category: str
    quantity: float
    unit: str
    rate: float
    amount: float


@dataclass
class CostEstimate:
    currency: str
    lines: list[CostLine] = field(default_factory=list)
    unpriced: list[str] = field(default_factory=list)
    subtotal: float = 0.0
    contingency_pct: float = 0.0
    contingency: float = 0.0
    total: float = 0.0


def load_rates(path: str | Path | None = None) -> dict:
    if path is None:
        p = RATE_PRESETS["default"]
    elif isinstance(path, (str, Path)) and str(path).lower() in RATE_PRESETS:
        p = RATE_PRESETS[str(path).lower()]
    else:
        p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise RatesError(f"Cannot read rates file {p}: {e}") from e
    if "rates" not in data or not isinstance(data["rates"], dict):
        raise RatesError("Rates file needs a 'rates' object")
    for cat, r in data["rates"].items():
        if not isinstance(r, dict) or "unit" not in r or "rate" not in r:
            raise RatesError(f"Rate for {cat!r} needs 'unit' and 'rate'")
    data.setdefault("currency", "INR")
    return data


def estimate_cost(plan: RenovationPlan, rates: dict, contingency_pct: float = 15.0) -> CostEstimate:
    if contingency_pct < 0:
        raise RatesError("contingency_pct cannot be negative")
    est = CostEstimate(currency=rates.get("currency", "INR"), contingency_pct=contingency_pct)
    table = rates["rates"]
    for it in plan.items:
        r = table.get(it.category)
        if r is None:
            est.unpriced.append(f"{it.name} (no rate for category '{it.category}')")
        elif r["unit"] != it.unit:
            est.unpriced.append(f"{it.name} (planned in '{it.unit}', rate is per '{r['unit']}')")
        else:
            amount = round(it.quantity * float(r["rate"]), 2)
            est.lines.append(CostLine(it.name, it.category, it.quantity, it.unit, float(r["rate"]), amount))
            est.subtotal += amount
    est.subtotal = round(est.subtotal, 2)
    est.contingency = round(est.subtotal * contingency_pct / 100.0, 2)
    est.total = round(est.subtotal + est.contingency, 2)
    return est
