from pathlib import Path 
from datetime import datetime, timezone

from common_io.load_trajectory import load_trajectory
from coords.trajectory_to_lla import trajectory_eci_to_lla
from coords.write_lla_csv import write_lla_csv

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "generated"

t, r, _ = load_trajectory(DATA / "truth.csv")

start_utc = datetime.now(timezone.utc)

lla = trajectory_eci_to_lla(t, r, start_utc)

out = DATA / "truth_lla.csv"
write_lla_csv(out, t, lla)

print(f"Earth-fixed coordinates written: {out}")

