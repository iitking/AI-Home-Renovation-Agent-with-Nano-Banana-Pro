from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .planner import PlanItem, RenovationPlan

DATA_DIR = Path(__file__).parent / "data"

class CostError(ValueError):
    pass

@dataclass
class CostItem:
    name: str
    category: str
    quantity: float
    unit: str
    unit_rate: float
    total: float
    notes: str = ""

@dataclass
class CostEstimate:
    currency: str
    items: list[CostItem] = field(default_factory=list)
    subtotals_by_category: dict[str, float] = field(default_factory=dict)
    contingency_percent: float = 10.0
    contingency_amount: float = 0.0
    grand_total: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
