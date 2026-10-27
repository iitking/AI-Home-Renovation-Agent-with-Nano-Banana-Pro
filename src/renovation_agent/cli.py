from __future__ import annotations

import argparse
import sys

from .agent import MAX_VARIANTS, RenovationAgent
from .config import ConfigError, Settings, make_client
from .costing import RatesError, list_rate_presets, load_rates
from .image_io import ImageError
from .planner import PlanError
from .renderer import RenderError
from .styles import STYLES, list_styles


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="renovate", description="AI home renovation agent (Nano Banana Pro)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("styles", help="List available design styles")
    rates_p = sub.add_parser("rates", help="List available rate presets or show rate card")
    rates_p.add_argument("--preset", default="default", help="Preset name (default, india-metro, india-tier2, us-standard) or custom JSON path")
    r = sub.add_parser("run", help="Analyse a room photo and generate redesigns")
    r.add_argument("--image", required=True, help="Path to room photo (jpg/png/webp)")
    r.add_argument("--style", default="modern", choices=list_styles())
    r.add_argument("--brief", default="", help="Your requirements, e.g. 'budget 3 lakh, need more storage'")
    r.add_argument("--variants", type=int, default=1, help=f"1-{MAX_VARIANTS} design variants")
    r.add_argument("--out", default=None, help="Output folder")
    r.add_argument("--rates", default=None, help="Preset name (e.g. india-metro, us-standard) or path to rates JSON")
    r.add_argument("--contingency", type=float, default=15.0, help="Contingency percent")
    r.add_argument("--interactive", action="store_true", help="Refine design 1 with follow-up instructions")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.cmd == "styles":
        for name in list_styles():
            print(f"{name:20s} {STYLES[name]}")
        return 0
    if args.cmd == "rates":
        try:
            data = load_rates(args.preset)
        except RatesError as e:
            print(f"error: {e}", file=sys.stderr)
            return 1
        name = data.get("name", args.preset)
        cur = data.get("currency", "INR")
        print(f"Rate Card: {name} (Currency: {cur})")
        print(f"Available presets: {', '.join(list_rate_presets())}\n")
        print(f"{'Category':20s} {'Unit':6s} {'Rate (' + cur + ')':>12s}  {'Description'}")
        print("-" * 75)
        for cat, r in data.get("rates", {}).items():
            desc = r.get("description", "")
            print(f"{cat:20s} {r.get('unit', ''):6s} {r.get('rate', 0):>12,g}  {desc}")
        return 0
    try:
        settings = Settings.from_env()
        agent = RenovationAgent(settings, make_client(settings), rates=load_rates(args.rates))
        res = agent.run(args.image, args.style, args.brief, args.variants, args.out, args.contingency)
    except (ConfigError, ImageError, PlanError, RenderError, RatesError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    print(f"Plan: {len(res.plan.items)} items | Total estimate: {res.estimate.currency} {res.estimate.total:,.0f}")
    for p in res.renders:
        print(f"Saved {p}")
    print(f"Report: {res.report_path}")
    if args.interactive:
        print("Refine design 1 (empty line to finish), e.g. 'make the sofa dark green'")
        while True:
            try:
                text = input("refine> ").strip()
            except EOFError:
                break
            if not text:
                break
            try:
                print(f"Saved {agent.refine(res, text)}")
            except RenderError as e:
                print(f"error: {e}", file=sys.stderr)
    return 0
