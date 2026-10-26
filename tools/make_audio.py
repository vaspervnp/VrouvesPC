"""Make the music and the sound effects (art/audio/*.wav) from the notes and the AY effect
tables of the CPC original (../VrouvesCPC/tools/gen_assets.py).

    .venv/bin/python tools/make_audio.py [path/to/VrouvesCPC]

The tune gets a lyra-like lead (a bright saw with vibrato), a plucked laouto bass and a
soft beat; the effects are played the way the AY chip plays them, one step per 50 Hz frame.
"""
import os
import sys
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CPC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(ROOT), "VrouvesCPC")
sys.path.insert(0, os.path.join(CPC, "tools"))
import gen_assets as g  # noqa: E402

RATE = 44100
OUT = os.path.join(ROOT, "art", "audio")
FRAME = 1 / 50


def freq(name):
    n, octv = name[:-1], int(name[-1])
    midi = 12 * (octv + 1) + g.NOTE_IDX[n]
    return 440.0 * 2 ** ((midi - 69) / 12)


def write(name, x):
    x = np.clip(x, -1, 1)
    os.makedirs(OUT, exist_ok=True)
    with wave.open(os.path.join(OUT, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes((x * 32000).astype("<i2").tobytes())


def adsr(n, a=0.01, d=0.08, s=0.7, r=0.05):
    t = np.arange(n) / RATE
    dur = n / RATE
    env = np.where(t < a, t / a, np.where(t < a + d, 1 - (1 - s) * (t - a) / d, s))
    rel = np.clip((dur - t) / r, 0, 1)
    return env * rel


def lead(f, n, phase0=0.0):
    t = np.arange(n) / RATE
    vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.clip(t / 0.15, 0, 1)
    ph = phase0 + np.cumsum(f * vib / RATE)
    saw = 2 * (ph % 1) - 1
    sq = np.sign(np.sin(2 * np.pi * ph)) * 0.3
    x = 0.6 * saw + sq
    # a one-pole low-pass to take the edge off
    y = np.empty_like(x)
    acc, k = 0.0, 0.25
    for i in range(n):
        acc += k * (x[i] - acc)
        y[i] = acc
    return y * adsr(n, 0.02, 0.1, 0.75, 0.04)


def pluck(f, n):
    """Karplus-Strong, a laouto-ish plucked string"""
    p = max(2, int(RATE / f))
    buf = np.random.default_rng(int(f)).uniform(-1, 1, p)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % p]
        buf[i % p] = 0.5 * (buf[i % p] + buf[(i + 1) % p]) * 0.996
    return out * adsr(n, 0.002, 0.2, 0.6, 0.03)


def drum(kind, n):
    t = np.arange(n) / RATE
    if kind == "kick":
        return np.sin(2 * np.pi * (60 + 90 * np.exp(-t * 30)) * t) * np.exp(-t * 14)
    noise = np.random.default_rng(7).uniform(-1, 1, n)
    return noise * np.exp(-t * (60 if kind == "hat" else 22)) * (0.25 if kind == "hat" else 0.5)


def music():
    six = g.SIXTEENTH * FRAME
    mel = g.parse_mel(g.MEL_A) + g.parse_mel(g.MEL_A) + g.parse_mel(g.MEL_B)
    bass = g.bass_line()
    total = sum(d for _, d in mel) * FRAME
    n = int(total * RATE)
    out = np.zeros(n + RATE)
    pos = 0
    for (note, d) in mel:
        ln = int(d * FRAME * RATE)
        if note != "R":
            out[pos:pos + ln] += 0.32 * lead(freq(note), ln)
        pos += ln
    pos = 0
    for (note, d) in bass:
        ln = int(d * FRAME * RATE)
        if note != "R" and pos < n:
            seg = pluck(freq(note), ln)
            out[pos:pos + ln] += 0.38 * seg[:len(out[pos:pos + ln])]
        pos += ln
    beat = int(4 * six * RATE)
    for k in range(0, n // beat + 1):
        p = k * beat
        for (off, kind) in ((0, "kick"), (2, "hat"), (3, "hat")):
            q = p + int(off * six * RATE)
            ln = min(int(0.2 * RATE), n - q)
            if ln > 0:
                out[q:q + ln] += 0.22 * drum(kind, ln)
    out = out[:n]
    # a short fade at the loop point so it joins cleanly
    f = int(0.01 * RATE)
    out[:f] *= np.linspace(0, 1, f)
    out[-f:] *= np.linspace(1, 0, f)
    write("music", out * 0.9)


def sfx():
    rng = np.random.default_rng(1)
    for name, steps in g.SFX.items():
        n1 = int(FRAME * RATE)
        out = []
        phase = 0.0
        lfsr_val = 1.0
        nph = 0.0
        for (period, nper, vol) in steps:
            amp = 0 if vol == 0 else 2 ** ((vol - 15) / 2)
            t = np.zeros(n1)
            if period:
                f = 1e6 / (16 * period)
                ph = phase + np.arange(1, n1 + 1) * f / RATE
                phase = ph[-1]
                t += np.sign(np.sin(2 * np.pi * ph)) * 0.6
            if nper:
                fn = 1e6 / (16 * nper)
                seq = np.empty(n1)
                for i in range(n1):
                    nph += fn / RATE
                    if nph >= 1:
                        nph %= 1
                        lfsr_val = rng.choice((-1.0, 1.0))
                    seq[i] = lfsr_val
                t += seq * 0.6
            out.append(t * amp)
        x = np.concatenate(out + [np.zeros(int(0.03 * RATE))])
        write(name.lower().replace("sfx_", "sfx_"), x * 0.8)


if __name__ == "__main__":
    music()
    sfx()
    print("audio in", OUT, sorted(os.listdir(OUT)))
