"""
src/coords/run_coordinate_pipeline.py

PURPOSE:
--------
Convert all ECI trajectories in data/generated/ into Earth-fixed LLA coordinates.
Handles truth, observed, estimated, and reference SGP4 trajectories dynamically.
"""

from pathlib import Path
import json
from datetime import datetime, timezone

from src.io_utils.load_trajectory import load_trajectory
from src.coords.trajectory_to_lla import trajectory_eci_to_lla
from src.coords.write_lla_csv import write_lla_csv

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "generated"
TIME_REF_PATH = ROOT / "time_reference.json"

def load_time_reference():
    if not TIME_REF_PATH.exists():
        raise FileNotFoundError(
            "Missing time_reference.json — global time contract violated."
        )

    with TIME_REF_PATH.open("r") as f:
        tref = json.load(f)

    epoch = datetime.fromisoformat(tref["epoch_utc"].replace("Z", "+00:00"))
    return epoch

def process_file(filename_eci, filename_lla, epoch_utc):
    eci_path = DATA_DIR / filename_eci
    lla_path = DATA_DIR / filename_lla

    if not eci_path.exists():
        # It's fine if some files (like reference_sgp4.csv) don't exist yet
        return

    print(f"Converting {filename_eci} to Earth-fixed coordinates...")
    times, positions, _ = load_trajectory(eci_path)
    lla = trajectory_eci_to_lla(times, positions, epoch_utc)
    write_lla_csv(lla_path, times, lla)
    print(f"Saved: {lla_path}")

def main():
    try:
        epoch_utc = load_time_reference()
    except Exception as e:
        print(f"Error loading time reference: {e}")
        return

    # Process all available ECI trajectories
    trajectories = [
        ("truth.csv", "truth_lla.csv"),
        ("observed.csv", "observed_lla.csv"),
        ("estimated.csv", "estimated_lla.csv"),
        ("reference_sgp4.csv", "reference_sgp4_lla.csv")
    ]

    for eci, lla in trajectories:
        process_file(eci, lla, epoch_utc)

if __name__ == "__main__":
    main()
