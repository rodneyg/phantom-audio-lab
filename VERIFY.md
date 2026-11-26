# Deterministic verification

Run from the repository root with Python 3.11 or later. If you already created `.venv` and installed the dependencies for the README demo, start at the activation command:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
. .venv/bin/activate
```

After setup, the verifier works without internet access. The reconnect flow uses a loopback socket. Generated fixtures and screenshots go in the gitignored `.verify/work/` directory. The check command also creates and removes a temporary directory for its screenshot comparison.

```sh
./verify seed
./verify run --list
./verify run framing-round-trip
./verify screenshot --list
./verify screenshot waveform
./verify check
```

`seed` prints stable JSON with the fixture timestamp, frame count, state path, and tone hash. `run --list` prints all four flows in stable order. A flow prints one JSON object:

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

`screenshot --list` prints `waveform`. `screenshot waveform` generates `.verify/work/shots/waveform.png`. Its JSON reports the path and SHA-256 of the committed baseline, `scripts/verify/baselines/screenshots/waveform.png`, when that file exists. If the baseline is missing, it reports the generated file. Run `check` to compare the generated screenshot with the baseline. On a passing run, the summary is:

```text
check: 5 passed, 0 failed
```

Update a reviewed baseline explicitly:

```sh
VERIFY_UPDATE_BASELINES=1 ./verify run framing-round-trip
VERIFY_UPDATE_BASELINES=1 ./verify screenshot waveform
```

Repeat the flow command for each changed flow. Normal runs never overwrite committed baselines. The fixed fixture, stable JSON ordering, and fixed image dimensions make outputs repeatable in the same environment. `./verify check` is the CI gate.
