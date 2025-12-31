from pathlib import Path 
from datetime import datetime, timezone, timedelta
import numpy as np

from catalog.celestrak import fetch_active_tles
from catalog.catalog_reader import read_tles
from catalog.selectors import select_by_name
from catalog.sgp4_propagator import propagate_tle
from catalog.write_reference_csv import write_csv

def run(repo_root: Path, dt: float, steps: int):
    cache = repo_root / "data" / "catalogs" / "celestrak"
    tle_path = fetch_active_tles(cache)

    tles = read_tles(tle_path)
    name, l1, l2 = select_by_name(tles, "ISS")

    # Use current UTC as reference epoch (simple & explicit)
    t0 = datetime.now(timezone.utc)

    times = []
    rs = []
    vs = []

    for i in range(steps):
        t = i * dt
        epoch = t0 + timedelta(seconds=t)
        r, v = propagate_tle(l1, l2, epoch)
        times.append(t)
        rs.append(r)
        vs.append(v)

    out = repo_root / "data" / "generated" / "reference_sgp4.csv"
    write_csv(out, times, rs, vs)
    print(f"SGP4 reference written: {out}")
    print(f"Object: {name}")

if __name__ == "__main__":
    # Defaults aligned with Julia v0.1/v0.2
    run(Path(__file__).resolve().parents[1], dt=10.0, steps=int(5400/10.0))

