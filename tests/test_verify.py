import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.verify import tool


class FixtureTests(unittest.TestCase):
    def setUp(self):
        directory = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.fixture = directory / "seed.json"
        self.work = directory / "work"
        self.enterContext(patch.multiple(tool, FIXTURE=self.fixture, WORK=self.work))
        self.write_fixture(2)

    def write_fixture(self, frames, clock="2026-01-01T00:00:00Z"):
        self.values = {"clock": clock, "frames": frames}
        self.fixture.write_text(json.dumps(self.values), encoding="utf-8")

    def assert_seeded_tone(self, result, frames):
        expected_pcm = b"".join(tool.tone(frame) for frame in range(frames))
        self.assertEqual(result["frames"], frames)
        self.assertEqual(result["samples"], len(expected_pcm) // 2)
        self.assertEqual(result["pcm_sha256"], hashlib.sha256(expected_pcm).hexdigest())
        self.assertEqual(json.loads((self.work / "state.json").read_bytes()), self.values)

    def test_synthetic_tone_creates_missing_cache_and_reuses_valid_cache(self):
        self.assert_seeded_tone(tool.synthetic_tone(), 2)

        with patch.object(tool, "tone", side_effect=AssertionError("Regenerated valid PCM")):
            result = tool.synthetic_tone()

        self.assert_seeded_tone(result, 2)

    def test_synthetic_tone_reseeds_after_frame_count_changes(self):
        self.assert_seeded_tone(tool.synthetic_tone(), 2)

        self.write_fixture(3)

        self.assert_seeded_tone(tool.synthetic_tone(), 3)

    def test_synthetic_tone_refreshes_state_when_only_clock_changes(self):
        self.assert_seeded_tone(tool.synthetic_tone(), 2)

        self.write_fixture(2, clock="2026-01-02T00:00:00Z")

        self.assert_seeded_tone(tool.synthetic_tone(), 2)

    def test_synthetic_tone_rebuilds_truncated_pcm(self):
        self.assert_seeded_tone(tool.synthetic_tone(), 2)
        pcm = self.work / "tone.pcm"
        pcm.write_bytes(pcm.read_bytes()[:-1])

        self.assert_seeded_tone(tool.synthetic_tone(), 2)
