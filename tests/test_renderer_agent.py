import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

from renovation_agent.agent import RenovationAgent
from renovation_agent.cli import build_parser, main
from renovation_agent.config import ConfigError, Settings
from renovation_agent.image_io import ImageError
from renovation_agent.planner import PlanError
from renovation_agent.renderer import RenderError, RenderSession, extract_result
from helpers import FakeClient, image_response, png_bytes

NOSLEEP = lambda s: None


class TestExtract(unittest.TestCase):
    def test_skips_thought_images_and_keeps_text(self):
        r = extract_result(image_response(color=(0, 255, 0), text="done", with_thought=True))
        self.assertEqual(r.image_bytes, png_bytes((0, 255, 0)))
        self.assertEqual(r.text, "done")

    def test_no_candidates(self):
        with self.assertRaises(RenderError):
            extract_result(SimpleNamespace(candidates=[], prompt_feedback="BLOCKED"))

    def test_text_only_is_error(self):
        resp = SimpleNamespace(candidates=[SimpleNamespace(
            content=SimpleNamespace(parts=[SimpleNamespace(thought=None, text="I can't", inline_data=None)]),
            finish_reason="SAFETY")])
        with self.assertRaisesRegex(RenderError, "no image"):
            extract_result(resp)


class TestSession(unittest.TestCase):
    def test_config_and_refine(self):
        c = FakeClient()
        s = RenderSession(c, "img-model", "4K", "16:9", sleep=NOSLEEP)
        model, cfg = c.chat_configs[0]
        self.assertEqual(model, "img-model")
        self.assertEqual(cfg["image_config"], {"image_size": "4K", "aspect_ratio": "16:9"})
        self.assertIn("IMAGE", cfg["response_modalities"])
        with self.assertRaises(RenderError):
            s.refine("too early")
        s.start("IMG", "prompt")
        s.refine("make sofa green")
        self.assertEqual(len(s.history), 2)
        self.assertEqual(c.chat_messages[1], "make sofa green")
        with self.assertRaises(RenderError):
            s.refine("  ")

    def test_retry_on_transient_error(self):
        c = FakeClient(fail_first_n=2)
        s = RenderSession(c, "m", sleep=NOSLEEP)
        self.assertTrue(s.start("IMG", "p").image_bytes)
        self.assertEqual(c.sends, 3)

    def test_gives_up_after_3(self):
        c = FakeClient(fail_first_n=99)
        s = RenderSession(c, "m", sleep=NOSLEEP)
        with self.assertRaisesRegex(RenderError, "3 attempts"):
            s.start("IMG", "p")


class TestAgentEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.photo = self.tmp / "room.jpg"
        Image.new("RGB", (1600, 1200), (180, 170, 160)).save(self.photo)
        self.settings = Settings(api_key="k", image_size="2K", output_dir=self.tmp / "out")

    def test_full_run(self):
        c = FakeClient()
        agent = RenovationAgent(self.settings, c, sleep=NOSLEEP)
        res = agent.run(self.photo, "scandinavian", "need storage", variants=2, out_dir=self.tmp / "run")
        names = sorted(p.name for p in (self.tmp / "run").iterdir())
        self.assertEqual(names, ["design_1.png", "design_2.png", "original.png", "plan.json", "report.md"])
        for n in ("design_1.png", "design_2.png"):
            Image.open(self.tmp / "run" / n).verify()
        # different variation hints sent per variant, aspect ratio derived from photo (1600x1200 = 4:3)
        self.assertNotEqual(c.chat_messages[0][0], c.chat_messages[1][0])
        self.assertEqual(c.chat_configs[0][1]["image_config"]["aspect_ratio"], "4:3")
        self.assertIn("scandinavian", c.chat_messages[0][0])
        self.assertIn("need storage", c.chat_messages[0][0])
        self.assertIn("Repaint walls", c.chat_messages[0][0])
        saved = json.loads((self.tmp / "run" / "plan.json").read_text())
        self.assertEqual(saved["room_type"], "living room")
        self.assertIn("Total", res.report_path.read_text())
        # refinement writes a new file
        out = agent.refine(res, "darker floor")
        self.assertTrue(out.exists())
        self.assertEqual(out.name, "design_1_refined_1.png")

    def test_fail_fast_before_api_call(self):
        c = FakeClient()
        agent = RenovationAgent(self.settings, c, sleep=NOSLEEP)
        with self.assertRaises(ValueError):
            agent.run(self.photo, "nonexistent-style")
        with self.assertRaises(ValueError):
            agent.run(self.photo, "modern", variants=9)
        with self.assertRaises(ImageError):
            agent.run(self.tmp / "missing.jpg", "modern")
        self.assertEqual(c.planner_calls, [])  # no paid calls were made

    def test_bad_planner_output(self):
        agent = RenovationAgent(self.settings, FakeClient(plan_text="lol no json"), sleep=NOSLEEP)
        with self.assertRaises(PlanError):
            agent.run(self.photo, "modern", out_dir=self.tmp / "r2")


class TestConfigCli(unittest.TestCase):
    def test_missing_key(self):
        import os
        old = {k: os.environ.pop(k, None) for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY")}
        try:
            # run from empty dir so a stray .env is not picked up
            cwd = os.getcwd(); os.chdir(tempfile.mkdtemp())
            try:
                with self.assertRaises(ConfigError):
                    Settings.from_env()
                self.assertEqual(main(["run", "--image", "x.jpg"]), 1)
            finally:
                os.chdir(cwd)
        finally:
            for k, v in old.items():
                if v is not None:
                    os.environ[k] = v

    def test_env_overrides(self):
        import os
        os.environ.update(GEMINI_API_KEY="abc", RENOVATION_IMAGE_SIZE="4k")
        try:
            s = Settings.from_env()
            self.assertEqual((s.api_key, s.image_size, s.image_model), ("abc", "4K", "gemini-3-pro-image-preview"))
            os.environ["RENOVATION_IMAGE_SIZE"] = "8K"
            with self.assertRaises(ConfigError):
                Settings.from_env()
        finally:
            for k in ("GEMINI_API_KEY", "RENOVATION_IMAGE_SIZE"):
                os.environ.pop(k, None)

    def test_parser_and_styles_cmd(self):
        a = build_parser().parse_args(["run", "--image", "a.jpg", "--style", "japandi", "--variants", "2"])
        self.assertEqual((a.style, a.variants), ("japandi", 2))
        self.assertEqual(main(["styles"]), 0)
        self.assertEqual(main(["rates"]), 0)
        self.assertEqual(main(["rates", "--preset", "us-standard"]), 0)


if __name__ == "__main__":
    unittest.main()
