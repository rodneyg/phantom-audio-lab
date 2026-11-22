#!/usr/bin/env python3
"""Deterministic, offline verification for Phantom Audio Lab."""
from __future__ import annotations
import argparse, asyncio, hashlib, json, os, shutil, struct, subprocess, sys, tempfile, zlib
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from protocol import MASK, PACKET_BYTES, Sequence, hello, packet, parse_packet
from receiver import receive
from sender import tone
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

HERE = Path(__file__).resolve().parent
WORK = ROOT / ".verify" / "work"
FIXTURE = HERE / "fixtures" / "seed.json"
FLOW_BASELINES = HERE / "baselines" / "flows"
SHOT_BASELINES = HERE / "baselines" / "screenshots"
FLOWS = ("framing-round-trip", "sequence-gap", "synthetic-tone", "reconnect")
PAGES = ("waveform",)

def stable_json(value):
    return json.dumps(value, indent=2, sort_keys=True, separators=(",", ": ")) + "\n"

def config():
    return json.loads(FIXTURE.read_text())

def seed(quiet=False):
    values = config()
    WORK.mkdir(parents=True, exist_ok=True)
    pcm = b"".join(tone(frame) for frame in range(values["frames"]))
    (WORK / "tone.pcm").write_bytes(pcm)
    (WORK / "state.json").write_text(stable_json(values))
    result = {"clock": values["clock"], "frames": values["frames"], "ok": True,
              "state": ".verify/work", "tone_sha256": hashlib.sha256(pcm).hexdigest()}
    if not quiet:
        print(stable_json(result), end="")
    return result

def ensure_seeded():
    if not (WORK / "tone.pcm").is_file() or not (WORK / "state.json").is_file():
        seed(quiet=True)

def framing_round_trip():
    pcm = tone(0)
    data = packet(7, pcm)
    seq, parsed = parse_packet(data)
    return {"bytes": len(data), "packet_bytes": PACKET_BYTES,
            "round_trip_equal": parsed == pcm, "seq": seq}

def sequence_gap():
    inputs = [MASK - 1, MASK, 0, 2, 2, 1, 3]
    state = Sequence()
    accepted = [state.accept(number) for number in inputs]
    return {"accepted_missing": accepted, "ignored": sum(v is None for v in accepted),
            "inputs": inputs, "missing": sum(v for v in accepted if v is not None)}

def synthetic_tone():
    ensure_seeded()
    pcm = (WORK / "tone.pcm").read_bytes()
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    rms = (sum(v * v for v in samples) / len(samples)) ** 0.5 / 32768
    return {"frames": config()["frames"], "pcm_sha256": hashlib.sha256(pcm).hexdigest(),
            "peak": max(abs(v) for v in samples), "peak_rms": round(rms, 6), "samples": len(samples)}

async def reconnect_result():
    reports = []
    callback = lambda text: reports.append(json.loads(text))
    async with serve(partial(receive, report=callback), "127.0.0.1", 0,
                     max_size=2048, origins=[None], compression=None) as server:
        port = server.sockets[0].getsockname()[1]
        for _ in range(2):
            async with connect(f"ws://127.0.0.1:{port}", proxy=None, compression=None) as socket:
                await socket.send(hello())
                for number in range(2):
                    await socket.send(packet(number, tone(number)))
    keys = ("packets", "missing", "ignored", "peak_rms")
    deliveries = [{key: report[key] for key in keys} for report in reports]
    return {"connections": len(deliveries), "deliveries": deliveries}

def flow_result(name):
    functions = {"framing-round-trip": framing_round_trip, "sequence-gap": sequence_gap,
                 "synthetic-tone": synthetic_tone, "reconnect": lambda: asyncio.run(reconnect_result())}
    if name not in functions:
        raise KeyError(name)
    return {"flow": name, "ok": True, "result": functions[name]()}

def png_chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xffffffff)

def render_waveform(path):
    ensure_seeded()
    width, height = 960, 480
    pixels = bytearray((248, 250, 252)) * (width * height)
    def dot(x, y, color):
        if 0 <= x < width and 0 <= y < height:
            offset = (y * width + x) * 3
            pixels[offset:offset + 3] = bytes(color)
    def line(x0, y0, x1, y1, color):
        dx, dy = abs(x1-x0), -abs(y1-y0); sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1
        error = dx + dy
        while True:
            dot(x0, y0, color)
            if x0 == x1 and y0 == y1: break
            twice = 2 * error
            if twice >= dy: error += dy; x0 += sx
            if twice <= dx: error += dx; y0 += sy
    glyphs = {
        " ": ("00000",)*7, "0": ("01110","10001","10011","10101","11001","10001","01110"),
        "2": ("01110","10001","00001","00010","00100","01000","11111"),
        "4": ("00010","00110","01010","10010","11111","00010","00010"),
        "A": ("01110","10001","10001","11111","10001","10001","10001"),
        "C": ("01111","10000","10000","10000","10000","10000","01111"),
        "D": ("11110","10001","10001","10001","10001","10001","11110"),
        "E": ("11111","10000","10000","11110","10000","10000","11111"),
        "F": ("11111","10000","10000","11110","10000","10000","10000"),
        "G": ("01111","10000","10000","10111","10001","10001","01111"),
        "I": ("11111","00100","00100","00100","00100","00100","11111"),
        "K": ("10001","10010","10100","11000","10100","10010","10001"),
        "M": ("10001","11011","10101","10101","10001","10001","10001"),
        "N": ("10001","11001","10101","10011","10001","10001","10001"),
        "O": ("01110","10001","10001","10001","10001","10001","01110"),
        "P": ("11110","10001","10001","11110","10000","10000","10000"),
        "R": ("11110","10001","10001","11110","10100","10010","10001"),
        "S": ("01111","10000","10000","01110","00001","00001","11110"),
        "T": ("11111","00100","00100","00100","00100","00100","00100"),
    }
    def text(x, y, value, scale=2):
        for character in value:
            for row, bits in enumerate(glyphs[character]):
                for column, bit in enumerate(bits):
                    if bit == "1":
                        for yy in range(scale):
                            for xx in range(scale): dot(x+column*scale+xx, y+row*scale+yy, (30, 41, 59))
            x += 6 * scale
    text(40, 32, "FRAMES 4  PACKETS 2  MISSING 0  IGNORED 0")
    for y in (80, 240, 400): line(40, y, 919, y, (203, 213, 225))
    pcm = (WORK / "tone.pcm").read_bytes()
    samples = struct.unpack(f"<{len(pcm)//2}h", pcm)
    points = [(x, 240 - round(samples[(x-40)*(len(samples)-1)//879] * 145 / 32768)) for x in range(40, 920)]
    for start, end in zip(points, points[1:]):
        line(*start, *end, (15, 118, 110)); line(start[0], start[1]+1, end[0], end[1]+1, (15, 118, 110))
    raw = b"".join(b"\0" + pixels[y*width*3:(y+1)*width*3] for y in range(height))
    data = (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + png_chunk(b"IDAT", zlib.compress(raw, 9)) + png_chunk(b"IEND", b""))
    path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(data)

def screenshot(page):
    if page not in PAGES: raise KeyError(page)
    generated = WORK / "shots" / f"{page}.png"
    render_waveform(generated)
    published = SHOT_BASELINES / f"{page}.png"
    if os.environ.get("VERIFY_UPDATE_BASELINES") == "1":
        published.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(generated, published)
    return published if published.exists() else generated

def tree_hash(path):
    digest = hashlib.sha256()
    for item in sorted(p for p in path.rglob("*") if p.is_file()):
        digest.update(item.relative_to(path).as_posix().encode() + b"\0" + item.read_bytes())
    return digest.hexdigest()

def run_check():
    rules = []
    def record(name, ok, detail):
        rules.append(ok); print(f"{name}: {'PASS' if ok else 'FAIL'} - {detail}")
    test = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                          cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    record("required-tests", test.returncode == 0, "python unittest suite passed" if test.returncode == 0 else "python unittest suite failed")
    outputs, errors = {}, []
    for name in FLOWS:
        try: outputs[name] = stable_json(flow_result(name))
        except Exception as error: errors.append(f"{name}: {type(error).__name__}")
    record("flows", not errors, f"{len(outputs)}/{len(FLOWS)} flows passed" if not errors else "; ".join(errors))
    mismatches = []
    for name in FLOWS:
        baseline = FLOW_BASELINES / f"{name}.json"
        if not baseline.exists(): mismatches.append(f"{name} missing; run VERIFY_UPDATE_BASELINES=1 ./verify run {name}")
        elif outputs.get(name) != baseline.read_text(): mismatches.append(f"{name} differs")
    record("flow-baselines", not mismatches, "; ".join(mismatches) if mismatches else f"{len(FLOWS)} baselines matched")
    shot_errors = []
    for page in PAGES:
        baseline = SHOT_BASELINES / f"{page}.png"
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / f"{page}.png"; render_waveform(generated)
            if not baseline.exists(): shot_errors.append(f"{page} missing; run VERIFY_UPDATE_BASELINES=1 ./verify screenshot {page}")
            elif generated.read_bytes() != baseline.read_bytes(): shot_errors.append(f"{page} differs")
    record("screenshots", not shot_errors, "; ".join(shot_errors) if shot_errors else f"{len(PAGES)} baseline matched")
    seed(quiet=True); first = tree_hash(WORK); seed(quiet=True); second = tree_hash(WORK)
    record("seed-idempotence", first == second, "fixture state hash stable" if first == second else "fixture state changed")
    passed, failed = sum(rules), len(rules)-sum(rules)
    print(f"check: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1

def main():
    parser = argparse.ArgumentParser(prog="./verify")
    commands = parser.add_subparsers(dest="command", required=True); commands.add_parser("seed")
    run = commands.add_parser("run"); run.add_argument("flow", nargs="?"); run.add_argument("--list", action="store_true")
    shot = commands.add_parser("screenshot"); shot.add_argument("page", nargs="?"); shot.add_argument("--list", action="store_true")
    commands.add_parser("check")
    args = parser.parse_args()
    if args.command == "seed": seed(); return 0
    if args.command == "run":
        if args.list: print("\n".join(FLOWS)); return 0
        if args.flow is None: run.error("a flow or --list is required")
        try: output = stable_json(flow_result(args.flow))
        except KeyError: print(f"verify: unknown flow: {args.flow}", file=sys.stderr); return 2
        if os.environ.get("VERIFY_UPDATE_BASELINES") == "1":
            FLOW_BASELINES.mkdir(parents=True, exist_ok=True); (FLOW_BASELINES / f"{args.flow}.json").write_text(output)
        print(output, end=""); return 0
    if args.command == "screenshot":
        if args.list: print("\n".join(PAGES)); return 0
        if args.page is None: shot.error("a page or --list is required")
        try: path = screenshot(args.page)
        except KeyError: print(f"verify: unknown page: {args.page}", file=sys.stderr); return 2
        result = {"ok": True, "page": args.page, "path": path.relative_to(ROOT).as_posix(),
                  "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        print(stable_json(result), end=""); return 0
    return run_check()

if __name__ == "__main__": raise SystemExit(main())
