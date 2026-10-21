from __future__ import annotations

import time
from dataclasses import dataclass


class RenderError(RuntimeError):
    pass


@dataclass
class RenderResult:
    image_bytes: bytes
    mime_type: str
    text: str = ""


def extract_result(response) -> RenderResult:
    """Pull the final image (and any text) out of a Gemini response.

    Nano Banana Pro may emit interim "thought" images; those are skipped.
    """
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        raise RenderError(f"Model returned no candidates (feedback={getattr(response, 'prompt_feedback', None)})")
    cand = candidates[0]
    parts = getattr(getattr(cand, "content", None), "parts", None) or []
    texts: list[str] = []
    image: tuple[bytes, str] | None = None
    for part in parts:
        if getattr(part, "thought", False):
            continue
        inline = getattr(part, "inline_data", None)
        data = getattr(inline, "data", None) if inline is not None else None
        if data:
            image = (data, getattr(inline, "mime_type", None) or "image/png")
        elif getattr(part, "text", None):
            texts.append(part.text)
    if image is None:
        raise RenderError(
            f"Model returned no image (finish_reason={getattr(cand, 'finish_reason', None)}, "
            f"text={' '.join(texts)[:300]!r}). The prompt may have been blocked by safety filters."
        )
    return RenderResult(image_bytes=image[0], mime_type=image[1], text=" ".join(texts).strip())


def _with_retry(fn, attempts: int = 3, base_delay: float = 2.0, sleep=time.sleep):
    last: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except RenderError:
            raise  # deterministic failure, retrying will not help
        except Exception as e:  # network / 429 / 5xx
            last = e
            if i < attempts - 1:
                sleep(base_delay * (2 ** i))
    raise RenderError(f"Gemini API call failed after {attempts} attempts: {last}") from last


class RenderSession:
    """Multi-turn editing session on one render (uses a Gemini chat so context is kept)."""

    def __init__(self, client, model: str, image_size: str = "2K",
                 aspect_ratio: str | None = None, sleep=time.sleep):
        image_config: dict = {"image_size": image_size}
        if aspect_ratio:
            image_config["aspect_ratio"] = aspect_ratio
        self._chat = client.chats.create(
            model=model,
            config={"response_modalities": ["TEXT", "IMAGE"], "image_config": image_config},
        )
        self._sleep = sleep
        self.history: list[RenderResult] = []

    def start(self, image, prompt: str) -> RenderResult:
        return self._send([prompt, image])

    def refine(self, instruction: str) -> RenderResult:
        if not self.history:
            raise RenderError("Call start() before refine()")
        if not instruction.strip():
            raise RenderError("Empty refinement instruction")
        return self._send(instruction)

    def _send(self, message) -> RenderResult:
        response = _with_retry(lambda: self._chat.send_message(message), sleep=self._sleep)
        result = extract_result(response)
        self.history.append(result)
        return result
