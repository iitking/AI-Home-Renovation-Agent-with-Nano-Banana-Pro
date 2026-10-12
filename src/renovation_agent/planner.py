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

# Supported measurement units
