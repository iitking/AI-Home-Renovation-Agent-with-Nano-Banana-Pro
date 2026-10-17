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
