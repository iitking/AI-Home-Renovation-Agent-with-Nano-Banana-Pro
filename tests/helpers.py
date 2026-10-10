"""Fake Gemini client used ONLY in offline tests. Live tests are in test_live.py."""
import io
import json
from types import SimpleNamespace

from PIL import Image

GOOD_PLAN = {
    "room_type": "Living Room",
    "observations": ["Beige walls", "Single ceiling light"],
    "issues": ["Poor lighting"],
    "items": [
        {"name": "Repaint walls", "category": "paint", "quantity": 400, "unit": "sqft", "notes": "approx"},
        {"name": "Floor lamps", "category": "lighting", "quantity": 3, "unit": "unit"},
        {"name": "Custom TV unit", "category": "carpentry", "quantity": 8, "unit": "rft"},
        {"name": "Mystery work", "category": "weird_cat", "quantity": 1, "unit": "lump"},
    ],
    "style_notes": "Warm and airy",
}


def png_bytes(color=(200, 50, 50), size=(64, 48)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def image_response(color=(200, 50, 50), text="here you go", with_thought=False):
    parts = []
    if with_thought:
        parts.append(SimpleNamespace(thought=True, text=None,
                                     inline_data=SimpleNamespace(data=png_bytes((1, 1, 1)), mime_type="image/png")))
    parts.append(SimpleNamespace(thought=None, text=text, inline_data=None))
    parts.append(SimpleNamespace(thought=None, text=None,
                                 inline_data=SimpleNamespace(data=png_bytes(color), mime_type="image/png")))
    return SimpleNamespace(candidates=[SimpleNamespace(content=SimpleNamespace(parts=parts), finish_reason="STOP")])


class FakeChat:
    def __init__(self, owner, model, config):
        self.owner, self.model, self.config = owner, model, config

    def send_message(self, message):
        self.owner.chat_messages.append(message)
        self.owner.sends += 1
        if self.owner.fail_first_n and self.owner.sends <= self.owner.fail_first_n:
            raise ConnectionError("transient")
        return image_response(color=(10 * self.owner.sends % 255, 80, 160), with_thought=True)


class FakeClient:
    def __init__(self, plan_text=None, fail_first_n=0):
        self.plan_text = plan_text if plan_text is not None else json.dumps(GOOD_PLAN)
        self.fail_first_n = fail_first_n
        self.sends = 0
        self.chat_messages = []
        self.planner_calls = []
        self.chat_configs = []
        self.models = SimpleNamespace(generate_content=self._generate)
        self.chats = SimpleNamespace(create=self._create_chat)

    def _generate(self, model, contents, config):
        self.planner_calls.append((model, contents, config))
        return SimpleNamespace(text=self.plan_text)

    def _create_chat(self, model, config):
        self.chat_configs.append((model, config))
        return FakeChat(self, model, config)
