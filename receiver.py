"""Loopback-only transport diagnostic. No audio is stored or played."""
import argparse
import asyncio
import json
import math
import struct

from websockets.asyncio.server import serve
from websockets.exceptions import ConnectionClosed
from protocol import Sequence, parse_hello, parse_packet
from sender import duration, port_number


async def receive(socket, report=print):
    stats = dict(packets=0, missing=0, ignored=0, peak_rms=0.0)
    sequence = Sequence()
    try:
        parse_hello(await asyncio.wait_for(socket.recv(), 5))
        async for message in socket:
            number, pcm = parse_packet(message)
            missing = sequence.accept(number)
            if missing is None:
                stats['ignored'] += 1
                continue
            samples = struct.unpack('<512h', pcm)
            rms = math.sqrt(sum(n * n for n in samples) / len(samples)) / 32768
            stats.update(packets=stats['packets'] + 1, missing=stats['missing'] + missing,
                         peak_rms=round(max(stats['peak_rms'], rms), 6))
    except (ValueError, TypeError, TimeoutError):
        stats['invalid'] = True
        await socket.close(code=1008, reason='Invalid lab protocol')
    except ConnectionClosed:
        pass
    finally:
        report(json.dumps(stats))


async def listen(port, seconds=None):
    async with serve(receive, '127.0.0.1', port, max_size=2048, max_queue=4,
                     origins=[None], compression=None):
        print(f'Lab receiver: ws://127.0.0.1:{port}', flush=True)
        if seconds is None:
            await asyncio.Event().wait()
        else:
            await asyncio.sleep(seconds)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=port_number, default=8799)
    parser.add_argument('--seconds', type=duration)
    args = parser.parse_args()
    try:
        asyncio.run(listen(args.port, args.seconds))
    except KeyboardInterrupt:
        pass
