"""
common_io/load_trajectory.py

PURPOSE:
--------
Canonical I/O contract for trajectory data.

This module defines:
- how trajectories are written to CSV
- how trajectories are read from CSV

This file is the SINGLE SOURCE OF TRUTH for trajectory formats.
"""

from pathlib import Path
import numpy as np
import pandas as pd


# ============================================================
# TRAJECTORY CSV FORMAT (LOCKED)
# ============================================================
# Columns:
#   time        : seconds since global epoch
#   x, y, z     : position in ECI frame (meters)
#   vx, vy, vz  : velocity in ECI frame (m/s)
#
# This format is shared by:
#   - Julia truth
#   - SGP4 reference
#   - Downstream Python processing
#   - R statistical analysis
# ============================================================


def write_trajectory_csv(path, times, positions, velocities):
    """
    Write a trajectory CSV using the canonical format.

    Parameters
    ----------
    path : Path or str
        Output CSV path
    times : iterable
        Time values (seconds since epoch)
    positions : iterable
        Iterable of position vectors [x, y, z] in meters
    velocities : iterable
        Iterable of velocity vectors [vx, vy, vz] in m/s
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "time": times,
        "x": [p[0] for p in positions],
        "y": [p[1] for p in positions],
        "z": [p[2] for p in positions],
        "vx": [v[0] for v in velocities],
        "vy": [v[1] for v in velocities],
        "vz": [v[2] for v in velocities],
    }

    df = pd.DataFrame(data)
    df.to_csv(path, index=False)


def load_trajectory(path):
    """
    Load a trajectory CSV in canonical format.

    Parameters
    ----------
    path : Path or str
        Input CSV path

    Returns
    -------
    times : np.ndarray
        Time values (seconds since epoch)
    positions : np.ndarray
        Position vectors, shape (N, 3)
    velocities : np.ndarray
        Velocity vectors, shape (N, 3)
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Trajectory file not found: {path}")

    df = pd.read_csv(path)

    times = df["time"].to_numpy(dtype=float)
    positions = df[["x", "y", "z"]].to_numpy(dtype=float)
    velocities = df[["vx", "vy", "vz"]].to_numpy(dtype=float)

    return times, positions, velocities
