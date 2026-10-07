from __future__ import annotations

STYLES: dict[str, str] = {
    "modern": "clean lines, neutral palette, matte black and brushed metal accents, minimal clutter, hidden storage",
    "scandinavian": "light oak wood, white walls, soft textiles, airy and bright, functional furniture, cozy hygge touches",
    "japandi": "warm natural wood, muted earth tones, low furniture, paper lamps, calm and uncluttered",
    "industrial": "exposed brick or concrete finish, dark metal fixtures, reclaimed wood, Edison-style lighting",
    "minimalist": "very few items, monochrome palette, hidden handles, lots of negative space",
    "indian-contemporary": "warm earthy palette, handcrafted wood and cane, brass accents, subtle ethnic textiles, layered lighting",
    "bohemian": "layered rugs and textiles, plants, rattan, warm eclectic colours",
    "mid-century": "teak wood, tapered legs, mustard/teal accents, geometric patterns, statement lamp",
    "luxury": "marble surfaces, fluted panels, gold accents, velvet upholstery, concealed cove lighting",
}

PRESERVE_RULES = (
    "Keep the room's architecture EXACTLY the same: walls, windows, doors, ceiling height, "
    "room proportions and the camera angle/perspective must not change. "
    "Only change finishes, furniture, lighting, decor and colours. "
    "Result must be a photorealistic interior photograph with natural lighting, correct shadows "
    "and realistic scale. Do not add text, watermarks or people."
)


def list_styles() -> list[str]:
    return sorted(STYLES)


def build_render_prompt(
    style: str,
    room_type: str = "room",
    plan_highlights: list[str] | None = None,
    brief: str = "",
    variation_hint: str = "",
) -> str:
    if style not in STYLES:
        raise ValueError(f"Unknown style {style!r}. Available: {', '.join(list_styles())}")
    lines = [
        f"Redesign this {room_type} as a {style} interior renovation.",
        f"Style characteristics: {STYLES[style]}.",
    ]
    if plan_highlights:
        lines.append("Apply these planned changes: " + "; ".join(plan_highlights) + ".")
    if brief.strip():
        lines.append(f"Owner's requirements: {brief.strip()}")
    if variation_hint.strip():
        lines.append(variation_hint.strip())
    lines.append(PRESERVE_RULES)
    return "\n".join(lines)
