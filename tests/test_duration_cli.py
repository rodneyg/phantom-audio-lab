import socket
import subprocess
import sys
import unittest
from pathlib import Path


class DurationCliTests(unittest.TestCase):
    def test_duration_overflow_is_reported_as_argument_error(self):
        repo = Path(__file__).resolve().parents[1]
        with socket.socket() as unused:
            unused.bind(('127.0.0.1', 0))
            port = str(unused.getsockname()[1])
        result = subprocess.run(
            [sys.executable, str(repo / 'sender.py'), '--port', port, '--seconds', '1e308'],
            capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('argument --seconds: Seconds is too large', result.stderr)
        self.assertNotIn('Traceback', result.stderr)
