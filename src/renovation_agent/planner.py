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
            if not isinstance(it, dict) or not str(it.get("name", "")).strip():
                continue  # skip malformed entries instead of failing the whole plan
            try:
                qty = float(it.get("quantity", 1))
            except (TypeError, ValueError):
                qty = 1.0
            cat = str(it.get("category", "other")).strip().lower()
            if cat not in CATEGORIES:
                cat = "other"
            items.append(PlanItem(
                name=str(it["name"]).strip(),
                category=cat,
                quantity=max(qty, 0.0),
                unit=str(it.get("unit", "unit")).strip().lower(),
                notes=str(it.get("notes", "")).strip(),
            ))
        return cls(
            room_type=room.strip().lower(),
            observations=[str(x) for x in d.get("observations", []) if str(x).strip()],
            issues=[str(x) for x in d.get("issues", []) if str(x).strip()],
            items=items,
            style_notes=str(d.get("style_notes", "")).strip(),
        )

    def highlights(self, limit: int = 8) -> list[str]:
        return [i.name for i in self.items[:limit]]


_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


def parse_plan(text: str) -> RenovationPlan:
    if not text or not text.strip():
        raise PlanError("Planner returned empty response")
    cleaned = _FENCE.sub("", text.strip())
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise PlanError("Planner response contained no JSON object")
    try:
        data = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as e:
        raise PlanError(f"Planner returned invalid JSON: {e}") from e
    return RenovationPlan.from_dict(data)


SYSTEM_PROMPT = (
    "You are an experienced interior designer and renovation planner. "
    "You look at a photo of a room and produce a practical renovation plan. "
    "Estimate quantities (e.g. wall/floor area in sq ft) from visual cues and say so in notes. "
    "Reply with ONE JSON object and nothing else."
)


def build_planner_prompt(style: str, brief: str = "") -> str:
    schema = {
        "room_type": "e.g. living room, bedroom, kitchen",
        "observations": ["what you see: layout, materials, lighting, condition"],
        "issues": ["problems to fix: damp, dated fixtures, poor lighting, clutter..."],
        "items": [{
            "name": "short description of the change",
            "category": " | ".join(CATEGORIES),
            "quantity": "number",
            "unit": " | ".join(UNITS),
            "notes": "assumptions behind the quantity",
        }],
        "style_notes": "how the plan achieves the target style",
    }
    out = [
        f"Target style: {style}.",
        "Plan the renovation of the room in the photo.",
    ]
    if brief.strip():
        out.append(f"Owner's requirements: {brief.strip()}")
    out.append("Use exactly this JSON shape:\n" + json.dumps(schema, indent=2))
    out.append("Use sqft for paint/wall_treatment/flooring/ceiling, unit for lighting/furniture/decor/electrical/plumbing, rft for carpentry, set for curtains_blinds.")
    return "\n\n".join(out)


class RoomPlanner:
    def __init__(self, client, model: str):
        self._client = client
        self._model = model

    def analyze(self, image, style: str, brief: str = "") -> RenovationPlan:
        response = self._client.models.generate_content(
            model=self._model,
            contents=[image, build_planner_prompt(style, brief)],
            config={
                "system_instruction": SYSTEM_PROMPT,
                "response_mime_type": "application/json",
                "temperature": 0.3,
            },
        )
        return parse_plan(getattr(response, "text", "") or "")
