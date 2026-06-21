"""
common_io/load_trajectory.py

CANONICAL TRAJECTORY I/O CONTRACT

This file defines the ONE AND ONLY format used for trajectory
exchange between Julia, Python, and R.

Do NOT duplicate trajectory writing logic elsewhere.
"""

from pathlib import Path
import pandas as pd
import numpy as np


# ============================================================
# CSV FORMAT (LOCKED)
# ============================================================
# time   : seconds since global epoch
# x,y,z  : ECI position (meters)
# vx,vy,vz : ECI velocity (m/s)
# ============================================================


def write_trajectory_csv(path, times, positions, velocities):
    """
    Write trajectory to CSV using canonical format.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    df = pd.DataFrame(
        {
            "time": times,
            "x": [p[0] for p in positions],
            "y": [p[1] for p in positions],
            "z": [p[2] for p in positions],
            "vx": [v[0] for v in velocities],
            "vy": [v[1] for v in velocities],
            "vz": [v[2] for v in velocities],
        }
    )

    df.to_csv(path, index=False)


def load_trajectory(path):
    """
    Load trajectory CSV in canonical format.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Trajectory file not found: {path}")

    df = pd.read_csv(path)

    times = df["time"].to_numpy(dtype=float)
    positions = df[["x", "y", "z"]].to_numpy(dtype=float)
    velocities = df[["vx", "vy", "vz"]].to_numpy(dtype=float)

    return times, positions, velocities
