"""REAL end-to-end test against the Gemini API (costs a little money).

Skipped unless GEMINI_API_KEY is set AND RUN_LIVE=1, and a photo is given:
    RUN_LIVE=1 LIVE_PHOTO=examples/room.jpg GEMINI_API_KEY=... python -m pytest tests/test_live.py -v -s
"""
import os
import tempfile
import unittest
from pathlib import Path

from PIL import Image

LIVE = bool(os.environ.get("GEMINI_API_KEY") and os.environ.get("RUN_LIVE") == "1" and os.environ.get("LIVE_PHOTO"))


@unittest.skipUnless(LIVE, "set GEMINI_API_KEY, RUN_LIVE=1 and LIVE_PHOTO to run live test")
class TestLive(unittest.TestCase):
    def test_real_pipeline(self):
        from renovation_agent.agent import RenovationAgent
        from renovation_agent.config import Settings, make_client

        s = Settings.from_env()
        agent = RenovationAgent(s, make_client(s))
        out = Path(tempfile.mkdtemp())
        res = agent.run(os.environ["LIVE_PHOTO"], "modern", "brighter and more storage", variants=1, out_dir=out)
        self.assertTrue(res.plan.items)
        self.assertGreater(res.estimate.total, 0)
        img = Image.open(res.renders[0])
        self.assertGreater(min(img.size), 500)
        print("live outputs in", out)
        refined = agent.refine(res, "make the walls warm white")
        Image.open(refined).verify()
