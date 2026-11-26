import asyncio
import sys
import unittest
from pathlib import Path

from websockets.asyncio.server import serve

ROOT = Path(__file__).resolve().parents[1]


class SenderDisconnectTests(unittest.IsolatedAsyncioTestCase):
    async def test_sender_explains_receiver_shutdown_during_tone(self):
        received = []

        async def stop_after_first_frame(socket):
            await socket.recv()  # Hello
            received.append(await socket.recv())
            await socket.close(code=1001)

        async with serve(stop_after_first_frame, '127.0.0.1', 0) as server:
            port = server.sockets[0].getsockname()[1]
            sender = await asyncio.create_subprocess_exec(
                sys.executable, str(ROOT / 'sender.py'),
                '--port', str(port), '--seconds', '2',
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(sender.communicate(), timeout=8)
            finally:
                if sender.returncode is None:
                    sender.kill()
                    await sender.wait()

        self.assertEqual(len(received), 1)
        self.assertEqual(sender.returncode, 1)
        self.assertEqual(stdout, b'')
        self.assertEqual(
            stderr.decode().strip(),
            f'The connection to the lab receiver on port {port} closed during the tone. '
            'Check that the receiver is running and try again.',
        )
