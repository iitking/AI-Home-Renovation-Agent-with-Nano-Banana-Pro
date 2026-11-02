from __future__ import annotations

import base64
import io
import json
import mimetypes
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from PIL import Image

from .agent import MAX_VARIANTS, RenovationAgent
from .config import ConfigError, Settings, make_client
from .costing import list_rate_presets, load_rates
from .image_io import ImageError
from .planner import PlanError
from .renderer import RenderError
from .styles import STYLES, list_styles

STATIC_DIR = Path(__file__).parent / "static"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


class RenovationServer(BaseHTTPRequestHandler):
    agent: RenovationAgent | None = None
    last_result: Any = None

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"[{self.log_date_time_string()}] {format % args}\n")

    def _send_json(self, data: Any, status: int = 200) -> None:
        raw = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(raw)

    def _send_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File not found")
            return
        mime, _ = mimetypes.guess_type(str(file_path))
        mime = mime or "application/octet-stream"
        raw = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path == "/" or path == "/index.html":
            self._send_file(STATIC_DIR / "index.html")
            return

        if path == "/api/metadata":
            presets = list_rate_presets()
            styles_data = [{"id": s, "description": STYLES[s]} for s in list_styles()]
            samples = [
                {"name": "Living Room", "path": "examples/room.jpg"},
                {"name": "Bedroom", "path": "examples/bedroom.jpg"},
                {"name": "Kitchen", "path": "examples/kitchen.jpg"},
            ]
            self._send_json({
                "styles": styles_data,
                "rate_presets": presets,
                "samples": samples,
            })
            return

        # Serve static assets or outputs or examples
        if path.startswith("/outputs/"):
            rel = path.removeprefix("/outputs/")
            file_path = PROJECT_ROOT / "outputs" / rel
            self._send_file(file_path)
            return

        if path.startswith("/examples/"):
            rel = path.removeprefix("/examples/")
            file_path = PROJECT_ROOT / "examples" / rel
            self._send_file(file_path)
            return

        if path.startswith("/static/"):
            rel = path.removeprefix("/static/")
            file_path = STATIC_DIR / rel
            self._send_file(file_path)
            return

        self.send_error(404, "Path not found")

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON payload"}, 400)
            return

        if path == "/api/renovate":
            self._handle_renovate(payload)
        elif path == "/api/refine":
            self._handle_refine(payload)
        else:
            self.send_error(404, "Unknown endpoint")

    def _handle_renovate(self, payload: dict) -> None:
        style = payload.get("style", "japandi")
        brief = payload.get("brief", "")
        variants = int(payload.get("variants", 1))
        rate_preset = payload.get("rates", "default")

        # Determine input image
        sample_path = payload.get("sample_image")
        image_base64 = payload.get("image_base64")

        temp_image_path = None
        if sample_path:
            input_file = PROJECT_ROOT / sample_path
        elif image_base64:
            if "," in image_base64:
                image_base64 = image_base64.split(",", 1)[1]
            data = base64.b64decode(image_base64)
            temp_dir = PROJECT_ROOT / "outputs" / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_image_path = temp_dir / f"upload_{int(time.time()*1000)}.jpg"
            temp_image_path.write_bytes(data)
            input_file = temp_image_path
        else:
            self._send_json({"error": "No image provided (either sample_image or image_base64 required)"}, 400)
            return

        try:
            settings = Settings.from_env()
            rates = load_rates(rate_preset)
            agent = RenovationAgent(settings, make_client(settings), rates=rates)
            self.__class__.agent = agent
            res = agent.run(input_file, style=style, brief=brief, variants=variants)
            self.__class__.last_result = res

            # Build URL paths for client
            rel_renders = ["/outputs/" + str(p.relative_to(PROJECT_ROOT / "outputs")) for p in res.renders]
            rel_original = "/outputs/" + str((res.out_dir / "original.png").relative_to(PROJECT_ROOT / "outputs"))
            report_text = res.report_path.read_text(encoding="utf-8") if res.report_path else ""

            self._send_json({
                "success": True,
                "room_type": res.plan.room_type,
                "style": style,
                "estimate": {
                    "currency": res.estimate.currency,
                    "subtotal": res.estimate.subtotal,
                    "contingency": res.estimate.contingency,
                    "contingency_pct": res.estimate.contingency_pct,
                    "total": res.estimate.total,
                    "lines": [
                        {
                            "item": l.item,
                            "category": l.category,
                            "quantity": l.quantity,
                            "unit": l.unit,
                            "rate": l.rate,
                            "amount": l.amount,
                        }
                        for l in res.estimate.lines
                    ],
                    "unpriced": res.estimate.unpriced,
                },
                "plan": res.plan.to_dict(),
                "original_url": rel_original,
                "render_urls": rel_renders,
                "report_markdown": report_text,
            })
        except (ConfigError, ImageError, PlanError, RenderError, ValueError) as e:
            self._send_json({"error": str(e)}, 500)
        except Exception as e:
            self._send_json({"error": f"Internal error: {e}"}, 500)
        finally:
            if temp_image_path and temp_image_path.exists():
                try:
                    temp_image_path.unlink()
                except OSError:
                    pass

    def _handle_refine(self, payload: dict) -> None:
        instruction = payload.get("instruction", "").strip()
        variant = int(payload.get("variant", 1))
        if not instruction:
            self._send_json({"error": "Instruction is required"}, 400)
            return
        if not self.__class__.last_result or not self.__class__.agent:
            self._send_json({"error": "No active renovation session. Run a renovation first."}, 400)
            return

        try:
            path = self.__class__.agent.refine(self.__class__.last_result, instruction, variant=variant)
            rel_path = "/outputs/" + str(path.relative_to(PROJECT_ROOT / "outputs"))
            self._send_json({
                "success": True,
                "refined_url": rel_path,
                "instruction": instruction,
            })
        except Exception as e:
            self._send_json({"error": str(e)}, 500)


def start_server(port: int = 8000, open_browser: bool = True) -> None:
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", port), RenovationServer)
    url = f"http://localhost:{port}"
    print(f"\n🏠 AI Home Renovation Web UI is running at: {url}")
    print("Press Ctrl+C to stop the server.\n")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()
