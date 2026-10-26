from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import Settings
from .costing import CostEstimate, estimate_cost, load_rates
from .image_io import load_image, nearest_aspect_ratio, save_image_bytes
from .planner import RenovationPlan, RoomPlanner
from .renderer import RenderSession
from .report import build_report
from .styles import build_render_prompt

VARIATION_HINTS = [
    "Keep the layout conventional, practical and budget-friendly.",
    "Be bolder with colour and materials while staying true to the style.",
    "Maximise natural light and the feeling of space.",
]
MAX_VARIANTS = len(VARIATION_HINTS)


@dataclass
class RunResult:
    out_dir: Path
    plan: RenovationPlan
    estimate: CostEstimate
    renders: list[Path] = field(default_factory=list)
    report_path: Path | None = None
    sessions: list[RenderSession] = field(default_factory=list)


class RenovationAgent:
    """Pipeline: photo -> plan (Gemini text) -> cost -> renders (Nano Banana Pro) -> report."""

    def __init__(self, settings: Settings, client, rates: dict | None = None, sleep=time.sleep):
        self.settings = settings
        self.client = client
        self.rates = rates if rates is not None else load_rates()
        self.planner = RoomPlanner(client, settings.planner_model)
        self._sleep = sleep

    def run(self, image_path: str | Path, style: str, brief: str = "",
            variants: int = 1, out_dir: str | Path | None = None,
            contingency_pct: float = 15.0) -> RunResult:
        if not 1 <= variants <= MAX_VARIANTS:
            raise ValueError(f"variants must be between 1 and {MAX_VARIANTS}")
        build_render_prompt(style)  # fail fast on unknown style, before any paid API call
        image = load_image(image_path)
        out = Path(out_dir) if out_dir else self.settings.output_dir / f"{Path(image_path).stem}_{int(time.time())}"
        out.mkdir(parents=True, exist_ok=True)

        plan = self.planner.analyze(image, style, brief)
        estimate = estimate_cost(plan, self.rates, contingency_pct)
        (out / "plan.json").write_text(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

        aspect = nearest_aspect_ratio(*image.size)
        result = RunResult(out_dir=out, plan=plan, estimate=estimate)
        for i in range(variants):
            prompt = build_render_prompt(style, plan.room_type, plan.highlights(), brief, VARIATION_HINTS[i])
            session = RenderSession(self.client, self.settings.image_model,
                                    self.settings.image_size, aspect, sleep=self._sleep)
            res = session.start(image, prompt)
            path = save_image_bytes(res.image_bytes, out / f"design_{i + 1}.png")
            result.renders.append(path)
            result.sessions.append(session)

        original_copy = out / "original.png"
        image.save(original_copy)
        report = build_report(plan, estimate, style, original_copy.name, [p.name for p in result.renders])
        result.report_path = out / "report.md"
        result.report_path.write_text(report, encoding="utf-8")
        return result

    def refine(self, result: RunResult, instruction: str, variant: int = 1) -> Path:
        session = result.sessions[variant - 1]
        res = session.refine(instruction)
        n = len(session.history) - 1
        path = save_image_bytes(res.image_bytes, result.out_dir / f"design_{variant}_refined_{n}.png")
        result.renders.append(path)
        return path
