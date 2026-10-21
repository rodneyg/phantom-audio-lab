"""Small, independent PCM transport specification. No product imports."""
import json
import struct

RATE = 16000
SAMPLES = 512
FRAME_SECONDS = SAMPLES / RATE
PACKET_BYTES = 4 + SAMPLES * 2
MASK = 0xffffffff


def hello():
    return json.dumps(dict(device='lab-tone', room='Test lab', rate=RATE, format='s16le'))


def parse_hello(message):
    if not isinstance(message, str) or len(message) > 2048:
        raise ValueError('Expected a small JSON text hello')
    value = json.loads(message)
    if not isinstance(value, dict) or set(value) != {'device', 'room', 'rate', 'format'}:
        raise ValueError('Expected device, room, rate, format')
    if any(not isinstance(value[k], str) or not 1 <= len(value[k]) <= 64
           or any(ord(c) < 32 for c in value[k]) for k in ('device', 'room')):
        raise ValueError('Invalid device or room')
    if type(value['rate']) is not int or value['rate'] != RATE or value['format'] != 's16le':
        raise ValueError('Expected 16 kHz s16le')
    return value


def packet(sequence, pcm):
    if type(sequence) is not int or not 0 <= sequence <= MASK:
        raise ValueError('Sequence must be uint32')
    if not isinstance(pcm, bytes) or len(pcm) != SAMPLES * 2:
        raise ValueError('Expected exactly 512 mono int16 samples')
    return struct.pack('<I', sequence) + pcm


def parse_packet(data):
    if not isinstance(data, bytes) or len(data) != PACKET_BYTES:
        raise ValueError('Invalid binary PCM frame')
    return struct.unpack_from('<I', data)[0], data[4:]


class Sequence:
    """Return missing frame count; None means duplicate or stale frame."""
    def __init__(self):
        self.last = None

    def accept(self, sequence):
        delta = 1 if self.last is None else (sequence - self.last) & MASK
        if delta == 0 or delta >= 0x80000000:
            return None
        self.last = sequence
        return delta - 1
