import json
from pathlib import Path

# Build registry from real catalog generator inventory
import sqlite3
con = sqlite3.connect(r'C:\Users\郑曾波\Projects\company-wiki\.source_catalog\catalog.sqlite3', timeout=30)
rows = con.execute(
    "SELECT DISTINCT generator_name, generator_version FROM artifacts "
    "WHERE generator_name IS NOT NULL AND generator_name != '' AND status='completed'"
).fetchall()
con.close()
registry = {}
for name, ver in rows:
    registry.setdefault(name, set()).add(ver)
print(f"generators: {len(registry)}")
print(json.dumps({k: sorted(v) for k, v in registry.items()}, indent=2))

# allowed_roots: paths where artifact files might reside
roots = [
    Path(r'C:\Users\郑曾波\Projects\company-wiki\companies'),
    Path(r'C:\Users\郑曾波\Projects\dayu-agent\workspace\portfolio'),
    Path.home() / 'Dropbox' / 'Stock',
    Path(r'C:\Users\郑曾波\Projects\company-wiki\future_lake'),
]
print("allowed_roots:", [str(r) for r in roots if r.is_dir()])
