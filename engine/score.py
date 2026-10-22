"""score.py -- procedural music. No samples, no network.

Every note is synthesised from oscillators + envelopes written to a WAV file,
then muxed by ffmpeg. Deterministic given the seed.
"""
from __future__ import annotations

import math
import struct
import wave
import numpy as np


SR = 44100


def _adsr(n, a, d, s, r):
    out = np.zeros(n, np.float32)
    na, nd, ns = int(SR * a), int(SR * d), int(SR * s)
    nr = int(SR * r)
    na = max(1, min(na, n))
    nd = max(1, min(nd, max(0, n - na)))
    ns = max(0, min(ns, max(0, n - na - nd)))
    nr = max(0, min(nr, max(0, n - na - nd - ns)))
    i = 0
    if na:
        out[:na] = np.linspace(0, 1, na, dtype=np.float32)
        i = na
    if nd:
        out[i:i + nd] = np.linspace(1, s, nd, dtype=np.float32)
        i += nd
    if ns:
        out[i:i + ns] = s
        i += ns
    if nr:
        out[i:i + nr] = np.linspace(s, 0, nr, dtype=np.float32)
    return out


def tone(freq, dur, kind="sine", amp=0.3, detune=0.0, env=(0.01, 0.08, 0.6, 0.25)):
    n = int(SR * dur)
    t = np.arange(n, dtype=np.float32) / SR
    ph = TAU_ = 2 * np.pi * freq * t
    if kind == "sine":
        w = np.sin(ph)
    elif kind == "tri":
        w = 2.0 / np.pi * np.arcsin(np.sin(ph))
    elif kind == "saw":
        w = 2.0 * ((freq * t) % 1.0) - 1.0
    elif kind == "square":
        w = np.sign(np.sin(ph))
    elif kind == "pulse":
        w = np.where((t * freq) % 1.0 < 0.25, 1.0, -1.0)
    else:
        w = np.sin(ph)
    if detune:
        w = 0.6 * w + 0.4 * np.sin(2 * np.pi * (freq * (1 + detune)) * t)
    return w * _adsr(n, *env) * amp


def noise_burst(dur, amp=0.15, env=(0.002, 0.05, 0.2, 0.4), seed=0):
    n = int(SR * dur)
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(n).astype(np.float32)
    # one-pole low pass -> filtered noise (a "shhh", not a sample)
    y = np.empty_like(x)
    prev = 0.0
    for i in range(n):
        prev = prev * 0.82 + x[i] * 0.18
        y[i] = prev
    return y * _adsr(n, *env) * amp


def note_table(root=220.0, scale=(0, 3, 5, 7, 10), pattern=(0, 2, 4, 2, 3, 1, 4, 0)):
    return [root * (2 ** (scale[i % len(scale)] / 12.0)) for i in pattern]


def build(duration=61.0, bpm=96, seed=7, act_map=None):
    """Render the full score as float32 mono at SR.

    act_map: list of (start, end, role) describing the dramatic arc:
      'drive'  -- pulsing bass arpeggio
      'hollow' -- the drop-out where the upstream feature was removed
      'pad'    -- warm strings returning
      'climax' -- voices converging
      'end'    -- low resolving drone
    """
    n = int(SR * duration)
    bus = np.zeros(n, np.float32)
    rng = np.random.default_rng(seed)

    if not act_map:
        act_map = [(0.0, duration, "drive")]

    def add(seg, buf):
        i = int(seg[0] * SR)
        j = min(n, i + len(buf))
        if i < n and j > i:
            bus[i:j] += buf[:j - i]

    for (a, b, role) in act_map:
        if role == "hollow":
            # a single low hit then silence -- the removal beat
            add((a, a), tone(55.0, 1.6, "tri", 0.45, env=(0.005, 0.5, 0.3, 1.0)))
            add((a, a), noise_burst(1.2, 0.18, seed=seed + 3))
            continue
        if role == "end":
            dur = b - a
            add((a, a), tone(55.0, dur, "sine", 0.42, env=(0.6, 0.8, 0.8, min(2.0, dur * 0.5))))
            add((a, a), tone(82.4, dur, "sine", 0.16, detune=0.004,
                            env=(0.9, 0.6, 0.8, min(2.0, dur * 0.5))))
            continue

        beat = 60.0 / bpm
        steps = int((b - a) / (beat / 2))
        for i in range(steps):
            t0 = a + i * beat / 2
            if role == "drive":
                scale = (0, 3, 5, 7, 10, 12)
                deg = [0, 3, 2, 5][i % 4]
                f = 55.0 * (2 ** (scale[deg % len(scale)] / 12.0))
                add((t0, t0), tone(f, beat * 0.48, "saw", 0.24, env=(0.006, 0.05, 0.35, 0.12)))
                if i % 4 == 0:
                    add((t0, t0), tone(41.2, beat * 0.9, "sine", 0.42, env=(0.01, 0.1, 0.4, 0.3)))
                if i % 4 == 2:
                    add((t0, t0), noise_burst(0.10, 0.07, seed=seed + i))
            elif role == "pad":
                root = 110.0
                for k, mult in enumerate((1.0, 1.5, 2.0, 2.5)):
                    add((t0, t0), tone(root * mult, beat * 3.4, "tri", 0.07,
                                     detune=0.006 * (k + 1),
                                     env=(0.9, 0.5, 0.7, 1.4)))
            elif role == "climax":
                scale = (0, 3, 7, 10, 12, 14)
                f = 110.0 * (2 ** (scale[i % len(scale)] / 12.0))
                add((t0, t0), tone(f, beat * 0.7, "tri", 0.16, detune=0.008,
                                  env=(0.02, 0.12, 0.5, 0.3)))
                add((t0, t0), tone(f * 2, beat * 0.4, "sine", 0.07,
                                  env=(0.01, 0.08, 0.4, 0.2)))
    # master: soft clip + fade
    bus = np.tanh(bus * 0.85) * 0.92
    fade = int(SR * 0.6)
    bus[:fade] *= np.linspace(0, 1, fade)
    bus[-fade:] *= np.linspace(1, 0, fade)
    return bus


def write_wav(path, samples, sr=SR):
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767.0).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path


def default_act_map(spec):
    """Derive the dramatic map from the beat spec's timeline."""
    amap = []
    timeline = spec.get("timeline") or []
    for item in timeline:
        if not isinstance(item, dict):
            continue
        amap.append((float(item.get("start", 0)), float(item.get("end", 0)),
                     item.get("music", "drive")))
    if not amap:
        amap = [(0.0, float(spec.get("duration", 61.0)), "drive")]
    return amap