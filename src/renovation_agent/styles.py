from __future__ import annotations

STYLES: dict[str, str] = {
    "modern": "clean lines, neutral palette, matte black and brushed metal accents, minimal clutter, hidden storage",
    "scandinavian": "light oak wood, white walls, soft textiles, airy and bright, functional furniture, cozy hygge touches",
    "industrial": "exposed brick or concrete finish, dark metal fixtures, reclaimed wood, Edison-style lighting",
}

def list_styles() -> list[str]:
    return sorted(STYLES)

PRESERVE_RULES = (
    "Keep the room's architecture EXACTLY the same: walls, windows, doors, ceiling height, "
    "room proportions and the camera angle/perspective must not change. "
    "Only change finishes, furniture, lighting, decor and colours. "
    "Result must be a photorealistic interior photograph with natural lighting, correct shadows "
    "and realistic scale. Do not add text, watermarks or people."
)
