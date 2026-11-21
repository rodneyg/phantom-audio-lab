# Deterministic verification

Run from the repository root with Python 3.11 or later. If you already created `.venv` and installed the dependencies for the README demo, start at the activation command:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
. .venv/bin/activate
```

The verification tool runs offline after setup and writes generated state only to the gitignored `.verify/work/` directory.

```sh
./verify seed
./verify run --list
./verify run framing-round-trip
./verify screenshot --list
./verify screenshot waveform
./verify check
```

`seed` prints stable JSON with the fixed clock, frame count, state path, and tone hash. `run --list` prints all four flows in stable order. A flow prints one JSON object:

```json
{
  "flow": "framing-round-trip",
  "ok": true,
  "result": {
    "bytes": 1028,
    "packet_bytes": 1028,
    "round_trip_equal": true,
    "seq": 7
  }
}
```

`screenshot --list` prints `waveform`. `screenshot waveform` prints stable JSON and generates `.verify/work/shots/waveform.png`. The committed baseline is `scripts/verify/baselines/screenshots/waveform.png`. `check` prints one PASS or FAIL line per rule and ends with:

```text
check: 5 passed, 0 failed
```

Update a reviewed baseline explicitly:

```sh
VERIFY_UPDATE_BASELINES=1 ./verify run framing-round-trip
VERIFY_UPDATE_BASELINES=1 ./verify screenshot waveform
```

Repeat the flow command for each changed flow. Normal runs never overwrite committed baselines. The fixed fixture, frozen clock, stable JSON ordering, fixed image dimensions, and standard-library PNG encoder make repeated outputs byte-identical. `./verify check` is the CI gate.
