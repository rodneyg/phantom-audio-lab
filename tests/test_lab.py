import asyncio
import argparse
import json
import sys
import unittest
from functools import partial
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from protocol import MASK, PACKET_BYTES, Sequence, hello, packet, parse_hello, parse_packet
from receiver import receive
from sender import duration, port_number, send, tone


class ProtocolTests(unittest.TestCase):
    def test_hello(self):
        self.assertEqual(parse_hello(hello())['rate'], 16000)
        for bad in [b'{}', 'null', '[]', '{', '{}', hello().replace('16000', 'true'),
                    hello().replace('lab-tone', 'x' * 65), hello().replace('s16le', 'f32')]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                parse_hello(bad)

    def test_framing_and_boundaries(self):
        data = packet(MASK, tone(0))
        self.assertEqual(len(data), PACKET_BYTES)
        self.assertEqual(parse_packet(data), (MASK, tone(0)))
        self.assertTrue(any(tone(0)))
        for bad in [data[:-1], data + b'\0', 'text', b'']:
            with self.assertRaises(ValueError):
                parse_packet(bad)
        for number in [-1, MASK + 1, True]:
            with self.assertRaises(ValueError):
                packet(number, tone(0))

    def test_sequence_gap_duplicate_stale_and_wrap(self):
        state = Sequence()
        self.assertEqual([state.accept(n) for n in [MASK - 1, MASK, 0, 2, 2, 1, 3]],
                         [0, 0, 0, 1, None, None, 0])

    def test_cli_bounds(self):
        for value in ['0', '-1', 'nan', 'inf']:
            with self.assertRaises(argparse.ArgumentTypeError):
                duration(value)
        for value in ['0', '-1', '65536']:
            with self.assertRaises(argparse.ArgumentTypeError):
                port_number(value)


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_tones_reconnect_and_invalid_frame(self):
        results = []
        async with serve(partial(receive, report=lambda text: results.append(json.loads(text))),
                         '127.0.0.1', 0, max_size=2048, origins=[None]) as server:
            port = server.sockets[0].getsockname()[1]
            for _ in range(2):
                count = await send(port, .064)
                self.assertEqual(count, 2)
            async with connect(f'ws://127.0.0.1:{port}', proxy=None) as socket:
                await socket.send(hello())
                for number in [0, 2, 2, 1, 3]:
                    await socket.send(packet(number, tone(0)))
            async with connect(f'ws://127.0.0.1:{port}', proxy=None) as socket:
                await socket.send(hello())
                await socket.send(b'invalid')
                await socket.wait_closed()
                self.assertEqual(socket.close_code, 1008)
        self.assertEqual(len(results), 4)
        self.assertEqual([r['packets'] for r in results], [2, 2, 3, 0])
        self.assertEqual(results[2]['missing'], 1)
        self.assertEqual(results[2]['ignored'], 2)
        self.assertGreater(results[0]['peak_rms'], .05)
        self.assertTrue(results[3]['invalid'])


if __name__ == '__main__':
    unittest.main()
