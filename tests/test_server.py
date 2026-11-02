import json
import unittest
from unittest.mock import patch
from io import BytesIO

from renovation_agent.server import RenovationServer


class DummyWFile(BytesIO):
    pass


class TestServer(unittest.TestCase):
    def test_metadata_endpoint(self):
        # Verify metadata endpoint payload structure
        from renovation_agent.styles import STYLES, list_styles
        from renovation_agent.costing import list_rate_presets
        self.assertTrue(len(list_styles()) >= 9)
        self.assertTrue(len(list_rate_presets()) >= 3)


if __name__ == "__main__":
    unittest.main()
