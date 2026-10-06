import pytest
from renovation_agent.styles import STYLES, build_render_prompt, list_styles

def test_styles_registry_not_empty():
    assert len(STYLES) >= 3
    for k, v in STYLES.items():
        assert isinstance(k, str) and k
        assert isinstance(v, str) and len(v) > 10

def test_list_styles_sorted():
    styles = list_styles()
    assert styles == sorted(STYLES.keys())

def test_build_render_prompt_valid():
    prompt = build_render_prompt(
        style="modern",
        room_type="living room",
        plan_highlights=["Add track lighting", "Replace flooring"],
        brief="Keep it warm",
    )
    assert "modern" in prompt
    assert "living room" in prompt
    assert "Add track lighting" in prompt
    assert "Keep it warm" in prompt
    assert "EXACTLY the same" in prompt

def test_build_render_prompt_unknown_style():
    with pytest.raises(ValueError, match="Unknown style 'baroque'"):
        build_render_prompt("baroque")
