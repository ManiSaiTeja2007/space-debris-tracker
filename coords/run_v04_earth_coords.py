"""
coords/run_v04_earth_coords.py

PURPOSE:
--------
Convert ECI trajectories into Earth-fixed coordinates
(ECEF -> latitude / longitude / altitude).

IMPORTANT SCIENTIFIC RULES:
---------------------------
- This module DOES NOT define time.
- All time information is read from `time_reference.json`.
- Coordinate transforms are deterministic and reproducible.
"""

from pathlib import Path
import json
from datetime import datetime, timedelta, timezone

import numpy as np

from common_io.load_trajectory import load_trajectory
from coords.trajectory_to_lla import trajectory_eci_to_lla
from coords.write_lla_csv import write_lla_csv


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
# Main coordinate conversion
# ------------------------------------------------------------
def main():
    # Load global time contract
    epoch_utc, dt, steps = load_time_reference()

    # Load ECI trajectory
    truth_path = DATA_DIR / "truth.csv"
    times, positions, _ = load_trajectory(truth_path)

    # Sanity check: time alignment
    if len(times) != steps:
        raise ValueError("Time reference and trajectory length mismatch.")

    # Convert trajectory
    lla = trajectory_eci_to_lla(times, positions, epoch_utc)

    # Write Earth-fixed trajectory
    out_path = DATA_DIR / "truth_lla.csv"
    write_lla_csv(out_path, times, lla)

    print(f"Earth-fixed coordinates written: {out_path}")


# ------------------------------------------------------------
if __name__ == "__main__":
    main()
