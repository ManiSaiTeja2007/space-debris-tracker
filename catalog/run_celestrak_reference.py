"""
catalog/run_celestrak_reference.py

PURPOSE:
--------
Generate a reference trajectory using SGP4 based on CelesTrak TLE data.

IMPORTANT SCIENTIFIC RULES:
---------------------------
- This module DOES NOT define time.
- All time information is read from `time_reference.json`.
- This module is REFERENCE-ONLY (not truth).
"""

from pathlib import Path
import json
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
from sgp4.api import Satrec, jday

from common_io.load_trajectory import write_trajectory_csv


# ------------------------------------------------------------
# Resolve paths
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "generated"
TIME_REF_PATH = ROOT / "time_reference.json"


# ------------------------------------------------------------
# Load global time reference
# ------------------------------------------------------------
def load_time_reference():
    if not TIME_REF_PATH.exists():
        raise FileNotFoundError(
            "Missing time_reference.json — global time contract violated."
        )

    with TIME_REF_PATH.open("r") as f:
        tref = json.load(f)

    epoch = datetime.fromisoformat(tref["epoch_utc"].replace("Z", "+00:00"))
    dt = float(tref["dt_seconds"])
    steps = int(tref["steps"])

    return epoch, dt, steps


# ------------------------------------------------------------
# Fetch TLE (ISS only for now)
# ------------------------------------------------------------
def load_iss_tle():
    """
    Hardcoded ISS TLE for reproducibility.
    (Online fetch will be added later in v0.6+)
    """
    line1 = "1 25544U 98067A   24001.00000000  .00016717  00000+0  10270-3 0  9993"
    line2 = "2 25544  51.6416  34.2078 0004023  80.1327  27.2144 15.50000000    15"
    return line1, line2


# ------------------------------------------------------------
# Main SGP4 propagation
# ------------------------------------------------------------
def main():
    # Load time contract
    epoch_utc, dt, steps = load_time_reference()

    # Load TLE
    tle_l1, tle_l2 = load_iss_tle()
    sat = Satrec.twoline2rv(tle_l1, tle_l2)

    times = []
    positions = []
    velocities = []

    for i in range(steps):
        current_time = epoch_utc + timedelta(seconds=i * dt)

        jd, fr = jday(
            current_time.year,
            current_time.month,
            current_time.day,
            current_time.hour,
            current_time.minute,
            current_time.second + current_time.microsecond * 1e-6,
        )

        error, r, v = sat.sgp4(jd, fr)
        if error != 0:
            raise RuntimeError(f"SGP4 propagation error code: {error}")

        times.append(i * dt)
        positions.append(np.array(r) * 1000.0)  # km → m
        velocities.append(np.array(v) * 1000.0)  # km/s → m/s

    # Write reference trajectory
    out_path = DATA_DIR / "reference_sgp4.csv"
    write_trajectory_csv(out_path, times, positions, velocities)

    print(f"SGP4 reference written: {out_path}")
    print("Object: ISS (ZARYA)")


# ------------------------------------------------------------
if __name__ == "__main__":
    main()
