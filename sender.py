"""Send generated tones to the lab receiver, never microphone audio."""
import argparse
import asyncio
import math
import struct
import time

from websockets.asyncio.client import connect
from protocol import FRAME_SECONDS, MASK, RATE, SAMPLES, hello, packet


def port_number(value):
    number = int(value)
    if not 1 <= number <= 65535:
        raise argparse.ArgumentTypeError('Port must be 1 to 65535')
    return number


def duration(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError('Seconds must be positive and finite')
    return number


def tone(frame):
    return struct.pack('<512h', *(round(3000 * math.sin(2 * math.pi * 440 *
        (frame * SAMPLES + n) / RATE)) for n in range(SAMPLES)))


async def send(port, seconds):
    async with connect(f'ws://127.0.0.1:{port}', proxy=None, compression=None) as socket:
        await socket.send(hello())
        started = time.monotonic()
        count = math.ceil(seconds / FRAME_SECONDS)
        for frame in range(count):
            await socket.send(packet(frame & MASK, tone(frame)))
            await asyncio.sleep(max(0, started + (frame + 1) * FRAME_SECONDS - time.monotonic()))
        return count


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=port_number, default=8799)
    parser.add_argument('--seconds', type=duration, default=3)
    args = parser.parse_args()
    print(f'Sent {asyncio.run(send(args.port, args.seconds))} generated tone frames.')
