import json
import pathlib
import sys

sys.stdout.reconfigure(encoding="utf-8")
p = pathlib.Path(r"C:\Users\Administrator\.dsh\skills\code-video\out\spec.json")
s = json.loads(p.read_text(encoding="utf-8"))
print(f"duration={s['duration']} fps={s['fps']} {s['width']}x{s['height']}")
for i in s["timeline"]:
    cap = str(i.get("caption") or "")
    print(f"{i['start']:6.2f}-{i['end']:6.2f}  {i['style']:<14} {cap[:44]}")
