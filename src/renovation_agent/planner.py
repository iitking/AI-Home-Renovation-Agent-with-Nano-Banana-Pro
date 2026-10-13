from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

CATEGORIES = [
    "paint", "wall_treatment", "flooring", "ceiling", "lighting", "furniture",
    "curtains_blinds", "decor", "electrical", "plumbing", "carpentry", "other",
]
UNITS = ["sqft", "unit", "rft", "set", "lump"]

class PlanError(ValueError):
    pass

@dataclass
class PlanItem:
    name: str
    category: str
    quantity: float
    unit: str
    notes: str = ""

@dataclass
class RenovationPlan:
    room_type: str
    observations: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    items: list[PlanItem] = field(default_factory=list)
    style_notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
