"""Set the world version in crash3/archipelago.json. Used by semantic-release: python tools/set_version.py 1.2.3"""
import json
import re
import sys
from pathlib import Path

MANIFEST = Path(__file__).resolve().parent.parent / "crash3" / "archipelago.json"

version = sys.argv[1]
if not re.fullmatch(r"\d+\.\d+\.\d+", version):
    sys.exit(f"not a plain x.y.z version: {version}")
manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
manifest["world_version"] = version
MANIFEST.write_text(json.dumps(manifest, indent=4) + "\n", encoding="utf-8")
print(f"{MANIFEST.name}: world_version = {version}")
