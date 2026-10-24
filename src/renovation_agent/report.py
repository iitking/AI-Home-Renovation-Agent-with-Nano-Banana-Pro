from __future__ import annotations

from collections import defaultdict
from .costing import CostEstimate
from .planner import RenovationPlan


def _money(v: float, cur: str) -> str:
    return f"{cur} {v:,.0f}"


def build_report(
    plan: RenovationPlan,
    estimate: CostEstimate,
    style: str,
    original: str,
    renders: list[str],
) -> str:
    cur = estimate.currency
    L: list[str] = [
        f"# Renovation report: {plan.room_type.title()} ({style.title()})",
        "",
        "> **AI Renovation Agent Report** · Photorealistic redesign powered by Nano Banana Pro "
        "and market-benchmarked rate estimation.",
        "",
        "---",
        "",
        "## 📋 Executive Summary",
        "",
        f"- **Room Type:** {plan.room_type.title()}",
        f"- **Design Style:** {style.title()}",
        f"- **Total Estimated Budget:** **{_money(estimate.total, cur)}** (including {estimate.contingency_pct:g}% contingency)",
        f"- **Base Renovation Cost:** {_money(estimate.subtotal, cur)}",
        f"- **Scope of Work:** {len(estimate.lines)} priced items"
        + (f" + {len(estimate.unpriced)} unpriced items" if estimate.unpriced else ""),
        "",
        "## 🖼️ Before / After Gallery",
        "",
        f"- **Original Photo:** `{original}`",
    ]
    for i, r in enumerate(renders, 1):
        L.append(f"- **Design {i}:** `{r}`")

    if renders:
        L.append("")
        L.append(f"| Before (`{original}`) | After (`{renders[0]}`) |")
        L.append("|:---:|:---:|")
        L.append(f"| ![{original}]({original}) | ![{renders[0]}]({renders[0]}) |")

    if plan.observations:
        L += ["", "## 🔍 Room Assessment (What the agent saw)"]
        for o in plan.observations:
            L.append(f"- {o}")

    if plan.issues:
        L += ["", "## ⚠️ Issues & Defects Identified"]
        for iss in plan.issues:
            L.append(f"- {iss}")

    # Category Breakdown Summary
    if estimate.lines:
        cat_totals: dict[str, float] = defaultdict(float)
        cat_counts: dict[str, int] = defaultdict(int)
        for ln in estimate.lines:
            cat_totals[ln.category] += ln.amount
            cat_counts[ln.category] += 1

        L += [
            "",
            "## 📊 Budget by Category",
            "",
            "| Category | Items | Subtotal | % of Base |",
            "|---|---:|---:|---:|",
        ]
        sub = estimate.subtotal or 1.0
        for cat, amt in sorted(cat_totals.items(), key=lambda x: x[1], reverse=True):
            pct = (amt / sub) * 100
            L.append(f"| {cat.replace('_', ' ').title()} | {cat_counts[cat]} | {_money(amt, cur)} | {pct:.1f}% |")

    # Itemized Table
    L += [
        "",
        "## 🔨 Itemized Work & Cost Breakdown",
        "",
        "| Item | Category | Qty | Unit | Rate | Amount | Notes |",
        "|---|---|---:|---|---:|---:|---|",
    ]
    # Match item notes from plan if available
    notes_map = {it.name.strip().lower(): it.notes for it in plan.items}
    for ln in estimate.lines:
        notes = notes_map.get(ln.item.strip().lower(), "")
        L.append(
            f"| {ln.item} | {ln.category} | {ln.quantity:g} | {ln.unit} | "
            f"{ln.rate:,.0f} | {ln.amount:,.0f} | {notes} |"
        )

    L += [
        "",
        f"- Subtotal: **{_money(estimate.subtotal, cur)}**",
        f"- Contingency ({estimate.contingency_pct:g}%): {_money(estimate.contingency, cur)}",
        f"- **Total: {_money(estimate.total, cur)}**",
    ]

    if estimate.unpriced:
        L += [
            "",
            "### 📌 Not priced (needs manual contractor quote)",
            "The following items require on-site measurement, structural assessment, or custom vendor pricing:",
        ]
        for u in estimate.unpriced:
            L.append(f"- {u}")

    if plan.style_notes:
        L += ["", "## 🎨 Style & Aesthetic Notes", plan.style_notes]

    # Roadmap / Phase Guide
    L += [
        "",
        "## 🗓️ Recommended Renovation Phases",
        "",
        "1. **Phase 1: Civil & Infrastructure** – Demolition of dated tiles, plumbing rough-ins, electrical conduits & point shifting.",
        "2. **Phase 2: Shell & Surface Finishing** – False ceiling framing, gypsum board installation, wall treatment, base paint.",
        "3. **Phase 3: Millwork & Carpentry** – Modular storage, built-in TV console, laminate application, hardware fittings.",
        "4. **Phase 4: Lighting & Final Styling** – Architectural downlights, magnetic track lights, curtains/blinds, furniture & decor placement.",
        "",
        "---",
        "",
        "> 💡 **Important Contractor Note:** Estimates use real market benchmark rates and visually estimated quantities. "
        "Always obtain on-site laser measurements and formal written quotes from licensed contractors before signing contracts. "
        "AI renders serve as photorealistic design inspiration and conceptual direction.",
        "",
    ]

    return "\n".join(L)
