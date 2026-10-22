"""brief.py -- turn an interview brief into a renderable spec.

The timeline is NEVER hard-coded. The brief (collected by the interview)
carries a list of narrative beats; this module decides how long each beat
lasts, which visual style carries it, and what payload that style needs.

Two public entry points:
  build_spec(brief)  -> the JSON spec consumed by director.py
  render_prompt(brief) -> the human-readable prompt (same format as the
                         reference reel), generated from the same brief so the
                         document and the video can never drift apart.
"""
from __future__ import annotations

import json
import re
import textwrap


# --------------------------------------------------------------------------
# style deck: what each engine style can carry, and what it needs
# --------------------------------------------------------------------------
# tags describe the CONTENT a style suits, not the topic.
STYLE_DECK = [
    {
        "style": "phyllotaxis", "label": "PHYLLOTAXIS", "beat": "title",
        "tags": ["title", "brand", "hero", "intro", "logo", "opening"],
        "payload": {"headline": "{title}", "kicker": "{kicker}"},
    },
    {
        "style": "truchet", "label": "TRUCHET", "beat": "mechanics",
        "tags": ["mechanics", "system", "process", "pipeline", "problem", "background"],
        "payload": {"caption": "{headline}", "kicker": "{kicker}"},
    },
    {
        "style": "flow", "label": "FLOW FIELD", "beat": "problem",
        "tags": ["problem", "obstacle", "block", "loss", "conflict", "risk"],
        "payload": {"caption": "{headline}", "kicker": "{kicker}"},
    },
    {
        "style": "voronoi", "label": "VORONOI", "beat": "repair",
        "tags": ["repair", "restore", "fix", "rebuild", "solution", "reassemble"],
        "payload": {"caption": "{headline}", "kicker": "{kicker}"},
    },
    {
        "style": "ascii", "label": "ASCII", "beat": "code",
        "tags": ["code", "terminal", "text", "claim", "audit", "checklist"],
        "payload": {"terminal": "{terminal}", "headline": "{headline}"},
    },
    {
        "style": "halftone", "label": "HALFTONE", "beat": "features",
        "tags": ["feature", "features", "capability", "entry", "menu", "print"],
        "payload": {"plates": "{plates}"},
    },
    {
        "style": "swiss", "label": "SWISS GRID", "beat": "components",
        "tags": ["component", "components", "variant", "stack", "options", "matrix"],
        "payload": {"kicker": "{kicker}", "rows": "{rows}"},
    },
    {
        "style": "crt", "label": "CRT / VHS", "beat": "trust",
        "tags": ["trust", "safety", "security", "signal", "scan", "clean", "no-virus"],
        "payload": {"claims": "{claims}", "ticker": "{headline}"},
    },
    {
        "style": "kaleidoscope", "label": "KALEIDOSCOPE", "beat": "ecosystem",
        "tags": ["ecosystem", "library", "community", "variety", "grid", "catalog"],
        "payload": {"caption": "{headline}"},
    },
    {
        "style": "xy", "label": "OSCILLOSCOPE XY", "beat": "flow",
        "tags": ["flow", "steps", "sequence", "wiring", "signal-path", "steps"],
        "payload": {"steps": "{rows}"},
    },
    {
        "style": "blueprint", "label": "BLUEPRINT", "beat": "architecture",
        "tags": ["architecture", "structure", "design", "engineering", "modules", "system"],
        "payload": {"title": "{title}", "sheet": "{sheet}", "modules": "{modules}"},
    },
    {
        "style": "terrain", "label": "TERRAIN", "beat": "scale",
        "tags": ["scale", "size", "volume", "data", "codebase", "growth"],
        "payload": {"caption": "{headline}"},
    },
    {
        "style": "editorial", "label": "EDITORIAL", "beat": "legal",
        "tags": ["legal", "license", "colophon", "credit", "attribution", "history"],
        "payload": {"kicker": "{kicker}", "body": "{body}", "quote": "{headline}",
                    "folio": "{folio}"},
    },
    {
        "style": "galaxy", "label": "GALAXY", "beat": "community",
        "tags": ["community", "stars", "open-source", "collective", "future"],
        "payload": {"caption": "{headline}"},
    },
    {
        "style": "destijl", "label": "DE STIJL", "beat": "recompose",
        "tags": ["recompose", "layout", "redesign", "geometry", "grid-cut", "restyle"],
        "payload": {"caption": "{headline}"},
    },
    {
        "style": "pixelsort", "label": "PIXELSORT", "beat": "progress",
        "tags": ["progress", "speed", "throughput", "performance", "download"],
        "payload": {"caption": "{headline}"},
    },
    {
        "style": "plotter", "label": "PLOTTER", "beat": "action",
        "tags": ["action", "one-click", "launch", "finish", "result", "call"],
        "payload": {"caption": "{headline}", "rose": "{rose}"},
    },
    {
        "style": "metaballs", "label": "METABALLS", "beat": "fusion",
        "tags": ["fusion", "combine", "integrate", "whole", "merge", "bundle"],
        "payload": {"caption": "{headline}"},
    },
    {
        "style": "matrix", "label": "MATRIX", "beat": "payoff",
        "tags": ["payoff", "final", "url", "call-to-action", "converge", "repo"],
        "payload": {"payoff": "{payoff}", "caption": "{headline}"},
    },
]

DECK_BY_STYLE = {s["style"]: s for s in STYLE_DECK}

# ordered fallback: the classic narrative arc, used when tags do not match
DEFAULT_ORDER = [s["style"] for s in STYLE_DECK]

ENDCARD_STYLE = "endcard"


# --------------------------------------------------------------------------
# spec assembly
# --------------------------------------------------------------------------
def _fmt(value, field):
    """Turn a brief field into the payload shape a style expects."""
    if value is None:
        return None
    if isinstance(value, list):
        return value
    return value


def _fill(template, beat, brief):
    """Substitute {placeholders} in a style payload template.

    Only plain strings are templates. A list (modules) or dict (a rose curve's
    {n, d}) is structural payload and is passed through untouched -- stringifying
    it would break the scene that expects to call .get() on it.
    """
    if isinstance(template, (list, tuple, dict)):
        return template
    if not isinstance(template, str):
        return template
    ctx = dict(beat)
    ctx.setdefault("title", brief.get("title", ""))
    ctx.setdefault("kicker", brief.get("kicker", ""))
    ctx.setdefault("sheet", brief.get("sheet", "REV A / 1:1"))
    ctx.setdefault("folio", brief.get("folio", "- 01 -"))
    ctx.setdefault("rose", brief.get("rose", {"n": 6, "d": 5}))
    ctx.setdefault("modules", brief.get("modules", []))
    ctx.setdefault("body", brief.get("body", ""))
    ctx.setdefault("terminal", brief.get("terminal", ""))
    ctx.setdefault("payoff", brief.get("payoff", "19"))
    ctx.setdefault("claims", brief.get("claims", []))
    ctx.setdefault("plates", brief.get("plates", []))
    ctx.setdefault("rows", brief.get("rows", []))
    out = template
    # a template that is exactly one placeholder forwards the value with its
    # original type; only mixed text ("{a} / {b}") is string-formatted
    stripped = out.strip()
    if stripped.startswith("{") and stripped.endswith("}") and stripped.count("{") == 1:
        name = stripped[1:-1]
        if name in ctx:
            val = ctx[name]
            if isinstance(val, (list, tuple, dict)):
                return val
    for key, val in ctx.items():
        out = out.replace("{" + key + "}", "" if val is None else str(val))
    return out


def assign_styles(beats: list[dict]) -> list[str]:
    """Pick a style per beat: explicit choice wins, else tag matching.

    Each style is used at most once so the reel keeps 19 distinct worlds.
    """
    used: set[str] = set()
    assigned: list[str] = []
    for i, b in enumerate(beats):
        want = (b.get("style") or "").strip()
        if want in DECK_BY_STYLE and want not in used:
            assigned.append(want)
            used.add(want)
            continue
        tags = set(t.lower() for t in (b.get("tags") or []))
        role = (b.get("role") or "").lower()
        best, best_score = None, 0
        for s in STYLE_DECK:
            if s["style"] in used:
                continue
            score = 0
            for tg in s["tags"]:
                if tg in tags:
                    score += 3
                if role and tg == role:
                    score += 5
                if role and s["beat"] == role:
                    score += 4
            if b.get("title") and tg_word_match(s, b):
                score += 1
            if score > best_score:
                best, best_score = s["style"], score
        if best is None:
            for s in DEFAULT_ORDER:
                if s not in used:
                    best = s
                    break
        assigned.append(best or DEFAULT_ORDER[i % len(DEFAULT_ORDER)])
        used.add(assigned[-1])
    return assigned


def tg_word_match(style: dict, beat: dict) -> bool:
    hay = " ".join(str(v) for v in beat.values() if isinstance(v, str)).lower()
    return any(t in hay for t in style["tags"])


def allocate(beats: list[dict], duration: float, endcard_len: float = 2.0) -> list[tuple[float, float]]:
    """Split the runtime across beats by their relative weight."""
    body = max(1.0, duration - endcard_len)
    weights = []
    for b in beats:
        w = float(b.get("weight", 1.0))
        weights.append(max(0.2, w))
    total = sum(weights)
    spans = []
    t = 0.0
    for w in weights:
        d = body * w / total
        spans.append((t, t + d))
        t += d
    spans.append((t, duration))
    return spans


def _ensure_payload(style: str, payload: dict, merged: dict) -> dict:
    """Fill every payload slot a style needs with something renderable.

    A terse brief (no components list, no terminal lines) must still produce a
    complete frame, so each structural slot falls back to brief-derived content
    rather than an empty list that would crash the scene.
    """
    title = str(merged.get("title", "") or "")
    headline = str(merged.get("headline", "") or "")
    fallback = headline or title or "SECTION"
    fixes = {
        "rows": lambda: merged.get("rows") or merged.get("components") or [fallback],
        "plates": lambda: merged.get("plates") or [fallback, "B", "C"],
        "claims": lambda: merged.get("claims") or ["0 VIRUS", "0 AD", "0 TRACKER"],
        "terminal": lambda: merged.get("terminal") or (
            f"{merged.get('repo_short', '')}".strip() or fallback),
        "modules": lambda: merged.get("modules") or [
            {"name": fallback, "sub": "01"}],
        "body": lambda: merged.get("body") or fallback,
        "payoff": lambda: merged.get("payoff") or "19",
        "headline": lambda: fallback,
        "kicker": lambda: merged.get("kicker") or "",
        "caption": lambda: fallback,
        "title": lambda: title or fallback,
        "sheet": lambda: merged.get("sheet") or "REV A / 1:1",
        "folio": lambda: merged.get("folio") or "- 01 -",
        "rose": lambda: merged.get("rose") or {"n": 6, "d": 5},
    }
    for key in list(payload.keys()):
        val = payload.get(key)
        if isinstance(val, str) and val.strip() == "{":
            val = "{"  # a lone brace can never be a template
        if val in (None, "", []):
            fix = fixes.get(key)
            if fix:
                payload[key] = fix()
    # structural slots that the template produced but that are the wrong type
    if isinstance(payload.get("rows"), str):
        payload["rows"] = [payload["rows"]]
    if isinstance(payload.get("plates"), str):
        payload["plates"] = [payload["plates"]]
    if isinstance(payload.get("claims"), str):
        payload["claims"] = [payload["claims"]]
    if isinstance(payload.get("modules"), str):
        payload["modules"] = [{"name": payload["modules"], "sub": "01"}]
    return payload


def validate(brief: dict) -> list[str]:
    """Check a brief before spending 30 minutes rendering it.

    Returns a list of human-readable problems; empty means the brief is safe to
    build. Raises nothing -- callers decide whether to warn or abort.
    """
    problems: list[str] = []
    if not isinstance(brief, dict):
        return ["brief must be a JSON object"]

    duration = brief.get("duration", 61.0)
    try:
        duration = float(duration)
    except (TypeError, ValueError):
        problems.append(f"duration is not a number: {duration!r}")
        duration = 0.0
    if duration < 6:
        problems.append(f"duration {duration}s is too short (need >= 6s: 2s endcard "
                        f"+ at least 4 acts)")
    if duration > 600:
        problems.append(f"duration {duration}s exceeds the 600s sanity cap")

    beats = brief.get("beats")
    if not beats:
        problems.append("beats is empty -- the interview must produce at least one act")
    elif not isinstance(beats, list):
        problems.append("beats must be a list")
    else:
        seen: dict[str, int] = {}
        for i, b in enumerate(beats):
            if not isinstance(b, dict):
                problems.append(f"beat[{i}] is not an object")
                continue
            if not b.get("role") and not b.get("tags") and not b.get("style"):
                problems.append(f"beat[{i}] has no role/tags/style, so it cannot be matched")
            st = b.get("style")
            if st:
                if st not in DECK_BY_STYLE:
                    problems.append(f"beat[{i}] uses unknown style {st!r}; "
                                    f"known: {', '.join(DECK_BY_STYLE)}")
                elif st in seen:
                    problems.append(f"beat[{i}] repeats style {st!r} already used by "
                                    f"beat[{seen[st]}]; each style renders once")
                else:
                    seen[st] = i
            w = b.get("weight", 1.0)
            try:
                if float(w) <= 0:
                    problems.append(f"beat[{i}] weight must be positive, got {w!r}")
            except (TypeError, ValueError):
                problems.append(f"beat[{i}] weight is not a number: {w!r}")
        if len(beats) > len(DECK_BY_STYLE):
            problems.append(f"{len(beats)} beats but only {len(DECK_BY_STYLE)} styles; "
                            f"extras would repeat a style")

    pal = brief.get("palette") or {}
    if not isinstance(pal, dict):
        problems.append("palette must be an object")
    else:
        for key, val in pal.items():
            if not isinstance(val, str) or not re.fullmatch(r"#?[0-9a-fA-F]{6}", val):
                problems.append(f"palette.{key} is not a hex colour: {val!r}")

    data = brief.get("data") or {}
    if data and not isinstance(data, dict):
        problems.append("data must be an object")
    elif isinstance(data, dict):
        heights = data.get("heights")
        if heights is not None:
            if not isinstance(heights, list) or not all(
                    isinstance(x, (int, float)) for x in heights):
                problems.append("data.heights must be a list of numbers")
            elif len(heights) < 8:
                problems.append(f"data.heights has {len(heights)} values; the terrain "
                                f"act looks flat below ~8")

    ec = brief.get("endcard_lines")
    if ec is not None and not isinstance(ec, list):
        problems.append("endcard_lines must be a list of [text, face, size]")

    return problems


def build_spec(brief: dict) -> dict:
    """Turn an interview brief into a full render spec."""
    duration = float(brief.get("duration", 61.0))
    beats = list(brief.get("beats") or [])
    if not beats:
        raise ValueError("brief has no beats -- the interview must produce at least one")

    styles = assign_styles(beats)
    endcard_len = float(brief.get("endcard_seconds", 2.0))
    spans = allocate(beats, duration, endcard_len)

    timeline = []
    for i, (b, style) in enumerate(zip(beats, styles)):
        deck = DECK_BY_STYLE[style]
        payload = {}
        merged = dict(brief)
        merged.update({k: v for k, v in b.items() if v not in (None, "", [], {})})
        for key, tmpl in deck["payload"].items():
            payload[key] = _fill(tmpl, merged, merged)
        # a style always gets a usable payload, even from a terse brief
        payload = _ensure_payload(style, payload, merged)
        music = b.get("music") or brief.get("music_default", "drive")
        timeline.append({
            "style": style,
            "start": round(spans[i][0], 3),
            "end": round(spans[i][1], 3),
            "music": music,
            "beat": payload,
            "caption": b.get("headline", ""),
        })

    # end card
    timeline.append({
        "style": ENDCARD_STYLE,
        "start": round(spans[-1][0], 3),
        "end": round(duration, 3),
        "music": "end",
        "beat": {"lines": brief.get("endcard_lines", [])},
        "caption": "",
    })

    spec = {
        "title": brief.get("title", ""),
        "duration": duration,
        "fps": int(brief.get("fps", 60)),
        "width": int(brief.get("width", 1920)),
        "height": int(brief.get("height", 1080)),
        "seed": int(brief.get("seed", 7)),
        "grain": float(brief.get("grain", 0.010)),
        "vignette": float(brief.get("vignette", 1.0)),
        "output": brief.get("output", "code-video.mp4"),
        "palette": brief.get("palette", {}),
        "music": brief.get("music", {"enabled": True, "bpm": 96}),
        "data": brief.get("data", {}),
        "timeline": timeline,
        # style keys, so render_prompt can look labels back up
        "beats": list(styles),
        "endcard": brief.get("endcard", {}),
    }
    return spec


# --------------------------------------------------------------------------
# the human-readable prompt (same shape as the reference reel)
# --------------------------------------------------------------------------
def render_prompt(brief: dict) -> str:
    spec = build_spec(brief)
    title = brief.get("title", "UNTITLED")
    subtitle = brief.get("subtitle", "")
    duration = spec["duration"]
    fps = spec["fps"]
    frames = int(round(duration * fps))
    styles = [DECK_BY_STYLE[s]["label"] for s in spec["beats"]]
    n_styles = len(styles)

    lines = []
    lines.append(
        f"做一个 {int(duration)} 秒、{n_styles} 种风格、不调用任何视频模型的代码视频。"
    )
    lines.append(
        "每一帧都是 Python 算出来的：numpy 数组 → ffmpeg。配乐也是程序化合成的，"
    )
    lines.append("没有一个采样素材。"
                 f"片长精确 {duration:.3f} 秒，{spec['width']}×{spec['height']}，"
                 f"{fps}fps，共 {frames} 帧。")
    lines.append("代码是 AI 写的，画面不是 —— 没有任何扩散模型、视频大模型参与，")
    lines.append("所有像素都是数学公式跑出来的。")
    lines.append(f"一次跑完，就能得到 {n_styles} 个完全不同的世界。")

    if subtitle:
        lines.append("")
        lines.append("## 视频主题（必须完整传达）")
        lines.append(subtitle)

    lines.append("")
    lines.append("## 时间轴")
    for item, style in zip(spec["timeline"], styles + ["END CARD"]):
        start = float(item["start"])
        mm = int(start // 60)
        ss = int(start % 60)
        ts = f"{mm:02d}:{ss:02d}"
        label = DECK_BY_STYLE.get(item["style"], {}).get("label", item["style"].upper())
        cap = item.get("caption") or ""
        lines.append(f"{ts} {label:<16} {cap}".rstrip())

    lines.append("")
    lines.append("## 技术栈")
    lines.append("Python 3.11 · numpy · OpenCV · Pillow · ffmpeg")
    lines.append("无网络请求，无外部素材，无视频生成模型")
    if brief.get("music_note"):
        lines.append(brief["music_note"])

    if brief.get("palette"):
        lines.append("")
        lines.append("## 画面与配色规则")
        for k, v in brief["palette"].items():
            lines.append(f"- {k}: {v}")

    if brief.get("rules"):
        lines.append("")
        lines.append("## 规则")
        for r in brief["rules"]:
            lines.append(f"- {r}")

    ec = brief.get("endcard") or {}
    if ec:
        lines.append("")
        lines.append("## 片尾卡文案（必须逐字渲染）")
        for k, v in ec.items():
            lines.append(str(v))

    return "\n".join(lines)


def save(spec: dict, path) -> None:
    import pathlib
    pathlib.Path(path).write_text(
        json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import sys
    brief = json.loads(open(sys.argv[1], encoding="utf-8").read())
    if "--prompt" in sys.argv:
        print(render_prompt(brief))
    else:
        print(json.dumps(build_spec(brief), ensure_ascii=False, indent=2))