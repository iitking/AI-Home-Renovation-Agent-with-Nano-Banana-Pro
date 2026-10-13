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

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RenovationPlan":
        if not isinstance(d, dict):
            raise PlanError("Plan must be a JSON object")
        room = d.get("room_type")
        if not isinstance(room, str) or not room.strip():
            raise PlanError("Plan is missing 'room_type'")
        raw_items = d.get("items", [])
        if not isinstance(raw_items, list):
            raise PlanError("'items' must be a list")
        items: list[PlanItem] = []
        for it in raw_items:
            if not isinstance(it, dict):
                continue
            cat = str(it.get("category", "other")).lower()
            if cat not in CATEGORIES:
                cat = "other"
            unit = str(it.get("unit", "unit")).lower()
            if unit not in UNITS:
                unit = "unit"
            try:
                qty = float(it.get("quantity", 1.0))
            except (TypeError, ValueError):
                qty = 1.0
            items.append(
                PlanItem(
                    name=str(it.get("name", "Unnamed item")).strip(),
                    category=cat,
                    quantity=max(qty, 0.0),
                    unit=unit,
                    notes=str(it.get("notes", "")).strip(),
                )
            )
        return cls(
            room_type=room.strip(),
            observations=[str(x) for x in d.get("observations", [])],
            issues=[str(x) for x in d.get("issues", [])],
            items=items,
            style_notes=str(d.get("style_notes", "")).strip(),
        )

# Validates type assertions on incoming dictionaries
